# HX711 vågcells‑UI (Tkinter, Raspberry Pi)

Modern UI i helskärmsläge med bakgrundsläsning, touchvänligt numeriskt
knappbord, JSON-baserad i18n och återanvändbar HX711‑modul.

## Snabbstart (Pi)

1) Installera beroenden  
   `sudo apt install python3-gpiozero python3-tk`
2) Koppla HX711  
   - DT/DOUT -> vald GPIO (standard 5)  
   - SCK -> vald GPIO (standard 6)  
   - VCC -> 3V3/5V, GND -> GND
3) Kör  
   `python main.py`
4) Kiosk: helskärm är aktiverat som standard.
5) (Valfritt) Skrivbordsstart på Pi: `bash scripts/install_desktop_entry.sh`

## UI-översikt (touch-vänlig)

- Display: mycket stort gramvärde (med tecken), Newton, råvärde, statustid och en färgad
  kalibreringsbanderoll (grön=OK, bärnsten=varning, röd=kräver kalibrering).
- Huvudknappar: Start / Stop / Nollställ / Inställningar.
- Inställningar (två kolumner, skrivskyddade fält med skärmtangentbord):
  - Pinnar: DOUT, SCK; Gain (32/64/128)
  - Skala, Offset (sparas)
  - Samples (medelvärden), Intervall (sekunder)
  - Känd vikt (gram) för kalibrering
  - Decimaler som visas (0+)
  - Språkval med stora knappar (`languages/*.json` autodetekteras)
  - Apply & Start, Stop, Nollställ, Kalibrera, Slå på/av, Avsluta, Tillbaka

## Kalibrering (säkrare)

1) I Inställningar: sätt pinnar/gain vid behov. Ange känd vikt i gram
   (t.ex. 1000 för 1 kg).
2) Tryck **Kalibrera**.  
   - Tare körs först (nollställning).  
   - En stor dialog ber om att lägga på vikten och bekräfta.  
   - Det uppmätta delta-värdet dubbelkollas; om det är ogiltigt/0 avbryts
     och inget sparas.  
   - Skala och offset sparas vid lyckad mätning.
3) Tryck **Apply & Start** (eller Start) för livevärden.
4) Vid start görs en snabb noll-driftkontroll; banderollen varnar om nollan drivit.

## Nollställ (Tare)

- Tryck **Nollställ** (huvud eller inställningar). Körs asynkront; lägger på en
  sessionsbaserad tare utan att ändra kalibrerings-offset. Kalibrera eller starta om läsningen
  för att rensa tare.

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

- `config.json` lagrar: pinnar, gain, skala, offset, samples, intervall,
  känd vikt, decimaler, kalibreringstid/-temp/-vikt, senaste nollvärde, språk.
- Sparas vid kalibrering, nollställning eller Apply & Start.
- Lägg till fler språk genom att lägga till `languages/<code>.json`.

## Kortkommandon

- Ctrl+Q: avsluta
- Esc: växla helskärm
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
