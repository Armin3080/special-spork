"""Persistent application settings."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from flask import current_app

_lock = threading.Lock()

DEFAULTS: dict[str, Any] = {
    "language": "fa",
    "theme": "aurora",
    "default_quality": "best",
    "preferred_format": "mp4",
    "download_folder": "",
    "max_concurrent": 3,
    "max_filesize_mb": 2048,
    "auto_cleanup": False,
    "history_limit": 100,
}


def _path() -> Path:
    return Path(current_app.config["SETTINGS_FILE"])


def _read_unlocked() -> dict[str, Any]:
    path = _path()
    if not path.exists():
        return dict(DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        merged = dict(DEFAULTS)
        merged.update({k: v for k, v in data.items() if k in DEFAULTS})
        return merged
    except Exception:
        return dict(DEFAULTS)


def load_settings() -> dict[str, Any]:
    with _lock:
        return _read_unlocked()


def save_settings(updates: dict[str, Any]) -> dict[str, Any]:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        current = _read_unlocked()
        for k, v in updates.items():
            if k in DEFAULTS:
                current[k] = v
        path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        return current
