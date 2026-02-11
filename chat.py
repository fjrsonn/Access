#!/usr/bin/env python3
"""Chat livre com LLM usando a mesma chave/API configurada em ia.py."""
from __future__ import annotations

import json
import os
import re
import traceback
from typing import Any

import ia

SYSTEM_PROMPT = (
    "Você é um assistente útil e objetivo. "
    "Responda em português quando o usuário falar em português. "
    "Seja claro, direto e educado."
)

DB_FILES = (
    "dadosend.json",
    "encomendasend.json",
    "avisos.json",
)

MAX_SOURCE_CHARS = 14000
MAX_RECORD_CHARS = 450
RECENT_RECORDS_PER_FILE = 30
QUERY_MATCH_LIMIT = 80
CONSOLIDATED_FILE = "contexto_ia.json"


def _shrink_value(value: Any, max_chars: int = MAX_RECORD_CHARS) -> Any:
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        return f"{value[:max_chars]}... [TRUNCADO {len(value) - max_chars} chars]"
    if isinstance(value, dict):
        return {k: _shrink_value(v, max_chars=max_chars) for k, v in value.items()}
    if isinstance(value, list):
        return [_shrink_value(v, max_chars=max_chars) for v in value]
    return value


def _to_records(raw: Any) -> list:
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return [raw]
    return []


def _load_all_sources() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sources = {}
    for filename in DB_FILES:
        path = os.path.join(base_dir, filename)
        try:
            raw = ia.carregar(path).get("registros", [])
            sources[filename] = _to_records(raw)
        except Exception:
            sources[filename] = []
    return sources


def _extract_person_name(record: dict) -> str:
    nome = str(record.get("NOME", "")).strip()
    sobrenome = str(record.get("SOBRENOME", "")).strip()
    full = f"{nome} {sobrenome}".strip()
    return full.lower()


def _extract_timestamp(record: dict) -> str:
    for key in ("DATA_HORA", "DATA", "HORARIO", "data_hora", "timestamp"):
        value = record.get(key)
        if value:
            return str(value)
    return ""


def _build_consolidated_context(full_sources: dict) -> dict:
    people_summary = {}
    stats_by_file = {}
    latest_seen = ""

    for filename, records in full_sources.items():
        stats_by_file[filename] = {"total_registros": len(records)}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            person = _extract_person_name(rec)
            if person:
                item = people_summary.setdefault(
                    person,
                    {
                        "total_eventos": 0,
                        "ultima_ocorrencia": "",
                    },
                )
                item["total_eventos"] += 1
                ts = _extract_timestamp(rec)
                if ts:
                    item["ultima_ocorrencia"] = ts
                    latest_seen = ts

    sorted_people = sorted(
        people_summary.items(), key=lambda kv: kv[1].get("total_eventos", 0), reverse=True
    )
    top_people = {k: v for k, v in sorted_people[:120]}

    return {
        "resumo_por_arquivo": stats_by_file,
        "pessoas_top_eventos": top_people,
        "ultimo_registro_observado": latest_seen,
    }


def _save_consolidated_context(data: dict) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, CONSOLIDATED_FILE)
    try:
        ia.salvar_atomico(path, data)
    except Exception:
        pass


def _build_recent_context(full_sources: dict) -> dict:
    recent = {}
    for filename, records in full_sources.items():
        trimmed = records[-RECENT_RECORDS_PER_FILE:]
        recent[filename] = _shrink_value(trimmed)
        if len(records) > RECENT_RECORDS_PER_FILE:
            recent[f"{filename}__meta"] = {
                "registros_totais": len(records),
                "registros_recentes_enviados": len(trimmed),
            }
    return recent


def _query_tokens(user_query: str) -> list[str]:
    terms = [t.lower() for t in re.findall(r"[\wÀ-ÿ]+", user_query or "")]
    stop = {"de", "da", "do", "das", "dos", "a", "o", "e", "que", "em", "no", "na", "para"}
    return [t for t in terms if len(t) >= 3 and t not in stop][:8]


def _build_query_specific_context(user_query: str, full_sources: dict) -> dict:
    tokens = _query_tokens(user_query)
    if not tokens:
        return {"tokens_consulta": [], "registros_relevantes": {}}

    matches = {}
    total_matches = 0

    for filename, records in full_sources.items():
        local = []
        for rec in records:
            rec_text = json.dumps(rec, ensure_ascii=False).lower()
            if any(tok in rec_text for tok in tokens):
                local.append(rec)
            if len(local) >= QUERY_MATCH_LIMIT:
                break
        if local:
            matches[filename] = _shrink_value(local)
            total_matches += len(local)

    return {
        "tokens_consulta": tokens,
        "total_registros_relevantes_enviados": total_matches,
        "registros_relevantes": matches,
    }


def _load_db_sources(user_query: str) -> dict:
    full_sources = _load_all_sources()
    consolidated = _build_consolidated_context(full_sources)
    _save_consolidated_context(consolidated)

    return {
        "estado_consolidado": consolidated,
        "contexto_recente": _build_recent_context(full_sources),
        "consulta_especifica": _build_query_specific_context(user_query, full_sources),
    }


def _build_partial_context_notice(sources: dict) -> str:
    partials = []
    recent = sources.get("contexto_recente", {}) if isinstance(sources, dict) else {}

    for filename in DB_FILES:
        meta = recent.get(f"{filename}__meta") if isinstance(recent, dict) else None
        if not isinstance(meta, dict):
            continue
        total = meta.get("registros_totais")
        sent = meta.get("registros_recentes_enviados")
        if isinstance(total, int) and isinstance(sent, int) and total > sent:
            partials.append(f"{filename}: recentes {sent}/{total}")

    if not partials:
        return ""

    details = "; ".join(partials)
    return (
        "ATENÇÃO: histórico completo mantido internamente; para o LLM foi enviado estado consolidado + recorte recente. "
        f"Cobertura do recorte recente -> {details}. "
        "Se precisar auditoria completa de um caso, informe nome, período ou referência."
    )


def _build_user_message(user_query: str) -> str:
    sources = _load_db_sources(user_query)
    partial_notice = _build_partial_context_notice(sources)
    try:
        db_json = json.dumps(sources, ensure_ascii=False)
    except Exception:
        db_json = str(sources)[:20000]

    if len(db_json) > MAX_SOURCE_CHARS:
        db_json = (
            f"{db_json[:MAX_SOURCE_CHARS]}"
            f"\n\n[CONTEXTO TRUNCADO: {len(db_json) - MAX_SOURCE_CHARS} chars removidos]"
        )

    return (f"{partial_notice}\n\n" if partial_notice else "") + (
        f"{db_json}\n\n"
        f"Pergunta do usuário: {user_query}\n"
        "Responda com base no estado consolidado e no recorte recente/relevante. "
        "Se a pergunta exigir histórico completo, explicite isso e use os registros relevantes fornecidos."
    )


def activate_chat_mode() -> None:
    ia.set_chat_mode(True)
    ia.activate_agent_prompt()


def deactivate_chat_mode() -> None:
    ia.deactivate_agent_prompt()
    ia.set_chat_mode(False)


def respond_chat(
    user_query: str,
    *,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.2,
) -> str:
    if not user_query:
        return ""

    if ia.client is None:
        return "IA REMOTA NAO ESTA DISPONIVEL NO MOMENTO. VERIFIQUE A CHAVE E A CONECTIVIDADE PARA CONTINUAR."

    try:
        user_msg = _build_user_message(user_query)
        resposta = ia.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=temperature,
            max_tokens=800,
        )
        content = (
            resposta.choices[0].message.content
            if hasattr(resposta, "choices") and resposta.choices
            else str(resposta)
        )
        if isinstance(content, str):
            return ia._apply_agent_prompt_template(content)
        return content
    except Exception as e:
        err_msg = str(e).lower()
        print(f"[chat.respond_chat] Erro ao consultar LLM: {e}")
        traceback.print_exc()
        if "invalid_api_key" in err_msg or "401" in err_msg:
            ia._disable_client_due_to_auth()
        if "413" in err_msg or "request too large" in err_msg or "tokens per minute" in err_msg:
            return (
                "A pergunta não pôde ser processada porque o contexto enviado para a IA ficou grande demais "
                "para o limite atual da conta/modelo. Tente uma pergunta mais específica ou reduza o volume "
                "de dados no contexto."
            )
        return f"ERRO AO CONSULTAR IA REMOTA: {e}"
