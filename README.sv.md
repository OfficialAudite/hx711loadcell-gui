# HX711 vågcells‑UI (Qt Quick, Raspberry Pi)

Modern, macOS-inspirerad UI (Qt Quick / PySide6) i helskärmsläge med
bakgrundsläsning, JSON-baserad i18n och återanvändbar HX711‑modul.

## Snabbstart

- Installera beroenden: `pip install -r requirements.txt`
- Skrivbord (Qt UI): `python main.py` (lägg till `--demo` för att prova utan hårdvara)
- Raspberry Pi med HX711:  
  `sudo apt install python3-gpiozero`  
  `pip install -r requirements.txt`  
  Koppla HX711 (DT/DOUT -> GPIO 5, SCK -> GPIO 6, VCC -> 3V3/5V, GND -> GND)  
  `python main.py`
- Helskärm (Qt): använd fönsterknapp eller systemets helskärmskommando.

## UI-översikt (Qt Quick, macOS-inspirerad)

- Ren huvudvy med mycket stora gram, Newton, råvärde, Hz och en pillformad
  kalibreringsindikator (grön/bärnsten/röd).
- Primära knappar: Start, Stop, Nollställ, Kalibrera, Inställningar.
- Inställningar i en högerpanel (desktop-vänlig):
  - Pinnar: DOUT, SCK; Gain (32/64/128)
  - Skala, Offset (sparas)
  - Samples (medelvärden), Intervall (sekunder)
  - Känd vikt (gram) för kalibrering
  - Decimaler som visas (0+)
  - Växling för "rolling window"-utjämning
  - Spara, Apply & Start
- Demoläge (`--demo`) för att testa UI utan HX711-hårdvara.

## Skärmdumpar

- Huvudvy  
  ![Huvudvy](images/Yv8BK4YuD8H1nFFbBG2icidUJBiwU3DS.png)
- Popup-numpad  
  ![Popup-numpad](images/WyOTsATb5McOK7cJnfEDknec2A0gIZHa.png)
- Inställningar  
  ![Inställningar](images/No6GX36zjPiGbg0uS1jHR5gyvpa5kibU.png)

## Kalibrering (förenklad i Qt-UI)

1) I Inställningar: sätt pinnar/gain vid behov. Ange känd vikt i gram
   (t.ex. 1000 för 1 kg).
2) Lägg vikten på vågen och tryck **Kalibrera** (i huvudvyn).  
   - Appen nollställer, mäter, beräknar skala och sparar offset/skala/tid.  
   - Om mätningen är ogiltig sparas inget och ett fel visas.
3) Tryck **Apply & Start** för att återgå till livevärden.
4) Banderollen varnar (bärnsten/röd) om kalibrering saknas eller är gammal.

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

- `main.py` — start (Qt Quick)
- `lib/qt_app.py` — Qt-brygga + controller
- `lib/hx711_device.py` — hårdvaru- och trådlogik
- `ui/MainView.qml` — Qt Quick UI
- `languages/` — JSON-översättningar (`en.json`, `sv.json`, fler kan läggas till)

## Licens

GPL-3.0-or-later. Se `LICENSE`.

## Tack / Upstream

- Baserad på HX711-Python-arbetet från Joy-IT (`JoyIT_hx711py`, GPL-2.0) på
  <https://github.com/joy-it/JoyIT_hx711py>.
