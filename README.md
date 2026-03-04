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
- Netzwerkstatus-API `GET /api/network_status` zeigt erkannte LAN/WLAN-Interfaces und prüft, ob die bevorzugte Pi-IP (`192.168.100.2`) aktiv ist.

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

Wenn du bereits im Projektordner bist (z. B. `~/Desktop/ROB-KLEIN-main`), funktioniert dieser Ablauf zuverlässig:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Dann im Browser öffnen:

- auf dem Pi: `http://localhost:5000`
- im gleichen Netzwerk: `http://<IP-des-Pi>:5000`

Wenn du nur schnell loslegen willst (ohne venv):

```bash
python3 app.py
```

Dann im Browser `http://<IP-des-Pi>:5000` öffnen.

## WLAN-Access-Point (Raspberry Pi)

Damit sich jeder direkt mit dem Pi verbinden kann, setze ihn als AP auf (z. B. mit `hostapd` + `dnsmasq`).

1. `hostapd` installieren und SSID/Passwort setzen.
2. `dnsmasq` für DHCP im AP-Netz konfigurieren.
3. WLAN-Interface statisch konfigurieren.
4. Python-App als `systemd` Service autostarten.

> Sicherheit: Verwende ein starkes WPA2/WPA3 Passwort und setze zusätzlich einen Not-Aus im Hardwarekreis.


## Test-Suite (Konsole)

Es gibt eine vollständige Konsolen-Test-Suite mit detaillierter Ausgabe:

```bash
python tests/run_console_tests.py
```

Sie führt aus:

- **Unit Tests** (Berechnungen/Logik):
  - Grad→Steps Umrechnung
  - Clamping auf Achsgrenzen
  - Homing setzt alle Zähler auf 0
  - Stop blockiert Bewegungen
  - Enable-Pins werden wirklich auf Treiber-Logik geschaltet (Fake-GPIO-Validierung)
- **Smoke Tests**:
  - API-/Server-Erreichbarkeit nach Start
  - WLAN-Statusabfrage (`/api/network_status`)
  - Motor-Erreichbarkeit über Enable AUS/AN (`/api/enable`)
  - Konsolen-/Log-Endpunkt (`/api/logs`)

## API Kurzüberblick

- `GET /api/config` → komplette Konfiguration
- `POST /api/config` → Achsenparameter speichern
- `POST /api/move` → einzelne Achse fahren
- `POST /api/move_all` → alle Achsen fahren

## Wichtiger Hinweis für GPIO/Mechanik

- Nutze saubere Pegel, gemeinsame Masse und geeignetes Netzteil.
- Teste zuerst mit kleinen Geschwindigkeiten/Beschleunigungen.
- Endanschläge im UI ersetzen **keine** physischen Not-Aus-/Limit-Sicherheitskette.
