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
LOCK_FILE = os.path.join(BASE_DIR, "monitor.lock")
REFRESH_MS = 2000  # 2s

# internal reference to Toplevel (quando embutido)
_monitor_toplevel = None
_monitor_after_id = None

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

# ---------- UI helpers (embutido) ----------
def _populate_text(text_widget, info_label):
    registros = _load_safe(ARQUIVO)
    info_label.config(text=f"Arquivo: {ARQUIVO} — registros: {len(registros)}")
    text_widget.config(state="normal")
    text_widget.delete("1.0", tk.END)
    for r in registros:
        linha = format_creative_entry(r)
        text_widget.insert(tk.END, linha + "\n\n")
    text_widget.config(state="disabled")

def _schedule_update(text_widget, info_label):
    global _monitor_after_id
    _populate_text(text_widget, info_label)
    # schedule next update
    try:
        _monitor_after_id = text_widget.after(REFRESH_MS, lambda: _schedule_update(text_widget, info_label))
    except Exception:
        _monitor_after_id = None

def _cancel_scheduled(text_widget):
    global _monitor_after_id
    try:
        if _monitor_after_id and text_widget:
            text_widget.after_cancel(_monitor_after_id)
    except Exception:
        pass
    _monitor_after_id = None

def forcar_recarregar(text_widget, info_label):
    _populate_text(text_widget, info_label)

def limpar_dados(text_widget, info_label):
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
    _populate_text(text_widget, info_label)

def _set_fullscreen(window):
    try:
        window.state("zoomed")
    except Exception:
        pass
    try:
        window.attributes("-fullscreen", True)
    except Exception:
        pass

def _apply_dark_theme(widget):
    try:
        widget.configure(bg="black")
    except Exception:
        pass

def _build_monitor_ui(container):
    _apply_dark_theme(container)
    style = ttk.Style(container)
    try:
        style.theme_use("default")
    except Exception:
        pass
    style.configure("Dark.TNotebook", background="black", borderwidth=0)
    style.configure("Dark.TNotebook.Tab", background="black", foreground="white")
    style.map("Dark.TNotebook.Tab", background=[("selected", "black")], foreground=[("selected", "white")])

    info_label = tk.Label(container, text=f"Arquivo: {ARQUIVO}", bg="black", fg="white")
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

    text_widget = tk.Text(
        controle_frame,
        wrap="word",
        bg="black",
        fg="white",
        insertbackground="white",
        relief="flat",
    )
    text_widget.pack(padx=10, pady=(8, 8), fill=tk.BOTH, expand=True)
    text_widget.config(state="disabled")

    btn_frame = tk.Frame(container, bg="black")
    btn_frame.pack(padx=10, pady=(0, 10))
    tk.Button(
        btn_frame,
        text="Load",
        command=lambda: forcar_recarregar(text_widget, info_label),
        bg="black",
        fg="white",
        activebackground="gray20",
        activeforeground="white",
    ).pack(side=tk.LEFT, padx=6)
    tk.Button(
        btn_frame,
        text="Beckup",
        command=lambda: limpar_dados(text_widget, info_label),
        bg="black",
        fg="white",
        activebackground="gray20",
        activeforeground="white",
    ).pack(side=tk.LEFT, padx=6)

    return text_widget, info_label

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
    text_widget, info_label = _build_monitor_ui(top)

    # Atualizar via after
    _schedule_update(text_widget, info_label)

    def on_close():
        # cancela after e destrói
        _cancel_scheduled(text_widget)
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

    text_widget, info_label = _build_monitor_ui(root)

    # atualiza via after
    _schedule_update(text_widget, info_label)

    def on_close_standalone():
        _cancel_scheduled(text_widget)
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
