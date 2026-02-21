"""Reusable UI components built on top of ui_theme tokens."""
from __future__ import annotations

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None
    ttk = None

from ui_theme import UI_THEME, theme_font, theme_space, build_card_frame, build_label, state_colors, normalize_tone


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


class AppMetricCard(tk.Frame):
    def __init__(self, parent, title: str, value: str = "0", tone: str = "info", icon: str = "●"):
        self._base_surface = UI_THEME.get("surface", "#151A22")
        self._lift_surface = UI_THEME.get("surface_alt", "#1B2430")
        self._shadow_idle = UI_THEME.get("shadow_1", UI_THEME.get("border", "#2B3442"))
        self._shadow_hover = UI_THEME.get("shadow_2", UI_THEME.get("primary", "#2F81F7"))
        super().__init__(parent, bg=self._base_surface, highlightthickness=1, highlightbackground=self._shadow_idle)
        self._tone = normalize_tone(tone)
        self._title = title
        self._icon = icon
        self._flash_after = None
        self._stagger_after = None
        self._pulse_after = None
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
        self._chart_state = {
            "capacity_percent": 0.0,
            "hover_segment": None,
            "selected_segment": None,
            "interaction_mode": "click-lock",
            "center_mode": "auto",
        }

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

        self.sparkline = tk.Canvas(self.text_column, height=32, highlightthickness=0, bd=0, bg=self._base_surface)
        self._sparkline_data = [0, 0, 0, 0, 0, 0, 0]

        self.donut_wrap = tk.Frame(self.body, bg=self._base_surface, height=170)
        self.donut_wrap.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(theme_space("space_1", 4), 0))
        self.donut_wrap.pack_propagate(False)
        self.donut_canvas = tk.Canvas(self.donut_wrap, width=1, height=1, bg=self._base_surface, highlightthickness=0, bd=0)

        self.legend_wrap = tk.Frame(self.body, bg=self._base_surface)
        self.legend_consumed = tk.Label(self.legend_wrap, text="● Consumido", bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), cursor="hand2")
        self.legend_remaining = tk.Label(self.legend_wrap, text="● Restante", bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), cursor="hand2")
        self.legend_consumed.pack(side=tk.LEFT, padx=(0, theme_space("space_2", 8)))
        self.legend_remaining.pack(side=tk.LEFT)

        self.title_lbl = tk.Label(self.body, textvariable=self.title_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.value_lbl = tk.Label(self.body, textvariable=self.value_var, bg=self._base_surface, fg=state_colors(self._tone)[0], font=theme_font("font_xl", "bold"))
        self.trend_lbl = tk.Label(self.body, textvariable=self.trend_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.capacity_lbl = tk.Label(self.body, textvariable=self.capacity_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.meta_lbl = tk.Label(self.body, textvariable=self.meta_var, bg=self._base_surface, fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))

        self._apply_density("confortavel")
        self.bottom_curve.bind("<Configure>", self._draw_bottom_curve, add="+")
        self.donut_canvas.bind("<Configure>", self._draw_donut, add="+")
        self.donut_canvas.bind("<Motion>", self._on_donut_hover, add="+")
        self.donut_canvas.bind("<Leave>", self._on_donut_leave, add="+")
        self.donut_canvas.bind("<Button-1>", self._on_donut_click, add="+")
        self.sparkline.bind("<Configure>", self._draw_sparkline, add="+")
        self.legend_consumed.bind("<Enter>", lambda _e: self._set_hover_segment("consumed"), add="+")
        self.legend_remaining.bind("<Enter>", lambda _e: self._set_hover_segment("remaining"), add="+")
        self.legend_consumed.bind("<Leave>", lambda _e: self._set_hover_segment(None), add="+")
        self.legend_remaining.bind("<Leave>", lambda _e: self._set_hover_segment(None), add="+")
        self.legend_consumed.bind("<Button-1>", lambda _e: self._toggle_selected_segment("consumed"), add="+")
        self.legend_remaining.bind("<Button-1>", lambda _e: self._toggle_selected_segment("remaining"), add="+")

        self.bind("<Enter>", self._on_card_hover_enter, add="+")
        self.bind("<Leave>", self._on_card_hover_leave, add="+")
        self.body.bind("<Enter>", self._on_card_hover_enter, add="+")
        self.body.bind("<Leave>", self._on_card_hover_leave, add="+")

        self.after(0, self._draw_bottom_curve)
        self.after(0, self._draw_donut)
        self.after(0, self._draw_sparkline)
        self.after(0, lambda: self._set_card_lift(False))

    def set_interaction_mode(self, mode: str = "click-lock"):
        self._chart_state["interaction_mode"] = "hover" if str(mode).strip().lower() == "hover" else "click-lock"
        if self._chart_state["interaction_mode"] == "hover":
            self._chart_state["selected_segment"] = None
            self._draw_donut()

    def set_center_mode(self, mode: str = "auto"):
        value = str(mode or "auto").strip().lower()
        if value not in {"auto", "consumed", "remaining"}:
            value = "auto"
        self._chart_state["center_mode"] = value
        self._draw_donut()

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
        self._draw_sparkline()

    def animate_entry_stagger(self, order: int = 0, base_delay_ms: int = 50, on_done=None):
        try:
            if self._stagger_after:
                self.after_cancel(self._stagger_after)
        except Exception:
            pass
        delay = max(0, int(order) * max(40, int(base_delay_ms)))

        def _run():
            self.animate_accent_growth()
            self.animate_capacity_fill(on_done=on_done)

        self._stagger_after = self.after(delay, _run)

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
        self.sparkline.pack(in_=self.text_column, fill=tk.X, pady=(2, 4))
        if self._donut_visible:
            self.donut_canvas.pack(fill=tk.BOTH, expand=True)
            self.legend_wrap.pack(fill=tk.X, padx=px, pady=(2, 0))
        else:
            self.donut_canvas.pack_forget()
            self.legend_wrap.pack_forget()
        self.trend_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.capacity_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.meta_lbl.pack(anchor="w", padx=px, pady=(0, py_bottom))

    def _draw_sparkline(self, _event=None):
        try:
            self.sparkline.delete("all")
            w = max(80, int(self.sparkline.winfo_width()))
            h = max(24, int(self.sparkline.winfo_height()))
            vals = self._sparkline_data[-7:]
            mn, mx = min(vals), max(vals)
            spread = max(1e-6, mx - mn)
            pad = 4
            step = (w - (2 * pad)) / max(1, len(vals) - 1)
            pts = []
            for idx, val in enumerate(vals):
                x = pad + (idx * step)
                y = pad + (h - (2 * pad)) * (1.0 - ((val - mn) / spread))
                pts.extend([x, y])
            line_color = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
            self.sparkline.create_line(*pts, smooth=True, width=2, fill=line_color)
            if pts:
                self.sparkline.create_oval(pts[-2] - 2, pts[-1] - 2, pts[-2] + 2, pts[-1] + 2, fill=line_color, outline="")
        except Exception:
            pass

    def _active_segment(self):
        selected = self._chart_state.get("selected_segment")
        hover = self._chart_state.get("hover_segment")
        return selected or hover

    def _center_info(self):
        mode = self._chart_state.get("center_mode", "auto")
        active = self._active_segment()
        if mode in {"consumed", "remaining"}:
            active = mode
        if active == "remaining":
            return f"{int(round((1.0 - self._capacity_percent) * 100))}%", "Restante"
        return f"{int(round(self._capacity_percent * 100))}%", "Consumido"

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

            active = self._active_segment()
            consumed_hovered = active == "consumed"
            remaining_hovered = active == "remaining"

            if consumed > 0:
                consumed_pad = hover_extra if consumed_hovered else 0
                self.donut_canvas.create_arc(
                    x0 - consumed_pad, y0 - consumed_pad, x1 + consumed_pad, y1 + consumed_pad,
                    start=90, extent=-(360.0 * consumed), style="arc", outline=fg_ring,
                    width=base_width + (3 if consumed_hovered else 0), tags=("segment", "segment_consumed"),
                )
            if remaining > 0:
                remaining_pad = hover_extra if remaining_hovered else 0
                self.donut_canvas.create_arc(
                    x0 - remaining_pad, y0 - remaining_pad, x1 + remaining_pad, y1 + remaining_pad,
                    start=90 - (360.0 * consumed), extent=-(360.0 * remaining), style="arc", outline=rem_ring,
                    width=base_width + (3 if remaining_hovered else 0), tags=("segment", "segment_remaining"),
                )

            pct_text, subtitle = self._center_info()
            main_color = UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3"))
            sub_color = UI_THEME.get("muted_text", "#9AA4B2")
            self.donut_canvas.create_text(w / 2, (h / 2) - 8, text=pct_text, fill=main_color, font=theme_font("font_xl", "bold"), tags=("label_center",))
            self.donut_canvas.create_text(w / 2, (h / 2) + 10, text=subtitle, fill=sub_color, font=theme_font("font_sm", "normal"), tags=("label_center",))
            self._update_legend_visual()
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
        if self._chart_state.get("hover_segment") == segment:
            return
        self._chart_state["hover_segment"] = segment
        self._draw_donut()

    def _toggle_selected_segment(self, segment):
        selected = self._chart_state.get("selected_segment")
        self._chart_state["selected_segment"] = None if selected == segment else segment
        self._draw_donut()

    def _update_legend_visual(self):
        tone_fg = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
        base_fg = UI_THEME.get("muted_text", "#9AA4B2")
        active = self._active_segment()
        self.legend_consumed.configure(fg=tone_fg if active == "consumed" else base_fg)
        self.legend_remaining.configure(fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")) if active == "remaining" else base_fg)

    def _on_donut_hover(self, _event=None):
        try:
            self._set_hover_segment(self._segment_from_current())
        except Exception:
            pass

    def _on_donut_click(self, _event=None):
        segment = self._segment_from_current()
        if self._chart_state.get("interaction_mode") == "hover":
            self._set_hover_segment(segment)
            return
        if segment in {"consumed", "remaining"}:
            self._toggle_selected_segment(segment)
        else:
            self._chart_state["selected_segment"] = None
            self._draw_donut()

    def _on_donut_leave(self, _event=None):
        if self._chart_state.get("interaction_mode") == "click-lock":
            self._set_hover_segment(None)
            return
        self._set_hover_segment(None)

    def set_donut_visibility(self, visible: bool):
        self._donut_visible = bool(visible)
        if not self._donut_visible:
            self._chart_state["hover_segment"] = None
            self._chart_state["selected_segment"] = None
        try:
            if self._donut_visible:
                self.donut_canvas.pack(fill=tk.BOTH, expand=True)
                self.legend_wrap.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(2, 0))
            else:
                self.donut_canvas.pack_forget()
                self.legend_wrap.pack_forget()
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

    def _set_accent_progress(self, progress: float):
        self._accent_gradient_progress = max(0.0, min(1.0, float(progress)))
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
        interval = max(16, int(duration_ms / total_steps))
        self._set_accent_progress(0.0)

        target_text = str(self._target_value_text)
        digits = "".join(ch for ch in target_text if ch.isdigit())
        target_value = int(digits) if digits else None
        value_start_progress = 0.55
        value_has_started = False

        def _tick(step_idx=0):
            nonlocal value_has_started
            progress = min(1.0, step_idx / total_steps)
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

    def _set_card_lift(self, lifted: bool):
        bg = self._lift_surface if lifted else self._base_surface
        border = self._shadow_hover if lifted else self._shadow_idle
        try:
            self.configure(bg=bg, highlightbackground=border, highlightthickness=2 if lifted else 1)
            for widget in (self.body, self.text_column, self.top_row, self.donut_wrap, self.legend_wrap, self.accent_wrap):
                widget.configure(bg=bg)
            self.sparkline.configure(bg=bg)
            self.donut_canvas.configure(bg=bg)
            self.title_lbl.configure(bg=bg)
            self.value_lbl.configure(bg=bg)
            self.trend_lbl.configure(bg=bg)
            self.capacity_lbl.configure(bg=bg)
            self.meta_lbl.configure(bg=bg)
            self.legend_consumed.configure(bg=bg)
            self.legend_remaining.configure(bg=bg)
            self.bottom_curve.configure(bg=bg)
            self.accent_canvas.configure(bg=bg)
            self._draw_bottom_curve()
            self._draw_donut()
            self._draw_sparkline()
        except Exception:
            pass

    def _on_card_hover_enter(self, _event=None):
        self._set_card_lift(True)

    def _on_card_hover_leave(self, _event=None):
        self._set_card_lift(False)

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
        self._pulse_after = self.after(int(UI_THEME.get("duration_fast", 220)), _off)

    def set_title(self, title: str, icon: str | None = None):
        if icon is not None:
            self._icon = icon
        self._title = str(title)
        self.title_var.set(f"{self._icon} {self._title}".strip())

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
            self.trend_var.set(f"↑ +{delta} vs último ciclo")
        elif delta < 0:
            self.trend_var.set(f"↓ {delta} vs último ciclo")
        else:
            self.trend_var.set("→ estável")

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
        self._chart_state["capacity_percent"] = self._capacity_percent
        self.capacity_var.set(f"Consumido {int(round(self._capacity_percent * 100))}% • {consumed_n} usados • {remaining} restantes")

        if consumed_n > limit_n:
            self._tone = "danger"
            self._pulse_card_status()
        elif consumed_n >= int(0.85 * limit_n):
            self._tone = "warning"
            self._pulse_card_status()
        self.value_lbl.configure(fg=state_colors(self._tone)[0])
        self._draw_sparkline()
        self._draw_donut()



def build_app_tree(parent, columns, style="Control.Treeview"):
    wrap = build_card_frame(parent)
    tree = ttk.Treeview(wrap, columns=columns, show="headings", style=style)
    yscroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    return wrap, tree
