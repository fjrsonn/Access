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


def _source_file_name(source_key: str) -> str:
    meta = DB_SOURCES.get(source_key)
    if not meta:
        return source_key
    return os.path.basename(meta.get("path") or source_key)


def _format_record_line(rec: dict) -> str:
    dh = rec.get("DATA_HORA", "-")
    nome = rec.get("NOME", "-")
    sobrenome = rec.get("SOBRENOME", "-")
    bloco = rec.get("BLOCO", "-")
    ap = rec.get("APARTAMENTO", "-")
    placa = rec.get("PLACA", "-")
    status = rec.get("STATUS", "-")
    origem = rec.get("_db", "-")
    return (
        f"{dh} | {nome} {sobrenome} | BLOCO {bloco} AP {ap} | "
        f"PLACA {placa} | STATUS {status} | FONTE {_source_file_name(str(origem).lower())}"
    )




def _is_meaningful_record(rec: dict) -> bool:
    keys = ("NOME", "SOBRENOME", "BLOCO", "APARTAMENTO", "PLACA", "STATUS", "DATA_HORA")
    for k in keys:
        v = str(rec.get(k, "") or "").strip()
        if v and v != "-":
            return True
    return False

def _fontes_texto(resultados: List[dict], fallback_sources: Iterable[str] = ()) -> str:
    keys = {str(r.get("_db", "")).lower() for r in resultados if r.get("_db")}
    keys.update(str(s).lower() for s in fallback_sources if s)
    if not keys:
        return "Fontes consultadas: nenhum banco identificado."
    arquivos = sorted({_source_file_name(k) for k in keys})
    return "Fontes consultadas: " + ", ".join(arquivos) + "."


def _person_signature(rec: dict):
    return (
        str(rec.get("NOME", "") or "").strip(),
        str(rec.get("SOBRENOME", "") or "").strip(),
        str(rec.get("BLOCO", "") or "").strip(),
        str(rec.get("APARTAMENTO", "") or "").strip(),
        str(rec.get("STATUS", "") or "").strip(),
    )


def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", _normalize_text(text))


def _record_name_tokens(rec: dict) -> set:
    nome = str(rec.get("NOME", "") or "")
    sobrenome = str(rec.get("SOBRENOME", "") or "")
    return set(_tokenize_words(f"{nome} {sobrenome}"))


def fallback_search(user_query: str, records: List[dict], consulted_sources: Iterable[str] = ()) -> str:
    try:
        q = _normalize_text(user_query)
        results = []
        partial_mode = False
        is_count = any(term in q for term in ("quantos", "quantas", "quantidade", "total"))
        asks_last = "ultima entrada" in q or "ultimo acesso" in q or "ultima passagem" in q
        asks_open = any(term in q for term in ("aberto", "abertos", "aberta", "abertas"))
        asks_apartment = (
            "apartamento" in q
            or "apartamneto" in q
            or "apto" in q
            or re.search(r"\bap\b", q) is not None
        )

        wants_avisos = "aviso" in q or "avisos" in q
        wants_analises = "analise" in q or "analises" in q
        wants_dadosend = "dadosend" in q or "dados end" in q or "banco final" in q
        wants_dadosinit = "dadosinit" in q or "dados init" in q or "banco inicial" in q

        m = re.search(r"\bbloco\s*(\d+)", q)
        block = m.group(1) if m else None
        m_ap = re.search(r"\b(?:apartamento|ap)\s*(\d+)", q)
        apartment = m_ap.group(1) if m_ap else None
        m2 = re.search(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", q)
        date_filter = m2.group(1) if m2 else None

        if "visit" in q or "visitante" in q:
            st = "VISITANTE"
        elif "morador" in q or "moradores" in q:
            st = "MORADOR"
        else:
            st = None

        stopwords = {
            "quantos", "quantas", "quantidade", "total", "quais", "qual", "como", "onde", "temos", "tem",
            "ha", "existe", "existem", "listar", "liste", "mostre", "mostrar", "por", "de", "do", "da",
            "dos", "das", "em", "no", "na", "nos", "nas", "os", "as", "o", "a", "que", "me", "para",
            "ultima", "ultimo", "entrada", "acesso", "passagem", "aberto", "abertos", "aberta", "abertas",
            "avisos", "aviso", "analise", "analises", "bloco", "apartamento", "ap", "tem", "temos",
            "esta", "está", "foi", "qual", "quero", "saber", "encontra", "encontra-se", "se"
        }
        tokens = [t for t in re.findall(r"[a-z0-9]+", q) if len(t) > 1 and t not in stopwords]
        name_hint_tokens = [
            t
            for t in tokens
            if t.isalpha() and t not in {"apartamento", "apartamneto", "apto", "bloco", "morador", "visitante"}
        ]

        filtered_records = records
        if any((wants_avisos, wants_analises, wants_dadosend, wants_dadosinit)):
            wanted = set()
            if wants_avisos:
                wanted.add("avisos")
            if wants_analises:
                wanted.add("analises")
            if wants_dadosend:
                wanted.add("dadosend")
            if wants_dadosinit:
                wanted.add("dadosinit")
            filtered_records = [r for r in records if str(r.get("_db", "")).lower() in wanted]

        filtered_records = [r for r in filtered_records if _is_meaningful_record(r)]

        for r in filtered_records:
            ok = True
            if block and str(r.get("BLOCO", "")).lower() != block.lower():
                ok = False
            if apartment and str(r.get("APARTAMENTO", "")).lower() != apartment.lower():
                ok = False
            if date_filter and date_filter not in str(r.get("DATA_HORA", "") or ""):
                ok = False
            if st and (r.get("STATUS") or "").lower() != st.lower():
                ok = False
            if asks_open and (r.get("STATUS") or "").lower() not in ("aberto", "aberta", "open"):
                ok = False

            if ok and (asks_apartment or asks_last) and name_hint_tokens:
                rec_name = _record_name_tokens(r)
                if rec_name and not any(tok in rec_name for tok in name_hint_tokens):
                    ok = False

            if ok and tokens:
                text_tokens = set(_tokenize_words(" ".join(str(v) for v in r.values())))
                if not all(tok in text_tokens for tok in tokens):
                    ok = False

            if ok:
                results.append(r)

        if not results and tokens:
            scored = []
            for r in filtered_records:
                text_tokens = set(_tokenize_words(" ".join(str(v) for v in r.values())))
                score = sum(1 for tok in tokens if tok in text_tokens)
                if (asks_apartment or asks_last) and name_hint_tokens:
                    rec_name = _record_name_tokens(r)
                    if rec_name:
                        score += 2 * sum(1 for tok in name_hint_tokens if tok in rec_name)
                if score:
                    scored.append((score, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            if scored:
                max_score = scored[0][0]
                min_score = max(1, min(max_score, 2))
                filtered_scored = [(s, r) for s, r in scored if s >= min_score]
                if filtered_scored:
                    partial_mode = True
                    results = [r for _, r in filtered_scored[:50]]

        fontes = _fontes_texto(results, fallback_sources=list(consulted_sources) + [r.get("_db") for r in filtered_records[:200]])

        if asks_apartment and results:
            with_date = [r for r in results if _parse_datetime(str(r.get("DATA_HORA", "")))]
            ranked = with_date if with_date else results
            ranked.sort(key=lambda r: _parse_datetime(str(r.get("DATA_HORA", ""))) or datetime.min, reverse=True)
            alvo = ranked[0]

            n = str(alvo.get("NOME", "-") or "-").strip()
            sn = str(alvo.get("SOBRENOME", "-") or "-").strip()
            b = str(alvo.get("BLOCO", "-") or "-").strip()
            a = str(alvo.get("APARTAMENTO", "-") or "-").strip()
            if a and a != "-":
                opcoes = {
                    _person_signature(r)
                    for r in results
                    if str(r.get("NOME", "")).strip().lower() == n.lower()
                    and str(r.get("SOBRENOME", "")).strip().lower() == sn.lower()
                }
                if len(opcoes) > 1 and not block and not apartment:
                    lista = []
                    for pn, ps, pb, pa, pst in list(opcoes)[:5]:
                        lista.append(f"• {pn} {ps} — bloco {pb}, apartamento {pa}, status {pst}.")
                    return (
                        "Após a conferência dos bancos de dados, identifiquei múltiplas ocorrências para a pessoa consultada. "
                        "Para assegurar precisão absoluta, preciso de um refinamento adicional (por exemplo: bloco, apartamento ou data).\n"
                        "Opções encontradas:\n"
                        + "\n".join(lista)
                        + "\n"
                        + fontes
                    )
                return (
                    f"Com certeza. Após uma análise minuciosa dos registros, verifiquei que {n} {sn} está associado ao apartamento {a}, no bloco {b}.\n"
                    f"Como referência, o registro mais recente identificado foi: {_format_record_line(alvo)}\n"
                    f"{fontes}"
                )

        if asks_last and results:
            with_date = [r for r in results if _parse_datetime(str(r.get("DATA_HORA", "")))]
            ranked = with_date if with_date else results
            ranked.sort(key=lambda r: _parse_datetime(str(r.get("DATA_HORA", ""))) or datetime.min, reverse=True)
            latest = ranked[0]

            nome_consulta = [r for r in results if str(r.get("NOME", "")).strip()]
            distintos = {(str(r.get("NOME", "")).strip(), str(r.get("SOBRENOME", "")).strip(), str(r.get("BLOCO", "")).strip(), str(r.get("APARTAMENTO", "")).strip()) for r in nome_consulta}
            if len(distintos) > 1 and not block and not apartment:
                opcoes = []
                for n, s, b, a in list(distintos)[:5]:
                    opcoes.append(f"- {n} {s} (bloco {b}, apartamento {a}).")
                return (
                    "A sua consulta sobre a última entrada retornou múltiplos resultados para nomes semelhantes. "
                    "Para que eu forneça a informação exata, peço, por gentileza, um refinamento com bloco, apartamento ou data aproximada.\n"
                    "Possibilidades identificadas:\n"
                    + "\n".join(opcoes)
                    + "\n"
                    + fontes
                )

            return (
                "Com certeza. Após uma verificação criteriosa dos bancos consultados, a ocorrência mais recente localizada é a seguinte:\n"
                f"{_format_record_line(latest)}\n"
                "Caso deseje, posso complementar a leitura com recorte por período, status ou unidade residencial.\n"
                f"{fontes}"
            )

        if is_count:
            target = "registros"
            if wants_avisos:
                target = "avisos"
            elif wants_analises:
                target = "análises"
            resumo = f"Após a consolidação dos dados, localizei {len(results)} {target} para os critérios informados."
            if not results:
                return resumo + "\n" + fontes
            details = "\n".join(_format_record_line(rec) for rec in results[:200])
            return f"{resumo}\n\nDetalhamento:\n{details}\n\n{fontes}"

        if not results:
            return (
                "Realizei uma consulta abrangente nos bancos disponíveis, porém não localizei registros aderentes ao pedido informado. "
                "Se desejar, posso refinar a busca com nome completo, bloco, apartamento, data/hora ou status para elevar a precisão.\n"
                + fontes
            )

        lines = "\n".join(_format_record_line(rec) for rec in results[:20])
        if partial_mode:
            return (
                "Com base na interpretação da pergunta livre, identifiquei registros correlatos e potencialmente úteis para o seu pedido. "
                "Caso deseje precisão unívoca, posso refinar imediatamente por nome completo, bloco, apartamento, data ou status.\n"
                f"{lines}\n\n"
                f"{fontes}"
            )
        return (
            "Perfeitamente. A partir da análise consolidada dos bancos consultados, apresento abaixo o resultado detalhado da sua solicitação:\n"
            f"{lines}\n\n"
            "Se desejar, posso organizar os mesmos dados por ordem cronológica, por unidade residencial ou por tipo de ocorrência.\n"
            f"{fontes}"
        )
    except Exception as e:
        return f"Erro ao processar consulta (fallback): {e}"
