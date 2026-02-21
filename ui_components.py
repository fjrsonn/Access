"""Reusable UI components built on top of ui_theme tokens."""
from __future__ import annotations

from dataclasses import dataclass, field
import time

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None
    ttk = None

import ui_theme as _ui_theme

UI_THEME = _ui_theme.UI_THEME
theme_font = _ui_theme.theme_font
theme_space = _ui_theme.theme_space
build_card_frame = _ui_theme.build_card_frame
build_label = _ui_theme.build_label
state_colors = _ui_theme.state_colors
normalize_tone = _ui_theme.normalize_tone
contrast_ratio = _ui_theme.contrast_ratio
resolve_card_variant = getattr(
    _ui_theme,
    "resolve_card_variant",
    lambda _name: {"density": "confortavel", "show_sparkline": True, "show_legend": True},
)


def build_section_title(parent, text: str):
    return tk.Label(
        parent,
        text=text,
        bg=UI_THEME.get("bg", "#0F1115"),
        fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")),
        font=theme_font("font_xl", "bold"),
        anchor="w",
    )


def build_form_row(parent, label_text: str, control):
    row = tk.Frame(parent, bg=UI_THEME.get("surface", "#151A22"))
    lbl = build_label(row, label_text, bg=UI_THEME.get("surface", "#151A22"), font=theme_font("font_md"))
    lbl.pack(side=tk.LEFT, padx=(theme_space("space_2", 8), theme_space("space_1", 4)), pady=theme_space("space_2", 8))
    control.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_2", 8))
    return row


class AppFeedbackBanner(tk.Frame):
    def __init__(self, parent, text: str = ""):
        super().__init__(parent, bg=UI_THEME.get("surface_alt", "#1B2430"), highlightthickness=1, highlightbackground=UI_THEME.get("border", "#2B3442"))
        self.var = tk.StringVar(value=text)
        self.lbl = tk.Label(self, textvariable=self.var, anchor="w", bg=self.cget("bg"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), font=theme_font("font_sm"))
        self.lbl.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=theme_space("space_1", 4))
        self._after_id = None

    def show(self, text: str, tone: str = "info", icon: str = "ℹ", timeout_ms: int = 2200):
        self.var.set(f"{icon} {text}".strip())
        bg, fg = state_colors(tone)
        self.configure(bg=bg)
        self.lbl.configure(bg=bg, fg=fg)
        try:
            self.pack_forget()
            self.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4), 0))
        except Exception:
            pass
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(timeout_ms, self.hide)

    def hide(self):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = None
        try:
            self.pack_forget()
        except Exception:
            pass


class AppStatusBar(tk.Frame):
    def __init__(self, parent, text: str = ""):
        super().__init__(parent, bg=UI_THEME.get("surface_alt", "#1B2430"), highlightthickness=1, highlightbackground=UI_THEME.get("border", "#2B3442"))
        self.var = tk.StringVar(value=text)
        self.lbl = tk.Label(self, textvariable=self.var, anchor="w", bg=UI_THEME.get("surface_alt", "#1B2430"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), font=theme_font("font_sm"))
        self.lbl.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=theme_space("space_1", 4))

    def set(self, text: str, tone: str = "info"):
        self.var.set(text)
        bg, fg = state_colors(tone)
        self.configure(bg=bg)
        self.lbl.configure(bg=bg, fg=fg)


class CardState:
    def __init__(self):
        self.capacity_percent = 0.0
        self.hover_segment = None
        self.selected_segment = None
        self.interaction_mode = "click-lock"
        self.center_mode = "auto"
        self.pinned = False


@dataclass
class CardMetricData:
    capacity_consumed: int = 0
    capacity_limit: int = 1
    history: list[float] = field(default_factory=lambda: [0.0] * 7)
    status: str = "info"
    meta: str = "Atualizado agora"


class SharedRepaintScheduler:
    _queue = []
    _after_id = None
    _root = None
    _frame_budget_ms = 16

    @classmethod
    def request(cls, widget, callback):
        cls._queue.append((widget, callback, time.perf_counter()))
        if cls._after_id:
            return
        try:
            cls._root = widget.winfo_toplevel()
            cls._after_id = cls._root.after(cls._frame_budget_ms, cls._flush)
        except Exception:
            cls._flush()

    @classmethod
    def _flush(cls):
        start = time.perf_counter()
        tasks = cls._queue[:]
        cls._queue.clear()
        cls._after_id = None
        for _widget, cb, requested_at in tasks:
            try:
                cb(max(0.0, (time.perf_counter() - requested_at) * 1000.0))
            except Exception:
                pass
        spent = (time.perf_counter() - start) * 1000.0
        cls._frame_budget_ms = 24 if spent > 18 else 16


class DonutRenderer:
    def __init__(self):
        self._last_snapshot = None

    @staticmethod
    def _effective_segment(state: CardState):
        return state.selected_segment or state.hover_segment

    def should_skip(self, snapshot):
        if snapshot == self._last_snapshot:
            return True
        self._last_snapshot = snapshot
        return False

    def draw(self, canvas, *, tone: str, capacity_percent: float, consumed_progress: float, remaining_progress: float,
             state: CardState, base_bg: str, density: str = "confortavel", low_motion: bool = False, force: bool = False):
        w = max(40, int(canvas.winfo_width()))
        h = max(40, int(canvas.winfo_height()))
        active = self._effective_segment(state)
        snapshot = (w, h, round(capacity_percent, 4), round(consumed_progress, 4), round(remaining_progress, 4), active, tone, state.center_mode)
        if (not force) and self.should_skip(snapshot):
            return
        canvas.delete("all")
        base_width = 12
        hover_extra = 0 if low_motion else 6
        max_stroke = base_width + 3
        safe_margin = hover_extra + (max_stroke / 2) + 2
        size = max(20, min(w, h) - (2 * safe_margin))
        x0 = (w - size) / 2
        y0 = (h - size) / 2
        x1 = x0 + size
        y1 = y0 + size
        fg_ring = UI_THEME.get(tone, UI_THEME.get("primary", "#2F81F7"))
        rem_ring = UI_THEME.get("remaining", "#5B6577")
        rem_ring_active = UI_THEME.get("remaining_active", "#7C8AA3")
        consumed = max(0.0, min(1.0, capacity_percent * consumed_progress))
        remaining_total = max(0.0, 1.0 - capacity_percent)
        remaining = max(0.0, min(1.0, remaining_total * remaining_progress))

        consumed_hovered = active == "consumed"
        remaining_hovered = active == "remaining"

        if consumed > 0:
            consumed_pad = hover_extra if consumed_hovered else 0
            canvas.create_arc(
                x0 - consumed_pad, y0 - consumed_pad, x1 + consumed_pad, y1 + consumed_pad,
                start=90, extent=-(360.0 * consumed), style="arc", outline=fg_ring,
                width=base_width + (3 if consumed_hovered else 0), tags=("segment", "segment_consumed"),
            )
        if remaining > 0:
            remaining_pad = hover_extra if remaining_hovered else 0
            canvas.create_arc(
                x0 - remaining_pad, y0 - remaining_pad, x1 + remaining_pad, y1 + remaining_pad,
                start=90 - (360.0 * consumed), extent=-(360.0 * remaining), style="arc", outline=(rem_ring_active if remaining_hovered else rem_ring),
                width=base_width + (3 if remaining_hovered else 0), tags=("segment", "segment_remaining"),
            )

        mode = state.center_mode
        active_mode = active
        if mode in {"consumed", "remaining"}:
            active_mode = mode
        if active_mode == "remaining":
            pct_text = f"{int(round((1.0 - capacity_percent) * 100))}%"
            subtitle = "Restante"
        else:
            pct_text = f"{int(round(capacity_percent * 100))}%"
            subtitle = "Consumido"

        compact = str(density).lower().startswith("compact")
        min_n, max_n = (16, 26) if compact else (18, 36)
        numeric = max(min_n, min(max_n, int(size * (0.16 if compact else 0.19))))
        subtitle_size = max(8, min(13, int(numeric * 0.45)))
        text_color = UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3"))
        if contrast_ratio(text_color, base_bg) < 4.5:
            text_color = UI_THEME.get("text", "#E6EDF3")
            if contrast_ratio(text_color, base_bg) < 4.5:
                text_color = UI_THEME.get("focus_text", "#111827")
        sub_color = UI_THEME.get("muted_text", "#9AA4B2")
        if contrast_ratio(sub_color, base_bg) < 4.5:
            sub_color = text_color

        canvas.create_text(w / 2, (h / 2) - 8, text=pct_text, fill=text_color, font=(UI_THEME.get("font_family", "Segoe UI"), numeric, "bold"), tags=("label_center",))
        canvas.create_text(w / 2, (h / 2) + 10, text=subtitle, fill=sub_color, font=(UI_THEME.get("font_family", "Segoe UI"), subtitle_size, "normal"), tags=("label_center",))

        if state.selected_segment in {"consumed", "remaining"}:
            consumed_n = int(round(capacity_percent * 100))
            ctx = f"{consumed_n}/100" if state.selected_segment == "consumed" else f"{100-consumed_n}/100"
            canvas.create_text(w / 2, (h / 2) + 24, text=ctx, fill=sub_color, font=(UI_THEME.get("font_family", "Segoe UI"), max(8, subtitle_size - 1), "normal"), tags=("label_center",))


class SparklineRenderer:
    def __init__(self):
        self._last_snapshot = None

    def draw(self, canvas, values, tone, force=False):
        w = max(80, int(canvas.winfo_width()))
        h = max(24, int(canvas.winfo_height()))
        bg = canvas.cget("bg")
        vals = list(values[-7:]) if values else [0.0]
        while len(vals) < 7:
            vals.insert(0, vals[0])
        snapshot = (w, h, tuple(round(v, 4) for v in vals), tone)
        if (not force) and snapshot == self._last_snapshot:
            return
        self._last_snapshot = snapshot
        canvas.delete("all")
        mn, mx = min(vals), max(vals)
        spread = max(1e-6, mx - mn)
        pad = 4
        step = (w - (2 * pad)) / max(1, len(vals) - 1)
        pts = []
        for idx, val in enumerate(vals):
            x = pad + (idx * step)
            y = pad + (h - (2 * pad)) * (1.0 - ((val - mn) / spread))
            pts.extend([x, y])
        line_color = UI_THEME.get(tone, UI_THEME.get("primary", "#2F81F7"))
        axis_color = UI_THEME.get("muted_text", "#9AA4B2")
        if contrast_ratio(axis_color, bg) < 4.5:
            axis_color = UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3"))
        canvas.create_line(*pts, smooth=True, width=2, fill=line_color)
        avg = sum(vals) / len(vals)
        y_avg = pad + (h - (2 * pad)) * (1.0 - ((avg - mn) / spread))
        canvas.create_line(pad, y_avg, w - pad, y_avg, fill=axis_color, dash=(2, 2))
        if pts:
            canvas.create_oval(pts[-2] - 2, pts[-1] - 2, pts[-2] + 2, pts[-1] + 2, fill=line_color, outline="")
        peak = max(range(len(vals)), key=lambda i: vals[i])
        trough = min(range(len(vals)), key=lambda i: vals[i])
        for idx, tag, color in ((peak, "P", UI_THEME.get("warning", "#CCA700")), (trough, "V", UI_THEME.get("info", "#2563EB"))):
            x = pad + (idx * step)
            y = pad + (h - (2 * pad)) * (1.0 - ((vals[idx] - mn) / spread))
            canvas.create_text(x, max(6, y - 8), text=tag, fill=color, font=theme_font("font_sm", "bold"))
        first = vals[0] if vals[0] != 0 else 1e-6
        delta = ((vals[-1] - vals[0]) / first) * 100.0
        delta_text = f"Δ {delta:+.0f}%"
        canvas.create_text(w - 4, 4, anchor="ne", text=delta_text, fill=axis_color, font=theme_font("font_sm", "normal"))


class RadialBarRenderer(DonutRenderer):
    """Compat renderer plugável que reaproveita o renderer de donut."""


class BulletChartRenderer(DonutRenderer):
    """Compat renderer plugável que reaproveita o renderer de donut."""


class AppMetricCard(tk.Frame):
    _pinned_cards = []

    def __init__(self, parent, title: str, value: str = "0", tone: str = "info", icon: str = "●", *,
                 enable_sparkline: bool = True, enable_legend: bool = True, enable_click_lock: bool = True,
                 enable_stagger: bool = True, variant: str = "default"):
        variant_cfg = resolve_card_variant(variant)
        self._base_surface = UI_THEME.get("surface", "#151A22")
        self._lift_surface = UI_THEME.get("surface_alt", "#1B2430")
        self._shadow_idle = UI_THEME.get("shadow_1", UI_THEME.get("border", "#2B3442"))
        self._shadow_hover = UI_THEME.get("shadow_2", UI_THEME.get("primary", "#2F81F7"))
        super().__init__(parent, bg=self._base_surface, highlightthickness=1, highlightbackground=self._shadow_idle)
        self._tone = normalize_tone(tone)
        self._title = title
        self._icon = icon
        self._enable_sparkline = bool(variant_cfg.get("show_sparkline", enable_sparkline))
        self._enable_legend = bool(variant_cfg.get("show_legend", enable_legend))
        self._enable_click_lock = bool(variant_cfg.get("enable_click_lock", enable_click_lock))
        self._enable_stagger = bool(variant_cfg.get("enable_stagger", enable_stagger))
        self._chart_type = str(variant_cfg.get("chart_type", "donut")).strip().lower()
        self._variant = variant_cfg

        self._flash_after = None
        self._stagger_after = None
        self._pulse_after = None
        self._hover_after = None
        self._pending_hover_segment = None
        self._lift_anim_after = None
        self._perf_low_motion = False
        self._focus_index = 0
        self._focus_targets = []
        self._lift_progress = 0.0

        self._metric_data = CardMetricData()

        self.title_var = tk.StringVar(value=f"{icon} {title}")
        self._target_value_text = str(value)
        self._value_revealed = False
        self.value_var = tk.StringVar(value="")
        self.meta_var = tk.StringVar(value="Atualizado agora")
        self.trend_var = tk.StringVar(value="→ estável")
        self.capacity_var = tk.StringVar(value="Consumido 0% • 0 usados • 0 restantes")
        self._capacity_percent = 0.0
        self._capacity_consumed_n = 0
        self._capacity_limit_n = 1
        self._state = CardState()
        self._state.interaction_mode = "click-lock" if self._enable_click_lock else "hover"

        self._renderer_registry = {"donut": DonutRenderer(), "radial-bar": RadialBarRenderer(), "bullet": BulletChartRenderer()}
        self._donut_renderer = self._renderer_registry.get(self._chart_type, self._renderer_registry["donut"])
        self._sparkline_renderer = SparklineRenderer()

        self.accent_wrap = tk.Frame(self, bg=self._base_surface, width=6)
        self.accent_wrap.pack(side=tk.LEFT, fill=tk.Y)
        self.accent_canvas = tk.Canvas(self.accent_wrap, width=6, highlightthickness=0, bd=0, bg=self._base_surface)
        self.accent_canvas.pack(fill=tk.BOTH, expand=True)
        self._accent_anim_after = None
        self._accent_gradient_progress = 0.0

        self.body = tk.Frame(self, bg=self._base_surface)
        self.body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bottom_curve = tk.Canvas(self.body, height=1, bg=self._base_surface, highlightthickness=0, bd=0)
        self.bottom_curve.pack(side=tk.BOTTOM, fill=tk.X)

        self._donut_consumed_progress = 1.0
        self._donut_remaining_progress = 1.0
        self._donut_visible = False
        self._donut_anim_after = None

        self.top_row = tk.Frame(self.body, bg=self._base_surface)
        self.top_row.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(theme_space("space_1", 4), 0))
        self.text_column = tk.Frame(self.top_row, bg=self._base_surface)
        self.text_column.pack(fill=tk.BOTH, expand=True)
        self.pin_btn = tk.Label(self.top_row, text="📌", bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), cursor="hand2", takefocus=1)
        self.pin_btn.pack(side=tk.RIGHT)

        self.sparkline = tk.Canvas(self.text_column, height=32, highlightthickness=0, bd=0, bg=self._base_surface)
        self._sparkline_data = [0, 0, 0, 0, 0, 0, 0]

        self.donut_wrap = tk.Frame(self.body, bg=self._base_surface, height=170)
        self.donut_wrap.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(theme_space("space_1", 4), 0))
        self.donut_wrap.pack_propagate(False)
        self.donut_canvas = tk.Canvas(self.donut_wrap, width=1, height=1, bg=self._base_surface, highlightthickness=0, bd=0, takefocus=1)

        self.legend_wrap = tk.Frame(self.body, bg=self._base_surface)
        self.legend_consumed = tk.Label(self.legend_wrap, text="● Consumido", bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), cursor="hand2", takefocus=1)
        self.legend_remaining = tk.Label(self.legend_wrap, text="● Restante", bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), cursor="hand2", takefocus=1)
        self.legend_consumed.pack(side=tk.LEFT, padx=(0, theme_space("space_2", 8)))
        self.legend_remaining.pack(side=tk.LEFT)

        self.title_lbl = tk.Label(self.body, textvariable=self.title_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.value_lbl = tk.Label(self.body, textvariable=self.value_var, bg=self._base_surface, fg=state_colors(self._tone)[0], font=theme_font("font_xl", "bold"))
        self.trend_lbl = tk.Label(self.body, textvariable=self.trend_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.capacity_lbl = tk.Label(self.body, textvariable=self.capacity_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.meta_lbl = tk.Label(self.body, textvariable=self.meta_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.context_var = tk.StringVar(value="Último ciclo 0 • Média 7d 0 • Variação +0%")
        self.context_lbl = tk.Label(self.body, textvariable=self.context_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.compare_var = tk.StringVar(value="")
        self.compare_lbl = tk.Label(self.body, textvariable=self.compare_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))

        self._apply_density(variant_cfg.get("density", "confortavel"))
        self.bottom_curve.bind("<Configure>", self._draw_bottom_curve, add="+")
        self.donut_canvas.bind("<Configure>", lambda _e: self._draw_donut(force=True), add="+")
        self.donut_canvas.bind("<Motion>", self._on_donut_hover, add="+")
        self.donut_canvas.bind("<Leave>", self._on_donut_leave, add="+")
        self.donut_canvas.bind("<Button-1>", self._on_donut_click, add="+")
        self.donut_canvas.bind("<Return>", lambda _e: self._on_donut_click(_e), add="+")
        self.donut_canvas.bind("<space>", lambda _e: self._on_donut_click(_e), add="+")
        self.sparkline.bind("<Configure>", lambda _e: self._draw_sparkline(force=True), add="+")

        self.legend_consumed.bind("<Enter>", lambda _e: self._set_hover_segment("consumed"), add="+")
        self.legend_remaining.bind("<Enter>", lambda _e: self._set_hover_segment("remaining"), add="+")
        self.legend_consumed.bind("<Leave>", lambda _e: self._set_hover_segment(None), add="+")
        self.legend_remaining.bind("<Leave>", lambda _e: self._set_hover_segment(None), add="+")
        self.legend_consumed.bind("<Button-1>", lambda _e: self._toggle_selected_segment("consumed"), add="+")
        self.legend_remaining.bind("<Button-1>", lambda _e: self._toggle_selected_segment("remaining"), add="+")
        self.legend_consumed.bind("<Return>", lambda _e: self._toggle_selected_segment("consumed"), add="+")
        self.legend_remaining.bind("<Return>", lambda _e: self._toggle_selected_segment("remaining"), add="+")

        self.pin_btn.bind("<Button-1>", self._toggle_pin, add="+")
        self.pin_btn.bind("<Return>", self._toggle_pin, add="+")

        for focus_widget in (self.donut_canvas, self.legend_consumed, self.legend_remaining, self.pin_btn):
            focus_widget.bind("<Left>", self._on_roving_focus, add="+")
            focus_widget.bind("<Right>", self._on_roving_focus, add="+")
            focus_widget.bind("<Escape>", self._on_clear_selection, add="+")

        self._focus_targets = [self.donut_canvas, self.legend_consumed, self.legend_remaining, self.pin_btn]

        self.bind("<Enter>", self._on_card_hover_enter, add="+")
        self.bind("<Leave>", self._on_card_hover_leave, add="+")
        self.body.bind("<Enter>", self._on_card_hover_enter, add="+")
        self.body.bind("<Leave>", self._on_card_hover_leave, add="+")

        self.after(0, self._draw_bottom_curve)
        self.after(0, lambda: self._draw_donut(force=True))
        self.after(0, lambda: self._draw_sparkline(force=True))
        self.after(0, lambda: self._set_card_lift(False))

    def _low_motion(self):
        return bool(UI_THEME.get("low_motion", False)) or self._perf_low_motion

    def _ease_by_token(self, t: float) -> float:
        t = max(0.0, min(1.0, float(t)))
        easing = str(UI_THEME.get("ease_out", "cubic")).strip().lower()
        if easing in {"quad", "ease_out_quad"}:
            return 1.0 - ((1.0 - t) ** 2)
        if easing in {"expo", "ease_out_expo"}:
            return 1.0 if t >= 1.0 else 1.0 - (2 ** (-10 * t))
        return 1.0 - ((1.0 - t) ** 3)

    def _truncate_text(self, text: str, limit: int) -> str:
        value = str(text or "").strip()
        if len(value) <= limit:
            return value
        return value[: max(1, limit - 1)].rstrip() + "…"

    def _aa_text(self, preferred: str, bg: str, fallback: str | None = None):
        color = preferred
        if contrast_ratio(color, bg) >= 4.5:
            return color
        fb = fallback or UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3"))
        if contrast_ratio(fb, bg) >= 4.5:
            return fb
        return UI_THEME.get("focus_text", "#FFFFFF")

    def set_interaction_mode(self, mode: str = "click-lock"):
        self._state.interaction_mode = "hover" if str(mode).strip().lower() == "hover" else "click-lock"
        if self._state.interaction_mode == "hover":
            self._state.selected_segment = None
            self._draw_donut()

    def set_center_mode(self, mode: str = "auto"):
        value = str(mode or "auto").strip().lower()
        if value not in {"auto", "consumed", "remaining"}:
            value = "auto"
        self._state.center_mode = value
        self._draw_donut()

    def set_chart_renderer(self, chart_type: str = "donut"):
        key = str(chart_type or "donut").strip().lower()
        self._chart_type = key
        self._donut_renderer = self._renderer_registry.get(key, self._renderer_registry["donut"])
        self._draw_donut(force=True)

    def set_metric_data(self, metric: CardMetricData):
        self._metric_data = metric if isinstance(metric, CardMetricData) else CardMetricData()
        self.set_history(self._metric_data.history)
        self.set_capacity(self._metric_data.capacity_consumed, self._metric_data.capacity_limit)
        self.set_meta(self._metric_data.meta)

    def set_history(self, points):
        values = []
        for item in list(points or [])[:7]:
            try:
                values.append(float(item))
            except Exception:
                values.append(0.0)
        if not values:
            values = [0.0]
        while len(values) < 7:
            values.insert(0, values[0])
        self._sparkline_data = values[-7:]
        self._metric_data.history = list(self._sparkline_data)
        self._update_inline_context()
        self._draw_sparkline()

    def animate_entry_stagger(self, order: int = 0, base_delay_ms: int = 50, on_done=None):
        try:
            if self._stagger_after:
                self.after_cancel(self._stagger_after)
        except Exception:
            pass
        if not self._enable_stagger or self._low_motion():
            self.animate_accent_growth()
            self.animate_capacity_fill(on_done=on_done)
            return
        delay = max(0, int(order) * max(40, int(base_delay_ms)))
        self._stagger_after = self.after(delay, lambda: (self.animate_accent_growth(), self.animate_capacity_fill(on_done=on_done)))

    def _draw_bottom_curve(self, _event=None):
        try:
            w = max(20, int(self.bottom_curve.winfo_width()))
            h = max(1, int(self.bottom_curve.winfo_height()))
            card_bg = self.body.cget("bg")
            self.bottom_curve.configure(bg=card_bg)
            self.bottom_curve.delete("all")
            self.bottom_curve.create_rectangle(0, 0, w, h, fill=card_bg, outline="")
        except Exception:
            pass

    def _apply_density(self, mode: str = "confortavel"):
        compact = str(mode).lower().startswith("compact")
        px = theme_space("space_1", 4) if compact else theme_space("space_2", 8)
        py_top = theme_space("space_1", 4)
        py_bottom = theme_space("space_1", 4) if compact else theme_space("space_2", 8)
        self.title_lbl.pack(in_=self.text_column, anchor="w", padx=(0, 0), pady=(py_top, 0))
        self.value_lbl.pack(in_=self.text_column, anchor="w", padx=(0, 0), pady=(0, 0))
        if self._enable_sparkline:
            self.sparkline.pack(in_=self.text_column, fill=tk.X, pady=(2, 4))
        else:
            self.sparkline.pack_forget()
        if self._donut_visible:
            self.donut_canvas.pack(fill=tk.BOTH, expand=True)
            if self._enable_legend:
                self.legend_wrap.pack(fill=tk.X, padx=px, pady=(2, 0))
            else:
                self.legend_wrap.pack_forget()
        else:
            self.donut_canvas.pack_forget()
            self.legend_wrap.pack_forget()
        self.trend_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.capacity_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.context_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.compare_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.meta_lbl.pack(anchor="w", padx=px, pady=(0, py_bottom))

    def _draw_sparkline(self, force=False):
        if not self._enable_sparkline:
            return
        def _run(latency_ms=0.0):
            self._perf_low_motion = latency_ms > 40.0
            self._sparkline_renderer.draw(self.sparkline, self._sparkline_data, self._tone, force=force)
            self._update_accessibility_colors()
        SharedRepaintScheduler.request(self, _run)

    def _draw_donut(self, force=False):
        try:
            if not self._donut_visible:
                self.donut_canvas.delete("all")
                return
            def _run(latency_ms=0.0):
                self._perf_low_motion = latency_ms > 40.0
                self._donut_renderer.draw(
                    self.donut_canvas,
                    tone=self._tone,
                    capacity_percent=self._capacity_percent,
                    consumed_progress=self._donut_consumed_progress,
                    remaining_progress=self._donut_remaining_progress,
                    state=self._state,
                    base_bg=self.body.cget("bg"),
                    low_motion=self._low_motion(),
                    force=force,
                )
                self._update_legend_visual()
                self._update_inline_context()
                self._update_accessibility_colors()
            SharedRepaintScheduler.request(self, _run)
        except Exception:
            pass

    def _segment_from_current(self):
        current = self.donut_canvas.find_withtag("current")
        if not current:
            return None
        tags = set(self.donut_canvas.gettags(current[0]))
        if "segment_consumed" in tags:
            return "consumed"
        if "segment_remaining" in tags:
            return "remaining"
        return None

    def _set_hover_segment(self, segment):
        if self._state.pinned:
            return
        if self._state.hover_segment == segment:
            return
        self._state.hover_segment = segment
        self._draw_donut()

    def _toggle_selected_segment(self, segment):
        selected = self._state.selected_segment
        self._state.selected_segment = None if selected == segment else segment
        self._draw_donut()

    def _active_segment(self):
        return self._state.selected_segment or self._state.hover_segment

    def _update_legend_visual(self):
        tone_fg = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
        bg = self.body.cget("bg")
        base_fg = self._aa_text(UI_THEME.get("muted_text", "#9AA4B2"), bg)
        active = self._active_segment()
        self.legend_consumed.configure(fg=self._aa_text(tone_fg if active == "consumed" else base_fg, bg))
        rem_fg = UI_THEME.get("remaining_active", UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))
        self.legend_remaining.configure(fg=self._aa_text(rem_fg if active == "remaining" else base_fg, bg))
        self.pin_btn.configure(fg=self._aa_text(tone_fg if self._state.pinned else base_fg, bg))

    def _update_inline_context(self):
        vals = list(self._sparkline_data or [0.0])
        last = vals[-1]
        avg = sum(vals) / max(1, len(vals))
        base = vals[0] if vals[0] != 0 else 1e-6
        delta = ((last - vals[0]) / base) * 100.0
        label = "Consumido" if self._active_segment() != "remaining" else "Restante"
        self.context_var.set(f"{label} • Último ciclo {last:.0f} • Média 7d {avg:.0f} • Variação {delta:+.0f}%")

    def _update_accessibility_colors(self):
        bg = self.body.cget("bg")
        muted = self._aa_text(UI_THEME.get("muted_text", "#9AA4B2"), bg)
        self.trend_lbl.configure(fg=muted)
        self.capacity_lbl.configure(fg=muted)
        self.meta_lbl.configure(fg=muted)
        self.context_lbl.configure(fg=muted)
        self.compare_lbl.configure(fg=muted)

    def _on_roving_focus(self, event=None):
        if not self._focus_targets:
            return "break"
        direction = -1 if getattr(event, "keysym", "") == "Left" else 1
        if event.widget in self._focus_targets:
            self._focus_index = self._focus_targets.index(event.widget)
        self._focus_index = (self._focus_index + direction) % len(self._focus_targets)
        target = self._focus_targets[self._focus_index]
        try:
            target.focus_set()
        except Exception:
            pass
        if target is self.legend_consumed:
            self._set_hover_segment("consumed")
        elif target is self.legend_remaining:
            self._set_hover_segment("remaining")
        return "break"

    def _on_clear_selection(self, _event=None):
        self._state.selected_segment = None
        self._state.hover_segment = None
        self._draw_donut()
        return "break"

    def _update_multi_pin_compare(self):
        if len(AppMetricCard._pinned_cards) < 2:
            self.compare_var.set("")
            return
        base = AppMetricCard._pinned_cards[0]
        if base is self and len(AppMetricCard._pinned_cards) > 1:
            base = AppMetricCard._pinned_cards[1]
        delta = self._capacity_percent - getattr(base, "_capacity_percent", 0.0)
        self.compare_var.set(f"Comparativo pinado • Δ {delta*100:+.1f}pp")

    def _schedule_hover_update(self, segment):
        self._pending_hover_segment = segment
        try:
            if self._hover_after:
                return
        except Exception:
            pass

        def _apply():
            self._hover_after = None
            self._set_hover_segment(self._pending_hover_segment)

        self._hover_after = self.after(16, _apply)

    def _on_donut_hover(self, _event=None):
        try:
            self._schedule_hover_update(self._segment_from_current())
        except Exception:
            pass

    def _on_donut_click(self, _event=None):
        segment = self._segment_from_current()
        if self._state.interaction_mode == "hover":
            self._set_hover_segment(segment)
            return
        if segment in {"consumed", "remaining"}:
            self._toggle_selected_segment(segment)
        else:
            self._state.selected_segment = None
            self._draw_donut()

    def _on_donut_leave(self, _event=None):
        self._set_hover_segment(None)

    def _toggle_pin(self, _event=None):
        self._state.pinned = not self._state.pinned
        if self._state.pinned:
            self._state.hover_segment = None
            if self not in AppMetricCard._pinned_cards:
                AppMetricCard._pinned_cards.append(self)
            if len(AppMetricCard._pinned_cards) > 2:
                oldest = AppMetricCard._pinned_cards.pop(0)
                oldest._state.pinned = False
                oldest._update_legend_visual()
        else:
            AppMetricCard._pinned_cards = [c for c in AppMetricCard._pinned_cards if c is not self]
        for card in list(AppMetricCard._pinned_cards) + [self]:
            try:
                card._update_multi_pin_compare()
            except Exception:
                pass
        self._update_legend_visual()
        self._draw_donut()

    def set_donut_visibility(self, visible: bool):
        self._donut_visible = bool(visible)
        if not self._donut_visible:
            self._state.hover_segment = None
            self._state.selected_segment = None
        try:
            if self._donut_visible:
                self.donut_canvas.pack(fill=tk.BOTH, expand=True)
                if self._enable_legend:
                    self.legend_wrap.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(2, 0))
            else:
                self.donut_canvas.pack_forget()
                self.legend_wrap.pack_forget()
        except Exception:
            pass
        self._draw_donut(force=True)

    def animate_capacity_fill(self, on_done=None, phase_one_ms: int = 420, phase_two_ms: int = 360, steps: int = 14):
        try:
            if self._donut_anim_after:
                self.after_cancel(self._donut_anim_after)
        except Exception:
            pass
        self._donut_anim_after = None
        self.set_donut_visibility(True)
        self._donut_consumed_progress = 0.0
        self._donut_remaining_progress = 0.0
        total_steps = max(1, int(steps))
        p1 = int(UI_THEME.get("duration_medium", phase_one_ms))
        p2 = int(UI_THEME.get("duration_fast", phase_two_ms))
        if self._low_motion():
            p1 = min(p1, 180)
            p2 = min(p2, 140)
        interval_one = max(16, int(p1 / total_steps))
        interval_two = max(16, int(p2 / total_steps))

        def _phase_two(idx=0):
            self._donut_remaining_progress = self._ease_by_token(idx / total_steps)
            self._draw_donut()
            if idx >= total_steps:
                self._donut_anim_after = None
                if callable(on_done):
                    try:
                        on_done()
                    except Exception:
                        pass
                return
            self._donut_anim_after = self.after(interval_two, lambda: _phase_two(idx + 1))

        def _phase_one(idx=0):
            self._donut_consumed_progress = self._ease_by_token(idx / total_steps)
            self._draw_donut()
            if idx >= total_steps:
                _phase_two(0)
                return
            self._donut_anim_after = self.after(interval_one, lambda: _phase_one(idx + 1))

        _phase_one(0)

    def set_density(self, mode: str = "confortavel"):
        try:
            self._apply_density(mode)
        except Exception:
            pass

    def _set_accent_progress(self, progress: float):
        self._accent_gradient_progress = self._ease_by_token(progress)
        self._draw_accent_gradient()

    def _draw_accent_gradient(self):
        try:
            self.accent_canvas.delete("all")
            w = max(2, int(self.accent_canvas.winfo_width()))
            h = max(24, int(self.accent_canvas.winfo_height()))
            hue = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
            top = UI_THEME.get("primary_active", "#1F6FEB")
            filled_h = int(h * self._accent_gradient_progress)
            y_start = h - filled_h
            steps = max(8, filled_h // 4) if filled_h > 0 else 0
            for idx in range(steps):
                t = idx / max(1, steps - 1)
                c = hue if t < 0.5 else top
                y0 = y_start + int((filled_h * idx) / max(1, steps))
                y1 = y_start + int((filled_h * (idx + 1)) / max(1, steps))
                self.accent_canvas.create_rectangle(0, y0, w, y1, fill=c, outline="")
        except Exception:
            pass

    def animate_accent_growth(self, duration_ms: int = 360, steps: int = 12, on_done=None):
        try:
            if self._accent_anim_after:
                self.after_cancel(self._accent_anim_after)
        except Exception:
            pass
        self._accent_anim_after = None
        total_steps = max(1, int(steps))
        dur = int(UI_THEME.get("duration_medium", duration_ms))
        if self._low_motion():
            dur = min(dur, 180)
        interval = max(16, int(dur / total_steps))
        self._set_accent_progress(0.0)

        target_text = str(self._target_value_text)
        digits = "".join(ch for ch in target_text if ch.isdigit())
        target_value = int(digits) if digits else None
        value_start_progress = 0.55
        value_has_started = False

        def _tick(step_idx=0):
            nonlocal value_has_started
            progress = self._ease_by_token(step_idx / total_steps)
            self._set_accent_progress(progress)

            if target_value is not None and progress >= value_start_progress:
                if not value_has_started:
                    value_has_started = True
                    self._value_revealed = True
                    self.value_var.set("0")
                rel = (progress - value_start_progress) / max(0.001, (1.0 - value_start_progress))
                rel = max(0.0, min(1.0, rel))
                self.value_var.set(str(int(round(target_value * rel))))

            if step_idx >= total_steps:
                self._accent_anim_after = None
                self._value_revealed = True
                self.value_var.set(target_text)
                if callable(on_done):
                    try:
                        on_done()
                    except Exception:
                        pass
                return
            self._accent_anim_after = self.after(interval, lambda: _tick(step_idx + 1))

        _tick(0)

    def _mix_hex(self, a: str, b: str, t: float):
        t = max(0.0, min(1.0, float(t)))
        try:
            ar, ag, ab = [int(a.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
            br, bg, bb = [int(b.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)]
            r = int(ar + ((br - ar) * t))
            g = int(ag + ((bg - ag) * t))
            b_ = int(ab + ((bb - ab) * t))
            return f"#{r:02X}{g:02X}{b_:02X}"
        except Exception:
            return b if t >= 0.5 else a

    def _set_card_lift_progress(self, progress: float):
        self._lift_progress = max(0.0, min(1.0, progress))
        bg = self._mix_hex(self._base_surface, self._lift_surface, self._lift_progress)
        border = self._mix_hex(self._shadow_idle, self._shadow_hover, self._lift_progress)
        try:
            self.configure(bg=bg, highlightbackground=border, highlightthickness=1 + int(round(self._lift_progress)))
            for widget in (self.body, self.text_column, self.top_row, self.donut_wrap, self.legend_wrap, self.accent_wrap):
                widget.configure(bg=bg)
            for widget in (self.sparkline, self.donut_canvas, self.title_lbl, self.value_lbl, self.trend_lbl, self.capacity_lbl, self.context_lbl, self.compare_lbl, self.meta_lbl, self.legend_consumed, self.legend_remaining, self.pin_btn, self.bottom_curve, self.accent_canvas):
                widget.configure(bg=bg)
            self._draw_bottom_curve()
            self._draw_donut(force=True)
            self._draw_sparkline(force=True)
        except Exception:
            pass

    def _animate_card_lift(self, lifted: bool):
        try:
            if self._lift_anim_after:
                self.after_cancel(self._lift_anim_after)
        except Exception:
            pass
        if self._low_motion():
            self._set_card_lift_progress(1.0 if lifted else 0.0)
            return
        start = self._lift_progress
        end = 1.0 if lifted else 0.0
        steps = 8
        interval = max(12, int(UI_THEME.get("duration_fast", 220) / steps))

        def _tick(idx=0):
            t = idx / steps
            eased = self._ease_by_token(t)
            self._set_card_lift_progress(start + ((end - start) * eased))
            if idx >= steps:
                self._lift_anim_after = None
                return
            self._lift_anim_after = self.after(interval, lambda: _tick(idx + 1))

        _tick(0)

    def _set_card_lift(self, lifted: bool):
        self._animate_card_lift(lifted)

    def _on_card_hover_enter(self, _event=None):
        self._animate_card_lift(True)

    def _on_card_hover_leave(self, _event=None):
        self._animate_card_lift(False)

    def _pulse_card_status(self):
        try:
            if self._pulse_after:
                self.after_cancel(self._pulse_after)
        except Exception:
            pass

        def _off():
            self._set_card_lift(False)
            self._pulse_after = None

        self._set_card_lift(True)
        dur = int(UI_THEME.get("duration_fast", 220))
        if self._low_motion():
            dur = min(dur, 120)
        self._pulse_after = self.after(dur, _off)

    def set_title(self, title: str, icon: str | None = None):
        if icon is not None:
            self._icon = icon
        self._title = str(title)
        limit = 24 if str(self._variant.get("density", "")).startswith("compact") else 36
        text = self._truncate_text(self._title, limit)
        self.title_var.set(f"{self._icon} {text}".strip())

    def flash(self, duration_ms: int = 280):
        try:
            self.configure(highlightbackground=UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7")), highlightthickness=2)
            if self._flash_after:
                self.after_cancel(self._flash_after)
            self._flash_after = self.after(duration_ms, lambda: self.configure(highlightbackground=self._shadow_idle, highlightthickness=1))
        except Exception:
            pass

    def set_value(self, value: str):
        self._target_value_text = str(value)
        if self._value_revealed:
            self.value_var.set(self._target_value_text)

    def set_trend(self, delta: int):
        if delta > 0:
            self.trend_var.set(f"Atenção • ↑ +{delta} vs último ciclo")
        elif delta < 0:
            self.trend_var.set(f"Crítico • ↓ {delta} vs último ciclo")
        else:
            self.trend_var.set("Info • → estável")

    def set_meta(self, text: str):
        self.meta_var.set(self._truncate_text(str(text), 52))
        self._metric_data.meta = self.meta_var.get()

    def set_capacity(self, consumed: int, limit: int):
        try:
            consumed_n = max(0, int(consumed))
        except Exception:
            consumed_n = 0
        try:
            limit_n = max(1, int(limit))
        except Exception:
            limit_n = 1
        remaining = max(limit_n - consumed_n, 0)
        self._capacity_consumed_n = consumed_n
        self._capacity_limit_n = limit_n
        self._capacity_percent = max(0.0, min(1.0, consumed_n / float(limit_n)))
        self._state.capacity_percent = self._capacity_percent

        prefix = "Info • "
        if consumed_n > limit_n:
            self._tone = "danger"
            prefix = "Crítico • "
            self._pulse_card_status()
            self.meta_var.set("Crítico: limite excedido")
        elif consumed_n >= int(0.85 * limit_n):
            self._tone = "warning"
            prefix = "Atenção • "
            self._pulse_card_status()
            self.meta_var.set("Atenção: próximo do limite")
        elif consumed_n <= int(0.35 * limit_n):
            self._tone = "success"
            prefix = "Saudável • "
        else:
            self._tone = normalize_tone(self._metric_data.status or self._tone)
        self.capacity_var.set(self._truncate_text(f"{prefix}Consumido {int(round(self._capacity_percent * 100))}% • {consumed_n} usados • {remaining} restantes", 70))

        self._metric_data.capacity_consumed = consumed_n
        self._metric_data.capacity_limit = limit_n
        self._metric_data.status = self._tone
        self.value_lbl.configure(fg=state_colors(self._tone)[0])
        self._update_inline_context()
        self._update_multi_pin_compare()
        self._draw_sparkline()
        self._draw_donut(force=True)



def build_app_tree(parent, columns, style="Control.Treeview"):
    wrap = build_card_frame(parent)
    tree = ttk.Treeview(wrap, columns=columns, show="headings", style=style)
    yscroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    return wrap, tree
