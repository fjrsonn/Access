#!/usr/bin/env python3
"""Agente de consulta para múltiplos bancos JSON."""
import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, Iterable, List, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_SOURCES: Dict[str, Dict[str, str]] = {
    "dadosinit": {"path": os.path.join(BASE_DIR, "dadosinit.json"), "label": "DADOSINIT"},
    "dadosend": {"path": os.path.join(BASE_DIR, "dadosend.json"), "label": "DADOSEND"},
    "analises": {"path": os.path.join(BASE_DIR, "analises.json"), "label": "ANALISES"},
    "avisos": {"path": os.path.join(BASE_DIR, "avisos.json"), "label": "AVISOS"},
}

SOURCE_PATTERNS: Dict[str, List[str]] = {
    "dadosinit": [r"\bdados\s*init\b", r"\bdadosinit\b", r"\binicial\b", r"\bentrada\b", r"\binicio\b"],
    "dadosend": [r"\bdados\s*end\b", r"\bdadosend\b", r"\bsaida\b", r"\bfinal\b"],
    "analises": [r"\banalises\b", r"\banalise\b"],
    "avisos": [r"\bavisos\b", r"\baviso\b"],
    "todos": [r"\btodos\b", r"\btodas\b"],
}


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", str(text))
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    return norm.lower()


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _coerce_registros(data) -> List[dict]:
    if isinstance(data, dict) and "registros" in data:
        regs = data.get("registros") or []
        return regs if isinstance(regs, list) else list(regs)
    if isinstance(data, list):
        return data
    return []


def select_sources(user_query: str, default: Iterable[str] = ("dadosend",)) -> List[str]:
    query_norm = _normalize_text(user_query)
    if not query_norm:
        return list(default)

    if any(re.search(pat, query_norm) for pat in SOURCE_PATTERNS["todos"]):
        return list(DB_SOURCES.keys())

    selected = []
    for source, patterns in SOURCE_PATTERNS.items():
        if source == "todos":
            continue
        for pat in patterns:
            if re.search(pat, query_norm):
                selected.append(source)
                break

    return selected or list(default)


def load_database(source_key: str) -> List[dict]:
    meta = DB_SOURCES.get(source_key)
    if not meta:
        return []
    data = _read_json(meta["path"])
    return _coerce_registros(data)

def load_database_from_path(path: str) -> List[dict]:
    data = _read_json(path)
    return _coerce_registros(data)

def tag_records(records: Iterable[dict], source_label: str) -> List[dict]:
    tagged: List[dict] = []
    for rec in records:
        if not isinstance(rec, dict):
            continue
        rec_copy = dict(rec)
        rec_copy["_db"] = source_label
        tagged.append(rec_copy)
    return tagged


def build_database(user_query: str, default_sources: Iterable[str] = ("dadosend",)) -> Tuple[List[dict], List[str]]:
    sources = select_sources(user_query, default=default_sources)
    combined: List[dict] = []
    for source in sources:
        combined.extend(tag_records(load_database(source), source))
    return combined, sources


def format_sources(sources: Iterable[str]) -> str:
    labels = []
    for source in sources:
        meta = DB_SOURCES.get(source)
        labels.append(meta["label"] if meta else source.upper())
    return ", ".join(labels) if labels else "NENHUM"


def _parse_datetime(ds: str):
    if not ds:
        return None
    s = (ds or "").strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def fallback_search(user_query: str, records: List[dict]) -> str:
    try:
        q = _normalize_text(user_query)
        results = []
        m = re.search(r"\bbloco\s*(\d+)", q)
        block = m.group(1) if m else None
        m2 = re.search(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", q)
        date_filter = m2.group(1) if m2 else None
        if "visit" in q or "visitante" in q:
            st = "VISITANTE"
        elif "morador" in q or "moradores" in q:
            st = "MORADOR"
        else:
            st = None

        tokens = [t for t in re.findall(r"[a-z0-9]+", q) if len(t) > 1]

        for r in records:
            ok = True
            if block and str(r.get("BLOCO", "")).lower() != str(block).lower():
                ok = False
            if date_filter:
                dh = r.get("DATA_HORA", "") or ""
                if date_filter not in dh:
                    ok = False
            if st and (r.get("STATUS") or "").lower() != st.lower():
                ok = False

            if ok and tokens:
                text = _normalize_text(" ".join(str(v) for v in r.values()))
                if not all(tok in text for tok in tokens):
                    ok = False

            if ok:
                results.append(r)

        if not results and tokens:
            scored = []
            for r in records:
                text = _normalize_text(" ".join(str(v) for v in r.values()))
                score = sum(1 for tok in tokens if tok in text)
                if score:
                    scored.append((score, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [r for _, r in scored[:200]]

        if not results:
            return (
                "NENHUM REGISTRO ENCONTRADO COM OS FILTROS APLICADOS (FALLBACK). "
                "SE DESEJAR RESPOSTAS MAIS FLEXIVEIS, CONFIGURE GROQ_API_KEY PARA USAR A IA."
            ).upper()

        lines = []
        for rec in results[:200]:
            dh = rec.get("DATA_HORA", "-")
            nome = rec.get("NOME", "-")
            sobrenome = rec.get("SOBRENOME", "-")
            bloco = rec.get("BLOCO", "-")
            ap = rec.get("APARTAMENTO", "-")
            placa = rec.get("PLACA", "-")
            status = rec.get("STATUS", "-")
            origem = rec.get("_db", "-")
            lines.append(
                f"{str(dh).upper()} | {str(nome).upper()} {str(sobrenome).upper()} | "
                f"BLOCO {str(bloco).upper()} AP {str(ap).upper()} | "
                f"PLACA {str(placa).upper()} | {str(status).upper()} | DB {str(origem).upper()}"
            )
        summary = f"RESULTADOS ({len(results)}):\n" + "\n".join(lines)
        return summary
    except Exception as e:
        return f"ERRO AO PROCESSAR CONSULTA (FALLBACK): {e}".upper()
