"""Shared UI theme and reusable Tkinter component helpers."""
from __future__ import annotations

try:
    import tkinter as tk
except Exception:  # pragma: no cover - GUI optional
    tk = None

UI_THEME = {
    "bg": "#0F1115",
    "surface": "#151A22",
    "surface_alt": "#1B2430",
    "border": "#2B3442",
    "text": "#E6EDF3",
    "muted_text": "#9AA4B2",
    "primary": "#2F81F7",
    "primary_active": "#1F6FEB",
    "success": "#2DA44E",
    "danger": "#DA3633",
    "warning": "#D29922",
    "focus_bg": "#F0F6FC",
    "focus_text": "#111827",
    "edit_badge_bg": "#F8E3A3",
    "edit_badge_text": "#111111",
    "status_avisado_text": "#6EE7B7",
    "status_sem_contato_text": "#FCA5A5",
    "light_bg": "#F5F7FA",
    "light_border": "#D1D5DB",
}

THEME_PRESETS = {
    "escuro": dict(UI_THEME),
    "claro": {
        "bg": "#F3F4F6",
        "surface": "#FFFFFF",
        "surface_alt": "#E5E7EB",
        "border": "#D1D5DB",
        "text": "#111827",
        "muted_text": "#6B7280",
        "primary": "#2563EB",
        "primary_active": "#1D4ED8",
        "success": "#15803D",
        "danger": "#B91C1C",
        "warning": "#B45309",
        "focus_bg": "#DBEAFE",
        "focus_text": "#111827",
        "edit_badge_bg": "#FEF3C7",
        "edit_badge_text": "#111827",
        "status_avisado_text": "#166534",
        "status_sem_contato_text": "#B91C1C",
        "light_bg": "#F5F7FA",
        "light_border": "#D1D5DB",
    },
    "alto_contraste": {
        "bg": "#000000",
        "surface": "#000000",
        "surface_alt": "#111111",
        "border": "#FFFFFF",
        "text": "#FFFFFF",
        "muted_text": "#E5E7EB",
        "primary": "#00A3FF",
        "primary_active": "#0077CC",
        "success": "#00FF7F",
        "danger": "#FF4D4D",
        "warning": "#FFD700",
        "focus_bg": "#FFFFFF",
        "focus_text": "#000000",
        "edit_badge_bg": "#FFD700",
        "edit_badge_text": "#000000",
        "status_avisado_text": "#00FF7F",
        "status_sem_contato_text": "#FF4D4D",
        "light_bg": "#000000",
        "light_border": "#FFFFFF",
    },
}

_ACTIVE_THEME = "escuro"


def available_theme_names():
    return list(THEME_PRESETS.keys())


def get_active_theme_name():
    return _ACTIVE_THEME


def apply_theme(name: str):
    global _ACTIVE_THEME
    key = (name or "").strip().lower()
    if key not in THEME_PRESETS:
        key = "escuro"
    UI_THEME.clear()
    UI_THEME.update(THEME_PRESETS[key])
    _ACTIVE_THEME = key
    return key


def _hex_to_rgb(value: str):
    v = (value or "").strip().lstrip("#")
    if len(v) == 3:
        v = "".join(ch * 2 for ch in v)
    if len(v) != 6:
        return (0, 0, 0)
    return (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))


def _luminance(rgb):
    def _c(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * _c(r) + 0.7152 * _c(g) + 0.0722 * _c(b)


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    l1 = _luminance(_hex_to_rgb(hex_a))
    l2 = _luminance(_hex_to_rgb(hex_b))
    high, low = max(l1, l2), min(l1, l2)
    return (high + 0.05) / (low + 0.05)


def validate_theme_contrast(theme: dict | None = None) -> dict:
    th = theme or UI_THEME
    checks = {
        "text_on_surface": contrast_ratio(th.get("text", "#fff"), th.get("surface", "#000")),
        "text_on_primary": contrast_ratio(th.get("text", "#fff"), th.get("primary", "#000")),
        "text_on_surface_alt": contrast_ratio(th.get("text", "#fff"), th.get("surface_alt", "#000")),
    }
    warnings = {k: round(v, 2) for k, v in checks.items() if v < 4.5}
    return {"ratios": {k: round(v, 2) for k, v in checks.items()}, "warnings": warnings}



def bind_focus_ring(widget):
    def _on_focus_in(_):
        try:
            widget.configure(highlightbackground=UI_THEME["primary"], highlightcolor=UI_THEME["primary"], highlightthickness=2)
        except Exception:
            pass

    def _on_focus_out(_):
        try:
            widget.configure(highlightbackground=UI_THEME["border"], highlightcolor=UI_THEME["border"], highlightthickness=1)
        except Exception:
            pass

    try:
        widget.bind("<FocusIn>", _on_focus_in, add="+")
        widget.bind("<FocusOut>", _on_focus_out, add="+")
    except Exception:
        pass


def bind_button_states(btn, base_bg, hover_bg):
    def _on_enter(_):
        try:
            btn.configure(bg=hover_bg)
        except Exception:
            pass

    def _on_leave(_):
        try:
            btn.configure(bg=base_bg)
        except Exception:
            pass

    try:
        btn.bind("<Enter>", _on_enter, add="+")
        btn.bind("<Leave>", _on_leave, add="+")
    except Exception:
        pass


def build_card_frame(parent):
    return tk.Frame(parent, bg=UI_THEME["surface"], highlightbackground=UI_THEME["border"], highlightthickness=1)


def build_primary_button(parent, text, command, padx=12):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=UI_THEME["primary"],
        fg=UI_THEME["text"],
        activebackground=UI_THEME["primary_active"],
        activeforeground=UI_THEME["text"],
        disabledforeground=UI_THEME["muted_text"],
        relief="flat",
        padx=padx,
        highlightthickness=1,
        highlightbackground=UI_THEME["border"],
        highlightcolor=UI_THEME["primary"],
    )
    bind_focus_ring(btn)
    bind_button_states(btn, UI_THEME["primary"], UI_THEME["primary_active"])
    return btn


def build_secondary_button(parent, text, command, padx=12):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=UI_THEME["surface_alt"],
        fg=UI_THEME["text"],
        activebackground=UI_THEME["border"],
        activeforeground=UI_THEME["text"],
        disabledforeground=UI_THEME["muted_text"],
        relief="flat",
        padx=padx,
        highlightthickness=1,
        highlightbackground=UI_THEME["border"],
        highlightcolor=UI_THEME["primary"],
    )
    bind_focus_ring(btn)
    bind_button_states(btn, UI_THEME["surface_alt"], UI_THEME["border"])
    return btn


def build_filter_input(parent, textvariable=None, width=12):
    ent = tk.Entry(
        parent,
        textvariable=textvariable,
        bg=UI_THEME["surface_alt"],
        fg=UI_THEME["text"],
        insertbackground=UI_THEME["text"],
        relief="flat",
        width=width,
        disabledbackground=UI_THEME["surface"],
        disabledforeground=UI_THEME["muted_text"],
        highlightthickness=1,
        highlightbackground=UI_THEME["border"],
        highlightcolor=UI_THEME["primary"],
    )
    bind_focus_ring(ent)
    return ent
