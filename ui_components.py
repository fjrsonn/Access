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
        super().__init__(
            parent,
            bg=UI_THEME.get("surface", "#151A22"),
            highlightthickness=0,
            highlightbackground=UI_THEME.get("border", "#2B3442"),
            bd=0,
        )
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
        self.capacity_var = tk.StringVar(value="Consumido 0% • 0 usados • 0 restantes")
        self._capacity_percent = 0.0
        self._card_shadow_shift_x = 1.8
        self._card_shadow_shift_y = 2.4
        self._card_shadow_steps = 7
        container_bg = UI_THEME.get("bg", "#0F1115")
        try:
            container_bg = parent.cget("bg")
        except Exception:
            pass
        self._card_shadow_canvas = tk.Canvas(
            self,
            bg=container_bg,
            highlightthickness=0,
            bd=0,
        )
        self._card_shadow_canvas.pack(fill=tk.BOTH, expand=True)
        self.card_shell = tk.Frame(
            self._card_shadow_canvas,
            bg=UI_THEME.get("surface", "#151A22"),
            highlightthickness=1,
            highlightbackground=UI_THEME.get("border", "#2B3442"),
            bd=0,
        )
        self._card_shell_window = self._card_shadow_canvas.create_window(0, 0, anchor="nw", window=self.card_shell)
        self.accent_wrap = tk.Frame(self.card_shell, bg=UI_THEME.get("surface", "#151A22"), width=4)
        self.accent_wrap.pack(side=tk.LEFT, fill=tk.Y)
        self.accent = tk.Frame(self.accent_wrap, bg=UI_THEME.get(tone, UI_THEME.get("primary", "#2F81F7")))
        self.accent.place(relx=0.0, rely=1.0, relwidth=1.0, relheight=0.0, anchor="sw")
        self._accent_anim_after = None
        self.body = tk.Frame(self.card_shell, bg=UI_THEME.get("surface", "#151A22"))
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
        self.top_row = tk.Frame(self.body, bg=UI_THEME.get("surface", "#151A22"))
        self.top_row.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4) // 2, 0))
        self.text_column = tk.Frame(self.top_row, bg=UI_THEME.get("surface", "#151A22"))
        self.text_column.pack(fill=tk.BOTH, expand=True)
        self.donut_wrap = tk.Frame(self.body, bg=UI_THEME.get("surface", "#151A22"), height=120)
        self.donut_wrap.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4) // 2, 0))
        self.donut_wrap.pack_propagate(False)
        self.donut_canvas = tk.Canvas(
            self.donut_wrap,
            width=1,
            height=1,
            bg=UI_THEME.get("surface", "#151A22"),
            highlightthickness=0,
            bd=0,
        )
        self.title_lbl = tk.Label(self.body, textvariable=self.title_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), anchor="w", justify="left")
        self.value_lbl = tk.Label(self.body, textvariable=self.value_var, bg=UI_THEME.get("surface", "#151A22"), fg=state_colors(tone)[0], font=theme_font("font_xl", "bold"), anchor="w", justify="left")
        self.trend_lbl = tk.Label(self.body, textvariable=self.trend_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), anchor="w", justify="left")
        self.capacity_lbl = tk.Label(self.body, textvariable=self.capacity_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), anchor="w", justify="left")
        self.meta_lbl = tk.Label(self.body, textvariable=self.meta_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"), anchor="w", justify="left")
        self._apply_density("confortavel")
        self._card_shadow_canvas.bind("<Configure>", self._draw_card_shadow, add="+")
        self.body.bind("<Configure>", self._apply_text_wrap, add="+")
        self.bottom_curve.bind("<Configure>", self._draw_bottom_curve, add="+")
        self.donut_canvas.bind("<Configure>", self._draw_donut, add="+")
        self.donut_canvas.bind("<Motion>", self._on_donut_hover, add="+")
        self.donut_canvas.bind("<Leave>", self._on_donut_leave, add="+")
        self.donut_canvas.bind("<Button-1>", self._on_donut_click, add="+")
        self.after(0, self._draw_card_shadow)
        self.after(0, self._draw_bottom_curve)
        self.after(0, self._draw_donut)

    def _draw_card_shadow(self, _event=None):
        try:
            canvas = self._card_shadow_canvas
            canvas.delete("card_shadow")
            self.card_shell.update_idletasks()
            content_w = max(8, int(self.card_shell.winfo_reqwidth()))
            content_h = max(8, int(self.card_shell.winfo_reqheight()))
            canvas_w = int(canvas.winfo_width())
            canvas_h = int(canvas.winfo_height())
            available_w = content_w if canvas_w <= 1 else max(8, canvas_w)
            available_h = content_h if canvas_h <= 1 else max(content_h, canvas_h)

            canvas.coords(self._card_shell_window, 0, 0)
            canvas.itemconfigure(self._card_shell_window, width=available_w, height=content_h)
            canvas.configure(scrollregion=(0, 0, available_w, available_h))
        except Exception:
            pass

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

    def _apply_text_wrap(self, _event=None):
        try:
            body_w = max(120, int(self.body.winfo_width()))
            wrap = max(90, body_w - (2 * theme_space("space_3", 10)))
            self.title_lbl.configure(wraplength=wrap)
            for lbl in (self.trend_lbl, self.capacity_lbl, self.meta_lbl):
                lbl.configure(wraplength=wrap, justify="left")
        except Exception:
            pass

    def _apply_density(self, mode: str = "confortavel"):
        compact = str(mode).lower().startswith("compact")
        px = theme_space("space_1", 4) if compact else theme_space("space_3", 10)
        py_top = theme_space("space_1", 4)
        py_bottom = theme_space("space_1", 4) if compact else theme_space("space_1", 4)
        self.title_lbl.pack(in_=self.text_column, fill=tk.X, anchor="w", padx=(0, 0), pady=(py_top, 0))
        self.value_lbl.pack(in_=self.text_column, fill=tk.X, anchor="w", padx=(0, 0), pady=(0, 0))
        if self._donut_visible:
            self.donut_canvas.pack(fill=tk.BOTH, expand=True)
        else:
            self.donut_canvas.pack_forget()
        self.trend_lbl.pack(fill=tk.X, anchor="w", padx=px, pady=(0, 0))
        self.capacity_lbl.pack(fill=tk.X, anchor="w", padx=px, pady=(0, 0))
        self.meta_lbl.pack(fill=tk.X, anchor="w", padx=px, pady=(0, py_bottom))
        self._apply_text_wrap()
        self.after_idle(self._draw_card_shadow)

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
            rem_ring = self._blend_hex(UI_THEME.get("surface_alt", "#1B2430"), UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), 0.18)
            consumed = max(0.0, min(1.0, self._capacity_percent * self._donut_consumed_progress))
            remaining_total = max(0.0, 1.0 - self._capacity_percent)
            remaining = max(0.0, min(1.0, remaining_total * self._donut_remaining_progress))

            consumed_hovered = self._donut_hover_segment == "consumed"
            remaining_hovered = self._donut_hover_segment == "remaining"

            shadow_shift_x = float(self._card_shadow_shift_x)
            shadow_shift_y = float(self._card_shadow_shift_y)
            shadow_steps = int(self._card_shadow_steps)
            shadow_bg = UI_THEME.get("surface", "#151A22")

            def _draw_shadow_arc(start_angle: float, extent_angle: float, pad: float, hovered: bool):
                if abs(extent_angle) <= 0.001:
                    return
                base_shadow_width = (base_width + 3) if hovered else (base_width + 1)
                for shadow_idx in range(shadow_steps):
                    opacity = 1.0 - (shadow_idx / float(shadow_steps - 1))
                    shadow_tone = self._blend_hex("#000000", shadow_bg, 1.0 - opacity)
                    spread = shadow_idx * 0.6
                    stroke = max(1, int(round(base_shadow_width - (shadow_idx * 0.5))))
                    self.donut_canvas.create_arc(
                        x0 - pad - spread + shadow_shift_x,
                        y0 - pad - spread + shadow_shift_y,
                        x1 + pad + spread + shadow_shift_x,
                        y1 + pad + spread + shadow_shift_y,
                        start=start_angle,
                        extent=extent_angle,
                        style="arc",
                        outline=shadow_tone,
                        width=stroke,
                    )

            if consumed > 0:
                consumed_pad = hover_extra if consumed_hovered else 0
                _draw_shadow_arc(90, -(360.0 * consumed), consumed_pad, consumed_hovered)

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
                _draw_shadow_arc(
                    90 - (360.0 * consumed),
                    -(360.0 * remaining),
                    remaining_pad,
                    remaining_hovered,
                )
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

    @staticmethod
    def _blend_hex(color_a: str, color_b: str, amount: float) -> str:
        def _to_rgb(value: str) -> tuple[int, int, int]:
            clean = str(value).strip().lstrip("#")
            if len(clean) == 3:
                clean = "".join(ch * 2 for ch in clean)
            if len(clean) != 6:
                return (0, 0, 0)
            try:
                return tuple(int(clean[idx:idx + 2], 16) for idx in (0, 2, 4))
            except ValueError:
                return (0, 0, 0)

        mix = max(0.0, min(1.0, float(amount)))
        a_r, a_g, a_b = _to_rgb(color_a)
        b_r, b_g, b_b = _to_rgb(color_b)
        out = (
            int(round((a_r * (1.0 - mix)) + (b_r * mix))),
            int(round((a_g * (1.0 - mix)) + (b_g * mix))),
            int(round((a_b * (1.0 - mix)) + (b_b * mix))),
        )
        return f"#{out[0]:02x}{out[1]:02x}{out[2]:02x}"

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
        self.after_idle(self._draw_card_shadow)


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
        p = max(0.0, min(1.0, float(progress)))
        try:
            self.accent.configure(bg=UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7")))
            self.accent.place_configure(relheight=p, rely=1.0, relx=0.0, relwidth=1.0, anchor="sw")
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
        try:
            self.card_shell.configure(
                highlightbackground=UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7")),
                highlightthickness=2,
            )
            if self._flash_after:
                self.after_cancel(self._flash_after)
            self._flash_after = self.after(
                duration_ms,
                lambda: self.card_shell.configure(
                    highlightbackground=UI_THEME.get("border", "#2B3442"),
                    highlightthickness=1,
                ),
            )
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
        self.capacity_var.set(
            f"Consumido {int(round(self._capacity_percent * 100))}% • {consumed_n} usados • {remaining} restantes"
        )
        self._draw_donut()



def build_app_tree(parent, columns, style="Control.Treeview"):
    wrap = build_card_frame(parent)
    tree = ttk.Treeview(wrap, columns=columns, show="headings", style=style)
    yscroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    return wrap, tree
