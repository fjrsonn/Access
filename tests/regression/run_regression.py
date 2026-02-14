#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ia
import interfaceone
import runtime_status
DATASET_PATH = ROOT / "tests" / "regression" / "data" / "v1" / "cases.json"
BASELINE_PATH = ROOT / "tests" / "regression" / "baseline" / "v1" / "summary.json"


class _Entry:
    def __init__(self, text: str):
        self._text = text
        self.deleted = False

    def get(self):
        return self._text

    def delete(self, *_args, **_kwargs):
        self.deleted = True
        self._text = ""

    def after(self, _ms, fn):
        fn()


def _run_save_text_case(case: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        paths = {
            "IN_FILE": os.path.join(td, "dadosinit.json"),
            "DB_FILE": os.path.join(td, "dadosend.json"),
            "ENCOMENDAS_IN_FILE": os.path.join(td, "encomendasinit.json"),
            "ENCOMENDAS_DB_FILE": os.path.join(td, "encomendasend.json"),
        }
        for p in paths.values():
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"registros": []}, f)

        entry = _Entry(case["text"])
        with mock.patch.multiple(interfaceone, **paths), \
             mock.patch.object(interfaceone, "classificar_destino_texto", return_value=case["classification"]), \
             mock.patch.object(interfaceone, "extrair_tudo_consumo", return_value=case.get("parsed") or {}), \
             mock.patch.object(interfaceone, "HAS_IA_MODULE", False):
            interfaceone.save_text(entry_widget=entry)

        with open(paths["IN_FILE"], "r", encoding="utf-8") as f:
            dadosinit_count = len((json.load(f) or {}).get("registros") or [])
        with open(paths["DB_FILE"], "r", encoding="utf-8") as f:
            dadosend_count = len((json.load(f) or {}).get("registros") or [])

        return {
            "dadosinit_count": dadosinit_count,
            "dadosend_count": dadosend_count,
            "entry_deleted": entry.deleted,
        }


def _run_ia_lock_case(case: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        events = os.path.join(td, "events.jsonl")
        last = os.path.join(td, "last.json")
        old_events = runtime_status.EVENTS_FILE
        old_last = runtime_status.LAST_STATUS_FILE
        runtime_status.EVENTS_FILE = events
        runtime_status.LAST_STATUS_FILE = last
        try:
            with mock.patch.object(ia, "is_chat_mode_active", return_value=False), \
                 mock.patch.object(ia, "acquire_lock", return_value=False):
                ia.processar()
            evs = runtime_status.read_runtime_events(events)
            stage = next((e.get("stage") for e in evs if e.get("stage") == case["expected_stage"]), "")
            return {"stage_detected": stage}
        finally:
            runtime_status.EVENTS_FILE = old_events
            runtime_status.LAST_STATUS_FILE = old_last


def run_cases(dataset_path: Path = DATASET_PATH) -> dict:
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    results = []
    for case in payload.get("cases", []):
        kind = case.get("kind")
        if kind == "save_text":
            out = _run_save_text_case(case)
        elif kind == "ia_lock":
            out = _run_ia_lock_case(case)
        else:
            raise ValueError(f"kind não suportado: {kind}")
        results.append({"id": case["id"], "kind": kind, "outcome": out})
    return {"version": payload.get("version", "v1"), "results": results}


def check_against_baseline(current: dict, baseline_path: Path = BASELINE_PATH) -> tuple[bool, dict]:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    return current == baseline, baseline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--reason", default="")
    args = parser.parse_args()

    if args.update_baseline and not args.reason.strip():
        raise SystemExit("--reason é obrigatório em --update-baseline")

    current = run_cases()

    if args.update_baseline:
        BASELINE_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        with open(ROOT / "tests" / "regression" / "BASELINE_CHANGELOG.md", "a", encoding="utf-8") as f:
            f.write(f"\n- update baseline: {args.reason.strip()}\n")
        print("Baseline atualizado.")
        return 0

    ok, baseline = check_against_baseline(current)
    if not args.check:
        print(json.dumps(current, ensure_ascii=False, indent=2))
        return 0

    if ok:
        print("Regression check: PASS")
        return 0

    print("Regression check: FAIL")
    print("Current:")
    print(json.dumps(current, ensure_ascii=False, indent=2))
    print("Baseline:")
    print(json.dumps(baseline, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
