"""
Qt Quick (PySide6) UI for the HX711 scale.

- macOS-flavored styling (QT_QUICK_CONTROLS_STYLE=macOS by default)
- Modern layout with a clean primary panel and a right-side settings drawer
- Optional demo mode to exercise the UI without HX711 hardware
"""

from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6 import QtCore, QtGui, QtQml, QtWidgets

from lib.config_store import load_config, save_config
from lib.hx711_device import HX711, HX711ReaderThread, Reading
from languages import load_languages


class HX711Controller(QtCore.QObject):
    """
    Bridges HX711 hardware to QML.
    Exposes properties for reading, status, calibration state, and config.
    """

    readingChanged = QtCore.Signal()
    readingStateChanged = QtCore.Signal()
    statusChanged = QtCore.Signal()
    calStatusChanged = QtCore.Signal()
    configChanged = QtCore.Signal()
    errorOccurred = QtCore.Signal(str)
    languagesChanged = QtCore.Signal()
    languageChanged = QtCore.Signal()

    def __init__(self, demo: bool = False):
        super().__init__()
        self.demo = demo
        self._config: Dict[str, Any] = load_config()
        self._reading: Dict[str, Any] = {
            "grams": None,
            "newtons": None,
            "raw": None,
            "hz": None,
            "timestamp": None,
        }
        self._status: str = "Idle"
        self._cal_status: Dict[str, Any] = {"level": "bad", "text": "Calibration required"}
        self._is_reading: bool = False
        self._languages = sorted(list(load_languages().keys()))
        self.languagesChanged.emit()
        self._lang_code = self._config.get("language", "en")
        self._lang_map = load_languages()

        self.hx: Optional[HX711] = None
        self.reader: Optional[HX711ReaderThread] = None
        self._demo_timer: Optional[QtCore.QTimer] = None

        self._eval_cal_status(initial=True)
        self.statusChanged.emit()
        self.calStatusChanged.emit()

    # --- Qt properties exposed to QML -------------------------------------------------
    @QtCore.Property("QVariantMap", notify=readingChanged)
    def reading(self) -> Dict[str, Any]:
        return self._reading

    @QtCore.Property(bool, notify=readingStateChanged)
    def isReading(self) -> bool:
        return self._is_reading

    @QtCore.Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status

    @QtCore.Property("QVariantMap", notify=calStatusChanged)
    def calStatus(self) -> Dict[str, Any]:
        return self._cal_status

    @QtCore.Property("QVariantMap", notify=configChanged)
    def config(self) -> Dict[str, Any]:
        return self._config

    @QtCore.Property("QStringList", notify=languagesChanged)
    def languagesList(self):
        return self._languages

    @QtCore.Property(str, notify=languageChanged)
    def language(self) -> str:
        return self._lang_code

    # --- Slots callable from QML ------------------------------------------------------
    @QtCore.Slot("QVariantMap")
    def applyAndStart(self, cfg: Dict[str, Any]):
        """Apply settings and begin reading."""
        try:
            parsed = self._parse_config(cfg)
        except ValueError as exc:
            self._set_status(f"Check settings: {exc}")
            self.errorOccurred.emit(str(exc))
            return
        self._start_reader(parsed)

    @QtCore.Slot("QVariantMap")
    def updateConfig(self, cfg: Dict[str, Any]):
        """Update config without starting the reader."""
        try:
            parsed = self._parse_config(cfg)
        except ValueError as exc:
            self._set_status(f"Check settings: {exc}")
            self.errorOccurred.emit(str(exc))
            return
        self._config.update(parsed)
        save_config(self._config)
        self.configChanged.emit()
        self._eval_cal_status()

    @QtCore.Slot()
    def stop(self):
        """Stop reading and release hardware."""
        if self.reader:
            self.reader.stop()
        self.reader = None
        if self.hx:
            try:
                self.hx.close()
            except Exception:
                pass
        self.hx = None
        if self._demo_timer:
            self._demo_timer.stop()
            self._demo_timer = None
        self._set_reading_state(False)
        self._set_status("Stopped")

    @QtCore.Slot()
    def tare(self):
        """Session-only tare offset."""
        if self.demo:
            self._set_status("Demo tare applied")
            return
        if not self.hx:
            self._set_status("Start the reader first")
            return
        try:
            samples = max(3, int(self._config.get("samples", 8)))
            tare_raw = self.hx.read_average(samples)
            tare_offset = abs(tare_raw - self.hx.get_offset())
            self.hx.set_tare_offset(tare_offset)
            self._set_status("Tared")
        except Exception as exc:
            self._set_status(f"Tare failed: {exc}")
            self.errorOccurred.emit(str(exc))

    @QtCore.Slot()
    def calibrate(self):
        """
        Simplified calibration:
        - Uses current known_weight, samples, and gain/pins from config
        - Assumes the known weight is already placed on the scale
        """
        self._calibrate_internal(weight_override=None)

    @QtCore.Slot(float)
    def calibrateWithWeight(self, weight: float):
        """Calibration entrypoint with an explicit known weight from the UI."""
        self._calibrate_internal(weight_override=weight)

    def _calibrate_internal(self, weight_override: Optional[float]):
        cfg = self._config
        try:
            samples = max(3, int(cfg.get("samples", 8)))
            known_weight = float(weight_override) if weight_override is not None else float(cfg.get("known_weight", 0))
            if known_weight <= 0:
                raise ValueError("Known weight must be greater than zero.")
        except Exception as exc:
            self._set_status(f"Calibration blocked: {exc}")
            self.errorOccurred.emit(str(exc))
            return

        was_reading = self.reader is not None or self._demo_timer is not None
        if was_reading:
            self.stop()

        if self.demo:
            # In demo mode, pretend calibration succeeded.
            self._config["scale"] = max(1.0, known_weight / max(known_weight, 1e-3))
            self._config["offset"] = 0.0
            self._config["last_zero_raw"] = 0.0
            self._config["calibration_time"] = time.time()
            save_config(self._config)
            self.configChanged.emit()
            self._set_cal_status("good", "Demo calibration saved")
            if was_reading:
                self._start_reader(self._config)
            return

        try:
            hx = self.hx or HX711(dout=int(cfg["dout"]), pd_sck=int(cfg["sck"]), gain=int(cfg["gain"]))
        except Exception as exc:
            self._set_status(f"HX711 init failed: {exc}")
            self.errorOccurred.emit(str(exc))
            return

        self.hx = hx
        try:
            self._set_status("Calibrating… zeroing")
            offset = hx.read_average(samples)
            hx.set_offset(offset)
            hx.clear_tare()
            measured = hx.read_average(samples) - hx.get_offset()
            measured = abs(measured)
            if measured <= 0 or not math.isfinite(measured):
                raise ValueError("Measured weight too small.")
            scale = measured / known_weight
            if scale <= 0 or not math.isfinite(scale):
                raise ValueError("Computed scale invalid.")
            hx.set_scale(scale)
            self._config.update(
                {
                    "scale": scale,
                    "offset": offset,
                    "known_weight": known_weight,
                    "calibration_time": time.time(),
                    "calibration_weight": known_weight,
                    "last_zero_raw": offset,
                }
            )
            save_config(self._config)
            self.configChanged.emit()
            self._set_cal_status("good", "Calibration OK")
            self._set_status("Calibration done")
        except Exception as exc:
            self._set_status(f"Calibration failed: {exc}")
            self.errorOccurred.emit(str(exc))
            return

        if was_reading:
            self._start_reader(self._config)

    @QtCore.Slot(str, result=str)
    @QtCore.Slot(str, str, result=str)
    def tr(self, key: str, fallback: str = "") -> str:
        if not key:
            return fallback
        lang = self._lang_code or "en"
        lang_map = self._lang_map.get(lang, {})
        if key in lang_map:
            return lang_map.get(key, fallback or key)
        return self._lang_map.get("en", {}).get(key, fallback or key)

    @QtCore.Slot(str)
    def setLanguage(self, lang: str):
        if not lang:
            return
        if lang not in self._lang_map:
            return
        self._lang_code = lang
        self._config["language"] = lang
        save_config(self._config)
        self.languageChanged.emit()
        self.configChanged.emit()
        self.languagesChanged.emit()
    @QtCore.Slot()
    def refreshCalibrationStatus(self):
        self._eval_cal_status()

    # --- Internal helpers -------------------------------------------------------------
    def _parse_config(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        try:
            dout = int(cfg.get("dout", self._config.get("dout", 5)))
            sck = int(cfg.get("sck", self._config.get("sck", 6)))
            gain = int(cfg.get("gain", self._config.get("gain", 128)))
            scale = float(cfg.get("scale", self._config.get("scale", 2280.0)))
            offset = float(cfg.get("offset", self._config.get("offset", 0.0)))
            samples = max(1, int(cfg.get("samples", self._config.get("samples", 8))))
            interval = max(0.05, float(cfg.get("interval", self._config.get("interval", 0.2))))
            known_weight = float(cfg.get("known_weight", self._config.get("known_weight", 1000.0)))
            decimals = max(0, int(cfg.get("decimals", self._config.get("decimals", 2))))
            rolling_window = bool(cfg.get("rolling_window", self._config.get("rolling_window", False)))
            fullscreen = bool(cfg.get("fullscreen", self._config.get("fullscreen", False)))
        except Exception as exc:
            raise ValueError("numeric fields") from exc
        return {
            "dout": dout,
            "sck": sck,
            "gain": gain,
            "scale": scale,
            "offset": offset,
            "samples": samples,
            "interval": interval,
            "known_weight": known_weight,
            "decimals": decimals,
            "rolling_window": rolling_window,
            "fullscreen": fullscreen,
        }

    def _start_reader(self, cfg: Dict[str, Any]):
        self.stop()
        self._config.update(cfg)
        save_config(self._config)
        self.configChanged.emit()

        if self.demo:
            self._start_demo(cfg)
            self._eval_cal_status()
            return

        try:
            hx = HX711(dout=cfg["dout"], pd_sck=cfg["sck"], gain=cfg["gain"])
        except Exception as exc:
            self._set_status(f"HX711 init failed: {exc}")
            self.errorOccurred.emit(str(exc))
            return

        hx.set_scale(cfg["scale"])
        hx.set_offset(cfg["offset"])
        hx.clear_tare()
        self.hx = hx
        self.reader = HX711ReaderThread(
            hx=self.hx,
            samples=cfg["samples"],
            interval=cfg["interval"],
            callback=self._on_reading,
            error_callback=self._on_error,
            rolling_window=cfg["rolling_window"],
        )
        self.reader.start()
        self._set_status("Reading…")
        self._set_reading_state(True)
        self._eval_cal_status()

    def _start_demo(self, cfg: Dict[str, Any]):
        timer = QtCore.QTimer(self)
        timer.setInterval(int(max(cfg["interval"], 0.1) * 1000))
        baseline = cfg.get("known_weight", 500.0)
        swing = max(40.0, baseline * 0.08)

        def tick():
            t = time.time()
            grams = baseline + swing * math.sin(t / 1.6)
            hz = 1.0 / cfg["interval"] if cfg["interval"] else None
            self._reading = {
                "grams": grams,
                "newtons": (grams / 1000.0) * 9.80665,
                "raw": int(grams * 10),
                "hz": hz,
                "timestamp": t,
            }
            self.readingChanged.emit()
            self._set_status(time.strftime("%H:%M:%S", time.localtime(t)))

        timer.timeout.connect(tick)
        timer.start()
        self._demo_timer = timer
        self._set_status("Demo mode: simulated data")
        self._set_reading_state(True)

    def _on_reading(self, reading: Reading):
        try:
            hz = 1.0 / reading.period_sec if reading.period_sec else None
        except Exception:
            hz = None
        grams = reading.grams
        newtons = (grams / 1000.0) * 9.80665 if grams is not None else None
        self._reading = {
            "grams": grams,
            "newtons": newtons,
            "raw": reading.raw,
            "hz": hz,
            "timestamp": reading.timestamp,
        }
        self.readingChanged.emit()
        self._set_status(time.strftime("%H:%M:%S", time.localtime(reading.timestamp)))

    def _on_error(self, exc: Exception):
        msg = f"HX711 error: {exc}"
        self._set_status(msg)
        self.errorOccurred.emit(str(exc))
        self._set_reading_state(False)

    def _eval_cal_status(self, initial: bool = False):
        cfg = self._config
        cal_time = cfg.get("calibration_time")
        scale = cfg.get("scale")
        offset = cfg.get("offset")
        if cal_time is None or scale is None or offset is None:
            self._set_cal_status("bad", "Calibration required")
            if not initial:
                self._set_status("Calibration required")
            return

        age_days = (time.time() - cal_time) / 86400 if cal_time else None
        if age_days and age_days > 7:
            self._set_cal_status("warn", "Calibration may be stale")
            if not initial:
                self._set_status("Calibration may be stale")
        else:
            self._set_cal_status("good", "Calibration OK")
            if not initial:
                self._set_status("Calibration OK")

    def _set_status(self, text: str):
        self._status = text
        self.statusChanged.emit()

    def _set_cal_status(self, level: str, text: str):
        self._cal_status = {"level": level, "text": text}
        self.calStatusChanged.emit()

    def _set_reading_state(self, val: bool):
        if self._is_reading == val:
            return
        self._is_reading = val
        self.readingStateChanged.emit()


def run_qt_app(demo: bool = False) -> int:
    """
    Launch the Qt Quick UI.

    Args:
        demo: when True, runs without HX711 hardware using simulated data.
    """
    # Use a widely available style to avoid missing platform plugins (e.g., macOS style on Windows).
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Fusion")

    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QtWidgets.QApplication([])
    controller = HX711Controller(demo=demo)

    engine = QtQml.QQmlApplicationEngine()
    engine.rootContext().setContextProperty("controller", controller)

    qml_path = Path(__file__).resolve().parent.parent / "ui" / "MainView.qml"
    qml_url = QtCore.QUrl.fromLocalFile(str(qml_path))
    if not qml_path.exists():
        print(f"QML not found at {qml_path}", file=sys.stderr)  # type: ignore[name-defined]
        return 1

    engine.load(qml_url)
    if not engine.rootObjects():
        print("Failed to load QML UI", file=sys.stderr)  # type: ignore[name-defined]
        if hasattr(engine, "warnings"):
            try:
                for err in engine.warnings():
                    try:
                        print(err.toString(), file=sys.stderr)
                    except Exception:
                        print(err, file=sys.stderr)
            except Exception:
                pass
        return 1

    return app.exec()

