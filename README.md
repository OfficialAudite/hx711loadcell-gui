# HX711 Load Cell UI (Tkinter, Raspberry Pi)

Modern, fullscreen-capable HX711 scale UI with background readings, JSON-based
i18n, and a reusable HX711 device module.

## Quick start (Pi)

1) Install deps  
   `sudo apt install python3-gpiozero python3-tk`
2) Wire HX711 board  
   - DT/DOUT -> chosen GPIO (default 5)  
   - SCK -> chosen GPIO (default 6)  
   - VCC -> 3V3/5V, GND -> GND
3) Run  
   `python main.py`
4) (Optional) Kiosk: uncomment `root.attributes("-fullscreen", True)` in `lib/app_ui.py`.

## UI overview

- Display: big grams value, raw count, status time.
- Buttons (main): Start / Stop / Tare / Settings.
- Settings:
  - DOUT pin, SCK pin, Gain (32/64/128)
  - Scale, Offset (persisted in session), Samples (avg count), Interval (s)
  - Known weight (g) for calibration
  - Language selector (auto-fills from `languages/*.json`)
  - Apply & Start, Stop, Tare, Calibrate with weight, Power Up/Down, Quit, Back

## Calibration (simple flow)

1) In Settings, set pins/gain if needed. Enter your known weight in grams
   (e.g., 1000 for 1 kg).
2) Tap **Calibrate with weight**.  
   - It first tares (clear the scale).  
   - When prompted, place the known weight and confirm.  
   - Scale is computed and stored; Offset updated.
3) Tap **Apply & Start** (or Start on main) for live readings.

## Tare

- Tap **Tare** (main or settings). Runs async; updates Offset and status.

## Language / i18n

- JSON files in `languages/*.json` (ships with `en.json`, `sv.json`). Add more
  files with same keys; they auto-appear in the selector.

## Reusing the HX711 device code (no GUI)

```python
from lib.hx711_device import HX711, HX711ReaderThread

hx = HX711(dout=5, pd_sck=6, gain=128)
hx.set_scale(2280)
hx.set_offset(0)

def on_reading(r):
    print(r.grams)

reader = HX711ReaderThread(hx, samples=8, interval=0.2, callback=on_reading, error_callback=print)
reader.start()
```

## Config & persistence

- Settings and calibration are stored in `config.json` (auto-created): pins, gain,
  scale, offset, samples, interval, known weight, calibration time/temp/weight,
  last zero raw.
- Saving happens when you calibrate, tare, or apply & start.
- Add more languages by dropping `languages/<code>.json`.

## Controls / shortcuts

- Ctrl+Q: quit
- Esc: toggle fullscreen (if enabled)
- Quit button in Settings (useful in kiosk)

## Project layout

- `main.py` — entry point
- `lib/hx711_device.py` — device + reader thread
- `lib/app_ui.py` — Tk UI
- `languages/` — JSON translations (`en.json`, `sv.json`, add more)

## License

GPL-3.0-or-later. See `LICENSE`.

## Credits / Upstream

- Based on the HX711 Python work from Joy-IT (`JoyIT_hx711py`, GPL-2.0) at
  <https://github.com/joy-it/JoyIT_hx711py>.
