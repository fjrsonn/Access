#!/usr/bin/env python3
"""Lógica pura extraída da interface para facilitar testes e manutenção."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict


def _has_explicit_access_fields(parsed: dict | None) -> bool:
    if not isinstance(parsed, dict):
        return False
    # BLOCO/APARTAMENTO isolados também aparecem em textos livres de orientação.
    # Aqui só forçamos "dados" quando há sinais realmente fortes de registro de acesso.
    return bool(
        str(parsed.get("PLACA") or "").strip()
        or (parsed.get("MODELOS") or [])
        or str(parsed.get("NOME_RAW") or "").strip()
        or str(parsed.get("STATUS") or "").strip()
    )


def decidir_destino(texto: str, parsed: dict | None, *,
                   classificar_fn: Callable[[str, dict | None], dict] | None,
                   is_encomenda_fn: Callable[[str, dict | None], bool]) -> dict:
    decision = classificar_fn(texto, parsed) if classificar_fn else {
        "destino": "dados", "motivo": "fallback", "score": 0.0,
        "ambiguo": False, "confianca": 0.0, "versao_regras": "v1"
    }
    destino = decision.get("destino")
    if destino == "encomendas" or is_encomenda_fn(texto, parsed):
        destino = "encomendas"
    if destino in {"encomendas", "observacoes", "orientacoes"} and _has_explicit_access_fields(parsed):
        destino = "dados"
    decision = dict(decision)
    decision["destino_final"] = destino
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
        "SOBRENOME": (sobrenome or "").upper(),
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
