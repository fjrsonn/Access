#!/usr/bin/env python3
# avisos.py — gera avisos a partir de analises.json e grava avisos.json
from datetime import datetime
import json
import os
import tempfile
import re
import shutil
import unicodedata
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALISES = os.path.join(BASE_DIR, "analises.json")
AVISOS = os.path.join(BASE_DIR, "avisos.json")

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
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            bak = f"{path}.corrupted.{ts}.bak"
            shutil.copy2(path, bak)
            print(f"[avisos] JSON corrompido em {path} — backup salvo em {bak}")
        except Exception:
            pass
        return None
    except Exception as e:
        print(f"[avisos] Erro ao ler {path}: {e}")
        return None

def _parse_datetime(s: str):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except:
            pass
    m = re.match(r"^(\d{2}/\d{2}/\d{4})\s*(\d{2}:\d{2}(:\d{2})?)?$", s)
    if m:
        date = m.group(1)
        timep = m.group(2) or "00:00:00"
        if len(timep.split(":")) == 2: timep += ":00"
        try:
            return datetime.strptime(f"{date} {timep}", "%d/%m/%Y %H:%M:%S")
        except:
            return None
    return None

ORD_MAP = {
    1: "PRIMEIRA", 2: "SEGUNDA", 3: "TERCEIRA", 4: "QUARTA", 5: "QUINTA",
    6: "SEXTA", 7: "SETIMA", 8: "OITAVA", 9: "NONA", 10: "DECIMA"
}
def ordinal_pt_upper(n):
    return ORD_MAP.get(n, f"{n}º".upper())

def _norm_field(v):
    return (v or "").strip().upper()

def _count_accesses(regs: List[dict]) -> int:
    return len(regs)

def _compare_fields(a: dict, b: dict, keys: List[str]):
    out = {}
    for k in keys:
        va = _norm_field(a.get(k)) if isinstance(a, dict) else ""
        vb = _norm_field(b.get(k)) if isinstance(b, dict) else ""
        out[k] = (va, vb, va == vb)
    return out

def _next_aviso_id(existing_avisos: List[dict]) -> str:
    if not existing_avisos:
        return "AVISO-000001"
    maxn = 0
    for a in existing_avisos:
        aid = a.get("id_aviso") or ""
        m = re.match(r"AVISO-(\d+)", aid)
        if m:
            try:
                v = int(m.group(1))
                if v > maxn: maxn = v
            except:
                pass
    return f"AVISO-{(maxn+1):06d}"

def _registro_event_id(rec: Dict[str, Any]) -> Any:
    if not isinstance(rec, dict):
        return None
    return rec.get("_entrada_id") or rec.get("ID") or rec.get("id")

def _aviso_exists(existing_avisos: List[dict], identidade: str, ultimo_id: Any, tipo: str) -> bool:
    for a in existing_avisos:
        if ( (a.get("identidade") or "").upper() == (identidade or "").upper() ):
            last = a.get("ultimo_registro") or {}
            if last and str(_registro_event_id(last) or "") == str(ultimo_id or "") and (a.get("tipo") or "") == (tipo or ""):
                return True
    return False

# -----------------------
# Helpers de normalização / comparação de veículo
# -----------------------
try:
    from rapidfuzz import fuzz as _rf_fuzz
except Exception:
    _rf_fuzz = None

def _norm_token(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^A-Za-z0-9]+", "", s).upper().strip()

def _plates_equal(p1: str, p2: str) -> bool:
    if not p1 or not p2:
        return False
    return _norm_token(p1) == _norm_token(p2)

def _models_similar(m1: str, m2: str, threshold: int = 85) -> bool:
    if not m1 and not m2:
        return True
    if not m1 or not m2:
        return False
    a = _norm_token(m1)
    b = _norm_token(m2)
    if a == b:
        return True
    if _rf_fuzz is not None:
        try:
            score = _rf_fuzz.WRatio(a, b)
            return score >= threshold
        except Exception:
            pass
    # fallback heuristics
    if a.startswith(b) or b.startswith(a):
        return True
    if abs(len(a) - len(b)) <= 1:
        return True
    return False

def _colors_similar(c1: str, c2: str) -> bool:
    a = _norm_token(c1); b = _norm_token(c2)
    if not a and not b:
        return True
    if not a or not b:
        return False
    return a == b

def vehicles_considered_same(rec_a: dict, rec_b: dict, fuzzy_threshold: int = 85) -> bool:
    """
    Decide se dois registros referem-se ao mesmo veículo.
    Regras (conservadoras):
     - Se ambos têm PLACA e são iguais -> same
     - Se ambos têm PLACA e diferentes -> different
     - Se ao menos uma placa falta -> comparar MODELO+COR com tolerância
     - Se um MODELO está ausente e o outro presente -> trate como *conservadoramente igual*
       (evita falsos positivos quando parser não extrai modelo)
    """
    p1 = (rec_a.get("PLACA") or "").strip()
    p2 = (rec_b.get("PLACA") or "").strip()
    if p1 and p2:
        return _plates_equal(p1, p2)

    m1 = (rec_a.get("MODELO") or "").strip()
    m2 = (rec_b.get("MODELO") or "").strip()
    c1 = (rec_a.get("COR") or "").strip()
    c2 = (rec_b.get("COR") or "").strip()

    # se ambos modelos ausentes -> comparar apenas cores (se possível) ou considerar igual
    if (not m1 or m1 in ("", "-")) and (not m2 or m2 in ("", "-")):
        return _colors_similar(c1, c2)

    # se um modelo ausente e outro presente -> conservadoramente tratar como igual (não sinalizar divergência)
    if (not m1 or m1 in ("", "-")) or (not m2 or m2 in ("", "-")):
        return True

    # ambos modelos presentes: comparar fuzzy + cores
    models_ok = _models_similar(m1, m2, threshold=fuzzy_threshold)
    colors_ok = _colors_similar(c1, c2)
    return models_ok and colors_ok

# -----------------------
# Mensagens: usam o STATUS do PRIMEIRO registro como "status verdadeiro"
# -----------------------
def _build_message_tipo1(primeiro, ultimo, entry, access_count: Optional[int] = None):
    status_true = (primeiro.get("STATUS") or "").strip().upper() or "MORADOR"
    n = (primeiro.get("NOME","") or "").strip().title()
    s = (primeiro.get("SOBRENOME","") or "").strip().title()
    b = ultimo.get("BLOCO","") or primeiro.get("BLOCO","")
    a = ultimo.get("APARTAMENTO","") or primeiro.get("APARTAMENTO","")
    count = access_count if access_count is not None else len(entry.get("registros", []) or [])
    vez = ordinal_pt_upper(count)
    dt = _parse_datetime(ultimo.get("DATA_HORA") or ultimo.get("data_hora") or "")
    data_str = dt.strftime("%d/%m/%Y") if dt else (ultimo.get("DATA_HORA") or "")
    hora_str = dt.strftime("%H:%M:%S") if dt else ""
    return f"{status_true} {n} {s}, DO BLOCO {b} APARTAMENTO {a}, ACESSOU O CONDOMINIO PELA {vez} VEZ, NA DATA {data_str}, HORARIO AS {hora_str}!"

def _build_message_tipo2(primeiro, ultimo, entry, access_count: Optional[int] = None):
    status_true = (primeiro.get("STATUS") or "").strip().upper() or "MORADOR"
    n = (primeiro.get("NOME","") or "").strip().title()
    s = (primeiro.get("SOBRENOME","") or "").strip().title()
    b = ultimo.get("BLOCO","") or primeiro.get("BLOCO","")
    a = ultimo.get("APARTAMENTO","") or primeiro.get("APARTAMENTO","")
    count = access_count if access_count is not None else len(entry.get("registros", []) or [])
    vez = ordinal_pt_upper(count)
    dt = _parse_datetime(ultimo.get("DATA_HORA") or ultimo.get("data_hora") or "")
    data_str = dt.strftime("%d/%m/%Y") if dt else (ultimo.get("DATA_HORA") or "")
    hora_str = dt.strftime("%H:%M:%S") if dt else ""
    return f"{status_true} {n} {s}, DO BLOCO {b} APARTAMENTO {a}, ACESSOU O CONDOMINIO PELA {vez} VEZ, NA DATA {data_str}, HORARIO AS {hora_str}, COM DADOS DIVERGENTES!"

def _build_message_tipo3(primeiro, ultimo, entry, access_count: Optional[int] = None):
    status_true = (primeiro.get("STATUS") or "").strip().upper() or "MORADOR"
    n = (primeiro.get("NOME","") or "").strip().title()
    s = (primeiro.get("SOBRENOME","") or "").strip().title()
    b = ultimo.get("BLOCO","") or primeiro.get("BLOCO","")
    a = ultimo.get("APARTAMENTO","") or primeiro.get("APARTAMENTO","")
    count = access_count if access_count is not None else len(entry.get("registros", []) or [])
    vez = ordinal_pt_upper(count)
    dt = _parse_datetime(ultimo.get("DATA_HORA") or ultimo.get("data_hora") or "")
    data_str = dt.strftime("%d/%m/%Y") if dt else (ultimo.get("DATA_HORA") or "")
    hora_str = dt.strftime("%H:%M:%S") if dt else ""
    return f"{status_true} {n} {s}, DO BLOCO {b} APARTAMENTO {a}, ACESSOU O CONDOMINIO PELA {vez} VEZ, NA DATA {data_str}, HORARIO AS {hora_str}, COM VEICULO DIVERGENTE!"

def build_avisos(analises_path: str = ANALISES, out_path: str = AVISOS) -> Dict[str, Any]:
    analises = _read_json(analises_path) or {"registros": []}
    avisos = _read_json(out_path) or {"registros": [], "ultimo_aviso_ativo": None}
    existing_list = avisos.get("registros", []) or []

    created = 0
    for entry in analises.get("registros", []) or []:
        regs = entry.get("registros", []) or []
        if len(regs) < 2:
            continue
        primeiro = regs[0]
        for idx in range(1, len(regs)):
            ultimo = regs[idx]
            access_count = idx + 1
            cmp_keys = ["NOME","SOBRENOME","BLOCO","APARTAMENTO","PLACA","MODELO","COR","STATUS"]
            comp = _compare_fields(primeiro, ultimo, cmp_keys)

            # nova lógica: usa vehicles_considered_same para evitar falsos positivos
            try:
                # se há qualquer informação de veículo, verificar se são considerados *o mesmo veículo*
                has_vehicle_info = bool((primeiro.get("PLACA") or "") or (ultimo.get("PLACA") or "") or (primeiro.get("MODELO") or "") or (ultimo.get("MODELO") or "") or (primeiro.get("COR") or "") or (ultimo.get("COR") or ""))
                if has_vehicle_info:
                    same_vehicle = vehicles_considered_same(primeiro, ultimo)
                    vehicle_div = not same_vehicle
                else:
                    vehicle_div = False
            except Exception:
                # fallback para comportamento antigo: checar diferenças em PLACA/MODELO/COR
                vehicle_keys = ["PLACA","MODELO","COR"]
                vehicle_div = any(not comp[k][2] and (comp[k][0] or comp[k][1]) for k in vehicle_keys)

            vehicle_keys = ["PLACA","MODELO","COR"]
            non_vehicle_div = any(not comp[k][2] and (comp[k][0] or comp[k][1]) for k in cmp_keys if k not in vehicle_keys)

            if vehicle_div:
                tipo = "PADRAO_3"
                nivel = "critical"
                bg_color = "#FF0000"
                txt = _build_message_tipo3(primeiro, ultimo, entry, access_count)
            elif non_vehicle_div:
                tipo = "PADRAO_2"
                nivel = "warn"
                bg_color = "#FFFF00"
                txt = _build_message_tipo2(primeiro, ultimo, entry, access_count)
            else:
                tipo = "PADRAO_1"
                nivel = "info"
                bg_color = "#FFFF00"
                txt = _build_message_tipo1(primeiro, ultimo, entry, access_count)

            ultimo_id = _registro_event_id(ultimo)
            identidade = entry.get("identidade") or ""

            # evita duplicar o MESMO evento (mesma identidade + mesmo ultimo_id + mesmo tipo)
            if _aviso_exists(existing_list, identidade, ultimo_id, tipo):
                continue

            id_aviso = _next_aviso_id(existing_list)
            aviso = {
                "id_aviso": id_aviso,
                "identidade": identidade,
                "tipo": tipo,
                "nivel": nivel,
                "mensagem": txt,
                "ui": {
                    "background_color": bg_color,
                    "opacity": 0.7,
                    "text_color": "#000000",
                    "icone": "⚠",
                    "exibir_botao_fechar": True
                },
                "referencias": {
                    "primeiro_registro_id": _registro_event_id(primeiro),
                    "ultimo_registro_id": ultimo_id,
                    "quantidade_acessos": access_count
                },
                "primeiro_registro": primeiro,
                "ultimo_registro": ultimo,
                "timestamps": {
                    "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "exibido_em": None,
                    "fechado_em": None
                },
                "status": {
                    "ativo": True,
                    "fechado_pelo_usuario": False
                }
            }
            existing_list.append(aviso)
            avisos["ultimo_aviso_ativo"] = id_aviso
            created += 1

    avisos["registros"] = existing_list
    # sempre gravar (mesmo vazio)
    try:
        atomic_save(out_path, avisos)
        print(f"[avisos] Gravado {out_path} — novos avisos criados: {created}, total avisos: {len(existing_list)}")
    except Exception as e:
        print(f"[avisos] Falha ao salvar {out_path}: {e}")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(avisos, f, ensure_ascii=False, indent=2)
        except Exception as e2:
            print(f"[avisos] Erro escrevendo direto: {e2}")
    return avisos

def build_avisos_for_identity(identity_key: str, analises_path: str = ANALISES, out_path: str = AVISOS) -> Dict[str, Any]:
    analises = _read_json(analises_path) or {"registros": []}
    avisos = _read_json(out_path) or {"registros": [], "ultimo_aviso_ativo": None}
    existing_list = avisos.get("registros", []) or []

    target = (identity_key or "").strip().upper()
    candidates = [e for e in analises.get("registros", []) if (e.get("identidade","") or "").upper() == target]
    created = 0
    for entry in candidates:
        regs = entry.get("registros", []) or []
        if len(regs) < 2:
            continue
        primeiro = regs[0]
        for idx in range(1, len(regs)):
            ultimo = regs[idx]
            access_count = idx + 1
            cmp_keys = ["NOME","SOBRENOME","BLOCO","APARTAMENTO","PLACA","MODELO","COR","STATUS"]
            comp = _compare_fields(primeiro, ultimo, cmp_keys)

            try:
                has_vehicle_info = bool((primeiro.get("PLACA") or "") or (ultimo.get("PLACA") or "") or (primeiro.get("MODELO") or "") or (ultimo.get("MODELO") or "") or (primeiro.get("COR") or "") or (ultimo.get("COR") or ""))
                if has_vehicle_info:
                    same_vehicle = vehicles_considered_same(primeiro, ultimo)
                    vehicle_div = not same_vehicle
                else:
                    vehicle_div = False
            except Exception:
                vehicle_keys = ["PLACA","MODELO","COR"]
                vehicle_div = any(not comp[k][2] and (comp[k][0] or comp[k][1]) for k in vehicle_keys)

            vehicle_keys = ["PLACA","MODELO","COR"]
            non_vehicle_div = any(not comp[k][2] and (comp[k][0] or comp[k][1]) for k in cmp_keys if k not in vehicle_keys)

            if vehicle_div:
                tipo = "PADRAO_3"; nivel="critical"; bg_color="#FF0000"; txt=_build_message_tipo3(primeiro, ultimo, entry, access_count)
            elif non_vehicle_div:
                tipo = "PADRAO_2"; nivel="warn"; bg_color="#FFFF00"; txt=_build_message_tipo2(primeiro, ultimo, entry, access_count)
            else:
                tipo = "PADRAO_1"; nivel="info"; bg_color="#FFFF00"; txt=_build_message_tipo1(primeiro, ultimo, entry, access_count)

            ultimo_id = _registro_event_id(ultimo)
            identidade = entry.get("identidade") or ""

            if _aviso_exists(existing_list, identidade, ultimo_id, tipo):
                continue

            id_aviso = _next_aviso_id(existing_list)
            aviso = {
                "id_aviso": id_aviso,
                "identidade": identidade,
                "tipo": tipo,
                "nivel": nivel,
                "mensagem": txt,
                "ui": {
                    "background_color": bg_color,
                    "opacity": 0.7,
                    "text_color": "#000000",
                    "icone": "⚠",
                    "exibir_botao_fechar": True
                },
                "referencias": {
                    "primeiro_registro_id": _registro_event_id(primeiro),
                    "ultimo_registro_id": ultimo_id,
                    "quantidade_acessos": access_count
                },
                "primeiro_registro": primeiro,
                "ultimo_registro": ultimo,
                "timestamps": {
                    "gerado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "exibido_em": None,
                    "fechado_em": None
                },
                "status": {
                    "ativo": True,
                    "fechado_pelo_usuario": False
                }
            }
            existing_list.append(aviso)
            avisos["ultimo_aviso_ativo"] = id_aviso
            created += 1

    avisos["registros"] = existing_list
    atomic_save(out_path, avisos)
    print(f"[avisos] build_avisos_for_identity('{identity_key}') criou: {created} novos avisos. total: {len(existing_list)}")
    return avisos

if __name__ == "__main__":
    print("[avisos] Executando build_avisos() inicial...")
    build_avisos()