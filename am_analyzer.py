# =============================================================================
# VIRTUAL AM SPECTRUM ANALYZER v5.6.4 (Full UI State Sync)
# Dibuat oleh: Dhimas Ardinata Putra Pamungkas
# NIM: 4.3.22.0.10 | Kelas: TE-4A
#
# Perubahan v5.6.4 (Full UI State Sync):
# - FIX: Memastikan semua kontrol UI (slider, dropdown, entry) pada tab
#   "Sinyal" dan "Kanal & Modulasi" diperbarui secara visual untuk
#   mencerminkan nilai dari preset yang baru dimuat.
# - Mengimplementasikan sistem state management yang lebih robust untuk
#   bentuk sinyal, memisahkan nama tampilan dari nilai internal.
# - Last User Request: Combining the previous "music preset" fix with this UI sync fix.
# =============================================================================

import tkinter as tk
from tkinter import ttk, filedialog
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.ticker import EngFormatter
from scipy import signal as sig
import textwrap
import threading
import queue

# --- Pustaka baru untuk pemutaran audio ---
try:
    import sounddevice as sd

    AUDIO_ENABLED = True
except ImportError:
    AUDIO_ENABLED = False

# --- Pustaka UI Modern ---
try:
    import ttkbootstrap as tb

    TTK_BOOTSTRAP_ENABLED = True
except ImportError:
    TTK_BOOTSTRAP_ENABLED = False

# --- Konstanta & Info Aplikasi ---
AUTHOR_NAME = "Dhimas Ardinata Putra Pamungkas"
NIM = "4.3.22.0.10"
CLASS = "TE-4A"
FULL_CREDIT = f"Dibuat oleh: {AUTHOR_NAME} | {NIM} - {CLASS}"
APP_TITLE = f"Virtual AM Spectrum Analyzer v5.6.4 - {AUTHOR_NAME}"


class ToolTip:
    """Membuat tooltip untuk widget tertentu."""

    def __init__(self, widget, text):
        self.widget, self.text, self.tooltip_window = widget, text, None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("tahoma", "8", "normal"),
        ).pack(ipadx=1)

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None


class SignalProcessor:
    """Menangani semua tugas pemrosesan sinyal."""

    def calculate_thd(self, signal_data, fundamental_freq, sampling_rate):
        n = len(signal_data)
        if n < 2:
            return 0.0
        yf, xf = np.fft.fft(signal_data), np.fft.fftfreq(n, 1 / sampling_rate)
        idx_fund = np.argmin(np.abs(xf - fundamental_freq))
        p_fund = np.abs(yf[idx_fund]) ** 2
        p_harm = sum(
            np.abs(yf[np.argmin(np.abs(xf - i * fundamental_freq))]) ** 2
            for i in range(2, 11)
        )
        if p_fund == 0:
            return float("inf")
        return (np.sqrt(p_harm) / np.sqrt(p_fund)) * 100

    def modulate(self, msg, carrier, ac, mode):
        return (ac + msg) * (carrier / ac) if mode == "DSB-FC" else msg * (carrier / ac)

    def envelope_demodulate(self, mod, fm, sr):
        rect = np.abs(mod)
        b, a = sig.butter(4, 1.5 * fm / (0.5 * sr), "low")
        dem = sig.filtfilt(b, a, rect)
        return dem - np.mean(dem)

    def coherent_demodulate(self, mod, t, fc, pe, fm, sr):
        lo = np.cos(2 * np.pi * fc * t + np.deg2rad(pe))
        mul = mod * lo
        b, a = sig.butter(4, 1.5 * fm / (0.5 * sr), "low")
        dem = sig.filtfilt(b, a, mul)
        return dem * 2

    def add_noise(self, s, snr):
        p_s = np.mean(s**2)
        p_s_db = 10 * np.log10(p_s + 1e-9)
        p_n_db = p_s_db - snr
        p_n = 10 ** (p_n_db / 10)
        return s + np.random.normal(0, np.sqrt(p_n), len(s))

    def calc_power(self, ac, m, mode):
        if mode == "DSB-FC":
            m_eff = min(m, 1.0)
            Pc, Psb = (ac**2) / 2, (ac**2 / 2) * (m_eff**2) / 2
            Pt = Pc + Psb
            eff = (Psb / Pt) * 100 if Pt > 0 else 0
        else:
            Pc, Pt, Psb, eff = (
                0,
                (ac * m) ** 2 / 2,
                (ac * m) ** 2 / 2,
                100.0 if (ac * m) > 0 else 0,
            )
        return {"Pc": Pc, "Psb": Psb, "Pt": Pt, "eff": eff}

    def gen_time_vector(self, dur, sr, max_s):
        n = min(int(dur * sr), max_s)
        return np.linspace(0, dur, n, endpoint=False)

    def gen_message_signal(self, t, a, f, sh):
        if sh == "dual_tone":
            tone1 = (a / 2) * np.cos(2 * np.pi * f * t)
            tone2 = (a / 2) * np.cos(2 * np.pi * (3 * f) * t)
            return tone1 + tone2
        return a * {"sine": np.cos, "square": sig.square, "sawtooth": sig.sawtooth}[sh](
            2 * np.pi * f * t
        )

    def gen_carrier_signal(self, t, a, f):
        return a * np.cos(2 * np.pi * f * t)

    def calc_fft(self, s, sr):
        n = len(s)
        if n == 0:
            return np.array([]), np.array([]), np.array([])
        yf, xf = np.fft.fft(s), np.fft.fftfreq(n, 1 / sr)
        mag = 2.0 / n * np.abs(yf[: n // 2])
        return xf[: n // 2], mag, 20 * np.log10(mag + 1e-9)


class AMSimulatorGUI:
    MAX_SAMPLES, DEBOUNCE_TIME_MS = 150_000, 300
    FONT_BOLD, FONT_ITALIC = ("Segoe UI", 10, "bold"), ("Segoe UI", 9, "italic")

    # NEW: Central source of truth for signal shapes
    SIGNAL_SHAPES = {
        "Sine": "sine",
        "Square": "square",
        "Sawtooth": "sawtooth",
        "Dual Tone (Music)": "dual_tone",
    }

    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1300x900")
        self.processor = SignalProcessor()
        self._debounce_timer = None
        self.previous_preset = "Default (Modulasi Baik)"
        self._is_updating_internally = False
        self.signals = {}
        self.play_buttons = []

        self.calculation_queue = queue.Queue()
        self.is_calculating = False

        self._define_presets()
        self._setup_styles()
        self._setup_vars()
        self._setup_ui()
        self.load_preset("Default (Modulasi Baik)")
        self._check_calculation_queue()

    def _define_presets(self):
        self.presets = {
            "--- Dasar & Edukasional ---": None,
            "Default (Modulasi Baik)": {
                "ac": "1",
                "fc": "10k",
                "m": 0.7,
                "fm": "500",
                "snr": 50,
                "shape": "sine",
                "mode": "DSB-FC",
                "demod_mode": "Envelope",
                "phase_error": 0,
            },
            "Modulasi 100% (Ideal)": {
                "ac": "1",
                "fc": "10k",
                "m": 1.0,
                "fm": "500",
                "snr": 50,
                "shape": "sine",
                "mode": "DSB-FC",
                "demod_mode": "Envelope",
                "phase_error": 0,
            },
            "Overmodulation (Distorsi)": {
                "ac": "1",
                "fc": "10k",
                "m": 1.5,
                "fm": "500",
                "snr": 50,
                "shape": "sine",
                "mode": "DSB-FC",
                "demod_mode": "Envelope",
                "phase_error": 0,
            },
            "Sinyal Kotak (Harmonik)": {
                "ac": "1",
                "fc": "50k",
                "m": 0.5,
                "fm": "1k",
                "snr": 50,
                "shape": "square",
                "mode": "DSB-FC",
                "demod_mode": "Envelope",
                "phase_error": 0,
            },
            "DSB-SC (Efisien)": {
                "ac": "1",
                "fc": "20k",
                "m": 1.0,
                "fm": "1k",
                "snr": 50,
                "shape": "sine",
                "mode": "DSB-SC",
                "demod_mode": "Coherent",
                "phase_error": 0,
            },
            "--- Audio & Dunia Nyata ---": None,
            "Nada Uji Terdengar (440Hz)": {
                "ac": "1",
                "fc": "10k",
                "m": 0.8,
                "fm": "440",
                "snr": 40,
                "shape": "sine",
                "mode": "DSB-FC",
                "demod_mode": "Envelope",
                "phase_error": 0,
            },
            "AM Radio - Musik (MW)": {
                "ac": "1",
                "fc": "900k",
                "m": 0.8,
                "fm": "400",
                "snr": 25,
                "shape": "dual_tone",
                "mode": "DSB-FC",
                "demod_mode": "Envelope",
                "phase_error": 0,
            },
            "--- Kondisi Buruk & Batasan ---": None,
            "Sangat Berisik (SNR Rendah)": {
                "ac": "1",
                "fc": "10k",
                "m": 0.8,
                "fm": "1k",
                "snr": 3,
                "shape": "sine",
                "mode": "DSB-FC",
                "demod_mode": "Envelope",
                "phase_error": 0,
            },
            "Coherent - Phase Error 45°": {
                "ac": "1",
                "fc": "10k",
                "m": 0.7,
                "fm": "500",
                "snr": 50,
                "shape": "sine",
                "mode": "DSB-FC",
                "demod_mode": "Coherent",
                "phase_error": 45,
            },
        }

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.map(
            "TEntry", fieldbackground=[("invalid", "#ffdddd"), ("!invalid", "white")]
        )

    def _setup_vars(self):
        (self.ac_var, self.fc_var, self.am_var, self.fm_var) = (
            tk.StringVar(),
            tk.StringVar(),
            tk.StringVar(),
            tk.StringVar(),
        )
        (self.m_var, self.snr_var, self.phase_error_var) = (
            tk.DoubleVar(),
            tk.DoubleVar(),
            tk.DoubleVar(),
        )
        # MODIFIED: Split shape_var into internal state and UI display
        self.shape_var = tk.StringVar()  # Internal value for calculations
        self.shape_display_var = tk.StringVar()  # Value shown in the OptionMenu
        (self.mode_var, self.demod_mode_var, self.fft_scale_var) = (
            tk.StringVar(),
            tk.StringVar(),
            tk.StringVar(),
        )
        self.pause_update_var, self.preset_var = tk.BooleanVar(), tk.StringVar()
        (
            self.status_var,
            self.bandwidth_var,
            self.efficiency_var,
            self.insights_var,
            self.thd_var,
        ) = (
            tk.StringVar(),
            tk.StringVar(),
            tk.StringVar(),
            tk.StringVar(),
            tk.StringVar(),
        )
        self.fft_center_var, self.fft_span_var = tk.StringVar(), tk.StringVar()
        self.marker_info_var = tk.StringVar(value="Marker: (Klik pada plot FFT)")
        self.app_status_var = tk.StringVar(value="Ready")

        self.fft_scale_var.set("dB")
        self.shape_display_var.set("Sine")  # Set default display value
        self.shape_var.set("sine")  # Set default internal value
        self.mode_var.set("DSB-FC")
        self.demod_mode_var.set("Envelope")
        self.ac_var.set("1")
        self.fc_var.set("10k")
        self.fm_var.set("500")
        self.snr_var.set(50.0)
        self.m_var.set(0.7)
        self.am_var.set("0.700")

    def _setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=3)

        self.controls_panel = self._create_controls_panel(main_frame)
        self.controls_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        plot_panel = self._create_plot_panel(main_frame)
        plot_panel.grid(row=0, column=1, sticky="nsew")
        footer_frame = ttk.Frame(main_frame)
        footer_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(
            footer_frame, textvariable=self.app_status_var, relief=tk.SUNKEN
        ).pack(side=tk.LEFT, fill="x", expand=True)
        ttk.Label(
            footer_frame,
            text=FULL_CREDIT,
            font=("Helvetica", 8, "italic"),
            foreground="grey",
        ).pack(side=tk.RIGHT)
        self._bind_events()

    def _create_controls_panel(self, parent):
        panel = ttk.Frame(parent)
        notebook = ttk.Notebook(panel)
        notebook.pack(fill="x", expand=False)
        tab1, tab2, tab3 = (
            self._create_signal_tab(notebook),
            self._create_channel_tab(notebook),
            self._create_display_tab(notebook),
        )
        notebook.add(tab1, text="Sinyal")
        notebook.add(tab2, text="Kanal & Modulasi")
        notebook.add(tab3, text="Tampilan & Ekspor")
        analysis_frame = self._create_analysis_panel(panel)
        analysis_frame.pack(fill="x", expand=False, pady=10)
        return panel

    def _create_signal_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=10)
        tab.columnconfigure(0, weight=1)
        vcmd_float, vcmd_eng = (self.root.register(self.validate_float), "%P", "%W"), (
            self.root.register(self.validate_eng),
            "%P",
            "%W",
        )
        carrier_frame = ttk.LabelFrame(tab, text="Sinyal Carrier", padding=10)
        carrier_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        carrier_frame.columnconfigure(1, weight=1)
        ttk.Label(carrier_frame, text="Ac (V):").grid(
            row=0, column=0, sticky="w", pady=2
        )
        ttk.Entry(
            carrier_frame,
            name="ac_entry",
            textvariable=self.ac_var,
            width=12,
            validate="focusout",
            validatecommand=vcmd_float,
        ).grid(row=0, column=1, sticky="ew")
        ttk.Label(carrier_frame, text="fc (Hz):").grid(
            row=1, column=0, sticky="w", pady=2
        )
        ttk.Entry(
            carrier_frame,
            name="fc_entry",
            textvariable=self.fc_var,
            width=12,
            validate="focusout",
            validatecommand=vcmd_eng,
        ).grid(row=1, column=1, sticky="ew")

        msg_frame = ttk.LabelFrame(tab, text="Sinyal Pesan", padding=10)
        msg_frame.grid(row=1, column=0, sticky="ew")
        msg_frame.columnconfigure(1, weight=1)
        ttk.Label(msg_frame, text="Bentuk Sinyal:").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )

        # MODIFIED: Create OptionMenu from the centralized dictionary
        shape_menu = ttk.OptionMenu(
            msg_frame,
            self.shape_display_var,
            self.shape_display_var.get(),
            *self.SIGNAL_SHAPES.keys(),
        )
        shape_menu.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 5))

        ttk.Label(msg_frame, text="fm (Hz):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(
            msg_frame,
            name="fm_entry",
            textvariable=self.fm_var,
            width=12,
            validate="focusout",
            validatecommand=vcmd_eng,
        ).grid(row=2, column=1, sticky="ew")
        ttk.Label(msg_frame, text="Mod. Index (m):").grid(
            row=3, column=0, sticky="w", pady=2
        )
        ttk.Label(msg_frame, textvariable=self.m_var, font=self.FONT_BOLD).grid(
            row=3, column=1, sticky="w"
        )
        self.m_slider = ttk.Scale(
            msg_frame, from_=0, to=2.0, orient="h", variable=self.m_var
        )
        self.m_slider.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Label(msg_frame, text="Am (V):").grid(row=5, column=0, sticky="w", pady=2)
        ttk.Entry(
            msg_frame,
            name="am_entry",
            textvariable=self.am_var,
            width=12,
            validate="focusout",
            validatecommand=vcmd_float,
        ).grid(row=5, column=1, sticky="ew")
        return tab

    # ... The rest of the UI creation functions are unchanged ...
    def _create_channel_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=10)
        tab.columnconfigure(1, weight=1)
        ttk.Label(tab, text="Mode AM:").grid(row=0, column=0, sticky="w")
        ttk.OptionMenu(tab, self.mode_var, "DSB-FC", "DSB-FC", "DSB-SC").grid(
            row=0, column=1, sticky="ew", pady=(0, 5)
        )
        ttk.Label(tab, text="Demodulator:").grid(row=1, column=0, sticky="w")
        ttk.OptionMenu(
            tab, self.demod_mode_var, "Envelope", "Envelope", "Coherent"
        ).grid(row=1, column=1, sticky="ew", pady=(0, 5))
        self.phase_lbl = ttk.Label(tab, text="Phase Error (°):")
        self.phase_lbl.grid(row=2, column=0, sticky="w")
        self.phase_slider = ttk.Scale(
            tab, from_=-180, to=180, orient="h", variable=self.phase_error_var
        )
        self.phase_slider.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Label(tab, text="SNR (dB):").grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Scale(tab, from_=0, to=50, orient="h", variable=self.snr_var).grid(
            row=5, column=0, columnspan=2, sticky="ew"
        )
        return tab

    def _create_display_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=10)
        ttk.Label(tab, text="Preset:").grid(row=0, column=0, sticky="w")
        self.preset_menu = ttk.OptionMenu(
            tab,
            self.preset_var,
            self.preset_var.get(),
            *self.presets.keys(),
            command=self.load_preset,
        )
        self.preset_menu.grid(row=0, column=1, sticky="ew", pady=(0, 10))
        ttk.Label(tab, text="Skala FFT:").grid(row=1, column=0, sticky="w")
        ttk.OptionMenu(tab, self.fft_scale_var, "dB", "dB", "Linear").grid(
            row=1, column=1, sticky="ew"
        )
        check_button_class = (
            tb.Checkbutton if TTK_BOOTSTRAP_ENABLED else ttk.Checkbutton
        )
        check_button_class(
            tab, text="Pause Update", variable=self.pause_update_var
        ).grid(row=2, column=0, columnspan=2, pady=10)
        self.manual_update_button = ttk.Button(
            tab, text="Update Manual", command=self.on_param_change
        )
        self.manual_update_button.grid(row=3, column=0)
        ttk.Button(tab, text="Export Plot...", command=self.export_plot).grid(
            row=3, column=1
        )
        ttk.Button(tab, text="Reset to Default", command=self._reset_to_default).grid(
            row=4, column=0, columnspan=2, pady=(10, 0)
        )
        return tab

    def _create_analysis_panel(self, parent):
        frame = ttk.LabelFrame(parent, text="Analisis & Insights", padding="10")
        self.status_label = ttk.Label(
            frame, textvariable=self.status_var, font=self.FONT_BOLD
        )
        self.status_label.grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(frame, text="Bandwidth (BW):").grid(row=1, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.bandwidth_var).grid(
            row=1, column=1, sticky="w"
        )
        ttk.Label(frame, text="Efisiensi (η):").grid(row=2, column=0, sticky="w")
        ttk.Label(frame, textvariable=self.efficiency_var, font=self.FONT_BOLD).grid(
            row=2, column=1, sticky="w"
        )
        thd_label = ttk.Label(frame, text="THD (Demod):")
        thd_label.grid(row=3, column=0, sticky="w")
        ToolTip(thd_label, "Total Harmonic Distortion pada sinyal hasil demodulasi.")
        ttk.Label(frame, textvariable=self.thd_var, font=self.FONT_BOLD).grid(
            row=3, column=1, sticky="w"
        )
        ttk.Separator(frame, orient="h").grid(row=4, columnspan=2, sticky="ew", pady=5)
        ttk.Label(
            frame,
            textvariable=self.insights_var,
            wraplength=300,
            justify=tk.LEFT,
            font=self.FONT_ITALIC,
        ).grid(row=5, columnspan=2, sticky="w")
        return frame

    def _create_plot_panel(self, parent):
        panel = ttk.Frame(parent)
        panel.rowconfigure(0, weight=1)
        panel.columnconfigure(0, weight=1)
        self.fig, self.axs_all = plt.subplots(
            5, 1, figsize=(9, 8), constrained_layout=True
        )
        self.axs, self.ax_fft = self.axs_all[:4], self.axs_all[4]
        self.canvas = FigureCanvasTkAgg(self.fig, master=panel)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
        toolbar = NavigationToolbar2Tk(self.canvas, panel, pack_toolbar=False)
        toolbar.grid(row=1, column=0, sticky="ew")

        fft_ctrl = ttk.Frame(panel)
        fft_ctrl.grid(row=2, column=0, sticky="ew", pady=5)
        ttk.Label(fft_ctrl, text="Center:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(fft_ctrl, textvariable=self.fft_center_var, width=10).pack(
            side=tk.LEFT
        )
        ttk.Label(fft_ctrl, text="Span:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Entry(fft_ctrl, textvariable=self.fft_span_var, width=10).pack(side=tk.LEFT)
        ttk.Label(
            fft_ctrl, textvariable=self.marker_info_var, font=("Consolas", 9)
        ).pack(side=tk.RIGHT, padx=10)

        self.lines = []
        labels, colors = ["Pesan (msg)", "Carrier", "Sinyal Kanal", "Demodulasi"], [
            "blue",
            "orange",
            "purple",
            "red",
        ]
        for ax, lbl, color in zip(self.axs, labels, colors):
            (ln,) = ax.plot([], [], label=lbl, color=color)
            self.lines.append(ln)
        (scaled_ln,) = self.axs[3].plot(
            [], [], "g--", alpha=0.7, label="Pesan Asli (scaled)"
        )
        self.lines.append(scaled_ln)
        (self.overmodulation_line,) = self.axs[3].plot(
            [], [], "r--", alpha=0.8, label="Original Envelope"
        )
        (self.fft_line,) = self.ax_fft.plot([], [], "c")
        self.fft_marker = self.ax_fft.axvline(0, color="r", ls="--", alpha=0.7)
        for ax in self.axs:
            ax.legend(fontsize="small")
            ax.set_ylabel("Amplitudo (V)")
        self.ax_fft.set_ylabel("Magnitudo")
        self.fft_annotations = [
            self.ax_fft.annotate(
                "",
                xy=(0, 0),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
                color="orange",
            )
            for _ in range(3)
        ]
        return panel

    def _bind_events(self):
        # NEW: Callback to link the display shape to the internal shape value
        self.shape_display_var.trace_add("write", self._update_shape_from_display)

        # MODIFIED: Trace the internal shape_var for calculations
        for var in [
            self.ac_var,
            self.fc_var,
            self.fm_var,
            self.shape_var,
            self.mode_var,
            self.demod_mode_var,
            self.fft_scale_var,
            self.fft_center_var,
            self.fft_span_var,
            self.am_var,
        ]:
            var.trace_add("write", self.on_param_change)

        self.m_var.trace_add("write", self._update_am_from_m)
        self.am_var.trace_add("write", self._update_m_from_am)
        for slider_var in (self.m_var, self.phase_error_var, self.snr_var):
            slider_var.trace_add("write", self.on_param_change)
        self.demod_mode_var.trace_add("write", self.toggle_phase_controls)
        self.fig.canvas.mpl_connect("button_press_event", self.on_fft_click)
        self.toggle_phase_controls()

    # NEW: Handler to synchronize internal shape value when UI display changes
    def _update_shape_from_display(self, *args):
        display_value = self.shape_display_var.get()
        internal_value = self.SIGNAL_SHAPES.get(display_value)
        if internal_value and internal_value != self.shape_var.get():
            self.shape_var.set(internal_value)

    def load_preset(self, preset_name):
        if self.presets.get(preset_name) is None:
            self.preset_var.set(self.previous_preset)
            return

        self.previous_preset = preset_name
        params = self.presets[preset_name]

        self._is_updating_internally = True

        # MODIFIED: Loop through params and update all corresponding UI variables
        for key, value in params.items():
            if key == "shape":
                # Special handling for shape to update the display variable
                for display_name, internal_name in self.SIGNAL_SHAPES.items():
                    if internal_name == value:
                        self.shape_display_var.set(display_name)
                        break
            elif hasattr(self, f"{key}_var"):
                # Generic handling for all other variables (m_var, fc_var, etc.)
                var = getattr(self, f"{key}_var")
                var.set(value)

        self._is_updating_internally = False

        # Manually trigger updates for dependent variables
        self.am_var.set(
            f"{params.get('m', 0.7) * self.parse_input(params.get('ac', '1')):.3f}"
        )

        fc = self.parse_input(params.get("fc", "10k"))
        fm = self.parse_input(params.get("fm", "500"))

        self.fft_center_var.set(EngFormatter(unit="Hz")(fc))

        # Adjust span for dual tone
        shape = params.get("shape", "sine")
        span_mult = 12 if shape == "square" else (8 if shape == "dual_tone" else 4)
        span = span_mult * fm
        self.fft_span_var.set(EngFormatter(unit="Hz")(span))

        self.start_calculation()

    # ... The rest of the code is unchanged until _update_plots ...
    # on_param_change, _update_am_from_m, _update_m_from_am, validators, etc. are identical

    def on_param_change(self, *args):
        if self._is_updating_internally:
            return
        if self.pause_update_var.get() and args:
            return
        if self._debounce_timer:
            self.root.after_cancel(self._debounce_timer)
        self._debounce_timer = self.root.after(
            self.DEBOUNCE_TIME_MS, self.start_calculation
        )

    def _update_am_from_m(self, *args):
        if self._is_updating_internally:
            return
        self._is_updating_internally = True
        try:
            self.am_var.set(f"{self.m_var.get() * float(self.ac_var.get()):.3f}")
        except (ValueError, tk.TclError):
            pass
        self._is_updating_internally = False

    def _update_m_from_am(self, *args):
        if self._is_updating_internally:
            return
        self._is_updating_internally = True
        try:
            ac = float(self.ac_var.get())
            if ac > 0:
                self.m_var.set(round(float(self.am_var.get()) / ac, 3))
        except (ValueError, tk.TclError):
            pass
        self._is_updating_internally = False

    def validate_float(self, v, w):
        widget = self.root.nametowidget(w)
        name = widget.winfo_name().replace("_entry", "").upper()
        try:
            float(v)
            widget.config(style="TEntry")
            return True
        except ValueError:
            widget.config(style="Invalid.TEntry")
            self.app_status_var.set(f"Error: {name} must be a number.")
            return False

    def validate_eng(self, v, w):
        widget = self.root.nametowidget(w)
        name = widget.winfo_name().replace("_entry", "").upper()
        if not str(v).strip():
            widget.config(style="TEntry")
            return True
        try:
            self.parse_input(v)
            widget.config(style="TEntry")
            return True
        except (ValueError, IndexError):
            widget.config(style="Invalid.TEntry")
            self.app_status_var.set(f"Error: Invalid value for {name}.")
            return False

    def toggle_phase_controls(self, *args):
        s = "normal" if self.demod_mode_var.get() == "Coherent" else "disabled"
        self.phase_lbl.config(state=s)
        self.phase_slider.config(state=s)

    def _reset_to_default(self):
        self.load_preset("Default (Modulasi Baik)")

    def export_plot(self):
        fp = filedialog.asksaveasfilename(
            defaultextension=".png", filetypes=[("PNG", "*.png"), ("SVG", "*.svg")]
        )
        if fp:
            self.fig.savefig(fp, dpi=300, bbox_inches="tight")
            self.app_status_var.set(f"Plot saved to {fp}")

    def parse_input(self, s):
        s = str(s).strip().lower().replace("hz", "").strip()
        mult = {"k": 1e3, "m": 1e6, "g": 1e9}
        if not s:
            raise ValueError("Input string is empty")
        return float(s[:-1]) * mult[s[-1]] if s and s[-1] in mult else float(s)

    def on_fft_click(self, event):
        if event.inaxes != self.ax_fft:
            return
        x, y = event.xdata, event.ydata
        self.fft_marker.set_xdata([x])
        unit = "dB" if self.fft_scale_var.get() == "dB" else "V"
        self.marker_info_var.set(
            f"Marker: {EngFormatter(unit='Hz')(x)} @ {y:.2f} {unit}"
        )
        self.canvas.draw_idle()

    def start_calculation(self):
        if self.is_calculating:
            self.app_status_var.set("Calculation in progress, please wait...")
            return

        self.is_calculating = True
        self._set_ui_state(tk.DISABLED)
        self.app_status_var.set("Calculating...")

        params = self._parse_inputs()
        if params is None:
            self.app_status_var.set(
                "Error: Input tidak valid. Periksa nilai yang ditandai merah."
            )
            self._set_ui_state(tk.NORMAL)
            self.is_calculating = False
            return

        thread = threading.Thread(
            target=self._calculation_worker, args=(params,), daemon=True
        )
        thread.start()

    def _calculation_worker(self, params):
        try:
            signals = self._generate_signals(params)
            self.calculation_queue.put({"params": params, "signals": signals})
        except Exception as e:
            self.calculation_queue.put({"error": str(e)})

    def _check_calculation_queue(self):
        try:
            result = self.calculation_queue.get_nowait()
            if "error" in result:
                self.app_status_var.set(f"Calculation Error: {result['error']}")
            else:
                self._process_calculation_result(result)

            self._set_ui_state(tk.NORMAL)
            self.is_calculating = False
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._check_calculation_queue)

    def _process_calculation_result(self, result):
        self.signals = result["signals"]
        self._update_plots(result["params"], self.signals)
        self._update_analysis(result["params"], self.signals)
        self.app_status_var.set("Ready")

    def _set_ui_state(self, state):
        self.root.config(cursor="watch" if state == tk.DISABLED else "")
        for widget in self.controls_panel.winfo_children():
            try:
                widget.config(state=state)
                if isinstance(widget, (ttk.Frame, ttk.LabelFrame, ttk.Notebook)):
                    for child in widget.winfo_children():
                        self._set_widget_state_recursively(child, state)
            except tk.TclError:
                pass
        if self.pause_update_var.get():
            self.manual_update_button.config(state=tk.NORMAL)

    def _set_widget_state_recursively(self, parent_widget, state):
        try:
            parent_widget.config(state=state)
        except tk.TclError:
            pass
        for child in parent_widget.winfo_children():
            self._set_widget_state_recursively(child, state)

    def _parse_inputs(self):
        try:
            p = {
                "Ac": float(self.ac_var.get()),
                "Am": float(self.am_var.get()),
                "fc": self.parse_input(self.fc_var.get()),
                "fm": self.parse_input(self.fm_var.get()),
                "shape": self.shape_var.get(),
                "mode": self.mode_var.get(),
                "snr_db": float(self.snr_var.get()),
                "fft_scale": self.fft_scale_var.get(),
                "demod_mode": self.demod_mode_var.get(),
                "phase_error": float(self.phase_error_var.get()),
            }
            try:
                p["fft_center"] = (
                    self.parse_input(s)
                    if (s := str(self.fft_center_var.get()).strip()) != ""
                    else p["fc"]
                )
            except (ValueError, IndexError):
                p["fft_center"] = p["fc"]
            try:
                shape = p["shape"]
                mult = 12 if shape == "square" else (8 if shape == "dual_tone" else 4)
                p["fft_span"] = (
                    self.parse_input(s)
                    if (s := str(self.fft_span_var.get()).strip()) != ""
                    else mult * p["fm"]
                )
            except (ValueError, IndexError):
                shape = p["shape"]
                mult = 12 if shape == "square" else (8 if shape == "dual_tone" else 4)
                p["fft_span"] = mult * p["fm"]
            if (
                any(v <= 0 for v in [p["fc"], p["fm"], p["Ac"], p["fft_span"]])
                or p["Am"] < 0
            ):
                return None
            p["m"] = p["Am"] / p["Ac"] if p["Ac"] > 0 else float("inf")
            return p
        except (ValueError, tk.TclError):
            return None

    def _generate_signals(self, p):
        MAX_SAMPLING_RATE = 10e6
        required_sr = max(5 * p["fc"], 20 * p["fm"], 44100)
        if p["shape"] == "dual_tone":
            required_sr = max(
                required_sr, 20 * (3 * p["fm"])
            )  # For higher harmonic of dual_tone

        if required_sr > MAX_SAMPLING_RATE:
            max_fc_str = EngFormatter(unit="Hz")(MAX_SAMPLING_RATE / 5)
            raise ValueError(
                f"Frekuensi Carrier terlalu tinggi. Coba nilai di bawah {max_fc_str}."
            )

        sr = required_sr
        t = self.processor.gen_time_vector(2.0, sr, self.MAX_SAMPLES * 2)
        msg = self.processor.gen_message_signal(t, p["Am"], p["fm"], p["shape"])
        carrier = self.processor.gen_carrier_signal(t, p["Ac"], p["fc"])
        mod = self.processor.modulate(msg, carrier, p["Ac"], p["mode"])
        noisy = self.processor.add_noise(mod, p["snr_db"])
        demod_func = (
            self.processor.coherent_demodulate
            if p["demod_mode"] == "Coherent"
            else self.processor.envelope_demodulate
        )
        demod = (
            demod_func(noisy, t, p["fc"], p["phase_error"], p["fm"], sr)
            if p["demod_mode"] == "Coherent"
            else demod_func(noisy, p["fm"], sr)
        )

        plot_samples = int((5 / p["fm"]) * sr)
        plot_samples = min(plot_samples, len(mod), self.MAX_SAMPLES)

        fft_samples = min(len(mod), 2**16)
        freq, mag_lin, mag_db = self.processor.calc_fft(mod[:fft_samples], sr)
        thd = self.processor.calculate_thd(demod, p["fm"], sr)

        return {
            "t": t,
            "msg": msg,
            "carrier": carrier,
            "noisy": noisy,
            "demod": demod,
            "freq": freq,
            "mag_lin": mag_lin,
            "mag_db": mag_db,
            "thd": thd,
            "sr": sr,
            "plot_samples": plot_samples,
        }

    def _update_plots(self, p, s):
        for btn in self.play_buttons:
            btn.destroy()
        self.play_buttons.clear()

        t_plot = s["t"][: s["plot_samples"]]
        self.lines[0].set_data(t_plot, s["msg"][: s["plot_samples"]])
        self.lines[1].set_data(t_plot, s["carrier"][: s["plot_samples"]])
        self.lines[2].set_data(t_plot, s["noisy"][: s["plot_samples"]])
        self.lines[3].set_data(t_plot, s["demod"][: s["plot_samples"]])

        max_demod = (
            np.max(np.abs(s["demod"][: s["plot_samples"]]))
            if s["plot_samples"] > 0
            else 1
        )
        max_msg = (
            np.max(np.abs(s["msg"][: s["plot_samples"]]))
            if s["plot_samples"] > 0
            else 1
        )
        scaled_msg = (
            s["msg"][: s["plot_samples"]] * (max_demod / max_msg)
            if max_msg > 1e-9
            else s["msg"][: s["plot_samples"]]
        )
        self.lines[4].set_data(t_plot, scaled_msg)

        # MODIFIED: Add analytical envelope to the modulated signal plot for clarity at high fc
        if not hasattr(self, "envelope_lines"):
            (line_pos,) = self.axs[2].plot(
                [], [], "r--", linewidth=1, alpha=0.9, label="Envelope"
            )
            (line_neg,) = self.axs[2].plot([], [], "r--", linewidth=1, alpha=0.9)
            self.envelope_lines = (line_pos, line_neg)

        if p["mode"] == "DSB-FC":
            envelope_pos = p["Ac"] + s["msg"][: s["plot_samples"]]
            envelope_neg = -(p["Ac"] + s["msg"][: s["plot_samples"]])
            self.envelope_lines[0].set_data(t_plot, envelope_pos)
            self.envelope_lines[1].set_data(t_plot, envelope_neg)
        else:  # Hide for DSB-SC
            self.envelope_lines[0].set_data([], [])
            self.envelope_lines[1].set_data([], [])

        self.overmodulation_line.set_visible(p["m"] > 1 and p["mode"] == "DSB-FC")
        if self.overmodulation_line.get_visible():
            self.overmodulation_line.set_data(t_plot, np.abs(scaled_msg))

        y_fft = s["mag_db"] if p["fft_scale"] == "dB" else s["mag_lin"]
        self.fft_line.set_data(s["freq"], y_fft)

        time_limit = t_plot[-1] if len(t_plot) > 0 else 0.005

        for ax in self.axs:
            ax.relim()
            ax.autoscale_view(scaley=True)
            ax.set_xlim(0, time_limit)
            ax.xaxis.set_major_formatter(EngFormatter(unit="s"))
            ax.set_xlabel("Waktu (s)")
            ax.legend(fontsize="small")

        self.ax_fft.set_xlim(
            p["fft_center"] - p["fft_span"] / 2, p["fft_center"] + p["fft_span"] / 2
        )
        try:
            mask = (s["freq"] >= self.ax_fft.get_xlim()[0]) & (
                s["freq"] <= self.ax_fft.get_xlim()[1]
            )
            y_vis = y_fft[mask]
            if len(y_vis) > 0:
                y_min, y_max = np.min(y_vis), np.max(y_vis)
                self.ax_fft.set_ylim(
                    y_min - 0.1 * (y_max - y_min), y_max + 0.1 * (y_max - y_min)
                )
            else:
                self.ax_fft.autoscale_view()
        except (ValueError, IndexError):
            self.ax_fft.relim()
            self.ax_fft.autoscale_view()

        self._update_plot_titles_and_audio(p)
        self._update_fft_annotations(p, s, y_fft)
        self.canvas.draw_idle()

    # ... The rest of the file is identical ...
    def _update_plot_titles_and_audio(self, p):
        titles = [
            "1. Sinyal Pesan (Message)",
            "2. Sinyal Pembawa (Carrier)",
            f'3. Sinyal Termodulasi di Kanal (SNR: {p["snr_db"]:.0f}dB)',
            f'4. Hasil Demodulasi ({p["demod_mode"]})',
        ]
        master_canvas = self.canvas.get_tk_widget()

        for i, (ax, title) in enumerate(zip(self.axs, titles)):
            ax.set_title(title, loc="left", fontsize=10)
            if AUDIO_ENABLED and i in [0, 3] and 20 < p["fm"] < 20000:
                btn = ttk.Button(
                    master_canvas,
                    text="▶ Play",
                    command=lambda sig_type=i: self._play_audio(sig_type),
                    width=8,
                )
                bbox = ax.get_position()
                btn.place(relx=bbox.x1, rely=1 - bbox.y1, x=-5, y=5, anchor="ne")
                self.play_buttons.append(btn)

        self.ax_fft.set_title("5. Spektrum Frekuensi (Zoom)", loc="left", fontsize=10)
        self.ax_fft.xaxis.set_major_formatter(EngFormatter(unit="Hz"))
        self.ax_fft.set_xlabel("Frekuensi (Hz)")

    def _update_fft_annotations(self, p, s, y_fft):
        if p["shape"] == "dual_tone":
            freqs = {
                "fc": p["fc"],
                "LSB1": p["fc"] - p["fm"],
                "USB1": p["fc"] + p["fm"],
                "LSB2": p["fc"] - 3 * p["fm"],
                "USB2": p["fc"] + 3 * p["fm"],
            }
        else:
            freqs = {"fc": p["fc"], "LSB": p["fc"] - p["fm"], "USB": p["fc"] + p["fm"]}

        # Hide all annotations first
        for ann in self.fft_annotations:
            ann.set_visible(False)
        # Resize if needed
        while len(self.fft_annotations) < len(freqs):
            self.fft_annotations.append(
                self.ax_fft.annotate(
                    "",
                    xy=(0, 0),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color="orange",
                )
            )

        for i, (label, freq) in enumerate(freqs.items()):
            ann = self.fft_annotations[i]
            if (
                len(s["freq"]) > 0
                and self.ax_fft.get_xlim()[0] < freq < self.ax_fft.get_xlim()[1]
            ):
                idx = np.argmin(np.abs(s["freq"] - freq))
                ann.set_text(label)
                ann.xy = (freq, y_fft[idx])
                ann.set_visible(True)

    def _update_analysis(self, p, s):
        status = (
            "Undermodulation"
            if p["m"] < 0.99
            else "100% Modulation" if p["m"] <= 1.01 else "Overmodulation"
        )
        colors = {
            "Undermodulation": "blue",
            "100% Modulation": "green",
            "Overmodulation": "red",
        }
        self.status_label.config(foreground=colors.get(status, "black"))
        self.status_var.set(f"m: {p['m']:.2f} | {status}")
        power = self.processor.calc_power(p["Ac"], p["m"], p["mode"])
        self.efficiency_var.set(f"{power['eff']:.2f}%")
        bw_mult = 6 if p["shape"] == "dual_tone" else 2
        self.bandwidth_var.set(EngFormatter(unit="Hz")(bw_mult * p["fm"]))
        self.thd_var.set(f"{s['thd']:.2f} %" if s["thd"] < 100 else ">100%")
        ins = []
        if p["m"] > 1:
            ins.append(
                f"Overmodulation terdeteksi. Coba kurangi 'm' di bawah 1.0 untuk menghilangkan distorsi (THD: {s['thd']:.1f}%)."
            )
        elif p["mode"] == "DSB-SC":
            ins.append(
                "Mode DSB-SC sangat efisien, namun memerlukan demodulator Coherent yang presisi."
            )
        elif p["demod_mode"] == "Coherent" and abs(p["phase_error"]) > 5:
            ins.append(
                f"Kesalahan fasa {p['phase_error']:.0f}° menyebabkan atenuasi. Coba setel Phase Error mendekati 0°."
            )
        elif p["snr_db"] < 15:
            ins.append(
                "SNR rendah menyebabkan noise. Coba tingkatkan SNR untuk sinyal yang lebih bersih."
            )
        else:
            ins.append(
                "Kondisi modulasi ideal. Sinyal ditransmisikan dan diterima dengan fidelitas tinggi."
            )
        self.insights_var.set("INSIGHT: " + textwrap.fill(ins[0], width=50))

    def _play_audio(self, signal_type):
        if not AUDIO_ENABLED:
            self.app_status_var.set("Error: Pustaka 'sounddevice' tidak ditemukan.")
            return
        signal_data = self.signals["msg"] if signal_type == 0 else self.signals["demod"]
        if signal_data is None or len(signal_data) == 0:
            return
        try:
            norm_sig = signal_data / (np.max(np.abs(signal_data)) + 1e-9)
            sd.stop()
            sd.play(norm_sig.astype(np.float32), int(self.signals["sr"]))
        except Exception as e:
            self.app_status_var.set(f"Kesalahan pemutaran audio: {e}")


if __name__ == "__main__":
    if TTK_BOOTSTRAP_ENABLED:
        root = tb.Window(themename="cosmo")
    else:
        print(
            "Peringatan: ttkbootstrap tidak ditemukan. Menggunakan fallback tkinter standar."
        )
        print(
            "Untuk tampilan yang lebih baik, install dengan: pip install ttkbootstrap"
        )
        root = tk.Tk()
    app = AMSimulatorGUI(root)
    root.mainloop()
