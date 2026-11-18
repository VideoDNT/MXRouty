"""Routing-Engine: Out -> [(In, Rule)], rtmidi-Callback -> Regel -> senden.
Keine GUI-Calls im Callback. Beobachtung nur über optionalen on_event-Hook (Monitor, Stufe 4).
Hotplug: reconcile() gleicht gewünschte Ports mit den aktuell vorhandenen ab (Watcher-Thread, pollt)."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable

from .filters import Rule, apply_rule
from .ports import DestPort, SourcePort, list_ins, list_outs, match_port

log = logging.getLogger("mxrouty.router")


@dataclass
class Route:
    out: str   # Quelle (Geräte-Out), gewünschter Name
    in_: str   # Ziel (Geräte-In), gewünschter Name
    rule: Rule


# on_event(out_name, in_name | None, msg_raw, msg_sent | None)
EventHook = Callable[[str, str | None, list[int], list[int] | None], None]


class Router:
    def __init__(self, on_event: EventHook | None = None):
        self._sources: dict[str, SourcePort] = {}
        self._dests: dict[str, DestPort] = {}
        self._table: dict[str, list[tuple[str, Rule]]] = {}  # out -> [(in, rule)]
        self._lock = threading.Lock()
        self.on_event = on_event
        self._watch_thread: threading.Thread | None = None
        self._watch_stop = threading.Event()

    # ---- Aufbau ----
    def set_routes(self, routes: list[Route]) -> None:
        """Ersetzt alle Routen; öffnet/schließt Ports nach Bedarf."""
        table: dict[str, list[tuple[str, Rule]]] = {}
        for r in routes:
            table.setdefault(r.out, []).append((r.in_, r.rule))
        with self._lock:
            self._table = table
        self.reconcile()

    def close(self) -> None:
        self.stop_watch()
        with self._lock:
            for s in self._sources.values():
                self._safe_close(s)
            for d in self._dests.values():
                self._safe_close(d)
            self._sources.clear()
            self._dests.clear()
            self._table.clear()

    # ---- Hotplug ----
    def reconcile(self) -> None:
        """Gewünschte Ports mit vorhandenen abgleichen: verschwundene schließen, (wieder) vorhandene öffnen.
        Wird von set_routes() und vom Watcher aufgerufen."""
        try:
            outs_now = list_outs()      # L1: dauerhafte Scanner-Clients statt neuer rtmidi-Objekte je Poll
            ins_now = list_ins()
        except Exception as e:
            log.error("Port-Scan: %s", e)
            return
        with self._lock:
            wanted_outs = set(self._table)
            wanted_ins = {i for lst in self._table.values() for i, _ in lst}

            # nicht mehr gewünscht oder verschwunden -> schließen
            for name, src in list(self._sources.items()):
                if name not in wanted_outs or src.name not in outs_now:
                    self._safe_close(self._sources.pop(name))
                    if name in wanted_outs:
                        log.warning("Out weg: %r", name)
            for name, dst in list(self._dests.items()):
                if name not in wanted_ins or dst.name not in ins_now:
                    self._safe_close(self._dests.pop(name))
                    if name in wanted_ins:
                        log.warning("In weg: %r", name)

            # gewünscht und noch nicht offen -> öffnen (still, wenn Gerät fehlt)
            for name in wanted_ins - set(self._dests):
                if match_port(name, ins_now, quiet=True) is None:
                    continue  # Gerät fehlt -> still warten
                try:
                    self._dests[name] = DestPort(name)
                    log.info("In offen: %r -> %r", name, self._dests[name].name)
                except Exception:
                    pass
            for name in wanted_outs - set(self._sources):
                if match_port(name, outs_now, quiet=True) is None:
                    continue
                try:
                    src = SourcePort(name)
                    src.set_callback(self._make_callback(name))
                    self._sources[name] = src
                    log.info("Out offen: %r -> %r", name, src.name)
                except Exception:
                    pass

    def start_watch(self, interval: float = 1.0) -> None:
        """Hotplug-Watcher: pollt Portliste alle `interval` Sekunden."""
        if self._watch_thread:
            return
        self._watch_stop.clear()

        def loop():
            while not self._watch_stop.wait(interval):
                self.reconcile()

        self._watch_thread = threading.Thread(target=loop, name="mxrouty-watch", daemon=True)
        self._watch_thread.start()

    def stop_watch(self) -> None:
        if self._watch_thread:
            self._watch_stop.set()
            self._watch_thread.join(timeout=3)
            self._watch_thread = None

    @staticmethod
    def _safe_close(port) -> None:
        try:
            port.close()
        except Exception as e:  # Gerät schon weg -> Treiber kann meckern
            log.debug("close %r: %s", getattr(port, "name", port), e)

    # ---- Status ----
    def routes(self) -> list[Route]:
        """Aktuelle Routen (Kopie der Tabelle) — für GUI-Start."""
        with self._lock:
            return [Route(o, i, r) for o, lst in self._table.items() for i, r in lst]

    def status(self) -> dict[str, bool]:
        """Port-Name -> offen? (für Tray grün/rot)"""
        with self._lock:
            wanted = set(self._table) | {i for lst in self._table.values() for i, _ in lst}
            opened = set(self._sources) | set(self._dests)
            return {n: n in opened for n in wanted}

    # ---- Callback (MIDI-Thread) ----
    def _make_callback(self, out_name: str):
        def cb(event, _data=None):
            msg, _dt = event
            targets = self._table.get(out_name, ())
            sent_any = False
            for in_name, rule in targets:
                dest = self._dests.get(in_name)
                if dest is None:
                    continue
                for out_msg in apply_rule(msg, rule):  # 0..n Messages (Mehrfach-Ziel)
                    try:
                        dest.send(out_msg)
                    except Exception as e:
                        log.error("Senden an %r: %s — Port wird neu geöffnet", in_name, e)
                        with self._lock:                 # V4: unter Lock entfernen UND schließen; Watcher öffnet neu
                            d = self._dests.pop(in_name, None)
                        if d is not None:
                            self._safe_close(d)
                        break
                    sent_any = True
                    if self.on_event:
                        self.on_event(out_name, in_name, msg, out_msg)
            if not sent_any and self.on_event:
                self.on_event(out_name, None, msg, None)
        return cb
