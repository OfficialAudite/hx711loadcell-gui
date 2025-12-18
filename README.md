# HX711 Load Cell UI (Tkinter, Raspberry Pi)

Modern, fullscreen HX711 scale UI for Raspberry Pi with background readings,
touch-friendly numpad, JSON-based i18n, and a reusable HX711 device module.

## Quick start (Pi)

1) Install deps  
   `sudo apt install python3-gpiozero python3-tk`
2) Wire HX711 board  
   - DT/DOUT -> chosen GPIO (default 5)  
   - SCK -> chosen GPIO (default 6)  
   - VCC -> 3V3/5V, GND -> GND
3) Run  
   `python main.py`
4) Kiosk: fullscreen is on by default (set in `main.py` / `app_ui`).
5) Optional desktop launcher on Pi: `bash scripts/install_desktop_entry.sh`
6) Optional perf tuning on Pi (sets CPU governor to performance):  
   `sudo bash scripts/optimize_pi.sh`

## UI overview (touch-friendly)

- Display: very large grams (signed), Newtons, raw count, status clock, and a colored
  calibration banner (green=ok, amber=warn, red=needs calibration).
- Main buttons: Start / Stop / Tare / Settings.
- Settings (two-column layout, readonly fields with on-screen numpad):
  - Pins: DOUT, SCK; Gain (32/64/128)
  - Scale, Offset (persisted)
  - Samples (average count), Interval (seconds)
  - Known weight (grams) for calibration
  - Decimals displayed (0+)
  - Language picker (large buttons; auto-lists `languages/*.json`)
  - Apply & Start, Stop, Tare, Calibrate, Power Up/Down, Quit, Back

## Screenshots

- Main view  
  ![Main view](images/Yv8BK4YuD8H1nFFbBG2icidUJBiwU3DS.png)
- Popup numpad  
  ![Popup numpad](images/WyOTsATb5McOK7cJnfEDknec2A0gIZHa.png)
- Settings  
  ![Settings](images/No6GX36zjPiGbg0uS1jHR5gyvpa5kibU.png)

## Calibration (safer flow)

1) In Settings, set pins/gain if needed. Enter a known weight in grams
   (e.g., 1000 for 1 kg).
2) Tap **Calibrate**.  
   - It tares (captures offset).  
   - You’re prompted on a large dialog to place the known weight.  
   - The measured delta is rechecked; if invalid/zero you get an error instead of saving.
   - Scale and offset are stored on success.
3) Tap **Apply & Start** (or Start on main) for live readings.
4) On start, a quick zero-drift check warns (banner amber/red) if the stored zero has drifted.

## Tare

- Tap **Tare** (main or settings). Runs async; applies a session-only tare offset that
  does **not** change the calibrated offset. Calibrate or restart reading to clear tare.

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

- `config.json` stores: pins, gain, scale, offset, samples, interval, known weight,
  decimals, calibration time/temp/weight, last zero raw, language.
- Saves on calibrate, tare, or Apply & Start.
- Add more languages by dropping `languages/<code>.json`.

## Controls / shortcuts

- Ctrl+Q: quit
- Esc: toggle fullscreen
- Quit button in Settings (kiosk-friendly)

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
