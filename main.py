"""MXRouty — Einstieg: Engine + Hotplug + GUI (Node-Ansicht, Seitenleiste, Monitor, Tray). Autoload letztes Preset."""
import logging
import sys

if sys.platform.startswith("win"):  # eigenes Taskleisten-Icon statt python.exe-Icon (AppUserModelID), Linux unberührt
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VideoDNT.MXRouty")

from PySide6.QtWidgets import QApplication

from core import preset
from core.instance import SingleInstance
from core.monitor import Monitor
from core.router import Router
from gui import style
from gui.main_window import MainWindow
from gui.tray import app_icon

from pathlib import Path
if getattr(sys, "frozen", False):   # gepackt (MXRouty.exe): kein Log — nur beim Entwickeln/Debuggen aus dem Quellordner
    logging.disable(logging.CRITICAL)
else:
    _handlers = [logging.FileHandler(Path(__file__).resolve().parent / "mxrouty.log", encoding="utf-8")]
    if sys.stderr is not None:   # T4: unter pythonw gibt es keine Konsole
        _handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s", handlers=_handlers)

app = QApplication(sys.argv)
app.setApplicationName("MXRouty"); app.setWindowIcon(app_icon()); app.setStyleSheet(style.QSS)
app.setQuitOnLastWindowClosed(False)  # Fenster schließen = in Tray

instance = SingleInstance()   # T1: läuft schon eine Instanz -> deren Fenster nach vorn, hier Schluss
if not instance.try_acquire():
    logging.getLogger("mxrouty").info("Zweite Instanz — Fenster der laufenden Instanz geholt, beende")
    sys.exit(0)

path, routes = preset.autoload()
if path:
    preset.remember(path)
monitor = Monitor()
router = Router(on_event=monitor.on_event)
router.set_routes(routes)
router.start_watch(1.0)  # Hotplug

win = MainWindow(router, monitor, path)
instance.show_requested.connect(win.bring_to_front)
if preset.get_setting("start_minimized", False):
    pass                        # Start minimized: nur Tray, Fenster erst über Tray/zweiten Start
else:
    win.show()
sys.exit(app.exec())
