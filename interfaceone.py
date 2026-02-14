#!/usr/bin/env python3
# interfaceone.py (versão corrigida — usa preprocessor.extrair_tudo_consumo
#  - evita atribuições erradas
#  - insere _entrada_id no append otimista para permitir merge pelo ia.processar
#  - adiciona token_common_prefix_len para overlay)
import os
import re
import sys
import json
import tempfile
import time
import unicodedata
import threading
import subprocess
from datetime import datetime
from collections import Counter
from typing import List, Iterable

try:
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import ttk, scrolledtext
except Exception as e:
    tk = None
    tkfont = None
    ttk = None
    scrolledtext = None
    print("Aviso: tkinter não disponível:", e)

# rapidfuzz opcional (fallback sem fuzzy quando indisponível)
try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
except Exception:
    rf_process = None
    rf_fuzz = None

# tentativas de módulo ia (opcionais)
try:
    import ia as ia_module
    HAS_IA_MODULE = True
except Exception:
    ia_module = None
    HAS_IA_MODULE = False

try:
    import chat as chat_module
    HAS_CHAT_MODULE = True
except Exception:
    chat_module = None
    HAS_CHAT_MODULE = False

# Import do parser robusto
try:
    from preprocessor import extrair_tudo_consumo, corrigir_token_nome
except Exception:
    # se faltar, manter compatibilidade — o código só chamará extrair_tudo_consumo quando disponível
    extrair_tudo_consumo = None
    corrigir_token_nome = None

try:
    from text_classifier import (
        classificar_destino_texto,
        build_structured_fields,
        validate_structured_record,
        log_audit_event,
        load_rules,
    )
except Exception:
    classificar_destino_texto = None
    build_structured_fields = None
    validate_structured_record = None
    log_audit_event = None
    load_rules = None

try:
    from interfaceone_core import decidir_destino, montar_registro_acesso, montar_entrada_bruta
except Exception:
    decidir_destino = None
    montar_registro_acesso = None
    montar_entrada_bruta = None

try:
    from runtime_status import report_status, report_log
except Exception:
    def report_status(*args, **kwargs):
        return None
    def report_log(*args, **kwargs):
        return None



def _log_ui(level: str, stage: str, message: str, **details):
    report_log("interfaceone", level, message, stage=stage, details=details)
    print(f"[interfaceone] {message}")
# paths
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "dados")
os.makedirs(DATA_DIR, exist_ok=True)
SUGG_PATH = os.path.join(DATA_DIR, "suggestions.txt")
DB_FILE = os.path.join(BASE, "dadosend.json")
IN_FILE = os.path.join(BASE, "dadosinit.json")
ENCOMENDAS_IN_FILE = os.path.join(BASE, "encomendasinit.json")
ENCOMENDAS_DB_FILE = os.path.join(BASE, "encomendasend.json")
ORIENTACOES_FILE = os.path.join(BASE, "orientacoes.json")
OBSERVACOES_FILE = os.path.join(BASE, "observacoes.json")
AVISOS_FILE = os.path.join(BASE, "avisos.json")
ANALISES_FILE = os.path.join(BASE, "analises.json")
_DB_LOCKFILE = DB_FILE + ".lock"
DB_PANEL_COMMANDS = {
    "/dadosinit.json": IN_FILE,
    "/dadosend.json": DB_FILE,
    "/analises.json": ANALISES_FILE,
    "/avisos.json": AVISOS_FILE,
}
_warning_bar = None

_ENCOMENDA_TIPO_TOKENS = {
    "ENCOMENDA",
    "PACOTE",
    "PAC",
    "PCT",
    "CAIXA",
    "CIXA",
    "CX",
    "ENVELOPE",
    "ENV",
    "SACOLA",
    "SACO",
    "CAIXA",
    "CARTA",
    "ENTREGA",
    "PACT",
    "PACOT",
    "PA",
    "CAIX",
    "EV",
    "ENVEL",
    "ENVLOPE",
    "EVELOPE",
    "ENVELOP",
    "EVENLOPE",
    "SAC",
    "SA",
    "SACOL",
    "SCOLA",
    "SAOLA",
}
_ENCOMENDA_LOJA_TOKENS = {
    "SHOPEE",
    "SHOPE",
    "MERCADO",
    "MERCADOLIVRE",
    "ML",
    "AMAZON",
    "AMAZ",
    "AMA",
    "TIKTOK",
    "TIKT",
    "TIKOK",
    "TITOK",
    "TKTK",
    "JNT",
    "J&T",
    "J&TEXPRESS",
    "JNTEXPRESS",
    "MAGAZINE",
    "MAGAZIN",
    "MAGAZI",
    "MAGA",
    "MLUIZA",
    "MLIVRE",
    "MAGALU",
    "ALIEXPRESS",
    "ALIEXPRES",
    "ALIEX",
    "ALIEXPR",
    "ALIE",
    "SHEIN",
    "CORREIOS",
    "CORREI",
    "COREIOS",
    "COREIO",
    "CRREIOS",
    "CREIOS",
    "CORREIS",
    "SEDEX",
    "SED",
    "SDEX",
    "SEDE",
    "RIACHUELO",
    "RIAHULE",
    "RCHLO",
    "RACHUELO",
    "RENNER",
    "RENER",
    "RENE",
    "RENNE",
    "CEA",
    "C&A",
    "JADLOG",
    "JADLO",
    "JALOG",
    "KABUM",
    "KABUN",
    "KBUN",
    "TERABYTE",
    "TERBYT",
    "TERABITE",
    "GROWTH",
    "GRONWTH",
}
_ENCOMENDA_LOJA_PATTERNS = {
    "MERCADO LIVRE",
    "M LIVRE",
    "MERCADO LIV",
    "MERC LIVR",
    "J T EXPRESS",
    "JNT EXPRESS",
    "J T",
    "MAGAZINE LUIZA",
    "MAGAZIN LUZ",
    "MAGAZI LUIZA",
    "MAGA LUIZA",
    "M LUIZA",
    "TIKTOK",
    "ALIEXPRESS",
    "SHOPEE",
    "CORREIOS",
    "SEDEX",
    "RIACHUELO",
    "C A",
    "C&A",
    "JADLOG",
    "KABUM",
    "TERABYTE",
    "GROWTH",
}

def _match_encomenda_store_token(tokens_up):
    if rf_process is None or rf_fuzz is None:
        return False
    candidates = list(_ENCOMENDA_LOJA_TOKENS) + [p.replace(" ", "") for p in _ENCOMENDA_LOJA_PATTERNS]
    for tok in tokens_up:
        if not tok or tok.isdigit():
            continue
        best = rf_process.extractOne(tok, candidates, scorer=rf_fuzz.WRatio)
        if best and best[1] >= 88:
            return True
    return False

def _has_encomenda_identificacao(tokens_up):
    for tok in tokens_up:
        if re.match(r"^[A-Z]{3}\d{4}$", tok) or re.match(r"^[A-Z]{3}\d[A-Z]\d{2}$", tok):
            continue
        if re.match(r"^(?=.*\d)[A-Z0-9]{10,}$", tok):
            return True
    return False


def _has_bloco_ap_indicador(tokens_up):
    bloco_alias = {"BL", "BLO", "BLOCO", "BLCO", "BLC", "B"}
    ap_alias = {"AP", "APT", "APART", "APTA", "APARTAMEN", "APARTAMENTO", "A"}
    has_bloco = False
    has_ap = False
    for i, tok in enumerate(tokens_up):
        if tok in bloco_alias and i + 1 < len(tokens_up) and tokens_up[i + 1].isdigit():
            has_bloco = True
        if tok in ap_alias and i + 1 < len(tokens_up) and tokens_up[i + 1].isdigit():
            has_ap = True
        if re.match(r"^(BL|BLO|BLOCO|BLCO|BLC)\d+$", tok):
            has_bloco = True
        if re.match(r"^(AP|APT|APART|APTA|APARTAMEN|APARTAMENTO|A)\d+[A-Z]?$", tok):
            has_ap = True
    return has_bloco, has_ap

def _is_encomenda_text(text: str, parsed: dict = None) -> bool:
    if not text:
        return False
    toks = tokens(text)
    toks_up = [t.upper() for t in toks]
    normalized = _norm(text)
    if parsed:
        if parsed.get("PLACA") or parsed.get("MODELOS"):
            return False
    has_tipo = any(t in _ENCOMENDA_TIPO_TOKENS for t in toks_up)
    has_loja = any(t in _ENCOMENDA_LOJA_TOKENS for t in toks_up)
    has_nf = _has_encomenda_identificacao(toks_up)
    has_bloco, has_ap = _has_bloco_ap_indicador(toks_up)
    has_endereco = has_bloco and has_ap

    if has_loja and (has_tipo or has_nf or has_endereco):
        return True
    if has_tipo and (has_nf or has_endereco):
        return True
    if has_nf and has_endereco:
        return True

    for pattern in _ENCOMENDA_LOJA_PATTERNS:
        if pattern.replace(" ", "") in normalized.replace(" ", ""):
            if has_tipo or has_nf or has_endereco:
                return True
    if _match_encomenda_store_token(toks_up):
        return has_tipo or has_nf or has_endereco
    if has_nf and has_endereco:
        return True
    return False

def _save_encomenda_init(txt: str, now_str: str) -> None:
    try:
        existing = _read_json(ENCOMENDAS_IN_FILE)
        if isinstance(existing, dict) and "registros" in existing:
            regs = existing.get("registros") or []
        elif isinstance(existing, list):
            regs = existing
        else:
            regs = []
    except Exception:
        regs = []

    nid = _compute_next_in_id(regs)
    new_rec = {
        "id": nid,
        "texto": txt,
        "processado": False,
        "data_hora": now_str,
    }
    regs.append(new_rec)
    try:
        atomic_save(ENCOMENDAS_IN_FILE, {"registros": regs})
    except Exception as e:
        print("Erro save (ENCOMENDAS_IN_FILE):", e)


_loaded_rules = load_rules() if load_rules else {}
_ORIENTACOES_KEYWORDS = set(k.upper() for k in _loaded_rules.get("keywords_orientacoes", [
    "RELATO", "RELATOS", "RELATADO", "OCORRENCIA", "OCORRIDO", "REGISTRO", "REGISTRADO",
    "ORIENTADO", "ORIENTADA", "ORIENTACAO", "ORIENTADOS", "ORIENTAÇÕES", "ORIENTAÇÃO",
]))

_OBSERVACOES_KEYWORDS = set(k.upper() for k in _loaded_rules.get("keywords_observacoes", [
    "AVISO", "AVISOS", "AVISAR", "AVISADO", "AVISADOS", "RECEBER", "ENTREGAR", "GUARDAR",
    "ERRADO", "ERRADA", "ENGANO", "ENGANADA", "ENGANADO",
]))

def _contains_keywords(text: str, keywords: set[str]) -> bool:
    toks_up = [t.upper() for t in tokens(text)]
    return any(t in keywords for t in toks_up)

def _extract_multi_fields(text: str) -> dict:
    if build_structured_fields:
        strict, inferred = build_structured_fields(text)
        return {k: list(dict.fromkeys((strict.get(k, []) + inferred.get(k, [])))) for k in strict.keys()}
    return {
        "BLOCO": [], "APARTAMENTO": [], "NOME": [], "SOBRENOME": [],
        "HORARIO": [], "VEICULO": [], "COR": [], "PLACA": []
    }


def _save_structured_text(path: str, txt: str, now_str: str, tipo: str, decision_meta: dict = None) -> None:
    try:
        existing = _read_json(path)
        if isinstance(existing, dict) and "registros" in existing:
            regs = existing.get("registros") or []
        elif isinstance(existing, list):
            regs = existing
        else:
            regs = []
    except Exception:
        regs = []

    nid = _compute_next_in_id(regs)
    strict, inferred = build_structured_fields(txt) if build_structured_fields else ({}, {})
    merged = {k: list(dict.fromkeys((strict.get(k, []) + inferred.get(k, [])))) for k in (strict.keys() or ["BLOCO","APARTAMENTO","NOME","SOBRENOME","HORARIO","VEICULO","COR","PLACA"])}
    rec = {
        "id": nid,
        "tipo": tipo,
        "texto": txt,
        "campos_extraidos_confirmados": strict,
        "campos_extraidos_inferidos": inferred,
        "campos_extraidos": merged,
        "data_hora": now_str,
        "processado": True,
        "motivo_roteamento": (decision_meta or {}).get("motivo", ""),
        "versao_regras": (decision_meta or {}).get("versao_regras", "v1"),
        "confianca_classificacao": (decision_meta or {}).get("confianca", 0.0),
        "ambiguo": bool((decision_meta or {}).get("ambiguo", False)),
    }
    ok, errs = validate_structured_record(rec) if validate_structured_record else (True, [])
    if not ok:
        review_path = os.path.join(BASE, "fila_revisao.json")
        fila = _read_json(review_path)
        if not isinstance(fila, dict) or "registros" not in fila:
            fila = {"registros": []}
        fila["registros"].append({"erro": errs, "registro": rec})
        atomic_save(review_path, fila)
        if log_audit_event:
            log_audit_event("texto_validacao_falhou", tipo, txt, erros=errs)
        return

    regs.append(rec)
    atomic_save(path, {"registros": regs})
    if log_audit_event:
        log_audit_event("texto_persistido", tipo, txt, confianca=rec.get("confianca_classificacao"), ambiguo=rec.get("ambiguo"))


# ---------- util ----------
def _norm(s: str, keep_dash=False) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKD", str(s).strip().upper())
    s = "".join(c for c in s if not unicodedata.combining(c))
    patt = r"[^A-Z0-9\s\-]" if keep_dash else r"[^A-Z0-9\s]"
    return re.sub(r"\s+", " ", re.sub(patt, " ", s)).strip()

def clean_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()

def tokens(text):
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9\-]+", str(text or ""))

def atomic_save(path, obj):
    dirn = os.path.dirname(path) or "."
    os.makedirs(dirn, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirn, prefix=".tmp_", suffix=os.path.splitext(path)[1] or ".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception:
                pass

# helper: garante data_hora válida e salva o DB (uso centralizado para evitar nulls)
def sanitize_and_save_db(regs):
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    changed = False

    if not isinstance(regs, list):
        if isinstance(regs, dict) and "registros" in regs:
            regs = regs.get("registros") or []
        else:
            regs = list(regs) if regs is not None else []

    for r in regs:
        dh = r.get("DATA_HORA", None) or r.get("data_hora", None)
        if dh is None or (isinstance(dh, str) and dh.strip() == ""):
            r["DATA_HORA"] = now_str
            if "data_hora" in r:
                try: r.pop("data_hora")
                except Exception:
                    pass
            changed = True

    try:
        atomic_save(DB_FILE, {"registros": regs})
    except Exception:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump({"registros": regs}, f, ensure_ascii=False, indent=2)
        except Exception:
            print("Falha ao persistir DB em sanitize_and_save_db")

    return changed

def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return None

def parse_datetime(ds: str):
    if not ds: return None
    s = (ds or "").strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try: return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def date_of_datetime_str(ds: str) -> str:
    dt = parse_datetime(ds); return dt.strftime("%d/%m/%Y") if dt else ""

def ordinal_pt_upper(n: int) -> str:
    m = {1:"PRIMEIRO",2:"SEGUNDO",3:"TERCEIRO",4:"QUARTO",5:"QUINTO",6:"SEXTO",7:"SETIMO",8:"OITAVO",9:"NONO",10:"DECIMO"}
    return m.get(n, f"{n}º".upper())

# ---------- DB helpers ----------
def load_db():
    d = _read_json(DB_FILE)
    if isinstance(d, dict) and "registros" in d:
        regs = d.get("registros") or []
    elif isinstance(d, list):
        regs = d
    else:
        regs = []
    changed = False
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    for r in regs:
        dh = r.get("DATA_HORA", None) or r.get("data_hora", None)
        if dh is None or (isinstance(dh, str) and dh.strip() == ""):
            r["DATA_HORA"] = now_str
            if "data_hora" in r:
                try: r.pop("data_hora")
                except Exception:
                    pass
            changed = True
    if changed:
        try:
            sanitize_and_save_db(regs)
        except Exception:
            pass
    return regs

# ---------- helpers summary ----------
def full_name(r):
    n = (r.get("NOME","") or "").strip()
    s = (r.get("SOBRENOME","") or "").strip()
    full = (n + " " + s).strip()
    return clean_whitespace(full).upper() if full else "-"

def details_only(r):
    parts = []
    b = (r.get("BLOCO","") or "").strip()
    if b and b != "-": parts.append(f"BLOCO {b}")
    a = (r.get("APARTAMENTO","") or "").strip()
    if a and a != "-": parts.append(f"APARTAMENTO {a}")
    p = (r.get("PLACA","") or "").strip()
    if p and p != "-": parts.append(f"PLACA {p}")
    m = (r.get("MODELO","") or "").strip()
    if m and m != "-": parts.append(f"VEICULO {m}")
    c = (r.get("COR","") or "").strip()
    if c and c != "-": parts.append(f"COR {c}")
    s = (r.get("STATUS","") or "").strip()
    if s and s != "-": parts.append(f"STATUS {s}")
    return clean_whitespace(" ".join(parts)).upper() if parts else ""

def full_summary(r):
    n = full_name(r); d = details_only(r)
    return f"{n} — {d}" if d else n

# ---------- suggestions (mantido) ----------
_db_mtime = 0.0
_sugg_list: List[str] = []
_sugg_mtime = 0.0

def build_suggestions(max_entries=2000):
    db = load_db()
    if not db:
        open(SUGG_PATH, "w", encoding="utf-8").close(); return
    cnt = Counter(); rep = {}
    def add(x):
        if not x or not isinstance(x,str): return
        k = _norm(x, keep_dash=True)
        if not k: return
        cnt[k]+=1
        if k not in rep or len(x) > len(rep[k]): rep[k] = x.strip()
    for r in db:
        add(full_name(r))
        det = details_only(r)
        if det:
            add(det)
        for k in ("NOME","SOBRENOME","MODELO","COR","STATUS","PLACA","BLOCO","APARTAMENTO"):
            v = r.get(k)
            if v:
                add(str(v).strip())
                for t in tokens(v):
                    add(t)
        for t in tokens(details_only(r)): add(t)
    items = sorted(cnt.items(), key=lambda kv:(-kv[1], -len(kv[0])))
    suggs=[]
    for k,_ in items:
        v = rep.get(k,k)
        if v not in suggs: suggs.append(v)
        if len(suggs)>=max_entries: break
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(SUGG_PATH) or ".", prefix=".tmp_sugg_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for s in suggs: f.write(s.replace("\n"," ").strip()+"\n")
        os.replace(tmp, SUGG_PATH)
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception:
                pass

def sync_suggestions(force=False):
    global _db_mtime
    try: m = os.path.getmtime(DB_FILE) if os.path.exists(DB_FILE) else 0
    except: m=0
    if force or m==0 or m!=_db_mtime or not os.path.exists(SUGG_PATH):
        try: build_suggestions()
        except Exception:
            pass
        _db_mtime = m

def _load_suggestions(force=False):
    global _sugg_list, _sugg_mtime
    sync_suggestions()
    try: m = os.path.getmtime(SUGG_PATH) if os.path.exists(SUGG_PATH) else 0
    except: m=0
    if force or m==0 or m!=_sugg_mtime:
        if os.path.exists(SUGG_PATH):
            try:
                with open(SUGG_PATH,"r",encoding="utf-8") as f:
                    _sugg_list = [ln.strip() for ln in f if ln.strip()]; _sugg_mtime = m
            except: _sugg_list=[]; _sugg_mtime=m
        else:
            _sugg_list=[]; _sugg_mtime=m

def provider_suggestions(prefix: str, max_results: int = 6):
    p = (prefix or "").strip()
    if not p: return []
    _load_suggestions()
    if not _sugg_list: return []
    try:
        results = rf_process.extract(p, _sugg_list, scorer=rf_fuzz.WRatio, limit=max_results)
    except Exception:
        return []
    out=[]
    for item in results:
        if len(item) >= 2: out.append((item[0], float(item[1])))
    return out

def spelling_suggestions_for_token(token: str, max_results: int = 6):
    return [s for s,_ in provider_suggestions(token, max_results)][:max_results]

# ---------- TokenCache ----------
class TokenCache:
    def __init__(self, db_path):
        self.db_path = db_path; self.m = 0; self.map = {}
        self._build()
    def _mtime(self):
        try: return os.path.getmtime(self.db_path)
        except: return 0
    def _build(self):
        m = self._mtime()
        if m==self.m and self.map: return
        self.m = m; self.map = {}
        for r in load_db():
            def add(orig):
                if not orig or not isinstance(orig,str): return
                for t in tokens(orig):
                    k = _norm(t)
                    if len(k) < 2: continue
                    self.map.setdefault(k, []).append(r)
            add(full_name(r)); add(details_only(r))
            for key in ("NOME","SOBRENOME","MODELO","COR","STATUS","PLACA","BLOCO","APARTAMENTO"):
                add(r.get(key))
    def has(self): self._build(); return bool(self.map)

CACHE = TokenCache(DB_FILE)

# ---------- search ----------
def search_prefix(pref, limit=12):
    if not CACHE.has(): return []
    p = str(pref).strip(); pn = _norm(p)
    if not p or not pn: return []
    res=[]; seen=set()
    for r in load_db():
        nome = full_name(r); resumo = details_only(r)
        candidates = [nome, resumo] + [r.get(k) or "" for k in ("NOME","SOBRENOME","MODELO","COR","STATUS","PLACA","BLOCO","APARTAMENTO")]
        matched=False
        is_multi = bool(re.search(r"\s+", p))
        if is_multi:
            for txt in candidates[:2]:
                if _norm(txt).startswith(pn) and nome not in seen:
                    res.append((nome,r)); seen.add(nome); matched=True; break
            if matched and len(res)>=limit: break
            if matched: continue
        for txt in candidates:
            for t in tokens(txt):
                if _norm(t).startswith(pn) and nome not in seen:
                    res.append((nome,r)); seen.add(nome); matched=True; break
            if matched: break
        if not matched:
            for txt in candidates:
                if _norm(txt).startswith(pn) and nome not in seen:
                    res.append((nome,r)); seen.add(nome); break
        if len(res)>=limit: break
    return res[:limit]

def search_fuzzy(pref, max_results=8):
    if not CACHE.has(): return []
    if not _norm(pref): return []
    db = load_db()
    if not db: return []
    reps=[]; rep_map={}
    for r in db:
        rep = full_summary(r)
        if rep not in rep_map:
            rep_map[rep] = r; reps.append(rep)
    try:
        matches = rf_process.extract(pref, reps, scorer=rf_fuzz.WRatio, limit=max_results)
    except Exception:
        return []
    results=[]; seen=set()
    for item in matches:
        if len(item) < 2: continue
        rep_text = item[0]; rec = rep_map.get(rep_text)
        if rec:
            nome = full_name(rec)
            if nome not in seen:
                results.append((nome,rec)); seen.add(nome)
        if len(results) >= max_results: break
    return results

# ---------- parsing / fingerprint ----------
def parse_input_to_fields(text: str) -> dict:
    # kept for backward compatibility but we prefer preprocessor.extrair_tudo_consumo when available
    out = {"NOME":"","SOBRENOME":"","BLOCO":"","APARTAMENTO":"","PLACA":"","MODELO":"","COR":"","STATUS":""}
    if not text: return out
    toks = tokens(text); toks_up = [t.upper() for t in toks]
    bloco=""; apt=""; placa=""; status=""
    for i,t in enumerate(toks_up):
        m = re.match(r"^BL(\d+)$", t)
        if m: bloco=m.group(1); break
        if t=="BLOCO" and i+1<len(toks_up) and toks_up[i+1].isdigit(): bloco=toks_up[i+1]; break
    for i,t in enumerate(toks_up):
        m = re.match(r"^AP(\d+)$", t)
        if m: apt=m.group(1); break
        if t in ("AP","APT","APARTAMENTO") and i+1<len(toks_up) and toks_up[i+1].isdigit(): apt=toks_up[i+1]; break
    for t in toks_up[::-1]:
        if re.match(r"^[A-Z0-9]{5,8}$", t) and re.search(r"\d", t): placa=t; break
        if re.match(r"^[A-Z]{3}\d{4}$", t): placa=t; break
    for t in toks_up:
        if t in ("MORADOR","MORADORES"): status="MORADOR"; break
        if t in ("VISITANTE","VISITA","VISIT"): status="VISITANTE"; break
        if t in ("PRESTADOR","PRESTADORES","SERVICO","SERVI\u00c7O","TECNICO"): status="PRESTADOR"; break
    out.update({"BLOCO":bloco,"APARTAMENTO":apt,"PLACA":placa,"STATUS":status})
    stop_tokens = set()
    if bloco: stop_tokens.add("BL"+bloco)
    stop_tokens.update(["BLOCO","AP","APT","APARTAMENTO","PLACA","VISITANTE","VISITA","MORADOR","PRESTADOR","SERVICO","SERVI\u00c7O","DESCONHECIDO"])
    name_parts=[]
    for t in toks_up:
        if t in stop_tokens or re.match(r"^BL\d+$", t) or re.match(r"^AP\d+$", t) or re.match(r"^[A-Z]{3}\d{1,4}$", t):
            break
        name_parts.append(t)
    if name_parts:
        if len(name_parts)==1:
            out["NOME"]=name_parts[0].title(); out["SOBRENOME"]=""
        else:
            out["NOME"]=name_parts[0].title(); out["SOBRENOME"]=" ".join([p.title() for p in name_parts[1:]])
    try: idx_pl = toks_up.index(placa) if placa else len(toks_up)
    except: idx_pl = len(toks_up)
    last_name_idx = 0
    if name_parts:
        for i in range(len(toks_up)):
            if toks_up[i] == name_parts[-1]: last_name_idx = i
    middle = toks_up[last_name_idx+1:idx_pl]
    modelo = cor = ""
    if middle:
        filtered = [m for m in middle if not re.match(r"^BL\d+$", m) and not re.match(r"^AP\d+$", m) and m not in ("BLOCO","BLOCO:","AP","APTO","APARTAMENTO","PLACA","PLACA:")]
        if filtered:
            modelo = filtered[0].title()
            if len(filtered) > 1: cor = filtered[1].title()
    out["MODELO"]=modelo; out["COR"]=cor
    return out

def identity_fp_from_parsed(parsed: dict) -> str:
    nome = clean_whitespace(((parsed.get("NOME","") or "") + " " + (parsed.get("SOBRENOME","") or "")).strip()).upper()
    bloco = str(parsed.get("BLOCO","") or "").strip().upper()
    apt = str(parsed.get("APARTAMENTO","") or "").strip().upper()
    return f"{nome}|{bloco}|{apt}"

def compute_fp_from_record(rec: dict) -> str:
    nome = clean_whitespace(((rec.get("NOME","") or "") + " " + (rec.get("SOBRENOME","") or "")).strip()).upper()
    bloco = str(rec.get("BLOCO","") or "").strip().upper()
    apt = str(rec.get("APARTAMENTO","") or "").strip().upper()
    placa = str(rec.get("PLACA","") or "").strip().upper()
    return f"{nome}|{bloco}|{apt}|{placa}"

def _identity_key(rec: dict) -> str:
    nome = clean_whitespace(((rec.get("NOME","") or "") + " " + (rec.get("SOBRENOME","") or "")).strip()).upper()
    bloco = str(rec.get("BLOCO","") or "").strip().upper()
    apt = str(rec.get("APARTAMENTO","") or "").strip().upper()
    return f"{nome}|{bloco}|{apt}"

# ---------- file lock ----------
def _acquire_db_lock(timeout=5.0, poll=0.05):
    start = time.time()
    while True:
        try:
            fd = os.open(_DB_LOCKFILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try: os.write(fd, f"{os.getpid()} {time.time()}".encode("utf-8"))
            except Exception:
                pass
            try: os.close(fd)
            except Exception:
                pass
            return True
        except FileExistsError:
            if (time.time() - start) >= timeout:
                try:
                    m = os.path.getmtime(_DB_LOCKFILE)
                    if time.time() - m > (timeout * 2):
                        try: os.remove(_DB_LOCKFILE)
                        except Exception:
                            pass
                except Exception:
                    pass
                return False
            time.sleep(poll)
        except Exception:
            return False

def _release_db_lock():
    try:
        if os.path.exists(_DB_LOCKFILE): os.remove(_DB_LOCKFILE)
    except Exception:
        pass

# ---------- ensure DATA_HORA ----------
def _ensure_datetime_on_records(regs):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    for r in regs:
        dh = r.get("DATA_HORA", None) or r.get("data_hora", None)
        if not dh or parse_datetime(dh) is None:
            r["DATA_HORA"] = now
            if "data_hora" in r:
                try: r.pop("data_hora")
                except Exception:
                    pass

# ---------- build record (mantido) ----------
def build_db_record_from_parsed(parsed: dict, raw_text: str = "") -> dict:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    def u(x): return x.upper() if isinstance(x, str) and x else ""
    rec = {
        "NOME": u(parsed.get("NOME","")),
        "SOBRENOME": u(parsed.get("SOBRENOME","")),
        "BLOCO": (parsed.get("BLOCO","") or "").strip(),
        "APARTAMENTO": (parsed.get("APARTAMENTO","") or "").strip(),
        "PLACA": u(parsed.get("PLACA","")),
        "MODELO": u(parsed.get("MODELO","")),
        "COR": u(parsed.get("COR","")),
        "STATUS": u(parsed.get("STATUS","")),
        "DATA_HORA": now
    }
    # não gravamos 'texto' no DB final (evita poluir dadosend.json)
    for k in list(rec.keys()):
        if rec[k] == "" or rec[k] is None:
            if k not in ("DATA_HORA",): rec.pop(k, None)
    return rec

def _normalize_field_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().upper()
    return str(value).strip().upper()

def _field_missing(value) -> bool:
    v = _normalize_field_value(value)
    return v in ("", "-")

def _has_vehicle_info(fields: dict) -> bool:
    return any(not _field_missing(fields.get(k)) for k in ("PLACA","MODELO","COR"))

def _compute_access_flags(fields: dict) -> dict:
    flags = {}
    if not _has_vehicle_info(fields):
        flags["ENTROU A PÉ"] = "SIM"
    status = _normalize_field_value(fields.get("STATUS"))
    if status == "MORADOR" and _has_vehicle_info(fields):
        flags["MORADOR SEM TAG"] = "SIM"
    return flags

def _missing_fields_from_record(fields: dict) -> List[str]:
    labels = ["NOME","SOBRENOME","PLACA","MODELO","COR","STATUS"]
    return [label for label in labels if _field_missing(fields.get(label))]

def _identity_from_record(rec: dict) -> str:
    def _v(k):
        return (rec.get(k, "") or "").strip().upper()
    nome = _v("NOME")
    sobrenome = _v("SOBRENOME")
    bloco = _v("BLOCO")
    ap = _v("APARTAMENTO")
    return f"{nome}|{sobrenome}|{bloco}|{ap}"

def _get_last_record_identity(dadosend_path: str) -> str:
    try:
        data = _read_json(dadosend_path)
    except Exception:
        return ""
    if isinstance(data, dict) and "registros" in data:
        regs = data.get("registros") or []
    elif isinstance(data, list):
        regs = data
    else:
        regs = []
    if not regs:
        return ""
    try:
        regs_with_id = [r for r in regs if isinstance(r.get("ID"), int)]
        if regs_with_id:
            last = max(regs_with_id, key=lambda r: int(r.get("ID") or 0))
            return _identity_from_record(last)
    except Exception:
        pass
    def _dt_key(rec):
        s = rec.get("DATA_HORA") or rec.get("data_hora") or ""
        return parse_datetime(s)
    try:
        regs_with_dt = [(r, _dt_key(r)) for r in regs]
        regs_with_dt = [t for t in regs_with_dt if t[1] is not None]
        if regs_with_dt:
            last = max(regs_with_dt, key=lambda t: t[1])[0]
            return _identity_from_record(last)
    except Exception:
        pass
    try:
        return _identity_from_record(regs[-1])
    except Exception:
        return ""

def _start_analises_watcher(poll_interval: float = 1.0):
    def _watch():
        import analises
        import avisos
        last_mtime_db = None
        last_mtime_encomendas = None
        while True:
            try:
                db_changed = False
                encomendas_changed = False

                if os.path.exists(DB_FILE):
                    mtime_db = os.path.getmtime(DB_FILE)
                    if last_mtime_db is None:
                        last_mtime_db = mtime_db
                    elif mtime_db != last_mtime_db:
                        last_mtime_db = mtime_db
                        db_changed = True

                if os.path.exists(ENCOMENDAS_DB_FILE):
                    mtime_encomendas = os.path.getmtime(ENCOMENDAS_DB_FILE)
                    if last_mtime_encomendas is None:
                        last_mtime_encomendas = mtime_encomendas
                    elif mtime_encomendas != last_mtime_encomendas:
                        last_mtime_encomendas = mtime_encomendas
                        encomendas_changed = True

                if db_changed:
                    ident = _get_last_record_identity(DB_FILE)
                    if ident:
                        try:
                            analises.build_analises_for_identity(ident, DB_FILE, ANALISES_FILE)
                        except Exception:
                            analises.build_analises(DB_FILE, ANALISES_FILE)
                        try:
                            avisos.build_avisos_for_identity(ident, ANALISES_FILE, AVISOS_FILE)
                        except Exception:
                            avisos.build_avisos(ANALISES_FILE, AVISOS_FILE)
                    else:
                        analises.build_analises(DB_FILE, ANALISES_FILE)
                        avisos.build_avisos(ANALISES_FILE, AVISOS_FILE)

                if encomendas_changed and not db_changed:
                    analises.build_analises(DB_FILE, ANALISES_FILE)
                    avisos.build_avisos(ANALISES_FILE, AVISOS_FILE)
            except Exception:
                pass
            time.sleep(poll_interval)
    threading.Thread(target=_watch, daemon=True).start()

# ---------- append (revisado) ----------
def _next_db_id(regs):
    max_id = 0
    for r in regs:
        try:
            v = int(r.get("ID") or r.get("id") or 0)
            if v > max_id: max_id = v
        except (TypeError, ValueError):
            pass
    return max_id + 1

def append_record_to_db(rec: dict):
    """
    Insere registro em dadosend.json.
    - Reusa o mesmo ID (campo ID) quando a mesma identidade (NOME|SOBRENOME|BLOCO|APARTAMENTO)
      já existe em registros anteriores.
    - Garante DATA_HORA e salva atômica.
    - Preserva campos extras como '_entrada_id' quando fornecidos.
    """
    if not isinstance(rec, dict):
        report_status("db_append", "ERROR", stage="input_validation", details={"reason": "record_not_dict"})
        return False
    if not rec.get("DATA_HORA"): rec["DATA_HORA"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    report_status("db_append", "STARTED", stage="prepare_record", details={"has_entrada_id": bool(rec.get("_entrada_id"))})
    got = _acquire_db_lock(timeout=3.0)
    if not got:
        try:
            return _append_record_to_db_nolock(rec)
        except:
            return False
    try:
        base = _read_json(DB_FILE)
        regs = [] if not base or not isinstance(base, dict) or "registros" not in base else (base.get("registros") or [])
        if not isinstance(regs, list): regs = list(regs)

        # procura identidade já existente para reaproveitar ID de pessoa
        new_idkey = _identity_key(rec)
        person_id = None
        for r in regs:
            if _identity_key(r) == new_idkey:
                try:
                    person_id = int(r.get("ID") or r.get("id"))
                    break
                except:
                    continue
        if person_id is None:
            person_id = _next_db_id(regs)

        # criar novo registro (histórico) e garantir campos
        rec_to_insert = dict(rec)
        # preserve any provided _entrada_id
        if not rec_to_insert.get("ID"):
            rec_to_insert["ID"] = person_id
        if not rec_to_insert.get("DATA_HORA") or parse_datetime(rec_to_insert.get("DATA_HORA") or "") is None:
            rec_to_insert["DATA_HORA"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # upper MODELO/COR/PLACA se informados
        if "MODELO" in rec and rec.get("MODELO"): rec_to_insert["MODELO"] = str(rec.get("MODELO")).upper()
        if "COR" in rec and rec.get("COR"): rec_to_insert["COR"] = str(rec.get("COR")).upper()
        if "PLACA" in rec and rec.get("PLACA"): rec_to_insert["PLACA"] = str(rec.get("PLACA")).upper()

        regs.append(rec_to_insert)

        _ensure_datetime_on_records(regs)
        sanitize_and_save_db(regs)
        report_status("db_append", "OK", stage="persisted", details={"id": rec_to_insert.get("ID"), "entrada_id": rec_to_insert.get("_entrada_id")})
        try: sync_suggestions(force=True)
        except Exception:
            pass
        return True
    except Exception as e:
        report_status("db_append", "ERROR", stage="exception", details={"error": str(e)})
        _log_ui("ERROR", "append_record_exception", "Erro append_record_to_db", error=str(e)); return False
    finally:
        _release_db_lock()

def _append_record_to_db_nolock(rec: dict):
    try:
        base = _read_json(DB_FILE)
        regs = [] if base is None or not isinstance(base, dict) else (base.get("registros") or [])
        if not isinstance(regs, list): regs = list(regs)
        id_fp = _identity_key(rec); person_id=None
        for r in regs:
            if _identity_key(r) == id_fp:
                try:
                    person_id = int(r.get("ID") or r.get("id"))
                    break
                except:
                    continue
        if person_id is None:
            person_id = _next_db_id(regs)
        rec_to_insert = dict(rec); rec_to_insert["ID"] = person_id
        if not rec_to_insert.get("DATA_HORA") or parse_datetime(rec_to_insert.get("DATA_HORA")) is None:
            rec_to_insert["DATA_HORA"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if "MODELO" in rec and rec.get("MODELO"): rec_to_insert["MODELO"] = str(rec.get("MODELO")).upper()
        if "COR" in rec and rec.get("COR"): rec_to_insert["COR"] = str(rec.get("COR")).upper()
        if "PLACA" in rec and rec.get("PLACA"): rec_to_insert["PLACA"] = str(rec.get("PLACA")).upper()
        regs.append(rec_to_insert)
        _ensure_datetime_on_records(regs); sanitize_and_save_db(regs)
        try: sync_suggestions(force=True)
        except Exception:
            pass
        return True
    except Exception as e:
        _log_ui("ERROR", "append_record_nolock_exception", "Erro _append_record_to_db_nolock", error=str(e)); return False

# ---------- util overlay: common prefix ----------
def token_common_prefix_len(a: str, b: str) -> int:
    if not a or not b: return 0
    i = 0
    la, lb = len(a), len(b)
    # compare case-insensitively
    while i < la and i < lb and a[i].lower() == b[i].lower():
        i += 1
    return i

# ------------------- validação final antes de gravar -------------------
def _tokenize_alpha(text: str):
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", str(text or ""))

def post_validate_and_clean_record(rec: dict, modelos_hint: Iterable[str]=None, cores_hint: Iterable[str]=None, fuzzy_threshold: int = 85):
    """
    Limpa 'NOME' e 'SOBRENOME' removendo tokens que sejam:
      - modelos (exatos ou fuzzy similares),
      - cores conhecidas,
      - placas, blocos, status.
    Altera o dicionário 'rec' in-place e retorna ele.
    """
    if not isinstance(rec, dict):
        return rec

    # coleta pistas
    modelos_hint = list(modelos_hint or [])
    cores_hint = list(cores_hint or [])
    try:
        if rec.get("MODELO") and rec.get("MODELO") not in ("", "-"):
            modelos_hint.append(rec.get("MODELO"))
    except Exception:
        pass

    def _norm_token_local(t):
        if not t: return ""
        s = unicodedata.normalize("NFKD", str(t))
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return re.sub(r"[^A-Za-z0-9]+", "", s).lower().strip()

    model_set = set(_norm_token_local(x) for x in modelos_hint if x)
    try:
        from preprocessor import VEICULOS_MAP as _VMAP
        for k, ab in _VMAP.items():
            model_set.add(_norm_token_local(k))
            if ab:
                for a in ab:
                    model_set.add(_norm_token_local(a))
    except Exception:
        pass

    color_set = set(_norm_token_local(x) for x in cores_hint if x)
    try:
        from preprocessor import _CORES as _PCORES
        for c in _PCORES:
            color_set.add(_norm_token_local(c))
    except Exception:
        pass

    def _is_model_like(tok):
        if not tok: return False
        k = _norm_token_local(tok)
        if k in model_set:
            return True
        try:
            from rapidfuzz import fuzz as _rf_fuzz
            for m in model_set:
                if not m: continue
                if _rf_fuzz.WRatio(k, m) >= fuzzy_threshold:
                    return True
        except Exception:
            for m in model_set:
                if not m: continue
                if k == m or (abs(len(k)-len(m))<=1 and (k.startswith(m) or m.startswith(k))):
                    return True
        return False

    def _is_color_like(tok):
        if not tok: return False
        k = _norm_token_local(tok)
        if k in color_set:
            return True
        return False

    nome = (rec.get("NOME") or "").strip()
    sobrenome = (rec.get("SOBRENOME") or "").strip()
    combined = []
    if nome:
        combined += _tokenize_alpha(nome)
    if sobrenome:
        combined += _tokenize_alpha(sobrenome)

    cleaned = []
    for tok in combined:
        if not tok: continue
        tu = tok.strip()
        if re.match(r"^[A-Z]{3}\d{4}$", tu, flags=re.IGNORECASE) or (re.match(r"^[A-Z0-9]{5,8}$", tu, flags=re.IGNORECASE) and re.search(r"\d", tu)):
            continue
        if re.match(r"^BL\d+$", tu.upper()) or re.match(r"^AP\d+$", tu.upper()):
            continue
        if tu.upper() in ("MORADOR","VISITANTE","PRESTADOR","DESCONHECIDO"):
            continue
        if _is_color_like(tu) or _is_model_like(tu):
            continue
        if tu.upper() in ("DO","DA","DE","DOS","DAS","E","O","A","SR","SRA"):
            continue
        corrected = corrigir_token_nome(tu) if corrigir_token_nome else tu
        cleaned.append(corrected.title())

    if cleaned:
        rec["NOME"] = cleaned[0].upper()
        rec["SOBRENOME"] = " ".join(cleaned[1:]).upper() if len(cleaned) > 1 else "-"
    else:
        if not rec.get("NOME") or rec.get("NOME") in ("", "-"):
            rec["NOME"] = "-"
        if not rec.get("SOBRENOME") or rec.get("SOBRENOME") in ("", "-"):
            rec["SOBRENOME"] = "-"

    for k in ("MODELO","PLACA","COR","STATUS","BLOCO","APARTAMENTO"):
        v = rec.get(k)
        if not v or (isinstance(v, str) and v.strip() == ""):
            rec[k] = "-"
        elif isinstance(v, str):
            rec[k] = v.upper()

    return rec

# ---------- UI: SuggestEntry (completo) ----------
class SuggestEntry(tk.Frame):
    MAX_VISIBLE = 8
    def __init__(self, master):
        super().__init__(master)
        self.entry_var = tk.StringVar(); self.entry = tk.Entry(self, textvariable=self.entry_var, width=80, font=("Segoe UI",11)); self.entry.pack(side=tk.TOP, fill=tk.X); self.entry.focus_set()
        self.font = tkfont.Font(font=self.entry["font"]); self._orig_entry_bg = self.entry.cget("bg")
        try: self._orig_entry_fg = self.entry.cget("fg")
        except: self._orig_entry_fg = "black"
        try: self._orig_insert_bg = self.entry.cget("insertbackground")
        except: self._orig_insert_bg = self._orig_entry_fg

        # overlay (completar token)
        self.overlay = tk.Label(self, text="", anchor="w", font=self.entry["font"], fg="gray65", bg=self._orig_entry_bg, bd=0); self.overlay_visible=False
        # suggestion list
        self.frame = tk.Frame(self); self.sbar = tk.Scrollbar(self.frame, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(self.frame, columns=("nome","detalhes"), show="headings"); self.tree.heading("nome", text="Nome"); self.tree.heading("detalhes", text="Detalhes")
        self.tree.column("nome", width=220, anchor="w"); self.tree.column("detalhes", width=620, anchor="w")
        self.tree.configure(yscrollcommand=self.sbar.set); self.sbar.config(command=self.tree.yview); self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.sbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.ia_mode=False; self.ia_waiting_for_query=False; self.list_visible=False; self.suggestions=[]; self.correction=""; self.curr=None
        self.steps=[]; self.step_idx=0; self._has_user_navigated=False; self._just_accepted=False
        self._stop_monitor=False; self._alert_cycle_idx=0; self._alert_cycle_ts=0.0
        self._db_panel_windows = {}

        self.entry.bind("<KeyRelease>", self.on_key)
        self.entry.bind("<Tab>", self.on_tab, add="+")
        self.entry.bind("<Down>", self.on_down); self.entry.bind("<Up>", self.on_up); self.entry.bind("<Return>", self.on_return); self.entry.bind("<Escape>", self.on_escape)
        self.entry.bind("<Control-space>", lambda e: (self.show_db(), "break"))

        self.tree.bind("<Double-1>", self.on_tree_double); self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Motion>", self.on_tree_motion); self.tree.bind("<Return>", self.on_tree_return)

        # Não há thread de avisos; mantemos apenas sugestões/sync se necessário.
        try:
            threading.Thread(target=lambda: sync_suggestions(force=False), daemon=True).start()
        except Exception:
            pass

    # overlay helpers
    def _typed_x(self):
        t = self.entry_var.get().rstrip(); return t, self.font.measure(t)

    def _show_overlay_for_last_token(self, suggestion_text: str, last_token: str):
        cut_chars = token_common_prefix_len(last_token, suggestion_text)
        suffix = suggestion_text[cut_chars:] if cut_chars < len(suggestion_text) else ""
        if not suffix: return self._hide_overlay()
        typed, x = self._typed_x()
        try:
            if self.entry.index("insert") != len(typed): return self._hide_overlay()
        except Exception:
            pass
        self.overlay.config(text=suffix)
        if not self.overlay_visible:
            self.overlay.place(in_=self.entry, x=x+4, y=1); self.overlay_visible = True
        else:
            self.overlay.place_configure(x=x+4, y=1)

    def _hide_overlay(self):
        if getattr(self, "overlay_visible", False):
            try: self.overlay.place_forget()
            except Exception:
                pass
            self.overlay_visible=False
        self.overlay.config(text="")

    # key handlers
    def on_key(self, event):
        k = event.keysym
        if self.ia_waiting_for_query and k not in ("Up","Down","Left","Right","Return","Tab","Escape"):
            try: self.entry_var.set(""); self.entry.icursor(0)
            except Exception:
                pass
            self.ia_waiting_for_query=False
        if self.ia_mode:
            if k not in ("Up","Down"): self._just_accepted=False
            return
        if k in ("Up","Down","Left","Right","Return","Tab","Escape"):
            if k not in ("Up","Down"): self._just_accepted=False
            return
        self._has_user_navigated=False; self._just_accepted=False
        for sel in list(self.tree.selection()):
            try: self.tree.selection_remove(sel)
            except Exception:
                pass
        typed = self.entry_var.get()
        if not typed.strip(): self.hide_list(); self._hide_overlay(); return
        tok_list = tokens(typed); last_token = tok_list[-1] if tok_list else typed.strip()
        suggestions = spelling_suggestions_for_token(last_token, max_results=4)
        if suggestions:
            best = suggestions[0]; self._show_overlay_for_last_token(best, last_token); self.correction = best
        else:
            self.correction = ""; self._hide_overlay()
        try: self.show_db()
        except Exception:
            pass

    def on_tab(self, event):
        if self.ia_mode: return "break"
        if not self.entry_var.get().strip(): return "break"
        # Completion from overlay / spelling suggestion
        if self.correction:
            typed = self.entry_var.get()
            tok_list = tokens(typed)
            last_token = tok_list[-1] if tok_list else typed
            cut = token_common_prefix_len(last_token, self.correction)
            suffix = self.correction[cut:] if cut < len(self.correction) else ""
            if suffix:
                if typed.endswith(last_token):
                    new_text = typed + suffix
                elif typed and typed[-1].isspace():
                    new_text = typed + suffix
                else:
                    new_text = typed + " " + suffix
                self.entry_var.set(new_text)
                try:
                    self.entry.icursor(len(new_text))
                    self.entry.selection_clear()
                    self.entry.focus_set()
                    try: self.entry.xview_moveto(1.0)
                    except Exception:
                        pass
                except Exception:
                    pass
            self._hide_overlay(); self.correction="";
            try: self.show_db()
            except Exception:
                pass
            self._just_accepted=True
            return "break"
        # Completion from the list
        if self.list_visible:
            sel = self.tree.selection()
            if sel:
                try: idx = int(sel[0])
                except: idx = 0
                self._accept_into_entry(idx, hide=False)
                if self.step_idx < len(self.steps):
                    token = self.steps[self.step_idx]; self._apply_step_token(token); self.step_idx += 1
                try: self.show_db()
                except Exception:
                    pass
                self._just_accepted=True
                return "break"
            return "break"
        return None if self.entry_var.get().strip() else "break"

    def on_down(self, event):
        if self.list_visible:
            ch = self.tree.get_children(); size = len(ch)
            if size==0: return "break"
            sel = self.tree.selection()
            cur = int(sel[0]) if sel else -1
            idx = (cur+1)%size
            iid = ch[idx]; self.tree.selection_set(iid); self.tree.focus(iid); self.tree.see(iid); self._has_user_navigated=True
            return "break"
        return None

    def on_up(self, event):
        if self.list_visible:
            ch = self.tree.get_children(); size = len(ch)
            if size==0: return "break"
            sel = self.tree.selection()
            cur = int(sel[0]) if sel else 0
            idx = (cur-1) % size if sel else len(ch)-1
            iid = ch[idx]; self.tree.selection_set(iid); self.tree.focus(iid); self.tree.see(iid); self._has_user_navigated=True
            return "break"
        return None

    def on_return(self, event):
        text_raw = (self.entry_var.get() or ""); text = text_raw.strip()
        if not self.ia_mode:
            if re.fullmatch(r"\s*(ia|ai)([,.\s]*)?$", text, flags=re.IGNORECASE) or re.match(r"^\s*(ia|ai)\b", text, flags=re.IGNORECASE):
                self.ia_mode=True; self.ia_waiting_for_query=True
                try: self._enter_ia_mode()
                except Exception:
                    pass
                self._hide_overlay(); self.hide_list(); return "break"
        if self.ia_mode:
            if self.ia_waiting_for_query: return "break"
            command = text.lower()
            if command in DB_PANEL_COMMANDS:
                try:
                    self.entry_var.set(""); self.entry.icursor(0)
                except Exception:
                    pass
                self._open_db_panel(DB_PANEL_COMMANDS[command], command)
                return "break"
            if text.lower() in ("sair","exit","fim","close","voltar"):
                try: self._exit_ia_mode()
                except Exception:
                    pass
                return "break"
            query_text = text; self.entry_var.set(""); self.entry.icursor(0)
            threading.Thread(target=self._send_query_to_ia_thread, args=(query_text,), daemon=True).start()
            return "break"
        if self.list_visible:
            sel = self.tree.selection()
            if sel:
                try: idx = int(sel[0])
                except: idx = 0
                self._accept_into_entry(idx, hide=True, append_all=True)
                try: self.show_db()
                except Exception:
                    pass
                self._just_accepted=True
                return "break"
            else:
                try: save_text(entry_widget=self.entry)
                except Exception:
                    pass
                return "break"
        else:
            try: save_text(entry_widget=self.entry)
            except Exception:
                pass
            return "break"

    def on_tree_return(self, event): return self.on_return(event)

    def _send_query_to_ia_thread(self, query_text: str):
        if HAS_CHAT_MODULE and hasattr(chat_module, "respond_chat"):
            try: resp = chat_module.respond_chat(query_text)
            except Exception as e: resp = f"Erro ao consultar IA: {e}"
        elif HAS_IA_MODULE and hasattr(ia_module, "respond_query"):
            try: resp = ia_module.respond_query(query_text)
            except Exception as e: resp = f"Erro ao consultar IA: {e}"
        else:
            try:
                registros = load_db()
                tokens_q = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", query_text)]
                found=[]
                for r in registros:
                    text_fields = " ".join([str(r.get(k,"")) for k in ("NOME","SOBRENOME","BLOCO","APARTAMENTO","PLACA","STATUS","DATA_HORA")]).lower()
                    if all(tok in text_fields for tok in tokens_q): found.append(r)
                if not found: resp = "Nenhum resultado encontrado (fallback local)."
                else:
                    lines = [f"{rec.get('DATA_HORA','-')} | {rec.get('NOME','-')} {rec.get('SOBRENOME','-')} | BLOCO {rec.get('BLOCO','-')} AP {rec.get('APARTAMENTO','-')} | PLACA {rec.get('PLACA','-')} | {rec.get('STATUS','-')}" for rec in found[:200]]
                    resp = f"Resultados ({len(found)}):\n" + "\n".join(lines)
            except Exception as e:
                resp = f"Erro no fallback local: {e}"
        try:
            root = self._root_for_ui()
            if root: root.after(0, lambda r=resp: self._show_ia_response_window(r))
            else: print(resp)
        except Exception:
            print(resp)

    def _show_ia_response_window(self, text: str):
        try:
            root = self._root_for_ui()
            if root is None: print(text); return
            top = tk.Toplevel(root); top.title("Resposta IA"); top.geometry("700x400")
            st = scrolledtext.ScrolledText(top, wrap=tk.WORD); st.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            st.insert(tk.END, text); st.configure(state="disabled")
            tk.Button(top, text="Fechar", command=top.destroy).pack(pady=(0,8))
        except Exception as e:
            print("Erro ao abrir janela de resposta IA:", e); print(text)

    def _root_for_ui(self):
        try:
            w = self
            while w.master is not None: w = w.master
            return w
        except: return None

    def _open_db_panel(self, db_path: str, command: str):
        root = self._root_for_ui()
        if root is None:
            print("Janela principal não encontrada para abrir painel DB.")
            return

        existing = self._db_panel_windows.get(db_path)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        def read_db_contents():
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    raw = f.read()
            except Exception:
                raw = ""
            try:
                parsed = json.loads(raw) if raw.strip() else {"registros": []}
            except Exception:
                parsed = {"registros": []}
            if isinstance(parsed, list):
                parsed = {"registros": parsed}
            if not isinstance(parsed, dict):
                parsed = {"registros": []}
            return parsed

        original_data = read_db_contents()
        structure_keys = set(original_data.keys())
        original_text = json.dumps(original_data, ensure_ascii=False, indent=2)

        top = tk.Toplevel(root)
        top.title(f"Painel DB {command}")
        top.geometry("900x600")
        self._db_panel_windows[db_path] = top

        def on_close():
            try:
                if db_path in self._db_panel_windows:
                    self._db_panel_windows.pop(db_path, None)
            except Exception:
                pass
            try:
                top.destroy()
            except Exception:
                pass

        top.protocol("WM_DELETE_WINDOW", on_close)

        top_banner = tk.Label(top, text="", bg="#4CAF50", fg="black")
        bottom_banner = tk.Label(top, text="", bg="#F44336", fg="black")

        def hide_banners():
            try:
                if top_banner.winfo_ismapped():
                    top_banner.pack_forget()
            except Exception:
                pass
            try:
                if bottom_banner.winfo_ismapped():
                    bottom_banner.pack_forget()
            except Exception:
                pass

        def show_success(msg: str):
            hide_banners()
            try:
                top_banner.config(text=msg)
                top_banner.pack(fill=tk.X, side=tk.TOP)
                top.after(4000, hide_banners)
            except Exception:
                pass

        def show_failure(msg: str):
            hide_banners()
            try:
                bottom_banner.config(text=msg)
                bottom_banner.pack(fill=tk.X, side=tk.BOTTOM)
                top.after(4000, hide_banners)
            except Exception:
                pass

        text_area = scrolledtext.ScrolledText(
            top,
            wrap=tk.WORD,
            bg="black",
            fg="white",
            insertbackground="white",
        )
        text_area.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        text_area.insert(tk.END, original_text)

        def validate_structure(data: dict) -> bool:
            if not isinstance(data, dict):
                return False
            if set(data.keys()) != structure_keys:
                return False
            if "registros" not in data or not isinstance(data.get("registros"), list):
                return False
            return True

        def parse_current_text():
            content = text_area.get("1.0", tk.END).strip()
            if not content:
                return None
            try:
                parsed = json.loads(content)
            except Exception:
                return None
            if isinstance(parsed, list):
                return None
            return parsed

        def save_changes():
            nonlocal original_data, original_text, structure_keys
            parsed = parse_current_text()
            if parsed is None or not validate_structure(parsed):
                show_failure("Falha ao salvar alteracoes!")
                return
            try:
                atomic_save(db_path, parsed)
            except Exception:
                show_failure("Falha ao salvar alteracoes!")
                return
            original_data = parsed
            structure_keys = set(parsed.keys())
            original_text = json.dumps(parsed, ensure_ascii=False, indent=2)
            show_success("Alteracoes salvas com sucesso!")

        def reset_changes():
            current = text_area.get("1.0", tk.END).strip()
            if current == original_text.strip():
                show_failure("Falha ao resertar: nao a dados a serem resertados!")
                return
            text_area.delete("1.0", tk.END)
            text_area.insert(tk.END, original_text)
            show_success("Dados resertados com sucesso!")

        def backup_changes():
            nonlocal original_data, original_text
            parsed = parse_current_text()
            if parsed is None or not validate_structure(parsed):
                show_failure("Backup falhou!")
                return
            registros = parsed.get("registros") or []
            if len(registros) == 0:
                show_failure("Backup falhou!")
                return
            new_data = {key: ( [] if key == "registros" else original_data.get(key)) for key in structure_keys}
            try:
                atomic_save(db_path, new_data)
            except Exception:
                show_failure("Backup falhou!")
                return
            original_data = new_data
            original_text = json.dumps(new_data, ensure_ascii=False, indent=2)
            text_area.delete("1.0", tk.END)
            text_area.insert(tk.END, original_text)
            show_success("Bakup efetuado!")

        btn_frame = tk.Frame(top)
        btn_frame.pack(fill=tk.X, pady=(0, 8))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=0)
        btn_frame.columnconfigure(2, weight=0)
        btn_frame.columnconfigure(3, weight=0)
        btn_frame.columnconfigure(4, weight=1)

        btn_save = tk.Button(btn_frame, text="Save", command=save_changes)
        btn_reset = tk.Button(btn_frame, text="Reset", command=reset_changes)
        btn_backup = tk.Button(btn_frame, text="Backup", command=backup_changes)

        btn_save.grid(row=0, column=1, padx=6)
        btn_reset.grid(row=0, column=2, padx=6)
        btn_backup.grid(row=0, column=3, padx=6)

    def on_escape(self, event):
        if self.ia_mode:
            try: self._exit_ia_mode()
            except: pass; return
        self.hide_list(); self._hide_overlay(); self.correction=""; self._has_user_navigated=False; self._just_accepted=False

    def on_tree_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            try: self.tree.selection_set(row)
            except Exception:
                pass
            self._has_user_navigated=True
        return None

    def on_tree_double(self, event):
        row = self.tree.identify_row(event.y)
        if not row: return
        try: idx = int(row)
        except: idx = 0
        self._accept_into_entry(idx, hide=True, append_all=True)
        try: self.show_db()
        except Exception:
            pass
        self._just_accepted=True

    def on_tree_motion(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            try: self.tree.selection_set(row)
            except Exception:
                pass
            self.tree.focus(row); self._has_user_navigated=True

    def _accept_into_entry(self, idx, hide=False, append_all=False):
        if idx < 0 or idx >= len(self.suggestions): return
        disp, rec = self.suggestions[idx]; name_text = full_name(rec)
        self.entry_var.set(name_text)
        try: self.entry.icursor(len(name_text)); self.entry.select_clear(); self.entry.focus_set()
        except Exception:
            pass
        steps=[]
        for k in ("BLOCO","APARTAMENTO","PLACA","MODELO","COR","STATUS"):
            v = clean_whitespace(rec.get(k) or "")
            if v and v != "-":
                steps.append("BLOCO " + v if k=="BLOCO" else ("AP " + v if k=="APARTAMENTO" else ("PLACA " + v if k=="PLACA" else v)))
        self.curr=rec; self.steps=steps; self.step_idx=0
        if append_all and steps:
            for token in steps: self._apply_step_token(token)
            self._hide_overlay()
        elif steps:
            t, x = self._typed_x()
            try:
                self.overlay.place_configure(x=x+4, y=1); self.overlay.config(text=steps[0]); self.overlay_visible=True
            except Exception:
                pass
        else:
            self._hide_overlay()
        if hide: self.hide_list()
        try: self.show_db()
        except Exception:
            pass

    def _apply_step_token(self, token):
        current = self.entry_var.get().strip()
        if current.upper().endswith(token.upper()): return
        new_text = f"{current} {token}".strip(); self.entry_var.set(new_text)
        try: self.entry.icursor(len(new_text)); self.entry.select_clear(); self.entry.focus_set()
        except Exception:
            pass
        if self.step_idx + 1 < len(self.steps):
            next_hint = self.steps[self.step_idx + 1]; x = self.font.measure(new_text)
            try: self.overlay.place_configure(x=x+4, y=1); self.overlay.config(text=next_hint); self.overlay_visible=True
            except Exception:
                pass
        else: self._hide_overlay()
        try: self.show_db()
        except Exception:
            pass

    def show_list(self, matches):
        if not self.entry_var.get().strip(): self.hide_list(); self._hide_overlay(); return
        for it in self.tree.get_children(): self.tree.delete(it)
        rows=[]
        max_nome_w = 0; max_det_w = 0
        for i,(disp,rec) in enumerate(matches):
            nome = clean_whitespace(full_name(rec)); det = clean_whitespace(details_only(rec));
            rows.append((nome,det,rec))
            try:
                w_nome = self.font.measure(nome)
                w_det = self.font.measure(det)
            except:
                w_nome = len(nome) * 7
                w_det = len(det) * 7
            if w_nome > max_nome_w: max_nome_w = w_nome
            if w_det > max_det_w: max_det_w = w_det

        pad_nome = 16
        pad_det = 16
        min_nome = 80
        min_det = 120
        col_nome_w = max(min_nome, max_nome_w + pad_nome)
        col_det_w = max(min_det, max_det_w + pad_det)

        try:
            parent_w = self.winfo_toplevel().winfo_width()
            if parent_w > 100:
                total_req = col_nome_w + col_det_w
                if total_req > (parent_w - 40):
                    scale = (parent_w - 40) / total_req
                    col_nome_w = int(col_nome_w * scale)
                    col_det_w = int(col_det_w * scale)
        except Exception:
            pass

        for i,(nome,det,rec) in enumerate(rows):
            self.tree.insert("", "end", str(i), values=(nome, det))

        try:
            self.tree.column("nome", width=col_nome_w, minwidth=40)
            self.tree.column("detalhes", width=col_det_w, minwidth=60)
        except Exception:
            pass

        visible = min(len(rows), self.MAX_VISIBLE) if rows else 0
        if visible <= 0: self.hide_list(); return
        try: self.tree.configure(height=visible)
        except Exception:
            pass
        for sel in list(self.tree.selection()):
            try: self.tree.selection_remove(sel)
            except Exception:
                pass
        if not self.list_visible:
            self.frame.pack(side=tk.TOP, fill=tk.X, pady=(4,0)); self.list_visible=True
        self._has_user_navigated=False; self._just_accepted=False

    def hide_list(self):
        if self.list_visible:
            self.frame.pack_forget(); self.list_visible=False
        for it in self.tree.get_children(): self.tree.delete(it)
        self._has_user_navigated=False; self._just_accepted=False

    def show_db(self):
        if self.ia_mode: self.hide_list(); self._hide_overlay(); return
        typed = self.entry_var.get().strip()
        if not typed: self.hide_list(); return
        matches = search_prefix(typed)
        if not matches: matches = search_fuzzy(typed)
        if matches: self.suggestions = matches; self.show_list(matches)
        else: self.hide_list()

    def _enter_ia_mode(self):
        try:
            self.ia_mode=True; self.ia_waiting_for_query=False; self._hide_overlay(); self.hide_list()
            if HAS_CHAT_MODULE and hasattr(chat_module, "activate_chat_mode"):
                try: chat_module.activate_chat_mode()
                except Exception as e: print("Falha ao ativar modo chat:", e)
            elif HAS_IA_MODULE and hasattr(ia_module, "activate_agent_prompt"):
                try: ia_module.activate_agent_prompt()
                except Exception as e: print("Falha ao ativar prompt do agente:", e)
            try: self.entry_var.set(""); self.entry.icursor(0)
            except Exception:
                pass
            try: self.entry.configure(bg="black", fg="white", insertbackground="white")
            except Exception:
                pass
            try: self.entry.focus_set()
            except Exception:
                pass
        except Exception:
            pass

    def _exit_ia_mode(self):
        try:
            self.ia_mode=False; self.ia_waiting_for_query=False
            if HAS_CHAT_MODULE and hasattr(chat_module, "deactivate_chat_mode"):
                try: chat_module.deactivate_chat_mode()
                except Exception as e: print("Falha ao desativar modo chat:", e)
            elif HAS_IA_MODULE and hasattr(ia_module, "deactivate_agent_prompt"):
                try: ia_module.deactivate_agent_prompt()
                except Exception as e: print("Falha ao desativar prompt do agente:", e)
            try: self.entry.configure(bg=self._orig_entry_bg, fg=self._orig_entry_fg, insertbackground=self._orig_insert_bg)
            except Exception:
                pass
            try: self.entry_var.set(""); self.entry.icursor(0); self.entry.focus_set()
            except Exception:
                pass
        except Exception:
            pass

# =========================
# save_text (corrigido para usar preprocessor.extrair_tudo_consumo quando disponível)
# =========================

def _compute_next_in_id(regs):
    max_id = 0
    for r in regs:
        try:
            v = int(r.get("id") or r.get("ID") or 0)
            if v > max_id: max_id = v
        except (TypeError, ValueError):
            pass
    return max_id + 1

def save_text(entry_widget=None, btn=None):
    if entry_widget is None:
        return
    txt = entry_widget.get().strip()
    if not txt:
        return
    report_status("user_input", "STARTED", stage="save_text", details={"text_len": len(txt)})
    parsed = None
    if extrair_tudo_consumo:
        try:
            parsed = extrair_tudo_consumo(txt)
        except Exception as e:
            _log_ui("WARNING", "preprocess_failed", "Falha no preprocess em save_text", error=str(e))
            parsed = None

    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    if log_audit_event:
        log_audit_event("texto_recebido", "entrada", txt)

    if decidir_destino:
        decision = decidir_destino(txt, parsed, classificar_fn=classificar_destino_texto, is_encomenda_fn=_is_encomenda_text)
    else:
        decision = classificar_destino_texto(txt, parsed) if classificar_destino_texto else {
            "destino": "dados", "motivo": "fallback", "score": 0.0, "ambiguo": False, "confianca": 0.0, "versao_regras": "v1"
        }
        decision["destino_final"] = decision.get("destino")
    destino = decision.get("destino_final")
    report_status("user_input", "OK", stage="classification", details={"destino": destino, "score": decision.get("score"), "ambiguo": decision.get("ambiguo")})
    if log_audit_event:
        log_audit_event("texto_classificado", destino, txt, motivo=decision.get("motivo"), score=decision.get("score"), confianca=decision.get("confianca"), ambiguo=decision.get("ambiguo"))

    if destino == "orientacoes":
        _save_structured_text(ORIENTACOES_FILE, txt, now_str, "ORIENTACAO", decision_meta=decision)
        report_status("user_input", "OK", stage="saved_orientacao", details={"path": ORIENTACOES_FILE})
        try:
            entry_widget.delete(0, "end")
        except Exception as e:
            _log_ui("WARNING", "entry_clear_failed", "Falha ao limpar entrada", error=str(e))
        return
    if destino == "observacoes":
        _save_structured_text(OBSERVACOES_FILE, txt, now_str, "OBSERVACAO", decision_meta=decision)
        report_status("user_input", "OK", stage="saved_observacao", details={"path": OBSERVACOES_FILE})
        try:
            entry_widget.delete(0, "end")
        except Exception as e:
            _log_ui("WARNING", "entry_clear_failed", "Falha ao limpar entrada", error=str(e))
        return

    if destino == "encomendas" or _is_encomenda_text(txt, parsed):
        _save_encomenda_init(txt, now_str)
        report_status("user_input", "OK", stage="saved_encomenda_init", details={"path": ENCOMENDAS_IN_FILE})
        if log_audit_event:
            log_audit_event("texto_persistido", "ENCOMENDAS_INIT", txt, motivo=decision.get("motivo"), score=decision.get("score"))
        try:
            entry_widget.delete(0, "end")
        except Exception as e:
            _log_ui("WARNING", "entry_clear_failed", "Falha ao limpar entrada", error=str(e))
        if btn:
            try:
                btn.config(state="disabled")
                entry_widget.after(500, lambda: btn.config(state="normal"))
            except Exception as e:
                _log_ui("WARNING", "button_toggle_failed", "Falha ao atualizar estado do botão", error=str(e))
        if HAS_IA_MODULE and hasattr(ia_module, "processar"):
            try:
                if not (hasattr(ia_module, "is_chat_mode_active") and ia_module.is_chat_mode_active()):
                    threading.Thread(target=ia_module.processar, daemon=True).start()
                    report_status("ia_pipeline", "STARTED", stage="thread_started", details={"source": "save_text_encomenda"})
            except Exception as e:
                report_status("ia_pipeline", "ERROR", stage="thread_start_failed", details={"error": str(e), "source": "save_text_encomenda"})
                _log_ui("ERROR", "ia_thread_start_failed", "Falha ao iniciar processamento IA para encomendas", error=str(e))
        return

    is_orientacao = _contains_keywords(txt, _ORIENTACOES_KEYWORDS)
    is_observacao = _contains_keywords(txt, _OBSERVACOES_KEYWORDS)
    if is_orientacao and not is_observacao:
        _save_structured_text(ORIENTACOES_FILE, txt, now_str, "ORIENTACAO")
        try:
            entry_widget.delete(0, "end")
        except Exception as e:
            _log_ui("WARNING", "entry_clear_failed", "Falha ao limpar entrada", error=str(e))
        return
    if is_observacao and not is_orientacao:
        _save_structured_text(OBSERVACOES_FILE, txt, now_str, "OBSERVACAO")
        try:
            entry_widget.delete(0, "end")
        except Exception as e:
            _log_ui("WARNING", "entry_clear_failed", "Falha ao limpar entrada", error=str(e))
        return
    rec = None
    fields_for_flags = {}
    if parsed:
        if montar_registro_acesso:
            rec = montar_registro_acesso(parsed, corrigir_nome_fn=corrigir_token_nome, now_str=now_str)
        else:
            rec = {
                "NOME": "-",
                "SOBRENOME": "-",
                "BLOCO": str(parsed.get("BLOCO") or "").strip(),
                "APARTAMENTO": str(parsed.get("APARTAMENTO") or "").strip(),
                "PLACA": (parsed.get("PLACA") or "").upper() or "-",
                "STATUS": (parsed.get("STATUS") or "").upper() or "-",
                "DATA_HORA": now_str,
            }
        fields_for_flags = dict(rec)

        # última validação antes de persistir (defensiva)
        try:
            post_validate_and_clean_record(rec, modelos_hint=[rec.get("MODELO")] if rec.get("MODELO") and rec.get("MODELO") != "-" else [], cores_hint=[rec.get("COR")] if rec.get("COR") and rec.get("COR") != "-" else [])
        except Exception as e:
            _log_ui("WARNING", "optimistic_validation_failed", "Falha validação final otimista", error=str(e))
    else:
        try:
            parsed2 = parse_input_to_fields(txt)
        except Exception:
            parsed2 = {}
        if parsed2:
            fields_for_flags = {
                "NOME": (parsed2.get("NOME") or "").upper(),
                "SOBRENOME": (parsed2.get("SOBRENOME") or "").upper(),
                "BLOCO": (parsed2.get("BLOCO") or "").strip(),
                "APARTAMENTO": (parsed2.get("APARTAMENTO") or "").strip(),
                "PLACA": (parsed2.get("PLACA") or "").upper(),
                "MODELO": (parsed2.get("MODELO") or "").upper(),
                "COR": (parsed2.get("COR") or "").upper(),
                "STATUS": (parsed2.get("STATUS") or "").upper(),
            }

    access_flags = _compute_access_flags(fields_for_flags) if fields_for_flags else {}
    missing_fields = _missing_fields_from_record(fields_for_flags) if fields_for_flags else []

    try:
        existing = _read_json(IN_FILE)
        if isinstance(existing, dict) and "registros" in existing:
            regs = existing.get("registros") or []
        elif isinstance(existing, list):
            regs = existing
        else:
            regs = []
    except (OSError, json.JSONDecodeError, TypeError):
        regs = []

    # compute next id robustly
    nid = _compute_next_in_id(regs)

    if montar_entrada_bruta:
        new_rec = montar_entrada_bruta(nid, txt, now_str, access_flags)
    else:
        new_rec = {
            "id": nid,
            "texto": txt,
            "processado": False,
            "data_hora": now_str
        }
        if access_flags:
            new_rec.update(access_flags)
    regs.append(new_rec)

    try:
        atomic_save(IN_FILE, {"registros": regs})
        report_status("user_input", "OK", stage="saved_dadosinit", details={"path": IN_FILE, "entrada_id": nid})
    except Exception as e:
        report_status("user_input", "ERROR", stage="save_dadosinit_failed", details={"error": str(e), "path": IN_FILE})
        _log_ui("ERROR", "save_dadosinit_failed", "Erro save (IN_FILE)", error=str(e))
    try: entry_widget.delete(0, "end")
    except Exception:
        pass
    if btn:
        try: btn.config(state="disabled"); entry_widget.after(500, lambda: btn.config(state="normal"))
        except Exception:
            pass
    try: threading.Thread(target=sync_suggestions, kwargs={"force": True}, daemon=True).start()
    except Exception:
        pass

    if missing_fields and _warning_bar:
        try:
            msgs = [f"AVISO: SALVO SEM O DADO {field}!" for field in missing_fields]
            _warning_bar.show_messages(msgs)
        except Exception:
            pass

    # disparar processamento IA em background (se módulo ia disponível)
    if HAS_IA_MODULE and hasattr(ia_module, "processar"):
        try:
            if hasattr(ia_module, "is_chat_mode_active") and ia_module.is_chat_mode_active():
                pass
            else:
                threading.Thread(target=ia_module.processar, daemon=True).start()
                report_status("ia_pipeline", "STARTED", stage="thread_started", details={"source": "save_text_dados"})
        except Exception as e:
            report_status("ia_pipeline", "ERROR", stage="thread_start_failed", details={"error": str(e), "source": "save_text_dados"})
            _log_ui("ERROR", "ia_thread_start_failed", "Falha ao iniciar processamento IA em background", error=str(e))

    # ----------------------
    # OTIMISTIC APPEND (melhorado): usa preprocessor.extrair_tudo_consumo se disponível
    # e inclui _entrada_id no registro para que IA.processar faça merge em vez de duplicar.
    # ----------------------
    if rec:
        rec["_entrada_id"] = nid
        if access_flags:
            rec.update(access_flags)
        # Append to dadosend.json (otimistic). append_record_to_db preserva _entrada_id.
        try:
            ok = append_record_to_db(rec)
            if not ok:
                report_status("db_append", "ERROR", stage="optimistic_append", details={"entrada_id": nid})
        except Exception as e:
            report_status("db_append", "ERROR", stage="optimistic_append_exception", details={"error": str(e), "entrada_id": nid})
            _log_ui("ERROR", "optimistic_db_append_failed", "Erro ao anexar rec otimista ao DB", error=str(e))
    else:
        # fallback ao parser simplista se preprocessor ausente
        try:
            parsed2 = parse_input_to_fields(txt)
            if (parsed2.get("NOME") and parsed2.get("NOME").strip()) or (parsed2.get("PLACA") and parsed2.get("PLACA").strip()):
                rec = build_db_record_from_parsed(parsed2, raw_text=txt)
                # attach entrada id
                rec["_entrada_id"] = nid
                if access_flags:
                    rec.update(access_flags)
                try:
                    post_validate_and_clean_record(rec, modelos_hint=[rec.get("MODELO")] if rec.get("MODELO") and rec.get("MODELO") != "-" else [], cores_hint=[rec.get("COR")] if rec.get("COR") and rec.get("COR") != "-" else [])
                except Exception as e:
                    _log_ui("WARNING", "fallback_validation_failed", "Falha validação final fallback", error=str(e))
                append_record_to_db(rec)
        except Exception as e:
            _log_ui("ERROR", "fallback_db_append_exception", "Erro ao parsear / anexar ao DB (fallback)", error=str(e))

# ---------- open monitor fallback (mantido) ----------
def open_monitor_fallback_subprocess():
    try:
        target = os.path.join(os.path.dirname(__file__), "interfacetwo.py")
        if not os.path.exists(target):
            print("interfacetwo.py não encontrado em:", target); return
        pythonw = None
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, "executable", None) else None
        if exe_dir:
            candidate = os.path.join(exe_dir, "pythonw.exe")
            if os.path.exists(candidate): pythonw = candidate
        if pythonw:
            subprocess.Popen([pythonw, target], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        else:
            python_exe = sys.executable if getattr(sys, "executable", None) else "python"
            kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            else:
                kwargs["start_new_session"] = True
            subprocess.Popen([python_exe, target], **kwargs)
    except Exception as e:
        print("Erro abrir monitor (fallback):", e)

# start_ui updated to ensure SuggestEntry exists before AvisoBar
class AvisoBar(tk.Frame):
    CYCLE_INTERVAL_MS = 10_000
    def __init__(self, master, entry_widget: tk.Entry):
        super().__init__(master)
        self.entry_widget = entry_widget
        try:
            self.font = tkfont.Font(font=self.entry_widget["font"])
        except Exception:
            self.font = tkfont.Font(family="Segoe UI", size=11)
        self.config(bg="#FFFFFF")
        self.msg_var = tk.StringVar()
        self.lbl = tk.Label(self, textvariable=self.msg_var, anchor="w", font=self.font, bd=0)
        self.lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,6), pady=(2,2))
        self.btn_close = tk.Button(self, text="X", width=3, command=self._on_close_click)
        self.btn_close.pack(side=tk.RIGHT, padx=(0,6), pady=(2,2))
        self._active_avisos = []
        self._idx = 0
        self._after_id = None
        self._visible = False
        try:
            self.pack_forget()
        except:
            pass
        try:
            self.after(100, self._schedule_cycle)
        except Exception:
            pass

    @staticmethod
    def _blend_with_white(hex_color: str, alpha: float = 0.7) -> str:
        try:
            if not hex_color or not hex_color.startswith("#"): return "#FFFFFF"
            h = hex_color.lstrip("#")
            if len(h) == 3: h = "".join([c*2 for c in h])
            r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
            a = alpha
            rr = int((a * r) + ((1 - a) * 255))
            gg = int((a * g) + ((1 - a) * 255))
            bb = int((a * b) + ((1 - a) * 255))
            return f"#{rr:02X}{gg:02X}{bb:02X}"
        except Exception:
            return hex_color or "#FFFFFF"

    def _load_avisos_active(self):
        # Recarrega sempre para garantir que qualquer alteração recém-gravada
        # em avisos.json apareça sem depender de resolução de timestamp do FS.
        self._active_avisos = []
        data = _read_json(AVISOS_FILE) or {}
        regs = data.get("registros", []) or []
        for a in regs:
            status = (a.get("status") or {})
            ativo = status.get("ativo", True) if isinstance(status, dict) else True
            fechado = status.get("fechado_pelo_usuario", False) if isinstance(status, dict) else False
            if ativo and not fechado:
                self._active_avisos.append(a)
        if self._idx >= len(self._active_avisos):
            self._idx = 0

    def _format_display_text(self, aviso):
        txt = aviso.get("mensagem") or ""
        txt = str(txt).strip().upper()
        if not txt:
            return ""
        return f"⚠ AVISO: {txt}    "

    def _show_current(self):
        if not self._active_avisos:
            self._hide()
            return
        aviso = self._active_avisos[self._idx % len(self._active_avisos)]
        ui = aviso.get("ui", {}) or {}
        bg = ui.get("background_color") or "#FFFF00"
        blended = self._blend_with_white(bg, alpha=0.7)
        try:
            self.config(bg=blended)
            self.lbl.config(bg=blended, fg=ui.get("text_color", "#000000"))
            self.btn_close.config(bg=blended)
        except:
            pass
        disp = self._format_display_text(aviso)
        self.msg_var.set(disp)
        try:
            parent_frame = getattr(self.entry_widget, "master", None)
            container = getattr(parent_frame, "master", None) or parent_frame
            if container and parent_frame:
                try:
                    self.pack(in_=container, before=parent_frame, fill=tk.X, pady=(0,4))
                except Exception:
                    try: self.pack(in_=container, fill=tk.X, pady=(0,4))
                    except: self.pack(fill=tk.X, pady=(0,4))
            else:
                self.pack(fill=tk.X, pady=(0,4))
        except Exception:
            try:
                self.pack(fill=tk.X, pady=(0,4))
            except:
                pass
        self._visible = True

    def _hide(self):
        if self._visible:
            try:
                self.pack_forget()
            except:
                pass
            self._visible = False
            self.msg_var.set("")

    def _advance_index(self):
        if not self._active_avisos:
            self._idx = 0
        else:
            self._idx = (self._idx + 1) % len(self._active_avisos)

    def _schedule_cycle(self):
        try:
            self._load_avisos_active()
            if self._active_avisos:
                self._show_current()
            else:
                self._hide()
        except Exception:
            pass
        try:
            if self._after_id:
                try: self.after_cancel(self._after_id)
                except Exception:
                    pass
            self._advance_index()
            self._after_id = self.after(self.CYCLE_INTERVAL_MS, self._schedule_cycle)
        except Exception:
            self._after_id = None

    def _on_close_click(self):
        if not self._active_avisos:
            return
        aviso = self._active_avisos[self._idx % len(self._active_avisos)]
        aid = aviso.get("id_aviso")
        try:
            data = _read_json(AVISOS_FILE) or {"registros": [], "ultimo_aviso_ativo": None}
            changed = False
            for a in data.get("registros", []):
                if (a.get("id_aviso") or "") == (aid or ""):
                    st = a.get("status") or {}
                    st["ativo"] = False
                    st["fechado_pelo_usuario"] = True
                    a["status"] = st
                    ts = a.get("timestamps") or {}
                    ts["fechado_em"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    a["timestamps"] = ts
                    changed = True
                    break
            if changed:
                try:
                    atomic_save(AVISOS_FILE, data)
                except Exception:
                    try:
                        with open(AVISOS_FILE, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    except:
                        pass
            self._load_avisos_active()
            if self._active_avisos:
                self._idx = self._idx % max(1, len(self._active_avisos))
                self._show_current()
            else:
                self._hide()
        except Exception as e:
            print("Erro ao fechar aviso:", e)

class WarningBar(tk.Frame):
    DISPLAY_MS = 3000
    def __init__(self, master, entry_widget: tk.Entry, aviso_bar: AvisoBar = None):
        super().__init__(master)
        self.entry_widget = entry_widget
        self.aviso_bar = aviso_bar
        try:
            self.font = tkfont.Font(font=self.entry_widget["font"])
        except Exception:
            self.font = tkfont.Font(family="Segoe UI", size=11)
        self.config(bg="#FF0000")
        self.msg_var = tk.StringVar()
        self.lbl = tk.Label(self, textvariable=self.msg_var, anchor="w", font=self.font, bd=0, bg="#FF0000", fg="#000000")
        self.lbl.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6,6), pady=(2,2))
        self._visible = False
        self._queue = []
        self._after_id = None
        try:
            self.pack_forget()
        except Exception:
            pass

    def show_messages(self, messages: List[str]):
        self._queue = [m for m in messages if m]
        if not self._queue:
            self._hide()
            return
        self._show_next()

    def _show_next(self):
        if not self._queue:
            self._hide()
            return
        msg = self._queue.pop(0)
        self.msg_var.set(msg)
        try:
            parent_frame = getattr(self.entry_widget, "master", None)
            container = getattr(parent_frame, "master", None) or parent_frame
            if self.aviso_bar and getattr(self.aviso_bar, "_visible", False):
                try:
                    self.pack(in_=container, after=self.aviso_bar, fill=tk.X, pady=(0,4))
                except Exception:
                    self.pack(in_=container, before=parent_frame, fill=tk.X, pady=(0,4))
            else:
                self.pack(in_=container, before=parent_frame, fill=tk.X, pady=(0,4))
        except Exception:
            try:
                self.pack(fill=tk.X, pady=(0,4))
            except Exception:
                pass
        self._visible = True
        try:
            if self._after_id:
                try: self.after_cancel(self._after_id)
                except Exception: pass
            self._after_id = self.after(self.DISPLAY_MS, self._show_next)
        except Exception:
            self._after_id = None

    def _hide(self):
        if self._visible:
            try:
                self.pack_forget()
            except Exception:
                pass
        self._visible = False
        self.msg_var.set("")
        if self._after_id:
            try: self.after_cancel(self._after_id)
            except Exception: pass
            self._after_id = None

# ---------------- UI bootstrap ----------------

def start_ui():
    if tk is None:
        print("Tkinter não disponível. Não é possível iniciar interface gráfica.")
        return
    global _warning_bar
    _start_analises_watcher()
    root = tk.Tk(); root.title("Controle de Acesso")
    container = tk.Frame(root); container.pack(padx=10, pady=10, fill=tk.X)

    s = SuggestEntry(container)
    aviso_bar = AvisoBar(container, s.entry)
    _warning_bar = WarningBar(container, s.entry, aviso_bar=aviso_bar)
    s.pack(fill=tk.X)

    btn_frame = tk.Frame(root); btn_frame.pack(padx=10, pady=(8,10))
    btn_save = tk.Button(btn_frame, text="SALVAR", width=12, command=lambda: save_text(entry_widget=s.entry, btn=btn_save)); btn_save.pack(side=tk.LEFT, padx=(0,8))
    def open_monitor_embedded():
        try:
            import interfacetwo
            if getattr(interfacetwo, "_monitor_toplevel", None):
                try: interfacetwo._monitor_toplevel.lift(); interfacetwo._monitor_toplevel.focus_force()
                except Exception:
                    pass
                return
            interfacetwo.create_monitor_toplevel(root)
        except Exception as e:
            print("Falha ao embutir monitor (abrindo fallback):", e); open_monitor_fallback_subprocess()
    btn_dados = tk.Button(btn_frame, text="DADOS", width=12, command=open_monitor_embedded); btn_dados.pack(side=tk.LEFT)
    def ctrl_enter(ev):
        if s.list_visible:
            sel = s.tree.selection()
            if sel:
                try: idx = int(sel[0])
                except: idx = 0
                s._accept_into_entry(idx, hide=True, append_all=True); s._just_accepted=True; return "break"
            else:
                save_text(entry_widget=s.entry, btn=btn_save); return "break"
        save_text(entry_widget=s.entry, btn=btn_save); return "break"
    root.bind("<Control-Return>", ctrl_enter)
    root.bind("<Escape>", lambda e: (s.hide_list(), s._hide_overlay()))
    try: sync_suggestions()
    except Exception:
        pass
    root.mainloop()

def iniciar_interface_principal():
    return start_ui()

if __name__ == "__main__":
    iniciar_interface_principal()
