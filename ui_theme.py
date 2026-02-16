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
