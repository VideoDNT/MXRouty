"""Monitor: nimmt Router-Events (MIDI-Thread) entgegen, Ringpuffer + Queue für die GUI. Kein Qt."""
from __future__ import annotations

import collections
import queue
import threading
import time
from dataclasses import dataclass

from .filters import msg_channel, msg_type


@dataclass(frozen=True)
class Event:
    ts: float                 # time.time()
    out: str                  # Quelle (Geräte-Out)
    in_: str | None           # Ziel (Geräte-In), None = verworfen
    raw: tuple[int, ...]      # Eingang roh
    sent: tuple[int, ...] | None  # Ausgang nach Remap, None = verworfen

    @property
    def type(self) -> str:
        return msg_type(list(self.raw))

    @property
    def channel(self) -> int | None:
        return msg_channel(list(self.raw))

    @property
    def channel_out(self) -> int | None:
        return msg_channel(list(self.sent)) if self.sent else None


class Monitor:
    """on_event() ist der Router-Hook. GUI zieht per drain() aus der Queue, history() liefert den Ringpuffer."""

    def __init__(self, maxlen: int = 5000):
        self._ring: collections.deque[Event] = collections.deque(maxlen=maxlen)
        self._queue: queue.Queue[Event] = queue.Queue()
        self._lock = threading.Lock()
        self.enabled = True
        self.last_channel: dict[tuple[str, str], set[int]] = {}   # ("out"|"in", Portname) -> alle seit Start gesehenen/gesendeten Channels

    # Router-Hook (MIDI-Thread)
    def on_event(self, out: str, in_: str | None, raw: list[int], sent: list[int] | None) -> None:
        if not self.enabled:
            return
        ev = Event(time.time(), out, in_, tuple(raw), tuple(sent) if sent else None)
        ch_in = msg_channel(list(raw))
        with self._lock:
            if ch_in is not None:   # U1: unter Lock, GUI liest per snapshot_last()
                self.last_channel.setdefault(("out", out), set()).add(ch_in)
                if in_ and sent:
                    self.last_channel.setdefault(("in", in_), set()).add(msg_channel(list(sent)))
            self._ring.append(ev)
        self._queue.put(ev)

    def snapshot_last(self) -> dict[tuple[str, str], frozenset[int]]:
        """Thread-sichere Kopie der Channel-Listen (GUI-Timer)."""
        with self._lock:
            return {k: frozenset(v) for k, v in self.last_channel.items()}

    def reset_last(self) -> None:
        """Reset-Dialog: Channel-Listen leeren."""
        with self._lock:
            self.last_channel.clear()

    # GUI-Seite
    def drain(self, limit: int = 500) -> list[Event]:
        """Alle seit dem letzten Aufruf neuen Events (max. limit)."""
        out: list[Event] = []
        try:
            while len(out) < limit:
                out.append(self._queue.get_nowait())
        except queue.Empty:
            pass
        return out

    def history(self) -> list[Event]:
        with self._lock:
            return list(self._ring)

    def clear(self) -> None:
        with self._lock:
            self._ring.clear()
        self.drain(10**9)


def match(ev: Event, port: str | None = None, types: set[str] | None = None, channels: set[int] | None = None) -> bool:
    """Filter für Monitor-Anzeige: Port (Out oder In, Substring), Typen (leer/None = alle), Channels (Eingang; leer/None = alle)."""
    if port and port.lower() not in ev.out.lower() and not (ev.in_ and port.lower() in ev.in_.lower()):
        return False
    if types and ev.type not in types:
        return False
    if channels and ev.channel not in channels:
        return False
    return True
