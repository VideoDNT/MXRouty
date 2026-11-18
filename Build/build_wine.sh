#!/bin/bash
# Baut Installer/MXRouty_Setup_<Version>.exe unter Linux (Version aus
# version.py VERSION, "_" statt "."). PyInstaller laeuft mit einer echten
# Windows-Python unter Wine, der Installer entsteht mit NSIS.
#
# Voraussetzungen (Ubuntu 24.04):
#   apt install wine64 nsis gcc-mingw-w64-x86-64 xvfb unzip
# Eingabe:
#   $1  python312_runtime.zip - Windows-Python 3.12 (python.exe, *.dll, DLLs\, Lib\;
#                               ZIP von C:\Program Files\Python312, 04.11.2026)
# Aufruf aus dem Projektordner (Kopie unter ~, nie im verbundenen Ordner):
#   Build/build_wine.sh python312_runtime.zip
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(sed -n 's/^VERSION = "\([0-9.]*\)".*/\1/p' "$ROOT/version.py")
[ -n "$VERSION" ] || { echo "VERSION nicht gefunden (version.py)"; exit 1; }
SETUP="$ROOT/Installer/MXRouty_${VERSION//./_}_win_amd64.exe"   # Namensstandard seit 18.11.2026
echo "Version $VERSION -> $(basename "$SETUP")"
PYZIP=$(readlink -f "$1")
W=${WORK:-/tmp/mxrouty_build}
export WINEPREFIX=$W/prefix WINEARCH=win64 WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml="
PY='C:\Python312\python.exe'
# Wine 9 stuerzt mit der grossen Umgebung des Cloud-Containers (>30 KB, >200 Variablen) sofort ab
# ("free(): invalid pointer" / "double free") -> Wine immer mit minimaler Umgebung starten (18.11.2026)
W_ENV=(env -i "PATH=$PATH" "HOME=$HOME" "WINEPREFIX=$WINEPREFIX" "WINEARCH=win64" "WINEDEBUG=-all"
       "WINEDLLOVERRIDES=mscoree,mshtml=" "DISPLAY=${DISPLAY:-}")
# Wine 9: Ausgabe NIE in eine Datei umleiten, nur in eine Pipe
# (sonst "init_sys_streams: Invalid handle")
wpy() { "${W_ENV[@]}" wine "$PY" "$@" 2>&1 | cat; return "${PIPESTATUS[0]}"; }

mkdir -p "$W"
[ -d "$WINEPREFIX/drive_c" ] || xvfb-run -a "${W_ENV[@]}" wineboot --init 2>&1 | cat

# 1. Windows-Python ins Prefix (ohne site-packages/test aus dem Zip)
PYDIR="$WINEPREFIX/drive_c/Python312"
if [ ! -f "$PYDIR/python.exe" ]; then
  mkdir -p "$PYDIR" && unzip -q -o "$PYZIP" -d "$PYDIR" -x "Lib/site-packages/*" "Lib/test/*" "Doc/*" "tcl/*" "Lib/idlelib/*" "Lib/turtledemo/*"
  mkdir -p "$PYDIR/Lib/site-packages"
fi
# Wine 9 kennt KERNEL32.CopyFile2 nicht -> shutil/pathlib nehmen den alten Weg
cp "$ROOT/Build/wine/sitecustomize.py" "$PYDIR/Lib/site-packages/"
# Qt6Core.dll braucht icuuc.dll (auf Windows ab 10/1903 im System, Wine hat keine)
x86_64-w64-mingw32-gcc -shared -O2 -o "$W/icuuc.dll" "$ROOT/Build/wine/icuuc_stub.c"
cp "$W/icuuc.dll" "$WINEPREFIX/drive_c/windows/system32/icuuc.dll"

# 2. Pakete (Windows-Wheels von PyPI; Staende vom 04.11.2026)
mkdir -p "$W/wheels"
pip download -q --only-binary=:all: --platform win_amd64 --python-version 3.12 \
  --implementation cp -d "$W/wheels" "PySide6-Essentials==6.12.0" "shiboken6==6.12.0" \
  "python-rtmidi==1.5.8" "pyinstaller==6.22.3" pyinstaller-hooks-contrib pefile altgraph \
  pywin32-ctypes packaging setuptools
wpy -m ensurepip --default-pip >/dev/null
wpy -m pip install -q --no-index --find-links "$("${W_ENV[@]}" winepath -w "$W/wheels")" \
  "PySide6-Essentials==6.12.0" "python-rtmidi==1.5.8" "pyinstaller==6.22.3"

# 3. exe bauen
rm -rf "$W/dist" "$W/work"
wpy -m PyInstaller --noconfirm --clean --distpath "$("${W_ENV[@]}" winepath -w "$W/dist")" \
  --workpath "$("${W_ENV[@]}" winepath -w "$W/work")" "$("${W_ENV[@]}" winepath -w "$ROOT/Build/MXRouty.spec")" \
  | tail -3
D="$W/dist/MXRouty"
chmod -R u+w "$D"
# Pruefung: gebrauchte Qt-Module im Paket?
for f in Qt6Network.dll QtNetwork.pyd Qt6Widgets.dll; do
  find "$D" -iname "$f" | grep -q . || { echo "FEHLT im Paket: $f"; exit 1; }
done

# 3b. Lizenztexte ins Paket (FOSS-Pflicht, 18.11.2026): Ordner Lizenzen neben der exe
mkdir -p "$D/Lizenzen"
cp "$ROOT/LICENSE" "$ROOT/THIRD-PARTY-NOTICES.md" "$ROOT/Build/licenses/"* "$D/Lizenzen/"

# 4. Installer
mkdir -p "$ROOT/Installer"
makensis -V2 -DVERSION="$VERSION" -DDIST="$D" -DOUTFILE="$SETUP" "$ROOT/Build/MXRouty.nsi"
ls -la "$SETUP"
