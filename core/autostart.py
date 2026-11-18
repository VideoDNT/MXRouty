"""Run at startup: Autostart-Eintrag anlegen/entfernen.
Windows: Verknüpfung (.lnk) im Startup-Ordner (per PowerShell/WScript.Shell, keine Zusatzabhängigkeit), KEINE .cmd.
Linux: ~/.config/autostart/mxrouty.desktop.
Ziel: gepackt die eigene exe (sys.executable), aus dem Quellordner .venv-pythonw + main.py."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "MXRouty"
ICON = ROOT / "Icon" / ("MXRouty_Icon.ico" if sys.platform.startswith("win") else "MXRouty_Icon.png")


def _target() -> tuple[Path, str]:
    """(Programm, Argumente): gepackt = die eigene exe (MXRouty.exe / Linux-Binary), aus dem Quellordner = .venv + main.py"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable), ""
    if sys.platform.startswith("win"):
        return ROOT / ".venv" / "Scripts" / "pythonw.exe", f'"{ROOT / "main.py"}"'
    return ROOT / ".venv" / "bin" / "python", str(ROOT / "main.py")


def _entry() -> Path:
    if sys.platform.startswith("win"):
        return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / f"{NAME}.lnk"
    return Path.home() / ".config" / "autostart" / f"{NAME.lower()}.desktop"


def is_enabled() -> bool:
    return _entry().exists()


def enable() -> None:
    e = _entry(); e.parent.mkdir(parents=True, exist_ok=True)
    prog, args = _target()
    workdir = prog.parent if getattr(sys, "frozen", False) else ROOT
    if sys.platform.startswith("win"):
        (e.parent / f"{NAME}.cmd").unlink(missing_ok=True)  # alten .cmd-Eintrag (Vorversion) entfernen
        q = lambda x: str(x).replace("'", "''")   # S4: Apostroph in PowerShell-Einzelanführung escapen
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(e)}');"
              f"$s.TargetPath='{q(prog)}';$s.Arguments='{q(args)}';$s.WorkingDirectory='{q(workdir)}';"
              f"$s.IconLocation='{q(ICON)},0';$s.Description='{NAME}';$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], check=True,
                       capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        dq = lambda x: '"' + str(x).replace('"', '\\"') + '"'   # S3: Pfade mit Leerzeichen quoten
        e.write_text(f"[Desktop Entry]\nType=Application\nName={NAME}\nExec={dq(prog)} {dq(args)}\n"
                     f"Path={workdir}\nIcon={ICON}\nX-GNOME-Autostart-enabled=true\n", "utf-8")


def disable() -> None:
    _entry().unlink(missing_ok=True)
    if sys.platform.startswith("win"):
        (_entry().parent / f"{NAME}.cmd").unlink(missing_ok=True)


def set_enabled(on: bool) -> None:
    enable() if on else disable()
