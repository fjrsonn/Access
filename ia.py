#!/usr/bin/env python3
# ia.py — versão corrigida (garante DATA_HORA visível no dadosend.json e atualiza registros UI com MODELO/COR)
import json
import re
import os
import sys
import tempfile
import time
import traceback
import unicodedata
from typing import Optional, Tuple, Any, Dict, Iterable
from datetime import datetime

# fuzzy matching
try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz
except Exception:
    rf_process = None
    rf_fuzz = None

try:
    from groq import Groq
except Exception:
    Groq = None

from preprocessor import (
    extrair_tudo_consumo,
    VEICULOS_MAP,
    remover_status,
    corrigir_token_nome,
)
from logger import log_forense

# =========================
# PATHS / ENV
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

def load_dotenv(path: str) -> None:
    encodings = ("utf-8-sig", "utf-8", "cp1252")
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip().lstrip("export ").strip()
                    value = value.strip().strip("\"'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            return
        except FileNotFoundError:
            return
        except UnicodeDecodeError:
            continue

def load_dotenv_candidates() -> None:
    candidates = []
    cwd_env = os.path.join(os.getcwd(), ".env")
    if cwd_env != ENV_PATH:
        candidates.append(cwd_env)
    candidates.append(ENV_PATH)
    for path in candidates:
        load_dotenv(path)

load_dotenv_candidates()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    GROQ_API_KEY = GROQ_API_KEY.strip().strip('"').strip("'")
    print(f"[ia.py] GROQ_API_KEY carregada: {GROQ_API_KEY[:6]}... (mascarada)")
else:
    print("[ia.py] AVISO: GROQ_API_KEY não encontrada. IA remota desativada.")

if GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_"):
    print("[ia.py] AVISO: a chave não parece ser Groq (não começa com 'gsk_').")

client = None
if GROQ_API_KEY and Groq is not None:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"[ia.py] Erro ao criar cliente Groq: {e}")
        client = None

ENTRADA = os.path.join(BASE_DIR, "dadosinit.json")
SAIDA = os.path.join(BASE_DIR, "dadosend.json")
ENCOMENDAS_ENTRADA = os.path.join(BASE_DIR, "encomendasinit.json")
ENCOMENDAS_SAIDA = os.path.join(BASE_DIR, "encomendasend.json")
PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "prompt_llm.txt")
AGENT_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "prompt_agente.txt")
LOCK_FILE = os.path.join(BASE_DIR, "process.lock")

_AGENT_PROMPT_ATIVO = ""
CHAT_MODE_ACTIVE = False


def _read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def activate_agent_prompt() -> bool:
    """Carrega prompt do agente apenas quando modo IA é ativado."""
    global _AGENT_PROMPT_ATIVO
    _AGENT_PROMPT_ATIVO = _read_text_file(AGENT_PROMPT_PATH)
    return bool(_AGENT_PROMPT_ATIVO)


def deactivate_agent_prompt() -> None:
    """Limpa prompt do agente ao sair do modo IA para evitar conflitos."""
    global _AGENT_PROMPT_ATIVO
    _AGENT_PROMPT_ATIVO = ""


def set_chat_mode(active: bool) -> None:
    global CHAT_MODE_ACTIVE
    CHAT_MODE_ACTIVE = bool(active)


def is_chat_mode_active() -> bool:
    return CHAT_MODE_ACTIVE


def _apply_agent_prompt_template(response_text: str) -> str:
    """Aplica template do prompt do agente sem alterar pipeline de tratamento."""
    if not isinstance(response_text, str):
        return response_text
    if os.getenv("USE_AGENT_PROMPT", "").strip().lower() not in ("1", "true", "yes", "on"):
        return response_text
    if not _AGENT_PROMPT_ATIVO:
        return response_text

    prompt_text = _AGENT_PROMPT_ATIVO
    marker = "<<TEMPLATE_RESPOSTA>>"
    if marker in prompt_text:
        template = prompt_text.split(marker, 1)[1].strip()
    else:
        template = prompt_text.strip()

    # Se o arquivo possuir instruções longas sem marcador/template utilizável,
    # evita vazamento e mantém resposta base.
    if len(template) > 1200 and "{RESPOSTA_BASE}" not in template:
        return response_text

    if "{RESPOSTA_BASE}" in template:
        return template.replace("{RESPOSTA_BASE}", response_text).strip()

    # fallback seguro: usa o texto como prefixo curto e anexa resposta base
    if len(template) <= 240:
        return f"{template}\n\n{response_text}".strip()
    return response_text

# =========================
# Utilitários IO
# =========================
def carregar(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"registros": data}
            if isinstance(data, dict) and "registros" in data:
                return data
            return {"registros": []}
    except FileNotFoundError:
        return {"registros": []}
    except json.JSONDecodeError:
        print(f"[ia.py] JSON inválido em {path}; usando fallback sem criar .corrupted")
        return {"registros": []}
    except Exception as e:
        print(f"[ia.py] Erro ao carregar {path}: {e}")
        return {"registros": []}

def salvar_atomico(path: str, dados):
    os.makedirs(os.path.dirname(path) or BASE_DIR, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(path),
            prefix=".tmp_",
            suffix=".json",
            delete=False,
        ) as f:
            tmp = f.name
            json.dump(dados, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
        raise

def carregar_prompt():
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "Retorne SOMENTE este JSON:\n"
            '{ "NOME": "", "SOBRENOME": "", "MODELO": "", "COR": "" }'
        )

def extrair_json_seguro(texto: str):
    if not texto:
        return None
    texto_limpo = re.sub(r"```(?:json)?", "", texto)
    blocos = re.findall(r"\{[\s\S]*?\}", texto_limpo)
    if not blocos:
        return None
    for bloco in reversed(blocos):
        try:
            return json.loads(bloco)
        except json.JSONDecodeError:
            continue
    return None

# =========================
# Lock simples (arquivo)
# =========================
def acquire_lock(timeout: int = 10) -> bool:
    start = time.time()
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            if (time.time() - start) > timeout:
                return False
            time.sleep(0.1)

def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass

# =========================
# Helpers para SAIDA (dadosend.json)
# =========================
def _load_saida():
    d = carregar(SAIDA) or {"registros": []}
    regs = d.get("registros", []) or []
    if not isinstance(regs, list): regs = list(regs)
    return regs

def _save_saida(regs):
    try:
        salvar_atomico(SAIDA, {"registros": regs})
        return True
    except Exception:
        try:
            with open(SAIDA, "w", encoding="utf-8") as f:
                json.dump({"registros": regs}, f, ensure_ascii=False, indent=4)
            return True
        except:
            return False

def _find_by_entrada_id(regs, entrada_id):
    if entrada_id is None:
        return None
    for r in regs:
        if str(r.get("_entrada_id") or "") == str(entrada_id):
            return r
    return None

def _next_saida_id(regs):
    maxid = 0
    for r in regs:
        try:
            v = int(r.get("ID") or r.get("id") or 0)
            if v > maxid: maxid = v
        except:
            pass
    return maxid + 1

def append_or_update_saida(dados: dict, entrada_id=None):
    """
    Busca por registro existente com _entrada_id == entrada_id.
    - Se achar, faz merge (preenche campos faltantes) e não cria novo ID.
    - Se não achar, cria novo registro com novo ID e opcionalmente grava _entrada_id.
    """
    regs = _load_saida()
    found = _find_by_entrada_id(regs, entrada_id)
    if found:
        for k in ("MODELO","COR","PLACA","NOME","SOBRENOME","BLOCO","APARTAMENTO","STATUS"):
            incoming = dados.get(k)
            if incoming and incoming != "-" and (not found.get(k) or found.get(k) in ("", "-")):
                found[k] = incoming
        if not found.get("DATA_HORA") and dados.get("DATA_HORA"):
            found["DATA_HORA"] = dados.get("DATA_HORA")
        if not found.get("ID"):
            found["ID"] = _next_saida_id(regs)
        _save_saida(regs)
        return True
    else:
        rec = dict(dados)
        rec.pop("texto", None); rec.pop("texto_original", None)
        rec["_entrada_id"] = entrada_id
        if not rec.get("ID"):
            rec["ID"] = _next_saida_id(regs)
        if not rec.get("DATA_HORA"):
            rec["DATA_HORA"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        regs.append(rec)
        _save_saida(regs)
        return True

_ENCOMENDA_TIPO_MAP = {
    "ENCOMENDA": "ENCOMENDA",
    "PACOTE": "PACOTE",
    "PAC": "PACOTE",
    "PCT": "PACOTE",
    "CAIXA": "CAIXA",
    "CIXA": "CAIXA",
    "CX": "CAIXA",
    "CARTA": "CARTA",
    "ENVELOPE": "ENVELOPE",
    "ENV": "ENVELOPE",
    "SACOLA": "SACOLA",
    "SACO": "SACOLA",
    "ENTREGA": "ENTREGA",
}
_ENCOMENDA_LOJA_MAP = {
    "SHOPEE": "SHOPEE",
    "SHOPE": "SHOPEE",
    "SHOPPE": "SHOPEE",
    "MERCADO": "MERCADO LIVRE",
    "MERCADOLIVRE": "MERCADO LIVRE",
    "MERCADO LIVRE": "MERCADO LIVRE",
    "ML": "MERCADO LIVRE",
    "AMAZON": "AMAZON",
    "TIKTOK": "TIKTOK",
    "TIKTOKSHOP": "TIKTOK",
    "TKTK": "TIKTOK",
    "J&T": "J&T EXPRESS",
    "J& T": "J&T EXPRESS",
    "JNT": "J&T EXPRESS",
    "JNTEXPRESS": "J&T EXPRESS",
    "J&TEXPRESS": "J&T EXPRESS",
    "J&T EXPRESS": "J&T EXPRESS",
    "MAGAZINE": "MAGAZINE LUIZA",
    "MAGALU": "MAGAZINE LUIZA",
    "MAGAZINELUIZA": "MAGAZINE LUIZA",
    "LUIZA": "MAGAZINE LUIZA",
    "ALIEXPRESS": "ALIEXPRESS",
    "ALIE": "ALIEXPRESS",
    "SHEIN": "SHEIN",
    "CORREIOS": "CORREIOS",
    "SEDEX": "CORREIOS",
    "RIACHUELO": "RIACHUELO",
    "GROWTH": "GROWTH",
    "GRONWTH": "GROWTH",
}

def _encomenda_tokens(texto: str):
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9\-]+", str(texto or ""))

def _build_loja_ignore_tokens():
    tokens_set = set()
    for key, value in _ENCOMENDA_LOJA_MAP.items():
        for part in re.findall(r"[A-Za-z0-9]+", str(key).upper()):
            tokens_set.add(part)
        for part in re.findall(r"[A-Za-z0-9]+", str(value).upper()):
            tokens_set.add(part)
    return tokens_set

_ENCOMENDA_LOJA_IGNORE_TOKENS = _build_loja_ignore_tokens()

_ENCOMENDA_NOME_CORRECOES = {
    "JOAO": "JOÃO",
    "JOSE": "JOSÉ",
    "MARIA": "MARIA",
    "ANA": "ANA",
    "LUIZ": "LUIZ",
    "LUIZA": "LUÍZA",
    "PAULO": "PAULO",
    "FERNANDO": "FERNANDO",
    "GABRIEL": "GABRIEL",
    "RAFAEL": "RAFAEL",
    "RAFAELA": "RAFAELA",
    "MARCIO": "MÁRCIO",
    "MARCIA": "MÁRCIA",
    "SIMONE": "SIMONE",
    "ANDRE": "ANDRÉ",
    "ANDREA": "ANDRÉA",
    "THIAGO": "THIAGO",
    "VICTOR": "VICTOR",
    "VICTORIA": "VICTÓRIA",
}

def _normalize_encomenda_text(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = re.sub(r"[^A-Za-z0-9]+", " ", base).upper()
    return re.sub(r"\s+", " ", base).strip()

def _match_encomenda_store(texto: str, tokens_up):
    normalized = _normalize_encomenda_text(texto)
    for key, value in _ENCOMENDA_LOJA_MAP.items():
        key_norm = _normalize_encomenda_text(key)
        if key_norm and key_norm in normalized:
            return value
    for tok in tokens_up:
        if tok in _ENCOMENDA_LOJA_MAP:
            return _ENCOMENDA_LOJA_MAP[tok]
    if rf_process and rf_fuzz:
        candidates = list(_ENCOMENDA_LOJA_MAP.keys())
        for tok in tokens_up:
            best = rf_process.extractOne(tok, candidates, scorer=rf_fuzz.WRatio)
            if best and best[1] >= 88:
                return _ENCOMENDA_LOJA_MAP.get(best[0], "")
    return ""

def _match_encomenda_tipo(tokens_up):
    for tok in tokens_up:
        if tok in _ENCOMENDA_TIPO_MAP:
            return _ENCOMENDA_TIPO_MAP[tok]
    if rf_process and rf_fuzz:
        candidates = list(_ENCOMENDA_TIPO_MAP.keys())
        for tok in tokens_up:
            best = rf_process.extractOne(tok, candidates, scorer=rf_fuzz.WRatio)
            if best and best[1] >= 88:
                return _ENCOMENDA_TIPO_MAP.get(best[0], "")
    return ""

def _fix_nome_token(token: str) -> str:
    if not token:
        return token
    token_up = token.upper()
    if token_up in _ENCOMENDA_NOME_CORRECOES:
        return _ENCOMENDA_NOME_CORRECOES[token_up]
    return token

def _parse_bloco_ap_tokens(tokens_up):
    bloco = ""
    ap = ""
    for i, tok in enumerate(tokens_up):
        if tok in ("BLOCO", "BL", "B") and i + 1 < len(tokens_up) and tokens_up[i + 1].isdigit():
            bloco = tokens_up[i + 1]
            break
        if re.match(r"^BL\d+$", tok):
            bloco = tok.replace("BL", "")
            break
        if re.match(r"^B\d+$", tok):
            bloco = tok.replace("B", "")
            break
    for i, tok in enumerate(tokens_up):
        if tok in ("AP", "APT", "APARTAMENTO", "A") and i + 1 < len(tokens_up) and tokens_up[i + 1].isdigit():
            ap = tokens_up[i + 1]
            break
        if re.match(r"^AP\d+$", tok):
            ap = tok.replace("AP", "")
            break
        if re.match(r"^A\d+$", tok):
            ap = tok.replace("A", "")
            break
    return bloco, ap

def _extract_identificacao(tokens_up):
    for tok in reversed(tokens_up):
        if re.match(r"^[A-Z]{3}\d{4}$", tok) or re.match(r"^[A-Z]{3}\d[A-Z]\d{2}$", tok):
            continue
        if re.match(r"^\d{5,}$", tok):
            return tok
        m = re.search(r"(\d{5,})", tok)
        if m:
            return m.group(1)
    return ""

def _parse_encomenda_text(texto: str) -> dict:
    toks = _encomenda_tokens(texto)
    toks_up = [t.upper() for t in toks]
    bloco, ap = _parse_bloco_ap_tokens(toks_up)
    identificacao = _extract_identificacao(toks_up)

    tipo = _match_encomenda_tipo(toks_up)
    loja = _match_encomenda_store(texto, toks_up)
    if not tipo:
        tipo = "ENCOMENDA" if loja or identificacao else ""

    ignore_tokens = set(_ENCOMENDA_TIPO_MAP.keys()) | set(_ENCOMENDA_LOJA_MAP.keys())
    ignore_tokens.update(_ENCOMENDA_LOJA_IGNORE_TOKENS)
    ignore_tokens.update({"BLOCO", "BL", "AP", "APT", "APARTAMENTO"})
    ignore_tokens.update({f"BL{bloco}" for bloco in ([bloco] if bloco else [])})
    ignore_tokens.update({f"AP{ap}" for ap in ([ap] if ap else [])})

    nome_parts = []
    for tok in toks:
        tok_up = tok.upper()
        if tok_up in ignore_tokens:
            continue
        if tok_up.isdigit():
            continue
        if identificacao and tok_up == identificacao:
            continue
        if re.match(r"^(BL|AP)\d+$", tok_up):
            continue
        if re.match(r"^\d{5,}$", tok_up):
            continue
        nome_parts.append(tok)

    if nome_parts and corrigir_token_nome:
        try:
            nome_parts = [corrigir_token_nome(p) for p in nome_parts]
        except Exception:
            pass
    nome_parts = [_fix_nome_token(p) for p in nome_parts]

    nome = nome_parts[0].upper() if nome_parts else "-"
    sobrenome = " ".join(nome_parts[1:]).upper() if len(nome_parts) > 1 else "-"

    return {
        "NOME": nome or "-",
        "SOBRENOME": sobrenome or "-",
        "BLOCO": bloco or "-",
        "APARTAMENTO": ap or "-",
        "TIPO": tipo or "-",
        "LOJA": loja or "-",
        "IDENTIFICACAO": identificacao or "-",
    }

def _load_encomendas_saida():
    d = carregar(ENCOMENDAS_SAIDA) or {"registros": []}
    regs = d.get("registros", []) or []
    if not isinstance(regs, list):
        regs = list(regs)
    return regs

def _save_encomendas_saida(regs):
    try:
        salvar_atomico(ENCOMENDAS_SAIDA, {"registros": regs})
        return True
    except Exception:
        try:
            with open(ENCOMENDAS_SAIDA, "w", encoding="utf-8") as f:
                json.dump({"registros": regs}, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            return False

def _next_encomenda_id(regs):
    maxid = 0
    for r in regs:
        try:
            v = int(r.get("ID") or r.get("id") or 0)
            if v > maxid:
                maxid = v
        except Exception:
            pass
    return maxid + 1

def append_or_update_encomendas(dados: dict, entrada_id=None):
    regs = _load_encomendas_saida()
    found = _find_by_entrada_id(regs, entrada_id)
    if found:
        for k in ("NOME","SOBRENOME","BLOCO","APARTAMENTO","TIPO","LOJA","IDENTIFICACAO"):
            incoming = dados.get(k)
            if incoming and incoming != "-" and (not found.get(k) or found.get(k) in ("", "-")):
                found[k] = incoming
        if not found.get("DATA_HORA") and dados.get("DATA_HORA"):
            found["DATA_HORA"] = dados.get("DATA_HORA")
        if not found.get("ID"):
            found["ID"] = _next_encomenda_id(regs)
        _save_encomendas_saida(regs)
        return True
    rec = dict(dados)
    rec.pop("texto", None)
    rec.pop("texto_original", None)
    rec["_entrada_id"] = entrada_id
    if not rec.get("ID"):
        rec["ID"] = _next_encomenda_id(regs)
    if not rec.get("DATA_HORA"):
        rec["DATA_HORA"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    regs.append(rec)
    _save_encomendas_saida(regs)
    return True

def parse_dt(s):
    if not s: return None
    try:
        for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                return datetime.strptime(s.strip(), fmt)
            except:
                pass
        m = re.match(r"^(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2}(:\d{2})?)?", s.strip())
        if m:
            date = m.group(1)
            timep = m.group(2) or "00:00:00"
            if len(timep.split(":")) == 2: timep += ":00"
            return datetime.strptime(f"{date} {timep}", "%d/%m/%Y %H:%M:%S")
    except:
        return None
    return None

def _disable_client_due_to_auth():
    global client, GROQ_API_KEY
    print("[ia.py] Desativando Groq client devido a erro de autenticação. Atualize GROQ_API_KEY e reinicie.")
    client = None
    GROQ_API_KEY = None

# =========================
# Validação híbrida de MODELO (com fuzzy match)
# =========================
def validar_modelo_str(s: str) -> Optional[str]:
    if not s:
        return None
    s_original = str(s).strip()
    s_norm = re.sub(r"[^\w\d\s\-]", " ", s_original).upper()

    # 1) mapeamento direto via VEICULOS_MAP (chaves e abreviações)
    try:
        for modelo_key, abrevs in VEICULOS_MAP.items():
            if re.search(rf"\b{re.escape(modelo_key.upper())}\b", s_norm):
                return modelo_key
            for ab in abrevs:
                if re.search(rf"\b{re.escape(ab.upper())}\b", s_norm):
                    return modelo_key
    except Exception:
        pass

    # 2) fuzzy match usando rapidfuzz (se disponível)
    try:
        if rf_process and VEICULOS_MAP:
            candidates = []
            for modelo_key, abrevs in VEICULOS_MAP.items():
                candidates.append(modelo_key.upper())
                for ab in abrevs:
                    candidates.append(str(ab).upper())
            candidates = list(dict.fromkeys(candidates))
            best = rf_process.extractOne(s_original.upper(), candidates, scorer=rf_fuzz.WRatio)
            if best and len(best) >= 2:
                value, score, _ = best
                if score >= 80:
                    for modelo_key, abrevs in VEICULOS_MAP.items():
                        if value.upper() == modelo_key.upper() or value.upper() in [a.upper() for a in abrevs]:
                            return modelo_key
    except Exception:
        pass

    # 3) heurística permissiva: remover palavras de cor e retornar o que sobrou
    if len(s_original) >= 3 and not re.fullmatch(r"[A-Z]{3}\d{4}", s_norm) and not re.fullmatch(r"\d+", s_norm):
        limpo = re.sub(
            r"\b(preto|preta|branco|branca|prata|cinza|vermelho|azul|verde|amarelo|dourado|bege|marrom|vinho)\b",
            "",
            s_original,
            flags=re.I,
        ).strip()
        if limpo:
            return limpo.title()

    return None

def _uppercase_value(v: Any) -> Any:
    if isinstance(v, str):
        return v.upper()
    if isinstance(v, list):
        return [_uppercase_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _uppercase_value(val) for k, val in v.items()}
    return v

def uppercase_dict_values(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        out[k] = _uppercase_value(v)
    return out

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
        # se existir campo MODELO no registro, use como hint
        if rec.get("MODELO") and rec.get("MODELO") not in ("", "-"):
            modelos_hint.append(rec.get("MODELO"))
    except: pass

    # build tokens sets (normalize)
    def _norm_token_local(t):
        if not t: return ""
        s = unicodedata.normalize("NFKD", str(t))
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        return re.sub(r"[^A-Za-z0-9]+", "", s).lower().strip()

    model_set = set(_norm_token_local(x) for x in modelos_hint if x)
    # include VEICULOS_MAP keys/abrev if available
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

    # helper fuzzy (usa rapidfuzz se disponível)
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
            # fallback cheap check
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

    # sanitize name fields
    nome = (rec.get("NOME") or "").strip()
    sobrenome = (rec.get("SOBRENOME") or "").strip()
    # combine tokens and preserve order: first name token is primeiro nome, rest sobrenome
    combined = []
    if nome:
        combined += _tokenize_alpha(nome)
    if sobrenome:
        combined += _tokenize_alpha(sobrenome)

    cleaned = []
    for tok in combined:
        if not tok: continue
        tu = tok.strip()
        # skip if looks like placa / bloco / ap / status
        if re.match(r"^[A-Z]{3}\d{4}$", tu, flags=re.IGNORECASE) or (re.match(r"^[A-Z0-9]{5,8}$", tu, flags=re.IGNORECASE) and re.search(r"\d", tu)):
            continue
        if re.match(r"^BL\d+$", tu.upper()) or re.match(r"^AP\d+$", tu.upper()):
            continue
        if tu.upper() in ("MORADOR","VISITANTE","PRESTADOR","DESCONHECIDO"):
            continue
        # skip color-like or model-like tokens
        if _is_color_like(tu) or _is_model_like(tu):
            continue
        # skip common prepositions
        if tu.upper() in ("DO","DA","DE","DOS","DAS","E","O","A","SR","SRA"):
            continue
        corrected = corrigir_token_nome(tu)
        cleaned.append(corrected.title())

    # reconstruct nome / sobrenome
    if cleaned:
        rec["NOME"] = cleaned[0].upper()
        rec["SOBRENOME"] = " ".join(cleaned[1:]).upper() if len(cleaned) > 1 else "-"
    else:
        # fallback: keep original if nothing left, but ensure '-' values
        if not rec.get("NOME") or rec.get("NOME") in ("", "-"):
            rec["NOME"] = "-"
        if not rec.get("SOBRENOME") or rec.get("SOBRENOME") in ("", "-"):
            rec["SOBRENOME"] = "-"

    # force MODEL/PLACA/COR uppercase and ensure not empty
    for k in ("MODELO","PLACA","COR","STATUS","BLOCO","APARTAMENTO"):
        v = rec.get(k)
        if not v or (isinstance(v, str) and v.strip() == ""):
            rec[k] = "-"
        elif isinstance(v, str):
            rec[k] = v.upper()

    return rec

def _split_nome_raw(nome_raw: str):
    parts = [p for p in str(nome_raw or "").split() if p]
    if not parts:
        return []
    try:
        return [corrigir_token_nome(p).upper() for p in parts]
    except Exception:
        return [p.upper() for p in parts]

def _fill_nome_from_raw(dados: dict, nome_raw: str) -> None:
    parts = _split_nome_raw(nome_raw)
    if not parts:
        return
    if dados.get("NOME") in (None, "", "-"):
        dados["NOME"] = parts[0]
    if len(parts) > 1 and dados.get("SOBRENOME") in (None, "", "-"):
        dados["SOBRENOME"] = " ".join(parts[1:])

# =========================
# PROCESSAMENTO PRINCIPAL
# =========================
def processar():
    if is_chat_mode_active():
        print("[ia.py] Modo chat ativo. Processamento IA suspenso.")
        return
    if not acquire_lock(timeout=5):
        print("[ia.py] Outro processo em execução. Abortando.")
        return

    try:
        entrada = carregar(ENTRADA)
        prompt_base = carregar_prompt()

        for r in entrada.get("registros", []):
            if r.get("processado"):
                continue

            texto_original = r.get("texto", "") or r.get("texto_original", "") or ""
            try:
                pre = extrair_tudo_consumo(texto_original)
            except Exception as e:
                print(f"[ia.py] Erro ao extrair dados (id={r.get('id')}): {e}")
                traceback.print_exc()
                pre = {
                    "TEXTO_LIMPO": texto_original or "",
                    "COR": "",
                    "PLACA": "",
                    "BLOCO": "",
                    "APARTAMENTO": "",
                    "MODELOS": [],
                    "NOME_RAW": "",
                }

            status = pre.get("STATUS", "DESCONHECIDO")
            modelos_pre = pre.get("MODELOS", []) or []
            endereco = {
                "BLOCO": pre.get("BLOCO", ""),
                "APARTAMENTO": pre.get("APARTAMENTO", ""),
                "PLACA": pre.get("PLACA", ""),
            }
            cor_pre = pre.get("COR", "") or ""
            if isinstance(cor_pre, list):
                cor_pre = next((c for c in cor_pre if isinstance(c, str) and c.strip()), " ".join(map(str, cor_pre)))
            cor_pre = str(cor_pre).strip()

            texto_limpo = pre.get("TEXTO_LIMPO") or pre.get("NOME_RAW") or remover_status(texto_original)

            prompt = (
                prompt_base
                + "\n\nTexto:\n"
                + texto_limpo
                + "\n\nResponda SOMENTE com JSON válido seguindo o schema:\n"
                '{ "NOME": "", "SOBRENOME": "", "MODELO": "", "COR": "" }'
            )

            dados_ia = None
            conteudo = ""

            if client:
                try:
                    resposta = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                    )
                    conteudo = (
                        resposta.choices[0].message.content
                        if hasattr(resposta, "choices") and resposta.choices
                        else str(resposta)
                    )
                    dados_ia = extrair_json_seguro(conteudo)
                    if isinstance(dados_ia, dict):
                        dados_ia = uppercase_dict_values(dados_ia)
                except Exception as e:
                    err_msg = str(e).lower()
                    print(f"⚠️ Falha IA (fallback ativo): {e}")
                    traceback.print_exc()
                    if "invalid_api_key" in err_msg or "401" in err_msg:
                        _disable_client_due_to_auth()

            dados = {
                "NOME": "-",
                "SOBRENOME": "-",
                "MODELO": "-",
                "COR": "-",
            }
            if dados_ia:
                if isinstance(dados_ia.get("NOME"), str) and dados_ia.get("NOME").strip():
                    dados["NOME"] = dados_ia.get("NOME").upper()
                if isinstance(dados_ia.get("SOBRENOME"), str) and dados_ia.get("SOBRENOME").strip():
                    dados["SOBRENOME"] = dados_ia.get("SOBRENOME").upper()
                ia_modelo = dados_ia.get("MODELO") if isinstance(dados_ia.get("MODELO"), str) else ""
                modelo_validado = validar_modelo_str(ia_modelo) if ia_modelo else None
                if modelo_validado:
                    dados["MODELO"] = modelo_validado.upper()
                cor_ia = dados_ia.get("COR") if isinstance(dados_ia.get("COR"), str) else ""
                if cor_ia:
                    dados["COR"] = cor_ia.upper()

            # fallback: se IA não deu modelo, usar parser preprocessor
            if modelos_pre:
                candidato = modelos_pre[0]
                if candidato:
                    candidato_val = validar_modelo_str(candidato)
                    if candidato_val:
                        dados["MODELO"] = candidato_val.upper()
                    else:
                        dados["MODELO"] = str(candidato).upper()
            else:
                mpre = pre.get("MODELO") or ""
                if mpre:
                    mv = validar_modelo_str(mpre) or mpre
                    dados["MODELO"] = str(mv).upper()

            if cor_pre:
                dados["COR"] = cor_pre.upper()

            nome_raw = pre.get("NOME_RAW", "") or ""
            if nome_raw:
                _fill_nome_from_raw(dados, nome_raw)

            dados["PLACA"] = (endereco.get("PLACA", "") or "-").upper()
            dados["BLOCO"] = (endereco.get("BLOCO", "") or "-").upper()
            dados["APARTAMENTO"] = (endereco.get("APARTAMENTO", "") or "-").upper()
            dados["STATUS"] = (status or "DESCONHECIDO").upper()

            for k in ["NOME","SOBRENOME","BLOCO","APARTAMENTO","PLACA","MODELO","COR","STATUS"]:
                v = dados.get(k)
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    dados[k] = "-"
                elif isinstance(v, str):
                    dados[k] = v.upper()

            # keep entrada id for matching
            entrada_id = r.get("id") or r.get("ID")
            if entrada_id is not None:
                try:
                    dados["_entrada_id"] = entrada_id
                except:
                    pass

            dh = r.get("DATA_HORA") or r.get("data_hora")
            if isinstance(dh, str) and dh.strip():
                dados["DATA_HORA"] = dh.strip()
            else:
                dados["DATA_HORA"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            # mark entrada as processed
            r["processado"] = True
            try:
                salvar_atomico(ENTRADA, entrada)
            except Exception as e:
                print("[ia.py] Falha ao salvar ENTRADA:", e)

            # última validação: limpa NOME/SOBRENOME de tokens de MODELO/COR/PLACA
            try:
                post_validate_and_clean_record(
                    dados,
                    modelos_hint=[dados.get("MODELO")] if dados.get("MODELO") and dados.get("MODELO") != "-" else [],
                    cores_hint=[dados.get("COR")] if dados.get("COR") and dados.get("COR") != "-" else []
                )
            except Exception as e:
                print("[ia.py] Aviso: falha na validação final (não bloqueante):", e)

            if nome_raw:
                _fill_nome_from_raw(dados, nome_raw)

            # Append or update SAIDA (merge por _entrada_id)
            try:
                ok = append_or_update_saida(dados, entrada_id=entrada_id)
                if not ok:
                    print("[ia.py] Falha ao anexar/atualizar registro em SAIDA")
                else:
                    print(f"[ia.py] Registro processado: entrada_id={entrada_id} PLACA={dados.get('PLACA')} MODELO={dados.get('MODELO')} COR={dados.get('COR')}")
            except Exception as e:
                print("[ia.py] Erro ao anexar/atualizar registro em SAIDA:", e)
                traceback.print_exc()

            log_forense(r.get("id"), texto_original, dados.get("STATUS"), "ia.py")

        encomendas = carregar(ENCOMENDAS_ENTRADA)
        for r in encomendas.get("registros", []):
            if r.get("processado"):
                continue

            texto_original = r.get("texto", "") or r.get("texto_original", "") or ""
            dados = _parse_encomenda_text(texto_original)
            for k in ("NOME", "SOBRENOME", "BLOCO", "APARTAMENTO", "TIPO", "LOJA", "IDENTIFICACAO"):
                v = dados.get(k)
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    dados[k] = "-"
                elif isinstance(v, str):
                    dados[k] = v.upper()

            entrada_id = r.get("id") or r.get("ID")
            if entrada_id is not None:
                dados["_entrada_id"] = entrada_id

            dh = r.get("DATA_HORA") or r.get("data_hora")
            if isinstance(dh, str) and dh.strip():
                dados["DATA_HORA"] = dh.strip()
            else:
                dados["DATA_HORA"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

            r["processado"] = True
            try:
                salvar_atomico(ENCOMENDAS_ENTRADA, encomendas)
            except Exception as e:
                print("[ia.py] Falha ao salvar ENCOMENDAS_ENTRADA:", e)

            try:
                ok = append_or_update_encomendas(dados, entrada_id=entrada_id)
                if not ok:
                    print("[ia.py] Falha ao anexar/atualizar encomenda em ENCOMENDAS_SAIDA")
            except Exception as e:
                print("[ia.py] Erro ao anexar/atualizar encomenda:", e)
                traceback.print_exc()

    finally:
        release_lock()

# =========================
# respond_query and IA utilities (mantidos)
# =========================
def respond_query(user_query: str, db_path: str = SAIDA, model: str = "llama-3.1-8b-instant", temperature: float = 0.0, timeout: int = 15) -> str:
    if db_path and db_path != SAIDA:
        db_sources = {os.path.basename(db_path): carregar(db_path).get("registros", [])}
    else:
        db_sources = {
            "dadosinit.json": carregar(ENTRADA).get("registros", []),
            "dadosend.json": carregar(SAIDA).get("registros", []),
            "analises.json": carregar(os.path.join(BASE_DIR, "analises.json")).get("registros", []),
            "avisos.json": carregar(os.path.join(BASE_DIR, "avisos.json")).get("registros", []),
        }

    try:
        db_json = json.dumps(db_sources, ensure_ascii=False)
    except Exception:
        db_json = str(db_sources)[:20000]

    user_msg = (
        f"{db_json}\n\n"
        f"Pergunta do usuário: {user_query}\n"
        "Responda livremente usando apenas os dados acima."
    )

    if IN_IA_MODE and client is not None:
        try:
            resposta = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "user", "content": user_msg},
                ],
                temperature=temperature,
            )
            content = (
                resposta.choices[0].message.content
                if hasattr(resposta, "choices") and resposta.choices
                else str(resposta)
            )
            return content if isinstance(content, str) else content
        except Exception as e:
            err_msg = str(e).lower()
            print(f"[ia.respond_query] Erro ao consultar LLM: {e}")
            traceback.print_exc()
            if "invalid_api_key" in err_msg or "401" in err_msg:
                _disable_client_due_to_auth()
            return f"ERRO AO CONSULTAR IA REMOTA: {e}"

    return "IA REMOTA NAO ESTA DISPONIVEL NO MOMENTO. VERIFIQUE A CHAVE E A CONECTIVIDADE PARA CONTINUAR."

# =========================
# MODO IA helpers (mantidos)
IN_IA_MODE = False

def _normalize_cmd(text: str) -> str:
    if text is None:
        return ""
    return str(text).strip().upper()

def is_enter_ia_command(text: str) -> bool:
    t = _normalize_cmd(text)
    return t in ("IA", "AI")

def is_exit_ia_command(text: str) -> bool:
    t = _normalize_cmd(text).lstrip("/")
    return t in ("SAIR", "EXIT", "QUIT")

def enter_ia_mode() -> str:
    global IN_IA_MODE
    IN_IA_MODE = True
    activate_agent_prompt()
    return "MODO IA ATIVADO — ESCREVA SUA PERGUNTA. PARA SAIR, DIGITE 'SAIR'.".upper()

def exit_ia_mode() -> str:
    global IN_IA_MODE
    IN_IA_MODE = False
    deactivate_agent_prompt()
    return "MODO IA DESATIVADO. VOCÊ PODE CONTINUAR DIGITANDO NORMALMENTE.".upper()

def handle_input_text(text: str, *, respond_fn=respond_query) -> Tuple[bool, str]:
    global IN_IA_MODE
    if not text:
        return False, ""
    if is_enter_ia_command(text) and not IN_IA_MODE:
        return True, enter_ia_mode()
    if IN_IA_MODE:
        if is_exit_ia_command(text):
            return True, exit_ia_mode()
        try:
            resp = respond_fn(text)
            return True, resp if isinstance(resp, str) else resp
        except Exception as e:
            print(f"[handle_input_text] Erro ao chamar IA: {e}")
            traceback.print_exc()
            return True, f"ERRO AO CONSULTAR IA: {e}".upper()
    return False, text.upper() if isinstance(text, str) else text

# CLI opcional
def _cli_repl():
    print("REPL IA — digite 'ia' para ativar modo IA; 'sair' para sair do modo IA; 'quit' para encerrar.".upper())
    while True:
        try:
            txt = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nENCERRANDO REPL.".upper())
            break
        if txt is None:
            continue
        t = txt.strip()
        if t.lower() in ("quit", "q", "sair_tudo"):
            print("ENCERRANDO.".upper())
            break
        handled, resp = handle_input_text(t)
        if handled:
            print(resp)
        else:
            print(f"[ENTRADA NORMAL] {resp}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("cli", "interactive", "repl"):
        _cli_repl()
    else:
        processar()
