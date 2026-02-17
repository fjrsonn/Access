"""Reusable UI components built on top of ui_theme tokens."""
from __future__ import annotations

try:
    import tkinter as tk
    from tkinter import ttk
except Exception:  # pragma: no cover
    tk = None
    ttk = None

from ui_theme import UI_THEME, theme_font, theme_space, build_card_frame, build_label


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


class AppStatusBar(tk.Frame):
    def __init__(self, parent, text: str = ""):
        super().__init__(parent, bg=UI_THEME.get("surface_alt", "#1B2430"), highlightthickness=1, highlightbackground=UI_THEME.get("border", "#2B3442"))
        self.var = tk.StringVar(value=text)
        self.lbl = tk.Label(self, textvariable=self.var, anchor="w", bg=UI_THEME.get("surface_alt", "#1B2430"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), font=theme_font("font_sm"))
        self.lbl.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=theme_space("space_1", 4))

    def set(self, text: str, tone: str = "info"):
        self.var.set(text)
        bg = UI_THEME.get(tone, UI_THEME.get("surface_alt", "#1B2430"))
        fg = UI_THEME.get(f"on_{tone}", UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")))
        self.configure(bg=bg)
        self.lbl.configure(bg=bg, fg=fg)


class AppMetricCard(tk.Frame):
    def __init__(self, parent, title: str, value: str = "0", tone: str = "info"):
        super().__init__(parent, bg=UI_THEME.get("surface", "#151A22"), highlightthickness=1, highlightbackground=UI_THEME.get("border", "#2B3442"))
        self.title_var = tk.StringVar(value=title)
        self.value_var = tk.StringVar(value=value)
        self.title_lbl = tk.Label(self, textvariable=self.title_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm"))
        self.value_lbl = tk.Label(self, textvariable=self.value_var, bg=UI_THEME.get("surface", "#151A22"), fg=UI_THEME.get(f"on_{tone}", UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3"))), font=theme_font("font_xl", "bold"))
        self.title_lbl.pack(anchor="w", padx=theme_space("space_2", 8), pady=(theme_space("space_1", 4), 0))
        self.value_lbl.pack(anchor="w", padx=theme_space("space_2", 8), pady=(0, theme_space("space_2", 8)))

    def set_value(self, value: str):
        self.value_var.set(str(value))



def build_app_tree(parent, columns, style="Control.Treeview"):
    wrap = build_card_frame(parent)
    tree = ttk.Treeview(wrap, columns=columns, show="headings", style=style)
    yscroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=yscroll.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    yscroll.pack(side=tk.RIGHT, fill=tk.Y)
    return wrap, tree
