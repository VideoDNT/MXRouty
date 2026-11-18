"""Seitenleiste: Regel der ausgewählten Verbindung (Channel-Filter, Remap grafisch + Textzeile, Typ-Filter, aktiv).
Ohne Auswahl ist nur „Keine Verbindung gewählt" sichtbar.
Überschrift = zwei Drop-Downs (Eingang / Ausgang) — Umpatchen der Verbindung direkt hier.
Eingabe-Bestätigung: Checkboxen/Drop-Downs sofort; Textfelder bei Enter (verlässt das Feld) oder Fokusverlust."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from core.filters import TYPE_ORDER, Rule, remap_text
from core.router import Route
from .channelmap import ChannelMap


def _parse_set(text: str) -> set[int]:
    return {int(t) for t in text.replace(";", ",").split(",") if t.strip().isdigit() and 1 <= int(t) <= 16}


def _parse_map(text: str) -> tuple[dict[int, set[int]], set[int]]:
    """„1:5,1:7,2:6,*:1" -> ({1:{5,7}, 2:{6}}, {1}); mehrere Ziele je Quelle = Message vervielfachen."""
    out: dict[int, set[int]] = {}; all_to: set[int] = set()
    for part in text.replace(";", ",").split(","):
        if ":" in part:
            a, b = (x.strip() for x in part.split(":", 1))
            if b.isdigit() and 1 <= int(b) <= 16:
                if a == "*":
                    all_to.add(int(b))
                elif a.isdigit() and 1 <= int(a) <= 16:
                    out.setdefault(int(a), set()).add(int(b))
    return out, all_to


def _map_text(remap: dict[int, set[int]], remap_all: set[int]) -> str:
    return remap_text(Rule(remap=remap, remap_all=remap_all))


class _PopupCombo(QComboBox):
    """QComboBox, die vor dem Aufklappen einen Hook ruft (Liste frisch befüllen)."""
    about_to_show = None

    def showPopup(self):
        if self.about_to_show:
            self.about_to_show()
        super().showPopup()


class Sidebar(QWidget):
    rule_changed = Signal()
    delete_requested = Signal()   # Delete-Button im Panel

    def mousePressEvent(self, e):
        e.accept()   # Klick INS Panel erreicht die Szene nicht -> Auswahl bleibt, Pop-up bleibt offen

    def __init__(self):
        super().__init__()
        self.setFixedWidth(260)
        self.setObjectName("connpanel")   # Overlay in der Mitte der Node-Ansicht (QSS: Fläche + Rahmen)
        self._route: Route | None = None
        self._routes: list[Route] = []          # alle Routen
        self._outs: list[str] = []; self._ins: list[str] = []
        outer = QVBoxLayout(self); outer.setContentsMargins(8, 8, 8, 8)
        self.title = QLabel("No connection selected"); self.title.setProperty("role", "h"); self.title.setWordWrap(True)
        trow = QHBoxLayout(); trow.addWidget(self.title, 1)
        self.btn_delete = QPushButton("Delete"); self.btn_delete.clicked.connect(self.delete_requested)   # rechtsbündig
        trow.addWidget(self.btn_delete, 0, Qt.AlignRight); outer.addLayout(trow)
        self.body = QWidget(); lay = QVBoxLayout(self.body); lay.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame); scroll.setWidget(self.body)
        outer.addWidget(scroll, 1)
        head = QHBoxLayout(); head.setSpacing(4)
        self.cb_out = _PopupCombo(); self.cb_in = _PopupCombo()
        self.cb_out.about_to_show = lambda: self._before_popup(self.cb_out)
        self.cb_in.about_to_show = lambda: self._before_popup(self.cb_in)
        arrow = QLabel("→"); arrow.setProperty("role", "h")
        head.addWidget(self.cb_out, 1); head.addWidget(arrow); head.addWidget(self.cb_in, 1)
        lay.addLayout(head)
        self.enabled = QCheckBox("active"); lay.addWidget(self.enabled)
        g = QGroupBox("Channel"); gl = QGridLayout(g)
        gl.addWidget(QLabel("Filter (empty = all)"), 0, 0); self.channels = QLineEdit(); self.channels.setPlaceholderText("1,2,10"); gl.addWidget(self.channels, 1, 0)
        gl.addWidget(QLabel("Remap source:target"), 2, 0); self.remap = QLineEdit(); self.remap.setPlaceholderText("1:5,2:6 or *:1"); gl.addWidget(self.remap, 3, 0)
        self.cmap = ChannelMap(); gl.addWidget(self.cmap, 4, 0, alignment=Qt.AlignHCenter)
        lay.addWidget(g)
        g2 = QGroupBox("Type filter (none = all)"); g2l = QVBoxLayout(g2)
        self.types: dict[str, QCheckBox] = {}
        for t in TYPE_ORDER:
            cb = QCheckBox(t); self.types[t] = cb; g2l.addWidget(cb)
        lay.addWidget(g2); lay.addStretch()
        self.cmap.changed.connect(self._map_dragged)
        self.cb_out.currentTextChanged.connect(self._repatch)
        self.cb_in.currentTextChanged.connect(self._repatch)
        self.enabled.toggled.connect(self._apply)
        self.channels.editingFinished.connect(self._apply)
        self.remap.editingFinished.connect(self._apply)
        for le in (self.channels, self.remap):
            le.returnPressed.connect(le.clearFocus)  # Enter = bestätigen + Feld verlassen
        for cb in self.types.values():
            cb.toggled.connect(self._apply)
        self.set_route(None)

    def set_ports(self, outs: list[str], ins: list[str], routes: list[Route]) -> None:
        """Verfügbare Ports (Anzeigenamen) + alle Routen merken; Drop-Downs werden erst beim Aufklappen befüllt (R1)."""
        self._outs, self._ins, self._routes = list(outs), list(ins), list(routes)

    def _before_popup(self, cb: QComboBox) -> None:
        """Beim Aufklappen: Liste frisch befüllen, Auswahl beibehalten."""
        if self._route is None:
            return
        r = self._route; self._route = None
        items = self._outs if cb is self.cb_out else self._ins
        cur = r.out if cb is self.cb_out else r.in_
        cb.blockSignals(True); cb.clear(); cb.addItems(sorted(set(items) | {cur}, key=str.casefold)); cb.setCurrentText(cur)
        cb.blockSignals(False); self._route = r

    def _fill_combos(self, route: Route) -> None:
        for cb, items, cur in ((self.cb_out, self._outs, route.out), (self.cb_in, self._ins, route.in_)):
            cb.blockSignals(True); cb.clear()
            cb.addItems(sorted(set(items) | {cur}, key=str.casefold)); cb.setCurrentText(cur)
            cb.blockSignals(False)

    def _repatch(self) -> None:
        if self._route is None:
            return
        out, in_ = self.cb_out.currentText(), self.cb_in.currentText()
        if (out, in_) == (self._route.out, self._route.in_):
            return
        self._route.out, self._route.in_ = out, in_
        self.rule_changed.emit()

    def _map_dragged(self) -> None:
        """Grafische Map geändert -> Textzeile nachziehen -> Regel übernehmen."""
        self.remap.setText(_map_text(self.cmap.remap, self.cmap.remap_all))
        self._apply()

    def set_route(self, route: Route | None) -> None:
        self._route = None  # während Befüllen nichts zurückschreiben
        on = route is not None
        self.body.setVisible(on)
        if route is None:
            self.title.setText("No connection selected")
            for cb in (self.cb_out, self.cb_in):
                cb.blockSignals(True); cb.clear(); cb.blockSignals(False)
            self.enabled.setChecked(False); self.channels.clear(); self.remap.clear()
            for cb in self.types.values(): cb.setChecked(False)
            return
        r = route.rule
        self.title.setText("Connection")
        self._fill_combos(route)
        self.enabled.setChecked(r.enabled)
        self.channels.setText(",".join(str(c) for c in sorted(r.channels)))
        self.remap.setText(_map_text(r.remap, r.remap_all))
        self.cmap.set_mapping(r.remap, r.remap_all)
        for t, cb in self.types.items(): cb.setChecked(t in r.types)
        self._route = route

    def _apply(self) -> None:
        if self._route is None:
            return
        remap, remap_all = _parse_map(self.remap.text())
        self._route.rule = Rule(
            enabled=self.enabled.isChecked(),
            channels=_parse_set(self.channels.text()),
            remap=remap,
            types={t for t, cb in self.types.items() if cb.isChecked()},
            remap_all=remap_all,
        )
        self.cmap.set_mapping(remap, remap_all)  # Textzeile -> Map
        self.rule_changed.emit()
