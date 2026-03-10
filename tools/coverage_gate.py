#!/usr/bin/env python3
"""Coverage gate por módulo crítico sem dependências externas.

Usa o módulo stdlib `trace` para contar linhas executadas durante a suíte de testes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unittest
from pathlib import Path
from trace import Trace

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THRESHOLDS = {
    "ia.py": 18.0,
    "interfaceone.py": 10.0,
    "main.py": 35.0,
}


def _candidate_lines(path: Path) -> set[int]:
    lines: set[int] = set()
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped in {"else:", "try:", "finally:"}:
            continue
        lines.add(idx)
    return lines


def _run_tests_with_trace(test_pattern: str = "tests"):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    tracer = Trace(count=1, trace=0)

    def _runner():
        suite = unittest.defaultTestLoader.discover(test_pattern)
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        if not result.wasSuccessful():
            raise SystemExit(1)

    tracer.runfunc(_runner)
    return tracer.results().counts


def _module_coverage(counts: dict, module_file: str) -> tuple[float, int, int]:
    path = (ROOT / module_file).resolve()
    candidates = _candidate_lines(path)
    if not candidates:
        return 100.0, 0, 0
    executed = 0
    for line in candidates:
        if counts.get((str(path), line), 0) > 0:
            executed += 1
    pct = round((executed / len(candidates)) * 100.0, 2)
    return pct, executed, len(candidates)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "coverage_gate.json"))
    parser.add_argument("--threshold", action="append", default=[], help="module.py=percent")
    args = parser.parse_args()

    thresholds = dict(DEFAULT_THRESHOLDS)
    for item in args.threshold:
        if "=" not in item:
            raise SystemExit(f"threshold inválido: {item}")
        mod, val = item.split("=", 1)
        thresholds[mod.strip()] = float(val)

    counts = _run_tests_with_trace("tests")

    report = {"modules": {}, "thresholds": thresholds, "ok": True}
    for module, threshold in thresholds.items():
        pct, executed, total = _module_coverage(counts, module)
        ok = pct >= threshold
        report["modules"][module] = {
            "coverage_percent": pct,
            "executed_lines": executed,
            "candidate_lines": total,
            "threshold": threshold,
            "ok": ok,
        }
        if not ok:
            report["ok"] = False

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Coverage gate report:")
    for mod, data in report["modules"].items():
        state = "OK" if data["ok"] else "FAIL"
        print(f" - {mod}: {data['coverage_percent']}% (threshold {data['threshold']}%) [{state}]")
    print(f"Report saved to: {out_path}")

    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
