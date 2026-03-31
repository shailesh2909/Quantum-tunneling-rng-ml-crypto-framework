"""
Randomness Security Analyzer
══════════════════════════════════════════════════════════
Premium desktop dashboard — Apple HIG‑inspired dark UI.
Quantum tunneling + Cryptographic Entropy Evaluation.
"""

import tkinter as tk
from tkinter import ttk, filedialog
import threading
import os
import math
import time
import secrets

import numpy as np
import pandas as pd
import joblib

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from features import extract_features
from crypto_engine import (
    bits_to_key, key_to_hex, hex_to_key,
    encrypt_file, decrypt_file,
    save_key_to_file, load_key_from_file,
)

# ═══════════════════════════════════════════════════════════════
#  DESIGN TOKENS  (Apple‑inspired dark palette)
# ═══════════════════════════════════════════════════════════════
BG            = "#0b0f1a"          # deepest background
SURFACE       = "#111827"          # card / panel fill
SURFACE_ALT   = "#151d2e"          # slightly lighter surface
ELEVATED      = "#1a2332"          # hover / elevated surface
BORDER        = "#1f2937"          # very subtle borders
BORDER_HOVER  = "#374151"          # border on hover

ACCENT        = "#3b82f6"          # soft blue
ACCENT_DIM    = "#2563eb"
ACCENT_GLOW   = "#60a5fa"
SUCCESS       = "#22c55e"
SUCCESS_DIM   = "#16a34a"
ERROR         = "#ef4444"
ERROR_DIM     = "#dc2626"
WARN          = "#f59e0b"

TEXT          = "#f1f5f9"          # primary text
TEXT_SEC      = "#94a3b8"          # secondary text
TEXT_MUTED    = "#475569"          # muted / placeholder

# 8px grid
S = 8                              # spacing unit
PAD = S * 3                        # standard card padding (24)
GAP = S * 2                        # gap between cards (16)

FONT_FAMILY   = "Segoe UI"
MONO          = "Consolas"


# ═══════════════════════════════════════════════════════════════
#  UTILITIES
# ═══════════════════════════════════════════════════════════════

def lerp_hex(a: str, b: str, t: float) -> str:
    """Linear interpolation between two hex colours, t ∈ [0, 1]."""
    t = max(0.0, min(1.0, t))
    ra, ga, ba = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    rb, gb, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return f"#{int(ra+(rb-ra)*t):02x}{int(ga+(gb-ga)*t):02x}{int(ba+(bb-ba)*t):02x}"


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


# ═══════════════════════════════════════════════════════════════
#  REUSABLE WIDGETS
# ═══════════════════════════════════════════════════════════════

class Card(tk.Frame):
    """
    A surface‑elevated card with a 1px border that brightens on hover.
    Uses a thin outer frame as the rounded‑border illusion.
    """

    def __init__(self, master, **kw):
        super().__init__(master, bg=BORDER, padx=1, pady=1, **kw)
        self.inner = tk.Frame(self, bg=SURFACE)
        self.inner.pack(fill="both", expand=True)
        self.bind("<Enter>", lambda _: self.configure(bg=BORDER_HOVER))
        self.bind("<Leave>", lambda _: self.configure(bg=BORDER))
        self.inner.bind("<Enter>", lambda _: self.configure(bg=BORDER_HOVER))
        self.inner.bind("<Leave>", lambda _: self.configure(bg=BORDER))


class SectionTitle(tk.Label):
    """Consistent section header label."""

    def __init__(self, master, text, **kw):
        super().__init__(master, text=text, bg=SURFACE, fg=TEXT_SEC,
                         font=(FONT_FAMILY, 10, "bold"), anchor="w", **kw)


class PillButton(tk.Canvas):
    """
    A pill‑shaped button drawn on a Canvas.
    Hover: smooth colour transition.  Disabled: dimmed.
    """

    WIDTH  = 220
    HEIGHT = 40
    RADIUS = 12

    def __init__(self, master, text="Button", command=None,
                 accent=ACCENT, width=None, height=None, **kw):
        w = width or self.WIDTH
        h = height or self.HEIGHT
        super().__init__(master, width=w, height=h,
                         bg=SURFACE, highlightthickness=0, **kw)
        self._bw, self._bh = w, h
        self._accent = accent
        self._text = text
        self._cmd = command
        self._disabled = False
        self._hover_t = 0.0        # 0 = rest, 1 = fully hovered
        self._target_t = 0.0
        self._animating = False

        self._render()
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.bind("<ButtonRelease-1>", self._on_release)

    # ── drawing ─────────────────
    def _pill(self, x1, y1, x2, y2, r, **opts):
        pts = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r,
               x2, y2-r, x2, y2, x2-r, y2, x1+r, y2,
               x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        return self.create_polygon(pts, smooth=True, **opts)

    def _render(self):
        self.delete("all")
        t = self._hover_t
        fill = lerp_hex(SURFACE_ALT, self._accent, t)
        outline = lerp_hex(BORDER_HOVER, self._accent, t)
        fg = lerp_hex(self._accent, "#ffffff", t)
        if self._disabled:
            fill = SURFACE_ALT
            outline = BORDER
            fg = TEXT_MUTED
        self._pill(2, 2, self._bw - 2, self._bh - 2, self.RADIUS,
                   fill=fill, outline=outline, width=1)
        self.create_text(self._bw // 2, self._bh // 2,
                         text=self._text, fill=fg,
                         font=(FONT_FAMILY, 10, "bold"))

    # ── hover animation ─────────
    def _animate(self):
        if not self._animating:
            return
        diff = self._target_t - self._hover_t
        if abs(diff) < 0.02:
            self._hover_t = self._target_t
            self._animating = False
        else:
            self._hover_t += diff * 0.22
        self._render()
        if self._animating:
            self.after(16, self._animate)

    def _start_anim(self, target):
        self._target_t = target
        if not self._animating:
            self._animating = True
            self._animate()

    def _on_enter(self, _=None):
        if not self._disabled:
            self._start_anim(1.0)
            self.configure(cursor="hand2")

    def _on_leave(self, _=None):
        self._start_anim(0.0)
        self.configure(cursor="")

    def _on_click(self, _=None):
        if self._disabled or not self._cmd:
            return
        # brief press flash
        self._hover_t = 0.7
        self._render()

    def _on_release(self, _=None):
        if self._disabled or not self._cmd:
            return
        self._cmd()

    def set_disabled(self, v: bool):
        self._disabled = v
        self._hover_t = 0.0
        self._target_t = 0.0
        self._render()


class MetricTile(tk.Frame):
    """A single metric: small label on top, large coloured value beneath."""

    def __init__(self, master, label, accent=ACCENT):
        super().__init__(master, bg=SURFACE_ALT, padx=PAD // 2, pady=S * 2)
        self._accent = accent
        tk.Label(self, text=label, bg=SURFACE_ALT, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, 9)).pack(anchor="w")
        self.val_lbl = tk.Label(self, text="—", bg=SURFACE_ALT, fg=accent,
                                font=(MONO, 20, "bold"))
        self.val_lbl.pack(anchor="w", pady=(4, 0))

    def set(self, v: str):
        self.val_lbl.configure(text=v)

    def reset(self):
        self.val_lbl.configure(text="—")


class GraphPopup:
    """
    Opens a Toplevel window showing a single graph at high resolution
    with a matplotlib NavigationToolbar (zoom, pan, save).
    """

    # graph_key: "distribution" | "transition" | "bitstream"
    def __init__(self, master, graph_key: str, bits):
        self.win = tk.Toplevel(master)
        self.win.title(self._title_for(graph_key))
        self.win.configure(bg=BG)
        self.win.minsize(800, 520)

        # centre relative to master
        sw, sh = master.winfo_screenwidth(), master.winfo_screenheight()
        w, h = 920, 600
        self.win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # ── header label ──
        tk.Label(self.win, text=self._title_for(graph_key), bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 14, "bold")).pack(
                     anchor="w", padx=PAD, pady=(PAD, S))
        tk.Frame(self.win, bg=BORDER, height=1).pack(fill="x", padx=PAD)

        # ── figure ──
        fig = Figure(figsize=(9, 5), dpi=110, facecolor=SURFACE)
        ax = fig.add_subplot(111)
        _style_single_ax(ax)
        _render_graph(ax, graph_key, bits)
        fig.tight_layout(pad=2.0)

        canvas = FigureCanvasTkAgg(fig, master=self.win)
        canvas.draw()

        # ── toolbar (dark‑ish) ──
        toolbar_frame = tk.Frame(self.win, bg=SURFACE)
        toolbar_frame.pack(fill="x", padx=PAD, pady=(S, 0))
        toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
        toolbar.update()
        toolbar.configure(background=SURFACE)
        for child in toolbar.winfo_children():
            try:
                child.configure(background=SURFACE)
            except Exception:
                pass

        canvas.get_tk_widget().pack(
            fill="both", expand=True, padx=PAD, pady=(S, PAD))

    @staticmethod
    def _title_for(key: str) -> str:
        return {
            "distribution": "Bit Distribution — Expanded View",
            "transition":   "Transition Probabilities — Expanded View",
            "bitstream":    "Bit Stream — Expanded View",
        }.get(key, "Graph")


# ═══════════════════════════════════════════════════════════════
#  STANDALONE GRAPH RENDERERS  (used by dashboard + popup)
# ═══════════════════════════════════════════════════════════════

def _style_single_ax(ax):
    """Apply the dark theme to a single matplotlib Axes."""
    ax.set_facecolor(BG)
    ax.tick_params(colors=TEXT_MUTED, labelsize=8, length=3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.title.set_color(TEXT_SEC)
    ax.xaxis.label.set_color(TEXT_MUTED)
    ax.yaxis.label.set_color(TEXT_MUTED)


def _render_graph(ax, key: str, bits, expanded=True):
    """Render the requested graph onto *ax* using *bits*."""
    arr = np.array(bits)
    n = len(arr)
    title_size = 12 if expanded else 9

    if key == "distribution":
        z = int(np.sum(arr == 0))
        o = n - z
        ax.set_title("Bit Distribution", fontsize=title_size, pad=10, color=TEXT_SEC)
        bars = ax.bar(["0", "1"], [z / n, o / n],
                      color=[ACCENT_DIM, ACCENT], alpha=0.80,
                      edgecolor=ACCENT_GLOW, linewidth=0.6, width=0.45)
        ax.set_ylim(0, 1)
        ax.set_ylabel("Proportion", fontsize=9, color=TEXT_MUTED)
        for bar, val in zip(bars, [z / n, o / n]):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.025,
                    f"{val:.4f}", ha="center", va="bottom",
                    color=TEXT, fontsize=9 if expanded else 8)
        if expanded:
            ax.set_xlabel(f"Total bits: {n:,}", fontsize=9, color=TEXT_MUTED)

    elif key == "transition":
        t00 = t01 = t10 = t11 = 0
        for i in range(n - 1):
            a, b = arr[i], arr[i + 1]
            if   a == 0 and b == 0: t00 += 1
            elif a == 0 and b == 1: t01 += 1
            elif a == 1 and b == 0: t10 += 1
            else:                   t11 += 1
        tot = t00 + t01 + t10 + t11
        mat = np.array([[t00, t01], [t10, t11]]) / max(tot, 1)
        ax.set_title("Transition Probabilities", fontsize=title_size, pad=10, color=TEXT_SEC)
        ax.imshow(mat, cmap="cividis", vmin=0, vmax=0.5, aspect="auto")
        ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
        fs = 10 if expanded else 8
        ax.set_xticklabels(["→0", "→1"], fontsize=fs, color=TEXT_SEC)
        ax.set_yticklabels(["0→", "1→"], fontsize=fs, color=TEXT_SEC)
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{mat[i, j]:.4f}", ha="center", va="center",
                        fontsize=11 if expanded else 9, fontweight="bold",
                        color="white" if mat[i, j] < 0.3 else BG)

    elif key == "bitstream":
        count = 500 if expanded else 300
        vis = arr[-count:]
        ax.set_title(f"Bit Stream (last {len(vis)})", fontsize=title_size, pad=10, color=TEXT_SEC)
        colors = [ACCENT if b == 1 else ACCENT_DIM for b in vis]
        ax.bar(range(len(vis)), vis * 2 - 1,
               color=colors, width=1.0, linewidth=0)
        ax.set_ylim(-1.5, 1.5)
        ax.set_xlabel("Bit index", fontsize=9, color=TEXT_MUTED)
        ax.axhline(0, color=BORDER, linewidth=0.4)


# ═══════════════════════════════════════════════════════════════

class SpinnerCanvas(tk.Canvas):
    """
    Smooth arc‑spinner drawn on a Canvas.
    Starts/stops on demand.
    """

    def __init__(self, master, size=24, color=ACCENT, **kw):
        super().__init__(master, width=size, height=size,
                         bg=SURFACE, highlightthickness=0, **kw)
        self._sz = size
        self._color = color
        self._angle = 0
        self._running = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self):
        self._running = False
        self.delete("all")

    def _tick(self):
        if not self._running:
            return
        self.delete("all")
        pad = 3
        self.create_arc(pad, pad, self._sz - pad, self._sz - pad,
                        start=self._angle, extent=80,
                        style="arc", outline=self._color, width=2.5)
        # faint track
        self.create_arc(pad, pad, self._sz - pad, self._sz - pad,
                        start=0, extent=359.9,
                        style="arc", outline=BORDER, width=1.5)
        self._angle = (self._angle + 8) % 360
        self.after(25, self._tick)


# ═══════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════

class RandomnessAnalyzer:
    """Apple‑HIG‑inspired Randomness Security Analyzer."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Randomness Security Analyzer")
        self.root.configure(bg=BG)
        self.root.minsize(1140, 880)

        # centre on screen
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = 1200, 940
        root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        # ── state ──
        self._bits = None
        self._features = None
        self._predictions = None
        self._collecting = False
        self._aes_key = None           # 32‑byte AES key
        self._randomness_good = False  # gate for encryption

        # ── load ML model ──
        model_path = os.path.join(os.path.dirname(__file__), "model.pkl")
        try:
            self.model = joblib.load(model_path)
        except Exception:
            self.model = None

        # ── configure ttk styles ──
        self._setup_styles()

        # ── build UI ──
        self._build_header()

        # scrollable body
        self._body = tk.Frame(root, bg=BG)
        self._body.pack(fill="both", expand=True, padx=PAD + S, pady=(0, PAD))

        self._body.columnconfigure(0, weight=2, uniform="c")
        self._body.columnconfigure(1, weight=3, uniform="c")
        self._body.columnconfigure(2, weight=2, uniform="c")
        self._body.rowconfigure(0, weight=3)
        self._body.rowconfigure(1, weight=4)
        self._body.rowconfigure(2, weight=3)

        self._build_control_card()
        self._build_metrics_card()
        self._build_result_card()
        self._build_graph_card()
        self._build_crypto_card()

    # ─── styles ───────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure("App.Horizontal.TProgressbar",
                    troughcolor=BORDER, background=ACCENT,
                    darkcolor=ACCENT_DIM, lightcolor=ACCENT_GLOW,
                    bordercolor=SURFACE, thickness=4)
        s.configure("App.Horizontal.TSeparator", background=BORDER)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  HEADER
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG, height=80)
        hdr.pack(fill="x", padx=PAD + S, pady=(PAD, GAP))
        hdr.pack_propagate(False)

        # Shield icon
        icon = tk.Canvas(hdr, width=44, height=44, bg=BG, highlightthickness=0)
        icon.pack(side="left", padx=(0, S * 2))
        self._draw_shield(icon)

        # text
        txt = tk.Frame(hdr, bg=BG)
        txt.pack(side="left", fill="y", anchor="w")

        self._title_lbl = tk.Label(
            txt, text="Randomness Security Analyzer", bg=BG, fg=TEXT,
            font=(FONT_FAMILY, 20, "bold"))
        self._title_lbl.pack(anchor="w")

        tk.Label(txt, text="Quantum tunneling  ·  Cryptographic Entropy Evaluation",
                 bg=BG, fg=TEXT_SEC, font=(FONT_FAMILY, 11)).pack(anchor="w", pady=(2, 0))

        # thin accent line under header
        sep = tk.Canvas(self.root, height=1, bg=BG, highlightthickness=0)
        sep.pack(fill="x", padx=PAD + S)
        sep.create_line(0, 0, 3000, 0, fill=BORDER, width=1)

    @staticmethod
    def _draw_shield(cv):
        cx, cy = 22, 22
        # shield body
        cv.create_polygon(
            cx, 3, cx + 18, 10, cx + 16, 32, cx, 42,
            cx - 16, 32, cx - 18, 10,
            smooth=True, fill=ACCENT_DIM, outline=ACCENT, width=1.5)
        # lock rectangle
        cv.create_rectangle(cx - 6, cy - 1, cx + 6, cy + 9,
                            fill=BG, outline=ACCENT_GLOW, width=1)
        # shackle
        cv.create_arc(cx - 4, cy - 9, cx + 4, cy + 1,
                      start=0, extent=180, style="arc",
                      outline=ACCENT_GLOW, width=1.5)
        # keyhole dot
        cv.create_oval(cx - 1.5, cy + 1, cx + 1.5, cy + 4,
                       fill=ACCENT_GLOW, outline="")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  CONTROL CARD  (column 0, row 0)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_control_card(self):
        card = Card(self._body)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, GAP // 2), pady=(GAP, GAP // 2))
        inner = card.inner

        SectionTitle(inner, text="Controls").pack(
            anchor="w", padx=PAD, pady=(PAD, S))

        ttk.Separator(inner, orient="horizontal",
                       style="App.Horizontal.TSeparator").pack(fill="x", padx=PAD)

        btn_frame = tk.Frame(inner, bg=SURFACE)
        btn_frame.pack(fill="x", padx=PAD, pady=(GAP, 0))

        self.btn_collect = PillButton(btn_frame, text="Collect Data",
                                      command=self._on_collect, accent=ACCENT)
        self.btn_collect.pack(fill="x", pady=(0, S))

        self.btn_analyze = PillButton(btn_frame, text="Run Analysis",
                                      command=self._on_analyze, accent=SUCCESS)
        self.btn_analyze.pack(fill="x", pady=(0, S))

        self.btn_reset = PillButton(btn_frame, text="Reset",
                                    command=self._on_reset, accent=ERROR)
        self.btn_reset.pack(fill="x")

        # status row
        status_row = tk.Frame(inner, bg=SURFACE)
        status_row.pack(fill="x", padx=PAD, pady=(GAP, 0))

        self.spinner = SpinnerCanvas(status_row, size=20, color=ACCENT)
        self.spinner.pack(side="left", padx=(0, S))

        self.status_var = tk.StringVar(value="Idle")
        self.status_lbl = tk.Label(status_row, textvariable=self.status_var,
                                   bg=SURFACE, fg=TEXT_SEC,
                                   font=(FONT_FAMILY, 10))
        self.status_lbl.pack(side="left")

        # progress bar
        self.progress = ttk.Progressbar(
            inner, orient="horizontal", mode="indeterminate",
            style="App.Horizontal.TProgressbar", length=180)
        self.progress.pack(padx=PAD, pady=(S, PAD), fill="x")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  METRICS CARD  (column 1, row 0)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_metrics_card(self):
        card = Card(self._body)
        card.grid(row=0, column=1, sticky="nsew",
                  padx=(GAP // 2, GAP // 2), pady=(GAP, GAP // 2))
        inner = card.inner

        SectionTitle(inner, text="Metrics").pack(
            anchor="w", padx=PAD, pady=(PAD, S))
        ttk.Separator(inner, orient="horizontal",
                       style="App.Horizontal.TSeparator").pack(fill="x", padx=PAD)

        grid = tk.Frame(inner, bg=SURFACE)
        grid.pack(fill="both", expand=True, padx=PAD, pady=(GAP, PAD))
        grid.columnconfigure(0, weight=1, uniform="m")
        grid.columnconfigure(1, weight=1, uniform="m")

        self.m_entropy  = MetricTile(grid, "Entropy",        accent=ACCENT)
        self.m_mean     = MetricTile(grid, "Mean",           accent=ACCENT_GLOW)
        self.m_variance = MetricTile(grid, "Variance",       accent=ACCENT)
        self.m_autocorr = MetricTile(grid, "Autocorrelation",accent=ACCENT_GLOW)
        self.m_runlen   = MetricTile(grid, "Run Length",     accent=ACCENT)

        self.m_entropy.grid( row=0, column=0, sticky="nsew", padx=(0, S//2), pady=(0, S))
        self.m_mean.grid(    row=0, column=1, sticky="nsew", padx=(S//2, 0), pady=(0, S))
        self.m_variance.grid(row=1, column=0, sticky="nsew", padx=(0, S//2), pady=(0, S))
        self.m_autocorr.grid(row=1, column=1, sticky="nsew", padx=(S//2, 0), pady=(0, S))
        self.m_runlen.grid(  row=2, column=0, columnspan=2, sticky="nsew")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  RESULT CARD  (column 2, row 0)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_result_card(self):
        card = Card(self._body)
        card.grid(row=0, column=2, sticky="nsew",
                  padx=(GAP // 2, 0), pady=(GAP, GAP // 2))
        inner = card.inner

        SectionTitle(inner, text="Verdict").pack(
            anchor="w", padx=PAD, pady=(PAD, S))
        ttk.Separator(inner, orient="horizontal",
                       style="App.Horizontal.TSeparator").pack(fill="x", padx=PAD)

        # result label — visually dominant
        self.result_lbl = tk.Label(inner, text="AWAITING\nANALYSIS",
                                   bg=SURFACE, fg=TEXT_MUTED,
                                   font=(FONT_FAMILY, 20, "bold"),
                                   justify="center")
        self.result_lbl.pack(expand=True, pady=(GAP, 0))

        # glow canvas behind result (drawn dynamically)
        self._glow_cv = tk.Canvas(inner, height=6, bg=SURFACE, highlightthickness=0)
        self._glow_cv.pack(fill="x", padx=PAD * 2, pady=(0, S))

        # chunk counts
        counts = tk.Frame(inner, bg=SURFACE)
        counts.pack(padx=PAD, pady=(0, PAD), fill="x")
        self.good_lbl = tk.Label(counts, text="Good chunks: —", bg=SURFACE,
                                 fg=SUCCESS, font=(MONO, 10))
        self.good_lbl.pack(anchor="w")
        self.weak_lbl = tk.Label(counts, text="Weak chunks: —", bg=SURFACE,
                                 fg=ERROR, font=(MONO, 10))
        self.weak_lbl.pack(anchor="w")

        # confidence bar placeholder
        self._conf_cv = tk.Canvas(inner, height=8, bg=SURFACE, highlightthickness=0)
        self._conf_cv.pack(fill="x", padx=PAD, pady=(0, PAD))

    def _draw_glow_bar(self, color):
        """Draw a thin glowing horizontal accent under the result."""
        cv = self._glow_cv
        cv.delete("all")
        w = cv.winfo_width() or 140
        cv.create_rectangle(0, 0, w, 6, fill=color, outline="")

    def _draw_confidence(self, good, total):
        """Draw a confidence bar: green portion vs red."""
        cv = self._conf_cv
        cv.delete("all")
        w = cv.winfo_width() or 180
        if total == 0:
            return
        ratio = good / total
        gw = int(w * ratio)
        cv.create_rectangle(0, 0, w, 8, fill=BORDER, outline="")
        cv.create_rectangle(0, 0, gw, 8, fill=SUCCESS, outline="")
        cv.create_rectangle(gw, 0, w, 8, fill=ERROR, outline="")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  GRAPH CARD  (row 1, spans all 3 columns)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_graph_card(self):
        card = Card(self._body)
        card.grid(row=1, column=0, columnspan=3, sticky="nsew",
                  pady=(GAP // 2, 0))
        inner = card.inner

        # header row with title + hint
        hdr_row = tk.Frame(inner, bg=SURFACE)
        hdr_row.pack(fill="x", padx=PAD, pady=(PAD, S))
        SectionTitle(hdr_row, text="Visualisation").pack(side="left")
        self._graph_hint = tk.Label(
            hdr_row, text="Click any graph to expand", bg=SURFACE,
            fg=TEXT_MUTED, font=(FONT_FAMILY, 9))
        self._graph_hint.pack(side="right")

        ttk.Separator(inner, orient="horizontal",
                       style="App.Horizontal.TSeparator").pack(fill="x", padx=PAD)

        # matplotlib figure
        self.fig = Figure(figsize=(11, 3), dpi=96, facecolor=SURFACE)
        self.ax1 = self.fig.add_subplot(131)
        self.ax2 = self.fig.add_subplot(132)
        self.ax3 = self.fig.add_subplot(133)
        self._style_axes()
        self._draw_empty_graphs()
        self.fig.tight_layout(pad=2.5)

        self.mpl_canvas = FigureCanvasTkAgg(self.fig, master=inner)
        self.mpl_canvas.draw()
        self.mpl_canvas.get_tk_widget().pack(
            fill="both", expand=True, padx=PAD, pady=(S, PAD))

        # ── interactive: click to expand ──
        self.mpl_canvas.mpl_connect("button_press_event", self._on_graph_click)
        self.mpl_canvas.mpl_connect("motion_notify_event", self._on_graph_hover)

        # map each axes → graph key
        self._ax_key_map = {
            self.ax1: "distribution",
            self.ax2: "transition",
            self.ax3: "bitstream",
        }

    # ── matplotlib helpers ──
    def _style_axes(self):
        for ax in (self.ax1, self.ax2, self.ax3):
            ax.set_facecolor(BG)
            ax.tick_params(colors=TEXT_MUTED, labelsize=7, length=3)
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.title.set_color(TEXT_SEC)
            ax.xaxis.label.set_color(TEXT_MUTED)
            ax.yaxis.label.set_color(TEXT_MUTED)

    def _reset_axes(self):
        for ax in (self.ax1, self.ax2, self.ax3):
            ax.cla()
        self._style_axes()

    def _draw_empty_graphs(self):
        self._reset_axes()
        self.ax1.set_title("Bit Distribution", fontsize=9, pad=8)
        self.ax1.bar(["0", "1"], [0.5, 0.5], color=[ACCENT_DIM, ACCENT],
                     edgecolor=ACCENT_GLOW, linewidth=0.4, alpha=0.35, width=0.5)
        self.ax1.set_ylim(0, 1)

        for ax, title in [(self.ax2, "Transition Matrix"),
                          (self.ax3, "Bit Stream")]:
            ax.set_title(title, fontsize=9, pad=8)
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    color=TEXT_MUTED, fontsize=10, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])

    def _update_graphs(self, bits):
        """Redraw all three subplots with real data using shared renderers."""
        self._reset_axes()
        _render_graph(self.ax1, "distribution", bits, expanded=False)
        _render_graph(self.ax2, "transition",   bits, expanded=False)
        _render_graph(self.ax3, "bitstream",    bits, expanded=False)
        self.fig.tight_layout(pad=2.5)
        self.mpl_canvas.draw_idle()

    # ── click / hover on graph ──
    def _on_graph_click(self, event):
        """Open an expanded view of the clicked subplot."""
        if event.inaxes is None or self._bits is None:
            return
        key = self._ax_key_map.get(event.inaxes)
        if key:
            GraphPopup(self.root, key, self._bits)

    def _on_graph_hover(self, event):
        """Change cursor to hand when hovering over a subplot with data."""
        widget = self.mpl_canvas.get_tk_widget()
        if event.inaxes is not None and self._bits is not None:
            widget.configure(cursor="hand2")
        else:
            widget.configure(cursor="")

    def _live_graph_tick(self, bits_so_far):
        """Called periodically during collection to update the graph in real time."""
        if not self._collecting or len(bits_so_far) < 20:
            return
        self._reset_axes()
        arr = np.array(bits_so_far)
        n = len(arr)

        # rolling mean
        window = min(100, n)
        cumsum = np.cumsum(arr)
        rolling = (cumsum[window:] - cumsum[:-window]) / window

        self.ax1.set_title("Rolling Mean (live)", fontsize=9, pad=8)
        self.ax1.plot(rolling, color=ACCENT, linewidth=1, alpha=0.85)
        self.ax1.axhline(0.5, color=SUCCESS, linewidth=0.6, linestyle="--", alpha=0.5)
        self.ax1.set_ylim(0, 1)
        self.ax1.set_ylabel("Mean", fontsize=8)
        self.ax1.set_xlabel(f"{n:,} bits collected", fontsize=8)

        # live distribution
        z = int(np.sum(arr == 0))
        o = n - z
        self.ax2.set_title("Distribution (live)", fontsize=9, pad=8)
        self.ax2.bar(["0", "1"], [z / n, o / n],
                     color=[ACCENT_DIM, ACCENT], alpha=0.75, width=0.5)
        self.ax2.set_ylim(0, 1)

        # live bit stream tail
        vis = arr[-200:]
        self.ax3.set_title("Bit Stream (live)", fontsize=9, pad=8)
        colors = [ACCENT if b == 1 else ACCENT_DIM for b in vis]
        self.ax3.bar(range(len(vis)), vis * 2 - 1,
                     color=colors, width=1.0, linewidth=0)
        self.ax3.set_ylim(-1.5, 1.5)
        self.ax3.axhline(0, color=BORDER, linewidth=0.4)

        self.fig.tight_layout(pad=2.5)
        self.mpl_canvas.draw_idle()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  STATUS / BUSY HELPERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _set_status(self, text, color=TEXT_SEC):
        self.status_var.set(text)
        self.status_lbl.configure(fg=color)

    def _start_busy(self):
        self.progress.start(12)
        self.spinner.start()
        self.btn_collect.set_disabled(True)
        self.btn_analyze.set_disabled(True)

    def _stop_busy(self):
        self.progress.stop()
        self.spinner.stop()
        self.btn_collect.set_disabled(False)
        self.btn_analyze.set_disabled(False)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  BUTTON HANDLERS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # ── Collect Data ──────────────────────────────────────────

    def _on_collect(self):
        self._set_status("Collecting entropy…", ACCENT)
        self._start_busy()
        self._collecting = True
        threading.Thread(target=self._collect_worker, daemon=True).start()

    def _collect_worker(self):
        """Try ESP32 serial; fall back to existing CSV."""
        shared_bits = []  # mutable list shared with main‑thread live updater

        def schedule_live():
            """Push a live‑graph tick onto the main thread."""
            if self._collecting:
                self.root.after(0, lambda: self._live_graph_tick(list(shared_bits)))
                self.root.after(500, schedule_live)

        self.root.after(200, schedule_live)

        bits = None
        try:
            import serial as _serial
            ser = _serial.Serial("COM19", 115200, timeout=1)
            hw, rnd, final = [], [], []
            for _ in range(50):
                ser.readline()
            while len(hw) < 10000:
                line = ser.readline().decode("utf-8", errors="ignore").strip()
                if line in ("0", "1"):
                    hb = int(line)
                    hw.append(hb)
                    rb = secrets.randbits(1)
                    rnd.append(rb)
                    fb = hb ^ rb
                    final.append(fb)
                    shared_bits.append(fb)
            ser.close()
            bits = final
            pd.DataFrame({
                "hardware_bit": hw, "random_bit": rnd, "final_bit": final
            }).to_csv(os.path.join(os.path.dirname(__file__),
                                    "hybrid_random_bits.csv"), index=False)
        except Exception:
            csv_path = os.path.join(os.path.dirname(__file__),
                                     "hybrid_random_bits.csv")
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                col = "final_bit" if "final_bit" in df.columns else "bit"
                bits = df[col].tolist()
                # simulate live feed for CSV fallback
                for b in bits:
                    shared_bits.append(b)

        self._collecting = False

        if bits:
            self._bits = bits
            self.root.after(0, lambda: self._post_collect(len(bits)))
        else:
            self.root.after(0, lambda: self._set_status("No data source found", ERROR))
            self.root.after(0, self._stop_busy)

    def _post_collect(self, n):
        self._set_status(f"Collected {n:,} bits", SUCCESS)
        self._stop_busy()
        self._update_graphs(self._bits)

    # ── Run Analysis ─────────────────────────────────────────

    def _on_analyze(self):
        if self._bits is None:
            self._set_status("Collect data first", WARN)
            return
        if self.model is None:
            self._set_status("model.pkl not found", ERROR)
            return
        self._set_status("Analyzing randomness…", ACCENT)
        self._start_busy()
        threading.Thread(target=self._analyze_worker, daemon=True).start()

    def _analyze_worker(self):
        bits = self._bits
        chunk_size = 1000
        chunks = [bits[i:i + chunk_size]
                  for i in range(0, len(bits), chunk_size)
                  if len(bits[i:i + chunk_size]) == chunk_size]

        feat_list = [extract_features(c) for c in chunks]
        names = ["entropy", "mean", "variance", "autocorr", "run_length"]
        fdf = pd.DataFrame(feat_list, columns=names)

        expected = list(getattr(self.model, "feature_names_in_", names))
        fdf = fdf[[c for c in expected if c in fdf.columns]]

        preds = list(self.model.predict(fdf))
        overall = extract_features(bits)
        self._features = overall
        self._predictions = preds

        self.root.after(0, lambda: self._post_analyze(overall, preds))

    def _post_analyze(self, feats, preds):
        entropy, mean, var, autocorr, runlen = feats

        # update metric tiles
        self.m_entropy.set(f"{entropy:.4f}")
        self.m_mean.set(f"{mean:.4f}")
        self.m_variance.set(f"{var:.6f}")
        self.m_autocorr.set(f"{autocorr:.4f}")
        self.m_runlen.set(f"{runlen:.4f}")

        good = preds.count("Good")
        weak = preds.count("Weak")
        total = good + weak
        self.good_lbl.configure(text=f"Good chunks: {good}")
        self.weak_lbl.configure(text=f"Weak chunks: {weak}")

        if good > weak:
            self.result_lbl.configure(text="GOOD\nRANDOMNESS ✓", fg=SUCCESS)
            self._draw_glow_bar(SUCCESS)
            self._set_status("Analysis complete — Good randomness", SUCCESS)
            self._animate_result_glow(SUCCESS)
            self._randomness_good = True
            self._generate_aes_key()
        else:
            self.result_lbl.configure(text="WEAK\nRANDOMNESS ✗", fg=ERROR)
            self._draw_glow_bar(ERROR)
            self._set_status("Analysis complete — Weak randomness", ERROR)
            self._animate_result_glow(ERROR)
            self._randomness_good = False
            self._aes_key = None
            self._crypto_status("Encryption unavailable — weak randomness", ERROR)

        self._update_crypto_buttons()
        self._draw_confidence(good, total)
        self._stop_busy()

    def _animate_result_glow(self, color, step=0):
        """Subtle 3‑pulse glow on the result label."""
        if step >= 6:
            self.result_lbl.configure(fg=color)
            return
        # alternate between bright and target
        bright = lerp_hex(color, "#ffffff", 0.4)
        c = bright if step % 2 == 0 else color
        self.result_lbl.configure(fg=c)
        self.root.after(120, lambda: self._animate_result_glow(color, step + 1))

    # ── Reset ─────────────────────────────────────────────────

    def _on_reset(self):
        self._bits = None
        self._features = None
        self._predictions = None
        self._collecting = False
        self._aes_key = None
        self._randomness_good = False
        self._set_status("Idle", TEXT_SEC)
        for m in (self.m_entropy, self.m_mean, self.m_variance,
                  self.m_autocorr, self.m_runlen):
            m.reset()
        self.result_lbl.configure(text="AWAITING\nANALYSIS", fg=TEXT_MUTED)
        self.good_lbl.configure(text="Good chunks: —")
        self.weak_lbl.configure(text="Weak chunks: —")
        self._glow_cv.delete("all")
        self._conf_cv.delete("all")
        self._draw_empty_graphs()
        self.fig.tight_layout(pad=2.5)
        self.mpl_canvas.draw_idle()
        self._stop_busy()
        # reset crypto card
        self._crypto_file_var.set("No file selected")
        self._crypto_key_var.set("—")
        self._crypto_status("Run analysis with GOOD randomness to enable", TEXT_MUTED)
        self._update_crypto_buttons()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  ENCRYPTION MODULE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _build_crypto_card(self):
        card = Card(self._body)
        card.grid(row=2, column=0, columnspan=3, sticky="nsew",
                  pady=(GAP // 2, 0))
        inner = card.inner

        # header row
        hdr = tk.Frame(inner, bg=SURFACE)
        hdr.pack(fill="x", padx=PAD, pady=(PAD, S))
        SectionTitle(hdr, text="Secure Encryption Module").pack(side="left")
        self._crypto_status_lbl = tk.Label(
            hdr, text="Run analysis with GOOD randomness to enable",
            bg=SURFACE, fg=TEXT_MUTED, font=(FONT_FAMILY, 9))
        self._crypto_status_lbl.pack(side="right")

        ttk.Separator(inner, orient="horizontal",
                       style="App.Horizontal.TSeparator").pack(fill="x", padx=PAD)

        # ── main content: 3 columns ──
        content = tk.Frame(inner, bg=SURFACE)
        content.pack(fill="both", expand=True, padx=PAD, pady=(GAP, PAD))
        content.columnconfigure(0, weight=2, uniform="cr")
        content.columnconfigure(1, weight=3, uniform="cr")
        content.columnconfigure(2, weight=2, uniform="cr")

        # ── col 0: file selection ──
        file_fr = tk.Frame(content, bg=SURFACE)
        file_fr.grid(row=0, column=0, sticky="nsew", padx=(0, GAP))

        tk.Label(file_fr, text="Selected File", bg=SURFACE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, 9)).pack(anchor="w")
        self._crypto_file_var = tk.StringVar(value="No file selected")
        self._crypto_file_lbl = tk.Label(
            file_fr, textvariable=self._crypto_file_var, bg=SURFACE_ALT,
            fg=TEXT_SEC, font=(MONO, 9), anchor="w", padx=S, pady=S,
            wraplength=260)
        self._crypto_file_lbl.pack(fill="x", pady=(4, S))

        self.btn_select_file = PillButton(
            file_fr, text="Select File", command=self._on_select_file,
            accent=ACCENT, width=220, height=36)
        self.btn_select_file.pack(fill="x", pady=(0, S))

        # encrypt / decrypt buttons
        self.btn_encrypt = PillButton(
            file_fr, text="Encrypt File", command=self._on_encrypt,
            accent=SUCCESS, width=220, height=36)
        self.btn_encrypt.pack(fill="x", pady=(0, S))

        self.btn_decrypt = PillButton(
            file_fr, text="Decrypt File", command=self._on_decrypt,
            accent=WARN, width=220, height=36)
        self.btn_decrypt.pack(fill="x")

        # ── col 1: key display ──
        key_fr = tk.Frame(content, bg=SURFACE)
        key_fr.grid(row=0, column=1, sticky="nsew", padx=(0, GAP))

        tk.Label(key_fr, text="AES‑256 Key", bg=SURFACE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, 9)).pack(anchor="w")

        key_display = tk.Frame(key_fr, bg=SURFACE_ALT)
        key_display.pack(fill="x", pady=(4, S))
        self._crypto_key_var = tk.StringVar(value="—")
        self._key_masked = True
        self._crypto_key_lbl = tk.Label(
            key_display, textvariable=self._crypto_key_var,
            bg=SURFACE_ALT, fg=ACCENT, font=(MONO, 10),
            anchor="w", padx=S, pady=S, wraplength=360)
        self._crypto_key_lbl.pack(side="left", fill="x", expand=True)

        # key action buttons row
        key_btns = tk.Frame(key_fr, bg=SURFACE)
        key_btns.pack(fill="x", pady=(0, S))

        self.btn_reveal = PillButton(
            key_btns, text="Reveal Key", command=self._on_toggle_key,
            accent=ACCENT, width=110, height=32)
        self.btn_reveal.pack(side="left", padx=(0, S))

        self.btn_copy_key = PillButton(
            key_btns, text="Copy Key", command=self._on_copy_key,
            accent=ACCENT, width=110, height=32)
        self.btn_copy_key.pack(side="left", padx=(0, S))

        self.btn_save_key = PillButton(
            key_btns, text="Save Key", command=self._on_save_key,
            accent=ACCENT, width=110, height=32)
        self.btn_save_key.pack(side="left")

        # load key from file
        self.btn_load_key = PillButton(
            key_fr, text="Load Key from File",
            command=self._on_load_key, accent=TEXT_SEC, width=220, height=32)
        self.btn_load_key.pack(anchor="w")

        # ── col 2: status / info ──
        info_fr = tk.Frame(content, bg=SURFACE)
        info_fr.grid(row=0, column=2, sticky="nsew")

        tk.Label(info_fr, text="Encryption Info", bg=SURFACE, fg=TEXT_MUTED,
                 font=(FONT_FAMILY, 9)).pack(anchor="w")

        self._crypto_info_var = tk.StringVar(value="AES‑256‑GCM\nAwaiting operation")
        tk.Label(info_fr, textvariable=self._crypto_info_var, bg=SURFACE_ALT,
                 fg=TEXT_SEC, font=(MONO, 9), anchor="nw", justify="left",
                 padx=S, pady=S, wraplength=220).pack(fill="x", pady=(4, S))

        # progress for crypto operations
        self._crypto_spinner = SpinnerCanvas(info_fr, size=20, color=ACCENT)
        self._crypto_spinner.pack(anchor="w", pady=(S, 0))

        self._update_crypto_buttons()

    # ── helpers ──

    def _crypto_status(self, text, color=TEXT_SEC):
        self._crypto_status_lbl.configure(text=text, fg=color)

    def _update_crypto_buttons(self):
        """Enable/disable crypto buttons based on state."""
        has_key = self._aes_key is not None
        self.btn_encrypt.set_disabled(not has_key)
        self.btn_decrypt.set_disabled(not has_key)
        self.btn_reveal.set_disabled(not has_key)
        self.btn_copy_key.set_disabled(not has_key)
        self.btn_save_key.set_disabled(not has_key)

    def _generate_aes_key(self):
        """Generate AES key from current bits (called after GOOD analysis)."""
        if self._bits:
            self._aes_key = bits_to_key(self._bits)
            self._key_masked = True
            self._crypto_key_var.set("•" * 48 + "  (hidden)")
            self._crypto_status("Key generated — ready to encrypt", SUCCESS)

    # ── file selection ──

    def _on_select_file(self):
        path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[("All files", "*.*")])
        if path:
            self._crypto_file_var.set(os.path.basename(path))
            self._selected_file = path

    # ── reveal / hide key ──

    def _on_toggle_key(self):
        if self._aes_key is None:
            return
        if self._key_masked:
            self._crypto_key_var.set(key_to_hex(self._aes_key))
            self._key_masked = False
        else:
            self._crypto_key_var.set("•" * 48 + "  (hidden)")
            self._key_masked = True

    # ── copy key ──

    def _on_copy_key(self):
        if self._aes_key is None:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(key_to_hex(self._aes_key))
        self._crypto_status("Key copied to clipboard", SUCCESS)

    # ── save key ──

    def _on_save_key(self):
        if self._aes_key is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save AES Key",
            defaultextension=".key",
            filetypes=[("Key file", "*.key"), ("Text file", "*.txt")])
        if path:
            try:
                save_key_to_file(self._aes_key, path)
                self._crypto_status(f"Key saved to {os.path.basename(path)}", SUCCESS)
            except Exception as e:
                self._crypto_status(f"Save failed: {e}", ERROR)

    # ── load key ──

    def _on_load_key(self):
        path = filedialog.askopenfilename(
            title="Load AES Key",
            filetypes=[("Key file", "*.key"), ("Text file", "*.txt"), ("All", "*.*")])
        if path:
            try:
                self._aes_key = load_key_from_file(path)
                self._key_masked = True
                self._crypto_key_var.set("•" * 48 + "  (loaded)")
                self._crypto_status(f"Key loaded from {os.path.basename(path)}", SUCCESS)
                self._update_crypto_buttons()
            except Exception as e:
                self._crypto_status(f"Load failed: {e}", ERROR)

    # ── encrypt ──

    def _on_encrypt(self):
        if self._aes_key is None:
            self._crypto_status("No key available", ERROR)
            return
        path = getattr(self, "_selected_file", None)
        if not path or not os.path.exists(path):
            self._crypto_status("Select a file first", WARN)
            return
        self._crypto_status("Encrypting…", ACCENT)
        self._crypto_spinner.start()
        self.btn_encrypt.set_disabled(True)
        self.btn_decrypt.set_disabled(True)
        threading.Thread(target=self._encrypt_worker, args=(path,), daemon=True).start()

    def _encrypt_worker(self, path):
        try:
            dest, elapsed = encrypt_file(path, self._aes_key)
            self.root.after(0, lambda: self._post_encrypt(dest, elapsed))
        except Exception as e:
            self.root.after(0, lambda: self._crypto_status(f"Encryption failed: {e}", ERROR))
            self.root.after(0, self._crypto_spinner.stop)
            self.root.after(0, lambda: self._update_crypto_buttons())

    def _post_encrypt(self, dest, elapsed):
        self._crypto_spinner.stop()
        fname = os.path.basename(dest)
        self._crypto_status(f"Encrypted → {fname}", SUCCESS)
        size_kb = os.path.getsize(dest) / 1024
        self._crypto_info_var.set(
            f"AES‑256‑GCM\n"
            f"Output: {fname}\n"
            f"Size: {size_kb:.1f} KB\n"
            f"Time: {elapsed*1000:.1f} ms")
        self._update_crypto_buttons()

    # ── decrypt ──

    def _on_decrypt(self):
        if self._aes_key is None:
            self._crypto_status("No key available", ERROR)
            return
        path = filedialog.askopenfilename(
            title="Select encrypted file",
            filetypes=[("Encrypted files", "*.enc"), ("All files", "*.*")])
        if not path:
            return
        self._crypto_status("Decrypting…", ACCENT)
        self._crypto_spinner.start()
        self.btn_encrypt.set_disabled(True)
        self.btn_decrypt.set_disabled(True)
        threading.Thread(target=self._decrypt_worker, args=(path,), daemon=True).start()

    def _decrypt_worker(self, path):
        try:
            dest, elapsed = decrypt_file(path, self._aes_key)
            self.root.after(0, lambda: self._post_decrypt(dest, elapsed))
        except Exception as e:
            msg = str(e)
            if "tag" in msg.lower() or "authenticate" in msg.lower():
                msg = "Wrong key or corrupted file"
            self.root.after(0, lambda: self._crypto_status(f"Decryption failed: {msg}", ERROR))
            self.root.after(0, self._crypto_spinner.stop)
            self.root.after(0, lambda: self._update_crypto_buttons())

    def _post_decrypt(self, dest, elapsed):
        self._crypto_spinner.stop()
        fname = os.path.basename(dest)
        self._crypto_status(f"Decrypted → {fname}", SUCCESS)
        size_kb = os.path.getsize(dest) / 1024
        self._crypto_info_var.set(
            f"AES‑256‑GCM\n"
            f"Output: {fname}\n"
            f"Size: {size_kb:.1f} KB\n"
            f"Time: {elapsed*1000:.1f} ms")
        self._update_crypto_buttons()


# ═══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════

def main():
    root = tk.Tk()
    RandomnessAnalyzer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
