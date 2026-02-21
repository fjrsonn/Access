"""Reusable UI components built on top of ui_theme tokens."""
from __future__ import annotations

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None
    ttk = None

from ui_theme import UI_THEME, theme_font, theme_space, build_card_frame, build_label, state_colors, normalize_tone, attach_tooltip


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
        self._apply_density("compacto" if self._operation_focus else "confortavel")
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


class AppMetricCard(tk.Frame):
    def __init__(self, parent, title: str, value: str = "0", tone: str = "info", icon: str = "●"):
        super().__init__(parent, bg=UI_THEME.get("surface", "#151A22"), highlightthickness=1, highlightbackground="#000000")
        self._tone = tone
        self._title = title
        self._icon = icon
        self._flash_after = None
        self.title_var = tk.StringVar(value=f"{icon} {title}")
        self._target_value_text = str(value)
        self._value_revealed = False
        self.value_var = tk.StringVar(value="")
        self.meta_var = tk.StringVar(value="Atualizado agora")
        self.trend_var = tk.StringVar(value="→ estável")
        self.capacity_var = tk.StringVar(value="0%")
        self._capacity_percent = 0.0
        self.accent_wrap = tk.Frame(self, bg=UI_THEME.get("surface", "#151A22"), width=4)
        self.accent_wrap.pack(side=tk.LEFT, fill=tk.Y)
        self.accent = tk.Frame(self.accent_wrap, bg=UI_THEME.get(tone, UI_THEME.get("primary", "#2F81F7")))
        self.accent.place(relx=0.0, rely=1.0, relwidth=1.0, relheight=0.0, anchor="sw")
        self._accent_anim_after = None
        self.body = tk.Frame(self, bg=UI_THEME.get("surface", "#151A22"))
        self.body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bottom_curve = tk.Canvas(self.body, height=1, bg=UI_THEME.get("surface", "#151A22"), highlightthickness=0, bd=0)
        self.bottom_curve.pack(side=tk.BOTTOM, fill=tk.X)
        self._donut_consumed_progress = 1.0
        self._donut_remaining_progress = 1.0
        self._donut_visible = False
        self._donut_anim_after = None
        self._donut_hover_segment = None
        self._capacity_consumed_n = 0
        self._capacity_limit_n = 1
        self._sparkline_points = []
        self._sparkline_max_points = 24
        self._sparkline_visible = True
        self._emphasis_mode = "secondary"
        self._trend_threshold = 2
        self._meta_visible = True
        self._operation_focus = False
        self._is_critical = False
        self._capacity_tooltip_bound = False
        self._metric_key = ""
        self._hide_title_in_operation = True
        self._disable_secondary_animation = False
        self.top_row = tk.Frame(self.body, bg=UI_THEME.get("surface", "#151A22"))
        self.top_row.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(theme_space("space_1", 4), 0))
        self.text_column = tk.Frame(self.top_row, bg=UI_THEME.get("surface", "#151A22"))
        self.text_column.pack(fill=tk.BOTH, expand=True)
        self.donut_wrap = tk.Frame(self.body, bg=UI_THEME.get("surface", "#151A22"), height=170)
        self.donut_wrap.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(theme_space("space_1", 4), 0))
        self.donut_wrap.pack_propagate(False)
        self.donut_canvas = tk.Canvas(
            self.donut_wrap,
            width=1,
            height=1,
            bg=UI_THEME.get("surface", "#151A22"),
            highlightthickness=0,
            bd=0,
        )
        self.title_lbl = tk.Label(self.body, textvariable=self.title_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.value_lbl = tk.Label(self.body, textvariable=self.value_var, bg=UI_THEME.get("surface", "#151A22"), fg=state_colors(tone)[0], font=theme_font("font_xl", "bold"))
        self.trend_lbl = tk.Label(self.body, textvariable=self.trend_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.sparkline = tk.Canvas(self.body, height=20, bg=UI_THEME.get("surface", "#151A22"), highlightthickness=0, bd=0)
        self.capacity_lbl = tk.Label(self.body, textvariable=self.capacity_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text_soft", UI_THEME.get("muted_text", "#9AA4B2")), font=theme_font("font_sm", "normal"))
        self.meta_lbl = tk.Label(self.body, textvariable=self.meta_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text_soft", UI_THEME.get("muted_text", "#9AA4B2")), font=theme_font("font_sm", "normal"))
        self._apply_density("confortavel")
        self.bottom_curve.bind("<Configure>", self._draw_bottom_curve, add="+")
        self.donut_canvas.bind("<Configure>", self._draw_donut, add="+")
        self.donut_canvas.bind("<Motion>", self._on_donut_hover, add="+")
        self.donut_canvas.bind("<Leave>", self._on_donut_leave, add="+")
        self.donut_canvas.bind("<Button-1>", self._on_donut_click, add="+")
        self.sparkline.bind("<Configure>", self._draw_sparkline, add="+")
        self.bind("<Enter>", lambda _e: self.set_donut_visibility(True), add="+")
        self.bind("<Leave>", lambda _e: self.set_donut_visibility(False), add="+")
        self.bind("<FocusIn>", lambda _e: self.set_donut_visibility(True), add="+")
        self.bind("<FocusOut>", lambda _e: self.set_donut_visibility(False), add="+")
        self.after(0, self._draw_bottom_curve)
        self.after(0, self._draw_donut)

    def _draw_bottom_curve(self, _event=None):
        try:
            w = max(20, int(self.bottom_curve.winfo_width()))
            h = max(1, int(self.bottom_curve.winfo_height()))
            card_bg = UI_THEME.get("surface", "#151A22")
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
        if self._operation_focus and self._hide_title_in_operation:
            self.title_lbl.pack_forget()
        else:
            self.title_lbl.pack(in_=self.text_column, anchor="w", padx=(0, 0), pady=(py_top, 0))
        self.value_lbl.pack(in_=self.text_column, anchor="w", padx=(0, 0), pady=(0, 0))
        if self._donut_visible:
            self.donut_canvas.pack(fill=tk.BOTH, expand=True)
        else:
            self.donut_canvas.pack_forget()
        self.trend_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        if self._sparkline_visible and not self._operation_focus:
            self.sparkline.pack(fill=tk.X, padx=px, pady=(0, 0))
        else:
            self.sparkline.pack_forget()
        self.capacity_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        if self._meta_visible:
            self.meta_lbl.pack(anchor="w", padx=px, pady=(0, py_bottom))
        else:
            self.meta_lbl.pack_forget()
        self._draw_sparkline()

    def _draw_sparkline(self, _event=None):
        try:
            self.sparkline.delete("all")
            if not self._sparkline_visible:
                return
            points = self._sparkline_points[-self._sparkline_max_points:]
            if len(points) < 2:
                return
            w = max(40, int(self.sparkline.winfo_width()))
            h = max(12, int(self.sparkline.winfo_height()))
            vmin = min(points)
            vmax = max(points)
            span = max(1.0, float(vmax - vmin))
            n = len(points) - 1
            coords = []
            for i, value in enumerate(points):
                x = int((i / max(1, n)) * (w - 2)) + 1
                y = int((1.0 - ((value - vmin) / span)) * (h - 4)) + 2
                coords.extend((x, y))
            median = sorted(points)[len(points) // 2]
            median_y = int((1.0 - ((median - vmin) / span)) * (h - 4)) + 2
            self.sparkline.create_line(1, median_y, w - 1, median_y, fill=UI_THEME.get("muted_text_soft", UI_THEME.get("muted_text", "#9AA4B2")), dash=(3, 2), width=1)
            line_color = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
            self.sparkline.create_line(*coords, fill=line_color, width=2, smooth=False)
            direction_up = points[-1] >= points[-2]
            dot_tone = self._tone
            if self._metric_key in {"pendentes", "sem_contato"}:
                dot_tone = "danger" if direction_up else "success"
            elif self._metric_key in {"avisado"}:
                dot_tone = "success" if direction_up else "danger"
            dot_color = UI_THEME.get(dot_tone, line_color)
            self.sparkline.create_oval(coords[-2] - 2, coords[-1] - 2, coords[-2] + 2, coords[-1] + 2, fill=dot_color, outline="")
        except Exception:
            pass

    def _draw_donut(self, _event=None):
        try:
            self.donut_canvas.delete("all")
            if not self._donut_visible:
                return
            w = max(40, int(self.donut_canvas.winfo_width()))
            h = max(40, int(self.donut_canvas.winfo_height()))
            base_width = 12
            hover_extra = 6
            max_stroke = base_width + 3
            safe_margin = hover_extra + (max_stroke / 2) + 2
            size = max(20, min(w, h) - (2 * safe_margin))
            x0 = (w - size) / 2
            y0 = (h - size) / 2
            x1 = x0 + size
            y1 = y0 + size
            fg_ring = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
            rem_ring = UI_THEME.get("surface_alt", "#1B2430")
            consumed = max(0.0, min(1.0, self._capacity_percent * self._donut_consumed_progress))
            remaining_total = max(0.0, 1.0 - self._capacity_percent)
            remaining = max(0.0, min(1.0, remaining_total * self._donut_remaining_progress))

            consumed_hovered = self._donut_hover_segment == "consumed"
            remaining_hovered = self._donut_hover_segment == "remaining"

            if consumed > 0:
                consumed_pad = hover_extra if consumed_hovered else 0
                self.donut_canvas.create_arc(
                    x0 - consumed_pad,
                    y0 - consumed_pad,
                    x1 + consumed_pad,
                    y1 + consumed_pad,
                    start=90,
                    extent=-(360.0 * consumed),
                    style="arc",
                    outline=fg_ring,
                    width=base_width + (3 if consumed_hovered else 0),
                    tags=("segment", "segment_consumed"),
                )
            if remaining > 0:
                remaining_pad = hover_extra if remaining_hovered else 0
                self.donut_canvas.create_arc(
                    x0 - remaining_pad,
                    y0 - remaining_pad,
                    x1 + remaining_pad,
                    y1 + remaining_pad,
                    start=90 - (360.0 * consumed),
                    extent=-(360.0 * remaining),
                    style="arc",
                    outline=rem_ring,
                    width=base_width + (3 if remaining_hovered else 0),
                    tags=("segment", "segment_remaining"),
                )
            self.donut_canvas.create_text(
                w / 2,
                h / 2,
                text=self._center_percentage_text(),
                fill=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")),
                font=theme_font("font_sm", "bold"),
                tags=("label_center",),
            )
        except Exception:
            pass

    def _center_percentage_text(self) -> str:
        if self._donut_hover_segment == "consumed":
            return f"{int(round(self._capacity_percent * 100))}%"
        if self._donut_hover_segment == "remaining":
            return f"{int(round((1.0 - self._capacity_percent) * 100))}%"
        return f"{int(round(self._capacity_percent * 100))}%"

    def _on_donut_hover(self, _event=None):
        try:
            current = self.donut_canvas.find_withtag("current")
            segment = None
            if current:
                tags = set(self.donut_canvas.gettags(current[0]))
                if "segment_consumed" in tags:
                    segment = "consumed"
                elif "segment_remaining" in tags:
                    segment = "remaining"
            if segment != self._donut_hover_segment:
                self._donut_hover_segment = segment
                self._draw_donut()
        except Exception:
            pass

    def _on_donut_click(self, _event=None):
        self._on_donut_hover(_event)

    def _on_donut_leave(self, _event=None):
        if self._donut_hover_segment is None:
            return
        self._donut_hover_segment = None
        self._draw_donut()

    def set_donut_visibility(self, visible: bool):
        self._donut_visible = bool(visible)
        if not self._donut_visible:
            self._donut_hover_segment = None
        try:
            if self._donut_visible:
                self.donut_canvas.pack(fill=tk.BOTH, expand=True)
            else:
                self.donut_canvas.pack_forget()
        except Exception:
            pass
        self._draw_donut()


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
        interval_one = max(16, int(phase_one_ms / total_steps))
        interval_two = max(16, int(phase_two_ms / total_steps))

        def _phase_two(idx=0):
            self._donut_remaining_progress = min(1.0, idx / total_steps)
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
            self._donut_consumed_progress = min(1.0, idx / total_steps)
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

    def set_emphasis(self, mode: str = "secondary"):
        self._emphasis_mode = "primary" if str(mode).lower().startswith("pri") else "secondary"
        try:
            if self._emphasis_mode == "primary":
                self.value_lbl.configure(font=theme_font("font_xl", "bold"))
                self.configure(highlightthickness=2, highlightbackground=UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7")))
            else:
                self.value_lbl.configure(font=theme_font("font_lg", "bold"))
                self.configure(highlightthickness=1, highlightbackground=UI_THEME.get("border", "#2B3442"))
        except Exception:
            pass

    def set_sparkline_visibility(self, visible: bool):
        self._sparkline_visible = bool(visible)
        self._apply_density("confortavel")

    def set_metric_key(self, metric_key: str):
        self._metric_key = str(metric_key or "").strip().lower()

    def set_secondary_animation_enabled(self, enabled: bool):
        self._disable_secondary_animation = not bool(enabled)

    def set_meta_visibility(self, visible: bool):
        self._meta_visible = bool(visible)
        self._apply_density("confortavel")

    def set_operation_focus(self, enabled: bool, critical: bool = False):
        self._operation_focus = bool(enabled)
        self._is_critical = bool(critical)
        if self._operation_focus:
            self.set_donut_visibility(False)
            self.set_meta_visibility(False)
        try:
            if self._operation_focus and not self._is_critical:
                muted = UI_THEME.get("muted_text_soft", UI_THEME.get("muted_text", "#9AA4B2"))
                self.value_lbl.configure(fg=muted)
                self.trend_lbl.configure(fg=muted)
                self.title_lbl.configure(fg=muted)
            else:
                tone_color = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
                self.value_lbl.configure(fg=tone_color)
                self.trend_lbl.configure(fg=UI_THEME.get("muted_text", "#9AA4B2"))
                self.title_lbl.configure(fg=UI_THEME.get("muted_text", "#9AA4B2"))
        except Exception:
            pass

    def push_history_value(self, value: int | float):
        try:
            v = float(value)
        except Exception:
            return
        self._sparkline_points.append(v)
        if len(self._sparkline_points) > self._sparkline_max_points:
            self._sparkline_points = self._sparkline_points[-self._sparkline_max_points:]
        self._draw_sparkline()


    def _set_accent_progress(self, progress: float):
        p = max(0.0, min(1.0, float(progress)))
        try:
            self.accent.configure(bg=UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7")))
            self.accent.place_configure(relheight=p, rely=1.0, relx=0.0, relwidth=1.0, anchor="sw")
        except Exception:
            pass

    def animate_accent_growth(self, duration_ms: int = 360, steps: int = 12, on_done=None):
        if self._disable_secondary_animation:
            self._value_revealed = True
            self.value_var.set(str(self._target_value_text))
            if callable(on_done):
                on_done()
            return
        try:
            if self._accent_anim_after:
                self.after_cancel(self._accent_anim_after)
        except Exception:
            pass
        self._accent_anim_after = None
        total_steps = max(1, int(steps))
        interval = max(16, int(duration_ms / total_steps))
        self._set_accent_progress(0.0)

        target_text = str(self._target_value_text)
        digits = "".join(ch for ch in target_text if ch.isdigit())
        target_value = int(digits) if digits else None
        value_start_progress = 0.55
        value_has_started = False

        def _format_value(v: int):
            if target_text.isdigit():
                return str(v)
            return str(v)

        def _tick(step_idx=0):
            nonlocal value_has_started
            progress = min(1.0, step_idx / total_steps)
            self._set_accent_progress(progress)

            if target_value is not None:
                if progress >= value_start_progress:
                    if not value_has_started:
                        value_has_started = True
                        self._value_revealed = True
                        self.value_var.set("0")
                    rel = (progress - value_start_progress) / max(0.001, (1.0 - value_start_progress))
                    rel = max(0.0, min(1.0, rel))
                    current = int(round(target_value * rel))
                    self.value_var.set(_format_value(current))

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

    def set_title(self, title: str, icon: str | None = None):
        if icon is not None:
            self._icon = icon
        self._title = str(title)
        self.title_var.set(f"{self._icon} {self._title}".strip())

    def flash(self, duration_ms: int = 280):
        if self._disable_secondary_animation:
            return
        try:
            self.configure(highlightbackground=UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7")), highlightthickness=2)
            if self._flash_after:
                self.after_cancel(self._flash_after)
            self._flash_after = self.after(duration_ms, lambda: self.configure(highlightbackground="#000000", highlightthickness=1))
        except Exception:
            pass

    def set_value(self, value: str):
        self._target_value_text = str(value)
        if self._value_revealed:
            self.value_var.set(self._target_value_text)

    def set_trend(self, delta: int, metric_key: str | None = None, threshold: int | None = None, rate_label: str | None = None):
        metric = str(metric_key or "").lower().strip()
        local_threshold = int(threshold) if threshold is not None else int(self._trend_threshold)
        if abs(int(delta)) < local_threshold:
            self.trend_var.set("→ estável")
            self.trend_lbl.configure(fg=UI_THEME.get("muted_text", "#9AA4B2"))
            return
        impact_up_bad = metric in {"pendentes", "sem_contato"}
        impact_up_good = metric in {"avisado"}
        trend_tone = "info"
        if delta > 0:
            self.trend_var.set(f"↑ +{delta} vs último ciclo")
            if impact_up_bad:
                trend_tone = "danger"
            elif impact_up_good:
                trend_tone = "success"
        elif delta < 0:
            self.trend_var.set(f"↓ {delta} vs último ciclo")
            if impact_up_bad:
                trend_tone = "success"
            elif impact_up_good:
                trend_tone = "danger"
        else:
            self.trend_var.set("→ estável")
        if rate_label:
            self.trend_var.set(f"{self.trend_var.get()} • {rate_label}")
        self.trend_lbl.configure(fg=UI_THEME.get(trend_tone, UI_THEME.get("muted_text", "#9AA4B2")))

    def set_meta(self, text: str):
        self.meta_var.set(str(text))

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
        short_txt = f"{int(round(self._capacity_percent * 100))}%"
        self.capacity_var.set(short_txt)
        if not self._capacity_tooltip_bound:
            attach_tooltip(self.capacity_lbl, "Capacidade do card: percentual consumido do limite configurado.")
            self._capacity_tooltip_bound = True
        self._draw_donut()



def build_app_tree(parent, columns, style="Control.Treeview"):
    wrap = build_card_frame(parent)
    tree = ttk.Treeview(wrap, columns=columns, show="headings", style=style)
    yscroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    return wrap, tree
