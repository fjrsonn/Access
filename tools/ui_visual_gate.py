#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_MARKERS = {
    "interfacetwo.py": [
        'Densidade:',
        'Exportar CSV',
        'Resetar colunas',
        'Salvar visão',
        'Focus mode',
        'values=["Compacto", "Confortável"]',
        'tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Control.Treeview", selectmode="extended")',
    ],
    "ui_components.py": [
        'class AppMetricCard',
        'self.accent = tk.Frame',
        'def set_density',
        'def flash',
    ],
    "ui_theme.py": [
        'STATE_PRIORITY = {"danger": 4, "warning": 3, "success": 2, "info": 1}',
        'def state_colors',
        'def normalize_tone',
    ],
}


def main() -> int:
    missing: list[str] = []
    for rel, markers in REQUIRED_MARKERS.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        for m in markers:
            if m not in text:
                missing.append(f"{rel}: missing marker {m}")
    if missing:
        print("[ui_visual_gate] FAIL")
        for m in missing:
            print(" -", m)
        return 1
    print("[ui_visual_gate] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
