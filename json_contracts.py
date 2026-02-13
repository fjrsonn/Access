#!/usr/bin/env python3
"""Contratos mínimos de JSON para validação de entrada/saída."""
from __future__ import annotations

from typing import Any, Dict, List


def _is_records_dict(obj: Any) -> bool:
    return isinstance(obj, dict) and isinstance(obj.get("registros"), list)


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
    return errs


def validate_encomendas(obj: Any) -> List[str]:
    errs: List[str] = []
    if not _is_records_dict(obj):
        return ["encomendas_formato_invalido"]
    for i, r in enumerate(obj.get("registros") or []):
        if not isinstance(r, dict):
            errs.append(f"registro_{i}_nao_dict")
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
