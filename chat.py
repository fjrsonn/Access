#!/usr/bin/env python3
"""Chat livre com LLM usando a mesma chave/API configurada em ia.py."""
from __future__ import annotations

import hashlib
import json
import os
import re
import traceback
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
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
FULL_AUDIT_SAMPLE_LIMIT = 40
CONSOLIDATED_FILE = "contexto_ia.json"
QUERY_LOW_CONFIDENCE_THRESHOLD = 8

SENSITIVE_KEY_PARTS = (
    "cpf",
    "cnpj",
    "telefone",
    "celular",
    "whatsapp",
    "documento",
    "rg",
    "placa",
)

STOPWORDS_PT = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "a",
    "o",
    "e",
    "que",
    "em",
    "no",
    "na",
    "para",
    "por",
    "com",
    "sem",
    "uma",
    "um",
    "ao",
    "aos",
    "as",
    "os",
    "como",
    "qual",
    "quais",
    "quando",
    "onde",
    "foi",
    "sao",
    "são",
    "mais",
    "menos",
    "sobre",
}

_CONSOLIDATED_CACHE: dict[str, Any] = {"mtimes": None, "value": None}
_LAST_CONTEXT_META: dict[str, Any] = {}


def _normalize_text(text: str) -> str:
    raw = (text or "").lower()
    no_accents = "".join(
        c for c in unicodedata.normalize("NFKD", raw) if not unicodedata.combining(c)
    )
    return no_accents


def _looks_sensitive_key(key: str | None) -> bool:
    if not key:
        return False
    k = _normalize_text(str(key))
    return any(part in k for part in SENSITIVE_KEY_PARTS)


def _mask_sensitive_text(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}***{value[-2:]}"


def _shrink_value(value: Any, max_chars: int = MAX_RECORD_CHARS, *, parent_key: str = "") -> Any:
    if isinstance(value, str):
        cleaned = value
        if _looks_sensitive_key(parent_key):
            cleaned = _mask_sensitive_text(cleaned)
        if len(cleaned) <= max_chars:
            return cleaned
        return f"{cleaned[:max_chars]}... [TRUNCADO {len(cleaned) - max_chars} chars]"
    if isinstance(value, dict):
        return {k: _shrink_value(v, max_chars=max_chars, parent_key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_shrink_value(v, max_chars=max_chars, parent_key=parent_key) for v in value]
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




def _extract_location(record: dict) -> tuple[str, str]:
    bloco = str(record.get("BLOCO", record.get("bloco", ""))).strip()
    apto = str(record.get("APARTAMENTO", record.get("apartamento", ""))).strip()
    return bloco, apto


def _person_identity(record: dict) -> str:
    name = _normalize_text(_extract_person_name(record))
    bloco, apto = _extract_location(record)
    identity_raw = f"{name}|{_normalize_text(bloco)}|{_normalize_text(apto)}"
    if not identity_raw.replace("|", "").strip():
        return "desconhecido"
    return hashlib.sha1(identity_raw.encode("utf-8")).hexdigest()[:12]


def _emit_telemetry(event: str, payload: dict) -> None:
    try:
        print(f"[chat.telemetria.{event}] {json.dumps(payload, ensure_ascii=False)}")
    except Exception:
        print(f"[chat.telemetria.{event}] {payload}")

def _extract_timestamp(record: dict) -> str:
    for key in ("DATA_HORA", "DATA", "HORARIO", "data_hora", "timestamp"):
        value = record.get(key)
        if value:
            return str(value)
    return ""


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    fmts = (
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
    )
    for fmt in fmts:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _build_consolidated_context(full_sources: dict) -> dict:
    people_summary = {}
    identities_by_name: dict[str, set[str]] = {}
    stats_by_file = {}
    latest_seen_text = ""
    latest_seen_dt: datetime | None = None

    for filename, records in full_sources.items():
        stats_by_file[filename] = {"total_registros": len(records)}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            person = _extract_person_name(rec)
            if person:
                person_id = _person_identity(rec)
                bloco, apto = _extract_location(rec)
                item = people_summary.setdefault(
                    person_id,
                    {
                        "nome": person,
                        "bloco": bloco,
                        "apartamento": apto,
                        "total_eventos": 0,
                        "ultima_ocorrencia": "",
                    },
                )
                identities_by_name.setdefault(person, set()).add(person_id)
                item["total_eventos"] += 1
                ts = _extract_timestamp(rec)
                ts_dt = _parse_timestamp(ts)
                if ts_dt:
                    if (latest_seen_dt is None) or (ts_dt > latest_seen_dt):
                        latest_seen_dt = ts_dt
                        latest_seen_text = ts
                    current_dt = _parse_timestamp(item.get("ultima_ocorrencia", ""))
                    if (current_dt is None) or (ts_dt > current_dt):
                        item["ultima_ocorrencia"] = ts
                elif ts and not item.get("ultima_ocorrencia"):
                    item["ultima_ocorrencia"] = ts

    sorted_people = sorted(
        people_summary.items(), key=lambda kv: kv[1].get("total_eventos", 0), reverse=True
    )
    top_people = {k: v for k, v in sorted_people[:120]}

    nomes_ambiguos = {n: len(ids) for n, ids in identities_by_name.items() if len(ids) > 1}

    return {
        "resumo_por_arquivo": stats_by_file,
        "pessoas_top_eventos": top_people,
        "nomes_ambiguos": nomes_ambiguos,
        "ultimo_registro_observado": latest_seen_text,
    }


def _source_mtimes(base_dir: str) -> tuple:
    values = []
    for filename in DB_FILES:
        path = os.path.join(base_dir, filename)
        try:
            values.append((filename, os.path.getmtime(path)))
        except OSError:
            values.append((filename, None))
    return tuple(values)


def _save_consolidated_context(data: dict) -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base_dir, CONSOLIDATED_FILE)
    try:
        ia.salvar_atomico(path, data)
    except Exception as exc:
        print(f"[chat] aviso: falha ao salvar {CONSOLIDATED_FILE}: {exc}")


def _get_cached_or_build_consolidated(full_sources: dict) -> dict:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    mtimes = _source_mtimes(base_dir)
    if _CONSOLIDATED_CACHE.get("mtimes") == mtimes and isinstance(_CONSOLIDATED_CACHE.get("value"), dict):
        return _CONSOLIDATED_CACHE["value"]

    consolidated = _build_consolidated_context(full_sources)
    _CONSOLIDATED_CACHE["mtimes"] = mtimes
    _CONSOLIDATED_CACHE["value"] = consolidated
    _save_consolidated_context(consolidated)
    return consolidated


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
    terms = [_normalize_text(t) for t in re.findall(r"[\wÀ-ÿ]+", user_query or "")]
    return [t for t in terms if len(t) >= 3 and t not in STOPWORDS_PT][:10]


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _record_semantic_score(record: Any, tokens: list[str]) -> float:
    if not isinstance(record, dict) or not tokens:
        return 0.0

    text = _normalize_text(json.dumps(record, ensure_ascii=False))
    name = _normalize_text(_extract_person_name(record))
    vehicle = _normalize_text(str(record.get("MODELO", "")))

    score = 0.0
    for tok in tokens:
        if tok in text:
            score += 2.2
        score += _text_similarity(tok, name) * 1.5
        score += _text_similarity(tok, vehicle) * 1.1
    return score


def _build_query_specific_context(user_query: str, full_sources: dict) -> dict:
    tokens = _query_tokens(user_query)
    if not tokens:
        return {"tokens_consulta": [], "confianca_busca": 0.0, "registros_relevantes": {}}

    matches = {}
    total_matches = 0
    score_acc = 0.0

    for filename, records in full_sources.items():
        scored = []
        for rec in records:
            score = _record_semantic_score(rec, tokens)
            if score > 0.55:
                scored.append((score, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        top_records = [item[1] for item in scored[:QUERY_MATCH_LIMIT]]
        if top_records:
            matches[filename] = _shrink_value(top_records)
            total_matches += len(top_records)
            score_acc += sum(item[0] for item in scored[:QUERY_MATCH_LIMIT])

    confidence = (score_acc / max(1, total_matches)) if total_matches else 0.0
    return {
        "tokens_consulta": tokens,
        "confianca_busca": round(confidence, 4),
        "total_registros_relevantes_enviados": total_matches,
        "registros_relevantes": matches,
    }


def _is_full_audit_query(user_query: str) -> bool:
    query = _normalize_text(user_query or "")
    triggers = (
        "completo",
        "completa",
        "todos os registros",
        "todo historico",
        "historico completo",
        "auditoria",
        "do primeiro ao ultimo",
        "primeiro ao ultimo",
    )
    return any(t in query for t in triggers)


def _intent_score(user_query: str) -> float:
    query = _normalize_text(user_query)
    score = 0.0
    strong = ("auditoria", "historico", "primeiro", "todos", "completo")
    for term in strong:
        if term in query:
            score += 1.0
    if "?" in (user_query or ""):
        score += 0.2
    if len((user_query or "").split()) > 12:
        score += 0.3
    return score


def _build_full_audit_context(user_query: str, full_sources: dict) -> dict:
    tokens = _query_tokens(user_query)
    if not tokens:
        return {"modo": "auditoria_completa", "tokens_consulta": [], "resumo": {}}

    summary = {}
    total_matches = 0
    exemplars = {}

    for filename, records in full_sources.items():
        count = 0
        first_match_dt: datetime | None = None
        first_match = ""
        last_match_dt: datetime | None = None
        last_match = ""
        samples = []

        for rec in records:
            score = _record_semantic_score(rec, tokens)
            if score <= 0.55:
                continue

            count += 1
            ts = _extract_timestamp(rec)
            ts_dt = _parse_timestamp(ts)
            if ts_dt:
                if first_match_dt is None or ts_dt < first_match_dt:
                    first_match_dt, first_match = ts_dt, ts
                if last_match_dt is None or ts_dt > last_match_dt:
                    last_match_dt, last_match = ts_dt, ts
            if len(samples) < FULL_AUDIT_SAMPLE_LIMIT:
                samples.append(rec)

        if count:
            summary[filename] = {
                "total_correspondencias": count,
                "primeira_correspondencia": first_match,
                "ultima_correspondencia": last_match,
            }
            exemplars[filename] = _shrink_value(samples)
            total_matches += count

    return {
        "modo": "auditoria_completa",
        "tokens_consulta": tokens,
        "total_correspondencias_no_historico": total_matches,
        "resumo": summary,
        "amostras_representativas": exemplars,
    }


def _build_query_context_with_fallback(user_query: str, full_sources: dict, force_audit: bool) -> tuple[dict, str]:
    if force_audit:
        return _build_full_audit_context(user_query, full_sources), "auditoria_por_intencao"

    default_context = _build_query_specific_context(user_query, full_sources)
    if default_context.get("total_registros_relevantes_enviados", 0) >= QUERY_LOW_CONFIDENCE_THRESHOLD:
        return default_context, "padrao"

    # fallback automático: auditoria quando confiança está fraca.
    fallback = _build_full_audit_context(user_query, full_sources)
    fallback["motivo_fallback"] = "baixa_confianca_no_modo_padrao"
    return fallback, "auditoria_por_fallback"


def _load_db_sources(user_query: str) -> dict:
    full_sources = _load_all_sources()
    consolidated = _get_cached_or_build_consolidated(full_sources)

    force_audit = _is_full_audit_query(user_query) or _intent_score(user_query) >= 2.0
    query_context, mode = _build_query_context_with_fallback(user_query, full_sources, force_audit)

    return {
        "modo_consulta": mode,
        "estado_consolidado": consolidated,
        "contexto_recente": _build_recent_context(full_sources),
        "consulta_especifica": query_context,
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


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4))


def _build_user_message(user_query: str) -> str:
    global _LAST_CONTEXT_META
    sources = _load_db_sources(user_query)
    partial_notice = _build_partial_context_notice(sources)
    try:
        db_json = json.dumps(sources, ensure_ascii=False)
    except Exception:
        db_json = str(sources)[:20000]

    truncated_chars = 0
    if len(db_json) > MAX_SOURCE_CHARS:
        truncated_chars = len(db_json) - MAX_SOURCE_CHARS
        db_json = (
            f"{db_json[:MAX_SOURCE_CHARS]}"
            f"\n\n[CONTEXTO TRUNCADO: {truncated_chars} chars removidos]"
        )

    message = (f"{partial_notice}\n\n" if partial_notice else "") + (
        f"{db_json}\n\n"
        f"Pergunta do usuário: {user_query}\n"
        "Responda com base no estado consolidado e no recorte recente/relevante. "
        "Quando modo_consulta for auditoria, considere o resumo de correspondências no histórico inteiro como fonte principal. "
        "No final, adicione um bloco 'EVIDENCIAS_USADAS' com fontes consultadas, quantidade de registros e se houve truncamento. Se houver nomes_ambiguos no contexto, explicite necessidade de desambiguação antes de afirmar destinatário."
    )

    _LAST_CONTEXT_META = {
        "modo_consulta": sources.get("modo_consulta", "desconhecido"),
        "tokens_input_estimado": _estimate_tokens(message),
        "chars_prompt": len(message),
        "chars_truncados": truncated_chars,
        "fontes": list(DB_FILES),
        "registros_relevantes": sources.get("consulta_especifica", {}).get(
            "total_registros_relevantes_enviados",
            sources.get("consulta_especifica", {}).get("total_correspondencias_no_historico", 0),
        ),
    }
    return message


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
        _emit_telemetry("sucesso", _LAST_CONTEXT_META)
        if isinstance(content, str):
            return ia._apply_agent_prompt_template(content)
        return content
    except Exception as e:
        err_msg = str(e).lower()
        print(f"[chat.respond_chat] Erro ao consultar LLM: {e}")
        _emit_telemetry("erro", _LAST_CONTEXT_META)
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
