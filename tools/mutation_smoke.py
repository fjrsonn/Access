#!/usr/bin/env python3
"""Mutation smoke testing sem dependências externas.

Aplica mutantes textuais pontuais em módulos críticos e valida se testes alvo falham.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Mutant:
    id: str
    file: str
    find: str
    replace: str
    test_cmd: list[str]
    risk: str


MUTANTS = [
    Mutant(
        id="ia_lock_guard_removed",
        file="ia.py",
        find="if not acquire_lock(timeout=5):",
        replace="if False and not acquire_lock(timeout=5):",
        test_cmd=["python", "-m", "unittest", "tests.test_e2e_pipeline.E2EPipelineTests.test_e2e_lock_ocupado_ia", "-v"],
        risk="alto",
    ),
    Mutant(
        id="main_skip_dadosend_processing",
        file="main.py",
        find='if event_name == "dadosend":',
        replace='if False and event_name == "dadosend":',
        test_cmd=["python", "-m", "unittest", "tests.test_watcher_integration.WatcherIntegrationTests.test_watcher_detects_changes_and_emits_status", "-v"],
        risk="alto",
    ),
    Mutant(
        id="interfaceone_disable_encomenda_branch",
        file="interfaceone.py",
        find='if destino == "encomendas" or _is_encomenda_text(txt, parsed):',
        replace='if False and (destino == "encomendas" or _is_encomenda_text(txt, parsed)):',
        test_cmd=["python", "-m", "unittest", "tests.test_e2e_pipeline.E2EPipelineTests.test_e2e_texto_encomenda", "-v"],
        risk="alto",
    ),
    Mutant(
        id="json_contracts_disable_runtime_status_validation",
        file="json_contracts.py",
        find="if status_value and status_value not in _RUNTIME_STATUS_ALLOWED:",
        replace="if False and status_value and status_value not in _RUNTIME_STATUS_ALLOWED:",
        test_cmd=["python", "-m", "unittest", "tests.test_json_contracts.JsonContractsTests.test_validate_contracts_detects_type_and_domain_errors", "-v"],
        risk="médio",
    ),
]


def run_mutant(mutant: Mutant) -> dict:
    target = ROOT / mutant.file
    original = target.read_text(encoding="utf-8")
    if mutant.find not in original:
        return {"id": mutant.id, "status": "skipped", "reason": "pattern_not_found", "risk": mutant.risk}

    mutated = original.replace(mutant.find, mutant.replace, 1)
    target.write_text(mutated, encoding="utf-8")
    try:
        proc = subprocess.run(mutant.test_cmd, cwd=ROOT, text=True, capture_output=True)
        killed = proc.returncode != 0
        return {
            "id": mutant.id,
            "status": "killed" if killed else "survived",
            "risk": mutant.risk,
            "command": " ".join(mutant.test_cmd),
            "returncode": proc.returncode,
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-10:]),
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-10:]),
        }
    finally:
        target.write_text(original, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "artifacts" / "mutation_smoke.json"))
    args = parser.parse_args()

    results = [run_mutant(m) for m in MUTANTS]
    killed = sum(1 for r in results if r["status"] == "killed")
    total = sum(1 for r in results if r["status"] in {"killed", "survived"})
    score = round((killed / total) * 100.0, 2) if total else 0.0

    per_module = {}
    for r in results:
        mid = r.get("id", "")
        mod = mid.split("_", 1)[0] if "_" in mid else "unknown"
        st = per_module.setdefault(mod, {"killed": 0, "total": 0})
        if r.get("status") in {"killed", "survived"}:
            st["total"] += 1
            if r.get("status") == "killed":
                st["killed"] += 1
    for mod, st in per_module.items():
        st["score"] = round((st["killed"] / st["total"]) * 100.0, 2) if st["total"] else 0.0

    top_survived = [r for r in results if r.get("status") == "survived"]

    report = {
        "mutation_score": score,
        "killed": killed,
        "total_executed": total,
        "per_module": per_module,
        "top_survived": top_survived[:5],
        "results": results,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Mutation smoke score: {score}% ({killed}/{total})")
    for r in results:
        print(f" - {r['id']}: {r['status']}")
    print(f"Report saved to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
