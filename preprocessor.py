# preprocessor.py (corrigido)
# Funções para extrair nome, placa, bloco, apartamento, modelos, cor e status
# Exporta: extrair_tudo_consumo, VEICULOS_MAP, remover_status, detectar_status

import re
from typing import Dict, Any, List, Tuple

# mapa simples de modelos -> abreviações/comuns (aumente conforme necessário)
VEICULOS_MAP = {
    "JETTA": ["JETTA", "JET"],
    "ONIX": ["ONIX", "ÔNIX"],
    "GOLF": ["GOLF"],
    "CIVIC": ["CIVIC"],
    "COROLLA": ["COROLLA"],
    "HB20": ["HB20"],
    "PALIO": ["PALIO"],
    "UNO": ["UNO"],
    "STRADA": ["STRADA"],
    "KWID": ["KWID"],
    "SANDERO": ["SANDERO"],
    "LOGAN": ["LOGAN"],
    "VERSYS": ["VERSYS"],
    "HONDA": ["HONDA"],  # fallback genérico (pouco usado)
    "YAMAHA": ["YAMAHA"],
    # adicione mais modelos conforme base local
}

# cores comuns (pt-BR)
_CORES = [
    "PRETO","PRETA","BRANCO","BRANCA","PRATA","CINZA","CINZENTO","VERMELHO","VERMELHA",
    "AZUL","VERDE","AMARELO","DOURADO","BEGE","MARROM","VINHO","ROSA","GRAFITE","CINZA",
    "CINZAS"
]
_CORES_SET = set([c.upper() for c in _CORES])

# palavras de status
_STATUS_MAP = {
    "MORADOR": ["MORADOR","MORADORES","M","RESIDENTE"],
    "VISITANTE": ["VISITANTE","VISITA","VISIT","VIS"],
    "PRESTADOR": ["PRESTADOR","PRESTADORES","PREST","PRESTAD","SERVICO","SERVIÇO","TECNICO","TÉCNICO"],
    "DESCONHECIDO": ["DESCONHECIDO","?"]
}
_STATUS_WORDS = set()
for k,v in _STATUS_MAP.items():
    for w in v:
        _STATUS_WORDS.add(w.upper())

_plate_re_1 = re.compile(r"^[A-Z]{3}\d{4}$", re.IGNORECASE)
_plate_re_2 = re.compile(r"^[A-Z0-9]{5,8}$", re.IGNORECASE)

_token_re = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9\-]+")

def tokens(text: str) -> List[str]:
    return _token_re.findall(str(text or ""))

def _is_plate(tok: str) -> bool:
    t = tok.strip().upper()
    if _plate_re_1.match(t):
        return True
    # second pattern: alnum 5-8 with at least one digit
    if _plate_re_2.match(t) and re.search(r"\d", t):
        return True
    return False

def detectar_status(texto: str) -> Tuple[str, str]:
    """
    Retorna (STATUS, texto_sem_status)
    STATUS é uma string padronizada ('MORADOR','VISITANTE','PRESTADOR','DESCONHECIDO')
    """
    if not texto:
        return "DESCONHECIDO", texto or ""
    toks = [t.upper() for t in tokens(texto)]
    found = None
    for t in toks:
        if t in _STATUS_WORDS:
            # map to canonical
            for k, aliases in _STATUS_MAP.items():
                if t in [a.upper() for a in aliases]:
                    found = k
                    break
            if found:
                break
    if not found:
        found = "DESCONHECIDO"
    # remove status words from text (first occurrences)
    pattern = r"\b(" + "|".join(re.escape(w) for w in _STATUS_WORDS) + r")\b"
    cleaned = re.sub(pattern, "", texto, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return found, cleaned

def remover_status(texto: str) -> str:
    st, cleaned = detectar_status(texto)
    return cleaned

# ===== utilities to normalize/match model candidates =====

def _normalize_token(tok: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(tok or "").upper())

def _edit_distance(a: str, b: str) -> int:
    # classic Levenshtein (efficient enough for short tokens)
    a = a or ""
    b = b or ""
    la, lb = len(a), len(b)
    if la == 0: return lb
    if lb == 0: return la
    dp = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1): dp[i][0] = i
    for j in range(lb + 1): dp[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i-1] == b[j-1] else 1
            dp[i][j] = min(dp[i-1][j] + 1, dp[i][j-1] + 1, dp[i-1][j-1] + cost)
    return dp[la][lb]

def _map_to_canonical_model(candidate: str) -> str:
    """Tenta mapear um candidato de modelo a uma chave canônica em VEICULOS_MAP.
    Estratégia:
      - busca igualdade com chave ou abreviações
      - busca igualdade normalizada
      - se não houver, tenta correspondência por distância de edição <=1 com chaves/abrev
      - se nada, retorna candidate.upper()
    """
    if not candidate:
        return ""
    cand_norm = _normalize_token(candidate)
    # exact matches
    for key, abrevs in VEICULOS_MAP.items():
        if cand_norm == _normalize_token(key):
            return key.upper()
        for a in abrevs:
            if cand_norm == _normalize_token(a):
                return key.upper()
    # substring / startswith (helps JETA -> JETTA)
    for key, abrevs in VEICULOS_MAP.items():
        kn = _normalize_token(key)
        if cand_norm in kn or kn in cand_norm:
            return key.upper()
    # edit distance <=1
    cand_short = cand_norm
    best_key = None
    best_dist = None
    for key, abrevs in VEICULOS_MAP.items():
        kn = _normalize_token(key)
        d = _edit_distance(cand_short, kn)
        if best_dist is None or d < best_dist:
            best_dist = d; best_key = key
        for a in abrevs:
            an = _normalize_token(a)
            d2 = _edit_distance(cand_short, an)
            if best_dist is None or d2 < best_dist:
                best_dist = d2; best_key = key
    if best_dist is not None and best_dist <= 1:
        return best_key.upper()
    return candidate.upper()

# ---------- model/color/block/ap helpers already used by original code ----------

def _find_model_candidates(toks_up: List[str]) -> List[str]:
    found = []
    # direct detection via VEICULOS_MAP keys/abrev
    for i, tok in enumerate(toks_up):
        for modelo_key, abrevs in VEICULOS_MAP.items():
            if tok.upper() == modelo_key.upper() or tok.upper() in [a.upper() for a in abrevs]:
                found.append(modelo_key.upper())
    # also try to look near plate: if token previous to plate is alphabetic and length>2, treat as model
    for i, tok in enumerate(toks_up):
        if _is_plate(tok):
            if i-1 >= 0:
                cand = toks_up[i-1]
                if cand.isalpha() and len(cand) >= 2 and cand.upper() not in _CORES_SET and cand.upper() not in _STATUS_WORDS:
                    found.append(cand.upper().title())
            # also check next tokens
            if i+1 < len(toks_up):
                cand2 = toks_up[i+1]
                if cand2.isalpha() and len(cand2) >= 2 and cand2.upper() not in _CORES_SET and cand2.upper() not in _STATUS_WORDS:
                    found.append(cand2.upper().title())
    # dedupe preserving order
    out = []
    for x in found:
        if x not in out:
            out.append(x)
    return out

def _find_color_candidates(toks_up: List[str]) -> List[str]:
    out = []
    for t in toks_up:
        if t.upper() in _CORES_SET:
            out.append(t.upper())
    return out

def _find_block_ap(toks_up: List[str]) -> (str, str):
    bloco = ""
    apt = ""
    for i, t in enumerate(toks_up):
        # BL10, BL-10 patterns
        m = re.match(r"^BL(?:OCO)?[-:]?(\d+)$", t, flags=re.IGNORECASE)
        if m:
            bloco = m.group(1)
            continue
        if t.startswith("BL") and t[2:].isdigit():
            bloco = t[2:]
            continue
        if t == "BLOCO":
            if i+1 < len(toks_up) and toks_up[i+1].isdigit():
                bloco = toks_up[i+1]
        if t in ("AP","APT","APTO","APARTAMENTO"):
            if i+1 < len(toks_up) and toks_up[i+1].isdigit():
                apt = toks_up[i+1]
                continue
        m2 = re.match(r"^AP(?:T|ARTAMENTO)?[-:]?(\d+)$", t, flags=re.IGNORECASE)
        if m2:
            apt = m2.group(1)
            continue
        if t.startswith("AP") and t[2:].isdigit():
            apt = t[2:]
            continue
    return bloco or "", apt or ""

def _extract_plate_and_indices(toks: List[str]) -> (str, int):
    # return (plate, index) of first found plate, else ("", -1)
    for i, t in enumerate(toks):
        if _is_plate(t):
            return t.upper(), i
    return "", -1

# =========================
# função principal: extrair_tudo_consumo
# =========================

def extrair_tudo_consumo(texto: str) -> Dict[str, Any]:
    """
    Extrai de forma robusta:
    - PLACA
    - MODELOS (lista)
    - COR
    - BLOCO, APARTAMENTO
    - NOME_RAW (possível nome completo)
    - STATUS
    - TEXTO_LIMPO (texto sem status)
    Retorna dicionário com keys (uppercase):
      { "TEXTO_LIMPO","COR","PLACA","BLOCO","APARTAMENTO","MODELOS","NOME_RAW","STATUS" }
    """
    original = (texto or "").strip()
    toks = tokens(original)
    toks_up = [t.upper() for t in toks]

    status, texto_sem_status = detectar_status(original)
    # recompute tokens without status words for some heuristics
    toks_ns = tokens(texto_sem_status)
    toks_ns_up = [t.upper() for t in toks_ns]

    placa, plate_idx = _extract_plate_and_indices(toks_up)

    bloco, apt = _find_block_ap(toks_up)

    modelos = _find_model_candidates(toks_up)
    # normalize/map modelos to canonical keys when possible and record their token indices to exclude from name
    modelos_mapped = []
    modelo_indices = set()
    if modelos:
        # modelos may be strings (from map keys) or heuristics (like 'JETA')
        for cand in modelos:
            canon = _map_to_canonical_model(str(cand))
            if canon and canon not in modelos_mapped:
                modelos_mapped.append(canon)
    else:
        modelos_mapped = []

    # ALSO, try to find model candidates near plate (again) and map them
    if plate_idx >= 0:
        # check previous token
        if plate_idx - 1 >= 0:
            p = toks_up[plate_idx - 1]
            if p.isalpha() and p.upper() not in _CORES_SET and p.upper() not in _STATUS_WORDS:
                cand = _map_to_canonical_model(p)
                if cand and cand not in modelos_mapped:
                    modelos_mapped.insert(0, cand)
        # check next token
        if plate_idx + 1 < len(toks_up):
            p2 = toks_up[plate_idx + 1]
            if p2.isalpha() and p2.upper() not in _CORES_SET and p2.upper() not in _STATUS_WORDS:
                cand = _map_to_canonical_model(p2)
                if cand and cand not in modelos_mapped:
                    modelos_mapped.append(cand)

    # dedupe modelos_mapped preserve order
    modelos_final = []
    for m in modelos_mapped:
        if m and m not in modelos_final:
            modelos_final.append(m)

    # find indices of tokens that correspond to model candidates (either exact match or normalized match)
    for i, t in enumerate(toks_up):
        tn = _normalize_token(t)
        for m in modelos_final:
            if tn == _normalize_token(m) or tn == _normalize_token(m[:4]) or m.upper().startswith(tn) or tn.startswith(_normalize_token(m)):
                modelo_indices.add(i)

    cores = _find_color_candidates(toks_up)
    cor = cores[0] if cores else ""

    # Name extraction: choose tokens that are alphabetic and not identified as other fields
    marked_indices = set()
    # mark plate index
    if plate_idx >= 0:
        marked_indices.add(plate_idx)
    # mark block/ap tokens indices
    for i,t in enumerate(toks_up):
        if re.match(r"^BL(?:OCO)?[-:]?\d+$", t) or (t.startswith("BL") and t[2:].isdigit()) or t=="BLOCO":
            marked_indices.add(i)
        if re.match(r"^AP(?:T|ARTAMENTO)?[-:]?\d+$", t) or (t.startswith("AP") and t[2:].isdigit()) or t in ("AP","APT","APTO","APARTAMENTO"):
            marked_indices.add(i)
    # mark status word indices and color/model tokens
    for i,t in enumerate(toks_up):
        if t in _STATUS_WORDS:
            marked_indices.add(i)
        if t in _CORES_SET:
            marked_indices.add(i)
        for modelo_key, abrevs in VEICULOS_MAP.items():
            if t == modelo_key.upper() or t in [a.upper() for a in abrevs]:
                marked_indices.add(i)
    # mark heuristic-detected model indices as well
    marked_indices.update(modelo_indices)

    # candidate name tokens (alphabetic, not marked)
    candidate_name_tokens = []
    for i,t in enumerate(toks_up):
        if i in marked_indices: continue
        # token should contain alphabetic characters
        if re.search(r"[A-ZÀ-ÖØ-öø-ÿ]", t) and not re.search(r"\d", t):
            candidate_name_tokens.append((i, t))

    # Build name_raw: choose contiguous sequence of up to 3 candidate tokens with likely person name
    name_raw = ""
    if candidate_name_tokens:
        seq = [t for i,t in candidate_name_tokens]
        # filter out common prepositions/particles
        stopwords = set(["DO","DA","DE","DOS","DAS","E","O","A","SR","SRA"])
        cleaned_seq = [t for t in seq if t.upper() not in stopwords]
        if cleaned_seq:
            top = cleaned_seq[:3]
            name_raw = " ".join([x.title() for x in top])
        else:
            name_raw = seq[0].title()
    else:
        name_raw = ""

    # Fallback: if there's a 'name-looking' block before block/ap token, use that
    if not name_raw:
        first_struct_idx = None
        for i,t in enumerate(toks_up):
            if i in marked_indices:
                first_struct_idx = i
                break
        if first_struct_idx:
            cand = [toks[j] for j in range(0, first_struct_idx) if toks[j].isalpha()]
            if cand:
                name_raw = " ".join([c.title() for c in cand[:3]])

    # TEXTO_LIMPO: original minus status word(s)
    texto_limpo = texto_sem_status.strip()
    if texto_limpo == "":
        texto_limpo = original

    return {
        "TEXTO_LIMPO": texto_limpo,
        "COR": cor.upper() if cor else "",
        "PLACA": placa.upper() if placa else "",
        "BLOCO": bloco,
        "APARTAMENTO": apt,
        "MODELOS": [m.upper() for m in modelos_final] if modelos_final else [],
        "NOME_RAW": name_raw.upper() if name_raw else "",
        "STATUS": status.upper() if status else "DESCONHECIDO"
    }
