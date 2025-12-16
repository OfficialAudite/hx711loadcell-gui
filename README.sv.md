# HX711 vågcells‑UI (Tkinter, Raspberry Pi)

Modern UI i helskärmsläge med bakgrundsläsning, JSON-baserad i18n och
återanvändbar HX711‑modul.

## Snabbstart (Pi)

1) Installera beroenden  
   `sudo apt install python3-gpiozero python3-tk`
2) Koppla HX711  
   - DT/DOUT -> vald GPIO (standard 5)  
   - SCK -> vald GPIO (standard 6)  
   - VCC -> 3V3/5V, GND -> GND
3) Kör  
   `python main.py`
4) (Valfritt) Kiosk: avkommentera `root.attributes("-fullscreen", True)` i `lib/app_ui.py`.

## UI-översikt

- Display: stort gramvärde, råvärde, statustid.
- Knappfält (huvud): Start / Stop / Nollställ / Inställningar.
- Inställningar:
  - DOUT-pin, SCK-pin, Gain (32/64/128)
  - Skala, Offset (under session), Medelvärdesprov (Samples), Intervall (s)
  - Känd vikt (g) för kalibrering
  - Språkval (fylls automatiskt från `languages/*.json`)
  - Apply & Start, Stop, Nollställ, Kalibrera med vikt, Slå på/av, Avsluta, Tillbaka

## Kalibrering (enkel)

1) I Inställningar: sätt pinnar/gain vid behov. Ange känd vikt i gram
   (t.ex. 1000 för 1 kg).
2) Tryck **Kalibrera med vikt**.  
   - Tare körs först (töm vågen).  
   - När du blir ombedd: lägg på vikten och bekräfta.  
   - Skala beräknas och sparas; Offset uppdateras.
3) Tryck **Apply & Start** (eller Start) för livevärden.

## Nollställ (Tare)

- Tryck **Nollställ** (huvud eller inställningar). Körs asynkront; uppdaterar Offset och status.

## Språk / i18n

- JSON-filer i `languages/*.json` (levereras med `en.json`, `sv.json`). Lägg till
  fler filer med samma nycklar; de dyker upp automatiskt i språkvalet.

## Återanvänd HX711 utan GUI

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

## Konfiguration & lagring

- Inställningar och kalibrering lagras i `config.json` (skapas automatiskt):
  pinnar, gain, skala, offset, samples, intervall, känd vikt,
  kalibreringstid/-temp/-vikt, senaste nollvärde.
- Sparas när du kalibrerar, nollställer eller väljer Apply & Start.
- Lägg till fler språk genom att lägga till `languages/<code>.json`.

## Kortkommandon

- Ctrl+Q: avsluta
- Esc: växla helskärm (om aktiverad)
- Avsluta-knapp i Inställningar (för kiosk)

## Struktur

- `main.py` — start
- `lib/hx711_device.py` — hårdvaru- och trådlogik
- `lib/app_ui.py` — Tk UI
- `languages/` — JSON-översättningar (`en.json`, `sv.json`, fler kan läggas till)

## Licens

GPL-3.0-or-later. Se `LICENSE`.

## Tack / Upstream

- Baserad på HX711-Python-arbetet från Joy-IT (`JoyIT_hx711py`, GPL-2.0) på
  <https://github.com/joy-it/JoyIT_hx711py>.
