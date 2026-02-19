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
    "on_primary": "#0B1117",
    "on_surface": "#E6EDF3",
    "success": "#2DA44E",
    "on_success": "#08120C",
    "danger": "#DA3633",
    "on_danger": "#FFFFFF",
    "warning": "#D29922",
    "on_warning": "#111827",
    "focus_bg": "#F0F6FC",
    "focus_text": "#111827",
    "edit_badge_bg": "#F8E3A3",
    "edit_badge_text": "#111111",
    "status_avisado_text": "#6EE7B7",
    "status_sem_contato_text": "#FCA5A5",
    "editor_bg": "#0B0F14",
    "editor_text": "#E6EDF3",
    "editor_insert": "#E6EDF3",
    "overlay_text": "#6B7280",
    "banner_success_bg": "#2DA44E",
    "banner_success_text": "#08120C",
    "banner_error_bg": "#DA3633",
    "banner_error_text": "#FFFFFF",
    "light_bg": "#F5F7FA",
    "light_border": "#D1D5DB",
    "font_family": "Segoe UI",
    "font_sm": 9,
    "font_md": 10,
    "font_lg": 11,
    "font_xl": 12,
    "radius_sm": 4,
    "radius_md": 8,
    "space_1": 4,
    "space_2": 8,
    "space_3": 12,
    "space_4": 16,
    "space_5": 20,
    "space_6": 24,
    "disabled_bg": "#2B3442",
    "disabled_fg": "#9AA4B2",
    "info": "#2563EB",
    "on_info": "#FFFFFF",
    "selection_bg": "#1F6FEB",
    "selection_fg": "#E6EDF3",
}

THEME_PRESETS = {
    "escuro": dict(UI_THEME),
    "vscode": {
        "bg": "#1E1E1E",
        "surface": "#252526",
        "surface_alt": "#2D2D2D",
        "border": "#3C3C3C",
        "text": "#D4D4D4",
        "muted_text": "#A6A6A6",
        "primary": "#0E639C",
        "primary_active": "#1177BB",
        "on_primary": "#FFFFFF",
        "on_surface": "#D4D4D4",
        "success": "#16825D",
        "on_success": "#FFFFFF",
        "danger": "#F14C4C",
        "on_danger": "#000000",
        "warning": "#CCA700",
        "on_warning": "#000000",
        "focus_bg": "#094771",
        "focus_text": "#FFFFFF",
        "edit_badge_bg": "#CCA700",
        "edit_badge_text": "#000000",
        "status_avisado_text": "#89D185",
        "status_sem_contato_text": "#F48771",
        "editor_bg": "#1E1E1E",
        "editor_text": "#D4D4D4",
        "editor_insert": "#AEAFAD",
        "overlay_text": "#8C8C8C",
        "banner_success_bg": "#16825D",
        "banner_success_text": "#FFFFFF",
        "banner_error_bg": "#F14C4C",
        "banner_error_text": "#000000",
        "light_bg": "#1E1E1E",
        "light_border": "#3C3C3C",
        "font_family": "Segoe UI",
        "font_sm": 9,
        "font_md": 10,
        "font_lg": 11,
        "font_xl": 12,
        "radius_sm": 4,
        "radius_md": 8,
        "space_1": 4,
        "space_2": 8,
        "space_3": 12,
        "space_4": 16,
        "space_5": 20,
        "space_6": 24,
        "disabled_bg": "#3C3C3C",
        "disabled_fg": "#A6A6A6",
        "info": "#3794FF",
        "on_info": "#000000",
        "selection_bg": "#094771",
        "selection_fg": "#FFFFFF",
    },
    "claro": {
        "bg": "#F3F4F6",
        "surface": "#FFFFFF",
        "surface_alt": "#E5E7EB",
        "border": "#D1D5DB",
        "text": "#111827",
        "muted_text": "#6B7280",
        "primary": "#2563EB",
        "primary_active": "#1D4ED8",
        "on_primary": "#FFFFFF",
        "on_surface": "#111827",
        "success": "#15803D",
        "on_success": "#FFFFFF",
        "danger": "#B91C1C",
        "on_danger": "#FFFFFF",
        "warning": "#B45309",
        "on_warning": "#FFFFFF",
        "focus_bg": "#DBEAFE",
        "focus_text": "#111827",
        "edit_badge_bg": "#FEF3C7",
        "edit_badge_text": "#111827",
        "status_avisado_text": "#166534",
        "status_sem_contato_text": "#B91C1C",
        "editor_bg": "#FFFFFF",
        "editor_text": "#111827",
        "editor_insert": "#111827",
        "overlay_text": "#6B7280",
        "banner_success_bg": "#15803D",
        "banner_success_text": "#FFFFFF",
        "banner_error_bg": "#B91C1C",
        "banner_error_text": "#FFFFFF",
        "light_bg": "#F5F7FA",
        "light_border": "#D1D5DB",
        "font_family": "Segoe UI",
        "font_sm": 9,
        "font_md": 10,
        "font_lg": 11,
        "font_xl": 12,
        "radius_sm": 4,
        "radius_md": 8,
        "space_1": 4,
        "space_2": 8,
        "space_3": 12,
        "space_4": 16,
        "space_5": 20,
        "space_6": 24,
        "disabled_bg": "#E5E7EB",
        "disabled_fg": "#6B7280",
        "info": "#2563EB",
        "on_info": "#FFFFFF",
        "selection_bg": "#2563EB",
        "selection_fg": "#FFFFFF",
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
        "on_primary": "#000000",
        "on_surface": "#FFFFFF",
        "success": "#00FF7F",
        "on_success": "#000000",
        "danger": "#FF4D4D",
        "on_danger": "#000000",
        "warning": "#FFD700",
        "on_warning": "#000000",
        "focus_bg": "#FFFFFF",
        "focus_text": "#000000",
        "edit_badge_bg": "#FFD700",
        "edit_badge_text": "#000000",
        "status_avisado_text": "#00FF7F",
        "status_sem_contato_text": "#FF4D4D",
        "editor_bg": "#000000",
        "editor_text": "#FFFFFF",
        "editor_insert": "#FFFFFF",
        "overlay_text": "#E5E7EB",
        "banner_success_bg": "#00FF7F",
        "banner_success_text": "#000000",
        "banner_error_bg": "#FF4D4D",
        "banner_error_text": "#000000",
        "light_bg": "#000000",
        "light_border": "#FFFFFF",
        "font_family": "Segoe UI",
        "font_sm": 9,
        "font_md": 10,
        "font_lg": 11,
        "font_xl": 12,
        "radius_sm": 4,
        "radius_md": 8,
        "space_1": 4,
        "space_2": 8,
        "space_3": 12,
        "space_4": 16,
        "space_5": 20,
        "space_6": 24,
        "disabled_bg": "#111111",
        "disabled_fg": "#E5E7EB",
        "info": "#00A3FF",
        "on_info": "#000000",
        "selection_bg": "#00A3FF",
        "selection_fg": "#000000",
    },
}

_ACTIVE_THEME = "escuro"
_ACTIVE_TYPOGRAPHY = "padrao"

TYPOGRAPHY_PRESETS = {
    "compacto": {"font_sm": 8, "font_md": 9, "font_lg": 10, "font_xl": 11},
    "padrao": {"font_sm": 9, "font_md": 10, "font_lg": 11, "font_xl": 12},
    "acessivel": {"font_sm": 11, "font_md": 12, "font_lg": 13, "font_xl": 15},
}


def available_theme_names():
    return list(THEME_PRESETS.keys())


def get_active_theme_name():
    return _ACTIVE_THEME


def available_typography_names():
    return list(TYPOGRAPHY_PRESETS.keys())


def get_active_typography_name():
    return _ACTIVE_TYPOGRAPHY


def apply_theme(name: str):
    global _ACTIVE_THEME
    key = (name or "").strip().lower()
    if key not in THEME_PRESETS:
        key = "escuro"
    UI_THEME.clear()
    UI_THEME.update(THEME_PRESETS[key])
    _ACTIVE_THEME = key
    return key


def apply_typography(name: str):
    global _ACTIVE_TYPOGRAPHY
    key = (name or "").strip().lower()
    if key not in TYPOGRAPHY_PRESETS:
        key = "padrao"
    UI_THEME.update(TYPOGRAPHY_PRESETS[key])
    _ACTIVE_TYPOGRAPHY = key
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



# Estado visual padronizado para evitar divergência entre componentes.
# Prioridade de destaque (do mais crítico para o menos crítico):
# danger > warning > success > info
STATE_PRIORITY = {"danger": 4, "warning": 3, "success": 2, "info": 1}


def normalize_tone(tone: str) -> str:
    t = str(tone or "info").strip().lower()
    aliases = {"error": "danger", "ok": "success"}
    return aliases.get(t, t if t in {"info", "success", "warning", "danger"} else "info")


def state_colors(tone: str) -> tuple[str, str]:
    t = normalize_tone(tone)
    bg = UI_THEME.get(t, UI_THEME.get("info", "#2563EB"))
    fg = UI_THEME.get(f"on_{t}", UI_THEME.get("on_info", UI_THEME.get("text", "#E6EDF3")))
    return bg, fg

def validate_theme_contrast(theme: dict | None = None) -> dict:
    th = theme or UI_THEME
    checks = {
        "text_on_surface": contrast_ratio(th.get("on_surface", th.get("text", "#fff")), th.get("surface", "#000")),
        "text_on_primary": contrast_ratio(th.get("on_primary", th.get("text", "#fff")), th.get("primary", "#000")),
        "text_on_surface_alt": contrast_ratio(th.get("text", "#fff"), th.get("surface_alt", "#000")),
        "text_on_warning": contrast_ratio(th.get("on_warning", th.get("on_surface", th.get("text", "#fff"))), th.get("warning", "#000")),
        "text_on_danger": contrast_ratio(th.get("on_danger", th.get("on_surface", th.get("text", "#fff"))), th.get("danger", "#000")),
        "text_on_success": contrast_ratio(th.get("on_success", th.get("on_surface", th.get("text", "#fff"))), th.get("success", "#000")),
    }
    warnings = {k: round(v, 2) for k, v in checks.items() if v < 4.5}
    return {"ratios": {k: round(v, 2) for k, v in checks.items()}, "warnings": warnings}



def bind_focus_ring(widget, focus_thickness=2, blur_thickness=1):
    def _on_focus_in(_):
        try:
            widget.configure(highlightbackground=UI_THEME["primary"], highlightcolor=UI_THEME["primary"], highlightthickness=focus_thickness)
        except Exception:
            pass

    def _on_focus_out(_):
        try:
            widget.configure(highlightbackground=UI_THEME["border"], highlightcolor=UI_THEME["border"], highlightthickness=blur_thickness)
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
        fg=UI_THEME.get("on_primary", UI_THEME["text"]),
        activebackground=UI_THEME["primary_active"],
        activeforeground=UI_THEME.get("on_primary", UI_THEME["text"]),
        disabledforeground=UI_THEME["muted_text"],
        relief="flat",
        padx=padx,
        highlightthickness=1,
        highlightbackground=UI_THEME["border"],
        highlightcolor=UI_THEME["primary"],
    )
    bind_focus_ring(btn, focus_thickness=3, blur_thickness=1)
    bind_button_states(btn, UI_THEME["primary"], UI_THEME["primary_active"])
    return btn


def build_secondary_button(parent, text, command, padx=12):
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=UI_THEME["surface_alt"],
        fg=UI_THEME.get("on_surface", UI_THEME["text"]),
        activebackground=UI_THEME["border"],
        activeforeground=UI_THEME.get("on_surface", UI_THEME["text"]),
        disabledforeground=UI_THEME["muted_text"],
        relief="flat",
        padx=padx,
        highlightthickness=1,
        highlightbackground=UI_THEME["border"],
        highlightcolor=UI_THEME["primary"],
    )
    bind_focus_ring(btn, focus_thickness=2, blur_thickness=1)
    bind_button_states(btn, UI_THEME["surface_alt"], UI_THEME["border"])
    return btn




def _build_semantic_secondary_button(parent, text, command, tone="warning", padx=12):
    base_bg = UI_THEME.get("surface_alt", "#1B2430")
    hover_bg = UI_THEME.get(tone, UI_THEME.get("border", "#2B3442"))
    btn = tk.Button(
        parent,
        text=text,
        command=command,
        bg=base_bg,
        fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")),
        activebackground=hover_bg,
        activeforeground=UI_THEME.get(f"on_{tone}", UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3"))),
        disabledforeground=UI_THEME.get("muted_text", "#9AA4B2"),
        relief="flat",
        padx=padx,
        highlightthickness=1,
        highlightbackground=UI_THEME.get("border", "#2B3442"),
        highlightcolor=UI_THEME.get("primary", "#2F81F7"),
    )
    bind_focus_ring(btn, focus_thickness=2, blur_thickness=1)
    bind_button_states(btn, base_bg, hover_bg)
    return btn


def build_secondary_warning_button(parent, text, command, padx=12):
    return _build_semantic_secondary_button(parent, text, command, tone="warning", padx=padx)


def build_secondary_danger_button(parent, text, command, padx=12):
    return _build_semantic_secondary_button(parent, text, command, tone="danger", padx=padx)
def build_filter_input(parent, textvariable=None, width=12):
    ent = tk.Entry(
        parent,
        textvariable=textvariable,
        bg=UI_THEME["surface_alt"],
        fg=UI_THEME.get("on_surface", UI_THEME["text"]),
        insertbackground=UI_THEME.get("on_surface", UI_THEME["text"]),
        relief="flat",
        width=width,
        disabledbackground=UI_THEME.get("disabled_bg", UI_THEME["surface"]),
        disabledforeground=UI_THEME.get("disabled_fg", UI_THEME["muted_text"]),
        highlightthickness=1,
        highlightbackground=UI_THEME["border"],
        highlightcolor=UI_THEME["primary"],
    )
    bind_focus_ring(ent, focus_thickness=3, blur_thickness=1)
    return ent


def build_label(parent, text, muted=False, **kwargs):
    return tk.Label(
        parent,
        text=text,
        bg=kwargs.pop("bg", UI_THEME["surface"]),
        fg=kwargs.pop("fg", UI_THEME["muted_text"] if muted else UI_THEME.get("on_surface", UI_THEME["text"])),
        **kwargs,
    )


def build_badge(parent, text, tone="warning", **kwargs):
    tone_bg, tone_fg = state_colors(tone)
    return tk.Label(parent, text=text, bg=tone_bg, fg=tone_fg, padx=10, pady=4, **kwargs)


def build_banner(parent, tone="success", **kwargs):
    t = normalize_tone(tone)
    if t == "danger":
        bg = UI_THEME.get("banner_error_bg", state_colors("danger")[0])
        fg = UI_THEME.get("banner_error_text", state_colors("danger")[1])
    else:
        bg = UI_THEME.get("banner_success_bg", state_colors(t)[0])
        fg = UI_THEME.get("banner_success_text", state_colors(t)[1])
    return tk.Label(parent, text="", bg=bg, fg=fg, **kwargs)


def theme_font(size_key="font_md", weight="normal"):
    return (UI_THEME.get("font_family", "Segoe UI"), UI_THEME.get(size_key, 10), weight)


def theme_space(key="space_2", fallback=8):
    return int(UI_THEME.get(key, fallback))


def apply_ttk_theme_styles(root=None):
    try:
        from tkinter import ttk
    except Exception:
        return
    try:
        style = ttk.Style(root)
        style.theme_use("clam")
    except Exception:
        style = ttk.Style(root)
    try:
        style.configure("TCombobox", fieldbackground=UI_THEME.get("surface_alt", "#1B2430"), background=UI_THEME.get("surface_alt", "#1B2430"), foreground=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), arrowcolor=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), bordercolor=UI_THEME.get("border", "#2B3442"), lightcolor=UI_THEME.get("border", "#2B3442"), darkcolor=UI_THEME.get("border", "#2B3442"))
        style.map("TCombobox", fieldbackground=[("readonly", UI_THEME.get("surface_alt", "#1B2430")), ("focus", UI_THEME.get("surface_alt", "#1B2430"))], foreground=[("readonly", UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3"))), ("focus", UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))], bordercolor=[("focus", UI_THEME.get("primary", "#2F81F7"))], lightcolor=[("focus", UI_THEME.get("primary", "#2F81F7"))], darkcolor=[("focus", UI_THEME.get("primary", "#2F81F7"))])
        style.configure("Vertical.TScrollbar", troughcolor=UI_THEME.get("surface", "#151A22"), background=UI_THEME.get("surface_alt", "#1B2430"), arrowcolor=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))
        style.configure("Horizontal.TScrollbar", troughcolor=UI_THEME.get("surface", "#151A22"), background=UI_THEME.get("surface_alt", "#1B2430"), arrowcolor=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))
    except Exception:
        pass


def refresh_theme(widget_tree, context="default"):
    if widget_tree is None or tk is None:
        return
    apply_ttk_theme_styles(widget_tree)

    ctx = str(context or "default").lower()
    if ctx in {"interfacetwo", "monitor"}:
        container_bg = UI_THEME.get("bg", "#0F1115")
    else:
        container_bg = UI_THEME.get("light_bg", UI_THEME.get("bg", "#0F1115"))

    def _walk(w):
        yield w
        try:
            for ch in w.winfo_children():
                yield from _walk(ch)
        except Exception:
            return

    for w in _walk(widget_tree):
        klass = str(getattr(w, "winfo_class", lambda: "")() or "")
        try:
            if klass in {"Frame", "Labelframe", "Toplevel"}:
                w.configure(bg=container_bg)
            elif klass == "Label":
                cur_bg = None
                try:
                    cur_bg = w.cget("bg")
                except Exception:
                    cur_bg = container_bg
                base_bg = cur_bg if cur_bg in {UI_THEME.get("surface"), UI_THEME.get("surface_alt"), UI_THEME.get("primary")} else container_bg
                w.configure(bg=base_bg, fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))
            elif klass == "Text":
                w.configure(bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), insertbackground=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))
            elif klass == "Entry":
                st = None
                try:
                    st = str(w.cget("state"))
                except Exception:
                    st = None
                if st == "disabled":
                    w.configure(disabledbackground=UI_THEME.get("disabled_bg", UI_THEME.get("surface", "#151A22")), disabledforeground=UI_THEME.get("disabled_fg", UI_THEME.get("muted_text", "#9AA4B2")))
                else:
                    w.configure(bg=UI_THEME.get("surface_alt", "#1B2430"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), insertbackground=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))
        except Exception:
            pass


def attach_tooltip(widget, text):
    tip = {"win": None}

    def _show(_e=None):
        if not text or tip["win"] is not None:
            return
        try:
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            x = widget.winfo_rootx() + 10
            y = widget.winfo_rooty() + widget.winfo_height() + 8
            tw.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(tw, text=text, bg=UI_THEME.get("surface_alt", "#1B2430"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), relief="solid", bd=1, padx=6, pady=4, font=theme_font("font_sm"))
            lbl.pack()
            tip["win"] = tw
        except Exception:
            tip["win"] = None

    def _hide(_e=None):
        try:
            if tip["win"] is not None:
                tip["win"].destroy()
        except Exception:
            pass
        tip["win"] = None

    try:
        widget.bind("<Enter>", _show, add="+")
        widget.bind("<Leave>", _hide, add="+")
        widget.bind("<ButtonPress>", _hide, add="+")
    except Exception:
        pass
