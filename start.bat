@echo off
rem MXRouty — Doppelklick genügt: venv anlegen, Abhängigkeiten installieren, GUI ohne Konsole starten (Log: mxrouty.log)
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [start] erstelle .venv ...
    python -m venv .venv || goto :err
)
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :err
start "" ".venv\Scripts\pythonw.exe" main.py
exit /b 0
:err
echo [start] FEHLER — siehe oben
pause
