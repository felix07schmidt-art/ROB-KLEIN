# ROB-KLEIN

Grobe Projektstruktur für einen 6-Achs-Roboterarm:
- Steuerung über **Raspberry Pi 5 GPIO**
- **6x 7B6600** Treiber für Schrittmotoren

## Ordnerstruktur

```text
.
├── config/               # GPIO, Achsen- und Motor-Profile
├── data/                 # Laufzeitdaten (Logs, Telemetrie, Kalibrierwerte)
├── docs/                 # Anforderungen, Schaltplan, Sicherheit, Kalibrierung
├── firmware/             # Echtzeitnahe Steuerlogik (GPIO, Motion, Kinematik)
├── hardware/             # Hardware-Doku (Pinout, Verdrahtung, PSU, Not-Aus)
├── scripts/              # Setup-, Deploy- und Wartungsskripte
└── software/             # API, UI, Simulation und Logging
```

## Vorschlag zur nächsten Aufteilung

1. `hardware/pinout/`: GPIO-Belegung für STEP/DIR/ENA je Achse dokumentieren.
2. `config/achsen/`: Achsenparameter (Steps/mm, Limits, Richtung, Homing-Sensoren).
3. `firmware/gpio-control/`: Low-Level Treiber für Puls-Generierung auf dem Pi 5.
4. `firmware/motion-control/`: Bahnplanung, Rampen (Accel/Decel), synchronisierte 6-Achs-Fahrten.
5. `firmware/kinematik/`: Vorwärts-/Inverse-Kinematik des Roboterarms.
6. `docs/sicherheit/`: Not-Aus, Endschalter, Stromgrenzen, Recovery-Prozeduren.
