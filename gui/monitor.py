"""Monitor-Fenster: zwei Spalten-Gruppen — Eingang roh | Ausgang nach Remap; Filter Port/Typ/Channel."""
from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QStyle, QStyleOptionComboBox, QStylePainter
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from core.filters import TYPE_ORDER
from core.monitor import Monitor, match
from . import style

MAX_ROWS = 2000
COLS = ["Time", "Input", "Ch", "Type", "Data", "Output", "Ch", "Data"]


class MultiCombo(QComboBox):
    """Drop-Down mit Checkboxen (Mehrfachauswahl); Anzeige: Platzhalter (= alle) oder die gewählten Einträge."""
    changed = Signal()

    def __init__(self, items: list[str], placeholder: str):
        super().__init__()
        self._placeholder = placeholder
        self._model = QStandardItemModel(self)
        for t in items:
            it = QStandardItem(t); it.setFlags(Qt.ItemIsEnabled); it.setCheckState(Qt.Unchecked)   # Haken schaltet NUR unser Klick-Handler
            self._model.appendRow(it)
        self.setModel(self._model)   # nicht editierbar: Klick aufs ganze Feld öffnet, Text wird selbst gezeichnet
        self.view().pressed.connect(self._toggle)   # Klick auf Name ODER Kästchen = umschalten
        self._force_close = False
        self.view().installEventFilter(self)   # U5: Esc schließt auch bei Maus über der Liste
        self._model.itemChanged.connect(lambda _: (self.update(), self.changed.emit()))   # V2: Feldtext sofort neu zeichnen

    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if obj is self.view() and ev.type() == QEvent.KeyPress and ev.key() == Qt.Key_Escape:
            self._esc(); return True
        return super().eventFilter(obj, ev)

    def _toggle(self, index) -> None:
        it = self._model.itemFromIndex(index)
        it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)

    def hidePopup(self):  # Popup bleibt offen, solange Haken gesetzt werden (schließt bei Klick außerhalb / Esc)
        if self._force_close or not self.view().underMouse():
            self._force_close = False
            super().hidePopup()

    def _esc(self) -> None:
        self._force_close = True; self.hidePopup()

    def set_all(self, on: bool) -> None:
        for i in range(self._model.rowCount()):
            self._model.item(i).setCheckState(Qt.Checked if on else Qt.Unchecked)

    def checked(self) -> list[str]:
        return [self._model.item(i).text() for i in range(self._model.rowCount()) if self._model.item(i).checkState() == Qt.Checked]

    def display_text(self) -> str:
        sel = self.checked()
        return ", ".join(sel) if sel else self._placeholder

    def paintEvent(self, e):  # eigener Text statt "aktuelles Item"
        p = QStylePainter(self); opt = QStyleOptionComboBox(); self.initStyleOption(opt)
        opt.currentText = self.display_text()
        p.drawComplexControl(QStyle.CC_ComboBox, opt); p.drawControl(QStyle.CE_ComboBoxLabel, opt)


class _Header(QLabel):
    """Klickbare Kopfzeile."""
    clicked = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()


HEADER_H = 22


class MonitorWidget(QWidget):
    toggled = Signal(bool)  # True = aufgeklappt

    def __init__(self, monitor: Monitor):
        super().__init__()
        self.monitor = monitor
        self.expanded = False
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
        self.header = _Header(); self.header.setProperty("role", "h"); self.header.setFixedHeight(HEADER_H)
        self.header.setContentsMargins(8, 0, 0, 0); self.header.setCursor(Qt.PointingHandCursor)
        self.header.clicked.connect(self.toggle); lay.addWidget(self.header)
        self.body = QWidget(); blay = QVBoxLayout(self.body); blay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.body, 1)
        bar = QHBoxLayout()
        self.f_port = QLineEdit(); self.f_port.setPlaceholderText("Port filter"); bar.addWidget(self.f_port)
        self.f_type = MultiCombo(TYPE_ORDER, "all types"); self.f_type.setMinimumWidth(130); bar.addWidget(self.f_type)
        self.f_ch = MultiCombo([str(i) for i in range(1, 17)], "all ch"); self.f_ch.setMinimumWidth(90); bar.addWidget(self.f_ch)
        self.pause = QPushButton("Pause"); self.pause.setCheckable(True); bar.addWidget(self.pause)
        clear = QPushButton("Clear"); clear.clicked.connect(self._clear); bar.addWidget(clear)
        rf = QPushButton("Reset filters"); rf.clicked.connect(self._reset_filters); bar.addWidget(rf)
        bar.addStretch(); blay.addLayout(bar)
        self.table = QTableWidget(0, len(COLS)); self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # S1: kein Auto-Resize je Zeile
        for c, wdt in enumerate((90, 140, 30, 90, 110, 140, 30)): self.table.setColumnWidth(c, wdt)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        blay.addWidget(self.table)
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick); self._timer.start(50)
        self.set_expanded(False)

    def set_expanded(self, on: bool) -> None:
        self.expanded = on
        self.body.setVisible(on)
        self.header.setText(("▾  " if on else "▸  ") + "MIDI-Monitor")
        self.setMaximumHeight(16777215 if on else HEADER_H)
        self.toggled.emit(on)

    def toggle(self) -> None:
        self.set_expanded(not self.expanded)

    def _filters(self):
        return self.f_port.text().strip() or None, set(self.f_type.checked()), {int(c) for c in self.f_ch.checked()}

    def _tick(self) -> None:
        evs = self.monitor.drain()
        if self.pause.isChecked() or not evs or not self.expanded:   # U4: eingeklappt nur Queue leeren
            return
        port, types, chs = self._filters()
        at_bottom = self.table.verticalScrollBar().value() == self.table.verticalScrollBar().maximum()
        shown = [ev for ev in evs if match(ev, port, types, chs)]
        if not shown:
            return
        t = self.table
        t.setUpdatesEnabled(False)      # S1: gebündelt einfügen, ein Repaint pro Tick
        overflow = t.rowCount() + len(shown) - MAX_ROWS
        if overflow > 0:
            if overflow >= t.rowCount():
                t.setRowCount(0)
            else:
                for _ in range(overflow):
                    t.removeRow(0)
        start = t.rowCount(); t.setRowCount(start + len(shown))
        for i, ev in enumerate(shown):
            row = start + i
            vals = [time.strftime("%H:%M:%S", time.localtime(ev.ts)) + f".{int(ev.ts * 1000) % 1000:03d}",
                    ev.out, "" if ev.channel is None else str(ev.channel), ev.type, " ".join(str(b) for b in ev.raw),
                    ev.in_ or "—", "" if ev.channel_out is None else str(ev.channel_out),
                    " ".join(str(b) for b in ev.sent) if ev.sent else "dropped"]
            col = QColor(style.route_color(ev.out, ev.in_)) if ev.in_ else QColor(style.MUTED)
            for c, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if c in (1, 5):          # Eingang / Ausgang in Routenfarbe
                    it.setForeground(col)
                t.setItem(row, c, it)
        t.setUpdatesEnabled(True)
        if at_bottom:
            t.scrollToBottom()

    def _reset_filters(self) -> None:
        self.f_port.clear()
        for cb in (self.f_type, self.f_ch):
            cb.set_all(False)

    def _clear(self) -> None:
        self.table.setRowCount(0); self.monitor.clear()
