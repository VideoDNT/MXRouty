#!/usr/bin/env bash
# MXRouty — Linux-Starter (Entwicklung, analog start.bat): venv anlegen, Abhängigkeiten installieren, GUI starten (Log: mxrouty.log)
# Aufruf: bash start.sh   (oder nach chmod +x start.sh: ./start.sh)
cd "$(dirname "$0")" || exit 1
if [ ! -x ".venv/bin/python" ]; then
    echo "[start] erstelle .venv ..."
    python3 -m venv .venv || { echo "[start] FEHLER: venv — fehlt python3-venv? (sudo apt install python3-venv)"; exit 1; }
fi
.venv/bin/python -m pip install -q -r requirements.txt || { echo "[start] FEHLER: pip install"; exit 1; }
nohup .venv/bin/python main.py >/dev/null 2>&1 &
echo "[start] MXRouty läuft (Log: mxrouty.log)"
