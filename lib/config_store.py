"""
Simple JSON config store for the HX711 app.
Keeps pins, gain, scale/offset, sampling prefs, and calibration metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "dout": 5,
    "sck": 6,
    "gain": 128,
    "scale": 2280.0,
    "offset": 0.0,
    "samples": 8,
    "interval": 0.2,
    "known_weight": 1000.0,
    "calibration_time": None,
    "calibration_temp": None,
    "calibration_weight": None,
    "last_zero_raw": None,
}


def load_config() -> Dict[str, Any]:
    data = DEFAULT_CONFIG.copy()
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data.update(loaded)
        except Exception:
            # fall back to defaults on any error
            pass
    return data


def save_config(cfg: Dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)

