"""Grafische Channel-Map: links Quell-Channels („*" = alle, 1–16), rechts Ziel-Channels 1–16.
Linie von links nach rechts ziehen = Ziel hinzufügen (mehrere Ziele je Quelle erlaubt = Message vervielfachen).
Löschen NUR: Linie anklicken + Entf. Loslassen ohne Ziel = nichts passiert.
Spiegelt Rule.remap / Rule.remap_all; die Textzeile („1:3,*:1") bleibt parallel editierbar."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QGraphicsItem, QGraphicsLineItem, QGraphicsRectItem, QGraphicsScene, QGraphicsSimpleTextItem,
                               QGraphicsView, QStyle)

from . import style

ROW, W, GAP = 16, 30, 150   # Zeilenhöhe, Knopfbreite, Abstand der Spalten
ALL = 0                     # interner Schlüssel für „*"


class _Pin(QGraphicsRectItem):
    def __init__(self, key: int, side: str):
        super().__init__(0, 0, W, ROW - 3)
        self.key, self.side = key, side
        self.setBrush(QBrush(QColor(style.PANEL))); self.setPen(QPen(QColor(style.BORDER), 1))
        t = QGraphicsSimpleTextItem("*" if key == ALL else str(key), self)
        f = QFont(); f.setPixelSize(11); t.setFont(f); t.setBrush(QBrush(QColor(style.TEXT)))
        t.setPos((W - t.boundingRect().width()) / 2, 0)

    def anchor(self) -> QPointF:
        r = self.sceneBoundingRect()
        return QPointF(r.right() if self.side == "src" else r.left(), r.center().y())


class _Line(QGraphicsLineItem):
    def __init__(self, src: int, dst: int, a: QPointF, b: QPointF):
        super().__init__(a.x(), a.y(), b.x(), b.y())
        self.src, self.dst = src, dst
        self.setFlag(QGraphicsItem.ItemIsSelectable); self.setZValue(-1)

    def paint(self, painter, option, widget=None):
        self.setPen(QPen(QColor(style.ACCENT), 3 if self.isSelected() else 2))
        option.state = option.state & ~QStyle.StateFlag.State_Selected
        super().paint(painter, option, widget)

    def shape(self):
        from PySide6.QtGui import QPainterPathStroker
        s = QPainterPathStroker(); s.setWidth(8)
        return s.createStroke(super().shape())


class ChannelMap(QGraphicsView):
    changed = Signal()  # Mapping durch Ziehen geändert

    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self); self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor(style.BG)))
        self.setFrameShape(QGraphicsView.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.remap: dict[int, set[int]] = {}; self.remap_all: set[int] = set()
        self._src: dict[int, _Pin] = {}; self._dst: dict[int, _Pin] = {}
        self._lines: list[_Line] = []
        self._drag: _Pin | None = None; self._drag_line: QGraphicsLineItem | None = None
        for i, key in enumerate([ALL] + list(range(1, 17))):
            p = _Pin(key, "src"); p.setPos(0, i * ROW); self._scene.addItem(p); self._src[key] = p
        for i, key in enumerate(range(1, 17)):
            p = _Pin(key, "dst"); p.setPos(W + GAP, (i + 1) * ROW); self._scene.addItem(p); self._dst[key] = p
        self._scene.setSceneRect(QRectF(-2, -2, 2 * W + GAP + 4, 17 * ROW + 4))
        self.setFixedHeight(17 * ROW + 6); self.setFixedWidth(2 * W + GAP + 6)
        self._redraw()

    def set_mapping(self, remap: dict[int, set[int]], remap_all: set[int]) -> None:
        self.remap, self.remap_all = {k: set(v) for k, v in remap.items() if v}, set(remap_all)
        self._redraw()

    def _redraw(self) -> None:
        for l in self._lines:
            self._scene.removeItem(l)
        self._lines.clear()
        pairs = [(ALL, d) for d in sorted(self.remap_all)]
        pairs += [(k, d) for k, v in self.remap.items() for d in sorted(v) if 1 <= d <= 16]
        for s, d in pairs:
            l = _Line(s, d, self._src[s].anchor(), self._dst[d].anchor())
            self._scene.addItem(l); self._lines.append(l)

    def _pin_at(self, pos, side: str) -> _Pin | None:
        for it in self.items(pos):
            if isinstance(it, _Pin) and it.side == side:
                return it
        return None

    def mousePressEvent(self, e):
        p = self._pin_at(e.pos(), "src")
        if e.button() == Qt.LeftButton and p:
            self._drag = p
            self._drag_line = QGraphicsLineItem(); self._drag_line.setPen(QPen(QColor(style.ACCENT), 2, Qt.DashLine))
            self._scene.addItem(self._drag_line); return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag:
            a = self._drag.anchor(); b = self.mapToScene(e.pos())
            self._drag_line.setLine(a.x(), a.y(), b.x(), b.y()); return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self._drag:
            src = self._drag; dst = self._pin_at(e.pos(), "dst")
            self._scene.removeItem(self._drag_line); self._drag = self._drag_line = None
            if not dst:
                return  # kein Ziel -> keine Änderung (Löschen nur über Linie + Entf)
            if src.key == ALL:
                self.remap_all.add(dst.key)
            else:
                self.remap.setdefault(src.key, set()).add(dst.key)
            self._redraw(); self.changed.emit(); return
        super().mouseReleaseEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            sel = [l for l in self._lines if l.isSelected()]
            if sel:
                for l in sel:
                    if l.src == ALL:
                        self.remap_all.discard(l.dst)
                    else:
                        self.remap.get(l.src, set()).discard(l.dst)
                        if not self.remap.get(l.src):
                            self.remap.pop(l.src, None)
                self._redraw(); self.changed.emit(); return
        super().keyPressEvent(e)
