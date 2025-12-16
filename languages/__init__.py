from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

# Fallback English strings to ensure the app stays functional if JSON files are missing.
DEFAULT_EN = {
    "title": "HX711 Load Cell",
    "grams": "Grams",
    "raw": "Raw",
    "status_idle": "Idle",
    "status_reading": "Reading…",
    "status_tared": "Tared",
    "status_calibrating_clear": "Calibrating: remove all weight, taring…",
    "status_calibration_done": "Calibration done",
    "status_calibration_cancelled": "Calibration cancelled",
    "status_power_down": "Powered down",
    "status_power_up": "Powered up",
    "status_error": "Error: {err}",
    "btn_start": "Start",
    "btn_stop": "Stop",
    "btn_tare": "Tare",
    "btn_settings": "Settings",
    "btn_apply_start": "Apply & Start",
    "btn_calibrate": "Calibrate with weight",
    "btn_power_down": "Power Down",
    "btn_power_up": "Power Up",
    "btn_quit": "Quit",
    "btn_back": "Back",
    "label_settings": "Settings",
    "label_dout": "DOUT pin",
    "label_sck": "SCK pin",
    "label_gain": "Gain (32/64/128)",
    "label_scale": "Scale",
    "label_offset": "Offset",
    "label_samples": "Samples",
    "label_interval": "Interval (s)",
    "label_known_weight": "Known weight (g)",
    "label_language": "Language / Språk",
    "invalid_input": "Check numeric fields.",
    "invalid_weight": "Known weight must be greater than zero.",
    "cal_prompt_place_weight": "Place the known weight on the scale, then tap OK.",
    "cal_title": "Calibration",
    "info_start_first": "Start the reader first.",
    "hx_error": "HX711 error",
    "hx_init_failed": "HX711 init failed",
}


def load_languages() -> Dict[str, Dict[str, str]]:
    """
    Load all *.json language files from this directory.
    Returns a mapping of language code -> strings.
    Falls back to English defaults if nothing is found.
    """
    base = Path(__file__).resolve().parent
    langs: Dict[str, Dict[str, str]] = {}
    for path in base.glob("*.json"):
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                langs[path.stem] = data
        except Exception:
            continue
    if "en" not in langs:
        langs["en"] = DEFAULT_EN
    return langs


__all__ = ["load_languages"]
