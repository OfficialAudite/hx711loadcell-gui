"""
Tkinter UI for the HX711 scale.
Uses lib.hx711_device for hardware access and languages for i18n.
"""

import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from lib.hx711_device import HX711, HX711ReaderThread, Reading
from languages import load_languages
from lib.config_store import load_config, save_config


class HX711App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.config = load_config()
        self.lang_data = load_languages()
        default_lang = "en" if "en" in self.lang_data else next(iter(self.lang_data))
        self.lang_var = tk.StringVar(value=default_lang)
        root.title(self._t("title"))
        # root.attributes("-fullscreen", True)  # enable for kiosk

        self._configure_style()

        self.hx: Optional[HX711] = None
        self.reader: Optional[HX711ReaderThread] = None

        self.status_var = tk.StringVar(value=self._t("status_idle"))
        self.raw_var = tk.StringVar(value="—")
        self.grams_var = tk.StringVar(value="—")

        self.dout_var = tk.StringVar(value=str(self.config.get("dout", 5)))
        self.sck_var = tk.StringVar(value=str(self.config.get("sck", 6)))
        self.gain_var = tk.StringVar(value=str(self.config.get("gain", 128)))
        self.scale_var = tk.StringVar(value=str(self.config.get("scale", 2280.0)))
        self.offset_var = tk.StringVar(value=str(self.config.get("offset", 0.0)))
        self.samples_var = tk.StringVar(value=str(self.config.get("samples", 8)))
        self.interval_var = tk.StringVar(value=str(self.config.get("interval", 0.2)))
        self.known_weight_var = tk.StringVar(value=str(self.config.get("known_weight", 1000.0)))

        self.display_frame: Optional[ttk.Frame] = None
        self.settings_frame: Optional[ttk.Frame] = None

        self._build_frames()
        self._eval_calibration_status(initial=True)

        # allow exiting via Ctrl+Q (useful during development)
        root.bind("<Control-q>", lambda _: self._quit())
        root.bind("<Escape>", lambda _: self._toggle_fullscreen())
        root.protocol("WM_DELETE_WINDOW", lambda: None)  # disable close button

    def _configure_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#0f1115"
        fg = "#e8eaed"
        accent = "#4f8cff"
        muted = "#9aa0a6"

        self.root.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 12))
        style.configure(
            "Display.TLabel",
            background=bg,
            foreground=fg,
            font=("Segoe UI", 72, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background=bg,
            foreground="#c9cdd1",
            font=("Segoe UI", 18),
        )
        style.configure(
            "Status.TLabel",
            background=bg,
            foreground=muted,
            font=("Segoe UI", 11),
        )
        style.configure(
            "TButton",
            font=("Segoe UI", 11),
            padding=8,
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=10,
            foreground=fg,
            background=accent,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#6a9dff")],
            foreground=[("disabled", "#555")],
        )

    def _build_frames(self):
        if self.display_frame:
            self.display_frame.destroy()
        if self.settings_frame:
            self.settings_frame.destroy()
        self._build_display()
        self._build_settings()
        self.show_display()
        self.root.title(self._t("title"))

    def _build_display(self):
        self.display_frame = ttk.Frame(self.root, padding=20)

        ttk.Label(
            self.display_frame,
            textvariable=self.grams_var,
            style="Display.TLabel",
            anchor="center",
        ).pack(fill="both", expand=True, pady=10)

        ttk.Label(
            self.display_frame,
            textvariable=self.raw_var,
            style="Sub.TLabel",
            anchor="center",
        ).pack(pady=4)

        ttk.Label(
            self.display_frame,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).pack(pady=4)

        self.cal_status_var = tk.StringVar(value=self._t("cal_status_valid"))
        self.cal_status_color = tk.StringVar(value="#4caf50")  # green
        cal_label = ttk.Label(
            self.display_frame,
            textvariable=self.cal_status_var,
            style="Status.TLabel",
            anchor="center",
            justify="center",
        )
        cal_label.pack(pady=(0, 8))
        # apply color via custom label config (ttk styles don't map dynamic fg easily)
        cal_label.configure(foreground=self.cal_status_color.get())

        btn_row = ttk.Frame(self.display_frame)
        btn_row.pack(pady=10)
        ttk.Button(
            btn_row, text=self._t("btn_start"), style="Accent.TButton", command=self.start_reading
        ).pack(side="left", padx=6)
        ttk.Button(btn_row, text=self._t("btn_stop"), command=self.stop_reading).pack(
            side="left", padx=6
        )
        ttk.Button(btn_row, text=self._t("btn_tare"), command=self._tare_async).pack(
            side="left", padx=6
        )
        ttk.Button(btn_row, text=self._t("btn_settings"), command=self.show_settings).pack(
            side="left", padx=6
        )

    def _build_settings(self):
        self.settings_frame = ttk.Frame(self.root, padding=16)

        ttk.Label(
            self.settings_frame, text=self._t("label_settings"), font=("Segoe UI", 18, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        inputs = [
            (self._t("label_dout"), self.dout_var),
            (self._t("label_sck"), self.sck_var),
            (self._t("label_gain"), self.gain_var),
            (self._t("label_scale"), self.scale_var),
            (self._t("label_offset"), self.offset_var),
            (self._t("label_samples"), self.samples_var),
            (self._t("label_interval"), self.interval_var),
            (self._t("label_known_weight"), self.known_weight_var),
        ]

        for idx, (label, var) in enumerate(inputs, start=1):
            ttk.Label(self.settings_frame, text=label).grid(
                row=idx, column=0, sticky="w", pady=4
            )
            ttk.Entry(self.settings_frame, textvariable=var, width=16).grid(
                row=idx, column=1, sticky="w", pady=4
            )

        ttk.Label(self.settings_frame, text=self._t("label_language")).grid(
            row=len(inputs) + 1, column=0, sticky="w", pady=4
        )
        lang_combo = ttk.Combobox(
            self.settings_frame,
            textvariable=self.lang_var,
            values=sorted(self.lang_data.keys()),
            state="readonly",
            width=14,
        )
        lang_combo.grid(row=len(inputs) + 1, column=1, sticky="w", pady=4)
        lang_combo.bind("<<ComboboxSelected>>", lambda _: self._on_language_change())

        btn_frame = ttk.Frame(self.settings_frame)
        btn_frame.grid(row=len(inputs) + 2, column=0, columnspan=2, pady=(12, 6))

        ttk.Button(btn_frame, text=self._t("btn_apply_start"), command=self.start_reading).grid(
            row=0, column=0, padx=4, pady=2
        )
        ttk.Button(btn_frame, text=self._t("btn_stop"), command=self.stop_reading).grid(
            row=0, column=1, padx=4, pady=2
        )
        ttk.Button(btn_frame, text=self._t("btn_tare"), command=self._tare_async).grid(
            row=0, column=2, padx=4, pady=2
        )
        ttk.Button(btn_frame, text=self._t("btn_calibrate"), command=self._calibrate_flow).grid(
            row=0, column=3, padx=4, pady=2
        )

        ttk.Button(btn_frame, text=self._t("btn_power_down"), command=self.power_down).grid(
            row=1, column=0, padx=4, pady=4
        )
        ttk.Button(btn_frame, text=self._t("btn_power_up"), command=self.power_up).grid(
            row=1, column=1, padx=4, pady=4
        )
        ttk.Button(btn_frame, text=self._t("btn_quit"), command=self._quit).grid(
            row=1, column=2, padx=4, pady=4
        )
        ttk.Button(btn_frame, text=self._t("btn_back"), command=self.show_display).grid(
            row=1, column=3, padx=4, pady=4
        )

        ttk.Label(
            self.settings_frame,
            textvariable=self.status_var,
            foreground="gray",
        ).grid(row=len(inputs) + 3, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def show_display(self):
        if self.settings_frame:
            self.settings_frame.pack_forget()
        if self.display_frame:
            self.display_frame.pack(fill="both", expand=True)

    def show_settings(self):
        if self.display_frame:
            self.display_frame.pack_forget()
        if self.settings_frame:
            self.settings_frame.pack(fill="both", expand=True)

    def start_reading(self):
        try:
            dout = int(self.dout_var.get())
            sck = int(self.sck_var.get())
            gain = int(self.gain_var.get())
            scale = float(self.scale_var.get())
            offset = float(self.offset_var.get())
            samples = max(1, int(self.samples_var.get()))
            interval = max(0.05, float(self.interval_var.get()))
            known_weight = float(self.known_weight_var.get())
        except ValueError:
            messagebox.showerror(self._t("hx_error"), self._t("invalid_input"))
            return

        self.stop_reading()

        hx = self._create_hx(dout, sck, gain)
        if not hx:
            return
        hx.set_scale(scale)
        hx.set_offset(offset)
        self.hx = hx

        self._save_config(
            {
                "dout": dout,
                "sck": sck,
                "gain": gain,
                "scale": scale,
                "offset": offset,
                "samples": samples,
                "interval": interval,
                "known_weight": known_weight,
            }
        )

        self.reader = HX711ReaderThread(
            hx=self.hx,
            samples=samples,
            interval=interval,
            callback=self._on_reading,
            error_callback=self._on_error,
        )
        self.reader.start()
        self.status_var.set(self._t("status_reading"))

    def stop_reading(self):
        if self.reader:
            self.reader.stop()
        self.reader = None

    def _on_reading(self, reading: Reading):
        self.root.after(0, self._update_ui, reading)

    def _update_ui(self, reading: Reading):
        self.raw_var.set(f"{reading.raw}")
        self.grams_var.set(f"{reading.grams:0.2f}")
        self.status_var.set(time.strftime("%H:%M:%S", time.localtime(reading.timestamp)))

    def _on_error(self, exc: Exception):
        self.root.after(0, lambda: self.status_var.set(self._t("status_error").format(err=exc)))

    def _tare_async(self):
        if not self.hx:
            messagebox.showinfo(self._t("hx_error"), self._t("info_start_first"))
            return

        import threading

        def do_tare():
            try:
                self.hx.tare(times=max(3, int(self.samples_var.get())))
                self.offset_var.set(str(self.hx.get_offset()))
                self.status_var.set(self._t("status_tared"))
                self._save_config({"offset": self.hx.get_offset()})
            except Exception as exc:
                self.status_var.set(self._t("status_error").format(err=exc))

        threading.Thread(target=do_tare, daemon=True).start()

    def power_down(self):
        if self.hx:
            self.hx.power_down()
            self.status_var.set(self._t("status_power_down"))

    def power_up(self):
        if self.hx:
            self.hx.power_up()
            self.status_var.set(self._t("status_power_up"))

    def _calibrate_flow(self):
        try:
            dout = int(self.dout_var.get())
            sck = int(self.sck_var.get())
            gain = int(self.gain_var.get())
            samples = max(3, int(self.samples_var.get()))
            known_weight = float(self.known_weight_var.get())
        except ValueError:
            messagebox.showerror(self._t("hx_error"), self._t("invalid_input"))
            return

        if known_weight <= 0:
            messagebox.showerror(self._t("hx_error"), self._t("invalid_weight"))
            return

        was_reading = self.reader is not None
        self.stop_reading()

        hx = self.hx or self._create_hx(dout, sck, gain)
        if not hx:
            return
        self.hx = hx

        self.status_var.set(self._t("status_calibrating_clear"))
        self.root.update_idletasks()
        time.sleep(0.2)
        offset = hx.read_average(samples)
        hx.set_offset(offset)
        self.offset_var.set(str(offset))
        calibration_temp = self._read_cpu_temp()

        messagebox.showinfo(
            self._t("cal_title"),
            self._t("cal_prompt_place_weight"),
        )
        measured = hx.read_average(samples) - hx.get_offset()

        scale = measured / known_weight if known_weight else 1.0
        hx.set_scale(scale)
        self.scale_var.set(f"{scale:.6f}")
        self.status_var.set(self._t("status_calibration_done"))

        self._save_config(
            {
                "scale": scale,
                "offset": offset,
                "known_weight": known_weight,
                "calibration_time": time.time(),
                "calibration_weight": known_weight,
                "calibration_temp": calibration_temp,
                "last_zero_raw": offset,
            }
        )
        self._eval_calibration_status()

        if was_reading:
            self.start_reading()

    def _create_hx(self, dout: int, sck: int, gain: int) -> Optional[HX711]:
        try:
            return HX711(dout=dout, pd_sck=sck, gain=gain)
        except Exception as exc:
            messagebox.showerror(self._t("hx_error"), str(exc))
            self.status_var.set(self._t("hx_init_failed"))
            return None

    def _toggle_fullscreen(self):
        current = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not current)

    def _quit(self):
        self.stop_reading()
        self.root.destroy()

    def _on_language_change(self):
        self._build_frames()
        if self.hx and self.reader:
            self.status_var.set(self._t("status_reading"))
        else:
            self.status_var.set(self._t("status_idle"))
        self._eval_calibration_status()

    def _t(self, key: str) -> str:
        lang = self.lang_var.get()
        if lang in self.lang_data:
            return self.lang_data[lang].get(key, self.lang_data.get("en", {}).get(key, key))
        if "en" in self.lang_data:
            return self.lang_data["en"].get(key, key)
        if self.lang_data:
            first_lang = next(iter(self.lang_data.values()))
            return first_lang.get(key, key)
        return key

    def _save_config(self, updates: dict):
        self.config.update(updates)
        save_config(self.config)

    def _read_cpu_temp(self) -> Optional[float]:
        try:
            path = "/sys/class/thermal/thermal_zone0/temp"
            with open(path, "r", encoding="utf-8") as fh:
                raw = fh.read().strip()
            return int(raw) / 1000.0
        except Exception:
            return None

    def _eval_calibration_status(self, initial: bool = False):
        """
        Lightweight validity check based on stored metadata.
        Warns if calibration is stale; does not block usage.
        """
        cfg = self.config
        cal_time = cfg.get("calibration_time")
        scale = cfg.get("scale")
        offset = cfg.get("offset")
        if cal_time is None or scale is None or offset is None:
            self.status_var.set(self._t("status_calibration_cancelled"))
            self._set_cal_status("bad", self._t("cal_status_bad"))
            return

        age_days = (time.time() - cal_time) / 86400 if cal_time else None
        warn_reasons = []
        if age_days and age_days > 7:
            warn_reasons.append(self._t("cal_warn_age"))

        if warn_reasons:
            msg = "; ".join(warn_reasons)
            self._set_cal_status("warn", msg)
            if not initial:
                self.status_var.set(msg)
        else:
            self._set_cal_status("good", self._t("cal_status_valid"))

    def _set_cal_status(self, level: str, text: str):
        self.cal_status_var.set(text)
        color = "#4caf50"  # green
        if level == "warn":
            color = "#fbbc04"  # amber
        elif level == "bad":
            color = "#ea4335"  # red
        self.cal_status_color.set(color)

