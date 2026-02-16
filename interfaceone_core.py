#!/usr/bin/env python3
"""Lógica pura extraída da interface para facilitar testes e manutenção."""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Callable, Dict


def _has_strong_people_signal(parsed: dict | None) -> bool:
    if not isinstance(parsed, dict):
        return False
    placa = str(parsed.get("PLACA") or "").strip()
    modelos = parsed.get("MODELOS") or []
    if isinstance(modelos, str):
        modelos = [modelos]
    status = str(parsed.get("STATUS") or "").strip().upper()
    bloco = str(parsed.get("BLOCO") or "").strip()
    ap = str(parsed.get("APARTAMENTO") or "").strip()
    nome = str(parsed.get("NOME_RAW") or "").strip()

    has_vehicle = bool(placa) or bool([m for m in modelos if str(m).strip()])
    has_identity = bool(nome) or (bool(bloco) and bool(ap))
    has_status = status not in ("", "-", "DESCONHECIDO")
    return has_vehicle and (has_identity or has_status)


def _has_strong_encomenda_signal(destino_base: str, decision: dict, has_encomenda_signal: bool) -> bool:
    if not has_encomenda_signal:
        return False
    scores = decision.get("scores") if isinstance(decision.get("scores"), dict) else {}
    enc_score = float(scores.get("encomendas") or 0.0)
    text = str(decision.get("_texto_raw") or "")
    has_tracking_like = bool(re.search(r"\b(?=[A-Z0-9]{8,}\b)(?=[A-Z0-9]*\d)[A-Z0-9]+\b", text.upper()))
    if destino_base in ("encomendas", "dados"):
        return True
    return enc_score >= 1.8 or has_tracking_like


def decidir_destino(texto: str, parsed: dict | None, *,
                   classificar_fn: Callable[[str, dict | None], dict] | None,
                   is_encomenda_fn: Callable[[str, dict | None], bool]) -> dict:
    decision = classificar_fn(texto, parsed) if classificar_fn else {
        "destino": "dados", "motivo": "fallback", "score": 0.0,
        "ambiguo": False, "confianca": 0.0, "versao_regras": "v1"
    }
    destino_base = str(decision.get("destino") or "dados")
    decision = dict(decision)
    decision["_texto_raw"] = texto
    has_encomenda_signal = bool(is_encomenda_fn(texto, parsed))
    strong_people = _has_strong_people_signal(parsed)
    strong_encomenda = _has_strong_encomenda_signal(destino_base, decision, has_encomenda_signal)
    ambiguo = bool(decision.get("ambiguo"))
    conf_raw = decision.get("confianca")
    has_confianca = conf_raw is not None
    confianca = float(conf_raw or 0.0)

    # Prioridade operacional (determinística):
    # 1) Pessoas (sinal forte)
    # 2) Encomendas (somente sinal forte)
    # 3) Orientações
    # 4) Observações
    # 5) Ambíguo -> revisão
    if strong_people:
        destino = "dados"
    elif destino_base in ("orientacoes", "observacoes") and not ambiguo and confianca >= 0.60 and not strong_encomenda:
        destino = destino_base
    elif strong_encomenda:
        destino = "encomendas"
    elif destino_base == "orientacoes":
        destino = "orientacoes"
    elif destino_base == "observacoes":
        destino = "observacoes"
    elif ambiguo or (destino_base == "dados" and has_confianca and confianca < 0.45):
        destino = "revisao"
    else:
        destino = "dados"

    decision.pop("_texto_raw", None)
    decision["destino_final"] = destino
    decision["strong_people_signal"] = strong_people
    decision["strong_encomenda_signal"] = strong_encomenda
    return decision


def montar_registro_acesso(parsed: dict, *, corrigir_nome_fn: Callable[[str], str] | None, now_str: str | None = None) -> Dict[str, Any]:
    now = now_str or datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    nome_raw = (parsed.get("NOME_RAW") or "").strip()
    nome, sobrenome = "", ""
    if nome_raw:
        parts = nome_raw.split()
        if parts:
            if corrigir_nome_fn:
                parts = [corrigir_nome_fn(p) for p in parts]
            nome = parts[0].title()
            sobrenome = " ".join(parts[1:]).title() if len(parts) > 1 else ""

    modelos = parsed.get("MODELOS") or []
    modelo = modelos[0] if modelos else None

    rec: Dict[str, Any] = {
        "NOME": (nome or "").upper(),
        "SOBRENOME": (sobrenome or "").upper() or "-",
        "BLOCO": str(parsed.get("BLOCO") or "").strip(),
        "APARTAMENTO": str(parsed.get("APARTAMENTO") or "").strip(),
        "PLACA": (parsed.get("PLACA") or "").upper() or "-",
        "MODELO": (str(modelo) or "").upper() if modelo else None,
        "COR": (str(parsed.get("COR") or "") or "").upper() if parsed.get("COR") else None,
        "STATUS": (parsed.get("STATUS") or "").upper() or "-",
        "DATA_HORA": now,
    }
    for k in list(rec.keys()):
        if rec[k] is None:
            rec.pop(k, None)
    if nome_raw and rec.get("SOBRENOME") in (None, "", "-"):
        parts = nome_raw.split()
        if parts and len(parts) > 1:
            if corrigir_nome_fn:
                parts = [corrigir_nome_fn(p) for p in parts]
            rec["SOBRENOME"] = " ".join(parts[1:]).upper()
    return rec


def montar_entrada_bruta(nid: int, texto: str, now_str: str, flags: dict | None = None) -> dict:
    out = {
        "id": nid,
        "texto": texto,
        "processado": False,
        "data_hora": now_str,
    }
    if flags:
        out.update(flags)
    return out
