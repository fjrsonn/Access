#!/usr/bin/env python3
# analises.py — agrupa registros de dadosend.json por identidade e grava analises.json
from datetime import datetime
import json
import os
import tempfile
import time
import re
import shutil
from typing import List, Dict, Any

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOSEND = os.path.join(BASE_DIR, "dadosend.json")
ENCOMENDASEND = os.path.join(BASE_DIR, "encomendasend.json")
ANALISES = os.path.join(BASE_DIR, "analises.json")

DATE_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")

def atomic_save(path: str, obj: Any):
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
            except: pass

def _read_json(path: str):
    if not os.path.exists(path):
        return None

    # Em ambientes com múltiplas threads/processos, pode haver leitura no meio da escrita.
    # Fazemos retries curtos antes de concluir corrupção para evitar falso positivo.
    last_raw = ""
    for attempt in range(5):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            if not raw or not raw.strip():
                return None
            return json.loads(raw)
        except json.JSONDecodeError:
            last_raw = raw if 'raw' in locals() else ""
            if attempt < 4:
                time.sleep(0.05)
                continue

            try:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                bak = f"{path}.corrupted.{ts}.bak"
                # salva exatamente o conteúdo inválido lido para diagnóstico fiel
                with open(bak, "w", encoding="utf-8") as bf:
                    bf.write(last_raw)
                print(f"[analises] JSON corrompido em {path} — backup salvo em {bak}")
            except Exception:
                pass
            return None
        except Exception as e:
            print(f"[analises] Erro ao ler {path}: {e}")
            return None
    return None

def _parse_datetime(s: str):
    if not s:
        return None
    s = str(s).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    # try loose matching dd/mm/yyyy [hh:mm[:ss]]
    m = re.match(r"^(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2}(:\d{2})?)?$", s)
    if m:
        date = m.group(1)
        timep = m.group(2) or "00:00:00"
        if len(timep.split(":")) == 2:
            timep += ":00"
        try:
            return datetime.strptime(f"{date} {timep}", "%d/%m/%Y %H:%M:%S")
        except Exception:
            return None
    return None

def _identity_key(rec: dict) -> str:
    nome = (rec.get("NOME","") or "").strip().upper()
    sobrenome = (rec.get("SOBRENOME","") or "").strip().upper()
    bloco = (rec.get("BLOCO","") or "").strip().upper()
    ap = (rec.get("APARTAMENTO","") or "").strip().upper()
    return f"{nome}|{sobrenome}|{bloco}|{ap}"

def _encomenda_bloco_ap_key(rec: dict) -> str:
    bloco = (rec.get("BLOCO","") or "").strip().upper()
    ap = (rec.get("APARTAMENTO","") or "").strip().upper()
    return f"{bloco}|{ap}"

def load_encomendas(path: str = ENCOMENDASEND) -> List[dict]:
    d = _read_json(path)
    if not d:
        return []
    if isinstance(d, dict) and "registros" in d:
        regs = d.get("registros") or []
    elif isinstance(d, list):
        regs = d
    else:
        regs = []
    if not isinstance(regs, list):
        regs = list(regs)
    return regs

def _build_encomendas_analises(encomendas_path: str = ENCOMENDASEND, min_group_size: int = 1) -> List[Dict[str, Any]]:
    regs = load_encomendas(encomendas_path)
    groups = {}
    for r in regs:
        key = _encomenda_bloco_ap_key(r)
        bloco, ap = key.split("|", 1)
        if not bloco or not ap:
            continue
        groups.setdefault(key, []).append(r)

    out = []
    for key, items in groups.items():
        sem_contato = []
        sem_status = []

        for rec in items:
            status = (rec.get("STATUS_ENCOMENDA") or "").strip().upper()
            if status == "AVISADO":
                continue
            if status == "SEM CONTATO":
                sem_contato.append(rec)
            else:
                sem_status.append(rec)

        def _dt_or_min(rec):
            dt = _parse_datetime(rec.get("DATA_HORA") or rec.get("data_hora") or "")
            return dt or datetime.min

        bloco, ap = key.split("|", 1)

        if len(sem_contato) >= min_group_size:
            sem_contato_sorted = sorted(sem_contato, key=_dt_or_min)
            out.append({
                "identidade": f"ENCOMENDA|{bloco}|{ap}|SEM_CONTATO",
                "tipo_analise": "ENCOMENDAS_MULTIPLAS_BLOCO_APARTAMENTO",
                "origem_status": "SEM_CONTATO",
                "bloco": bloco,
                "apartamento": ap,
                "quantidade": len(sem_contato_sorted),
                "registros": sem_contato_sorted,
            })

        if len(sem_status) >= min_group_size:
            sem_status_sorted = sorted(sem_status, key=_dt_or_min)
            out.append({
                "identidade": f"ENCOMENDA|{bloco}|{ap}|SEM_STATUS",
                "tipo_analise": "ENCOMENDAS_MULTIPLAS_BLOCO_APARTAMENTO",
                "origem_status": "SEM_STATUS",
                "bloco": bloco,
                "apartamento": ap,
                "quantidade": len(sem_status_sorted),
                "registros": sem_status_sorted,
            })
    return out

def load_dadosend(path: str = DADOSEND) -> List[dict]:
    d = _read_json(path)
    if not d:
        return []
    if isinstance(d, dict) and "registros" in d:
        regs = d.get("registros") or []
    elif isinstance(d, list):
        regs = d
    else:
        regs = []
    # ensure list
    if not isinstance(regs, list):
        regs = list(regs)
    return regs

def build_analises(dadosend_path: str = DADOSEND, out_path: str = ANALISES, min_group_size: int = 2) -> Dict[str, Any]:
    """
    Varre dadosend.json, agrupa por identidade e grava analises.json com grupos
    que têm >= min_group_size registros (por padrão 2).
    Sempre grava analises.json (mesmo se vazio).
    """
    print(f"[analises] Lendo {dadosend_path}")
    regs = load_dadosend(dadosend_path)
    groups = {}
    for r in regs:
        key = _identity_key(r)
        groups.setdefault(key, []).append(r)

    out = {"registros": [], "encomendas_multiplas_bloco_apartamento": []}
    for key, items in groups.items():
        if len(items) < min_group_size:
            continue
        # ordenar por DATA_HORA asc (se parsing falhar, datetime.min)
        def _dt_or_min(rec):
            dt = _parse_datetime(rec.get("DATA_HORA") or rec.get("data_hora") or "")
            return dt or datetime.min
        items_sorted = sorted(items, key=_dt_or_min)
        # split identidade safely (tem 4 partes)
        parts = key.split("|")
        while len(parts) < 4:
            parts.append("")
        nome, sobrenome, bloco, ap = parts[0:4]
        out_entry = {
            "identidade": key,
            "nome": nome.title() if nome else "",
            "sobrenome": sobrenome.title() if sobrenome else "",
            "bloco": bloco,
            "apartamento": ap,
            "registros": items_sorted
        }
        out["registros"].append(out_entry)

    out["encomendas_multiplas_bloco_apartamento"] = _build_encomendas_analises(ENCOMENDASEND, 1)

    try:
        atomic_save(out_path, out)
        print(f"[analises] Gravado {out_path} com {len(out.get('registros', []))} grupos.")
    except Exception as e:
        print(f"[analises] Falha ao salvar {out_path}: {e}")
        # ainda tentar escrever diretamente
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
        except Exception as e2:
            print(f"[analises] Erro escrevendo direto: {e2}")
    return out

def build_analises_for_identity(identity_key: str, dadosend_path: str = DADOSEND, out_path: str = ANALISES) -> Dict[str, Any]:
    regs = load_dadosend(dadosend_path)
    ident = (identity_key or "").strip().upper()
    items = [r for r in regs if _identity_key(r) == ident]
    existing = _read_json(out_path) or {"registros": [], "encomendas_multiplas_bloco_apartamento": []}
    others = [e for e in existing.get("registros", []) if (e.get("identidade","") or "").upper() != ident]
    if not items:
        existing["registros"] = others
        existing["encomendas_multiplas_bloco_apartamento"] = _build_encomendas_analises(ENCOMENDASEND, 1)
        atomic_save(out_path, existing)
        return existing
    def _dt_or_min(rec):
        dt = _parse_datetime(rec.get("DATA_HORA") or rec.get("data_hora") or "")
        return dt or datetime.min
    items_sorted = sorted(items, key=_dt_or_min)
    nome, sobrenome, bloco, ap = ident.split("|")
    new_entry = {
        "identidade": ident,
        "nome": nome.title() if nome else "",
        "sobrenome": sobrenome.title() if sobrenome else "",
        "bloco": bloco,
        "apartamento": ap,
        "registros": items_sorted
    }
    others.append(new_entry)
    existing["registros"] = others
    existing["encomendas_multiplas_bloco_apartamento"] = _build_encomendas_analises(ENCOMENDASEND, 1)
    atomic_save(out_path, existing)
    return existing

if __name__ == "__main__":
    print("[analises] Executando build_analises() inicial...")
    build_analises()
