import re
import unicodedata

# =========================
# NORMALIZAÇÃO
# =========================
def normalizar(txt):
    if not txt:
        return ""
    txt = txt.upper().strip()
    txt = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in txt if not unicodedata.combining(c))


# =========================
# STATUS
# =========================
STATUS_MAP = {
    "VISITANTE": ["VIS", "VISIT", "VISI", "VST", "V", "VISITANTE"],
    "MORADOR": ["MOR", "MORA", "MORAD", "M", "MORADOR"],
    "PRESTADOR DE SERVIÇO": ["PREST", "PRES", "SERV", "FUNC", "FORN", "TERC", "PR", "P", "PRESTADOR DE SERVIÇO"]
}

def extrair_status(texto):
    t = normalizar(texto)
    for status, termos in STATUS_MAP.items():
        for termo in termos:
            if re.search(rf"\b{re.escape(termo)}\b", t):
                return status
    return "DESCONHECIDO"

def remover_status(texto):
    t = texto
    for termos in STATUS_MAP.values():
        for termo in termos:
            t = re.sub(rf"\b{re.escape(termo)}\b", "", t, flags=re.IGNORECASE)
    return t.strip()


# =========================
# ENDEREÇO / PLACA
# =========================
def extrair_endereco(texto):
    t = normalizar(texto)

    bloco = ""
    ap = ""
    placa = ""

    m = re.search(r"\b(BLOCO|BL|B)\s*(\d+)\b", t)
    if m:
        bloco = m.group(2)

    m = re.search(r"\b(APARTAMENTO|AP|A)\s*(\d+)\b", t)
    if m:
        ap = m.group(2)

    m = re.search(r"\b[A-Z]{3}\d{4}\b", t)
    if m:
        placa = m.group(0)

    return {"BLOCO": bloco, "APARTAMENTO": ap, "PLACA": placa}


# =========================
# VEÍCULOS
# =========================
VEICULOS_MAP = {
    "ONIX": ["ONIX","ONI","ONX","ONICS","ONIX LT","ONIX PLUS"],
    "CORSA": ["CORSA","COR","CRSA","CORZA"],
    "CRUZE": ["CRUZE","CRUZ","CRUS","CRZE"],
    "CELTA": ["CELTA","CELT","CLTA"],
    "PRISMA": ["PRISMA","PRISM","PRZMA"],
    "SPIN": ["SPIN","SPN"],
    "S10": ["S10","S-10","S 10"],
    "CLASSIC": ["CLASSIC","CLASIC","CLSIC"],
    "VIRTUS": ["VIRTUS","VIRT","VIRTS","VIR"],
    "POLO": ["POLO","POL","PLO","POLL"],
    "GOL": ["GOL","GOOL","GL"],
    "JETTA": ["JETTA","JET","JETA","JTA"],
    "SAVEIRO": ["SAVEIRO","SAVEIR","SAVERO"],
    "VOYAGE": ["VOYAGE","VOIAGE","VYAGE"],
    "FOX": ["FOX","FOXX"],
    "UP": ["UP","UP!"],
    "MOBI": ["MOBI","MOB","MBI","MOBBY"],
    "UNO": ["UNO","UN","UUNO"],
    "ARGO": ["ARGO","ARG","AROG"],
    "PALIO": ["PALIO","PAL","PLIO"],
    "SIENA": ["SIENA","SENA","SINA"],
    "STRADA": ["STRADA","STRD","STRDA"],
    "TORO": ["TORO","TOR","TRO"],
    "CRONOS": ["CRONOS","CRONO","CRNS"],
    "IDEA": ["IDEA","IDA"],
    "HB20": ["HB20","HB 20","H B 20","HB2O","HB-20"],
    "CRETA": ["CRETA","CRET","CRTA"],
    "IX35": ["IX35","IX 35","I X 35"],
    "KA": ["KA","KÁ","K","FORD KA"],
    "FIESTA": ["FIESTA","FIEST","FSTA"],
    "ECOSPORT": ["ECOSPORT","ECO","ECOSP","ECOS"],
    "RANGER": ["RANGER","RANGR"],
    "COROLLA": ["COROLLA","COROLA","CORLLA"],
    "ETIOS": ["ETIOS","ETIO","ETIUS"],
    "HILUX": ["HILUX","HILUXX","HLUX"],
    "YARIS": ["YARIS","YRS","IARIS"],
    "CIVIC": ["CIVIC","CIV","CIVIK","CIVC"],
    "FIT": ["FIT","FITT"],
    "HRV": ["HRV","H-RV","H R V"],
    "CITY": ["CITY","CTY"],
    "SANDERO": ["SANDERO","SAND","SNDR"],
    "LOGAN": ["LOGAN","LOG","LAGN"],
    "KWID": ["KWID","KWD","QUID"],
    "DUSTER": ["DUSTER","DUST","DSTR"],
}

def separar_modelos(texto):
    t = normalizar(texto)
    encontrados = []

    for modelo, abrevs in VEICULOS_MAP.items():
        for ab in abrevs:
            if re.search(rf"\b{re.escape(ab)}\b", t):
                encontrados.append(modelo)
                t = re.sub(rf"\b{re.escape(ab)}\b", "", t)
                break

    return t.strip(), encontrados


# =========================
# CORES
# =========================
COR_MAP = {
    "PRET": "PRETO",
    "PRETO": "PRETO",
    "PRAT": "PRATA",
    "PRATA": "PRATA",
    "BRANC": "BRANCO",
    "BRANCO": "BRANCO",
    "CHUMB": "CHUMBO",
    "CHUMBO": "CHUMBO",
    "CINZ": "CINZA",
    "CINZA": "CINZA",
    "VERMEL": "VERMELHO",
    "VERMELHO": "VERMELHO"
}

def extrair_cor(texto):
    t = normalizar(texto)
    for bruto, normal in COR_MAP.items():
        if re.search(rf"\b{re.escape(bruto)}\b", t):
            return normal.title()
    return ""


# =========================
# NOME
# =========================
NOME_MAP = {
    "JAOA": "JOAO",
    "OLIEIRA": "OLIVEIRA",
    "MARIA": "MARIA",
    "APARECIDA": "APARECIDA",
    "HENRIQUE": "HENRIQUE",
    "CAIO": "CAIO",
    "ANA": "ANA",
    "JULIA": "JULIA",
    "JORGE": "JORGE",
}

# Termos a remover do nome
RESIDUAIS = (
    ["BLOCO","BL","B","APARTAMENTO","AP","A","PLACA"] +
    [ab.upper() for abrevs in VEICULOS_MAP.values() for ab in abrevs] +
    [c.upper() for c in COR_MAP.keys()] +
    [s.upper() for termos in STATUS_MAP.values() for s in termos]
)

def limpar_texto_nome(texto):
    t = normalizar(texto)
    for termo in RESIDUAIS:
        t = re.sub(rf"\b{re.escape(termo)}\b", "", t, flags=re.IGNORECASE)
    # remove números isolados
    t = re.sub(r"\b\d+\b", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()

def corrigir_nome(texto):
    if not texto:
        return ""
    t = limpar_texto_nome(texto)
    tokens = [NOME_MAP.get(n.upper(), n) for n in t.split()]
    return " ".join(tokens).title() if tokens else "-"
