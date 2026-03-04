#!/usr/bin/env bash
set -u

# ROB-KLEIN Raspberry Pi AP Diagnose Script
# Ziel: Reproduzierbare, phasenbasierte Analyse für WLAN-AP + Flask-Erreichbarkeit.

LOG_DIR="${1:-./diagnostics}"
TS="$(date +%Y%m%d_%H%M%S)"
OUT_FILE=""
SUMMARY_FILE=""

has_cmd() { command -v "$1" >/dev/null 2>&1; }

section() {
  local title="$1"
  {
    echo
    echo "============================================================"
    echo "$title"
    echo "============================================================"
  } | tee -a "$OUT_FILE"
}

run_cmd() {
  local description="$1"
  shift
  {
    echo
    echo "--- $description"
    echo "+ $*"
  } | tee -a "$OUT_FILE"

  if "$@" >>"$OUT_FILE" 2>&1; then
    echo "[OK] $description" | tee -a "$OUT_FILE"
  else
    local rc=$?
    echo "[WARN] $description (Exit $rc)" | tee -a "$OUT_FILE"
  fi
}

run_shell() {
  local description="$1"
  local cmd="$2"
  {
    echo
    echo "--- $description"
    echo "+ $cmd"
  } | tee -a "$OUT_FILE"
  if bash -lc "$cmd" >>"$OUT_FILE" 2>&1; then
    echo "[OK] $description" | tee -a "$OUT_FILE"
  else
    local rc=$?
    echo "[WARN] $description (Exit $rc)" | tee -a "$OUT_FILE"
  fi
}

collect_file() {
  local f="$1"
  run_shell "Datei anzeigen: $f" "[ -f '$f' ] && cat '$f' || echo 'Nicht vorhanden: $f'"
}

collect_phase_0() {
  section "Phase 0 – Ist-Zustand erfassen"
  run_cmd "OS Release" cat /etc/os-release
  run_cmd "Kernel" uname -a
  if has_cmd raspi-config; then
    run_cmd "WiFi Country" raspi-config nonint get_wifi_country
  else
    run_shell "WiFi Country" "echo 'raspi-config nicht verfügbar'"
  fi

  run_cmd "Interface-Übersicht" ip -br link
  if has_cmd iw; then
    run_cmd "iw dev" iw dev
    run_cmd "iw reg get" iw reg get
  else
    run_shell "iw" "echo 'iw nicht installiert'"
  fi
  if has_cmd rfkill; then
    run_cmd "rfkill list" rfkill list
  else
    run_shell "rfkill" "echo 'rfkill nicht installiert'"
  fi
  run_shell "dmesg WLAN/Firmware" "dmesg | egrep -i 'brcm|wlan|cfg80211|firmware' | tail -n 80"

  run_cmd "hostapd Status" systemctl status hostapd --no-pager
  run_cmd "dnsmasq Status" systemctl status dnsmasq --no-pager
  run_cmd "NetworkManager Status" systemctl status NetworkManager --no-pager
  run_cmd "dhcpcd Status" systemctl status dhcpcd --no-pager
  run_cmd "wpa_supplicant Status" systemctl status wpa_supplicant --no-pager

  run_cmd "hostapd Journal" journalctl -u hostapd -n 120 --no-pager
  run_cmd "dnsmasq Journal" journalctl -u dnsmasq -n 120 --no-pager
  run_cmd "Boot Journal" journalctl -b -n 200 --no-pager

  run_shell "Ports 53/67/68/5000" "ss -ltnup | egrep ':53|:67|:68|:5000'"
  run_shell "Relevante Prozesse" "ps aux | egrep 'hostapd|dnsmasq|wpa_supplicant|python|gunicorn'"

  collect_file /etc/hostapd/hostapd.conf
  collect_file /etc/default/hostapd
  collect_file /etc/dnsmasq.conf
  run_shell "dnsmasq.d Liste" "ls -la /etc/dnsmasq.d/ 2>/dev/null || echo '/etc/dnsmasq.d/ fehlt'"
  run_shell "dnsmasq.d Inhalte" "for f in /etc/dnsmasq.d/*; do [ -f \"\$f\" ] && echo '===== '\"\$f\"' =====' && cat \"\$f\"; done"
  collect_file /etc/dhcpcd.conf
  collect_file /etc/network/interfaces
  run_shell "NetworkManager Profiles" "ls -la /etc/NetworkManager/system-connections/ 2>/dev/null || echo 'NM-Profilpfad fehlt'"
  run_shell "NetworkManager Profile Inhalte" "for f in /etc/NetworkManager/system-connections/*; do [ -f \"\$f\" ] && echo '===== '\"\$f\"' =====' && cat \"\$f\"; done"

  run_cmd "ROB-KLEIN Service" systemctl status 'rob-klein*' --no-pager
  run_shell "Port 5000" "ss -ltnup | grep 5000"
  run_cmd "Local API Check" curl -i --max-time 5 http://127.0.0.1:5000/api/network_status
}

analyze_summary() {
  section "Automatische Kurz-Auswertung"
  {
    echo "Diagnose-Zusammenfassung:"

    if grep -q "country_code=" "$OUT_FILE"; then
      echo "- hostapd country_code gefunden (gut)."
    else
      echo "- [Branch A] Kein country_code in hostapd.conf erkannt → hostapd kann auf Bookworm scheitern."
    fi

    if grep -q "AP-ENABLED\|state UP" "$OUT_FILE"; then
      echo "- WLAN-Interface wirkt aktiv."
    else
      echo "- [Branch B] WLAN-Interface/AP wirkt nicht aktiv."
    fi

    if grep -q "failed\|error\|nl80211" "$OUT_FILE"; then
      echo "- [Branch C] Fehlerhinweise in Logs erkannt (hostapd/nl80211/failed/error)."
    fi

    if grep -qE "LISTEN.+:53" "$OUT_FILE"; then
      echo "- DNS-Port 53 belegt. Prüfen, ob dnsmasq oder Konflikt (systemd-resolved)."
    else
      echo "- [Branch D] Port 53 nicht offen (dnsmasq evtl. nicht aktiv)."
    fi

    if grep -qE "LISTEN.+:5000" "$OUT_FILE"; then
      echo "- Flask Port 5000 offen."
    else
      echo "- [Branch E] Flask Port 5000 nicht offen."
    fi

    if grep -q "127.0.0.1:5000" "$OUT_FILE"; then
      echo "- API lokal abgefragt. Prüfen, ob Bindung nur 127.0.0.1 statt 0.0.0.0."
    fi

    echo
    echo "Nächste Schritte (rekursiv):"
    echo "1) Phase 1: Funkhardware/Regulatory/Kill-Switch"
    echo "2) Phase 2: Service-Konflikte (NM vs dhcpcd vs wpa_supplicant)"
    echo "3) Phase 3: hostapd-Syntax + Kanal + Country"
    echo "4) Phase 4: dnsmasq-Portkonflikte/DHCP"
    echo "5) Phase 5: wlan0 statische IP/Netz"
    echo "6) Phase 6: Flask-Bindung 0.0.0.0:5000 + Firewall"
  } | tee "$SUMMARY_FILE"

  {
    echo
    echo "Summary gespeichert: $SUMMARY_FILE"
    echo "Komplettlog gespeichert: $OUT_FILE"
  } | tee -a "$OUT_FILE"
}

usage() {
  cat <<USAGE
Verwendung:
  $(basename "$0") [LOG_DIR]

Beispiel:
  sudo ./scripts/setup/pi_ap_diagnose.sh /tmp/rob-klein-diag
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

OUT_FILE="${LOG_DIR%/}/pi_ap_diagnose_${TS}.log"
SUMMARY_FILE="${LOG_DIR%/}/pi_ap_summary_${TS}.txt"
mkdir -p "$LOG_DIR"

section "ROB-KLEIN AP Diagnose gestartet"
run_shell "Laufkontext" "date; whoami; hostname; pwd"
collect_phase_0
analyze_summary
