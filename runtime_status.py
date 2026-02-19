#!/usr/bin/env python3
"""Rastreio de status em tempo real para ações do usuário e pipeline interno."""
from __future__ import annotations

import json
import os
import tempfile
import threading
from datetime import datetime
from typing import Any, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

EVENTS_FILE = os.path.join(LOG_DIR, "runtime_events.jsonl")
LAST_STATUS_FILE = os.path.join(LOG_DIR, "runtime_last_status.json")

_LOCK = threading.Lock()


class RuntimeStatusStore:
    """Armazena caminhos de status/eventos para evitar dependência em globais mutáveis."""

    def __init__(self, *, events_file: str = EVENTS_FILE, last_status_file: str = LAST_STATUS_FILE):
        self.events_file = events_file
        self.last_status_file = last_status_file

    def get_last_status(self) -> Dict[str, Any]:
        return get_last_status(self.last_status_file)


DEFAULT_STORE = RuntimeStatusStore()


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_json(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except Exception:
        return str(value)


def _write_atomic_json(path: str, payload: Dict[str, Any]) -> None:
    dirn = os.path.dirname(path) or "."
    os.makedirs(dirn, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirn, prefix=".tmp_runtime_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def report_status(action: str, status: str, *, stage: str = "", details: Dict[str, Any] | None = None) -> None:
    """Registra evento em JSONL e atualiza snapshot de último status."""
    event = {
        "timestamp": _now_iso(),
        "action": str(action or "").strip() or "UNKNOWN_ACTION",
        "status": str(status or "").strip().upper() or "UNKNOWN",
        "stage": str(stage or "").strip(),
        "details": _safe_json(details or {}),
    }
    with _LOCK:
        try:
            with open(EVENTS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            return
        try:
            _write_atomic_json(LAST_STATUS_FILE, event)
        except Exception:
            pass


def report_log(module: str, level: str, message: str, *, stage: str = "", details: Dict[str, Any] | None = None) -> None:
    """Atalho para logs estruturados com action fixa de componente."""
    payload = dict(details or {})
    payload.update({"module": module, "message": str(message)})
    report_status(f"log:{module}", str(level).upper(), stage=stage, details=payload)


def get_last_status(path: str | None = None) -> Dict[str, Any]:
    target = path or LAST_STATUS_FILE
    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _read_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _to_records(obj: Any) -> list:
    if isinstance(obj, dict) and "registros" in obj:
        recs = obj.get("registros") or []
        return recs if isinstance(recs, list) else list(recs)
    if isinstance(obj, list):
        return obj
    return []


def read_runtime_events(path: str = EVENTS_FILE) -> list[Dict[str, Any]]:
    events: list[Dict[str, Any]] = []
    if not os.path.exists(path):
        return events
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                    if isinstance(ev, dict):
                        events.append(ev)
                except Exception:
                    continue
    except Exception:
        return []
    return events


def _parse_ts(value: Any):
    s = str(value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None


def analisar_saude_pipeline(events_path: str = EVENTS_FILE) -> Dict[str, Any]:
    """Analisa saúde do pipeline baseado em runtime_events.jsonl."""
    events = read_runtime_events(events_path)
    stage_counts: Dict[str, int] = {}
    stage_errors: Dict[str, int] = {}
    error_messages: Dict[str, int] = {}
    action_started: Dict[str, datetime] = {}
    action_durations: Dict[str, list[float]] = {}

    for ev in events:
        stage = str(ev.get("stage") or "-")
        status = str(ev.get("status") or "").upper()
        action = str(ev.get("action") or "UNKNOWN")

        stage_counts[stage] = stage_counts.get(stage, 0) + 1
        if status == "ERROR":
            stage_errors[stage] = stage_errors.get(stage, 0) + 1
            details = ev.get("details") or {}
            err = ""
            if isinstance(details, dict):
                err = str(details.get("error") or details.get("reason") or "unknown")
            else:
                err = str(details)
            error_messages[err] = error_messages.get(err, 0) + 1

        ts = _parse_ts(ev.get("timestamp"))
        if status == "STARTED" and ts:
            action_started[action] = ts
        elif status in ("OK", "ERROR") and ts and action in action_started:
            diff = (ts - action_started[action]).total_seconds()
            if diff >= 0:
                action_durations.setdefault(action, []).append(diff)
            action_started.pop(action, None)

    error_rate_by_stage = {}
    for st, total in stage_counts.items():
        err = stage_errors.get(st, 0)
        error_rate_by_stage[st] = round((err / total) if total else 0.0, 4)

    avg_time_started_to_end = {
        action: round(sum(vals) / len(vals), 4) for action, vals in action_durations.items() if vals
    }

    top_5_errors = sorted(error_messages.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_events": len(events),
        "error_rate_by_stage": error_rate_by_stage,
        "top_5_errors": [{"error": e, "count": c} for e, c in top_5_errors],
        "avg_time_started_to_end_by_action": avg_time_started_to_end,
    }



UX_METRICS_FILE = os.path.join(LOG_DIR, "ux_metrics_dashboard.json")


def analisar_metricas_ux(events_path: str = EVENTS_FILE) -> Dict[str, Any]:
    events = read_runtime_events(events_path)
    out: Dict[str, Any] = {
        "time_to_apply_filter_ms": {"count": 0, "avg": 0.0, "p95": 0.0},
        "edit_save_success_rate": 0.0,
        "theme_switch_count": 0,
        "keyboard_shortcut_adoption": 0,
    }

    apply_times = []
    started_ts = {}
    save_ok = 0
    save_total = 0

    for ev in events:
        action = str(ev.get("action") or "")
        stage = str(ev.get("stage") or "")
        status = str(ev.get("status") or "")
        ts = _parse_ts(ev.get("timestamp"))
        details = ev.get("details") or {}

        if action == "ux_metrics" and stage == "filter_apply_started" and ts:
            started_ts["filter_apply"] = ts
        if action == "ux_metrics" and stage == "filter_apply" and ts and "filter_apply" in started_ts:
            diff = (ts - started_ts.pop("filter_apply")).total_seconds() * 1000.0
            if diff >= 0:
                apply_times.append(diff)

        if action == "ux_metrics" and stage in {"edit_save", "edit_save_error"}:
            save_total += 1
            if stage == "edit_save" and status == "OK":
                save_ok += 1

        if action == "ux_metrics" and stage == "theme_switch":
            out["theme_switch_count"] += 1

        if action == "ux_metrics" and stage == "shortcut_used":
            out["keyboard_shortcut_adoption"] += 1

    if apply_times:
        arr = sorted(apply_times)
        idx = int(max(0, min(len(arr) - 1, round(0.95 * (len(arr) - 1)))))
        out["time_to_apply_filter_ms"] = {
            "count": len(arr),
            "avg": round(sum(arr) / len(arr), 2),
            "p95": round(arr[idx], 2),
        }
    if save_total:
        out["edit_save_success_rate"] = round(save_ok / save_total, 4)

    try:
        _write_atomic_json(UX_METRICS_FILE, out)
    except Exception:
        pass
    return out

def detectar_conflitos_dados(base_dir: str = BASE_DIR) -> Dict[str, Any]:
    """Procura inconsistências entre dadosinit/dadosend/analises/avisos."""
    dadosinit = _to_records(_read_json(os.path.join(base_dir, "dadosinit.json")))
    dadosend = _to_records(_read_json(os.path.join(base_dir, "dadosend.json")))
    analises_raw = _read_json(os.path.join(base_dir, "analises.json")) or {}
    avisos_raw = _read_json(os.path.join(base_dir, "avisos.json")) or {}

    analises_regs = []
    if isinstance(analises_raw, dict):
        analises_regs = analises_raw.get("registros") or []
    avisos_regs = []
    if isinstance(avisos_raw, dict):
        avisos_regs = avisos_raw.get("registros") or []

    saida_entrada_ids = set(str(r.get("_entrada_id")) for r in dadosend if r.get("_entrada_id") is not None)

    processed_without_saida = []
    for r in dadosinit:
        if not r.get("processado"):
            continue
        rid = r.get("id") or r.get("ID")
        if rid is None:
            continue
        if str(rid) not in saida_entrada_ids:
            processed_without_saida.append(rid)

    duplicated_entrada_ids = {}
    seen = {}
    for r in dadosend:
        eid = r.get("_entrada_id")
        if eid is None:
            continue
        k = str(eid)
        seen[k] = seen.get(k, 0) + 1
    for k, v in seen.items():
        if v > 1:
            duplicated_entrada_ids[k] = v

    analysis_ids = set()
    for a in analises_regs:
        ident = (a.get("identidade") or "").strip().upper()
        if ident:
            analysis_ids.add(ident)

    avisos_sem_analise = []
    for av in avisos_regs:
        ident = (av.get("identidade") or "").strip().upper()
        if ident and ident not in analysis_ids and not ident.startswith("ENCOMENDA|"):
            avisos_sem_analise.append(ident)

    return {
        "processed_without_saida": processed_without_saida,
        "duplicated_entrada_ids": duplicated_entrada_ids,
        "avisos_sem_analise": sorted(set(avisos_sem_analise)),
    }


def gerar_relatorio_diagnostico_diario(base_dir: str = BASE_DIR, events_path: str = EVENTS_FILE) -> Dict[str, Any]:
    """Resumo diário: volume, falhas e sugestões automáticas."""
    events = read_runtime_events(events_path)
    today = datetime.now().strftime("%Y-%m-%d")

    daily = [e for e in events if str(e.get("timestamp") or "").startswith(today)]

    volume_by_action: Dict[str, int] = {}
    failures_by_stage: Dict[str, int] = {}
    for ev in daily:
        action = str(ev.get("action") or "UNKNOWN")
        volume_by_action[action] = volume_by_action.get(action, 0) + 1
        if str(ev.get("status") or "").upper() == "ERROR":
            st = str(ev.get("stage") or "-")
            failures_by_stage[st] = failures_by_stage.get(st, 0) + 1

    saude = analisar_saude_pipeline(events_path)
    conflitos = detectar_conflitos_dados(base_dir)

    sugestoes = []
    if conflitos.get("processed_without_saida"):
        sugestoes.append("Revisar fluxo de merge por _entrada_id entre dadosinit e dadosend.")
    if conflitos.get("duplicated_entrada_ids"):
        sugestoes.append("Validar deduplicação no append otimista e na atualização da IA.")
    if failures_by_stage:
        sugestoes.append("Priorizar correções nos estágios com mais ERROR no runtime_events.jsonl.")
    if not sugestoes:
        sugestoes.append("Pipeline estável no dia atual; manter monitoramento e ampliar testes E2E.")

    return {
        "date": today,
        "volume_by_action": volume_by_action,
        "failures_by_stage": failures_by_stage,
        "pipeline_health": saude,
        "data_conflicts": conflitos,
        "suggestions": sugestoes,
    }