from __future__ import annotations

import json
import subprocess
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlparse

try:
    import RPi.GPIO as GPIO  # type: ignore
except Exception:
    GPIO = None

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "data" / "settings.json"
STATIC_DIR = BASE_DIR / "static"
TEMPLATE_FILE = BASE_DIR / "templates" / "index.html"

DEFAULT_CONFIG = {
    "network": {
        "ap_ssid": "Robot-Controller",
        "ap_password": "Roboter123!",
        "expose_on_ethernet_and_wlan": True,
        "host": "0.0.0.0",
        "port": 5000,
        "preferred_ip": "192.168.100.2",
    },
    "axes": [
        {
            "id": i + 1,
            "name": f"Achse {i + 1}",
            "step_pin": 17 + (i * 2),
            "dir_pin": 18 + (i * 2),
            "min_deg": -90,
            "max_deg": 90,
            "steps_per_90_deg": 1600,
            "max_speed_steps_s": 2000,
            "accel_steps_s2": 2500,
            "invert_direction": False,
            "current_deg": 0,
        }
        for i in range(6)
    ],
}


@dataclass
class AxisRuntime:
    lock: threading.Lock


class StepDirController:
    def __init__(self, config: dict):
        self.config = config
        self._active_moves = 0
        self._active_moves_lock = threading.Lock()
        self.axes_runtime: Dict[int, AxisRuntime] = {
            axis["id"]: AxisRuntime(lock=threading.Lock()) for axis in config["axes"]
        }
        self.simulation_mode = GPIO is None
        if not self.simulation_mode:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for axis in config["axes"]:
                GPIO.setup(axis["step_pin"], GPIO.OUT)
                GPIO.setup(axis["dir_pin"], GPIO.OUT)
                GPIO.output(axis["step_pin"], GPIO.LOW)

    @staticmethod
    def _clamp(value: float, min_value: float, max_value: float) -> float:
        return max(min_value, min(max_value, value))

    def _pulse(self, step_pin: int, pulse_delay_s: float) -> None:
        if self.simulation_mode:
            return
        GPIO.output(step_pin, GPIO.HIGH)
        time.sleep(pulse_delay_s)
        GPIO.output(step_pin, GPIO.LOW)
        time.sleep(pulse_delay_s)

    def move_axis_to(self, axis_id: int, target_deg: float) -> dict:
        axis = next((a for a in self.config["axes"] if a["id"] == axis_id), None)
        if not axis:
            raise ValueError(f"Achse {axis_id} nicht gefunden")

        runtime = self.axes_runtime[axis_id]
        with runtime.lock:
            clamped_target = self._clamp(target_deg, axis["min_deg"], axis["max_deg"])
            delta_deg = clamped_target - axis["current_deg"]
            if abs(delta_deg) < 1e-6:
                return {"axis_id": axis_id, "target_deg": clamped_target, "current_deg": axis["current_deg"], "steps": 0}

            steps_per_deg = axis["steps_per_90_deg"] / 90.0
            total_steps = int(round(abs(delta_deg) * steps_per_deg))
            direction_positive = delta_deg >= 0
            if axis.get("invert_direction", False):
                direction_positive = not direction_positive

            if not self.simulation_mode:
                GPIO.output(axis["dir_pin"], GPIO.HIGH if direction_positive else GPIO.LOW)

            max_speed = max(100.0, float(axis["max_speed_steps_s"]))
            accel = max(100.0, float(axis["accel_steps_s2"]))
            current_speed = 100.0
            min_delay = 1.0 / max_speed / 2.0

            with self._track_move():
                for _ in range(total_steps):
                    current_speed = min(max_speed, current_speed + accel * 0.001)
                    pulse_delay = max(min_delay, 1.0 / current_speed / 2.0)
                    self._pulse(axis["step_pin"], pulse_delay)

            axis["current_deg"] = clamped_target
            return {
                "axis_id": axis_id,
                "target_deg": clamped_target,
                "current_deg": axis["current_deg"],
                "steps": total_steps,
                "clamped": clamped_target != target_deg,
            }

    def is_moving(self) -> bool:
        with self._active_moves_lock:
            return self._active_moves > 0

    class _MoveTracker:
        def __init__(self, parent: "StepDirController"):
            self.parent = parent

        def __enter__(self) -> None:
            with self.parent._active_moves_lock:
                self.parent._active_moves += 1

        def __exit__(self, exc_type, exc, tb) -> None:
            with self.parent._active_moves_lock:
                self.parent._active_moves = max(0, self.parent._active_moves - 1)

    def _track_move(self) -> "StepDirController._MoveTracker":
        return StepDirController._MoveTracker(self)


def load_config() -> dict:
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        network_config = config.setdefault("network", {})
        network_config.setdefault("host", "0.0.0.0")
        network_config.setdefault("port", 5000)
        network_config.setdefault("expose_on_ethernet_and_wlan", True)
        network_config.setdefault("preferred_ip", "192.168.100.2")
        return config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")


def get_lan_addresses() -> List[dict]:
    try:
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "up"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return []

    addresses: List[dict] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        interface_name = parts[1]
        if not interface_name.startswith(("eth", "en", "wlan", "wl")):
            continue
        cidr = next((part for part in parts if "/" in part and part.count(".") == 3), None)
        if not cidr:
            continue
        ip_addr = cidr.split("/", 1)[0]
        addresses.append({"interface": interface_name, "ip": ip_addr})

    unique_addresses: Dict[str, dict] = {}
    for entry in addresses:
        unique_addresses[f"{entry['interface']}:{entry['ip']}"] = entry
    return [unique_addresses[key] for key in sorted(unique_addresses.keys())]


def get_lan_urls(port: int) -> List[str]:
    return [f"http://{entry['ip']}:{port} ({entry['interface']})" for entry in get_lan_addresses()]


def get_network_status() -> dict:
    network = config_store["network"]
    port = int(network.get("port", 5000))
    preferred_ip = network.get("preferred_ip", "192.168.100.2")
    lan_addresses = get_lan_addresses()
    return {
        "host": network.get("host", "0.0.0.0"),
        "port": port,
        "preferred_ip": preferred_ip,
        "preferred_url": f"http://{preferred_ip}:{port}",
        "reachable_urls": [f"http://{entry['ip']}:{port}" for entry in lan_addresses],
        "interfaces": lan_addresses,
        "preferred_ip_detected": any(entry["ip"] == preferred_ip for entry in lan_addresses),
        "wifi_connected": is_wifi_connected(),
    }


def get_wifi_interface() -> str | None:
    for interface in get_lan_addresses():
        interface_name = interface["interface"]
        if interface_name.startswith(("wlan", "wl")):
            return interface_name
    try:
        result = subprocess.run(
            ["ip", "-o", "link", "show"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None

    for line in result.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 2:
            continue
        interface_name = parts[1].strip()
        if interface_name.startswith(("wlan", "wl")):
            return interface_name
    return None


def is_wifi_connected() -> bool:
    interface = get_wifi_interface()
    if not interface:
        return False
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", interface],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False
    return "inet " in result.stdout


def configure_wifi_connection() -> None:
    network = config_store.setdefault("network", {})
    wifi_ssid = network.setdefault("wifi_ssid", "KRA1 W-Lan")
    wifi_password = network.setdefault("wifi_password", "kukakuka")
    network.setdefault("wifi_hidden", False)

    wifi_interface = get_wifi_interface()
    if not wifi_interface:
        print("WLAN: Keine WLAN-USB-Antenne erkannt (Interface wlan*/wl* nicht gefunden).")
        return

    try:
        nmcli_exists = subprocess.run(
            ["nmcli", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("WLAN: 'nmcli' ist nicht installiert. WLAN wird nicht automatisch konfiguriert.")
        return

    if nmcli_exists.returncode != 0:
        print("WLAN: NetworkManager ist nicht verfügbar. WLAN wird nicht automatisch konfiguriert.")
        return

    connection_name = "robot-wifi"
    existing = subprocess.run(
        ["nmcli", "-t", "-f", "NAME", "connection", "show"],
        capture_output=True,
        text=True,
        check=False,
    )
    connection_exists = connection_name in [line.strip() for line in existing.stdout.splitlines() if line.strip()]

    hidden_flag = "no"
    if connection_exists:
        subprocess.run(
            [
                "nmcli",
                "connection",
                "modify",
                connection_name,
                "802-11-wireless.ssid",
                wifi_ssid,
                "802-11-wireless.hidden",
                hidden_flag,
                "wifi-sec.key-mgmt",
                "wpa-psk",
                "wifi-sec.psk",
                wifi_password,
                "connection.interface-name",
                wifi_interface,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    else:
        subprocess.run(
            [
                "nmcli",
                "connection",
                "add",
                "type",
                "wifi",
                "ifname",
                wifi_interface,
                "con-name",
                connection_name,
                "ssid",
                wifi_ssid,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        subprocess.run(
            [
                "nmcli",
                "connection",
                "modify",
                connection_name,
                "802-11-wireless.hidden",
                hidden_flag,
                "wifi-sec.key-mgmt",
                "wpa-psk",
                "wifi-sec.psk",
                wifi_password,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    connect_result = subprocess.run(
        ["nmcli", "connection", "up", connection_name],
        capture_output=True,
        text=True,
        check=False,
    )
    if connect_result.returncode == 0:
        print(f"WLAN konfiguriert: SSID '{wifi_ssid}' (sichtbar), Interface {wifi_interface}.")
    else:
        error_output = connect_result.stderr.strip() or connect_result.stdout.strip() or "Unbekannter Fehler"
        print(f"WLAN-Verbindung konnte nicht aufgebaut werden: {error_output}")


def print_runtime_status() -> None:
    wifi_status = "Verbunden" if is_wifi_connected() else "Getrennt"
    motion_status = "In Bewegung" if controller.is_moving() else "Stillstand"
    print(f"Status | WLAN: {wifi_status} | Motoren: {motion_status}")


def start_status_monitor() -> None:
    def _worker() -> None:
        while True:
            print_runtime_status()
            time.sleep(2)

    thread = threading.Thread(target=_worker, daemon=True, name="status-monitor")
    thread.start()


config_store = load_config()
controller = StepDirController(config_store)


class RobotRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Datei nicht gefunden")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw) if raw else {}

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self._send_file(TEMPLATE_FILE, "text/html; charset=utf-8")
        elif path == "/api/config":
            self._send_json(config_store)
        elif path == "/api/network_status":
            self._send_json(get_network_status())
        elif path.startswith("/static/"):
            rel = path.replace("/static/", "", 1)
            file_path = STATIC_DIR / rel
            ctype = "text/plain"
            if rel.endswith(".css"):
                ctype = "text/css; charset=utf-8"
            elif rel.endswith(".js"):
                ctype = "application/javascript; charset=utf-8"
            self._send_file(file_path, ctype)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Route nicht gefunden")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        payload = self._read_json()

        try:
            if path == "/api/config":
                axes_payload: List[dict] = payload.get("axes", [])
                axis_by_id = {axis["id"]: axis for axis in config_store["axes"]}
                for axis_update in axes_payload:
                    axis_id = int(axis_update["id"])
                    if axis_id not in axis_by_id:
                        continue
                    axis = axis_by_id[axis_id]
                    for key in ["name", "step_pin", "dir_pin", "min_deg", "max_deg", "steps_per_90_deg", "max_speed_steps_s", "accel_steps_s2", "invert_direction", "current_deg"]:
                        if key in axis_update:
                            axis[key] = axis_update[key]
                    if axis["min_deg"] > axis["max_deg"]:
                        axis["min_deg"], axis["max_deg"] = axis["max_deg"], axis["min_deg"]
                    axis["current_deg"] = max(axis["min_deg"], min(axis["max_deg"], axis["current_deg"]))
                save_config(config_store)
                self._send_json({"status": "ok", "config": config_store})
                return

            if path == "/api/move":
                result = controller.move_axis_to(int(payload["axis_id"]), float(payload["target_deg"]))
                save_config(config_store)
                self._send_json({"status": "ok", "result": result})
                return

            if path == "/api/move_all":
                results = []
                for target in payload.get("targets", []):
                    results.append(controller.move_axis_to(int(target["axis_id"]), float(target["target_deg"])))
                save_config(config_store)
                self._send_json({"status": "ok", "results": results})
                return

            self.send_error(HTTPStatus.NOT_FOUND, "Route nicht gefunden")
        except Exception as exc:
            self._send_json({"status": "error", "message": str(exc)}, status=400)


def run() -> None:
    configure_wifi_connection()
    save_config(config_store)
    network = config_store["network"]
    host = network.get("host", "0.0.0.0")
    port = int(network.get("port", 5000))
    if network.get("expose_on_ethernet_and_wlan", True):
        host = "0.0.0.0"

    server = ThreadingHTTPServer((host, port), RobotRequestHandler)
    print(f"Server läuft auf http://{host}:{port}")
    start_status_monitor()
    if host == "0.0.0.0":
        network_status = get_network_status()
        lan_urls = [
            f"http://{entry['ip']}:{port} ({entry['interface']})"
            for entry in network_status["interfaces"]
        ]
        print(f"Bevorzugte Adresse: {network_status['preferred_url']}")
        if not network_status["preferred_ip_detected"]:
            print("Hinweis: Bevorzugte IP aktuell nicht auf einem LAN/WLAN-Interface gefunden.")
        if lan_urls:
            print("Erreichbar über Ethernet/WLAN:")
            for url in lan_urls:
                print(f" - {url}")
        else:
            print("Ethernet/WLAN aktiv: nutze die IP-Adresse des Geräts und Port", port)
    server.serve_forever()


if __name__ == "__main__":
    run()
