"""Node-Ansicht: links Eingänge (Geräte-Outs = Quellen), rechts Ausgänge (Geräte-Ins = Ziele).
Verbindung per Drag von links nach rechts ziehen; Auswahl + Entf löscht. Ports ohne Gerät ausgegraut.
Portnamen plattformabhängig gekürzt (display_name): Windows ohne Index-Suffix ' <n>' (bestätigt 02.11.2026),
Linux/ALSA nur Client-Name vor dem ersten ':' (ANNAHME zum rtmidi-ALSA-Format „Client:Port c:p", ungetestet)."""
from __future__ import annotations

import re
import sys

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem, QGraphicsScene,
                               QGraphicsSimpleTextItem, QGraphicsView, QStyle)

from core.filters import Rule, remap_text
from core.router import Route
from . import style

_WIN_SUFFIX = re.compile(r" \d+$")
_ALSA_SUFFIX = re.compile(r" \d+:\d+$")


def display_name(port: str) -> str:
    """Anzeige-/Routen-Name ohne systemabhängige Index-Anhängsel."""
    if sys.platform.startswith("win"):
        return _WIN_SUFFIX.sub("", port)
    if sys.platform.startswith("linux"):
        base = _ALSA_SUFFIX.sub("", port)          # „... 20:0" weg
        return base.split(":", 1)[0] if ":" in base else base  # Client-Name
    return port


PORT_W, PORT_H, GAP, COL_GAP = 200, 28, 10, 420   # COL_GAP: Platz für das Connection-Panel (260 px) in der Mitte


class PortItem(QGraphicsRectItem):
    def __init__(self, name: str, side: str, present: bool):
        super().__init__(0, 0, PORT_W, PORT_H)
        self.name, self.side, self.present = name, side, present
        self.label = QGraphicsSimpleTextItem(name, self)
        f = QFont(); f.setPixelSize(12); self.label.setFont(f)  # QSS setzt px -> pointSize -1 -> Warnung vermeiden
        self.label.setPos(8, 7)
        self.last = QGraphicsSimpleTextItem("", self)            # rechts: "Last: Ch n" (zuletzt gesendeter/empfangener Channel)
        f2 = QFont(); f2.setPixelSize(10); self.last.setFont(f2)
        self.last.setBrush(QBrush(QColor(style.MUTED)))
        self.setZValue(1)
        self.refresh()

    def refresh(self) -> None:
        col = style.TEXT if self.present else style.MUTED
        pen = QPen(QColor(style.BORDER if self.present else style.MUTED), 1)
        if not self.present:
            pen.setStyle(Qt.DashLine)
        self.setPen(pen)
        self.setBrush(QBrush(QColor(style.PANEL)))
        self.label.setBrush(QBrush(QColor(col)))
        self.setToolTip(self.name + ("" if self.present else " — device not present"))

    def set_last(self, chs) -> None:
        self.last.setText("Last Ch: " + ", ".join(str(c) for c in sorted(chs)) if chs else "")
        self.last.setPos(PORT_W - 8 - self.last.boundingRect().width(), 9)

    def anchor(self) -> QPointF:
        r = self.sceneBoundingRect()
        return QPointF(r.right() if self.side == "out" else r.left(), r.center().y())


class LinkItem(QGraphicsPathItem):
    def __init__(self, route: Route, src: PortItem, dst: PortItem, offset: int = 0):
        super().__init__()
        self.route, self.src, self.dst = route, src, dst
        self.offset = offset  # Versatz bei mehreren Verbindungen derselben Paarung
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setZValue(0)
        f = QFont(); f.setPixelSize(10)
        self.lbl_a = QGraphicsSimpleTextItem("", self); self.lbl_b = QGraphicsSimpleTextItem("", self)   # Remap-Info an beiden Enden
        for l in (self.lbl_a, self.lbl_b):
            l.setFont(f)
        self.update_path()

    def update_path(self) -> None:
        a, b = self.src.anchor(), self.dst.anchor()
        dx = (b.x() - a.x()) * 0.5
        oy = self.offset * 14  # Duplikate sichtbar auseinander
        p = QPainterPath(a)
        p.cubicTo(a.x() + dx, a.y() + oy, b.x() - dx, b.y() + oy, b.x(), b.y())
        self.setPath(p)
        txt = remap_text(self.route.rule)
        self.lbl_a.setText(txt); self.lbl_b.setText(txt)
        self.lbl_a.setPos(a.x() + 6, a.y() + oy * 0.5 - 14)
        self.lbl_b.setPos(b.x() - 6 - self.lbl_b.boundingRect().width(), b.y() + oy * 0.5 - 14)
        self._style()

    def _style(self) -> None:
        active = self.route.rule.enabled and self.src.present and self.dst.present
        col = style.route_color(self.route.out, self.route.in_) if active else style.MUTED
        pen = QPen(QColor(col), 3 if self.isSelected() else 2)
        if not self.route.rule.enabled:
            pen.setStyle(Qt.DashLine)
        self.setPen(pen)
        for l in (self.lbl_a, self.lbl_b):
            l.setBrush(QBrush(QColor(col)))

    def paint(self, painter, option, widget=None):
        self._style()
        option.state = option.state & ~QStyle.StateFlag.State_Selected  # keine Standard-Auswahlbox
        super().paint(painter, option, widget)

    def shape(self):
        from PySide6.QtGui import QPainterPathStroker
        s = QPainterPathStroker(); s.setWidth(12)
        return s.createStroke(self.path())


class NodeView(QGraphicsView):
    routes_changed = Signal()          # Routen geändert (neu/gelöscht/Regel)
    selection_changed = Signal(object)  # Route | None

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self); self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(style.BG)))
        self.setDragMode(QGraphicsView.NoDrag)
        self._ports: dict[tuple[str, str], PortItem] = {}  # (side, name) -> item
        self._links: list[LinkItem] = []
        self._routes: list[Route] = []
        self._drag_from: PortItem | None = None
        self._drag_line: QGraphicsPathItem | None = None
        self._rebuild_pending = False
        self._overlay = None
        self._last: dict[tuple[str, str], frozenset[int]] = {}
        self.scene().selectionChanged.connect(self._on_selection)
        self.horizontalScrollBar().valueChanged.connect(lambda _: self.place_overlay())
        self.verticalScrollBar().valueChanged.connect(lambda _: self.place_overlay())

    # ---- Overlay (Connection-Panel in der Mitte zwischen den Spalten) ----
    def update_last(self, last) -> None:
        """Alle seit Start gesehenen Channels je Port (Monitor.snapshot_last) in die Port-Kästen schreiben — nur bei Änderung (U2)."""
        new = {k: frozenset(v) for k, v in last.items()}
        if new == self._last:
            return
        changed = {k for k in set(new) | set(self._last) if new.get(k) != self._last.get(k)}
        self._last = new
        for key in changed:
            it = self._ports.get(key)
            if it:
                it.set_last(self._last.get(key))

    def set_overlay(self, w) -> None:
        self._overlay = w; w.setParent(self.viewport()); w.hide()

    def place_overlay(self) -> None:
        w = self._overlay
        if not w:
            return
        vp = self.viewport()
        cx = self.mapFromScene(QPointF(PORT_W + COL_GAP / 2, 0)).x()          # Spaltenmitte
        want = getattr(w, "body", w).sizeHint().height() + 48       # kompletter Inhalt, sonst Scrollbalken
        h = min(want, vp.height() - 16)
        w.resize(w.width(), max(h, 100))
        w.move(int(cx - w.width() / 2), max(8, (vp.height() - w.height()) // 2))
        w.raise_()

    def resizeEvent(self, e):
        super().resizeEvent(e); self.place_overlay()

    # ---- Daten ----
    def routes(self) -> list[Route]:
        return list(self._routes)

    def set_routes(self, routes: list[Route]) -> None:
        self._routes = list(routes)
        self.rebuild()

    def set_ports(self, outs: list[str], ins: list[str]) -> None:
        """Aktuell vorhandene Ports (rohe rtmidi-Namen). Fehlende, aber verwendete Ports bleiben grau."""
        po = {display_name(p) for p in outs}; pi = {display_name(p) for p in ins}
        if po == getattr(self, "_present_outs", None) and pi == getattr(self, "_present_ins", None):
            return  # nichts geändert -> Szene in Ruhe lassen
        self._present_outs, self._present_ins = po, pi
        if self._drag_from is None:
            self.rebuild()
        else:
            self._rebuild_pending = True

    def rebuild(self) -> None:
        sel = self.selected_route()
        sc = self.scene()
        self._ports.clear(); self._links.clear()
        sc.blockSignals(True); sc.clear(); sc.blockSignals(False)
        outs = sorted(getattr(self, "_present_outs", set()) | {r.out for r in self._routes}, key=str.casefold)  # R10
        ins = sorted(getattr(self, "_present_ins", set()) | {r.in_ for r in self._routes}, key=str.casefold)
        for i, n in enumerate(outs):
            it = PortItem(n, "out", n in getattr(self, "_present_outs", set()))
            it.setPos(0, i * (PORT_H + GAP)); sc.addItem(it); self._ports[("out", n)] = it
            it.set_last(self._last.get(("out", n)))
        for i, n in enumerate(ins):
            it = PortItem(n, "in", n in getattr(self, "_present_ins", set()))
            it.setPos(PORT_W + COL_GAP, i * (PORT_H + GAP)); sc.addItem(it); self._ports[("in", n)] = it
            it.set_last(self._last.get(("in", n)))
        seen: dict[tuple[str, str], int] = {}
        for r in self._routes:
            n = seen.get((r.out, r.in_), 0); seen[(r.out, r.in_)] = n + 1
            lk = LinkItem(r, self._ports[("out", r.out)], self._ports[("in", r.in_)], offset=n)
            sc.addItem(lk); self._links.append(lk)
            if r is sel:
                lk.setSelected(True)
        sc.setSceneRect(sc.itemsBoundingRect().adjusted(-20, -20, 20, 20))
        if sel is None:
            self.selection_changed.emit(None)
            if self._overlay:
                self._overlay.hide()

    def selected_route(self) -> Route | None:
        for lk in self._links:
            if lk.isSelected():
                return lk.route
        return None

    def _on_selection(self) -> None:
        r = self.selected_route()
        self.selection_changed.emit(r)
        if self._overlay:
            self._overlay.setVisible(r is not None); self.place_overlay()
        for lk in self._links:
            lk.update()

    # ---- Interaktion ----
    def _port_at(self, pos) -> PortItem | None:
        for it in self.items(pos):
            if isinstance(it, PortItem):
                return it
        return None

    def mousePressEvent(self, e):
        p = self._port_at(e.pos())
        if e.button() == Qt.LeftButton and p and p.side == "out":
            self._drag_from = p
            self._drag_line = QGraphicsPathItem()
            self._drag_line.setPen(QPen(QColor(style.ACCENT), 2, Qt.DashLine))
            self._drag_line.setZValue(2)
            self.scene().addItem(self._drag_line)
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_from:
            try:
                a = self._drag_from.anchor()
            except RuntimeError:  # Item während Drag gelöscht -> Drag abbrechen
                self._drag_from = self._drag_line = None
                return
            b = self.mapToScene(e.pos())
            dx = (b.x() - a.x()) * 0.5
            path = QPainterPath(a); path.cubicTo(a.x() + dx, a.y(), b.x() - dx, b.y(), b.x(), b.y())
            self._drag_line.setPath(path)
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._drag_from:
            target = self._port_at(e.pos())
            src = self._drag_from
            try:
                self.scene().removeItem(self._drag_line)
            except RuntimeError:
                pass
            self._drag_from = self._drag_line = None
            if target and target.side == "in":
                new = Route(src.name, target.name, Rule())   # Mehrfach-Patch derselben Paarung erlaubt
                self._routes.append(new)
                self._rebuild_pending = False
                self.rebuild()
                for lk in self._links:                       # neue Verbindung sofort zum Editieren auswählen
                    lk.setSelected(lk.route is new)
                self.routes_changed.emit()
            elif self._rebuild_pending:
                self._rebuild_pending = False
                self.rebuild()
            return
        super().mouseReleaseEvent(e)

    def delete_selected(self) -> None:
        sel = [lk.route for lk in self._links if lk.isSelected()]
        if sel:
            self._routes = [r for r in self._routes if not any(r is s for s in sel)]   # V1: Identität, nicht Gleichheit (Duplikate bleiben)
            self.rebuild()
            self.routes_changed.emit()

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace) and self.selected_route() is not None:
            self.delete_selected(); return
        super().keyPressEvent(e)
