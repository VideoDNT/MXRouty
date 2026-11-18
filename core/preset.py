"""Presets: JSON laden/speichern, zuletzt genutztes Preset merken (Autoload). Kein Qt."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from .filters import Rule
from .router import Route

ROOT = Path(__file__).resolve().parents[1]


def _data_dir() -> Path:
    """Gepackt (MXRouty.exe): Program Files ist schreibgeschützt -> %APPDATA%\\MXRouty bzw. ~/.config/mxrouty.
    Aus dem Quellordner (start.bat/start.sh): alles bleibt lokal im Projektordner (Regel 29.10.2026)."""
    if getattr(sys, "frozen", False):
        if sys.platform.startswith("win"):
            return Path(os.environ.get("APPDATA", Path.home())) / "MXRouty"
        return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "mxrouty"
    return ROOT


DATA_DIR = _data_dir()
PRESET_DIR = DATA_DIR / "presets"
SETTINGS = DATA_DIR / "settings.json"


def load(path: Path) -> list[Route]:
    data = json.loads(Path(path).read_text("utf-8"))
    return [Route(r["out"], r["in"], Rule.from_json(r.get("rule", {}))) for r in data.get("routes", [])]


def save(path: Path, routes: list[Route]) -> None:
    data = {"routes": [{"out": r.out, "in": r.in_, "rule": r.rule.to_json()} for r in routes]}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")


def _natural(p: Path):
    import re
    return [int(t) if t.isdigit() else t.casefold() for t in re.split(r"(\d+)", p.stem.strip())]


def list_presets() -> list[Path]:
    """Alphabetisch (Groß/Klein egal, Zahlen natürlich: 2 vor 10)."""
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(PRESET_DIR.glob("*.json"), key=_natural)


def path_for(name: str) -> Path:
    """Preset-Name -> Datei im Programmordner (presets/<name>.json).
    T6: existiert schon eine Datei, die sich nur in Groß/Klein unterscheidet, wird DIESE genommen (Windows-FS ist case-insensitiv)."""
    safe = "".join(c for c in name.strip() if c not in '\\/:*?"<>|')
    for p in list_presets():
        if p.stem.casefold() == safe.casefold():
            return p
    return PRESET_DIR / f"{safe}.json"


def delete(path: Path) -> None:
    Path(path).unlink(missing_ok=True)
    if _settings().get("last_preset") == str(Path(path).resolve()):
        s = _settings(); s.pop("last_preset", None); _write_settings(s)


def export_to(src: Path, dst: Path) -> None:
    """Sicherung / Übertragung: Kopie der Preset-Datei an beliebigen Ort."""
    Path(dst).write_bytes(Path(src).read_bytes())


def import_from(src: Path) -> Path:
    """Fremde Preset-Datei in den Programmordner übernehmen (validiert durch load); gibt neuen Pfad zurück."""
    routes = load(Path(src))
    dst = path_for(Path(src).stem)
    n = 2
    while dst.exists():
        dst = path_for(f"{Path(src).stem} ({n})"); n += 1
    save(dst, routes)
    return dst


def _settings() -> dict:
    try:
        return json.loads(SETTINGS.read_text("utf-8"))
    except Exception:
        return {}


def get_setting(key: str, default=None):
    return _settings().get(key, default)


def _write_settings(s: dict) -> None:
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(s, indent=2), "utf-8")


def set_setting(key: str, value) -> None:
    s = _settings(); s[key] = value
    _write_settings(s)


def last_preset() -> Path | None:
    p = _settings().get("last_preset")
    return Path(p) if p and Path(p).exists() else None


def remember(path: Path) -> None:
    s = _settings()
    s["last_preset"] = str(Path(path).resolve())
    _write_settings(s)


def autoload() -> tuple[Path | None, list[Route]]:
    """Zuletzt genutztes Preset, sonst presets/current.json, sonst leer."""
    p = last_preset() or (PRESET_DIR / "current.json" if (PRESET_DIR / "current.json").exists() else None)
    return (p, load(p)) if p else (None, [])
