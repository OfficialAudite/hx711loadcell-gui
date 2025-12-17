"""
Tkinter UI for the HX711 scale.
Uses lib.hx711_device for hardware access and languages for i18n.
"""

import time
import math
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
        config_lang = self.config.get("language")
        if config_lang in self.lang_data:
            default_lang = config_lang
        elif "en" in self.lang_data:
            default_lang = "en"
        else:
            default_lang = next(iter(self.lang_data))
        self.lang_var = tk.StringVar(value=default_lang)
        root.title(self._t("title"))
        root.attributes("-fullscreen", True)  # enable for kiosk

        self._configure_style()

        self.hx: Optional[HX711] = None
        self.reader: Optional[HX711ReaderThread] = None
        self.cal_banner = None
        self.cal_banner_label = None

        self.status_var = tk.StringVar(value=self._t("status_idle"))
        self.raw_var = tk.StringVar(value="—")
        self.grams_var = tk.StringVar(value="—")
        self.newtons_var = tk.StringVar(value="—")
        self.decimals_var = tk.StringVar(value=str(self.config.get("decimals", 2)))
        self.tare_offset = 0.0

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
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 16))
        style.configure(
            "Display.TLabel",
            background=bg,
            foreground=fg,
            font=("Segoe UI", 96, "bold"),
        )
        style.configure(
            "Sub.TLabel",
            background=bg,
            foreground="#c9cdd1",
            font=("Segoe UI", 24),
        )
        style.configure(
            "Status.TLabel",
            background=bg,
            foreground=muted,
            font=("Segoe UI", 16),
        )
        style.configure(
            "TButton",
            font=("Segoe UI", 15),
            padding=12,
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 15, "bold"),
            padding=14,
            foreground=fg,
            background=accent,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#6a9dff")],
            foreground=[("disabled", "#555")],
        )
        style.configure(
            "TEntry",
            font=("Segoe UI", 18),
            padding=10,
        )
        style.configure(
            "Numpad.TButton",
            font=("Segoe UI", 18, "bold"),
            padding=12,
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

        # Calibration banner at top
        self.cal_status_var = tk.StringVar(value=self._t("cal_status_valid"))
        self.cal_status_color = tk.StringVar(value="#4caf50")  # green
        self.cal_banner = tk.Frame(self.display_frame, bg=self.cal_status_color.get(), height=44)
        self.cal_banner.pack(fill="x", pady=(0, 8))
        self.cal_banner_label = tk.Label(
            self.cal_banner,
            textvariable=self.cal_status_var,
            bg=self.cal_status_color.get(),
            fg="#ffffff",
            font=("Segoe UI", 16, "bold"),
            anchor="center",
        )
        self.cal_banner_label.pack(fill="both", expand=True, padx=6, pady=6)

        ttk.Label(
            self.display_frame,
            textvariable=self.grams_var,
            style="Display.TLabel",
            anchor="center",
        ).pack(fill="both", expand=True, pady=10)

        ttk.Label(
            self.display_frame,
            textvariable=self.newtons_var,
            style="Sub.TLabel",
            anchor="center",
        ).pack(pady=2)

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
            self.settings_frame, text=self._t("label_settings"), font=("Segoe UI", 20, "bold")
        ).grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))

        form_frame = self.settings_frame
        for col in range(6):
            form_frame.grid_columnconfigure(col, weight=1, uniform="settings")

        inputs = [
            (self._t("label_dout"), self.dout_var, False, False),
            (self._t("label_sck"), self.sck_var, False, False),
            (self._t("label_gain"), self.gain_var, False, False),
            (self._t("label_scale"), self.scale_var, True, True),
            (self._t("label_offset"), self.offset_var, True, True),
            (self._t("label_samples"), self.samples_var, False, False),
            (self._t("label_interval"), self.interval_var, True, False),
            (self._t("label_known_weight"), self.known_weight_var, True, False),
            (self._t("label_decimals"), self.decimals_var, False, False),
        ]

        for idx, (label, var, allow_float, allow_negative) in enumerate(inputs):
            row = 1 + (idx // 2)
            col_base = 0 if idx % 2 == 0 else 3
            ttk.Label(form_frame, text=label).grid(
                row=row, column=col_base, sticky="w", pady=6, padx=(0, 4)
            )
            entry = ttk.Entry(
                form_frame,
                textvariable=var,
                width=9,
                state="readonly",
                justify="left",
            )
            entry.grid(row=row, column=col_base + 1, sticky="w", pady=6, padx=(0, 4))
            entry.bind(
                "<Button-1>",
                lambda _e, v=var, t=label, f=allow_float, n=allow_negative: self._open_numpad(v, t, f, n),
            )
            ttk.Button(
                form_frame,
                text="⌨",
                width=4,
                command=lambda v=var, t=label, f=allow_float, n=allow_negative: self._open_numpad(v, t, f, n),
            ).grid(row=row, column=col_base + 2, sticky="w", pady=6, padx=(0, 10))

        rows_used = 1 + (len(inputs) + 1) // 2
        ttk.Label(self.settings_frame, text=self._t("label_language")).grid(
            row=rows_used, column=0, sticky="w", pady=8
        )
        ttk.Button(
            self.settings_frame,
            text=self._t("btn_change_language"),
            command=self._open_language_picker,
            width=18,
        ).grid(row=rows_used, column=1, sticky="w", pady=8, padx=(0, 4))
        ttk.Label(
            self.settings_frame,
            textvariable=self.lang_var,
            width=10,
            anchor="w",
        ).grid(row=rows_used, column=2, sticky="w", pady=8)

        btn_frame = ttk.Frame(self.settings_frame)
        btn_frame.grid(row=rows_used + 1, column=0, columnspan=6, pady=(16, 10))
        for col in range(4):
            btn_frame.grid_columnconfigure(col, weight=1, uniform="actions")

        ttk.Button(btn_frame, text=self._t("btn_apply_start"), command=self.start_reading, width=16).grid(
            row=0, column=0, padx=6, pady=4
        )
        ttk.Button(btn_frame, text=self._t("btn_stop"), command=self.stop_reading, width=16).grid(
            row=0, column=1, padx=6, pady=4
        )
        ttk.Button(btn_frame, text=self._t("btn_tare"), command=self._tare_async, width=16).grid(
            row=0, column=2, padx=6, pady=4
        )
        ttk.Button(btn_frame, text=self._t("btn_calibrate"), command=self._calibrate_flow, width=16).grid(
            row=0, column=3, padx=6, pady=4
        )

        ttk.Button(btn_frame, text=self._t("btn_power_down"), command=self.power_down, width=16).grid(
            row=1, column=0, padx=6, pady=6
        )
        ttk.Button(btn_frame, text=self._t("btn_power_up"), command=self.power_up, width=16).grid(
            row=1, column=1, padx=6, pady=6
        )
        ttk.Button(btn_frame, text=self._t("btn_quit"), command=self._quit, width=16).grid(
            row=1, column=2, padx=6, pady=6
        )
        ttk.Button(btn_frame, text=self._t("btn_back"), command=self.show_display, width=16).grid(
            row=1, column=3, padx=6, pady=6
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
            decimals = max(0, int(self.decimals_var.get()))
        except ValueError:
            messagebox.showerror(self._t("hx_error"), self._t("invalid_input"))
            return

        self.stop_reading()

        hx = self._create_hx(dout, sck, gain)
        if not hx:
            return
        hx.set_scale(scale)
        hx.set_offset(offset)
        hx.clear_tare()
        self.tare_offset = 0.0
        self.hx = hx

        # Quick zero-drift check against stored calibration zero.
        last_zero_raw = self.config.get("last_zero_raw")
        if last_zero_raw is not None:
            try:
                zero_samples = max(3, samples)
                current_zero = hx.read_average(zero_samples)
                drift_grams = abs((current_zero - hx.get_offset()) / max(hx.get_scale(), 1e-9))
                drift_limit = 5.0  # grams tolerance for drift warning
                if drift_grams > drift_limit:
                    self._set_cal_status("warn", self._t("cal_warn_zero"))
                    self.status_var.set(self._t("cal_warn_zero"))
            except Exception:
                # Non-blocking: ignore drift check failures
                pass

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
                "decimals": decimals,
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
        if self.hx:
            try:
                self.hx.close()
            except Exception:
                pass
        self.hx = None

    def _on_reading(self, reading: Reading):
        self.root.after(0, self._update_ui, reading)

    def _update_ui(self, reading: Reading):
        self.raw_var.set(f"{reading.raw}")
        grams = reading.grams  # allow signed values when tared
        try:
            decimals = max(0, int(self.decimals_var.get()))
        except Exception:
            decimals = 2
        if decimals == 0:
            self.grams_var.set(f"{round(grams):.0f} g")
        else:
            fmt = f"{{grams:0.{decimals}f}} g"
            self.grams_var.set(fmt.format(grams=grams))
        # Newtons: grams -> kg -> N
        try:
            newtons = (grams / 1000.0) * 9.80665
            self.newtons_var.set(f"{newtons:0.3f} N")
        except Exception:
            self.newtons_var.set("—")
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
                samples = max(3, int(self.samples_var.get()))
                tare_raw = self.hx.read_average(samples)
                tare_offset = tare_raw - self.hx.get_offset()
                self.hx.set_tare_offset(tare_offset)
                self.tare_offset = tare_offset
                self.status_var.set(self._t("status_tared"))
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
        hx.clear_tare()
        self.tare_offset = 0.0
        self.offset_var.set(str(offset))
        calibration_temp = self._read_cpu_temp()

        messagebox.showinfo(
            self._t("cal_title"),
            self._t("cal_prompt_place_weight"),
        )
        measured = hx.read_average(samples) - hx.get_offset()
        measured = abs(measured)
        if measured <= 0 or not math.isfinite(measured):
            messagebox.showerror(self._t("hx_error"), self._t("invalid_scale"))
            if was_reading:
                self.start_reading()
            return

        proceed = self._prompt_continue(self._t("cal_title"), self._t("cal_prompt_place_weight"))
        if not proceed:
            if was_reading:
                self.start_reading()
            return

        measured = hx.read_average(samples) - hx.get_offset()
        measured = abs(measured)
        if measured <= 0 or not math.isfinite(measured):
            messagebox.showerror(self._t("hx_error"), self._t("invalid_scale"))
            if was_reading:
                self.start_reading()
            return

        scale = measured / known_weight if known_weight else 1.0
        if scale <= 0 or not math.isfinite(scale):
            messagebox.showerror(self._t("hx_error"), self._t("invalid_scale"))
            if was_reading:
                self.start_reading()
            return
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

    def _open_numpad(self, target_var: tk.StringVar, title: str, allow_float: bool, allow_negative: bool):
        """
        Touch-friendly numeric pad dialog that updates target_var.
        allow_float controls '.'; allow_negative toggles sign.
        """
        top = tk.Toplevel(self.root)
        top.title(title)
        top.transient(self.root)
        top.grab_set()

        val = tk.StringVar(value=target_var.get())

        def append_char(ch: str):
            current = val.get()
            if ch == "." and not allow_float:
                return
            if ch == "." and "." in current:
                return
            val.set(current + ch)

        def toggle_sign():
            if not allow_negative:
                return
            current = val.get()
            if current.startswith("-"):
                val.set(current[1:])
            else:
                val.set("-" + current)

        def backspace():
            val.set(val.get()[:-1])

        def clear():
            val.set("")

        def accept():
            target_var.set(val.get() or "0")
            top.destroy()

        def cancel():
            top.destroy()

        ttk.Label(top, text=title, font=("Segoe UI", 16, "bold")).grid(
            row=0, column=0, columnspan=4, pady=(8, 4), padx=10, sticky="we"
        )
        entry = ttk.Entry(top, textvariable=val, font=("Segoe UI", 18), justify="right")
        entry.grid(row=1, column=0, columnspan=4, pady=4, padx=10, sticky="we")
        entry.focus_set()

        buttons = [
            ("7", lambda: append_char("7")),
            ("8", lambda: append_char("8")),
            ("9", lambda: append_char("9")),
            ("⌫", backspace),
            ("4", lambda: append_char("4")),
            ("5", lambda: append_char("5")),
            ("6", lambda: append_char("6")),
            ("±", toggle_sign),
            ("1", lambda: append_char("1")),
            ("2", lambda: append_char("2")),
            ("3", lambda: append_char("3")),
            ("C", clear),
            (".", lambda: append_char(".")),
            ("0", lambda: append_char("0")),
            (self._t("btn_cancel"), cancel),
            ("OK", accept),
        ]

        row = 2
        col = 0
        for text, cmd in buttons:
            ttk.Button(top, text=text, command=cmd, width=8, style="Numpad.TButton").grid(
                row=row, column=col, padx=4, pady=4, sticky="nsew"
            )
            col += 1
            if col > 3:
                col = 0
                row += 1

        for i in range(4):
            top.grid_columnconfigure(i, weight=1)

        self.root.wait_window(top)

    def _open_language_picker(self):
        """Touch-friendly language chooser with large buttons."""
        top = tk.Toplevel(self.root)
        top.title(self._t("label_language"))
        top.transient(self.root)
        top.grab_set()

        ttk.Label(top, text=self._t("label_language"), font=("Segoe UI", 14, "bold")).pack(
            padx=12, pady=(10, 6)
        )

        btn_frame = ttk.Frame(top)
        btn_frame.pack(padx=12, pady=(0, 10), fill="both", expand=True)

        def choose(lang: str):
            self.lang_var.set(lang)
            top.destroy()
            self._on_language_change()

        for lang in sorted(self.lang_data.keys()):
            ttk.Button(
                btn_frame,
                text=lang,
                command=lambda l=lang: choose(l),
                width=24,
            ).pack(fill="x", pady=4)

        ttk.Button(top, text=self._t("btn_cancel"), command=top.destroy).pack(pady=(0, 10))

    def _prompt_continue(self, title: str, message: str) -> bool:
        """Large-format modal prompt used for calibration steps."""
        top = tk.Toplevel(self.root)
        top.title(title)
        top.transient(self.root)
        top.grab_set()
        top.geometry("520x280")

        ttk.Label(top, text=title, font=("Segoe UI", 18, "bold")).pack(
            padx=16, pady=(18, 10)
        )
        msg = ttk.Label(top, text=message, font=("Segoe UI", 16), wraplength=460, justify="center")
        msg.pack(padx=16, pady=(0, 18))

        result = {"ok": False}

        def on_ok():
            result["ok"] = True
            top.destroy()

        def on_cancel():
            top.destroy()

        btn_frame = ttk.Frame(top)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text=self._t("btn_cancel"), command=on_cancel, width=14).pack(
            side="left", padx=8
        )
        ttk.Button(
            btn_frame, text=self._t("btn_apply_start"), style="Accent.TButton", command=on_ok, width=16
        ).pack(side="left", padx=8)

        self.root.wait_window(top)
        return result["ok"]

    def _on_language_change(self):
        self._save_config({"language": self.lang_var.get()})
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
        self._apply_cal_status_style()

    def _apply_cal_status_style(self):
        """Update banner colors to match current status."""
        if not self.cal_banner or not self.cal_banner_label:
            return
        color = self.cal_status_color.get()
        fg = "#0f1115" if color == "#fbbc04" else "#ffffff"
        self.cal_banner.configure(bg=color)
        self.cal_banner_label.configure(bg=color, fg=fg)

