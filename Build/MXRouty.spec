# -*- mode: python ; coding: utf-8 -*-
# PyInstaller-Rezept fuer MXRouty: ein Ordner, ohne Konsolenfenster.
# Aufruf (aus dem Projektordner):  pyinstaller Build\MXRouty.spec
# Ergebnis: dist\MXRouty\MXRouty.exe + _internal\ (darin Icon\ als Daten)
# Der Installer (Build\MXRouty.nsi) packt den ganzen Ordner.
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
ICON = os.path.join(ROOT, "Icon", "MXRouty_Icon.ico")

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    # Icon\ wandert nach _internal\Icon: core/autostart.py und gui/tray.py suchen es
    # relativ zum Paketstamm (Path(__file__).parents[1] = _internal)
    datas=[(os.path.join(ROOT, "Icon", "MXRouty_Icon.ico"), "Icon"),
           (os.path.join(ROOT, "Icon", "MXRouty_Icon.png"), "Icon")],
    hiddenimports=["PySide6.QtNetwork"],   # Einzelinstanz (core/instance.py)
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "_tkinter", "unittest", "pydoc", "test"],
    noarchive=False,
)
# Nicht gebraucht, zusammen ~26 MB: Software-OpenGL (reine Widgets-Oberflaeche)
# und die Qt-Uebersetzungen (die App laedt keinen QTranslator).
# Linux: das GTK-Plattformthema zieht libgtk-3/gio/glib (~12 MB) mit - die App stylt sich
# komplett selbst (dunkles QSS), das Thema wird nicht gebraucht.
_DROP = ("opengl32sw.dll", "libqgtk3.so", "libgtk-3.so.0", "libgdk-3.so.0")
a.binaries = [b for b in a.binaries
              if os.path.basename(b[0]).lower() not in _DROP]
a.datas = [d for d in a.datas
           if "translations" not in d[0].replace("\\", "/").split("/")]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MXRouty",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=ICON,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="MXRouty")
