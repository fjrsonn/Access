import json
import os
import re
import hashlib
import unicodedata
from datetime import datetime
from typing import Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RULES_FILE = os.path.join(BASE_DIR, "keyword_rules.json")
AUDIT_FILE = os.path.join(BASE_DIR, "logs", "audit_events.jsonl")
RULES_VERSION = "v2.0"

DEFAULT_RULES = {
    "keywords_orientacoes": [
        "relato", "relatos", "relatado", "ocorrencia", "ocorrências", "ocorrido",
        "registro", "registrado", "orientado", "orientada", "orientacao", "orientação", "orientados",
    ],
    "keywords_observacoes": [
        "aviso", "avisos", "avisar", "avisado", "avisados", "receber", "entregar", "guardar",
        "errado", "errada", "engano", "enganada", "enganado",
    ],
    "keywords_encomendas": [
        "encomenda", "encomendas", "pacote", "entrega", "shopee", "amazon", "mercado livre", "correios",
    ],
    "context_observacoes": ["quando chegar", "avisar", "morador", "nome", "bloco", "apartamento"],
    "context_orientacoes": ["ocorrencia", "ocorrido", "relato", "registrado", "orientado", "portaria"],
}


def _normalize_text(text: str) -> str:
    raw = (text or "").lower()
    no_accents = "".join(c for c in unicodedata.normalize("NFKD", raw) if not unicodedata.combining(c))
    return no_accents


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9à-öø-ÿ]+", _normalize_text(text))


def load_rules() -> dict:
    if not os.path.exists(RULES_FILE):
        return dict(DEFAULT_RULES)
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULT_RULES)
        if isinstance(data, dict):
            merged.update({k: v for k, v in data.items() if isinstance(v, list)})
        return merged
    except Exception:
        return dict(DEFAULT_RULES)


def _score_by_keywords(text: str, keywords: list[str], contexts: list[str]) -> float:
    norm = _normalize_text(text)
    toks = set(_tokens(text))
    score = 0.0
    for kw in keywords:
        nkw = _normalize_text(kw)
        if " " in nkw:
            if nkw in norm:
                score += 2.2
        elif nkw in toks:
            score += 2.0
        elif re.search(rf"\b{re.escape(nkw)}[a-z]*\b", norm):
            score += 1.2
    for ctx in contexts:
        if _normalize_text(ctx) in norm:
            score += 0.7
    return score


def _score_encomenda(text: str, rules: dict) -> float:
    norm = _normalize_text(text)
    toks = set(_tokens(text))
    score = 0.0
    for kw in rules.get("keywords_encomendas", []):
        nkw = _normalize_text(kw)
        if " " in nkw:
            if nkw in norm:
                score += 2.0
        elif nkw in toks:
            score += 1.8
    if re.search(r"\b(bloco|bl)\s*\d+\b", norm) and re.search(r"\b(ap|apto|apartamento|unidade)\s*\d+\b", norm):
        score += 0.8
    if re.search(r"\b\d{5,}\b", norm):
        score += 0.6
    return score


def classificar_destino_texto(texto: str, parsed: dict | None = None) -> dict:
    rules = load_rules()
    s_orient = _score_by_keywords(texto, rules.get("keywords_orientacoes", []), rules.get("context_orientacoes", []))
    s_obs = _score_by_keywords(texto, rules.get("keywords_observacoes", []), rules.get("context_observacoes", []))
    s_enc = _score_encomenda(texto, rules)

    # Evitar conflitos com texto de acesso veicular (já extraído por parsed)
    if parsed and (parsed.get("PLACA") or parsed.get("MODELOS")):
        s_enc = max(0.0, s_enc - 1.0)

    scores = {"orientacoes": s_orient, "observacoes": s_obs, "encomendas": s_enc}
    destino = max(scores, key=scores.get)
    top = scores[destino]
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    second = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
    ambiguo = abs(top - second) < 0.9
    confianca = 0.0 if top <= 0 else min(1.0, (top + 0.1) / (top + second + 0.2))

    if top < 1.0:
        destino = "dados"
    motivo = f"scores={scores}; escolhido={destino}"
    return {
        "destino": destino,
        "motivo": motivo,
        "score": round(top, 3),
        "scores": scores,
        "ambiguo": ambiguo,
        "confianca": round(confianca, 3),
        "versao_regras": RULES_VERSION,
    }


_FIELDS = ["BLOCO", "APARTAMENTO", "NOME", "SOBRENOME", "HORARIO", "VEICULO", "COR", "PLACA"]


def extract_fields_strict(text: str) -> dict:
    up = (text or "").upper()
    out = {k: [] for k in _FIELDS}

    for m in re.finditer(r"\b(?:BLOCO|BL)\s*[:\-]?\s*([A-Z0-9]{1,6})\b", up):
        out["BLOCO"].append(m.group(1))
    for m in re.finditer(r"\b(?:APARTAMENTO|APTO|APT|AP|UNIDADE|UN)\s*[:\-]?\s*([0-9]{1,4}[A-Z]?)\b", up):
        out["APARTAMENTO"].append(m.group(1))
    for m in re.finditer(r"\b([01]?\d|2[0-3])[:H]([0-5]\d)\b", up):
        out["HORARIO"].append(f"{int(m.group(1)):02d}:{m.group(2)}")
    for m in re.finditer(r"\b([A-Z]{3}[0-9][A-Z0-9][0-9]{2}|[A-Z]{3}[0-9]{4})\b", up):
        out["PLACA"].append(m.group(1))
    for m in re.finditer(r"\bCOR\s*[:\-]?\s*([A-ZÇÃÕÁÉÍÓÚÀÂÊÔÜ]{3,})\b", up):
        out["COR"].append(m.group(1))

    # nome contextual estrito
    for m in re.finditer(r"\b(?:MORADOR(?:A)?|SR\.?|SRA\.?|SENHOR|SENHORA|NOME)\s*[:\-]?\s*([A-ZÀ-Ý]{2,}(?:\s+[A-ZÀ-Ý]{2,})+)\b", up):
        parts = [p for p in re.sub(r"\s+", " ", m.group(1)).strip().split() if p]
        if len(parts) >= 2:
            out["NOME"].append(parts[0])
            out["SOBRENOME"].append(" ".join(parts[1:]))

    # dedup
    for k in out:
        seen = []
        for v in out[k]:
            if v and v not in seen:
                seen.append(v)
        out[k] = seen
    return out


def extract_fields_heuristic(text: str, strict: dict | None = None) -> dict:
    up = (text or "").upper()
    strict = strict or {k: [] for k in _FIELDS}
    out = {k: list(strict.get(k, [])) for k in _FIELDS}

    # infer veículo após "ENCOMENDA" raramente útil, manter baixo impacto
    for m in re.finditer(r"\b(?:VEICULO|VEÍCULO|CARRO|MOTO|MODELO)\s*[:\-]?\s*([A-Z0-9]{2,}(?:\s+[A-Z0-9]{2,}){0,2})", up):
        cand = m.group(1).strip()
        if cand and cand not in out["VEICULO"]:
            out["VEICULO"].append(cand)

    return out


def build_structured_fields(text: str) -> tuple[dict, dict]:
    strict = extract_fields_strict(text)
    inferred = extract_fields_heuristic(text, strict)
    # keep only inferred extras for inferred map
    only_inferred = {k: [v for v in inferred.get(k, []) if v not in strict.get(k, [])] for k in _FIELDS}
    return strict, only_inferred


def validate_structured_record(rec: dict) -> tuple[bool, list[str]]:
    errors = []
    required = ["id", "tipo", "texto", "data_hora", "processado"]
    for k in required:
        if k not in rec:
            errors.append(f"campo_obrigatorio_ausente:{k}")
    if rec.get("tipo") not in ("ORIENTACAO", "OBSERVACAO"):
        errors.append("tipo_invalido")
    if not isinstance(rec.get("texto", ""), str):
        errors.append("texto_invalido")
    if not isinstance(rec.get("processado"), bool):
        errors.append("processado_invalido")
    if "campos_extraidos_confirmados" in rec and not isinstance(rec.get("campos_extraidos_confirmados"), dict):
        errors.append("campos_extraidos_confirmados_invalido")
    if "campos_extraidos_inferidos" in rec and not isinstance(rec.get("campos_extraidos_inferidos"), dict):
        errors.append("campos_extraidos_inferidos_invalido")
    return len(errors) == 0, errors


def _hash_text(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]


def log_audit_event(event: str, destino: str, texto: str, **extra: Any) -> None:
    os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
    payload = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "destino": destino,
        "texto_hash": _hash_text(texto),
        "versao_regras": RULES_VERSION,
    }
    payload.update(extra)
    try:
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
