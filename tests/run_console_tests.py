from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def print_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_unit_tests() -> bool:
    print_header("UNIT TESTS – Berechnungen & Logik")
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_robot_suite.py")
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    print(f"\nUnit-Test Ergebnis: {'OK' if result.wasSuccessful() else 'FEHLER'}")
    return result.wasSuccessful()


def request_json(url: str, method: str = "GET", payload: dict | None = None) -> tuple[bool, str]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=3) as response:
            body = response.read().decode("utf-8")
            return True, body
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return False, str(exc)


def run_smoke_tests() -> bool:
    print_header("SMOKE TESTS – WLAN & Motor-Erreichbarkeit")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(2)

        ok_cfg, cfg_payload = request_json("http://127.0.0.1:5000/api/config")
        print(f"[1] API /api/config erreichbar: {'PASS' if ok_cfg else 'FAIL'}")

        ok_net, net_payload = request_json("http://127.0.0.1:5000/api/network_status")
        print(f"[2] API /api/network_status erreichbar: {'PASS' if ok_net else 'FAIL'}")
        if ok_net:
            data = json.loads(net_payload)
            print(f"    WLAN Interface: {data.get('wifi_interface')}")
            print(f"    WLAN verbunden: {data.get('wifi_connected')}")
            print(f"    Aktive SSID: {data.get('wifi_ssid_active')}")

        ok_disable, disable_payload = request_json("http://127.0.0.1:5000/api/enable", method="POST", payload={"enabled": False})
        ok_enable, enable_payload = request_json("http://127.0.0.1:5000/api/enable", method="POST", payload={"enabled": True})
        print(f"[3] Motor-Treiber schaltbar über Enable-Pins (AUS/AN): {'PASS' if (ok_disable and ok_enable) else 'FAIL'}")
        if ok_disable:
            print(f"    Antwort AUS: {disable_payload}")
        if ok_enable:
            print(f"    Antwort AN: {enable_payload}")

        ok_logs, logs_payload = request_json("http://127.0.0.1:5000/api/logs")
        print(f"[4] Log-Konsole /api/logs erreichbar: {'PASS' if ok_logs else 'FAIL'}")
        if ok_logs:
            logs = json.loads(logs_payload).get("logs", [])
            print(f"    Anzahl Logeinträge: {len(logs)}")
            if logs:
                print(f"    Letzter Eintrag: {logs[-1]['message']}")

        success = ok_cfg and ok_net and ok_disable and ok_enable and ok_logs
        print(f"\nSmoke-Test Ergebnis: {'OK' if success else 'FEHLER'}")
        return success
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    unit_ok = run_unit_tests()
    smoke_ok = run_smoke_tests()
    print_header("GESAMTERGEBNIS")
    print(f"Unit Tests: {'OK' if unit_ok else 'FEHLER'}")
    print(f"Smoke Tests: {'OK' if smoke_ok else 'FEHLER'}")
    return 0 if (unit_ok and smoke_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
