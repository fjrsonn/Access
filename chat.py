#!/usr/bin/env python3
"""Chat livre com LLM usando a mesma chave/API configurada em ia.py."""
from __future__ import annotations

import json
import os
import traceback

import ia

SYSTEM_PROMPT = (
    "Você é um assistente útil e objetivo. "
    "Responda em português quando o usuário falar em português. "
    "Seja claro, direto e educado."
)

DB_FILES = (
    "dadosinit.json",
    "dadosend.json",
    "analises.json",
    "avisos.json",
)


def _load_db_sources() -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sources = {}
    for filename in DB_FILES:
        path = os.path.join(base_dir, filename)
        try:
            sources[filename] = ia.carregar(path).get("registros", [])
        except Exception:
            sources[filename] = []
    return sources


def _build_user_message(user_query: str) -> str:
    sources = _load_db_sources()
    try:
        db_json = json.dumps(sources, ensure_ascii=False)
    except Exception:
        db_json = str(sources)[:20000]
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
    model: str = "llama-3.1-8b-instant",
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
        return f"ERRO AO CONSULTAR IA REMOTA: {e}"
