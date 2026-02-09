# interfacetwo.py — monitor (suporta modo embutido via create_monitor_toplevel)
"""
Monitor de dados:
- Pode ser embutido via create_monitor_toplevel(master)
- Ou executado standalone (python interfacetwo.py)
"""

import os
import json
import shutil
import tempfile
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, ttk
import re
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(BASE_DIR, "dadosend.json")
ENCOMENDAS_ARQUIVO = os.path.join(BASE_DIR, "encomendasend.json")
LOCK_FILE = os.path.join(BASE_DIR, "monitor.lock")
REFRESH_MS = 2000  # 2s

# internal reference to Toplevel (quando embutido)
_monitor_toplevel = None
_monitor_after_id = None
_filter_state = {}
_monitor_sources = {}
_hover_state = {}
_encomenda_display_map = {}
_encomenda_action_ui = {}

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
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            corrupted = f"{path}.corrupted.{ts}.bak"
            shutil.copy2(path, corrupted)
        except Exception:
            pass
        # não imprimir (para evitar janela/console indesejada)
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
    """
    Formata a linha exibida no monitor. Se MODELO/COR estiverem ausentes tenta inferir
    a partir do campo 'texto' (heurística simples).
    """
    modelo = r.get("MODELO") or ""
    cor = r.get("COR") or ""
    if (not modelo or modelo == "-") or (not cor or cor == "-"):
        # tentar inferir do campo texto
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
    """
    Gera um texto criativo para cada registro, preservando os dados.
    """
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
        return f"{base_text} — {status} {status_dh}"
    return base_text

# ---------- UI helpers (embutido) ----------
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
    order = filters.get("order", "Recentes")
    date_mode = filters.get("date_mode", "Recentes")
    date_value = filters.get("date_value", "")
    time_mode = filters.get("time_mode", "Recentes")
    time_value = filters.get("time_value", "")
    query = filters.get("query", "")

    normalized_date = _normalize_date_value(date_value) if date_mode == "Especifica" else None
    normalized_time = _normalize_time_value(time_value) if time_mode == "Especifica" else None

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
        filtrados.append(r)

    def sort_key(record):
        parsed = _parse_data_hora(record.get("DATA_HORA", ""))
        return parsed or datetime.min

    reverse = True if order == "Recentes" else False
    filtrados.sort(key=sort_key, reverse=reverse)
    return filtrados

def _populate_text(text_widget, info_label):
    source = _monitor_sources.get(text_widget, {})
    arquivo = source.get("path", ARQUIVO)
    formatter = source.get("formatter", format_creative_entry)
    registros = _load_safe(arquivo)
    filters = _filter_state.get(text_widget, {})
    filtrados = _apply_filters(registros, filters)
    info_label.config(
        text=f"Arquivo: {arquivo} — registros: {len(filtrados)} (de {len(registros)})"
    )
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    record_map = {}
    for idx, r in enumerate(filtrados):
        start = text_widget.index(tk.END)
        linha = formatter(r)
        text_widget.insert(tk.END, linha + "\n\n")
        end = text_widget.index(tk.END)
        if formatter == format_encomenda_entry:
            tag_name = f"encomenda_{idx}"
            text_widget.tag_add(tag_name, start, end)
            record_map[tag_name] = r
            status = (r.get("STATUS_ENCOMENDA") or "").strip().upper()
            if status == "AVISADO":
                text_widget.tag_add("status_avisado", start, end)
            elif status == "SEM CONTATO":
                text_widget.tag_add("status_sem_contato", start, end)
    text_widget.config(state="disabled")
    if formatter == format_encomenda_entry:
        _encomenda_display_map[text_widget] = record_map
    _restore_hover_if_needed(text_widget, "hover_line")

def _schedule_update(text_widgets, info_label):
    global _monitor_after_id
    for tw in text_widgets:
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
        "order": "Recentes",
        "date_mode": "Recentes",
        "date_value": "",
        "time_mode": "Recentes",
        "time_value": "",
        "query": "",
    }

def _build_filter_bar(parent, text_widget, info_label):
    bar = tk.Frame(parent, bg="#111111", highlightbackground="#222222", highlightthickness=1)
    bar.pack(fill=tk.X, padx=10, pady=(10, 6))

    order_var = tk.StringVar(value="Recentes")
    date_mode_var = tk.StringVar(value="Recentes")
    time_mode_var = tk.StringVar(value="Recentes")
    query_var = tk.StringVar(value="")

    date_entry = tk.Entry(bar, bg="#1c1c1c", fg="white", insertbackground="white", relief="flat", width=12)
    time_entry = tk.Entry(bar, bg="#1c1c1c", fg="white", insertbackground="white", relief="flat", width=10)
    query_entry = tk.Entry(bar, textvariable=query_var, bg="#1c1c1c", fg="white", insertbackground="white", relief="flat", width=18)

    def update_entry_state():
        date_state = "normal" if date_mode_var.get() == "Especifica" else "disabled"
        time_state = "normal" if time_mode_var.get() == "Especifica" else "disabled"
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
        }
        _populate_text(text_widget, info_label)

    def clear_filters():
        order_var.set("Recentes")
        date_mode_var.set("Recentes")
        time_mode_var.set("Recentes")
        query_var.set("")
        date_entry.delete(0, tk.END)
        time_entry.delete(0, tk.END)
        update_entry_state()
        _filter_state[text_widget] = _default_filters()
        _populate_text(text_widget, info_label)

    tk.Label(bar, text="Ordem", bg="#111111", fg="white").grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")
    ttk.Combobox(bar, textvariable=order_var, values=["Recentes", "Ultimas"], width=10, state="readonly").grid(
        row=0, column=1, padx=(0, 12), pady=8, sticky="w"
    )

    tk.Label(bar, text="Data", bg="#111111", fg="white").grid(row=0, column=2, padx=(0, 6), pady=8, sticky="w")
    ttk.Combobox(
        bar,
        textvariable=date_mode_var,
        values=["Recentes", "Especifica"],
        width=10,
        state="readonly",
    ).grid(row=0, column=3, padx=(0, 6), pady=8, sticky="w")
    date_entry.grid(row=0, column=4, padx=(0, 12), pady=8, sticky="w")

    tk.Label(bar, text="Hora", bg="#111111", fg="white").grid(row=0, column=5, padx=(0, 6), pady=8, sticky="w")
    ttk.Combobox(
        bar,
        textvariable=time_mode_var,
        values=["Recentes", "Especifica"],
        width=10,
        state="readonly",
    ).grid(row=0, column=6, padx=(0, 6), pady=8, sticky="w")
    time_entry.grid(row=0, column=7, padx=(0, 12), pady=8, sticky="w")

    tk.Label(bar, text="Consultar", bg="#111111", fg="white").grid(row=0, column=8, padx=(0, 6), pady=8, sticky="w")
    query_entry.grid(row=0, column=9, padx=(0, 12), pady=8, sticky="w")

    tk.Button(
        bar,
        text="Aplicar",
        command=apply_filters,
        bg="#1f6feb",
        fg="white",
        activebackground="#215db0",
        activeforeground="white",
        relief="flat",
        padx=12,
    ).grid(row=0, column=10, padx=(0, 6), pady=8)
    tk.Button(
        bar,
        text="Limpar",
        command=clear_filters,
        bg="#2a2a2a",
        fg="white",
        activebackground="#3a3a3a",
        activeforeground="white",
        relief="flat",
        padx=12,
    ).grid(row=0, column=11, padx=(0, 10), pady=8)

    bar.grid_columnconfigure(12, weight=1)
    date_mode_var.trace_add("write", lambda *_: update_entry_state())
    time_mode_var.trace_add("write", lambda *_: update_entry_state())
    update_entry_state()
    _filter_state[text_widget] = _default_filters()

def _apply_hover_line(text_widget, line, hover_tag):
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
    text_widget.tag_configure(hover_tag, background="white", foreground="black")
    _hover_state[text_widget] = None

    def on_motion(event):
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
    record_map = _encomenda_display_map.get(text_widget, {})
    if not record_map:
        return None
    try:
        tags = text_widget.tag_names(index)
    except Exception:
        return None
    for tag in tags:
        if tag.startswith("encomenda_"):
            return record_map.get(tag)
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
    if match is None:
        return False
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    match["STATUS_ENCOMENDA"] = status
    match["STATUS_DATA_HORA"] = now_str
    try:
        _atomic_write(ENCOMENDAS_ARQUIVO, {"registros": registros})
        return True
    except Exception:
        return False

def _build_encomenda_actions(frame, text_widget, info_label):
    action_frame = tk.Frame(frame, bg="white")
    action_frame.pack_forget()

    current = {"record": None}

    def hide_actions():
        action_frame.pack_forget()
        current["record"] = None

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

    def on_click(event):
        try:
            index = text_widget.index(f"@{event.x},{event.y}")
        except Exception:
            return
        record = _find_encomenda_record_at_index(text_widget, index)
        if not record:
            hide_actions()
            return
        current["record"] = record
        show_actions()

    tk.Button(
        action_frame,
        text="AVISADO",
        command=lambda: apply_status("AVISADO"),
        bg="white",
        fg="black",
        activebackground="#e6e6e6",
        activeforeground="black",
        relief="flat",
        padx=18,
    ).pack(side=tk.LEFT, expand=True, padx=10, pady=8)
    tk.Button(
        action_frame,
        text="SEM CONTATO",
        command=lambda: apply_status("SEM CONTATO"),
        bg="white",
        fg="black",
        activebackground="#e6e6e6",
        activeforeground="black",
        relief="flat",
        padx=18,
    ).pack(side=tk.LEFT, expand=True, padx=10, pady=8)

    text_widget.bind("<Button-1>", on_click)
    _encomenda_action_ui[text_widget] = {"frame": action_frame, "hide": hide_actions}

def _set_fullscreen(window):
    try:
        window.state("zoomed")
    except Exception:
        pass

def _apply_dark_theme(widget):
    try:
        widget.configure(bg="black")
    except Exception:
        pass

def _apply_light_theme(widget):
    try:
        widget.configure(bg="white")
    except Exception:
        pass

def _build_monitor_ui(container):
    _apply_light_theme(container)
    style = ttk.Style(container)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Dark.TNotebook", background="white", borderwidth=0)
    style.configure("Dark.TNotebook.Tab", background="black", foreground="white", padding=(16, 6))
    style.map(
        "Dark.TNotebook.Tab",
        background=[("selected", "black"), ("active", "#222222")],
        foreground=[("selected", "white"), ("active", "white")],
    )
    style.configure("Encomenda.Text", background="black", foreground="white")

    info_label = tk.Label(container, text=f"Arquivo: {ARQUIVO}", bg="white", fg="black")
    info_label.pack(padx=10, pady=(6, 0), anchor="w")

    notebook = ttk.Notebook(container, style="Dark.TNotebook")
    notebook.pack(padx=10, pady=(8, 10), fill=tk.BOTH, expand=True)

    controle_frame = tk.Frame(notebook, bg="black")
    encomendas_frame = tk.Frame(notebook, bg="black")
    orientacoes_frame = tk.Frame(notebook, bg="black")
    observacoes_frame = tk.Frame(notebook, bg="black")

    notebook.add(controle_frame, text="CONTROLE")
    notebook.add(encomendas_frame, text="ENCOMENDAS")
    notebook.add(orientacoes_frame, text="ORIENTACOES")
    notebook.add(observacoes_frame, text="OBSERVACOES")

    text_widgets = []
    tab_configs = [
        (controle_frame, ARQUIVO, format_creative_entry),
        (encomendas_frame, ENCOMENDAS_ARQUIVO, format_encomenda_entry),
        (orientacoes_frame, ARQUIVO, format_creative_entry),
        (observacoes_frame, ARQUIVO, format_creative_entry),
    ]
    for frame, arquivo, formatter in tab_configs:
        text_widget = tk.Text(
            frame,
            wrap="word",
            bg="black",
            fg="white",
            insertbackground="white",
            relief="flat",
        )
        if formatter == format_encomenda_entry:
            text_widget.tag_configure("status_avisado", foreground="#2ecc71")
            text_widget.tag_configure("status_sem_contato", foreground="#ff5c5c")
        _build_filter_bar(frame, text_widget, info_label)
        text_widget.pack(padx=10, pady=(0, 8), fill=tk.BOTH, expand=True)
        text_widget.config(state="disabled")
        _bind_hover_highlight(text_widget)
        if formatter == format_encomenda_entry:
            _build_encomenda_actions(frame, text_widget, info_label)
        text_widgets.append(text_widget)
        _monitor_sources[text_widget] = {"path": arquivo, "formatter": formatter}

    btn_frame = tk.Frame(container, bg="white")
    btn_frame.pack(padx=10, pady=(0, 10))
    tk.Button(
        btn_frame,
        text="Load",
        command=lambda: forcar_recarregar(text_widgets, info_label),
        bg="white",
        fg="black",
        activebackground="#e6e6e6",
        activeforeground="black",
    ).pack(side=tk.LEFT, padx=6)
    tk.Button(
        btn_frame,
        text="Beckup",
        command=lambda: limpar_dados(text_widgets, info_label),
        bg="white",
        fg="black",
        activebackground="#e6e6e6",
        activeforeground="black",
    ).pack(side=tk.LEFT, padx=6)

    return text_widgets, info_label

# ---------- embutir como Toplevel ----------
def create_monitor_toplevel(master):
    """
    Cria um Toplevel embutido na aplicação principal (não usa mainloop).
    Guarda referência em _monitor_toplevel e atualiza via after.
    """
    global _monitor_toplevel
    if _monitor_toplevel:
        try:
            _monitor_toplevel.lift()
            _monitor_toplevel.focus_force()
        except Exception:
            pass
        return _monitor_toplevel

    # cria Toplevel
    top = tk.Toplevel(master)
    top.title("Monitor de Acessos (embutido)")
    # salvar referência global
    _monitor_toplevel = top

    _set_fullscreen(top)
    text_widgets, info_label = _build_monitor_ui(top)

    # Atualizar via after
    _schedule_update(text_widgets, info_label)

    def on_close():
        # cancela after e destrói
        _cancel_scheduled(text_widgets)
        try:
            top.destroy()
        except Exception:
            pass
        # limpa referência global
        global _monitor_toplevel
        _monitor_toplevel = None

    top.protocol("WM_DELETE_WINDOW", on_close)
    return top

# ---------- standalone (modo original) ----------
def iniciar_monitor_standalone():
    """
    Modo standalone: cria Tk() próprio e roda mainloop.
    Mantém lock file para evitar múltiplas instâncias.
    """
    # lock simples (escreve PID)
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    root = tk.Tk()
    root.title("Monitor de Acessos (standalone)")

    text_widgets, info_label = _build_monitor_ui(root)

    # atualiza via after
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
