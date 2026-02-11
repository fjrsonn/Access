#!/usr/bin/env python3
"""Chat livre com LLM usando a mesma chave/API configurada em ia.py."""
from __future__ import annotations

import json
import os
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
MAX_RECORDS_PER_FILE = 40
MAX_RECORD_CHARS = 450


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


def _load_db_sources() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sources = {}
    for filename in DB_FILES:
        path = os.path.join(base_dir, filename)
        try:
            records = ia.carregar(path).get("registros", [])
            if not isinstance(records, list):
                records = [records]
            trimmed_records = records[:MAX_RECORDS_PER_FILE]
            sources[filename] = _shrink_value(trimmed_records)
            if len(records) > MAX_RECORDS_PER_FILE:
                sources[f"{filename}__meta"] = {
                    "registros_totais": len(records),
                    "registros_enviados": len(trimmed_records),
                }
        except Exception:
            sources[filename] = []
    return sources


def _build_user_message(user_query: str) -> str:
    sources = _load_db_sources()
    try:
        db_json = json.dumps(sources, ensure_ascii=False)
    except Exception:
        db_json = str(sources)[:20000]

    if len(db_json) > MAX_SOURCE_CHARS:
        db_json = (
            f"{db_json[:MAX_SOURCE_CHARS]}"
            f"\n\n[CONTEXTO TRUNCADO: {len(db_json) - MAX_SOURCE_CHARS} chars removidos]"
        )

    return (
        f"{db_json}\n\n"
        f"Pergunta do usuário: {user_query}\n"
        "Responda livremente usando apenas os dados acima."
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
