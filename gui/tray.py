"""Tray-Icon: Status grün (alle Ports offen) / rot (mind. einer fehlt); Menü Anzeigen/Beenden."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import style

_ICON_DIR = Path(__file__).resolve().parents[1] / "Icon"
ICON = _ICON_DIR / ("MXRouty_Icon.ico" if sys.platform.startswith("win") else "MXRouty_Icon.png")  # Linux: .png


def app_icon() -> QIcon:
    return QIcon(str(ICON))


def _status_icon(ok: bool) -> QIcon:
    pm = app_icon().pixmap(64, 64)
    if pm.isNull():
        pm = QPixmap(64, 64); pm.fill(QColor("#7b1113"))
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor(style.OK if ok else style.ERR))); p.setPen(QPen(QColor(style.BG), 2))
    p.drawEllipse(40, 40, 22, 22); p.end()
    return QIcon(pm)


class Tray(QSystemTrayIcon):
    def __init__(self, window):
        super().__init__(_status_icon(True), window)
        self.window = window
        m = QMenu()
        m.addAction("Show", self._show)
        m.addAction("Quit", window.quit_app)
        self.setContextMenu(m)
        self.activated.connect(lambda r: self._show() if r == QSystemTrayIcon.Trigger else None)
        self.setToolTip("MXRouty")
        self.show()

    def set_status(self, status: dict[str, bool]) -> None:
        ok = all(status.values()) if status else True
        missing = [n for n, v in status.items() if not v]
        key = (ok, tuple(missing))
        if key == getattr(self, "_last_key", None):   # U6: nur bei Statuswechsel neu zeichnen
            return
        self._last_key = key
        self.setIcon(_status_icon(ok))
        self.setToolTip("MXRouty — " + ("all ports open" if ok else "missing: " + ", ".join(missing)))

    def _show(self) -> None:
        self.window.showNormal(); self.window.activateWindow()
