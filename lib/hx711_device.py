"""
HX711 device and helper classes.
Separated for reuse in GUI and non-GUI contexts.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

try:
    import gpiozero  # type: ignore[import]
except ImportError as exc:  # pragma: no cover - hardware dependency
    gpiozero = None
    GPIOZERO_IMPORT_ERROR = exc
else:
    GPIOZERO_IMPORT_ERROR = None


class HX711:
    """
    HX711 load cell amplifier helper adapted for gpiozero pins.
    """

    def __init__(self, dout: int, pd_sck: int, gain: int = 128):
        if gpiozero is None:
            raise RuntimeError(
                "gpiozero is required on Raspberry Pi. "
                "Install with `sudo apt install python3-gpiozero`."
            ) from GPIOZERO_IMPORT_ERROR

        self.GAIN = 0
        self.OFFSET = 0
        self.SCALE = 1
        self.TARE_OFFSET = 0  # additional, non-persisted offset from user tare (raw units)

        self.PD_SCK = gpiozero.OutputDevice(pd_sck)
        self.DOUT = gpiozero.DigitalInputDevice(dout, pull_up=False)
        self._closed = False

        self.power_up()
        self.set_gain(gain)

    def set_gain(self, gain: int = 128):
        try:
            if gain == 128:
                self.GAIN = 3
            elif gain == 64:
                self.GAIN = 2
            elif gain == 32:
                self.GAIN = 1
        except Exception:
            self.GAIN = 3  # default to 128

        self.PD_SCK.off()
        self.read()

    def set_scale(self, scale: float):
        self.SCALE = scale

    def set_offset(self, offset: float):
        self.OFFSET = offset

    def get_scale(self) -> float:
        return self.SCALE

    def get_offset(self) -> float:
        return self.OFFSET

    def set_tare_offset(self, tare_offset: float):
        """Store a transient tare offset without modifying calibration offset."""
        self.TARE_OFFSET = tare_offset

    def clear_tare(self):
        self.TARE_OFFSET = 0

    def get_tare_offset(self) -> float:
        return self.TARE_OFFSET

    def read(self) -> int:
        while not (self.DOUT.is_active == 0):
            time.sleep(0.0001)

        count = 0
        for _ in range(24):
            self.PD_SCK.on()
            count <<= 1
            self.PD_SCK.off()
            if self.DOUT.is_active == 1:
                count += 1

        self.PD_SCK.on()
        count ^= 0x800000
        self.PD_SCK.off()

        for _ in range(self.GAIN):
            self.PD_SCK.on()
            self.PD_SCK.off()

        return count

    def read_average(self, times: int = 16) -> float:
        total = 0
        for _ in range(times):
            total += self.read()
        return total / times

    def get_grams(self, times: int = 16) -> float:
        raw_delta = abs(self.read_average(times) - self.OFFSET)
        tare_delta = abs(self.TARE_OFFSET)
        return (raw_delta - tare_delta) / self.SCALE

    def tare(self, times: int = 16):
        self.set_offset(self.read_average(times))

    def power_down(self):
        self.PD_SCK.off()
        self.PD_SCK.on()

    def power_up(self):
        self.PD_SCK.off()

    def close(self):
        """Release GPIO resources."""
        if self._closed:
            return
        self._closed = True
        for dev in (self.DOUT, self.PD_SCK):
            try:
                dev.close()
            except Exception:
                pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


@dataclass
class Reading:
    raw: int
    grams: float
    timestamp: float = field(default_factory=time.time)
    period_sec: Optional[float] = None


class HX711ReaderThread:
    """
    Polls HX711 in background and pushes results to a callback.
    """

    def __init__(
        self,
        hx: HX711,
        samples: int,
        interval: float,
        callback: Callable[[Reading], None],
        error_callback: Callable[[Exception], None],
    ):
        self.hx = hx
        self.samples = samples
        self.interval = interval
        self.callback = callback
        self.error_callback = error_callback
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # lightweight smoothing buffer to reduce visible jitter without slowing updates
        self._gram_buffer = deque(maxlen=3)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.5)

    def _run(self):
        while not self._stop.is_set():
            t0 = time.time()
            try:
                raw = self.hx.read_average(self.samples)
                raw_delta = abs(raw - self.hx.get_offset())
                tare_delta = abs(self.hx.get_tare_offset())
                grams = (raw_delta - tare_delta) / max(self.hx.get_scale(), 1e-9)
                self._gram_buffer.append(grams)
                grams_smoothed = sorted(self._gram_buffer)[len(self._gram_buffer) // 2]
                elapsed = time.time() - t0
                period = elapsed + self.interval  # approximate full cycle incl. sleep
                self.callback(Reading(raw=int(raw), grams=grams_smoothed, period_sec=period))
            except Exception as exc:  # hardware/IO errors
                self.error_callback(exc)
                time.sleep(self.interval)
                continue
            time.sleep(self.interval)

