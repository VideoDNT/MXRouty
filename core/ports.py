"""Port-Scan, Öffnen/Schließen, Namens-Matching (GUI-frei).

Begriffe (Nutzersicht):
  Out = MIDI-Out eines Geräts  -> wir lesen davon (rtmidi.MidiIn)
  In  = MIDI-In eines Geräts   -> wir senden dorthin (rtmidi.MidiOut)
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

import rtmidi

log = logging.getLogger("mxrouty.ports")
CLIENT = "MXRouty"   # ALSA-Sequencer-Clientname (Linux: in aconnect/qjackctl sichtbar); WinMM ignoriert ihn

# L1 (Linux, 04.11.2026): pro Scan ein NEUER rtmidi-Client = neuer ALSA-Sequencer-Client -> nach kurzer Zeit
# "error creating ALSA sequencer client object", Hotplug tot. Deshalb EIN dauerhafter Scanner-Client je Richtung;
# schlägt ein Scan fehl, wird der Scanner einmal neu angelegt.
_scan_lock = threading.Lock()
_scan: dict[str, object] = {}


def _scan_ports(kind: str) -> list[str]:
    cls = rtmidi.MidiIn if kind == "in" else rtmidi.MidiOut
    with _scan_lock:
        try:
            if kind not in _scan:
                _scan[kind] = cls(name=CLIENT)
            return _scan[kind].get_ports()
        except Exception:
            _scan.pop(kind, None)           # Scanner kaputt -> einmal neu anlegen
            _scan[kind] = cls(name=CLIENT)
            return _scan[kind].get_ports()


@dataclass(frozen=True)
class PortMatch:
    index: int
    name: str
    exact: bool


def list_outs() -> list[str]:
    """Geräte-Outs = Quellen (rtmidi MidiIn-Ports)."""
    return _scan_ports("in")


def list_ins() -> list[str]:
    """Geräte-Ins = Ziele (rtmidi MidiOut-Ports)."""
    return _scan_ports("out")


def match_port(wanted: str, available: list[str], quiet: bool = False) -> PortMatch | None:
    """Exakter Treffer bevorzugt, sonst Substring (case-insensitive).
    Mehrfach-Treffer -> Log-Warnung, erster Treffer wird genommen. quiet: kein Log bei Nicht-Treffer (Hotplug-Polling)."""
    for i, name in enumerate(available):
        if name == wanted:
            return PortMatch(i, name, True)
    hits = [(i, n) for i, n in enumerate(available) if wanted.lower() in n.lower()]
    if not hits:
        if not quiet:
            log.warning("Port nicht gefunden: %r", wanted)
        return None
    if len(hits) > 1:
        log.warning("Mehrfach-Treffer für %r: %s — nehme %r", wanted, [n for _, n in hits], hits[0][1])
    i, name = hits[0]
    return PortMatch(i, name, False)


class SourcePort:
    """Geöffneter Geräte-Out (wir empfangen)."""

    def __init__(self, wanted: str):
        self.wanted = wanted
        self._midi = rtmidi.MidiIn(name=CLIENT)
        m = match_port(wanted, self._midi.get_ports())
        if m is None:
            raise LookupError(f"Out nicht gefunden: {wanted!r}")
        self.name = m.name
        self._midi.ignore_types(sysex=False, timing=False, active_sense=True)
        self._midi.open_port(m.index)

    def set_callback(self, cb) -> None:
        # cb(event, data) mit event = (message: list[int], delta_time: float)
        self._midi.set_callback(cb)

    def close(self) -> None:
        self._midi.cancel_callback()
        self._midi.close_port()


class DestPort:
    """Geöffneter Geräte-In (wir senden)."""

    def __init__(self, wanted: str):
        self.wanted = wanted
        self._midi = rtmidi.MidiOut(name=CLIENT)
        m = match_port(wanted, self._midi.get_ports())
        if m is None:
            raise LookupError(f"In nicht gefunden: {wanted!r}")
        self.name = m.name
        self._midi.open_port(m.index)

    def send(self, msg: list[int]) -> None:
        self._midi.send_message(msg)

    def close(self) -> None:
        self._midi.close_port()
