# interfacetwo.py — monitor (suporta modo embutido via create_monitor_toplevel)
"""
Monitor de dados:
- Pode ser embutido via create_monitor_toplevel(master)
- Ou executado standalone (python interfacetwo.py)
"""

import os
import json
import tempfile
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import re
import hashlib

from ui_theme import (
    UI_THEME,
    build_card_frame,
    build_primary_button,
    build_secondary_button,
    build_filter_input,
    bind_focus_ring,
    bind_button_states,
)

try:
    from text_classifier import build_structured_fields, log_audit_event
except Exception:
    build_structured_fields = None
    log_audit_event = None


try:
    from runtime_status import get_last_status, report_status
except Exception:
    def get_last_status():
        return {}
    def report_status(*args, **kwargs):
        return None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(BASE_DIR, "dadosend.json")
ENCOMENDAS_ARQUIVO = os.path.join(BASE_DIR, "encomendasend.json")
ORIENTACOES_ARQUIVO = os.path.join(BASE_DIR, "orientacoes.json")
OBSERVACOES_ARQUIVO = os.path.join(BASE_DIR, "observacoes.json")
ANALISES_ARQUIVO = os.path.join(BASE_DIR, "analises.json")
AVISOS_ARQUIVO = os.path.join(BASE_DIR, "avisos.json")
LOCK_FILE = os.path.join(BASE_DIR, "monitor.lock")
REFRESH_MS = 2000  # 2s

# internal reference to Toplevel (quando embutido)
_monitor_toplevel = None
_monitor_after_id = None
_filter_state = {}
_monitor_sources = {}
_hover_state = {}
_encomenda_display_map = {}
_encomenda_tag_map = {}
_encomenda_line_map = {}
_encomenda_action_ui = {}
_text_action_ui = {}
_record_tag_map_generic = {}
_text_edit_lock = set()
_filter_controls = {}
_control_table_map = {}
_control_details_var = {}
_control_sort_state = {}
_control_selection_state = {}


# ---------- inferência MODELO/COR (fallback a partir de 'texto') ----------
_STATUS_WORDS = set(["MORADOR","MORADORES","VISITANTE","VISITA","VISIT","PRESTADOR","PRESTADORES","SERVICO","SERVIÇO","TECNICO","DESCONHECIDO","FUNCIONARIO","FUNCIONÁRIO"])

def _tokens(text):
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9\-]+", str(text or ""))

def _infer_model_color_from_text(text: str):
    if not text or not isinstance(text, str):
        return ("", "")
    toks = _tokens(text)
    toks_up = [t.upper() for t in toks]
    plate_idx = None
    for i, t in enumerate(toks_up):
        if re.match(r"^[A-Z]{3}\d{4}$", t):
            plate_idx = i
            break
        if re.match(r"^[A-Z0-9]{5,8}$", t) and re.search(r"\d", t):
            plate_idx = i
            break
    if plate_idx is None:
        return ("", "")
    following = []
    for tok in toks_up[plate_idx+1:]:
        if tok in _STATUS_WORDS:
            break
        following.append(tok)
    modelo = ""
    cor = ""
    if following:
        filtered = [t for t in following if not re.match(r"^BL\d+$", t) and not re.match(r"^AP\d+$", t)]
        if filtered:
            modelo = filtered[0].title()
            if len(filtered) > 1:
                for tok in filtered[1:4]:
                    if re.search(r"[A-Za-z]", tok):
                        cor = tok.title()
                        break
    return (modelo or "", cor or "")

# ---------- safe IO ----------
def _load_safe(path: str):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "registros" in data:
                return data.get("registros", [])
            if isinstance(data, list):
                return data
            return data.get("registros", []) if isinstance(data, dict) else []
    except json.JSONDecodeError:
        print(f"[interfacetwo] JSON inválido em {path}; usando fallback sem criar .corrupted")
        return []
    except Exception:
        return []

def _atomic_write(path: str, obj):
    dirn = os.path.dirname(path) or "."
    os.makedirs(dirn, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dirn, prefix=".tmp_", suffix=".json", delete=False) as tf:
            tmp = tf.name
            json.dump(obj, tf, ensure_ascii=False, indent=4)
            tf.flush()
        os.replace(tmp, path)
    except Exception:
        if tmp and os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception: pass
        raise

def safe(v):
    return v if v and v != "-" else "-"

def format_line(r: dict) -> str:
    modelo = r.get("MODELO") or ""
    cor = r.get("COR") or ""
    if (not modelo or modelo == "-") or (not cor or cor == "-"):
        texto = r.get("texto") or r.get("texto_original") or ""
        inf_mod, inf_cor = _infer_model_color_from_text(texto)
        if not modelo and inf_mod:
            modelo = inf_mod
        if not cor and inf_cor:
            cor = inf_cor

    return (
        f"{safe(r.get('DATA_HORA'))} | "
        f"{safe(r.get('NOME'))} {safe(r.get('SOBRENOME'))} | "
        f"BLOCO {safe(r.get('BLOCO'))} APARTAMENTO {safe(r.get('APARTAMENTO'))} | "
        f"PLACA {safe(r.get('PLACA'))} | "
        f"{safe(modelo)} | "
        f"{safe(cor)} | "
        f"{safe(r.get('STATUS'))}"
    )

def _split_date_time(data_hora: str):
    parts = (data_hora or "").strip().split()
    if len(parts) >= 2:
        return parts[0], parts[1]
    if len(parts) == 1:
        return parts[0], ""
    return "", ""

def _status_phrase(status: str) -> str:
    s = (status or "").strip().lower()
    if not s or s == "-":
        return "registrado"
    if "morador" in s:
        return "morador"
    if "visit" in s:
        return "visitante"
    if "prestador" in s or "servi" in s or "tecnico" in s:
        return "prestador de serviço"
    if "funcion" in s:
        return "funcionário"
    return s

def _title_name(*parts):
    joined = " ".join(p for p in parts if p and p != "-").strip()
    return joined.title() if joined else "Visitante"

def _record_hash_key(r: dict) -> str:
    raw = "|".join([
        str(r.get("DATA_HORA", "")),
        str(r.get("NOME", "")),
        str(r.get("SOBRENOME", "")),
        str(r.get("BLOCO", "")),
        str(r.get("APARTAMENTO", "")),
        str(r.get("PLACA", "")),
        str(r.get("MODELO", "")),
        str(r.get("COR", "")),
        str(r.get("STATUS", "")),
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def format_creative_entry(r: dict) -> str:
    modelo = r.get("MODELO") or ""
    cor = r.get("COR") or ""
    if (not modelo or modelo == "-") or (not cor or cor == "-"):
        texto = r.get("texto") or r.get("texto_original") or ""
        inf_mod, inf_cor = _infer_model_color_from_text(texto)
        if not modelo and inf_mod:
            modelo = inf_mod
        if not cor and inf_cor:
            cor = inf_cor

    data_hora = safe(r.get("DATA_HORA"))
    data, hora = _split_date_time(data_hora)
    nome = _title_name(r.get("NOME", ""), r.get("SOBRENOME", ""))
    bloco = safe(r.get("BLOCO"))
    ap = safe(r.get("APARTAMENTO"))
    placa = safe(r.get("PLACA")).upper()
    status = _status_phrase(r.get("STATUS"))
    modelo_fmt = safe(modelo).title()
    cor_fmt = safe(cor).lower()

    templates = [
        "Às {hora} do dia {data}, {nome}, {status}, acessou o local conduzindo um {modelo} {cor}, placa {placa}.",
        "Em {data} às {hora}, {nome}, {status}, chegou ao Bloco {bloco}, Apartamento {ap}, em um {modelo} {cor}, placa {placa}.",
        "Pouco antes, às {hora} de {data}, {nome}, {status}, entrou no Bloco {bloco}, Apartamento {ap}, dirigindo um {modelo} {cor}, placa {placa}.",
        "Às {hora} de {data}, {nome}, {status}, acessou o Bloco {bloco}, Apartamento {ap}, com um {modelo} {cor}, placa {placa}.",
    ]
    key = _record_hash_key(r)
    idx = int(key[:2], 16) % len(templates)
    return templates[idx].format(
        hora=hora or "-",
        data=data or "-",
        nome=nome,
        status=status,
        bloco=bloco,
        ap=ap,
        placa=placa,
        modelo=modelo_fmt or "-",
        cor=cor_fmt or "-",
    )

def _record_hash_key_encomenda(r: dict) -> str:
    raw = "|".join([
        str(r.get("DATA_HORA", "")),
        str(r.get("NOME", "")),
        str(r.get("SOBRENOME", "")),
        str(r.get("BLOCO", "")),
        str(r.get("APARTAMENTO", "")),
        str(r.get("TIPO", "")),
        str(r.get("LOJA", "")),
        str(r.get("IDENTIFICACAO", "")),
    ])
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def format_encomenda_entry(r: dict) -> str:
    data_hora = safe(r.get("DATA_HORA"))
    data, hora = _split_date_time(data_hora)
    nome = _title_name(r.get("NOME", ""), r.get("SOBRENOME", ""))
    bloco = safe(r.get("BLOCO"))
    ap = safe(r.get("APARTAMENTO"))
    tipo = safe(r.get("TIPO")).lower()
    loja = safe(r.get("LOJA")).title()
    identificacao = safe(r.get("IDENTIFICACAO"))

    templates = [
        "Às {hora} do dia {data}, chegou uma {tipo} da {loja} destinada a {nome}, moradora do bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "Foi registrada às {hora} de {data} a chegada de uma {tipo} da {loja} para {nome}, do bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "No dia {data}, às {hora}, uma entrega da {loja} foi recebida para {nome}, residente no bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "Encomenda da {loja} entregue às {hora} em {data} para {nome}, bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "Às {hora} do dia {data}, foi entregue uma {tipo} da {loja} para {nome}, localizada no bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "Registro de entrega: {tipo} da {loja} destinada a {nome}, bloco {bloco}, apartamento {ap}, recebida às {hora} de {data}, identificação {identificacao}.",
        "Em {data}, às {hora}, uma {tipo} da {loja} chegou para {nome}, moradora do bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "Às {hora} do dia {data} houve a entrega de uma {tipo} da {loja} para {nome}, bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "Entrega realizada às {hora} em {data}: {tipo} da {loja} para {nome}, residente no bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
        "Uma {tipo} da {loja} foi registrada às {hora} de {data} para {nome}, do bloco {bloco}, apartamento {ap}, identificação {identificacao}.",
    ]
    status = safe(r.get("STATUS_ENCOMENDA"))
    status_dh = safe(r.get("STATUS_DATA_HORA"))
    key = _record_hash_key_encomenda(r)
    idx = int(key[:2], 16) % len(templates)
    base_text = templates[idx].format(
        hora=hora or "-",
        data=data or "-",
        tipo=tipo or "encomenda",
        loja=loja or "-",
        nome=nome,
        bloco=bloco,
        ap=ap,
        identificacao=identificacao,
    )
    if status not in ("-", ""):
        status_up = status.strip().upper()
        if status_up == "AVISADO":
            prefix = "[AVISADO ✅]"
        elif status_up == "SEM CONTATO":
            prefix = "[SEM CONTATO ⚠]"
        else:
            prefix = f"[{status_up}]"
        return f"{base_text} — {prefix} {status_dh}"
    return base_text

# ---------- UI helpers (embutido) ----------


def _extract_multi_fields(text: str) -> dict:
    if build_structured_fields:
        strict, inferred = build_structured_fields(text)
        return {k: list(dict.fromkeys((strict.get(k, []) + inferred.get(k, [])))) for k in strict.keys()}
    return {
        "BLOCO": [], "APARTAMENTO": [], "NOME": [], "SOBRENOME": [],
        "HORARIO": [], "VEICULO": [], "COR": [], "PLACA": []
    }



def format_orientacao_entry(r: dict) -> str:
    return str(r.get("texto") or r.get("texto_original") or "")

def format_observacao_entry(r: dict) -> str:
    return str(r.get("texto") or r.get("texto_original") or "")

def _normalize_date_value(value: str):
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

def _normalize_time_value(value: str):
    if not value:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None

def _parse_data_hora(value: str):
    if not value:
        return None
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None

def _record_matches_query(record: dict, query: str) -> bool:
    if not query:
        return True
    needle = query.strip().lower()
    if not needle:
        return True
    haystack_parts = []
    for key, value in record.items():
        if value is None:
            continue
        haystack_parts.append(str(value))
    haystack = " ".join(haystack_parts).lower()
    return needle in haystack

def _apply_filters(registros, filters):
    if not filters:
        return registros
    order = filters.get("order", "Mais recentes")
    date_mode = filters.get("date_mode", "Mais recentes")
    date_value = filters.get("date_value", "")
    time_mode = filters.get("time_mode", "Mais recentes")
    time_value = filters.get("time_value", "")
    query = filters.get("query", "")
    status_filter = (filters.get("status", "Todos") or "Todos").strip().upper()
    bloco_filter = (filters.get("bloco", "Todos") or "Todos").strip().upper()

    normalized_date = _normalize_date_value(date_value) if date_mode == "Específica" else None
    normalized_time = _normalize_time_value(time_value) if time_mode == "Específica" else None

    filtrados = []
    for r in registros:
        data_hora = r.get("DATA_HORA", "")
        data_str, hora_str = _split_date_time(data_hora)
        record_date = _normalize_date_value(data_str)
        record_time = _normalize_time_value(hora_str)

        if normalized_date and record_date != normalized_date:
            continue
        if normalized_time and record_time != normalized_time:
            continue
        if not _record_matches_query(r, query):
            continue
        record_status = (safe(r.get("STATUS") if r.get("STATUS") is not None else r.get("STATUS_ENCOMENDA")) or "-").strip().upper()
        record_bloco = (safe(r.get("BLOCO")) or "-").strip().upper()
        if status_filter != "TODOS" and record_status != status_filter:
            continue
        if bloco_filter != "TODOS" and record_bloco != bloco_filter:
            continue
        filtrados.append(r)

    def sort_key(record):
        parsed = _parse_data_hora(record.get("DATA_HORA", ""))
        return parsed or datetime.min

    reverse = True if order == "Mais recentes" else False
    filtrados.sort(key=sort_key, reverse=reverse)
    return filtrados

# ---------- novo helper: handler quando tag de encomenda for clicada ----------
def _encomenda_on_tag_click(text_widget, record, event=None, rec_tag=None):
    """
    Handler chamado a partir de tag_bind para o registro clicado.
    Atualiza o UI de ações associado ao text_widget e mostra o frame de ações.
    Também destaca visualmente o registro selecionado.
    """
    ui = _encomenda_action_ui.get(text_widget)
    if not ui:
        return
    current = ui.get("current")
    if current is None:
        current = {"record": None, "rec_tag": None}
        ui["current"] = current
    current["record"] = record
    current["rec_tag"] = rec_tag

    # highlight selected record visually
    try:
        # remove old highlight
        text_widget.config(state="normal")
        text_widget.tag_remove("encomenda_selected", "1.0", tk.END)
        if rec_tag:
            ranges = text_widget.tag_ranges(rec_tag)
            if ranges and len(ranges) >= 2:
                text_widget.tag_add("encomenda_selected", ranges[0], ranges[1])
        text_widget.config(state="disabled")
    except Exception:
        try:
            text_widget.tag_remove("encomenda_selected", "1.0", tk.END)
        except Exception:
            pass

    show_fn = ui.get("show")
    if callable(show_fn):
        show_fn()

def _record_on_tag_click(text_widget, record, event=None, rec_tag=None):
    ui = _text_action_ui.get(text_widget) or _encomenda_action_ui.get(text_widget)
    if not ui:
        return
    is_editing = ui.get("is_editing")
    if callable(is_editing) and is_editing():
        return
    current = ui.get("current") or {"record": None, "rec_tag": None}
    ui["current"] = current
    current["record"] = record
    current["rec_tag"] = rec_tag
    show_fn = ui.get("show")
    if callable(show_fn):
        show_fn()

def _format_control_row(record: dict):
    nome = _title_name(record.get("NOME", ""), record.get("SOBRENOME", ""))
    return (
        safe(record.get("DATA_HORA")),
        nome,
        f"{safe(record.get('BLOCO'))}/{safe(record.get('APARTAMENTO'))}",
        safe(record.get("PLACA")).upper(),
        safe(record.get("STATUS")),
    )




def _control_sort_value(record: dict, sort_key: str):
    if sort_key == "data_hora":
        return _parse_data_hora(record.get("DATA_HORA", "")) or datetime.min
    if sort_key == "nome":
        return _title_name(record.get("NOME", ""), record.get("SOBRENOME", "")).upper()
    if sort_key == "bloco_ap":
        return f"{safe(record.get('BLOCO'))}/{safe(record.get('APARTAMENTO'))}"
    if sort_key == "placa":
        return safe(record.get("PLACA")).upper()
    if sort_key == "status":
        return safe(record.get("STATUS")).upper()
    return str(record.get(sort_key, ""))


def _update_control_details(tree_widget, selection):
    details_var = _control_details_var.get(tree_widget)
    record_map = _control_table_map.get(tree_widget, {})
    if details_var is None:
        return
    if not selection:
        details_var.set("Selecione um registro para ver detalhes.")
        return
    rec = record_map.get(selection[0])
    _control_selection_state[tree_widget] = str((rec or {}).get("ID") or (rec or {}).get("_entrada_id") or "")
    if not rec:
        details_var.set("Selecione um registro para ver detalhes.")
        return
    details_var.set(
        f"Nome: {_title_name(rec.get('NOME',''), rec.get('SOBRENOME',''))}\n"
        f"Bloco/AP: {safe(rec.get('BLOCO'))}/{safe(rec.get('APARTAMENTO'))}\n"
        f"Placa: {safe(rec.get('PLACA')).upper()}\n"
        f"Modelo/Cor: {safe(rec.get('MODELO'))} / {safe(rec.get('COR'))}\n"
        f"Status: {safe(rec.get('STATUS'))}\n"
        f"Data/Hora: {safe(rec.get('DATA_HORA'))}"
    )


def _populate_control_table(tree_widget, info_label):
    source = _monitor_sources.get(tree_widget, {})
    arquivo = source.get("path", ARQUIVO)
    registros = _load_safe(arquivo)
    filter_key = source.get("filter_key", tree_widget)
    filters = _filter_state.get(filter_key, {})
    filtrados = _apply_filters(registros, filters)

    sort_state = _control_sort_state.get(tree_widget, {"key": "data_hora", "reverse": True})
    sort_key = sort_state.get("key", "data_hora")
    reverse = bool(sort_state.get("reverse", True))
    filtrados = sorted(filtrados, key=lambda rec: _control_sort_value(rec, sort_key), reverse=reverse)

    last = get_last_status()
    status_hint = ""
    if last:
        status_hint = f" | último status: {last.get('action','-')}:{last.get('status','-')}"
    info_label.config(text=f"Arquivo: {arquivo} — registros: {len(filtrados)} (de {len(registros)}){status_hint}")

    selected_record = _control_selection_state.get(tree_widget)
    for iid in tree_widget.get_children():
        tree_widget.delete(iid)

    record_map = {}
    selected_iid = None
    for idx, rec in enumerate(filtrados):
        iid = f"row_{idx}"
        tree_widget.insert("", tk.END, iid=iid, values=_format_control_row(rec))
        record_map[iid] = rec
        if selected_record and str(rec.get("ID") or rec.get("_entrada_id") or "") == selected_record:
            selected_iid = iid

    _control_table_map[tree_widget] = record_map
    if selected_iid:
        try:
            tree_widget.selection_set(selected_iid)
            tree_widget.focus(selected_iid)
            tree_widget.see(selected_iid)
        except Exception:
            pass
    _update_control_details(tree_widget, tree_widget.selection())

def _populate_text(text_widget, info_label):
    source = _monitor_sources.get(text_widget, {})
    report_status("monitor", "STARTED", stage="populate_text", details={"source": source.get("path")})
    if source.get("view") == "table":
        _populate_control_table(text_widget, info_label)
        report_status("monitor", "OK", stage="populate_text_done", details={"source": source.get("path"), "view": "table"})
        return
    arquivo = source.get("path", ARQUIVO)
    formatter = source.get("formatter", format_creative_entry)
    registros = _load_safe(arquivo)
    filter_key = source.get("filter_key", text_widget)
    filters = _filter_state.get(filter_key, {})
    filtrados = _apply_filters(registros, filters)
    last = get_last_status()
    status_hint = ""
    if last:
        status_hint = f" | último status: {last.get('action','-')}:{last.get('status','-')}"
    info_label.config(
        text=f"Arquivo: {arquivo} — registros: {len(filtrados)} (de {len(registros)}){status_hint}"
    )
    # sempre operar em state normal para evitar problemas na medição de ranges
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    record_ranges = []
    record_tag_map = {}
    record_line_map = {}
    has_clickable_records = False

    for idx, r in enumerate(filtrados):
        is_clickable = formatter in (format_encomenda_entry, format_orientacao_entry, format_observacao_entry)
        rec_tag = None
        if is_clickable:
            has_clickable_records = True
            prefix = "encomenda" if formatter == format_encomenda_entry else ("orientacao" if formatter == format_orientacao_entry else "observacao")
            rec_tag = f"{prefix}_record_{idx}"
        linha = formatter(r)
        # Inserir já com a tag — isto garante que o tag cubra exatamente o texto
        try:
            if rec_tag and formatter in (format_orientacao_entry, format_observacao_entry):
                text_widget.insert(tk.END, linha + "\n", (rec_tag,))
                if idx < len(filtrados) - 1:
                    text_widget.insert(tk.END, "─" * 80 + "\n\n")
                else:
                    text_widget.insert(tk.END, "\n")
            elif rec_tag:
                text_widget.insert(tk.END, linha + "\n\n", (rec_tag,))
            else:
                text_widget.insert(tk.END, linha + "\n\n")
        except Exception:
            # fallback simples
            text_widget.insert(tk.END, linha + "\n\n")

        # calcular start/end com base nas ranges da tag (quando aplicável)
        if rec_tag:
            try:
                ranges = text_widget.tag_ranges(rec_tag)
                if ranges and len(ranges) >= 2:
                    start = ranges[0]
                    end = ranges[1]
                else:
                    # fallback: aproximar pelo 'end' antes das quebras adicionadas
                    end = text_widget.index("end-2c")
                    start = text_widget.index(f"{end} - {len(linha)}c")
            except Exception:
                start = "1.0"
                end = text_widget.index("end-2c")
            record_ranges.append((start, end, r))
            record_tag_map[rec_tag] = r
            try:
                line_no = str(start).split(".", 1)[0]
                record_line_map[line_no] = r
            except Exception:
                pass
            status = (r.get("STATUS_ENCOMENDA") or "").strip().upper()
            if status == "AVISADO":
                try:
                    text_widget.tag_add("status_avisado", start, end)
                except Exception:
                    pass
            elif status == "SEM CONTATO":
                try:
                    text_widget.tag_add("status_sem_contato", start, end)
                except Exception:
                    pass

            # bind por tag: captura o registro e a tag
            try:
                text_widget.tag_unbind(rec_tag, "<Button-1>")
            except Exception:
                pass
            try:
                # capturar rec_tag e r no default args
                text_widget.tag_bind(rec_tag, "<Button-1>", lambda ev, tw=text_widget, rec=r, tag=rec_tag: _record_on_tag_click(tw, rec, ev, tag))
            except Exception:
                pass
        else:
            # para registros não-encomenda, só guardar ranges genéricos
            try:
                end = text_widget.index("end-2c")
                start = text_widget.index(f"{end} - {len(linha)}c")
                record_ranges.append((start, end, r))
                try:
                    line_no = str(start).split(".", 1)[0]
                    record_line_map[line_no] = r
                except Exception:
                    pass
            except Exception:
                pass

    # desativa edição após inserir
    text_widget.config(state="disabled")
    report_status("monitor", "OK", stage="populate_text_done", details={"source": arquivo, "visible": len(filtrados)})
    if formatter == format_encomenda_entry:
        _encomenda_display_map[text_widget] = record_ranges
        _encomenda_tag_map[text_widget] = record_tag_map
        _encomenda_line_map[text_widget] = record_line_map
    else:
        _encomenda_display_map.pop(text_widget, None)
        _encomenda_tag_map.pop(text_widget, None)
        _encomenda_line_map.pop(text_widget, None)

    if has_clickable_records or formatter in (format_orientacao_entry, format_observacao_entry):
        _record_tag_map_generic[text_widget] = record_tag_map
    else:
        _record_tag_map_generic.pop(text_widget, None)
    _restore_hover_if_needed(text_widget, "hover_line")

def _schedule_update(text_widgets, info_label):
    global _monitor_after_id
    for tw in text_widgets:
        if tw in _text_edit_lock:
            continue
        _populate_text(tw, info_label)
    # schedule next update
    try:
        _monitor_after_id = text_widgets[0].after(
            REFRESH_MS, lambda: _schedule_update(text_widgets, info_label)
        )
    except Exception:
        _monitor_after_id = None

def _cancel_scheduled(text_widgets):
    global _monitor_after_id
    try:
        if _monitor_after_id and text_widgets:
            text_widgets[0].after_cancel(_monitor_after_id)
    except Exception:
        pass
    _monitor_after_id = None

def forcar_recarregar(text_widgets, info_label):
    for tw in text_widgets:
        _populate_text(tw, info_label)

def limpar_dados(text_widgets, info_label):
    if not os.path.exists(ARQUIVO):
        messagebox.showinfo("Limpar dados", "Arquivo não existe.")
        return
    resp = messagebox.askyesno("Limpar dados", "Criar backup e limpar dadosend.json (registros serão removidos)?")
    if not resp:
        return
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = os.path.join(os.path.dirname(ARQUIVO), f"dadosend_backup_{ts}.json")
        shutil.copy2(ARQUIVO, bak)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao criar backup: {e}")
        return
    try:
        _atomic_write(ARQUIVO, {"registros": []})
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao limpar arquivo: {e}")
        return
    messagebox.showinfo("Limpar dados", f"Backup salvo em:\n{bak}\nArquivo limpo.")
    for tw in text_widgets:
        _populate_text(tw, info_label)

def _default_filters():
    return {
        "order": "Mais recentes",
        "date_mode": "Mais recentes",
        "date_value": "",
        "time_mode": "Mais recentes",
        "time_value": "",
        "query": "",
        "status": "Todos",
        "bloco": "Todos",
    }

def _build_filter_bar(parent, text_widget, info_label):
    bar = build_card_frame(parent)
    bar.pack(fill=tk.X, padx=10, pady=(10, 6))

    order_var = tk.StringVar(value="Mais recentes")
    date_mode_var = tk.StringVar(value="Mais recentes")
    time_mode_var = tk.StringVar(value="Mais recentes")
    query_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="Todos")
    bloco_var = tk.StringVar(value="Todos")

    date_entry = build_filter_input(bar, width=12)
    time_entry = build_filter_input(bar, width=10)
    query_entry = build_filter_input(bar, textvariable=query_var, width=18)

    def update_entry_state():
        date_state = "normal" if date_mode_var.get() == "Específica" else "disabled"
        time_state = "normal" if time_mode_var.get() == "Específica" else "disabled"
        date_entry.configure(state=date_state)
        time_entry.configure(state=time_state)

    def apply_filters():
        _filter_state[text_widget] = {
            "order": order_var.get(),
            "date_mode": date_mode_var.get(),
            "date_value": date_entry.get().strip(),
            "time_mode": time_mode_var.get(),
            "time_value": time_entry.get().strip(),
            "query": query_entry.get().strip(),
            "status": status_var.get().strip() or "Todos",
            "bloco": bloco_var.get().strip() or "Todos",
        }
        report_status("ux_metrics", "OK", stage="filter_apply", details={"source": str(text_widget), "query_len": len(query_entry.get().strip())})
        _populate_text(text_widget, info_label)

    def clear_filters():
        order_var.set("Mais recentes")
        date_mode_var.set("Mais recentes")
        time_mode_var.set("Mais recentes")
        query_var.set("")
        status_var.set("Todos")
        bloco_var.set("Todos")
        date_entry.delete(0, tk.END)
        time_entry.delete(0, tk.END)
        update_entry_state()
        _filter_state[text_widget] = _default_filters()
        report_status("ux_metrics", "OK", stage="filter_clear", details={"source": str(text_widget)})
        _populate_text(text_widget, info_label)

    tk.Label(bar, text="Ordem", bg=UI_THEME["surface"], fg=UI_THEME["text"]).grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")
    order_combo = ttk.Combobox(bar, textvariable=order_var, values=["Mais recentes", "Mais antigas"], width=12, state="readonly")
    order_combo.grid(row=0, column=1, padx=(0, 12), pady=8, sticky="w")

    tk.Label(bar, text="Data", bg=UI_THEME["surface"], fg=UI_THEME["text"]).grid(row=0, column=2, padx=(0, 6), pady=8, sticky="w")
    date_mode_combo = ttk.Combobox(
        bar,
        textvariable=date_mode_var,
        values=["Mais recentes", "Específica"],
        width=10,
        state="readonly",
    )
    date_mode_combo.grid(row=0, column=3, padx=(0, 6), pady=8, sticky="w")
    date_entry.grid(row=0, column=4, padx=(0, 12), pady=8, sticky="w")

    tk.Label(bar, text="Hora", bg=UI_THEME["surface"], fg=UI_THEME["text"]).grid(row=0, column=5, padx=(0, 6), pady=8, sticky="w")
    time_mode_combo = ttk.Combobox(
        bar,
        textvariable=time_mode_var,
        values=["Mais recentes", "Específica"],
        width=10,
        state="readonly",
    )
    time_mode_combo.grid(row=0, column=6, padx=(0, 6), pady=8, sticky="w")
    time_entry.grid(row=0, column=7, padx=(0, 12), pady=8, sticky="w")

    tk.Label(bar, text="Buscar", bg=UI_THEME["surface"], fg=UI_THEME["text"]).grid(row=0, column=8, padx=(0, 6), pady=8, sticky="w")
    query_entry.grid(row=0, column=9, padx=(0, 12), pady=8, sticky="w")

    tk.Label(bar, text="Status", bg=UI_THEME["surface"], fg=UI_THEME["text"]).grid(row=0, column=10, padx=(0, 6), pady=8, sticky="w")
    status_combo = ttk.Combobox(bar, textvariable=status_var, values=["Todos", "MORADOR", "VISITANTE", "PRESTADOR", "AVISADO", "SEM CONTATO"], width=14, state="readonly")
    status_combo.grid(row=0, column=11, padx=(0, 12), pady=8, sticky="w")

    tk.Label(bar, text="Bloco", bg=UI_THEME["surface"], fg=UI_THEME["text"]).grid(row=0, column=12, padx=(0, 6), pady=8, sticky="w")
    bloco_combo = ttk.Combobox(bar, textvariable=bloco_var, values=["Todos"] + [str(i) for i in range(1, 31)], width=8, state="readonly")
    bloco_combo.grid(row=0, column=13, padx=(0, 12), pady=8, sticky="w")

    build_primary_button(bar, "Aplicar", apply_filters).grid(row=0, column=14, padx=(0, 6), pady=8)
    build_secondary_button(bar, "Limpar", clear_filters).grid(row=0, column=15, padx=(0, 10), pady=8)

    _filter_controls[text_widget] = [
        order_combo,
        date_mode_combo,
        date_entry,
        time_mode_combo,
        time_entry,
        query_entry,
        status_combo,
        bloco_combo,
    ]
    for control in _filter_controls[text_widget]:
        bind_focus_ring(control)
    bar.grid_columnconfigure(16, weight=1)
    date_mode_var.trace_add("write", lambda *_: update_entry_state())
    time_mode_var.trace_add("write", lambda *_: update_entry_state())
    update_entry_state()
    _filter_state[text_widget] = _default_filters()

def _apply_hover_line(text_widget, line, hover_tag):
    if text_widget in _text_edit_lock:
        return
    if not line:
        return
    start = f"{line}.0"
    end = f"{line}.0 lineend+1c"
    try:
        text_widget.config(state="normal")
        text_widget.tag_add(hover_tag, start, end)
        text_widget.config(state="disabled")
    except Exception:
        try:
            text_widget.tag_add(hover_tag, start, end)
        except Exception:
            pass

def _clear_hover_line(text_widget, hover_tag):
    if text_widget in _text_edit_lock:
        return
    try:
        text_widget.config(state="normal")
        text_widget.tag_remove(hover_tag, "1.0", tk.END)
        text_widget.config(state="disabled")
    except Exception:
        try:
            text_widget.tag_remove(hover_tag, "1.0", tk.END)
        except Exception:
            pass
    _hover_state[text_widget] = None

def _restore_hover_if_needed(text_widget, hover_tag):
    if text_widget in _text_edit_lock:
        return
    line = _hover_state.get(text_widget)
    if not line:
        return
    try:
        line_text = text_widget.get(f"{line}.0", f"{line}.end")
    except Exception:
        line_text = ""
    if not line_text.strip():
        _hover_state[text_widget] = None
        return
    try:
        x_root = text_widget.winfo_pointerx()
        y_root = text_widget.winfo_pointery()
        widget_at_pointer = text_widget.winfo_containing(x_root, y_root)
        if widget_at_pointer is not text_widget:
            return
    except Exception:
        return
    _apply_hover_line(text_widget, line, hover_tag)

def _bind_hover_highlight(text_widget):
    hover_tag = "hover_line"
    text_widget.tag_configure(hover_tag, background=UI_THEME["focus_bg"], foreground=UI_THEME["focus_text"])
    _hover_state[text_widget] = None

    def on_motion(event):
        if text_widget in _text_edit_lock:
            return
        try:
            index = text_widget.index(f"@{event.x},{event.y}")
        except Exception:
            return
        line = index.split(".")[0]
        try:
            line_text = text_widget.get(f"{line}.0", f"{line}.end")
        except Exception:
            line_text = ""
        if not line_text.strip():
            _clear_hover_line(text_widget, hover_tag)
            return
        if _hover_state.get(text_widget) == line:
            return
        _clear_hover_line(text_widget, hover_tag)
        _apply_hover_line(text_widget, line, hover_tag)
        _hover_state[text_widget] = line

    text_widget.bind("<Motion>", on_motion)
    text_widget.bind("<Leave>", lambda _event: _clear_hover_line(text_widget, hover_tag))

def _find_encomenda_record_at_index(text_widget, index):
    try:
        line = index.split(".", 1)[0]
        line_text = text_widget.get(f"{line}.0", f"{line}.end")
        if not line_text.strip():
            return None
    except Exception:
        pass

    tag_map = _encomenda_tag_map.get(text_widget, {})
    if tag_map:
        try:
            for tag in text_widget.tag_names(index):
                if tag.startswith("encomenda_record_") and tag in tag_map:
                    return tag_map[tag]
        except Exception:
            pass

    ranges = _encomenda_display_map.get(text_widget, [])
    if not ranges:
        return None

    try:
        line_no = int(line)
    except Exception:
        line_no = None

    for start, end, record in ranges:
        try:
            if text_widget.compare(index, ">=", start) and text_widget.compare(index, "<=", end):
                return record
        except Exception:
            pass
        if line_no is not None:
            try:
                s_line = int(str(start).split(".", 1)[0])
                e_line = int(str(end).split(".", 1)[0])
            except Exception:
                continue
            if s_line <= line_no <= e_line:
                return record
    return None

def _update_encomenda_status(record, status):
    registros = _load_safe(ENCOMENDAS_ARQUIVO)
    match = None
    for r in registros:
        if r.get("ID") and record.get("ID") and str(r.get("ID")) == str(record.get("ID")):
            match = r
            break
        if r.get("_entrada_id") and record.get("_entrada_id") and str(r.get("_entrada_id")) == str(record.get("_entrada_id")):
            match = r
            break
    if match is None and record:
        try:
            target_key = _record_hash_key_encomenda(record)
        except Exception:
            target_key = None
        if target_key:
            for r in registros:
                try:
                    if _record_hash_key_encomenda(r) == target_key:
                        match = r
                        break
                except Exception:
                    continue
    if match is None:
        return False
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    match["STATUS_ENCOMENDA"] = status
    match["STATUS_DATA_HORA"] = now_str
    try:
        _atomic_write(ENCOMENDAS_ARQUIVO, {"registros": registros})

        # Recalcula análises/avisos para refletir imediatamente mudança de status (AVISADO <-> SEM CONTATO).
        try:
            import analises as analises_mod
            import avisos as avisos_mod
            analises_mod.build_analises(ARQUIVO, ANALISES_ARQUIVO)
            avisos_mod.build_avisos(ANALISES_ARQUIVO, AVISOS_ARQUIVO)
        except Exception:
            pass

        return True
    except Exception:
        return False

def _build_encomenda_actions(frame, text_widget, info_label):
    action_frame = tk.Frame(frame, bg=UI_THEME["surface"])
    action_frame.pack_forget()

    # manter estado por widget dentro do mapa global
    current = {"record": None, "rec_tag": None}

    def hide_actions():
        action_frame.pack_forget()
        current["record"] = None
        current["rec_tag"] = None
        # remover highlight
        try:
            text_widget.config(state="normal")
            text_widget.tag_remove("encomenda_selected", "1.0", tk.END)
            text_widget.config(state="disabled")
        except Exception:
            pass

    def show_actions():
        if action_frame.winfo_ismapped():
            return
        action_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

    def apply_status(status):
        record = current.get("record")
        if not record:
            return
        if _update_encomenda_status(record, status):
            _populate_text(text_widget, info_label)
        hide_actions()

    # botões existentes
    tk.Button(
        action_frame,
        text="AVISADO",
        command=lambda: apply_status("AVISADO"),
        bg=UI_THEME["surface_alt"],
        fg=UI_THEME["text"],
        activebackground=UI_THEME["primary"],
        activeforeground=UI_THEME["text"],
        relief="flat",
        padx=18,
    ).pack(side=tk.LEFT, expand=True, padx=10, pady=8)
    tk.Button(
        action_frame,
        text="SEM CONTATO",
        command=lambda: apply_status("SEM CONTATO"),
        bg=UI_THEME["surface_alt"],
        fg=UI_THEME["text"],
        activebackground=UI_THEME["primary"],
        activeforeground=UI_THEME["text"],
        relief="flat",
        padx=18,
    ).pack(side=tk.LEFT, expand=True, padx=10, pady=8)

    # Armazenar a UI de ações no mapa global, incluindo current e funções de show/hide
    _encomenda_action_ui[text_widget] = {
        "frame": action_frame,
        "hide": hide_actions,
        "show": show_actions,
        "current": current,
    }

    # --- fallback global: bind no Text que localiza o registro clicado e mostra ações ---
    def on_click(event):
        """
        Handler global: quando o usuário clicar em qualquer ponto do Text, busca o registro
        e atualiza `current` no mapa global, depois mostra o painel de ações.
        Isso funciona mesmo quando tag_bind falha.
        """
        try:
            idx = text_widget.index(f"@{event.x},{event.y}")
        except Exception:
            return
        record = _find_encomenda_record_at_index(text_widget, idx)
        ui = _encomenda_action_ui.get(text_widget)
        if not ui:
            return
        if record:
            cur = ui.get("current")
            if cur is None:
                cur = {"record": None, "rec_tag": None}
                ui["current"] = cur
            cur["record"] = record
            # tentar achar o rec_tag correspondente (comparando hash)
            rec_tag_found = None
            tag_map = _encomenda_tag_map.get(text_widget, {})
            try:
                target_key = _record_hash_key_encomenda(record)
            except Exception:
                target_key = None
            if target_key:
                for tag, rec_obj in tag_map.items():
                    try:
                        if _record_hash_key_encomenda(rec_obj) == target_key:
                            rec_tag_found = tag
                            break
                    except Exception:
                        continue
            cur["rec_tag"] = rec_tag_found
            # destacar se houver tag encontrada
            try:
                text_widget.config(state="normal")
                text_widget.tag_remove("encomenda_selected", "1.0", tk.END)
                if rec_tag_found:
                    ranges = text_widget.tag_ranges(rec_tag_found)
                    if ranges and len(ranges) >= 2:
                        text_widget.tag_add("encomenda_selected", ranges[0], ranges[1])
                text_widget.config(state="disabled")
            except Exception:
                pass
            show_fn = ui.get("show")
            if callable(show_fn):
                show_fn()
        else:
            hide_fn = ui.get("hide")
            if callable(hide_fn):
                hide_fn()

    # garantir que não existam binds duplicados:
    try:
        text_widget.unbind("<Button-1>")
    except Exception:
        pass
    # adicionar bind de fallback
    text_widget.bind("<Button-1>", on_click)

def _set_fullscreen(window):
    try:
        window.state("zoomed")
    except Exception:
        pass

def _apply_dark_theme(widget):
    try:
        widget.configure(bg=UI_THEME["surface"])
    except Exception:
        pass

def _apply_light_theme(widget):
    try:
        widget.configure(bg=UI_THEME["bg"])
    except Exception:
        pass

def _build_text_actions(frame, text_widget, info_label, path):
    action_frame = tk.Frame(frame, bg=UI_THEME["surface"])
    action_frame.pack_forget()
    current = {"record": None, "rec_tag": None}
    edit_state = {"active": False, "tag": None, "dirty": False}

    edit_badge = tk.Label(action_frame, text="MODO EDIÇÃO ATIVO", bg=UI_THEME["edit_badge_bg"], fg=UI_THEME["edit_badge_text"], padx=10, pady=4)
    edit_badge.pack_forget()

    def _set_filters_enabled(enabled: bool):
        for w in _filter_controls.get(text_widget, []):
            try:
                if isinstance(w, ttk.Combobox):
                    w.configure(state=("readonly" if enabled else "disabled"))
                else:
                    w.configure(state=("normal" if enabled else "disabled"))
            except Exception:
                pass

    def is_editing():
        return bool(edit_state.get("active"))

    def _bind_edit_shortcuts():
        def _only_editing(handler):
            def _wrapped(event):
                if not is_editing():
                    return None
                return handler(event)
            return _wrapped

        def _sel_all(_event):
            try:
                text_widget.tag_add("sel", "1.0", "end-1c")
                text_widget.mark_set("insert", "1.0")
                text_widget.see("insert")
            except Exception:
                pass
            return "break"

        def _virtual(name):
            def _h(_event):
                try:
                    text_widget.event_generate(name)
                    edit_state["dirty"] = True
                except Exception:
                    pass
                return "break"
            return _h

        shortcuts = {
            "<Control-a>": _sel_all,
            "<Control-A>": _sel_all,
            "<Control-z>": _virtual("<<Undo>>"),
            "<Control-Z>": _virtual("<<Undo>>"),
            "<Control-y>": _virtual("<<Redo>>"),
            "<Control-Y>": _virtual("<<Redo>>"),
            "<Control-x>": _virtual("<<Cut>>"),
            "<Control-X>": _virtual("<<Cut>>"),
            "<Control-c>": _virtual("<<Copy>>"),
            "<Control-C>": _virtual("<<Copy>>"),
            "<Control-v>": _virtual("<<Paste>>"),
            "<Control-V>": _virtual("<<Paste>>"),
        }
        shortcuts["<Escape>"] = lambda _event: (cancel_edit() or "break")
        for seq, handler in shortcuts.items():
            try:
                text_widget.bind(seq, _only_editing(handler), add="+")
            except Exception:
                pass

    def hide_actions():
        if is_editing():
            return
        action_frame.pack_forget()
        current["record"] = None
        current["rec_tag"] = None

    def show_actions():
        rec = current.get("record")
        if not rec:
            return
        if not action_frame.winfo_ismapped():
            action_frame.pack(fill=tk.X, padx=10, pady=(0, 8))

    def enable_edit():
        rec_tag = current.get("rec_tag")
        if not rec_tag:
            return
        edit_state["active"] = True
        edit_state["tag"] = rec_tag
        edit_state["dirty"] = False
        _text_edit_lock.add(text_widget)
        _set_filters_enabled(False)
        try:
            text_widget.tag_remove("sel", "1.0", tk.END)
        except Exception:
            pass
        try:
            text_widget.config(state="normal")
            text_widget.focus_set()
            edit_badge.pack(fill=tk.X, padx=8, pady=(6, 2), before=action_frame.winfo_children()[0] if action_frame.winfo_children() else None)
        except Exception:
            pass

    def _finish_editing(reload_text=True):
        edit_state["active"] = False
        edit_state["tag"] = None
        edit_state["dirty"] = False
        _text_edit_lock.discard(text_widget)
        _set_filters_enabled(True)
        try:
            edit_badge.pack_forget()
            text_widget.config(state="disabled")
        except Exception:
            pass
        if reload_text:
            _populate_text(text_widget, info_label)

    def cancel_edit():
        if not is_editing():
            return
        if edit_state.get("dirty"):
            try:
                if not messagebox.askyesno("Cancelar edição", "Descartar alterações não salvas?"):
                    return
            except Exception:
                pass
        if log_audit_event:
            log_audit_event("texto_cancelado", os.path.basename(path), (current.get("record") or {}).get("texto", ""))
        _finish_editing(reload_text=True)

    def save_edit():
        rec = current.get("record")
        rec_tag = current.get("rec_tag")
        if not rec or not rec_tag:
            return
        try:
            ranges = text_widget.tag_ranges(rec_tag)
            if not ranges or len(ranges) < 2:
                return
            new_text = text_widget.get(ranges[0], ranges[1]).strip()
        except Exception:
            return

        registros = _load_safe(path)
        target = None
        for r in registros:
            if str(r.get("id")) == str(rec.get("id")):
                target = r
                break
        if not target:
            return

        target["texto"] = new_text
        strict, inferred = build_structured_fields(new_text) if build_structured_fields else ({}, {})
        target["campos_extraidos_confirmados"] = strict
        target["campos_extraidos_inferidos"] = inferred
        target["campos_extraidos"] = _extract_multi_fields(new_text)
        _atomic_write(path, {"registros": registros})
        if log_audit_event:
            log_audit_event("texto_editado", os.path.basename(path), new_text)
            log_audit_event("campos_reextraidos", os.path.basename(path), new_text)

        _finish_editing(reload_text=True)

    tk.Button(action_frame, text="Editar", command=enable_edit, bg=UI_THEME["surface_alt"], fg=UI_THEME["text"], activebackground=UI_THEME["primary"], activeforeground=UI_THEME["text"], relief="flat", padx=18).pack(side=tk.LEFT, expand=True, padx=10, pady=8)
    tk.Button(action_frame, text="Salvar", command=save_edit, bg=UI_THEME["primary"], fg=UI_THEME["text"], activebackground=UI_THEME["primary_active"], activeforeground=UI_THEME["text"], relief="flat", padx=18).pack(side=tk.LEFT, expand=True, padx=10, pady=8)
    tk.Button(action_frame, text="Cancelar", command=cancel_edit, bg=UI_THEME["surface_alt"], fg=UI_THEME["text"], activebackground=UI_THEME["border"], activeforeground=UI_THEME["text"], relief="flat", padx=18).pack(side=tk.LEFT, expand=True, padx=10, pady=8)

    _text_action_ui[text_widget] = {
        "frame": action_frame,
        "hide": hide_actions,
        "show": show_actions,
        "current": current,
        "is_editing": is_editing,
    }

    def on_click(event):
        if is_editing():
            if edit_state.get("dirty"):
                try:
                    if not messagebox.askyesno("Alterações não salvas", "Deseja sair da edição sem salvar?"):
                        return
                except Exception:
                    return
                cancel_edit()
            else:
                return
        try:
            idx = text_widget.index(f"@{event.x},{event.y}")
            for tag in text_widget.tag_names(idx):
                if "_record_" in tag:
                    rec = _record_tag_map_generic.get(text_widget, {}).get(tag)
                    if rec:
                        current["record"] = rec
                        current["rec_tag"] = tag
                        show_actions()
                        return
            hide_actions()
        except Exception:
            return

    def on_click_outside(_event):
        if is_editing():
            return
        hide_actions()

    def on_key_change(_event):
        if is_editing():
            edit_state["dirty"] = True

    _bind_edit_shortcuts()
    try:
        text_widget.bind("<Button-1>", on_click, add="+")
        text_widget.bind("<Key>", on_key_change, add="+")
    except Exception:
        pass
    try:
        frame.bind("<Button-1>", on_click_outside, add="+")
    except Exception:
        pass

def _build_monitor_ui(container):
    _apply_light_theme(container)
    style = ttk.Style(container)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Dark.TNotebook", background=UI_THEME["bg"], borderwidth=0)
    style.configure("Dark.TNotebook.Tab", background=UI_THEME["surface"], foreground=UI_THEME["text"], padding=(16, 6))
    style.map(
        "Dark.TNotebook.Tab",
        background=[("selected", UI_THEME["primary"]), ("active", UI_THEME["surface_alt"])],
        foreground=[("selected", UI_THEME["text"]), ("active", UI_THEME["text"])],
    )
    style.configure("Encomenda.Text", background=UI_THEME["surface"], foreground=UI_THEME["text"])
    style.configure("Control.Treeview", background=UI_THEME["surface"], fieldbackground=UI_THEME["surface"], foreground=UI_THEME["text"], bordercolor=UI_THEME["border"], rowheight=28)
    style.configure("Control.Treeview.Heading", background=UI_THEME["surface_alt"], foreground=UI_THEME["text"], relief="flat")
    style.map("Control.Treeview", background=[("selected", UI_THEME["primary"])], foreground=[("selected", UI_THEME["text"])])

    info_label = tk.Label(container, text=f"Arquivo: {ARQUIVO}", bg=UI_THEME["bg"], fg=UI_THEME["muted_text"])
    info_label.pack(padx=10, pady=(6, 0), anchor="w")

    notebook = ttk.Notebook(container, style="Dark.TNotebook")
    notebook.pack(padx=10, pady=(8, 10), fill=tk.BOTH, expand=True)

    controle_frame = tk.Frame(notebook, bg=UI_THEME["surface"])
    encomendas_frame = tk.Frame(notebook, bg=UI_THEME["surface"])
    orientacoes_frame = tk.Frame(notebook, bg=UI_THEME["surface"])
    observacoes_frame = tk.Frame(notebook, bg=UI_THEME["surface"])

    notebook.add(controle_frame, text="CONTROLE")
    notebook.add(encomendas_frame, text="ENCOMENDAS")
    notebook.add(orientacoes_frame, text="ORIENTAÇÕES")
    notebook.add(observacoes_frame, text="OBSERVAÇÕES")

    monitor_widgets = []
    tab_configs = [
        (controle_frame, ARQUIVO, format_creative_entry),
        (encomendas_frame, ENCOMENDAS_ARQUIVO, format_encomenda_entry),
        (orientacoes_frame, ORIENTACOES_ARQUIVO, format_orientacao_entry),
        (observacoes_frame, OBSERVACOES_ARQUIVO, format_observacao_entry),
    ]
    for frame, arquivo, formatter in tab_configs:
        if formatter == format_creative_entry:
            table_wrap = build_card_frame(frame)
            table_wrap.pack(padx=10, pady=(0, 8), fill=tk.BOTH, expand=True)
            columns = ("data_hora", "nome", "bloco_ap", "placa", "status")
            tree = ttk.Treeview(table_wrap, columns=columns, show="headings", style="Control.Treeview")
            tree.heading("data_hora", text="Data/Hora")
            tree.heading("nome", text="Nome")
            tree.heading("bloco_ap", text="Bloco/AP")
            tree.heading("placa", text="Placa")
            tree.heading("status", text="Status")
            _control_sort_state[tree] = {"key": "data_hora", "reverse": True}

            def _sort_by(col, tw=tree):
                st = _control_sort_state.get(tw, {"key": col, "reverse": False})
                reverse = not st.get("reverse", False) if st.get("key") == col else False
                _control_sort_state[tw] = {"key": col, "reverse": reverse}
                _populate_text(tw, info_label)

            for _col in columns:
                tree.heading(_col, command=lambda c=_col: _sort_by(c))
            tree.column("data_hora", width=160, anchor="w")
            tree.column("nome", width=220, anchor="w")
            tree.column("bloco_ap", width=110, anchor="center")
            tree.column("placa", width=120, anchor="center")
            tree.column("status", width=160, anchor="w")

            def _on_resize(event, tw=tree):
                total = max(event.width - 24, 300)
                tw.column("data_hora", width=max(120, int(total * 0.22)))
                tw.column("nome", width=max(180, int(total * 0.30)))
                tw.column("bloco_ap", width=max(90, int(total * 0.14)))
                tw.column("placa", width=max(90, int(total * 0.14)))
                tw.column("status", width=max(120, int(total * 0.20)))

            table_wrap.bind("<Configure>", _on_resize, add="+")
            _build_filter_bar(frame, tree, info_label)
            yscroll = ttk.Scrollbar(table_wrap, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=yscroll.set)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            yscroll.pack(side=tk.RIGHT, fill=tk.Y)
            details_var = tk.StringVar(value="Selecione um registro para ver detalhes.")
            details = tk.Label(frame, textvariable=details_var, bg=UI_THEME["surface_alt"], fg=UI_THEME["text"], anchor="w", justify="left", padx=10, pady=8)
            details.pack(fill=tk.X, padx=10, pady=(0, 10))
            _control_details_var[tree] = details_var
            def _on_select(_e, tw=tree):
                _update_control_details(tw, tw.selection())
                report_status("ux_metrics", "OK", stage="control_row_selected", details={"selection_count": len(tw.selection())})
            tree.bind("<<TreeviewSelect>>", _on_select, add="+")
            bind_focus_ring(tree)
            monitor_widgets.append(tree)
            _monitor_sources[tree] = {"path": arquivo, "formatter": formatter, "view": "table", "filter_key": tree}
            continue

        text_widget = tk.Text(
            frame,
            wrap="word",
            bg=UI_THEME["surface"],
            fg=UI_THEME["text"],
            insertbackground=UI_THEME["text"],
            relief="flat",
            undo=True,
            autoseparators=True,
            maxundo=-1,
        )
        _build_filter_bar(frame, text_widget, info_label)
        if formatter == format_encomenda_entry:
            text_widget.tag_configure("status_avisado", foreground=UI_THEME["status_avisado_text"])
            text_widget.tag_configure("status_sem_contato", foreground=UI_THEME["status_sem_contato_text"])
            text_widget.tag_configure("encomenda_selected", background=UI_THEME["focus_bg"], foreground=UI_THEME["focus_text"])
        text_widget.pack(padx=10, pady=(0, 8), fill=tk.BOTH, expand=True)
        text_widget.config(state="disabled")
        _bind_hover_highlight(text_widget)
        if formatter == format_encomenda_entry:
            _build_encomenda_actions(frame, text_widget, info_label)
        elif formatter in (format_orientacao_entry, format_observacao_entry):
            _build_text_actions(frame, text_widget, info_label, arquivo)
        monitor_widgets.append(text_widget)
        _monitor_sources[text_widget] = {"path": arquivo, "formatter": formatter, "filter_key": text_widget}

    btn_frame = tk.Frame(container, bg=UI_THEME["bg"])
    btn_frame.pack(padx=10, pady=(0, 10))
    build_primary_button(btn_frame, "Recarregar", lambda: forcar_recarregar(monitor_widgets, info_label)).pack(side=tk.LEFT, padx=6)
    build_secondary_button(btn_frame, "Backup e Limpar", lambda: limpar_dados(monitor_widgets, info_label)).pack(side=tk.LEFT, padx=6)

    return monitor_widgets, info_label

# ---------- embutir como Toplevel ----------
def create_monitor_toplevel(master):
    global _monitor_toplevel
    if _monitor_toplevel:
        try:
            _monitor_toplevel.lift()
            _monitor_toplevel.focus_force()
        except Exception:
            pass
        return _monitor_toplevel

    top = tk.Toplevel(master)
    top.title("Monitor de Acessos (embutido)")
    _monitor_toplevel = top

    _set_fullscreen(top)
    text_widgets, info_label = _build_monitor_ui(top)

    _schedule_update(text_widgets, info_label)

    def on_close():
        _cancel_scheduled(text_widgets)
        try:
            top.destroy()
        except Exception:
            pass
        global _monitor_toplevel
        _monitor_toplevel = None

    top.protocol("WM_DELETE_WINDOW", on_close)
    return top

# ---------- standalone (modo original) ----------
def iniciar_monitor_standalone():
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    root = tk.Tk()
    root.title("Monitor de Acessos (standalone)")

    text_widgets, info_label = _build_monitor_ui(root)

    _schedule_update(text_widgets, info_label)

    def on_close_standalone():
        _cancel_scheduled(text_widgets)
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass
        try:
            root.destroy()
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", on_close_standalone)
    try:
        root.mainloop()
    finally:
        try:
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass

# ---------- entrypoint ----------
if __name__ == "__main__":
    iniciar_monitor_standalone()
