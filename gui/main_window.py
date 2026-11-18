"""Hauptfenster (UI-Texte englisch): oben Splitter links Geräte (Nodes) / rechts Verbindung (Seitenleiste, Default 2/3 : 1/3),
darunter Monitor (Default unteres Drittel); Teilungen + Fenstergröße/-position in settings.json gemerkt. Menü Preset laden/speichern."""
from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QPushButton, QSplitter, QVBoxLayout, QWidget)

from core import autostart, preset
from core.monitor import Monitor
from core.ports import list_ins, list_outs
from core.router import Router
from version import VERSION
from .monitor import MonitorWidget
from .nodes import NodeView, display_name
from .sidebar import Sidebar
from .tray import Tray, app_icon
from . import style


class _InlineEdit(QLineEdit):
    """Preset-Feld mit Inline-Vorschlag: ist das Getippte der Anfang eines Preset-Namens (Groß/Klein egal), wird der Rest
    markiert angehängt. Tab / Pfeil rechts übernimmt den Vorschlag; Enter nimmt NUR das Getippte (Vorschlag wird verworfen)."""
    def __init__(self, names):
        super().__init__()
        self._names = names          # Callable -> Liste der Preset-Namen
        self._sugg = False           # True = aktuell ist ein Vorschlag markiert angehängt
        self._skip = False           # nach Backspace/Entf keinen neuen Vorschlag anhängen
        self.textEdited.connect(self._suggest)

    def _suggest(self, typed: str) -> None:
        self._sugg = False
        if not typed or self._skip:
            self._skip = False
            return
        low = typed.casefold()
        for n in self._names():
            if n.casefold().startswith(low) and len(n) > len(typed):
                self.setText(typed + n[len(typed):])
                self.setSelection(len(typed), len(n) - len(typed))
                self._sugg = True
                return

    def _accept(self) -> None:
        self.deselect(); self.setCursorPosition(len(self.text())); self._sugg = False

    def _drop(self) -> None:
        if self._sugg and self.hasSelectedText():
            self.setText(self.text()[:self.selectionStart()])
        self._sugg = False

    def event(self, ev):
        # event() statt keyPressEvent: Tab wird sonst von QWidget als Fokuswechsel geschluckt
        if ev.type() == QEvent.KeyPress:
            k = ev.key()
            self._skip = k in (Qt.Key_Backspace, Qt.Key_Delete)
            if self._sugg:
                if k in (Qt.Key_Tab, Qt.Key_Right, Qt.Key_End):
                    self._accept(); return True
                if k in (Qt.Key_Return, Qt.Key_Enter):
                    self._drop()                    # weiter zu returnPressed mit nur dem Getippten
        return super().event(ev)


class MainWindow(QMainWindow):
    def __init__(self, router: Router, monitor: Monitor, preset_path: Path | None):
        super().__init__()
        self.router, self.monitor, self.preset_path = router, monitor, preset_path
        self._really_quit = False
        self.setWindowIcon(app_icon())
        geo = preset.get_setting("window")  # [x, y, w, h]
        if geo and len(geo) == 4 and self._on_screen(*geo):   # T5: nur, wenn sichtbar
            self.setGeometry(*geo)
        else:
            self.resize(1100, 720)
        self._title()

        self.nodes = NodeView(); self.sidebar = Sidebar(); self.monitor_w = MonitorWidget(monitor)
        self.nodes.set_overlay(self.sidebar)   # Connection-Panel als Pop-up in der Mitte der Node-Ansicht
        self.v_split = QSplitter(Qt.Vertical); self.v_split.addWidget(self.nodes); self.v_split.addWidget(self.monitor_w)
        central = QWidget(); cl = QVBoxLayout(central); cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(0)
        cl.addWidget(self._preset_bar()); cl.addWidget(self.v_split, 1)
        self.setCentralWidget(central)
        self.status = QLabel(); self.statusBar().addWidget(self.status, 1)
        self._layout_timer = QTimer(self); self._layout_timer.setSingleShot(True); self._layout_timer.setInterval(500)
        self._layout_timer.timeout.connect(self._save_layout)   # R2: Splitter/Fenster erst 0,5 s nach letzter Bewegung schreiben
        self.v_split.splitterMoved.connect(lambda *_: self._layout_timer.start())
        self.v_split.setCollapsible(1, False)
        self.monitor_w.toggled.connect(self._monitor_toggled)

        self.menuBar().hide()  # Preset-Verwaltung nur in der Leiste; Beenden über Tray
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_preset)

        self.nodes.routes_changed.connect(self._routes_changed)
        self.nodes.selection_changed.connect(self.sidebar.set_route)
        self.sidebar.rule_changed.connect(self._routes_changed)
        self.sidebar.delete_requested.connect(self.nodes.delete_selected)
        self._dirty = False
        self._refresh_preset_list()

        self.tray = Tray(self)
        self.nodes.set_routes(router.routes())
        self._restore_splits()
        self._poll(); self._timer = QTimer(self); self._timer.timeout.connect(self._poll); self._timer.start(1000)
        self._last_timer = QTimer(self); self._last_timer.timeout.connect(lambda: self.nodes.update_last(self.monitor.snapshot_last()))
        self._last_timer.start(200)   # "Last: Ch n" in den Port-Kästen (Sitzungsgedächtnis, Reset bei Neustart)

    @staticmethod
    def _on_screen(x: int, y: int, w: int, h: int) -> bool:
        """Liegt die Titelzeile des Fensters auf einem vorhandenen Bildschirm?"""
        from PySide6.QtCore import QRect
        from PySide6.QtGui import QGuiApplication
        probe = QRect(x, y, max(w, 100), 40)
        return any(s.availableGeometry().intersects(probe) for s in QGuiApplication.screens())

    def bring_to_front(self) -> None:
        """T1: zweite Instanz gestartet -> dieses Fenster zeigen."""
        self.showNormal(); self.raise_(); self.activateWindow()

    def _restore_splits(self) -> None:
        self._monitor_toggled(False)   # Start immer eingeklappt; Höhe beim Aufklappen aus split_v (Default unteres Drittel)

    def _monitor_toggled(self, on: bool) -> None:
        from .monitor import HEADER_H
        h = self.v_split.height() or self.height()
        if on:
            sizes = preset.get_setting("split_v") or [h * 2 // 3, h // 3]
            self.v_split.setSizes(sizes)
        else:
            self.v_split.setSizes([h - HEADER_H, HEADER_H])

    # ---- Preset-Leiste (im Fenster; Ablage = presets/ im Programmordner) ----
    def _preset_bar(self) -> QWidget:
        bar = QWidget(); l = QHBoxLayout(bar); l.setContentsMargins(8, 4, 8, 4); l.setSpacing(6)
        lab = QLabel("Preset"); lab.setProperty("role", "h"); l.addWidget(lab)
        self.preset_box = QComboBox(); self.preset_box.setEditable(True); self.preset_box.setInsertPolicy(QComboBox.NoInsert)
        self.preset_box.setLineEdit(_InlineEdit(lambda: [self.preset_box.itemText(i) for i in range(self.preset_box.count())]))
        self.preset_box.setMinimumWidth(220); self.preset_box.lineEdit().setPlaceholderText("Type name + Enter = new preset")
        self.preset_box.setCompleter(None)  # kein Qt-Completer: Enter nimmt exakt das Getippte (Inline-Vorschlag s. _InlineEdit)
        self.preset_box.activated.connect(self._preset_chosen)
        self.preset_box.lineEdit().returnPressed.connect(self._preset_entered)
        l.addWidget(self.preset_box)
        for text, fn in (("Save", self.save_preset), ("Delete", self.delete_preset),
                         ("Import…", self.import_preset), ("Save and export…", self.export_preset), ("Reset…", self.reset_dialog)):
            b = QPushButton(text); b.clicked.connect(fn); l.addWidget(b)
        l.addSpacing(12)
        self.cb_tray = QCheckBox("Close to tray"); self.cb_tray.setChecked(bool(preset.get_setting("close_to_tray", True)))
        self.cb_tray.toggled.connect(lambda v: preset.set_setting("close_to_tray", v))
        self.cb_startup = QCheckBox("Run at startup"); self.cb_startup.setChecked(bool(preset.get_setting("run_at_startup", True)))
        self.cb_startup.toggled.connect(self._set_startup)
        self.cb_min = QCheckBox("Start minimized"); self.cb_min.setChecked(bool(preset.get_setting("start_minimized", False)))
        self.cb_min.toggled.connect(lambda v: preset.set_setting("start_minimized", v))
        l.addWidget(self.cb_tray); l.addWidget(self.cb_startup); l.addWidget(self.cb_min)
        l.addStretch()
        self._set_startup(self.cb_startup.isChecked(), quiet=True)  # Default on -> Eintrag beim ersten Start anlegen
        return bar

    def _set_startup(self, on: bool, quiet: bool = False) -> None:
        preset.set_setting("run_at_startup", on)
        try:
            if on == autostart.is_enabled():     # R4: nichts tun, wenn Zustand schon stimmt (kein PowerShell bei jedem Start)
                return
            autostart.set_enabled(on)
            if not quiet:
                self._status("Run at startup: " + ("on" if on else "off"))
        except Exception as e:
            self._status(f"Run at startup failed: {e}", err=True)

    def _refresh_preset_list(self) -> None:
        self.preset_box.blockSignals(True); self.preset_box.clear()
        for p in preset.list_presets():
            self.preset_box.addItem(p.stem, str(p))
        if self.preset_path:
            i = self.preset_box.findData(str(self.preset_path))
            if i >= 0: self.preset_box.setCurrentIndex(i)
            else: self.preset_box.setCurrentText(self.preset_path.stem)
        else:
            self.preset_box.setCurrentIndex(-1); self.preset_box.setCurrentText("")
        self.preset_box.blockSignals(False)

    def _preset_chosen(self, index: int) -> None:
        path = Path(self.preset_box.itemData(index))
        if self.preset_path and path == self.preset_path:
            return
        self._load(path)

    def _preset_entered(self) -> None:
        """Name eingetippt + Enter: vorhandenes Preset laden, sonst neues Preset mit aktuellen Routen anlegen."""
        name = self.preset_box.currentText().strip()
        if not name:
            return
        path = preset.path_for(name)
        if self.preset_path and path == self.preset_path:
            self.save_preset()                       # R8: Enter auf dem geladenen Preset = einfach speichern
        elif path.exists():
            self._load(path)
        else:
            self.preset_path = path; self.save_preset(); self._refresh_preset_list()
        self.preset_box.lineEdit().clearFocus()

    def _confirm_switch(self) -> bool:
        """Ungespeicherte Änderungen: Popup Save / Discard / Cancel. True = weitermachen."""
        if not getattr(self, "_dirty", False):
            return True
        d = QDialog(self); d.setWindowTitle("Unsaved changes"); d.setModal(True)
        l = QVBoxLayout(d); l.setContentsMargins(12, 12, 12, 12)
        name = self.preset_path.stem if self.preset_path else "current connections"
        l.addWidget(QLabel(f"Unsaved changes in '{name}'."))
        row = QHBoxLayout(); row.addStretch()
        choice = {"v": None}
        for text, val in (("Save", "save"), ("Discard", "discard"), ("Cancel", "cancel")):
            b = QPushButton(text); b.clicked.connect(lambda _=False, v=val: (choice.update(v=v), d.accept())); row.addWidget(b)
        l.addLayout(row); d.exec()
        if choice["v"] == "save":
            if not self.preset_path:
                self._status("No preset name — switch cancelled", err=True); return False
            preset.save(self.preset_path, self.nodes.routes()); self._dirty = False; return True
        if choice["v"] == "discard":
            self._dirty = False; return True
        self._refresh_preset_list()  # Drop-Down auf aktuelles Preset zurück
        return False

    def _load(self, path: Path) -> None:
        if not self._confirm_switch():
            return
        self.preset_path = path; preset.remember(path)
        self.nodes.set_routes(preset.load(path)); self._routes_changed(); self._dirty = False
        self._refresh_preset_list(); self._title()

    def delete_preset(self) -> None:
        if not self.preset_path:
            return
        d = QDialog(self); d.setWindowTitle("Delete preset"); d.setModal(True)   # S5: Rückfrage
        l = QVBoxLayout(d); l.setContentsMargins(12, 12, 12, 12)
        l.addWidget(QLabel(f"Delete preset '{self.preset_path.stem}'?"))
        row = QHBoxLayout(); row.addStretch()
        b_del = QPushButton("Delete"); b_cancel = QPushButton("Cancel")
        b_del.clicked.connect(d.accept); b_cancel.clicked.connect(d.reject)
        row.addWidget(b_del); row.addWidget(b_cancel); l.addLayout(row)
        if d.exec() != QDialog.Accepted:
            return
        preset.delete(self.preset_path); self.preset_path = None; self._dirty = False
        self._refresh_preset_list(); self._title(); self._status("Preset deleted")

    def import_preset(self) -> None:
        if not self._confirm_switch():      # R3: erst Popup, dann kopieren
            return
        f, _ = QFileDialog.getOpenFileName(self, "Import preset", "", "Preset (*.json)")
        if f:
            try:
                p = preset.import_from(Path(f)); self._load(p); self._status(f"Imported: {p.name}")
            except Exception as e:
                self._status(f"Import failed: {e}", err=True)

    def export_preset(self) -> None:
        if not self.preset_path:
            return self._status("No preset selected", err=True)
        f, _ = QFileDialog.getSaveFileName(self, "Save and export preset", self.preset_path.name, "Preset (*.json)")
        if f:
            self.save_preset(); preset.export_to(self.preset_path, Path(f)); self._status(f"Exported: {f}")

    def reset_dialog(self) -> None:
        """Reset…: Dialog mit Haken Connections (vorangehakt) / Presets; Buttons Reset / Back."""
        d = QDialog(self); d.setWindowTitle("Reset"); d.setModal(True)
        l = QVBoxLayout(d); l.setContentsMargins(12, 12, 12, 12)
        cb_conn = QCheckBox("Connections"); cb_conn.setChecked(True)
        cb_pre = QCheckBox("Presets")
        cb_last = QCheckBox("Last channel list")
        l.addWidget(cb_conn); l.addWidget(cb_pre); l.addWidget(cb_last)
        row = QHBoxLayout(); row.addStretch()
        b_reset = QPushButton("Reset"); b_back = QPushButton("Back")
        b_reset.clicked.connect(d.accept); b_back.clicked.connect(d.reject)
        row.addWidget(b_reset); row.addWidget(b_back); l.addLayout(row)
        if d.exec() != QDialog.Accepted:
            return
        done = []
        if cb_pre.isChecked():
            for p in preset.list_presets():
                preset.delete(p)
            self.preset_path = None; self._refresh_preset_list(); done.append("presets")
        if cb_conn.isChecked():
            self.nodes.set_routes([]); self._routes_changed(); done.append("connections")
        if cb_last.isChecked():
            self.monitor.reset_last(); self.nodes.update_last({}); done.append("last channel list")
        self._title(); self._status("Reset: " + ", ".join(done) if done else "Nothing selected")

    # ---- Statuszeile (kein Popup) ----
    def _status(self, text: str, err: bool = False) -> None:
        self.status.setStyleSheet(f"color: {style.ERR if err else style.MUTED};")
        self.status.setText(text)

    # ---- Engine-Kopplung ----
    def _routes_changed(self) -> None:
        self.router.set_routes(self.nodes.routes())
        self.nodes.rebuild()
        self._dirty = True; self._title()
        self._poll()

    def _poll(self) -> None:
        try:
            outs, ins = list_outs(), list_ins()
            self.nodes.set_ports(outs, ins)
            self.sidebar.set_ports([display_name(p) for p in outs], [display_name(p) for p in ins], self.nodes.routes())
        except Exception as e:
            logging.getLogger("mxrouty.gui").error("Port-Scan: %s", e)   # T7
        st = self.router.status(); self.tray.set_status(st)
        missing = [n for n, ok in st.items() if not ok]
        if missing:
            self._status("Port missing: " + ", ".join(missing), err=True)
        elif self.status.text().startswith("Port missing"):
            self._status("All ports open")

    # ---- Presets ----
    def _title(self) -> None:
        name = self.preset_path.stem if self.preset_path else "no preset"
        self.setWindowTitle(f"MXRouty {VERSION} — {name}{' *' if getattr(self, '_dirty', False) else ''}")

    def save_preset(self) -> None:
        """Save: Name im Feld ist das Ziel — anderer Name als das aktuelle Preset = neues Preset (Save as)."""
        name = self.preset_box.currentText().strip()
        if name and (not self.preset_path or name != self.preset_path.stem):
            self.preset_path = preset.path_for(name)
        if not self.preset_path:
            return self._status("Enter a preset name above, then Save", err=True)
        preset.save(self.preset_path, self.nodes.routes()); preset.remember(self.preset_path)
        self._dirty = False; self._refresh_preset_list(); self._title(); self._status(f"Saved: {self.preset_path.name}")

    # ---- Fenster/Tray ----
    def _save_layout(self) -> None:
        """Fenstergeometrie + Splitter in einem Rutsch schreiben (entprellt)."""
        if not self.isMaximized() and not self.isMinimized():
            g = self.geometry(); preset.set_setting("window", [g.x(), g.y(), g.width(), g.height()])
        if self.monitor_w.expanded:                       # eingeklappte Höhe nie als Monitor-Höhe merken
            preset.set_setting("split_v", self.v_split.sizes())

    def _save_window(self) -> None:
        self._layout_timer.stop(); self._save_layout()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if hasattr(self, "_layout_timer"): self._layout_timer.start()

    def moveEvent(self, e):
        super().moveEvent(e)
        if hasattr(self, "_layout_timer"): self._layout_timer.start()

    def closeEvent(self, e):
        self._save_window()
        if self._really_quit or not self.cb_tray.isChecked():   # Close to tray aus -> X beendet komplett
            if not self._confirm_switch():                      # R5: ungespeicherte Änderungen -> Popup Save/Discard/Cancel
                self._really_quit = False; e.ignore(); return
            self._really_quit = True
            self.router.close(); e.accept()
            from PySide6.QtWidgets import QApplication
            QApplication.quit()
        else:
            e.ignore(); self.hide()

    def quit_app(self) -> None:
        self._really_quit = True
        self.showNormal(); self.close()  # closeEvent beendet (oder bricht per Popup ab)

