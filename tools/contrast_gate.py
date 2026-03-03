#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui_theme import THEME_PRESETS, validate_theme_contrast


def main() -> int:
    failed = False
    for name, theme in THEME_PRESETS.items():
        out = validate_theme_contrast(theme)
        warnings = out.get("warnings") or {}
        if warnings:
            failed = True
            print(f"[contrast_gate] {name}: FAIL {warnings}")
        else:
            print(f"[contrast_gate] {name}: OK {out.get('ratios')}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
