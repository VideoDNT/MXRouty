# MXRouty

MIDI-Routing mit Channel-Filter und Remap — Windows und Linux.

[English version below](#english)

## Funktionen

- MIDI-Ausgänge (Quellen, links) frei auf MIDI-Eingänge (Ziele, rechts) patchen — per Drag & Drop wie Nodes
- Je Verbindung: Channel-Filter, Channel-Remap (auch ein Channel auf mehrere, Wildcard `*:n` wirkt zusätzlich), Typ-Filter (note_on, note_off, clock, start, stop, …), aktiv/inaktiv
- Mehrere Verbindungen derselben Paarung, grafische Channel-Map mit ziehbaren Linien
- Hotplug: abgezogene Geräte werden ausgegraut, nach dem Anstecken laufen die Routen nahtlos weiter
- MIDI-Monitor (Eingang roh / Ausgang nach Remap) mit Filtern nach Port, Typ und Channel
- Presets als JSON, Import/Export, letztes Preset wird beim Start geladen
- Tray-Icon mit Status, „Close to tray", „Run at startup", „Start minimized"
- Dunkle Oberfläche; keine Online-Dienste, keine Telemetrie

Ungepatchte Eingänge werden nicht geöffnet — die Geräte bleiben für andere Programme frei.

## Installation

Fertige Pakete liegen unter *Releases*:

- Windows 10/11 (64 Bit): `MXRouty_<Version>_win_amd64.exe` — Setup für alle Benutzer nach `C:\Program Files\MXRouty`. Das Setup ist nicht signiert; Windows SmartScreen zeigt beim ersten Start einen Hinweis („Weitere Informationen" → „Trotzdem ausführen").
- Linux Mint 22 / Ubuntu 24.04 (amd64): `sudo apt install ./MXRouty_<Version>_linux_amd64.deb` — installiert nach `/opt/mxrouty`, Startmenü-Eintrag, Befehl `mxrouty`.

Einstellungen und Presets liegen je Benutzer in `%APPDATA%\MXRouty` (Windows) bzw. `~/.config/mxrouty` (Linux) und bleiben bei einer Deinstallation erhalten.

## Start aus dem Quelltext

Voraussetzung: Python 3.10 oder neuer.

- Windows: `start.bat` ausführen — legt beim ersten Start `.venv` an, installiert die Abhängigkeiten und startet das Programm.
- Linux: `bash start.sh` (braucht das Paket `python3-venv`).

Aus dem Quellordner gestartet liegen `settings.json` und `presets/` im Projektordner.

## Installer bauen

Siehe `Build/`:

- `Build/build_wine.sh <python-runtime.zip>` baut die Windows-Setup-EXE unter Linux (PyInstaller unter Wine, NSIS). Die Windows-Python-Laufzeit wird als ZIP übergeben.
- `Build/build_linux.sh` baut das `.deb` (PyInstaller, dpkg-deb).

Beide nutzen `Build/MXRouty.spec`; die Version steht in `version.py`.

## Lizenz

MXRouty ist freie Software unter der GNU General Public License, Version 3 oder neuer — siehe `LICENSE`.
Verwendete Bibliotheken und ihre Lizenzen: `THIRD-PARTY-NOTICES.md`.

---

## English

MIDI routing with channel filter and remap — Windows and Linux.

### Features

- Patch MIDI outputs (sources, left) freely to MIDI inputs (destinations, right) — drag and drop like nodes
- Per connection: channel filter, channel remap (one channel to several, wildcard `*:n` always adds), type filter (note_on, note_off, clock, start, stop, …), active/inactive
- Several connections for the same pair, graphical channel map with draggable lines
- Hotplug: unplugged devices are greyed out, routes resume seamlessly after reconnecting
- MIDI monitor (input raw / output after remap) with filters by port, type and channel
- Presets as JSON, import/export, last preset loads on start
- Tray icon with status, "Close to tray", "Run at startup", "Start minimized"
- Dark UI; no online services, no telemetry

Unpatched inputs are not opened — the devices stay available for other programs.

### Installation

Packages are under *Releases*:

- Windows 10/11 (64-bit): `MXRouty_<version>_win_amd64.exe` — setup for all users into `C:\Program Files\MXRouty`. The setup is not signed; Windows SmartScreen shows a warning on first run ("More info" → "Run anyway").
- Linux Mint 22 / Ubuntu 24.04 (amd64): `sudo apt install ./MXRouty_<version>_linux_amd64.deb` — installs into `/opt/mxrouty`, adds a menu entry and the command `mxrouty`.

Settings and presets are stored per user in `%APPDATA%\MXRouty` (Windows) or `~/.config/mxrouty` (Linux) and survive uninstallation.

### Run from source

Requires Python 3.10 or newer.

- Windows: run `start.bat` — creates `.venv` on first start, installs dependencies and starts the program.
- Linux: `bash start.sh` (needs the `python3-venv` package).

When started from source, `settings.json` and `presets/` live in the project folder.

### Building the installers

See `Build/`:

- `Build/build_wine.sh <python-runtime.zip>` builds the Windows setup EXE on Linux (PyInstaller under Wine, NSIS). The Windows Python runtime is passed as a ZIP.
- `Build/build_linux.sh` builds the `.deb` (PyInstaller, dpkg-deb).

Both use `Build/MXRouty.spec`; the version is defined in `version.py`.

### License

MXRouty is free software under the GNU General Public License, version 3 or later — see `LICENSE`.
Third-party libraries and their licenses: `THIRD-PARTY-NOTICES.md`.
