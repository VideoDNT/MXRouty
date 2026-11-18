"""Reine Funktionen: Channel-Filter, Channel-Remap, Typ-Filter. Kein State, kein Qt."""
from __future__ import annotations

from dataclasses import dataclass, field

# Message-Typen (Status-Nibble -> Name)
TYPES = {
    0x80: "note_off",
    0x90: "note_on",
    0xA0: "poly_aftertouch",
    0xB0: "cc",
    0xC0: "pc",
    0xD0: "aftertouch",
    0xE0: "pitch",
}
# System-Messages (Status-Byte -> Name); Rest von 0xF0.. = "system"
SYSTEM_TYPES = {0xF8: "clock", 0xFA: "start", 0xFB: "continue", 0xFC: "stop", 0xF0: "sysex"}
ALL_TYPES = set(TYPES.values()) | set(SYSTEM_TYPES.values()) | {"system"}
# Anzeige-Reihenfolge (Nutzer): note_on, note_off, clock, start, stop, danach alphabetisch
TYPE_ORDER = ["note_on", "note_off", "clock", "start", "stop"] + sorted(ALL_TYPES - {"note_on", "note_off", "clock", "start", "stop"})


@dataclass
class Rule:
    """Regel einer Matrix-Zelle (Out -> In)."""
    enabled: bool = True
    channels: set[int] = field(default_factory=set)      # 1–16, leer = alle
    remap: dict[int, set[int]] = field(default_factory=dict)  # {quelle: {ziele}}, 1–16; mehrere Ziele = Message vervielfachen
    types: set[str] = field(default_factory=set)              # leer = alle (siehe ALL_TYPES)
    remap_all: set[int] = field(default_factory=set)          # „*:n" — ALLE Channels zusätzlich -> {n, ...} (gilt auch für einzeln gemappte)

    def to_json(self) -> dict:
        return {
            "enabled": self.enabled,
            "channels": sorted(self.channels),
            "remap": {str(k): sorted(v) for k, v in self.remap.items() if v} | ({"*": sorted(self.remap_all)} if self.remap_all else {}),
            "types": sorted(self.types),
        }

    @classmethod
    def from_json(cls, d: dict) -> "Rule":
        return cls(
            enabled=bool(d.get("enabled", True)),
            channels={int(c) for c in d.get("channels", []) if 1 <= int(c) <= 16},
            remap={int(k): t for k, v in d.get("remap", {}).items() if k != "*" and str(k).isdigit() and 1 <= int(k) <= 16
                   for t in [_targets(v)] if t},
            types=set(d.get("types", [])),
            remap_all=_targets(d["remap"]["*"]) if "*" in d.get("remap", {}) else set(),
        )


def _targets(v) -> set[int]:
    """JSON-Wert int oder Liste -> Ziel-Set 1–16 (alte Presets mit Einzelwert bleiben lesbar; Ungültiges wird verworfen)."""
    vals = [v] if isinstance(v, int) else list(v)
    return {int(x) for x in vals if str(x).lstrip("-").isdigit() and 1 <= int(x) <= 16}


def remap_text(rule: "Rule") -> str:
    """„1:3,1:5,*:1" — gleiche Schreibweise wie das Remap-Feld; leer = kein Remap."""
    return ",".join([f"{a}:{b}" for a in sorted(rule.remap) for b in sorted(rule.remap[a])] + [f"*:{b}" for b in sorted(rule.remap_all)])


def msg_type(msg: list[int]) -> str:
    if msg[0] < 0xF0:
        return TYPES.get(msg[0] & 0xF0, "system")
    return SYSTEM_TYPES.get(msg[0], "system")


def msg_channel(msg: list[int]) -> int | None:
    """Channel 1–16, None bei System-Messages."""
    return (msg[0] & 0x0F) + 1 if msg[0] < 0xF0 else None


def apply_rule(msg: list[int], rule: Rule) -> list[list[int]]:
    """Gibt die umgepatchten Messages zurück (0 = verwerfen, >1 = vervielfacht auf mehrere Ziel-Channels)."""
    if not rule.enabled or not msg:
        return []
    t = msg_type(msg)
    if rule.types and t not in rule.types:
        return []
    ch = msg_channel(msg)
    if ch is None:
        return [list(msg)]  # System-Messages: kein Channel, kein Remap
    if rule.channels and ch not in rule.channels:
        return []
    targets = (rule.remap.get(ch, set()) | rule.remap_all) or {ch}  # * wirkt immer, zusätzlich zu Einzel-Remaps
    return [[(msg[0] & 0xF0) | (t - 1)] + list(msg[1:]) for t in sorted(targets)]
