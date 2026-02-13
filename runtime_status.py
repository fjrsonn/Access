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


def get_last_status() -> Dict[str, Any]:
    try:
        with open(LAST_STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}
