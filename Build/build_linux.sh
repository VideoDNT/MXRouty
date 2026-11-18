#!/bin/bash
# Baut Installer/mxrouty_<Version>_amd64.deb unter Linux (Ubuntu 24.04 = Basis von Linux Mint 22).
# PyInstaller (ein Ordner) -> /opt/mxrouty, Startmenue-Eintrag, Icon, Symlink /usr/bin/mxrouty.
# Voraussetzungen: python3.12 + venv, dpkg-deb (apt install python3.12-venv dpkg)
# Aufruf aus einer Kopie des Projektordners unter ~ (nie im verbundenen Ordner):
#   Build/build_linux.sh
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(sed -n 's/^VERSION = "\([0-9.]*\)".*/\1/p' "$ROOT/version.py")
[ -n "$VERSION" ] || { echo "VERSION nicht gefunden (version.py)"; exit 1; }
W=${WORK:-/tmp/mxrouty_build_linux}
DEB="$ROOT/Installer/MXRouty_${VERSION//./_}_linux_amd64.deb"   # Namensstandard seit 18.11.2026 (Paketname im System bleibt klein: mxrouty)
echo "Version $VERSION -> $(basename "$DEB")"

# 1. Build-venv (gleiche Staende wie Windows-Build, 04.11.2026)
if [ ! -x "$W/venv/bin/python" ]; then
  mkdir -p "$W" && python3.12 -m venv "$W/venv"
  "$W/venv/bin/pip" install -q "PySide6-Essentials==6.12.0" "python-rtmidi==1.5.8" "pyinstaller==6.22.3"
fi

# 2. exe bauen (dasselbe Rezept wie Windows; Icon-Parameter wirkt nur auf Windows)
rm -rf "$W/dist" "$W/work"
"$W/venv/bin/python" -m PyInstaller --noconfirm --clean --distpath "$W/dist" --workpath "$W/work" \
  "$ROOT/Build/MXRouty.spec" | tail -3
D="$W/dist/MXRouty"
for f in libQt6Network.so.6 libQt6Widgets.so.6; do
  find "$D" -name "$f" | grep -q . || { echo "FEHLT im Paket: $f"; exit 1; }
done

# 3. Paketbaum
P="$W/pkg"; rm -rf "$P"
mkdir -p "$P/DEBIAN" "$P/opt/mxrouty" "$P/usr/bin" "$P/usr/share/applications" "$P/usr/share/icons/hicolor/256x256/apps"
cp -r "$D"/. "$P/opt/mxrouty/"
ln -s /opt/mxrouty/MXRouty "$P/usr/bin/mxrouty"
python3 - "$ROOT/Icon/MXRouty_Icon.png" "$P/usr/share/icons/hicolor/256x256/apps/mxrouty.png" <<'PY'
import sys
from PIL import Image
Image.open(sys.argv[1]).resize((256, 256), Image.LANCZOS).save(sys.argv[2])
PY
# Lizenztexte (FOSS-Pflicht, 18.11.2026): /usr/share/doc/mxrouty/Lizenzen + copyright
mkdir -p "$P/usr/share/doc/mxrouty/Lizenzen"
cp "$ROOT/LICENSE" "$ROOT/THIRD-PARTY-NOTICES.md" "$ROOT/Build/licenses/"* "$P/usr/share/doc/mxrouty/Lizenzen/"
cat > "$P/usr/share/doc/mxrouty/copyright" <<CPR
MXRouty - MIDI routing with channel filter and remap
Source: https://github.com/VideoDNT/MXRouty
Copyright: MXRouty contributors
License: GPL-3.0-or-later (see Lizenzen/LICENSE)
Bundled: Qt 6 / PySide6 (LGPL-3.0), python-rtmidi + RtMidi (MIT), Python (PSF) - see Lizenzen/
CPR
cat > "$P/usr/share/applications/mxrouty.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=MXRouty
Comment=patch and remap MIDI
Exec=/opt/mxrouty/MXRouty
Icon=mxrouty
Terminal=false
Categories=AudioVideo;Audio;Midi;
DESK
SIZE=$(du -sk "$P/opt" | cut -f1)
cat > "$P/DEBIAN/control" <<CTRL
Package: mxrouty
Version: $VERSION
Section: sound
Priority: optional
Architecture: amd64
Installed-Size: $SIZE
Depends: libasound2t64 | libasound2, libxcb-cursor0, libxkbcommon0, libxkbcommon-x11-0, libgl1, libegl1, libfontconfig1, libdbus-1-3, libxcb-xinerama0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-render-util0, libxcb-shape0
Maintainer: VideoDNT
Description: MXRouty - MIDI routing with channel filter and remap
 Patches MIDI outs (sources) to MIDI ins (destinations) with channel filter,
 channel remap, type filter, hotplug and presets. Settings and presets are
 stored per user in ~/.config/mxrouty.
CTRL
cat > "$P/DEBIAN/postinst" <<'POST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
exit 0
POST
cp "$P/DEBIAN/postinst" "$P/DEBIAN/postrm"
chmod 755 "$P/DEBIAN/postinst" "$P/DEBIAN/postrm" "$P/opt/mxrouty/MXRouty"
chmod -R a+rX "$P/opt/mxrouty"

# 4. .deb
mkdir -p "$ROOT/Installer"
dpkg-deb --root-owner-group -Zxz -b "$P" "$DEB" >/dev/null
ls -la "$DEB"
