"""Persistent configuration (XDG). Stored as JSON so writing needs no extra deps."""
from __future__ import annotations

import json
import os
from pathlib import Path

APP = "zvstudio"

DEFAULT = {
    "brightness": 255,
    "fps": 20,
    "playlist": [
        {"applet": "clock", "config": {}, "duration": 10},
        {"applet": "sysmon", "config": {}, "duration": 10},
    ],
    "preempt": ["nowplaying"],
}


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = Path(base) / APP
    d.mkdir(parents=True, exist_ok=True)
    return d


def config_path() -> Path:
    return config_dir() / "config.json"


def load() -> dict:
    p = config_path()
    if not p.exists():
        return json.loads(json.dumps(DEFAULT))
    try:
        data = json.loads(p.read_text())
    except Exception:
        return json.loads(json.dumps(DEFAULT))
    merged = json.loads(json.dumps(DEFAULT))
    merged.update(data)
    return merged


def save(cfg: dict) -> None:
    config_path().write_text(json.dumps(cfg, indent=2))


def uploads_dir() -> Path:
    d = config_dir() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d
