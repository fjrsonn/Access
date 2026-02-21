#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
METRICS_FILE = ROOT / "logs" / "ux_metrics_dashboard.json"
EVENTS_FILE = ROOT / "logs" / "runtime_events.jsonl"
BASELINE_FILE = ROOT / "config" / "ux_gate_baseline.json"


def fail(msg: str):
    print(f"[UX-GATE][FAIL] {msg}")
    sys.exit(1)


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


metrics = load_json(METRICS_FILE)
if not isinstance(metrics, dict):
    fail(f"Arquivo de métricas ausente/inválido: {METRICS_FILE}")

baseline = load_json(BASELINE_FILE)
if not isinstance(baseline, dict):
    fail(f"Baseline ausente/inválida para gate de release: {BASELINE_FILE}")

# 1) Contraste: não pode haver theme_contrast_alert ERROR no runtime log.
if EVENTS_FILE.exists():
    for raw in EVENTS_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if str(ev.get("action")) == "ux_metrics" and str(ev.get("stage")) == "theme_contrast_alert" and str(ev.get("status")) == "ERROR":
            fail("theme_contrast_alert em estado ERROR detectado no runtime_events.jsonl")

# 2) Gates de UX
current_p95 = float((metrics.get("time_to_apply_filter_ms") or {}).get("p95") or 0)
current_save = float(metrics.get("edit_save_success_rate") or 0)
current_shortcuts = float(metrics.get("keyboard_shortcut_adoption") or 0)
current_theme_switch = float(metrics.get("theme_switch_count") or 0)

max_p95 = float(baseline.get("max_time_to_apply_filter_p95_ms", current_p95))
min_save = float(baseline.get("min_edit_save_success_rate", current_save))
min_shortcuts = float(baseline.get("min_keyboard_shortcut_adoption", current_shortcuts))
max_theme_switch = float(baseline.get("max_theme_switch_count", current_theme_switch))

errors = []
if current_p95 > max_p95:
    errors.append(f"p95 filtro piorou: atual={current_p95} limite={max_p95}")
if current_save < min_save:
    errors.append(f"taxa de sucesso edição caiu: atual={current_save} mínimo={min_save}")
if current_shortcuts < min_shortcuts:
    errors.append(f"adoção de atalhos abaixo do mínimo: atual={current_shortcuts} mínimo={min_shortcuts}")
if current_theme_switch > max_theme_switch:
    errors.append(f"trocas de tema acima do limite: atual={current_theme_switch} limite={max_theme_switch}")

if errors:
    fail("; ".join(errors))

print("[UX-GATE][OK] métricas e contraste dentro dos limites.")
