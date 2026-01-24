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
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(BASE_DIR, "dadosend.json")
LOCK_FILE = os.path.join(BASE_DIR, "monitor.lock")
REFRESH_MS = 2000  # 2s

# internal reference to Toplevel (quando embutido)
_monitor_toplevel = None
_monitor_after_id = None

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
    return (
        f"{safe(r.get('DATA_HORA'))} | "
        f"{safe(r.get('NOME'))} {safe(r.get('SOBRENOME'))} | "
        f"BLOCO {safe(r.get('BLOCO'))} APARTAMENTO {safe(r.get('APARTAMENTO'))} | "
        f"PLACA {safe(r.get('PLACA'))} | "
        f"{safe(r.get('MODELO'))} | "
        f"{safe(r.get('COR'))} | "
        f"{safe(r.get('STATUS'))}"
    )

# ---------- UI helpers (embutido) ----------
def _populate_listbox(lista_widget, info_label):
    registros = _load_safe(ARQUIVO)
    info_label.config(text=f"Arquivo: {ARQUIVO} — registros: {len(registros)}")
    lista_widget.delete(0, tk.END)
    for r in registros:
        linha = format_line(r)
        lista_widget.insert(tk.END, linha)

def _schedule_update(lista_widget, info_label):
    global _monitor_after_id
    _populate_listbox(lista_widget, info_label)
    # schedule next update
    try:
        _monitor_after_id = lista_widget.after(REFRESH_MS, lambda: _schedule_update(lista_widget, info_label))
    except Exception:
        _monitor_after_id = None

def _cancel_scheduled(lista_widget):
    global _monitor_after_id
    try:
        if _monitor_after_id and lista_widget:
            lista_widget.after_cancel(_monitor_after_id)
    except Exception:
        pass
    _monitor_after_id = None

def forcar_recarregar(lista_widget, info_label):
    _populate_listbox(lista_widget, info_label)

def limpar_dados(lista_widget, info_label):
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
    _populate_listbox(lista_widget, info_label)

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

    info_label = tk.Label(top, text=f"Arquivo: {ARQUIVO}")
    info_label.pack(padx=10, pady=(6,0), anchor="w")

    lista = tk.Listbox(top, width=160)
    lista.pack(padx=10, pady=(2,6))

    btn_frame = tk.Frame(top)
    btn_frame.pack(padx=10, pady=(0,10))
    tk.Button(btn_frame, text="Forçar recarregar", command=lambda: forcar_recarregar(lista, info_label)).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="Limpar (backup + vazio)", command=lambda: limpar_dados(lista, info_label)).pack(side=tk.LEFT, padx=6)

    # Atualizar via after
    _schedule_update(lista, info_label)

    def on_close():
        # cancela after e destrói
        _cancel_scheduled(lista)
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

    info_label = tk.Label(root, text=f"Arquivo: {ARQUIVO}")
    info_label.pack(padx=10, pady=(6,0), anchor="w")

    lista = tk.Listbox(root, width=160)
    lista.pack(padx=10, pady=(2,6))

    btn_frame = tk.Frame(root)
    btn_frame.pack(padx=10, pady=(0,10))
    tk.Button(btn_frame, text="Forçar recarregar", command=lambda: forcar_recarregar(lista, info_label)).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="Limpar (backup + vazio)", command=lambda: limpar_dados(lista, info_label)).pack(side=tk.LEFT, padx=6)

    # atualiza via after
    _schedule_update(lista, info_label)

    def on_close_standalone():
        _cancel_scheduled(lista)
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
