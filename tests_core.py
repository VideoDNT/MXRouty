"""Tests ohne Hardware: Filter/Remap, Monitor, Preset. Aufruf über start.bat nicht nötig — reiner Entwicklertest"""
import json, tempfile
from pathlib import Path
from core.filters import Rule, apply_rule, msg_channel, msg_type
from core.monitor import Monitor, match
from core import preset
from core.router import Route

# filters
assert msg_type([0x90, 60, 100]) == "note_on" and msg_channel([0x90, 60, 100]) == 1
assert msg_type([0xF8]) == "clock" and msg_type([0xFA]) == "start" and msg_type([0xFC]) == "stop" and msg_type([0xF0, 0x7E, 0xF7]) == "sysex" and msg_type([0xF1, 0]) == "system" and msg_channel([0xF8]) is None
from core.filters import TYPE_ORDER; assert TYPE_ORDER[:5] == ["note_on", "note_off", "clock", "start", "stop"] and TYPE_ORDER[5:] == sorted(TYPE_ORDER[5:])
assert apply_rule([0x91, 60, 100], Rule()) == [[0x91, 60, 100]]
assert apply_rule([0x91, 60, 100], Rule(channels={1})) == []
assert apply_rule([0x91, 60, 100], Rule(channels={2})) == [[0x91, 60, 100]]
assert apply_rule([0x91, 60, 100], Rule(remap={2: {5}})) == [[0x94, 60, 100]]
assert apply_rule([0xB0, 7, 1], Rule(types={"note_on"})) == []
assert apply_rule([0xF8], Rule(channels={3})) == [[0xF8]]
assert apply_rule([0x90, 1, 1], Rule(enabled=False)) == []
assert Rule.from_json(Rule(channels={1,2}, remap={1:{3}}, types={"cc"}).to_json()) == Rule(channels={1,2}, remap={1:{3}}, types={"cc"})
assert Rule.from_json({"remap": {"1": 5, "*": 2}}) == Rule(remap={1:{5}}, remap_all={2})  # altes Einzelwert-Format
assert apply_rule([0x93, 1, 1], Rule(remap_all={1})) == [[0x90, 1, 1]]          # *:1
assert apply_rule([0x91, 1, 1], Rule(remap={2: {5}}, remap_all={1})) == [[0x90, 1, 1], [0x94, 1, 1]]  # * zusätzlich zu Einzel-Remap
assert apply_rule([0x90, 1, 1], Rule(remap={2: {5}}, remap_all={3})) == [[0x92, 1, 1]]  # ch1 nicht einzeln -> *:3
assert apply_rule([0x90, 1, 1], Rule(remap={1: {3, 5}})) == [[0x92, 1, 1], [0x94, 1, 1]]  # Mehrfach-Ziel = vervielfacht
rj = Rule(remap={1: {3, 5}}, remap_all={9}).to_json(); assert rj["remap"] == {"1": [3, 5], "*": [9]} and Rule.from_json(rj) == Rule(remap={1: {3, 5}}, remap_all={9})
assert Rule.from_json({"remap": {"1": [0, 3, 17], "*": [20], "9": 99, "x": 1}, "channels": [0, 2, 17]}) == Rule(channels={2}, remap={1: {3}})  # S2
print("filters OK")

# monitor
m = Monitor(maxlen=3)
m.on_event("A", "B", [0x90, 1, 2], [0x94, 1, 2])
m.on_event("A", None, [0xB0, 7, 1], None)
evs = m.drain()
assert len(evs) == 2 and evs[0].channel == 1 and evs[0].channel_out == 5 and evs[1].sent is None
assert evs[1].sent is None and evs[0].in_ == "B"  # line() entfernt (S7)
assert match(evs[0], port="b") and not match(evs[0], types={"cc"}) and match(evs[1], types={"cc", "note_on"}, channels={1, 3}) and not match(evs[1], channels={2})
for i in range(5): m.on_event("A", "B", [0x90, i, 0], [0x90, i, 0])
assert len(m.history()) == 3 and m.drain() and not m.drain()
print("monitor OK")

# preset
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "t.json"
    routes = [Route("Out X", "In Y", Rule(channels={1}, remap={1: {5}}))]
    preset.save(p, routes)
    back = preset.load(p)
    assert back[0].out == "Out X" and back[0].in_ == "In Y" and back[0].rule == routes[0].rule
    assert json.loads(p.read_text("utf-8"))["routes"][0]["rule"]["remap"] == {"1": [5]}
print("preset OK")
