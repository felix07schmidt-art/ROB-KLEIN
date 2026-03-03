# ROB-KLEIN – 6-Achs-Roboter Websteuerung

Dieses Repository enthält jetzt eine lauffähige Websteuerung für einen 6-Achs-Roboter mit STEP/DIR-Treibern am Raspberry Pi.

## Features

- Weboberfläche mit **Tabs**:
  - **Steuerung**: Achsen per Slider oder Grad-Eingabe fahren.
  - **Einstellungen**: Endanschläge, max. Tempo, Steps pro 90°, Beschleunigung, GPIO-Pins.
  - **Netzwerk**: AP-Daten (SSID/Passwort/Server).
- 6 Achsen mit STEP/DIR-Ansteuerung über GPIO.
- Endanschläge werden beim Fahren serverseitig erzwungen (Clamping).
- Konfiguration wird persistent in `data/settings.json` gespeichert.
- Simulationsmodus auf Nicht-Raspberry-Systemen (wenn `RPi.GPIO` nicht verfügbar ist).

## Projektstruktur

```text
.
├── app.py                # HTTP-API + STEP/DIR Controller
├── requirements.txt      # Python-Abhängigkeiten
├── templates/
│   └── index.html        # UI mit Tabs
├── static/
│   ├── app.js            # Frontend-Logik
│   └── style.css         # Styling
├── data/
│   └── settings.json     # Laufzeit-Konfiguration (wird beim ersten Start erstellt)
└── docs/
```

## Starten

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Dann im Browser öffnen (Server hört auf `0.0.0.0`, also Ethernet **und** WLAN):

- Lokal: `http://localhost:5000`
- Über Ethernet: `http://<eth0-ip>:5000`
- Über WLAN: `http://<wlan0-ip>:5000`

## WLAN-Access-Point (Raspberry Pi)

Damit sich jeder direkt mit dem Pi verbinden kann, setze ihn als AP auf (z. B. mit `hostapd` + `dnsmasq`).

1. `hostapd` installieren und SSID/Passwort setzen.
2. `dnsmasq` für DHCP im AP-Netz konfigurieren.
3. WLAN-Interface statisch konfigurieren.
4. Python-App als `systemd` Service autostarten.

> Sicherheit: Verwende ein starkes WPA2/WPA3 Passwort und setze zusätzlich einen Not-Aus im Hardwarekreis.

## API Kurzüberblick

- `GET /api/config` → komplette Konfiguration
- `GET /api/network_status` → erkannte Ethernet-/WLAN-IP + URLs
- `POST /api/config` → Achsenparameter speichern
- `POST /api/move` → einzelne Achse fahren
- `POST /api/move_all` → alle Achsen fahren

## Wichtiger Hinweis für GPIO/Mechanik

- Nutze saubere Pegel, gemeinsame Masse und geeignetes Netzteil.
- Teste zuerst mit kleinen Geschwindigkeiten/Beschleunigungen.
- Endanschläge im UI ersetzen **keine** physischen Not-Aus-/Limit-Sicherheitskette.


## Netzwerk-Check auf dem Raspberry Pi

Falls der Browser vom PC die Seite nicht erreicht:

```bash
hostname -I
ip -4 addr show eth0
ip -4 addr show wlan0
curl http://127.0.0.1:5000/api/network_status
```

Damit siehst du direkt, unter welcher Ethernet-/WLAN-Adresse die Weboberfläche erreichbar ist.
