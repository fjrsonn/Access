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
        self.capacity_var = tk.StringVar(value="Consumido 0% • 0 usados • 0 restantes")
        self._capacity_percent = 0.0
        self.accent_wrap = tk.Frame(self, bg=UI_THEME.get("surface", "#151A22"), width=4)
        self.accent_wrap.pack(side=tk.LEFT, fill=tk.Y)
        self.accent = tk.Frame(self.accent_wrap, bg=UI_THEME.get(tone, UI_THEME.get("primary", "#2F81F7")))
        self.accent.place(relx=0.0, rely=1.0, relwidth=1.0, relheight=0.0, anchor="sw")
        self._accent_anim_after = None
        self.body = tk.Frame(self, bg=UI_THEME.get("surface", "#151A22"))
        self.body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bottom_curve = tk.Canvas(self.body, height=28, bg=UI_THEME.get("surface", "#151A22"), highlightthickness=0, bd=0)
        self.bottom_curve.pack(side=tk.BOTTOM, fill=tk.X)
        self._donut_consumed_progress = 1.0
        self._donut_remaining_progress = 1.0
        self._donut_anim_after = None
        self.donut_wrap = tk.Frame(self.body, bg=UI_THEME.get("surface", "#151A22"))
        self.donut_canvas = tk.Canvas(
            self.donut_wrap,
            width=84,
            height=84,
            bg=UI_THEME.get("surface", "#151A22"),
            highlightthickness=0,
            bd=0,
        )
        self.title_lbl = tk.Label(self.body, textvariable=self.title_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.value_lbl = tk.Label(self.body, textvariable=self.value_var, bg=UI_THEME.get("surface", "#151A22"), fg=state_colors(tone)[0], font=theme_font("font_xl", "bold"))
        self.trend_lbl = tk.Label(self.body, textvariable=self.trend_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.capacity_lbl = tk.Label(self.body, textvariable=self.capacity_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self.meta_lbl = tk.Label(self.body, textvariable=self.meta_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm", "normal"))
        self._apply_density("confortavel")
        self.bottom_curve.bind("<Configure>", self._draw_bottom_curve, add="+")
        self.donut_canvas.bind("<Configure>", self._draw_donut, add="+")
        self.after(0, self._draw_bottom_curve)
        self.after(0, self._draw_donut)

    def _draw_bottom_curve(self, _event=None):
        try:
            w = max(20, int(self.bottom_curve.winfo_width()))
            h = max(8, int(self.bottom_curve.winfo_height()))
            card_bg = UI_THEME.get("surface", "#151A22")
            cutout_bg = UI_THEME.get("bg", "#0D1117")
            self.bottom_curve.configure(bg=card_bg)
            self.bottom_curve.delete("all")

            # base reta do retângulo
            self.bottom_curve.create_rectangle(0, 0, w, h, fill=card_bg, outline="")

            # círculo de fundo com metade visível no final do retângulo, sem encostar nele
            gap_top = 4
            radius = max(9, min(w // 8, (h - gap_top) // 2))
            cx = w // 2
            cy = gap_top
            self.bottom_curve.create_oval(
                cx - radius,
                cy - radius,
                cx + radius,
                cy + radius,
                outline="",
                width=0,
                fill=cutout_bg,
            )
        except Exception:
            pass

    def _apply_density(self, mode: str = "confortavel"):
        compact = str(mode).lower().startswith("compact")
        px = theme_space("space_1", 4) if compact else theme_space("space_2", 8)
        py_top = theme_space("space_1", 4)
        py_bottom = theme_space("space_1", 4) if compact else theme_space("space_2", 8)
        self.title_lbl.pack(anchor="w", padx=px, pady=(py_top, 0))
        self.value_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.donut_wrap.pack(fill=tk.X, padx=px, pady=(theme_space("space_1", 4), theme_space("space_1", 4)))
        self.donut_canvas.pack(anchor="center")
        self.trend_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.capacity_lbl.pack(anchor="w", padx=px, pady=(0, 0))
        self.meta_lbl.pack(anchor="w", padx=px, pady=(0, py_bottom))

    def _draw_donut(self, _event=None):
        try:
            self.donut_canvas.delete("all")
            w = max(40, int(self.donut_canvas.winfo_width()))
            h = max(40, int(self.donut_canvas.winfo_height()))
            size = min(w, h) - 6
            x0 = (w - size) / 2
            y0 = (h - size) / 2
            x1 = x0 + size
            y1 = y0 + size
            fg_ring = UI_THEME.get(self._tone, UI_THEME.get("primary", "#2F81F7"))
            rem_ring = UI_THEME.get("surface_alt", "#1B2430")
            consumed = max(0.0, min(1.0, self._capacity_percent * self._donut_consumed_progress))
            remaining_total = max(0.0, 1.0 - self._capacity_percent)
            remaining = max(0.0, min(1.0, remaining_total * self._donut_remaining_progress))

            if consumed > 0:
                self.donut_canvas.create_arc(
                    x0,
                    y0,
                    x1,
                    y1,
                    start=90,
                    extent=-(360.0 * consumed),
                    style="arc",
                    outline=fg_ring,
                    width=9,
                )
            if remaining > 0:
                self.donut_canvas.create_arc(
                    x0,
                    y0,
                    x1,
                    y1,
                    start=90 - (360.0 * consumed),
                    extent=-(360.0 * remaining),
                    style="arc",
                    outline=rem_ring,
                    width=9,
                )
            self.donut_canvas.create_text(
                w / 2,
                h / 2,
                text=f"{int(round(self._capacity_percent * 100))}%",
                fill=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")),
                font=theme_font("font_sm", "bold"),
            )
        except Exception:
            pass


    def animate_capacity_fill(self, on_done=None, phase_one_ms: int = 420, phase_two_ms: int = 360, steps: int = 14):
        try:
            if self._donut_anim_after:
                self.after_cancel(self._donut_anim_after)
        except Exception:
            pass
        self._donut_anim_after = None
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
