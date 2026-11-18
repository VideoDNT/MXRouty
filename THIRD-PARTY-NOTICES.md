# Third-party notices / Hinweise zu Drittkomponenten

MXRouty is licensed under GPL-3.0-or-later (see `LICENSE`). It uses the following components.
MXRouty steht unter GPL-3.0-or-later (siehe `LICENSE`) und verwendet folgende Komponenten.

## Runtime / Laufzeit (shipped in the installers)

| Component | License | Source |
|---|---|---|
| Python | Python Software Foundation License (PSF-2.0) | https://www.python.org/ |
| PySide6 / shiboken6 (Qt for Python) | LGPL-3.0 (also available under GPL and commercial terms) | https://www.qt.io/qt-for-python · https://code.qt.io/cgit/pyside/pyside-setup.git |
| Qt 6 (Essentials modules: QtCore, QtGui, QtWidgets, QtNetwork) | LGPL-3.0 | https://www.qt.io/ · https://code.qt.io/ |
| python-rtmidi | MIT | https://github.com/SpotlightKid/python-rtmidi |
| RtMidi (bundled in python-rtmidi) | MIT-style (RtMidi license) | https://github.com/thestk/rtmidi |

Qt is used unmodified as dynamically linked libraries; its source code is available at the links above. The installers of MXRouty version 1.1 and later carry the license texts in a `Lizenzen` folder.

Qt wird unverändert als dynamisch gelinkte Bibliothek genutzt; der Qt-Quelltext ist über die Links oben verfügbar. Die Installer ab MXRouty 1.1 enthalten die Lizenztexte im Ordner `Lizenzen`.

## Build-time only / nur zum Bauen

| Component | License | Source |
|---|---|---|
| PyInstaller | GPL-2.0-or-later with bootloader exception | https://pyinstaller.org/ |
| NSIS | zlib/libpng | https://nsis.sourceforge.io/ |
| Wine (Windows build on Linux) | LGPL-2.1 | https://www.winehq.org/ |
