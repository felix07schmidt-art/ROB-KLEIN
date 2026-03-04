RUN_ID: 1
ZEIT: 2026-03-04T08:47:00Z
VERMUTETE URSACHE: Diagnose- und AP-Werkzeuge fehlen in der aktuellen Umgebung; zusätzlich ist kein systemd verfügbar und Paketinstallation schlägt wegen 403-Proxysperre fehl. Dadurch kann weder AP-Stack (hostapd/dnsmasq) gestartet noch AP-Fähigkeit geprüft werden.
AUSGEFÜHRTE AKTION: apt-get update && apt-get install -y hostapd dnsmasq iw rfkill iproute2 usbutils pciutils wireless-tools kmod
ERGEBNIS: failure — apt konnte keine Repositories abrufen (HTTP 403), daher keine Pakete installiert; Zustand unverändert.
