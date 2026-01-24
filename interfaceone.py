# interfaceone.py — interface principal (agora com modo IA interativo)
# Requer: rapidfuzz (pip install rapidfuzz)

import os
import json
import threading
import tempfile
import re
import unicodedata
from datetime import datetime
from collections import Counter
import sys
import shutil

# rapidfuzz
try:
    from rapidfuzz import process as rf_process
    from rapidfuzz import fuzz as rf_fuzz
except Exception as e:
    raise ImportError("rapidfuzz é obrigatório. Instale com: pip install rapidfuzz") from e

# tenta importar ia.responser (pode falhar, temos fallback)
try:
    import ia as ia_module
    HAS_IA_MODULE = True
except Exception:
    ia_module = None
    HAS_IA_MODULE = False

# paths
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "dados")
os.makedirs(DATA_DIR, exist_ok=True)

SUGG_PATH = os.path.join(DATA_DIR, "suggestions.txt")
DB_FILE = os.path.join(BASE, "dadosend.json")
IN_FILE = os.path.join(BASE, "dadosinit.json")
MONITOR_LOCK = os.path.join(BASE, "monitor.lock")

# ---------- util ----------
def _norm_compare(s: str) -> str:
    if not s: return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9\s]", "", s)

def normalize(s: str) -> str:
    if not s: return ""
    s = str(s).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9\s\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokens(text):
    if not text: return []
    return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9\-]+", str(text).strip())

def _is_pid_alive(pid: int) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except Exception:
        return False
    return True

# compute how many characters from suggestion correspond to matched normalized chars
def token_common_prefix_len(token: str, suggestion: str) -> int:
    tn = normalize(token)
    sn = normalize(suggestion)
    i = 0
    while i < len(tn) and i < len(sn) and tn[i] == sn[i]:
        i += 1
    if i == 0:
        return 0
    count = 0
    norm_count = 0
    for ch in suggestion:
        nch = normalize(ch)
        if nch:
            norm_count += len(nch)
        count += 1
        if norm_count >= i:
            break
    return count

# ---------- db helpers ----------
def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            if isinstance(d, dict) and "registros" in d:
                return d["registros"] or []
            if isinstance(d, list):
                return d
    except Exception:
        pass
    return []

def full_name(r):
    n = r.get("NOME","") or ""
    s = r.get("SOBRENOME","") or ""
    return (n + " " + s).strip() or "-"

def details_only(r):
    parts = []
    for k, label in (("BLOCO","BLOCO"),("APARTAMENTO","AP"),("PLACA","PLACA"),
                     ("MODELO","MODELO"),("COR","COR"),("STATUS","STATUS")):
        v = r.get(k) or ""
        if v and v != "-": parts.append(f"{label} {v}")
    return " ".join(parts) if parts else ""

def full_summary(r):
    nome = full_name(r)
    det = details_only(r)
    return f"{nome} — {det}" if det else nome

# ---------- suggestions builder/cache ----------
_db_mtime = 0.0
_sugg_list = []
_sugg_mtime = 0.0

def build_suggestions(max_entries=2000):
    db = load_db()
    if not db:
        if not os.path.exists(SUGG_PATH):
            open(SUGG_PATH, "w", encoding="utf-8").close()
        return
    cnt = Counter()
    rep = {}
    def add(x):
        if not x or not isinstance(x, str): return
        x = x.strip()
        if not x: return
        k = normalize(x)
        if not k: return
        cnt[k] += 1
        if k not in rep or len(x) > len(rep[k]):
            rep[k] = x
    for r in db:
        for k in ("NOME","SOBRENOME","MODELO","COR","STATUS","PLACA","BLOCO","APARTAMENTO"):
            add(r.get(k))
        add(full_name(r))
        add(details_only(r))
        for k in ("NOME","SOBRENOME","MODELO","COR","STATUS","PLACA","BLOCO","APARTAMENTO"):
            v = r.get(k)
            if v:
                for t in tokens(v):
                    add(t)
        for t in tokens(details_only(r)):
            add(t)
    items = sorted(cnt.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    suggs = []
    for k, _ in items:
        v = rep.get(k, k)
        if v not in suggs:
            suggs.append(v)
        if len(suggs) >= max_entries:
            break
    dirn = os.path.dirname(SUGG_PATH) or "."
    fd, tmp = tempfile.mkstemp(dir=dirn, prefix=".tmp_sugg_", suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for s in suggs:
                f.write(s.replace("\n", " ").strip() + "\n")
        os.replace(tmp, SUGG_PATH)
    finally:
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception: pass

def sync_suggestions(force=False):
    global _db_mtime
    try:
        m = os.path.getmtime(DB_FILE) if os.path.exists(DB_FILE) else 0
    except Exception:
        m = 0
    if force or m == 0 or m != _db_mtime or not os.path.exists(SUGG_PATH):
        try: build_suggestions()
        except Exception: pass
        _db_mtime = m

def _load_suggestions(force=False):
    global _sugg_list, _sugg_mtime
    sync_suggestions()
    try:
        m = os.path.getmtime(SUGG_PATH) if os.path.exists(SUGG_PATH) else 0
    except Exception:
        m = 0
    if force or m == 0 or m != _sugg_mtime:
        if os.path.exists(SUGG_PATH):
            try:
                with open(SUGG_PATH, "r", encoding="utf-8") as f:
                    _sugg_list = [ln.strip() for ln in f if ln.strip()]
                    _sugg_mtime = m
            except Exception:
                _sugg_list = []; _sugg_mtime = m
        else:
            _sugg_list = []; _sugg_mtime = m

# provider: rapidfuzz
def provider_suggestions(prefix: str, max_results: int = 6):
    p = (prefix or "").strip()
    if not p: return []
    _load_suggestions()
    if not _sugg_list: return []
    try:
        results = rf_process.extract(p, _sugg_list, scorer=rf_fuzz.WRatio, limit=max_results)
    except Exception:
        return []
    out = []
    for item in results:
        if len(item) >= 2:
            out.append((item[0], float(item[1])))
    return out

def spelling_suggestions_for_token(token: str, max_results: int = 6):
    return [s for s, _ in provider_suggestions(token, max_results)][:max_results]

# ---------- token cache ----------
class TokenCache:
    def __init__(self, db_path):
        self.db_path = db_path
        self.m = 0
        self.map = {}
        self._build()
    def _mtime(self):
        try: return os.path.getmtime(self.db_path)
        except Exception: return 0
    def _build(self):
        m = self._mtime()
        if m == self.m and self.map: return
        self.m = m
        self.map = {}
        for r in load_db():
            def add(orig):
                if not orig or not isinstance(orig, str): return
                for t in tokens(orig):
                    k = normalize(t)
                    if len(k) < 2: continue
                    self.map.setdefault(k, []).append(r)
            add(full_name(r)); add(details_only(r))
            for key in ("NOME","SOBRENOME","MODELO","COR","STATUS","PLACA","BLOCO","APARTAMENTO"):
                add(r.get(key))
    def has(self):
        self._build()
        return bool(self.map)

CACHE = TokenCache(DB_FILE)

# ---------- search ----------
def search_prefix(pref, limit=12):
    if not CACHE.has(): return []
    p = str(pref).strip()
    if not p: return []
    pn = normalize(p)
    res = []; seen = set()
    for r in load_db():
        nome = full_name(r)
        resumo = details_only(r)
        candidates = [nome, resumo] + [r.get(k) or "" for k in ("NOME","SOBRENOME","MODELO","COR","STATUS","PLACA","BLOCO","APARTAMENTO")]
        matched = False
        is_multi = bool(re.search(r"\s+", p))
        if is_multi:
            for txt in candidates[:2]:
                if normalize(txt).startswith(pn):
                    if nome not in seen:
                        res.append((nome, r)); seen.add(nome); matched = True; break
            if matched:
                if len(res) >= limit: break
                continue
        for txt in candidates:
            for t in tokens(txt):
                if normalize(t).startswith(pn):
                    if nome not in seen:
                        res.append((nome, r)); seen.add(nome); matched = True; break
            if matched: break
        if not matched:
            for txt in candidates:
                if normalize(txt).startswith(pn):
                    if nome not in seen:
                        res.append((nome, r)); seen.add(nome); break
        if len(res) >= limit: break
    return res[:limit]

def search_fuzzy(pref, max_results=8):
    if not CACHE.has(): return []
    pn = normalize(pref)
    if not pn: return []
    db = load_db()
    if not db: return []
    reps = []; rep_map = {}
    for r in db:
        rep = full_summary(r)
        if rep not in rep_map:
            rep_map[rep] = r; reps.append(rep)
    try:
        matches = rf_process.extract(pref, reps, scorer=rf_fuzz.WRatio, limit=max_results)
    except Exception:
        return []
    results = []; seen = set()
    for item in matches:
        if len(item) < 2: continue
        rep_text = item[0]
        rec = rep_map.get(rep_text)
        if rec:
            nome = full_name(rec)
            if nome not in seen:
                results.append((nome, rec)); seen.add(nome)
        if len(results) >= max_results: break
    return results

# ---------- UI ----------
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from tkinter import scrolledtext

def common_prefix_len(t, s):
    tn = _norm_compare(t); sn = _norm_compare(s); i = 0
    while i < len(tn) and i < len(sn) and tn[i] == sn[i]:
        i += 1
    if i == 0: return 0
    count = 0; norm_count = 0
    for ch in s:
        nc = _norm_compare(ch)
        if nc: norm_count += len(nc)
        count += 1
        if norm_count >= i: break
    return count

class SuggestEntry(tk.Frame):
    MAX_VISIBLE = 8
    def __init__(self, master):
        super().__init__(master)
        self.entry_var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.entry_var, width=80, font=("Segoe UI", 11))
        self.entry.pack(side=tk.TOP, fill=tk.X)
        self.entry.focus_set()
        self.font = tkfont.Font(font=self.entry["font"])
        entry_bg = self.entry.cget("bg")
        self.overlay = tk.Label(self, text="", anchor="w", font=self.entry["font"], fg="gray65", bg=entry_bg, bd=0)

        # treeview
        self.frame = tk.Frame(self)
        self.sbar = tk.Scrollbar(self.frame, orient=tk.VERTICAL)
        self.tree = ttk.Treeview(self.frame, columns=("nome","detalhes"), show="headings")
        self.tree.heading("nome", text="Nome"); self.tree.heading("detalhes", text="Detalhes")
        self.tree.column("nome", width=220, anchor="w"); self.tree.column("detalhes", width=620, anchor="w")
        self.tree.configure(yscrollcommand=self.sbar.set); self.sbar.config(command=self.tree.yview)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.sbar.pack(side=tk.RIGHT, fill=tk.Y)

        # IA mode state
        self.ia_mode = False            # quando True -> sugestões desativadas; Enter envia para ia.respond_query
        self.ia_waiting_for_query = False  # True quando mostramos "IA INICIADA..." esperando o usuário digitar

        # state
        self.list_visible = False
        self.suggestions = []   # list of (display_name, record)
        self.correction = ""
        self.curr = None
        self.steps = []
        self.step_idx = 0
        self._has_user_navigated = False
        self._just_accepted = False

        # binds
        self.entry.bind("<KeyRelease>", self.on_key)
        self.entry.bind("<Tab>", self.on_tab, add="+")
        self.entry.bind("<Down>", self.on_down, add="+")
        self.entry.bind("<Up>", self.on_up, add="+")
        self.entry.bind("<Return>", self.on_return, add="+")
        self.entry.bind("<Escape>", self.on_escape, add="+")
        self.entry.bind("<Control-space>", lambda e: (self.show_db(), "break"))

        self.tree.bind("<Double-1>", self.on_tree_double)
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<Motion>", self.on_tree_motion)
        self.tree.bind("<Return>", self.on_tree_return)

    def _typed_x(self):
        t = self.entry_var.get().rstrip(); return t, self.font.measure(t)

    def _show_overlay_for_last_token(self, suggestion_text: str, last_token: str):
        cut_chars = token_common_prefix_len(last_token, suggestion_text)
        suffix = suggestion_text[cut_chars:] if cut_chars < len(suggestion_text) else ""
        if not suffix:
            self._hide_overlay(); return
        typed, x = self._typed_x()
        try:
            if self.entry.index("insert") != len(typed):
                self._hide_overlay(); return
        except Exception:
            pass
        self.overlay.config(text=suffix)
        if not getattr(self, "overlay_visible", False):
            self.overlay.place(in_=self.entry, x=x+4, y=1); self.overlay_visible = True
        else:
            self.overlay.place_configure(x=x+4, y=1)

    def _hide_overlay(self):
        if getattr(self, "overlay_visible", False):
            try: self.overlay.place_forget()
            except Exception: pass
            self.overlay_visible = False
        self.overlay.config(text="")

    # handle keys
    def on_key(self, event):
        k = event.keysym
        # If we are in IA waiting state and user types anything (except navigation), clear the placeholder
        if self.ia_waiting_for_query and k not in ("Up","Down","Left","Right","Return","Tab","Escape"):
            # clear placeholder and prepare for typing query
            try:
                self.entry_var.set("")
                self.entry.icursor(0)
            except Exception:
                pass
            self.ia_waiting_for_query = False
            # keep ia_mode True; suggestions remain disabled until exit

        # If IA mode active -> do not show suggestions (just let user type)
        if self.ia_mode:
            # reset navigation flags but avoid suggestions
            if k not in ("Up","Down"):
                self._just_accepted = False
            return

        # normal suggestion behaviour
        if k in ("Up","Down","Left","Right","Return","Tab","Escape"):
            if k not in ("Up","Down"):
                self._just_accepted = False
            return
        self._has_user_navigated = False
        self._just_accepted = False
        for sel in list(self.tree.selection()):
            try: self.tree.selection_remove(sel)
            except Exception: pass

        typed = self.entry_var.get()
        if not typed.strip():
            self.hide_list(); self._hide_overlay(); return

        tok_list = tokens(typed)
        last_token = tok_list[-1] if tok_list else typed.strip()
        suggestions = spelling_suggestions_for_token(last_token, max_results=4)
        if suggestions:
            best = suggestions[0]
            self._show_overlay_for_last_token(best, last_token)
            self.correction = best
        else:
            self.correction = ""
            self._hide_overlay()

        try:
            self.show_db()
        except Exception:
            pass

    def on_tab(self, event):
        # If IA mode active -> ignore tab completions
        if self.ia_mode:
            return "break"

        # If overlay exists (for last token) -> accept overlay (append suffix to last token)
        if self.correction:
            typed = self.entry_var.get()
            tok_list = tokens(typed)
            last_token = tok_list[-1] if tok_list else typed
            cut = token_common_prefix_len(last_token, self.correction)
            suffix = self.correction[cut:] if cut < len(self.correction) else ""
            if suffix:
                if typed.endswith(last_token):
                    new_text = typed + suffix
                else:
                    new_text = typed + " " + suffix
                self.entry_var.set(new_text.strip())
            self._hide_overlay()
            self.correction = ""
            try: self.show_db()
            except: pass
            self._just_accepted = True
            return "break"

        # If list visible and selection exists -> accept name and apply first step (if any)
        if self.list_visible:
            sel = self.tree.selection()
            if sel:
                try: idx = int(sel[0])
                except: idx = 0
                self._accept_into_entry(idx, hide=False)
                # apply first step (if exists)
                if self.step_idx < len(self.steps):
                    token = self.steps[self.step_idx]
                    self._apply_step_token(token)
                    self.step_idx += 1
                try: self.show_db()
                except: pass
                self._just_accepted = True
                return "break"
            return "break"

        current = self.entry_var.get().strip()
        if current:
            return None
        else:
            return "break"

    def on_down(self, event):
        if self.list_visible:
            ch = self.tree.get_children(); size = len(ch)
            if size == 0: return "break"
            sel = self.tree.selection()
            if sel:
                try: cur = int(sel[0])
                except: cur = -1
                idx = (cur + 1) % size
            else:
                idx = 0
            iid = ch[idx]
            self.tree.selection_set(iid); self.tree.focus(iid); self.tree.see(iid)
            self._has_user_navigated = True
            return "break"
        return None

    def on_up(self, event):
        if self.list_visible:
            ch = self.tree.get_children(); size = len(ch)
            if size == 0: return "break"
            sel = self.tree.selection()
            if sel:
                try: cur = int(sel[0])
                except: cur = 0
                idx = (cur - 1) % size
            else:
                idx = len(ch) - 1
            iid = ch[idx]
            self.tree.selection_set(iid); self.tree.focus(iid); self.tree.see(iid)
            self._has_user_navigated = True
            return "break"
        return None

    def on_return(self, event):
        # If not IA mode: check activation or normal behaviour
        text = (self.entry_var.get() or "").strip()

        # detect activation token: only token like "ia" or "ai" optionally followed by punctuation
        if not self.ia_mode:
            if re.fullmatch(r"\s*(ia|ai|IA|Ai|Ai\.)\s*|^(ia|ai)[,\.\s]*$", text, flags=re.IGNORECASE) or re.match(r"^\s*(ia|ai)\b", text, flags=re.IGNORECASE):
                # Activate IA mode: show placeholder "IA INICIADA..."
                self.ia_mode = True
                self.ia_waiting_for_query = True
                try:
                    self.entry_var.set("IA INICIADA...")
                    self.entry.icursor(len(self.entry_var.get()))
                    self.entry.select_clear()
                    self.entry.focus_set()
                except Exception:
                    pass
                # hide suggestions overlay/list
                self._hide_overlay()
                self.hide_list()
                return "break"

        # If IA mode active:
        if self.ia_mode:
            # If entry currently has the waiting placeholder, ignore
            if self.ia_waiting_for_query:
                return "break"
            # If user typed 'sair' or 'exit' -> exit IA mode
            if text.lower() in ("sair", "exit", "fim", "close"):
                self.ia_mode = False
                self.ia_waiting_for_query = False
                try:
                    # clear entry
                    self.entry_var.set("")
                    self.entry.icursor(0)
                    self.entry.focus_set()
                except Exception:
                    pass
                return "break"

            # Otherwise send query to IA (spawn thread)
            query_text = text
            self.entry_var.set("")  # limpa campo para próxima pergunta
            self.entry.icursor(0)
            # spawn background thread
            threading.Thread(target=self._send_query_to_ia_thread, args=(query_text,), daemon=True).start()
            return "break"

        # Normal non-IA enter behavior:
        if self.list_visible:
            sel = self.tree.selection()
            if sel:
                try: idx = int(sel[0])
                except: idx = 0
                self._accept_into_entry(idx, hide=True, append_all=True)
                try: self.show_db()
                except: pass
                self._just_accepted = True
                return "break"
            else:
                try: save_text(entry_widget=self.entry)
                except Exception: pass
                return "break"
        else:
            try: save_text(entry_widget=self.entry)
            except Exception: pass
            return "break"

    def _send_query_to_ia_thread(self, query_text: str):
        """
        Thread worker: chama ia_module.respond_query e exibe resultado em Toplevel no thread principal.
        """
        # call IA
        if HAS_IA_MODULE and hasattr(ia_module, "respond_query"):
            try:
                resp = ia_module.respond_query(query_text)
            except Exception as e:
                resp = f"Erro ao consultar IA: {e}"
        else:
            # fallback: simples busca local quando módulo ia não disponível
            try:
                registros = load_db()
                # formato simples: listar registros contendo tokens da query
                tokens_q = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", query_text)]
                found = []
                for r in registros:
                    text_fields = " ".join([str(r.get(k,"")) for k in ("NOME","SOBRENOME","BLOCO","APARTAMENTO","PLACA","STATUS","DATA_HORA")]).lower()
                    if all(tok in text_fields for tok in tokens_q):
                        found.append(r)
                if not found:
                    resp = "Nenhum resultado encontrado (fallback local)."
                else:
                    lines = []
                    for rec in found[:200]:
                        lines.append(f"{rec.get('DATA_HORA','-')} | {rec.get('NOME','-')} {rec.get('SOBRENOME','-')} | BLOCO {rec.get('BLOCO','-')} AP {rec.get('APARTAMENTO','-')} | PLACA {rec.get('PLACA','-')} | {rec.get('STATUS','-')}")
                    resp = f"Resultados ({len(found)}):\n" + "\n".join(lines)
            except Exception as e:
                resp = f"Erro no fallback local: {e}"

        # schedule UI creation on main thread
        try:
            root = self._root_for_ui()
            if root:
                root.after(0, lambda r=resp: self._show_ia_response_window(r))
            else:
                # if we can't get root, just print
                print(resp)
        except Exception:
            print(resp)

    def _root_for_ui(self):
        # traverse up to find root window
        try:
            w = self
            while w.master is not None:
                w = w.master
            return w
        except Exception:
            return None

    def _show_ia_response_window(self, text: str):
        # Cria um Toplevel simples com scrolledtext mostrando a resposta
        try:
            root = self._root_for_ui()
            if root is None:
                print(text)
                return
            top = tk.Toplevel(root)
            top.title("Resposta IA")
            top.geometry("700x400")
            st = scrolledtext.ScrolledText(top, wrap=tk.WORD)
            st.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
            st.insert(tk.END, text)
            st.configure(state="disabled")
            # botão fechar
            btn = tk.Button(top, text="Fechar", command=top.destroy)
            btn.pack(pady=(0,8))
        except Exception as e:
            print("Erro ao abrir janela de resposta IA:", e)
            print(text)

    def on_escape(self, event):
        # se em IA mode, esc cancela IA e limpa
        if self.ia_mode:
            self.ia_mode = False
            self.ia_waiting_for_query = False
            try:
                self.entry_var.set("")
                self.entry.icursor(0)
            except Exception:
                pass
            return
        self.hide_list(); self._hide_overlay(); self.correction = ""
        self._has_user_navigated = False; self._just_accepted = False

    # tree handlers (sem alteração)
    def on_tree_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            try: self.tree.selection_set(row)
            except Exception: pass
            self._has_user_navigated = True
        return None

    def on_tree_double(self, event):
        row = self.tree.identify_row(event.y)
        if not row: return
        try: idx = int(row)
        except: idx = 0
        self._accept_into_entry(idx, hide=True, append_all=True)
        try: self.show_db()
        except: pass
        self._just_accepted = True

    def on_tree_motion(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            try: self.tree.selection_set(row)
            except Exception: pass
            self.tree.focus(row); self._has_user_navigated = True

    def on_tree_return(self, event):
        return self.on_return(event)

    # accept helpers (mantidos, mas respeitam ia_mode onde aplicável)
    def _accept_into_entry(self, idx, hide=False, append_all=False):
        if idx < 0 or idx >= len(self.suggestions): return
        disp, rec = self.suggestions[idx]
        name_text = full_name(rec)
        self.entry_var.set(name_text)
        try:
            self.entry.icursor(len(name_text)); self.entry.select_clear(); self.entry.focus_set()
        except Exception:
            pass
        steps = []
        for k in ("BLOCO","APARTAMENTO","PLACA","MODELO","COR","STATUS"):
            v = rec.get(k) or ""
            if v and v != "-":
                if k == "BLOCO": steps.append(f"BLOCO {v}")
                elif k == "APARTAMENTO": steps.append(f"AP {v}")
                elif k == "PLACA": steps.append(f"PLACA {v}")
                else: steps.append(f"{v}")
        self.curr = rec; self.steps = steps; self.step_idx = 0
        if append_all and steps:
            for token in steps:
                self._apply_step_token(token)
            self._hide_overlay()
        elif steps:
            t, x = self._typed_x()
            self.overlay.place_configure(x=x+4, y=1)
            self.overlay.config(text=steps[0])
            self.overlay_visible = True
        else:
            self._hide_overlay()
        if hide:
            self.hide_list()
        try: self.show_db()
        except: pass

    def _apply_step_token(self, token):
        current = self.entry_var.get().strip()
        if current.upper().endswith(token.upper()):
            return
        new_text = f"{current} {token}".strip()
        self.entry_var.set(new_text)
        try:
            self.entry.icursor(len(new_text)); self.entry.select_clear(); self.entry.focus_set()
        except Exception:
            pass
        if self.step_idx + 1 < len(self.steps):
            next_hint = self.steps[self.step_idx + 1]
            x = self.font.measure(new_text)
            self.overlay.place_configure(x=x+4, y=1)
            self.overlay.config(text=next_hint)
            self.overlay_visible = True
        else:
            self._hide_overlay()
        try: self.show_db()
        except: pass

    # show/hide list
    def show_list(self, matches):
        for it in self.tree.get_children():
            self.tree.delete(it)
        for i, (disp, rec) in enumerate(matches):
            nome = full_name(rec)
            det = details_only(rec)
            self.tree.insert("", "end", str(i), values=(nome, det))
        visible = min(len(matches), self.MAX_VISIBLE) if matches else 0
        if visible <= 0:
            self.hide_list(); return
        try:
            self.tree.configure(height=visible)
        except Exception:
            pass
        for sel in list(self.tree.selection()):
            try: self.tree.selection_remove(sel)
            except Exception: pass
        if not self.list_visible:
            self.frame.pack(side=tk.TOP, fill=tk.X, pady=(4,0))
            self.list_visible = True
        self._has_user_navigated = False
        self._just_accepted = False

    def hide_list(self):
        if self.list_visible:
            self.frame.pack_forget(); self.list_visible = False
        for it in self.tree.get_children():
            self.tree.delete(it)
        self._has_user_navigated = False
        self._just_accepted = False

    def show_db(self):
        # if IA mode active, do not show DB suggestions
        if self.ia_mode:
            self.hide_list()
            self._hide_overlay()
            return

        typed = self.entry_var.get().strip()
        if not typed:
            self.hide_list(); return
        matches = search_prefix(typed)
        if not matches:
            matches = search_fuzzy(typed)
        if matches:
            self.suggestions = matches
            self.show_list(matches)
        else:
            self.hide_list()

# ---------- atomic save/load ----------
def load_in():
    try:
        with open(IN_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            if isinstance(d, dict) and "registros" in d: return d
            if isinstance(d, list): return {"registros": d}
    except Exception:
        pass
    return {"registros": []}

def atomic_save(path, obj):
    dirn = os.path.dirname(path) or "."
    os.makedirs(dirn, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=dirn, prefix=".tmp_", suffix=".json", delete=False) as tf:
            tmp = tf.name
            json.dump(obj, tf, ensure_ascii=False, indent=4)
            tf.flush()
        os.replace(tmp, path)
    finally:
        if tmp and os.path.exists(tmp):
            try: os.remove(tmp)
            except Exception: pass

# optional IA batch processor
try:
    from ia import processar
    IA = True
except Exception:
    IA = False

def save_text(entry_widget=None, btn=None):
    if entry_widget is None: return
    txt = entry_widget.get().strip()
    if not txt: return
    data = load_in()
    nid = len(data.get("registros", [])) + 1
    data.setdefault("registros", []).append({
        "id": nid,
        "texto": txt,
        "processado": False,
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })
    try:
        atomic_save(IN_FILE, data)
    except Exception as e:
        print("Erro save:", e)
    try:
        entry_widget.delete(0, "end")
    except Exception:
        pass
    if btn:
        try:
            btn.config(state="disabled")
            entry_widget.after(500, lambda: btn.config(state="normal"))
        except Exception:
            pass
    if IA:
        try: threading.Thread(target=processar, daemon=True).start()
        except Exception: pass
    try: threading.Thread(target=sync_suggestions, kwargs={"force": True}, daemon=True).start()
    except Exception: pass

# ---------- open monitor fallback (mantido) ----------
def open_monitor_fallback_subprocess():
    try:
        import subprocess
        target = os.path.join(os.path.dirname(__file__), "interfacetwo.py")
        if not os.path.exists(target):
            print("interfacetwo.py não encontrado em:", target)
            return
        # tenta pythonw.exe
        pythonw = None
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, "executable", None) else None
        if exe_dir:
            candidate = os.path.join(exe_dir, "pythonw.exe")
            if os.path.exists(candidate):
                pythonw = candidate
        if pythonw:
            subprocess.Popen([pythonw, target],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             start_new_session=True)
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

# ---------- main UI ----------
def start_ui():
    import tkinter as tk
    root = tk.Tk(); root.title("Controle de Acesso")
    container = tk.Frame(root); container.pack(padx=10, pady=10)
    s = SuggestEntry(container); s.pack(fill=tk.X)
    btn_frame = tk.Frame(root); btn_frame.pack(padx=10, pady=(8,10))
    btn_save = tk.Button(btn_frame, text="SALVAR", width=12, command=lambda: save_text(entry_widget=s.entry, btn=btn_save))
    btn_save.pack(side=tk.LEFT, padx=(0,8))

    def open_monitor_embedded():
        try:
            import interfacetwo
            if getattr(interfacetwo, "_monitor_toplevel", None):
                try:
                    interfacetwo._monitor_toplevel.lift()
                    interfacetwo._monitor_toplevel.focus_force()
                except Exception:
                    pass
                return
            interfacetwo.create_monitor_toplevel(root)
        except Exception as e:
            print("Falha ao embutir monitor (abrindo fallback):", e)
            open_monitor_fallback_subprocess()

    btn_dados = tk.Button(btn_frame, text="DADOS", width=12, command=open_monitor_embedded)
    btn_dados.pack(side=tk.LEFT)
    def ctrl_enter(ev):
        if s.list_visible:
            sel = s.tree.selection()
            if sel:
                try: idx = int(sel[0])
                except: idx = 0
                s._accept_into_entry(idx, hide=True, append_all=True)
                s._just_accepted = True
                return "break"
            else:
                save_text(entry_widget=s.entry, btn=btn_save); return "break"
        save_text(entry_widget=s.entry, btn=btn_save); return "break"
    root.bind("<Control-Return>", ctrl_enter)
    root.bind("<Escape>", lambda e: (s.hide_list(), s._hide_overlay()))
    try: sync_suggestions()
    except Exception: pass
    root.mainloop()

def iniciar_interface_principal():
    return start_ui()

if __name__ == "__main__":
    iniciar_interface_principal()
