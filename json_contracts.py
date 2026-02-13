#!/usr/bin/env python3
"""Contratos mínimos de JSON para validação de entrada/saída."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

_STATUS_ALLOWED = {"MORADOR", "VISITANTE", "PRESTADOR", "DESCONHECIDO", "-"}
_RUNTIME_STATUS_ALLOWED = {"STARTED", "OK", "ERROR", "SKIPPED", "FINISHED", "WARNING", "UNKNOWN"}


def _is_records_dict(obj: Any) -> bool:
    return isinstance(obj, dict) and isinstance(obj.get("registros"), list)


def _is_valid_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    s = value.strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            datetime.strptime(s, fmt)
            return True
        except ValueError:
            pass
    return False


def validate_dadosinit(obj: Any) -> List[str]:
    errs: List[str] = []
    if not _is_records_dict(obj):
        return ["dadosinit_formato_invalido"]
    for i, r in enumerate(obj.get("registros") or []):
        if not isinstance(r, dict):
            errs.append(f"registro_{i}_nao_dict")
            continue
        for key in ("id", "texto", "processado", "data_hora"):
            if key not in r:
                errs.append(f"registro_{i}_campo_ausente_{key}")
        if "id" in r and not isinstance(r.get("id"), int):
            errs.append(f"registro_{i}_id_tipo_invalido")
        if "texto" in r and not isinstance(r.get("texto"), str):
            errs.append(f"registro_{i}_texto_tipo_invalido")
        if "processado" in r and not isinstance(r.get("processado"), bool):
            errs.append(f"registro_{i}_processado_tipo_invalido")
        if "data_hora" in r and not _is_valid_datetime(r.get("data_hora")):
            errs.append(f"registro_{i}_data_hora_invalida")
    return errs


def validate_dadosend(obj: Any) -> List[str]:
    errs: List[str] = []
    if not _is_records_dict(obj):
        return ["dadosend_formato_invalido"]
    for i, r in enumerate(obj.get("registros") or []):
        if not isinstance(r, dict):
            errs.append(f"registro_{i}_nao_dict")
            continue
        for key in ("ID", "BLOCO", "APARTAMENTO", "DATA_HORA"):
            if key not in r:
                errs.append(f"registro_{i}_campo_ausente_{key}")
        if "ID" in r and not isinstance(r.get("ID"), int):
            errs.append(f"registro_{i}_id_tipo_invalido")
        if "DATA_HORA" in r and not _is_valid_datetime(r.get("DATA_HORA")):
            errs.append(f"registro_{i}_data_hora_invalida")
        if "STATUS" in r and str(r.get("STATUS") or "").upper() not in _STATUS_ALLOWED:
            errs.append(f"registro_{i}_status_fora_dominio")
    return errs


def validate_encomendas(obj: Any) -> List[str]:
    errs: List[str] = []
    if not _is_records_dict(obj):
        return ["encomendas_formato_invalido"]
    for i, r in enumerate(obj.get("registros") or []):
        if not isinstance(r, dict):
            errs.append(f"registro_{i}_nao_dict")
            continue
        if "DATA_HORA" in r and not _is_valid_datetime(r.get("DATA_HORA")):
            errs.append(f"registro_{i}_data_hora_invalida")
    return errs


def validate_analises(obj: Any) -> List[str]:
    if not isinstance(obj, dict):
        return ["analises_formato_invalido"]
    errs: List[str] = []
    if "registros" not in obj or not isinstance(obj.get("registros"), list):
        errs.append("analises_registros_invalido")
    if "encomendas_multiplas_bloco_apartamento" not in obj or not isinstance(obj.get("encomendas_multiplas_bloco_apartamento"), list):
        errs.append("analises_encomendas_invalido")
    return errs


def validate_avisos(obj: Any) -> List[str]:
    if not isinstance(obj, dict):
        return ["avisos_formato_invalido"]
    errs: List[str] = []
    if "registros" not in obj or not isinstance(obj.get("registros"), list):
        errs.append("avisos_registros_invalido")
    return errs


def validate_runtime_last_status(obj: Any) -> List[str]:
    if not isinstance(obj, dict):
        return ["runtime_last_status_formato_invalido"]
    errs: List[str] = []
    for key in ("timestamp", "action", "status", "stage", "details"):
        if key not in obj:
            errs.append(f"runtime_last_status_campo_ausente_{key}")
    if "timestamp" in obj and not _is_valid_datetime(obj.get("timestamp")):
        errs.append("runtime_last_status_timestamp_invalido")
    status_value = str(obj.get("status") or "").upper()
    if status_value and status_value not in _RUNTIME_STATUS_ALLOWED:
        errs.append("runtime_last_status_status_fora_dominio")
    if "details" in obj and not isinstance(obj.get("details"), dict):
        errs.append("runtime_last_status_details_tipo_invalido")
    return errs


def validate_all_contracts(payloads: Dict[str, Any]) -> Dict[str, List[str]]:
    return {
        "dadosinit": validate_dadosinit(payloads.get("dadosinit")),
        "dadosend": validate_dadosend(payloads.get("dadosend")),
        "encomendasinit": validate_encomendas(payloads.get("encomendasinit")),
        "encomendasend": validate_encomendas(payloads.get("encomendasend")),
        "analises": validate_analises(payloads.get("analises")),
        "avisos": validate_avisos(payloads.get("avisos")),
        "runtime_last_status": validate_runtime_last_status(payloads.get("runtime_last_status")),
    }
