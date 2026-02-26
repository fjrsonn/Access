# interfacetwo.py — monitor (suporta modo embutido via create_monitor_toplevel)
"""
Monitor de dados:
- Pode ser embutido via create_monitor_toplevel(master)
- Ou executado standalone (python interfacetwo.py)
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import re
import hashlib
import math

from ui_theme import (
    UI_THEME,
    build_card_frame,
    build_primary_button,
    build_secondary_button,
    build_secondary_warning_button,
    build_secondary_danger_button,
    build_filter_input,
    build_label,
    build_badge,
    theme_font,
    theme_space,
    refresh_theme,
    apply_ttk_theme_styles,
    attach_tooltip,
    bind_focus_ring,
    bind_button_states,
    apply_theme,
    get_active_theme_name,
    validate_theme_contrast,
    state_colors,
)

try:
    from ui_components import AppMetricCard, AppStatusBar, AppFeedbackBanner, build_section_title
except Exception:
    class AppMetricCard(tk.Frame):
        def __init__(self, parent, title: str, value: str = "0", tone: str = "info", icon: str = "●"):
            super().__init__(parent, bg=UI_THEME.get("surface", "#151A22"), highlightthickness=1, highlightbackground=UI_THEME.get("border", "#2B3442"), bd=0)
            self.value_var = tk.StringVar(value=str(value))
            self.meta_var = tk.StringVar(value="Atualizado agora")
            self._tone = tone
            self._title = title
            self._icon = icon
            self._label = tk.Label(self, text=f"{icon} {title}", anchor="w", bg=self.cget("bg"), fg=UI_THEME.get("muted_text", "#9AA4B2"), font=theme_font("font_sm"))
            self._label.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(theme_space("space_1", 4), 0))
            self._value = tk.Label(self, textvariable=self.value_var, anchor="w", bg=self.cget("bg"), fg=state_colors(tone)[0], font=theme_font("font_xl", "bold"))
            self._value.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(0, theme_space("space_1", 4)))

        def set_value(self, value: str):
            self.value_var.set(str(value))

        def set_trend(self, _delta):
            return None

        def set_capacity(self, _used, _limit):
            return None

        def set_meta(self, text: str):
            self.meta_var.set(str(text))

        def flash(self, _duration_ms=220):
            return None

        def set_density(self, _mode: str = "confortavel"):
            return None

        def set_donut_visibility(self, _visible: bool):
            return None

        def animate_capacity_fill(self, on_done=None, **_kwargs):
            if callable(on_done):
                on_done()

        def animate_accent_growth(self, on_done=None, **_kwargs):
            if callable(on_done):
                on_done()

    class AppStatusBar(tk.Frame):
        def __init__(self, parent, text: str = ""):
            super().__init__(parent, bg=UI_THEME.get("surface_alt", "#1B2430"), highlightthickness=1, highlightbackground=UI_THEME.get("border", "#2B3442"))
            self.var = tk.StringVar(value=text)
            self.lbl = tk.Label(self, textvariable=self.var, anchor="w", bg=self.cget("bg"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), font=theme_font("font_sm"))
            self.lbl.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=theme_space("space_1", 4))

        def set(self, text: str, tone: str = "info"):
            self.var.set(text)
            bg, fg = state_colors(tone)
            self.configure(bg=bg)
            self.lbl.configure(bg=bg, fg=fg)

    class AppFeedbackBanner(AppStatusBar):
        def show(self, text: str, tone: str = "info", icon: str = "ℹ", timeout_ms: int = 2200):
            self.set(f"{icon} {text}".strip(), tone=tone)

        def hide(self):
            return None

    def build_section_title(parent, text: str):
        return tk.Label(parent, text=text, bg=UI_THEME.get("bg", "#0F1115"), fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")), font=theme_font("font_xl", "bold"), anchor="w")

try:
    from text_classifier import build_structured_fields, log_audit_event
except Exception:
    build_structured_fields = None
    log_audit_event = None


try:
    from runtime_status import get_last_status, report_status, analisar_metricas_ux
except Exception:
    def get_last_status():
        return {}
    def report_status(*args, **kwargs):
        return None
    def analisar_metricas_ux(*args, **kwargs):
        return {}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(BASE_DIR, "dadosend.json")
ENCOMENDAS_ARQUIVO = os.path.join(BASE_DIR, "encomendasend.json")
ORIENTACOES_ARQUIVO = os.path.join(BASE_DIR, "orientacoes.json")
OBSERVACOES_ARQUIVO = os.path.join(BASE_DIR, "observacoes.json")
ANALISES_ARQUIVO = os.path.join(BASE_DIR, "analises.json")
AVISOS_ARQUIVO = os.path.join(BASE_DIR, "avisos.json")
LOCK_FILE = os.path.join(BASE_DIR, "monitor.lock")
REFRESH_MS = 2000  # 2s
PREFS_FILE = os.path.join(BASE_DIR, "config", "ui_monitor_prefs.json")
CONSUMO_24H_FILE = os.path.join(BASE_DIR, "config", "consumo_24h.json")
CARD_CAPACITY_LIMITS = {
    "ativos": 1500,
    "pendentes": 1200,
    "sem_contato": 800,
    "avisado": 1000,
}

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
_restored_control_sort_state = {}
_pending_focus_identity = None
_ux_cards = {}
_status_bar = None
_feedback_banner = None
_metrics_previous_cards = {}
_last_filter_snapshot = {}
_filter_auto_apply_after = {}
_layout_density_mode = "confortavel"
_operation_mode_enabled = False
_runtime_refresh_ms = REFRESH_MS
_cards_last_update_at = None
_control_filtered_count_var = None
_control_toolbar = None
_last_quick_filter_kind = None
_metrics_accessibility_var = None
_filter_bars = {}
_filter_toggle_buttons = {}
_filter_toggle_state = {"visible": False}
_text_breakpoints = {}
_text_hover_marker = {}
_record_num_tag_map = {}
_text_record_ranges = {}
_sticky_header_state = {}
_consumo_24h_por_dia = {}


def _gerar_consumo_24h_base(day_key: str) -> list[int]:
    digest = hashlib.sha256(day_key.encode("utf-8")).hexdigest()
    values = []
    for hour in range(24):
        seed = int(digest[(hour % 16) * 4:((hour % 16) * 4) + 4], 16)
        wave = 22 + int(13 * (1 + math.sin((hour / 24) * 6.28318 - 1.0)))
        noise = seed % 16
        values.append(max(0, min(100, wave + noise)))
    return values


def _normalizar_24h(points) -> list[int]:
    base = [0] * 24
    src = list(points or [])[:24]
    for idx, val in enumerate(src):
        try:
            base[idx] = max(0, min(100, int(val)))
        except Exception:
            base[idx] = 0
    return base


def _save_consumo_24h_data():
    try:
        os.makedirs(os.path.dirname(CONSUMO_24H_FILE), exist_ok=True)
        with open(CONSUMO_24H_FILE, "w", encoding="utf-8") as f:
            json.dump(_consumo_24h_por_dia, f, ensure_ascii=False, indent=2)
    except Exception:
        return


def _load_consumo_24h_data():
    global _consumo_24h_por_dia
    if _consumo_24h_por_dia:
        return
    data = {}
    try:
        with open(CONSUMO_24H_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for day_key, points in raw.items():
                data[str(day_key)] = _normalizar_24h(points)
    except Exception:
        data = {}

    if not data:
        today = datetime.now().date()
        for back in range(13, -1, -1):
            d = (today - timedelta(days=back)).strftime("%Y-%m-%d")
            data[d] = _gerar_consumo_24h_base(d)
        _consumo_24h_por_dia = data
        _save_consumo_24h_data()
        return

    _consumo_24h_por_dia = data


def _carregar_consumo_24h(day_key: str) -> list[int]:
    _load_consumo_24h_data()
    points = _consumo_24h_por_dia.get(day_key)
    if points is None:
        points = _gerar_consumo_24h_base(day_key)
        _consumo_24h_por_dia[day_key] = points
        _save_consumo_24h_data()
    return list(points)



_consumo_24h_por_dia = {}


def _gerar_consumo_24h_base(day_key: str) -> list[int]:
    digest = hashlib.sha256(day_key.encode("utf-8")).hexdigest()
    values = []
    for hour in range(24):
        seed = int(digest[(hour % 16) * 4:((hour % 16) * 4) + 4], 16)
        wave = 22 + int(13 * (1 + math.sin((hour / 24) * 6.28318 - 1.0)))
        noise = seed % 16
        values.append(max(0, min(100, wave + noise)))
    return values


def _normalizar_24h(points) -> list[int]:
    base = [0] * 24
    src = list(points or [])[:24]
    for idx, val in enumerate(src):
        try:
            base[idx] = max(0, min(100, int(val)))
        except Exception:
            base[idx] = 0
    return base


def _save_consumo_24h_data():
    try:
        os.makedirs(os.path.dirname(CONSUMO_24H_FILE), exist_ok=True)
        with open(CONSUMO_24H_FILE, "w", encoding="utf-8") as f:
            json.dump(_consumo_24h_por_dia, f, ensure_ascii=False, indent=2)
    except Exception:
        return


def _load_consumo_24h_data():
    global _consumo_24h_por_dia
    if _consumo_24h_por_dia:
        return
    data = {}
    try:
        with open(CONSUMO_24H_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for day_key, points in raw.items():
                data[str(day_key)] = _normalizar_24h(points)
    except Exception:
        data = {}

    if not data:
        today = datetime.now().date()
        for back in range(13, -1, -1):
            day_key = (today - timedelta(days=back)).strftime("%Y-%m-%d")
            data[day_key] = _gerar_consumo_24h_base(day_key)
        _consumo_24h_por_dia = data
        _save_consumo_24h_data()
        return

    _consumo_24h_por_dia = data


def _carregar_consumo_24h(day_key: str) -> list[int]:
    _load_consumo_24h_data()
    points = _consumo_24h_por_dia.get(day_key)
    if points is None:
        points = _gerar_consumo_24h_base(day_key)
        _consumo_24h_por_dia[day_key] = points
        _save_consumo_24h_data()
    return list(points)





def _summarize_sticky_header(formatter, record: dict, position: int | None = None) -> str:
    try:
        base = formatter(record) if callable(formatter) else str(record or "")
    except Exception:
        base = str(record or "")
    txt = re.sub(r"\s+", " ", str(base or "")).strip()
    if position is None:
        return txt or "Sem contexto visível"
    return f"  {position + 1:>3}  {txt or 'Sem contexto visível'}"


def _update_sticky_header_for_text(text_widget):
    state = _sticky_header_state.get(text_widget)
    if not state:
        return
    var = state.get("var")
    formatter = state.get("formatter")
    if var is None:
        return
    ranges = _text_record_ranges.get(text_widget) or []
    if not ranges:
        var.set("Sem registros visíveis")
        return
    try:
        top_idx = text_widget.index("@0,0")
    except Exception:
        return

    current = None
    current_pos = 0
    for pos, (start, end, rec) in enumerate(ranges):
        try:
            if text_widget.compare(start, "<=", top_idx) and text_widget.compare(top_idx, "<", end):
                current = rec
                current_pos = pos
                break
            if text_widget.compare(start, "<=", top_idx):
                current = rec
                current_pos = pos
        except Exception:
            continue
    if current is None:
        current = ranges[0][2]
        current_pos = 0
    var.set(_summarize_sticky_header(formatter, current, current_pos))


def _bind_sticky_header_updates(text_widget):
    try:
        text_widget.configure(yscrollcommand=lambda *_: _update_sticky_header_for_text(text_widget))
    except Exception:
        pass

    for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>", "<KeyRelease>", "<Configure>"):
        try:
            text_widget.bind(seq, lambda _e, tw=text_widget: _update_sticky_header_for_text(tw), add="+")
        except Exception:
            pass

def _load_prefs():
    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_prefs(payload: dict):
    try:
        os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _serialize_filter_state():
    out = {}
    for key, val in _filter_state.items():
        out[str(key)] = dict(val or {})
    return out


def _restore_filter_state(snapshot: dict):
    if not isinstance(snapshot, dict):
        return
    for key, val in snapshot.items():
        _filter_state[key] = dict(val or {})


def _persist_ui_state(extra: dict | None = None):
    payload = _load_prefs()
    payload["theme"] = get_active_theme_name()
    payload["filter_state"] = _serialize_filter_state()
    payload["control_sort_state"] = {
        str(k): dict(v or {}) for k, v in _control_sort_state.items()
    }
    if extra:
        payload.update(extra)
    _save_prefs(payload)


def _restore_ui_state():
    global _restored_control_sort_state
    prefs = _load_prefs()
    apply_theme(prefs.get("theme") or get_active_theme_name())
    _restore_filter_state(prefs.get("filter_state") or {})
    restored_sort = prefs.get("control_sort_state") or {}
    _restored_control_sort_state = dict(restored_sort) if isinstance(restored_sort, dict) else {}
    return prefs



def _get_filter_presets() -> dict:
    prefs = _load_prefs()
    presets = prefs.get("filter_presets") or {}
    return dict(presets) if isinstance(presets, dict) else {}


def _save_filter_presets(presets: dict):
    payload = _load_prefs()
    payload["filter_presets"] = dict(presets or {})
    _save_prefs(payload)


def _get_filter_default_preset(filter_key: str) -> str:
    prefs = _load_prefs()
    defaults = prefs.get("filter_default_presets") or {}
    if not isinstance(defaults, dict):
        return ""
    return str(defaults.get(str(filter_key)) or "").strip()


def _set_filter_default_preset(filter_key: str, preset_name: str):
    payload = _load_prefs()
    defaults = payload.get("filter_default_presets") or {}
    if not isinstance(defaults, dict):
        defaults = {}
    name = str(preset_name or "").strip()
    if name:
        defaults[str(filter_key)] = name
    else:
        defaults.pop(str(filter_key), None)
    payload["filter_default_presets"] = defaults
    _save_prefs(payload)


def _rename_filter_preset(old_name: str, new_name: str) -> bool:
    old_name = str(old_name or "").strip()
    new_name = str(new_name or "").strip()
    if not old_name or not new_name or old_name == new_name:
        return False
    payload = _load_prefs()
    presets = payload.get("filter_presets") or {}
    if not isinstance(presets, dict) or old_name not in presets:
        return False
    if new_name in presets:
        return False
    presets[new_name] = presets.pop(old_name)
    payload["filter_presets"] = presets
    defaults = payload.get("filter_default_presets") or {}
    if isinstance(defaults, dict):
        payload["filter_default_presets"] = {
            str(k): (new_name if str(v) == old_name else v)
            for k, v in defaults.items()
        }
    _save_prefs(payload)
    return True


def _delete_filter_preset(name: str):
    name = str(name or "").strip()
    if not name:
        return
    payload = _load_prefs()
    presets = payload.get("filter_presets") or {}
    if isinstance(presets, dict):
        presets.pop(name, None)
        payload["filter_presets"] = presets
    defaults = payload.get("filter_default_presets") or {}
    if isinstance(defaults, dict):
        payload["filter_default_presets"] = {
            str(k): v for k, v in defaults.items() if str(v) != name
        }
    _save_prefs(payload)


def _collect_status_cards_data() -> dict:
    try:
        analises = _load_safe(ANALISES_ARQUIVO)
        avisos = _load_safe(AVISOS_ARQUIVO)
        encomendas = _load_safe(ENCOMENDAS_ARQUIVO)
        controle = _load_safe(ARQUIVO)
    except Exception:
        analises, avisos, encomendas, controle = [], [], [], []

    pendentes = 0
    sem_contato = 0
    avisado = 0
    alta_severidade = 0

    def _status_text(rec: dict) -> str:
        if not isinstance(rec, dict):
            return ""
        return str(
            rec.get("STATUS_ENCOMENDA")
            or rec.get("status_encomenda")
            or rec.get("STATUS")
            or rec.get("status")
            or ""
        ).upper().strip()

    for r in analises if isinstance(analises, list) else []:
        sev = str((r or {}).get("severidade") or (r or {}).get("SEVERIDADE") or "").lower()
        if sev in {"alta", "crítica", "critica"}:
            pendentes += 1
            alta_severidade += 1

    for aviso in avisos if isinstance(avisos, list) else []:
        status_obj = (aviso or {}).get("status")
        if isinstance(status_obj, dict):
            ativo = bool(status_obj.get("ativo", False))
            fechado = bool(status_obj.get("fechado_pelo_usuario", False))
            if ativo and not fechado:
                pendentes += 1
        else:
            txt = str(status_obj or (aviso or {}).get("STATUS") or "").upper()
            if any(k in txt for k in ("PEND", "ABERTO", "ATIVO")):
                pendentes += 1

    monitor_rows = (controle if isinstance(controle, list) else []) + (encomendas if isinstance(encomendas, list) else [])
    for r in monitor_rows:
        st = _status_text(r)
        if "SEM CONTATO" in st:
            sem_contato += 1
        elif "AVISADO" in st:
            avisado += 1
        elif "PEND" in st:
            pendentes += 1

    return {
        "ativos": len(avisos) if isinstance(avisos, list) else 0,
        "pendentes": pendentes,
        "sem_contato": sem_contato,
        "avisado": avisado,
        "alta_severidade": alta_severidade,
    }


def _update_status_cards():
    global _metrics_previous_cards, _cards_last_update_at
    data = _collect_status_cards_data()
    ux = analisar_metricas_ux() if callable(analisar_metricas_ux) else {}
    now = datetime.now()
    now_label = now.strftime("%H:%M:%S")
    _cards_last_update_at = now
    for k in ("ativos", "pendentes", "sem_contato", "avisado"):
        card = _ux_cards.get(k)
        if card:
            try:
                current = int(data.get(k, 0))
                previous = int(_metrics_previous_cards.get(k, current))
                card.set_value(str(current))
                card.set_trend(current - previous)
                card.set_capacity(current, CARD_CAPACITY_LIMITS.get(k, 1000))
                card.set_meta(f"Atualizado às {now_label} • há 0s")
                card.flash(260)
            except Exception:
                pass
    _metrics_previous_cards = dict(data)
    if _metrics_accessibility_var is not None:
        try:
            _metrics_accessibility_var.set(
                f"Métricas: Ativos {data.get('ativos',0)}, Pendentes {data.get('pendentes',0)}, Sem contato {data.get('sem_contato',0)}, Avisado {data.get('avisado',0)}"
            )
        except Exception:
            pass
    if _status_bar is not None and isinstance(ux, dict):
        try:
            p95 = ((ux.get("time_to_apply_filter_ms") or {}).get("p95") or 0)
            ok = ux.get("edit_save_success_rate") or 0
            _status_bar.set(f"UX: p95 filtro {p95}ms • sucesso edição {round(ok*100,1)}% • trocas de tema {ux.get('theme_switch_count',0)}", tone="info")
        except Exception:
            pass


def _refresh_cards_relative_meta():
    if _cards_last_update_at is None:
        return
    elapsed = max(int((datetime.now() - _cards_last_update_at).total_seconds()), 0)
    for card in _ux_cards.values():
        try:
            base = str(card.meta_var.get() or "")
            if "• há" in base:
                base = base.split("• há", 1)[0].strip()
            card.set_meta(f"{base} • há {elapsed}s")
        except Exception:
            pass



def set_monitor_focus_identity(identidade: str):
    global _pending_focus_identity
    _pending_focus_identity = (identidade or "").strip().upper()

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
def _parse_json_lenient(raw: str):
    text = str(raw or "").strip()
    if not text:
        return []
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # fallback 1: JSON por linha (ndjson/jsonl)
    items = []
    for line in text.splitlines():
        candidate = line.strip().rstrip(",")
        if not candidate:
            continue
        try:
            items.append(json.loads(candidate))
        except Exception:
            continue
    if items:
        return items

    # fallback 2: múltiplos objetos JSON concatenados sem vírgula
    decoder = json.JSONDecoder()
    pos = 0
    length = len(text)
    recovered = []
    while pos < length:
        while pos < length and text[pos] not in "[{":
            pos += 1
        if pos >= length:
            break
        try:
            obj, end = decoder.raw_decode(text, pos)
            recovered.append(obj)
            pos = end
        except Exception:
            pos += 1
    if recovered:
        if len(recovered) == 1:
            return recovered[0]
        return recovered

    raise json.JSONDecodeError("invalid json for known encodings", text, 0)


def _read_json_flexible(path: str):
    # Robustez para ambientes Windows/produção: arquivos podem chegar com BOM,
    # codificação ANSI/latin-1 ou serializações não estritamente válidas.
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                raw = f.read()
            return _parse_json_lenient(raw)
        except UnicodeDecodeError:
            continue
        except json.JSONDecodeError:
            continue
    raise json.JSONDecodeError("invalid json for known encodings", "", 0)


def _load_safe(path: str):
    if not os.path.exists(path):
        return []
    try:
        data = _read_json_flexible(path)
        if isinstance(data, dict) and "registros" in data:
            registros_payload = data.get("registros", [])
            if isinstance(registros_payload, list):
                return _normalize_records_for_monitor(registros_payload)
            if isinstance(registros_payload, dict):
                # caso comum em produção: "registros" como mapa id -> registro
                return _extract_records_from_dict_payload(registros_payload)
            return []
        if isinstance(data, list):
            return _normalize_records_for_monitor(data)
        if isinstance(data, dict):
            # tolera formatos legados/heterogêneos onde o JSON vem como
            # objeto-mapa (id -> registro) ou wrappers diferentes de "registros"
            return _extract_records_from_dict_payload(data)
        return []
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


def _normalize_records_for_monitor(records):
    if not isinstance(records, list):
        return []
    normalized = []
    for r in records:
        if isinstance(r, dict):
            normalized.append(_normalize_record_for_monitor(r))
        elif isinstance(r, (str, int, float, bool)):
            text = str(r)
            normalized.append({
                "texto": text,
                "texto_original": text,
                "DATA_HORA": "",
                "NOME": "",
                "SOBRENOME": "",
                "BLOCO": "",
                "APARTAMENTO": "",
                "PLACA": "",
                "MODELO": "",
                "COR": "",
                "STATUS": "",
                "STATUS_ENCOMENDA": "",
                "TIPO": "",
                "LOJA": "",
                "IDENTIFICACAO": "",
            })
    return normalized


def _looks_like_monitor_record(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    keyset = {str(k).upper() for k in payload.keys()}
    canonical_hint = {
        "NOME", "SOBRENOME", "BLOCO", "APARTAMENTO", "PLACA", "STATUS", "STATUS_ENCOMENDA", "DATA_HORA", "TIPO", "LOJA"
    }
    if keyset.intersection(canonical_hint):
        return True
    alias_hint = {"nome", "sobrenome", "bloco", "apartamento", "ap", "placa", "status", "status_encomenda", "data_hora", "tipo", "loja"}
    return bool(set(payload.keys()).intersection(alias_hint))


def _extract_records_from_dict_payload(payload: dict):
    if not isinstance(payload, dict):
        return []

    # Caso 1: o próprio dict já é um único registro
    if _looks_like_monitor_record(payload):
        return _normalize_records_for_monitor([payload])

    # Caso 2: wrappers conhecidos com coleção de registros
    for key in ("dados", "data", "items", "rows", "entries"):
        candidate = payload.get(key)
        if isinstance(candidate, list):
            return _normalize_records_for_monitor(candidate)
        if isinstance(candidate, dict):
            nested = _extract_records_from_dict_payload(candidate)
            if nested:
                return nested

    # Caso 3: dict-mapa (id -> registro)
    dict_values = [v for v in payload.values() if isinstance(v, dict)]
    if dict_values and all(_looks_like_monitor_record(v) for v in dict_values):
        return _normalize_records_for_monitor(dict_values)

    # Caso 4: procurar recursivamente em qualquer sub-estrutura
    for value in payload.values():
        if isinstance(value, list):
            normalized = _normalize_records_for_monitor(value)
            if normalized:
                return normalized
        elif isinstance(value, dict):
            nested = _extract_records_from_dict_payload(value)
            if nested:
                return nested

    return []


def _normalize_record_for_monitor(record: dict) -> dict:
    normalized = dict(record or {})

    def pick(*keys):
        for key in keys:
            value = record.get(key)
            if value not in (None, ""):
                return value
        return ""

    aliases = {
        "NOME": ("NOME", "nome"),
        "SOBRENOME": ("SOBRENOME", "sobrenome"),
        "BLOCO": ("BLOCO", "bloco"),
        "APARTAMENTO": ("APARTAMENTO", "apartamento", "ap"),
        "PLACA": ("PLACA", "placa"),
        "MODELO": ("MODELO", "modelo", "veiculo_modelo"),
        "COR": ("COR", "cor", "veiculo_cor"),
        "STATUS": ("STATUS", "status"),
        "STATUS_ENCOMENDA": ("STATUS_ENCOMENDA", "status_encomenda"),
        "TIPO": ("TIPO", "tipo"),
        "LOJA": ("LOJA", "loja"),
        "IDENTIFICACAO": ("IDENTIFICACAO", "identificacao", "identificação"),
        "DATA_HORA": ("DATA_HORA", "data_hora", "datahora", "timestamp"),
    }

    for canonical, keys in aliases.items():
        value = pick(*keys)
        if value not in (None, ""):
            normalized[canonical] = value

    return normalized

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


def _record_original_id(r: dict) -> str:
    return str(r.get("ID") or r.get("id") or r.get("_entrada_id") or "-")

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
    formatted = templates[idx].format(
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
    return f"[ID {_record_original_id(r)}] {formatted}"

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
    texto_final = base_text
    if status not in ("-", ""):
        status_up = status.strip().upper()
        if status_up == "AVISADO":
            prefix = "[AVISADO ✅]"
        elif status_up == "SEM CONTATO":
            prefix = "[SEM CONTATO ⚠]"
        else:
            prefix = f"[{status_up}]"
        texto_final = f"{base_text} — {prefix} {status_dh}"
    return f"[ID {_record_original_id(r)}] {texto_final}"

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
    texto = str(r.get("texto") or r.get("texto_original") or "")
    return f"[ID {_record_original_id(r)}] {texto}"

def format_observacao_entry(r: dict) -> str:
    texto = str(r.get("texto") or r.get("texto_original") or "")
    return f"[ID {_record_original_id(r)}] {texto}"

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



def _filters_are_active(filters: dict | None) -> bool:
    f = filters or {}
    return any([
        str(f.get("query") or "").strip() != "",
        str(f.get("status") or "Todos").strip().upper() != "TODOS",
        str(f.get("bloco") or "Todos").strip().upper() != "TODOS",
        str(f.get("date_mode") or "Mais recentes") == "Específica",
        str(f.get("time_mode") or "Mais recentes") == "Específica",
    ])

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
    if ui:
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

    try:
        text_widget.config(state="normal")
        text_widget.tag_remove("controle_selected", "1.0", tk.END)
        if rec_tag:
            ranges = text_widget.tag_ranges(rec_tag)
            if ranges and len(ranges) >= 2:
                text_widget.tag_add("controle_selected", ranges[0], ranges[1])
        text_widget.config(state="disabled")
    except Exception:
        pass

    details_var = _control_details_var.get(text_widget)
    if details_var is not None:
        _control_selection_state[text_widget] = str((record or {}).get("ID") or (record or {}).get("_entrada_id") or "")
        _set_control_details(details_var, record)


def _on_record_line_number_click(text_widget, record, rec_tag, idx):
    bp = _text_breakpoints.setdefault(text_widget, set())
    if idx in bp:
        bp.remove(idx)
    else:
        bp.add(idx)
    _record_on_tag_click(text_widget, record, rec_tag=rec_tag)
    source = _monitor_sources.get(text_widget, {})
    info_label = source.get("info_label")
    if info_label is not None:
        _populate_text(text_widget, info_label)


def _on_record_text_click_toggle_bp(text_widget, record, rec_tag, idx):
    _on_record_line_number_click(text_widget, record, rec_tag, idx)

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


def _set_control_details(details_var, rec):
    if details_var is None:
        return
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


def _restore_control_text_selection(text_widget, record_tag_map):
    selected_record = _control_selection_state.get(text_widget)
    if not selected_record:
        return
    selected_tag = None
    selected_rec = None
    for rec_tag, rec in (record_tag_map or {}).items():
        rec_id = str((rec or {}).get("ID") or (rec or {}).get("_entrada_id") or "")
        if rec_id and rec_id == selected_record:
            selected_tag = rec_tag
            selected_rec = rec
            break
    if not selected_tag:
        return
    try:
        text_widget.config(state="normal")
        text_widget.tag_remove("controle_selected", "1.0", tk.END)
        ranges = text_widget.tag_ranges(selected_tag)
        if ranges and len(ranges) >= 2:
            text_widget.tag_add("controle_selected", ranges[0], ranges[1])
        text_widget.config(state="disabled")
    except Exception:
        pass
    details_var = _control_details_var.get(text_widget)
    if details_var is not None:
        _set_control_details(details_var, selected_rec)


def _update_control_details(tree_widget, selection):
    details_var = _control_details_var.get(tree_widget)
    record_map = _control_table_map.get(tree_widget, {})
    if details_var is None:
        return
    if not selection:
        _set_control_details(details_var, None)
        return
    rec = record_map.get(selection[0])
    _control_selection_state[tree_widget] = str((rec or {}).get("ID") or (rec or {}).get("_entrada_id") or "")
    _set_control_details(details_var, rec)


def _populate_control_table(tree_widget, info_label):
    source = _monitor_sources.get(tree_widget, {})
    arquivo = source.get("path", ARQUIVO)
    registros = _load_safe(arquivo)
    filter_key = source.get("filter_key", tree_widget)
    filters = _filter_state.get(filter_key, {})
    filtrados = _apply_filters(registros, filters)
    header_filters = source.get("header_filters") or {}
    if isinstance(header_filters, dict) and header_filters:
        def _match_header(rec):
            for key, val in header_filters.items():
                txt = str(val or "").strip().upper()
                if not txt:
                    continue
                rv = str((rec or {}).get(key.upper()) or (rec or {}).get(key.lower()) or "").upper()
                if txt not in rv:
                    return False
            return True
        filtrados = [r for r in filtrados if _match_header(r)]
    if registros and not filtrados and _filters_are_active(filters):
        _filter_state[filter_key] = _default_filters()
        filters = _filter_state[filter_key]
        filtrados = _apply_filters(registros, filters)
        report_status("ux_metrics", "OK", stage="filters_auto_reset", details={"source": str(filter_key), "reason": "empty_result"})

    sort_key_name = source.get("sort_key", "controle")
    sort_state = _control_sort_state.get(sort_key_name, {"key": "data_hora", "reverse": True})
    sort_key = sort_state.get("key", "data_hora")
    reverse = bool(sort_state.get("reverse", True))
    filtrados = sorted(filtrados, key=lambda rec: _control_sort_value(rec, sort_key), reverse=reverse)

    last = get_last_status()
    status_hint = ""
    if last:
        status_hint = f" | último status: {last.get('action','-')}:{last.get('status','-')}"
    info_label.config(text=f"Arquivo: {arquivo} — registros: {len(filtrados)} (de {len(registros)}){status_hint}")
    if _control_filtered_count_var is not None:
        try:
            _control_filtered_count_var.set(f"Registros filtrados: {len(filtrados)} / {len(registros)}")
        except Exception:
            pass

    selected_record = _control_selection_state.get(tree_widget)
    global _pending_focus_identity
    focus_ident = _pending_focus_identity
    for iid in tree_widget.get_children():
        tree_widget.delete(iid)

    record_map = {}
    selected_iid = None
    if not filtrados:
        tree_widget.insert("", tk.END, iid="empty", values=("—", "Sem registros", "Aplique filtros rápidos ou limpe busca", "", ""), tags=("empty",))
    for idx, rec in enumerate(filtrados):
        iid = f"row_{idx}"
        row_tags = ["row_even" if idx % 2 == 0 else "row_odd"]
        status = str((rec or {}).get("STATUS") or "").upper()
        if "SEM CONTATO" in status:
            row_tags.append("status_sem_contato")
        if "AVISADO" in status:
            row_tags.append("status_avisado")
        tree_widget.insert("", tk.END, iid=iid, values=_format_control_row(rec), tags=tuple(row_tags))
        record_map[iid] = rec
        if selected_record and str(rec.get("ID") or rec.get("_entrada_id") or "") == selected_record:
            selected_iid = iid
        if focus_ident:
            ident = f"{(rec.get('NOME') or '').strip().upper()}|{(rec.get('SOBRENOME') or '').strip().upper()}|{(rec.get('BLOCO') or '').strip().upper()}|{(rec.get('APARTAMENTO') or '').strip().upper()}"
            if ident == focus_ident:
                selected_iid = iid

    _control_table_map[tree_widget] = record_map
    if _operation_mode_enabled and not selected_iid:
        for iid, rec in record_map.items():
            st = str((rec or {}).get("STATUS") or (rec or {}).get("STATUS_ENCOMENDA") or "").upper()
            if "PEND" in st:
                selected_iid = iid
                break
    if selected_iid:
        _pending_focus_identity = None
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
    if isinstance(text_widget, ttk.Treeview):
        _populate_control_table(text_widget, info_label)
        report_status("monitor", "OK", stage="populate_text_done", details={"source": source.get("path"), "view": "table"})
        return
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
    if registros and not filtrados and _filters_are_active(filters):
        _filter_state[filter_key] = _default_filters()
        filters = _filter_state[filter_key]
        filtrados = _apply_filters(registros, filters)
        report_status("ux_metrics", "OK", stage="filters_auto_reset", details={"source": str(filter_key), "reason": "empty_result"})
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

    text_widget.tag_configure("row_even", background=UI_THEME.get("surface", "#151A22"))
    text_widget.tag_configure("row_odd", background=UI_THEME.get("surface", "#151A22"))
    text_widget.tag_configure("line_number", foreground=UI_THEME.get("muted_text", "#A6A6A6"))
    for idx, r in enumerate(filtrados):
        is_clickable = formatter in (format_creative_entry, format_encomenda_entry, format_orientacao_entry, format_observacao_entry)
        row_tag = "row_even" if idx % 2 == 0 else "row_odd"
        rec_tag = None
        if is_clickable:
            has_clickable_records = True
            prefix = "controle" if formatter == format_creative_entry else ("encomenda" if formatter == format_encomenda_entry else ("orientacao" if formatter == format_orientacao_entry else "observacao"))
            rec_tag = f"{prefix}_record_{idx}"
        linha = formatter(r)
        hover_idx = _text_hover_marker.get(text_widget)
        marker = "●" if idx in _text_breakpoints.get(text_widget, set()) or hover_idx == idx else " "
        numbered = f"{marker} {idx + 1:>3}  {linha}"
        text_tags = [row_tag]
        if rec_tag:
            text_tags.append(rec_tag)
        # Inserir já com a tag — isto garante que o tag cubra exatamente o texto
        try:
            if rec_tag:
                text_widget.insert(tk.END, numbered + "\n\n", tuple(text_tags))
            else:
                text_widget.insert(tk.END, numbered + "\n\n", tuple(text_tags))
        except Exception:
            # fallback simples
            text_widget.insert(tk.END, numbered + "\n\n", tuple(text_tags))

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
                    start = text_widget.index(f"{end} - {len(numbered)}c")
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
                text_widget.tag_bind(rec_tag, "<Button-1>", lambda ev, tw=text_widget, rec=r, tag=rec_tag, pos=idx: _on_record_text_click_toggle_bp(tw, rec, tag, pos))
            except Exception:
                pass
            try:
                prefix = f"{marker} {idx + 1:>3}"
                num_tag = f"line_number_{idx}"
                text_widget.tag_add(num_tag, start, f"{start} + {len(prefix)}c")
                text_widget.tag_add("line_number", start, f"{start} + {len(prefix)}c")
                text_widget.tag_configure(num_tag, foreground=UI_THEME.get("muted_text", "#A6A6A6"))
                text_widget.tag_bind(num_tag, "<Button-1>", lambda ev, tw=text_widget, rec=r, tag=rec_tag, pos=idx: _on_record_line_number_click(tw, rec, tag, pos))
                text_widget.tag_bind(num_tag, "<Enter>", lambda ev, tw=text_widget, rec=r, tag=rec_tag: _record_on_tag_click(tw, rec, ev, tag))
                _record_num_tag_map.setdefault(text_widget, {})[rec_tag] = num_tag
            except Exception:
                pass
        else:
            # para registros não-encomenda, só guardar ranges genéricos
            try:
                end = text_widget.index("end-2c")
                start = text_widget.index(f"{end} - {len(numbered)}c")
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
    _text_record_ranges[text_widget] = record_ranges
    if formatter == format_encomenda_entry:
        _encomenda_display_map[text_widget] = record_ranges
        _encomenda_tag_map[text_widget] = record_tag_map
        _encomenda_line_map[text_widget] = record_line_map
    else:
        _encomenda_display_map.pop(text_widget, None)
        _encomenda_tag_map.pop(text_widget, None)
        _encomenda_line_map.pop(text_widget, None)

    if has_clickable_records or formatter in (format_creative_entry, format_orientacao_entry, format_observacao_entry):
        _record_tag_map_generic[text_widget] = record_tag_map
    else:
        _record_tag_map_generic.pop(text_widget, None)
        _record_num_tag_map.pop(text_widget, None)
    if formatter == format_creative_entry:
        _restore_control_text_selection(text_widget, record_tag_map)
    _restore_hover_if_needed(text_widget, "hover_line")
    _update_sticky_header_for_text(text_widget)

def _schedule_update(text_widgets, info_label):
    global _monitor_after_id
    for tw in text_widgets:
        if tw in _text_edit_lock:
            continue
        try:
            _populate_text(tw, info_label)
        except Exception as e:
            report_status("monitor", "ERROR", stage="populate_text_failed", details={"error": str(e)})
            continue
    # schedule next update
    _refresh_cards_relative_meta()
    try:
        _monitor_after_id = text_widgets[0].after(
            int(_runtime_refresh_ms), lambda: _schedule_update(text_widgets, info_label)
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
    _update_status_cards()

def limpar_dados(text_widgets, info_label, action_button=None):
    if not os.path.exists(ARQUIVO):
        messagebox.showinfo("Limpar dados", "Arquivo não existe.")
        return
    if action_button is not None:
        try:
            action_button.configure(state="disabled", text="Processando...")
        except Exception:
            pass
    resp = messagebox.askyesno("Limpar dados", "Criar backup e limpar dadosend.json (registros serão removidos)?")
    if not resp:
        if action_button is not None:
            try:
                action_button.configure(state="normal", text="Limpar")
            except Exception:
                pass
        return
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = os.path.join(os.path.dirname(ARQUIVO), f"dadosend_backup_{ts}.json")
        shutil.copy2(ARQUIVO, bak)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao criar backup: {e}")
        if action_button is not None:
            try:
                action_button.configure(state="normal", text="Limpar")
            except Exception:
                pass
        return
    try:
        _atomic_write(ARQUIVO, {"registros": []})
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao limpar arquivo: {e}")
        if action_button is not None:
            try:
                action_button.configure(state="normal", text="Limpar")
            except Exception:
                pass
        return
    messagebox.showinfo("Limpar dados", f"Backup salvo em:\n{bak}\nArquivo limpo.")
    for tw in text_widgets:
        _populate_text(tw, info_label)
    if action_button is not None:
        try:
            action_button.configure(state="normal", text="Limpar")
        except Exception:
            pass

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

def _announce_feedback(text: str, tone: str = "info"):
    icon_map = {"info": "ℹ", "success": "✅", "warning": "⚠", "danger": "⛔", "error": "⛔"}
    if _feedback_banner is not None:
        try:
            _feedback_banner.show(text, tone=tone if tone != "error" else "danger", icon=icon_map.get(tone, "ℹ"), timeout_ms=2200)
        except Exception:
            pass


def _snapshot_current_filter(filter_key):
    return dict(_filter_state.get(filter_key) or _default_filters())

def _build_filter_bar(parent, filter_key, info_label, target_widget=None):
    target_widget = target_widget or filter_key
    bar = build_card_frame(parent)
    bar.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(0, theme_space("space_2", 6)))

    top_row = tk.Frame(bar, bg=UI_THEME["surface"])
    top_row.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(theme_space("space_2", 8), theme_space("space_1", 4)))
    actions_row = tk.Frame(bar, bg=UI_THEME["surface"])
    actions_row.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(0, theme_space("space_2", 8)))

    order_var = tk.StringVar(value="Mais recentes")
    date_mode_var = tk.StringVar(value="Mais recentes")
    time_mode_var = tk.StringVar(value="Mais recentes")
    query_var = tk.StringVar(value="")
    status_var = tk.StringVar(value="Todos")
    bloco_var = tk.StringVar(value="Todos")
    advanced_visible = tk.BooleanVar(value=False)
    preset_var = tk.StringVar(value="Preset (opcional)")
    auto_apply_defaults = (_load_prefs().get("filter_auto_apply") or {})
    auto_apply_var = tk.BooleanVar(value=bool(auto_apply_defaults.get(str(filter_key), False)))

    advanced_frame = tk.Frame(bar, bg=UI_THEME["surface"])
    date_entry = build_filter_input(advanced_frame, width=10)
    time_entry = build_filter_input(advanced_frame, width=8)
    query_entry = build_filter_input(top_row, textvariable=query_var, width=18)
    filtro_badge = build_badge(top_row, text="Nenhum filtro ativo", tone="info")
    filtro_badge.grid(row=0, column=8, padx=(theme_space("space_2", 8), 0), pady=theme_space("space_1", 4), sticky="e")

    try:
        parent.bind("<Control-f>", lambda _e: (report_status("ux_metrics", "OK", stage="shortcut_used", details={"shortcut": "Ctrl+F", "source": str(filter_key)}), query_entry.focus_set(), "break")[2], add="+")
        parent.bind("<Control-Shift-L>", lambda _e: (report_status("ux_metrics", "OK", stage="shortcut_used", details={"shortcut": "Ctrl+Shift+L", "source": str(filter_key)}), clear_filters(), "break")[2], add="+")
        parent.bind("<Control-Return>", lambda _e: (report_status("ux_metrics", "OK", stage="shortcut_used", details={"shortcut": "Ctrl+Enter", "source": str(filter_key)}), apply_filters(), "break")[2], add="+")
    except Exception:
        pass

    def _current_payload():
        return {
            "order": order_var.get(),
            "date_mode": date_mode_var.get(),
            "date_value": date_entry.get().strip(),
            "time_mode": time_mode_var.get(),
            "time_value": time_entry.get().strip(),
            "query": query_entry.get().strip(),
            "status": status_var.get().strip() or "Todos",
            "bloco": bloco_var.get().strip() or "Todos",
        }

    def _count_active_filters(payload=None):
        payload = payload or _current_payload()
        count = 0
        if (payload.get("query") or "").strip():
            count += 1
        if (payload.get("status") or "Todos") != "Todos":
            count += 1
        if (payload.get("bloco") or "Todos") != "Todos":
            count += 1
        if (payload.get("date_mode") or "Mais recentes") == "Específica" and (payload.get("date_value") or "").strip():
            count += 1
        if (payload.get("time_mode") or "Mais recentes") == "Específica" and (payload.get("time_value") or "").strip():
            count += 1
        if (payload.get("order") or "Mais recentes") != "Mais recentes":
            count += 1
        return count

    def update_entry_state():
        date_state = "normal" if date_mode_var.get() == "Específica" else "disabled"
        time_state = "normal" if time_mode_var.get() == "Específica" else "disabled"
        date_entry.configure(state=date_state)
        time_entry.configure(state=time_state)

    icon_map = {"info": "ℹ", "success": "✅", "warning": "⚠", "danger": "⛔", "error": "⛔"}

    def _update_filter_badge(transient_msg=None, tone="info"):
        active_count = _count_active_filters()
        if transient_msg:
            tone_key = "danger" if tone == "error" else tone
            bg, fg = state_colors(tone_key)
            filtro_badge.configure(
                text=f"{icon_map.get(tone, 'ℹ')} {transient_msg}",
                bg=bg,
                fg=fg,
            )
            return
        if active_count > 0:
            bg, fg = state_colors("info")
            filtro_badge.configure(
                text=f"🔎 {active_count} filtros ativos",
                bg=bg,
                fg=fg,
            )
        else:
            filtro_badge.configure(
                text="○ Nenhum filtro ativo",
                bg=UI_THEME.get("surface_alt", "#1B2430"),
                fg=UI_THEME.get("muted_text", "#9AA4B2"),
            )

    def _set_apply_dirty_state(*_):
        if not isinstance(btn_apply, tk.Button):
            return
        is_dirty = _current_payload() != (_filter_state.get(filter_key) or _default_filters())
        if is_dirty:
            btn_apply.configure(bg=UI_THEME.get("success", "#2DA44E"), activebackground=UI_THEME.get("success", "#2DA44E"), fg=UI_THEME.get("on_success", "#08120C"), activeforeground=UI_THEME.get("on_success", "#08120C"))
            bind_button_states(btn_apply, UI_THEME.get("success", "#2DA44E"), UI_THEME.get("primary", "#2F81F7"))
        else:
            btn_apply.configure(bg=UI_THEME["primary"], activebackground=UI_THEME["primary_active"], fg=UI_THEME.get("on_primary", UI_THEME["text"]), activeforeground=UI_THEME.get("on_primary", UI_THEME["text"]))
            bind_button_states(btn_apply, UI_THEME["primary"], UI_THEME["primary_active"])

    def _flash_feedback(msg, tone="info"):
        _announce_feedback(msg, tone)
        if _status_bar is not None:
            try:
                _status_bar.set(str(msg), tone=("danger" if tone == "error" else tone))
            except Exception:
                pass

    def _apply_payload(payload: dict):
        if not isinstance(payload, dict):
            return
        order_var.set(payload.get("order") or "Mais recentes")
        date_mode_var.set(payload.get("date_mode") or "Mais recentes")
        time_mode_var.set(payload.get("time_mode") or "Mais recentes")
        query_var.set(payload.get("query") or "")
        status_var.set(payload.get("status") or "Todos")
        bloco_var.set(payload.get("bloco") or "Todos")
        date_entry.delete(0, tk.END); date_entry.insert(0, payload.get("date_value") or "")
        time_entry.delete(0, tk.END); time_entry.insert(0, payload.get("time_value") or "")
        update_entry_state()
        _update_filter_badge()
        _set_apply_dirty_state()

    def apply_filters():
        global _last_filter_snapshot
        _last_filter_snapshot[filter_key] = _snapshot_current_filter(filter_key)
        report_status("ux_metrics", "STARTED", stage="filter_apply_started", details={"source": str(filter_key)})
        _filter_state[filter_key] = _current_payload()
        _update_filter_badge()
        _set_apply_dirty_state()
        _flash_feedback("Filtros aplicados", "success")
        _persist_ui_state({"last_filter_saved_at": datetime.now().isoformat()})
        details = {"source": str(filter_key), "query_len": len(query_entry.get().strip())}
        if _last_quick_filter_kind:
            details["quick_filter_conversion"] = _last_quick_filter_kind
        report_status("ux_metrics", "OK", stage="filter_apply", details=details)
        _persist_ui_state()
        _populate_text(target_widget, info_label)
        if _last_quick_filter_kind:
            report_status("ux_metrics", "OK", stage="quick_filter_conversion", details={"source": str(filter_key), "kind": _last_quick_filter_kind})

    def clear_filters():
        global _last_filter_snapshot
        _last_filter_snapshot[filter_key] = _snapshot_current_filter(filter_key)
        order_var.set("Mais recentes")
        date_mode_var.set("Mais recentes")
        time_mode_var.set("Mais recentes")
        query_var.set("")
        status_var.set("Todos")
        bloco_var.set("Todos")
        date_entry.delete(0, tk.END)
        time_entry.delete(0, tk.END)
        update_entry_state()
        _filter_state[filter_key] = _default_filters()
        _update_filter_badge()
        _set_apply_dirty_state()
        _flash_feedback("Filtros limpos", "warning")
        report_status("ux_metrics", "OK", stage="filter_clear", details={"source": str(filter_key)})
        _persist_ui_state()
        _populate_text(target_widget, info_label)

    def _undo_last_filter():
        snapshot = _last_filter_snapshot.get(filter_key)
        if not snapshot:
            _flash_feedback("Nada para desfazer", "warning")
            return
        _apply_payload(snapshot)
        _filter_state[filter_key] = dict(snapshot)
        _flash_feedback("Último filtro desfeito", "info")
        _populate_text(target_widget, info_label)

    def _quick_filter(kind: str):
        global _last_quick_filter_kind
        _last_quick_filter_kind = kind
        payload = _current_payload()
        if kind == "today":
            payload["date_mode"] = "Específica"
            payload["date_value"] = datetime.now().strftime("%d/%m/%Y")
        elif kind == "sem_contato":
            payload["status"] = "SEM CONTATO"
        elif kind == "alta":
            payload["query"] = "alta"
        _apply_payload(payload)
        apply_filters()
        report_status("ux_metrics", "OK", stage="quick_filter_used", details={"kind": kind, "source": str(filter_key)})

    def _toggle_advanced():
        advanced_visible.set(not advanced_visible.get())
        if advanced_visible.get():
            advanced_frame.pack(fill=tk.X, padx=theme_space("space_2", 8), pady=(0, theme_space("space_2", 8)))
            btn_advanced.configure(text="Ocultar filtros avançados")
        else:
            advanced_frame.pack_forget()
            btn_advanced.configure(text="Filtros avançados")

    def _save_preset():
        name = simpledialog.askstring("Salvar preset", "Nome do preset (operador/turno):", parent=bar.winfo_toplevel())
        name = (name or "").strip()
        if not name:
            return
        presets = _get_filter_presets()
        presets[name] = _current_payload()
        _save_filter_presets(presets)
        _refresh_preset_combo(name)
        _flash_feedback("Preset salvo", "success")

    def _load_preset(_e=None):
        name = (preset_var.get() or "").strip()
        if not name or name == "Preset (opcional)":
            return
        presets = _get_filter_presets()
        _apply_payload(presets.get(name) or {})
        apply_filters()

    def _refresh_preset_combo(selected="Preset (opcional)"):
        presets_local = _get_filter_presets()
        values = ["Preset (opcional)"] + sorted(presets_local.keys())
        preset_combo.configure(values=values)
        preset_var.set(selected if selected in values else "Preset (opcional)")

    def _rename_selected_preset():
        current = (preset_var.get() or "").strip()
        if not current or current == "Preset (opcional)":
            _flash_feedback("Selecione um preset para renomear", "warning")
            return
        novo = simpledialog.askstring("Renomear preset", f"Novo nome para '{current}':", parent=bar.winfo_toplevel())
        if not novo:
            return
        if _rename_filter_preset(current, novo):
            _refresh_preset_combo(novo.strip())
            _flash_feedback("Preset renomeado", "success")
        else:
            _flash_feedback("Não foi possível renomear preset", "danger")

    def _delete_selected_preset():
        current = (preset_var.get() or "").strip()
        if not current or current == "Preset (opcional)":
            _flash_feedback("Selecione um preset para excluir", "warning")
            return
        if not messagebox.askyesno("Excluir preset", f"Excluir preset '{current}'?", parent=bar.winfo_toplevel()):
            return
        _delete_filter_preset(current)
        _refresh_preset_combo("Preset (opcional)")
        _flash_feedback("Preset excluído", "warning")

    def _set_default_preset_for_tab():
        current = (preset_var.get() or "").strip()
        if not current or current == "Preset (opcional)":
            _set_filter_default_preset(filter_key, "")
            _flash_feedback("Preset padrão removido da aba", "info")
            return
        _set_filter_default_preset(filter_key, current)
        _flash_feedback(f"Preset padrão da aba: {current}", "success")

    def _schedule_auto_apply(*_):
        global _filter_auto_apply_after
        if not auto_apply_var.get():
            return
        prev = _filter_auto_apply_after.get(filter_key)
        if prev:
            try:
                bar.after_cancel(prev)
            except Exception:
                pass
        _filter_auto_apply_after[filter_key] = bar.after(380, lambda: (apply_filters(), _filter_auto_apply_after.pop(filter_key, None)))

    def _save_auto_apply_pref(*_):
        payload = _load_prefs()
        auto_cfg = payload.get("filter_auto_apply") or {}
        if not isinstance(auto_cfg, dict):
            auto_cfg = {}
        auto_cfg[str(filter_key)] = bool(auto_apply_var.get())
        payload["filter_auto_apply"] = auto_cfg
        _save_prefs(payload)
        if auto_apply_var.get():
            _schedule_auto_apply()

    build_label(top_row, "Buscar", font=theme_font("font_sm")).grid(row=0, column=0, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")
    query_entry.grid(row=0, column=1, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_1", 4), sticky="ew")

    build_label(top_row, "Status", font=theme_font("font_sm")).grid(row=0, column=2, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")
    status_combo = ttk.Combobox(top_row, textvariable=status_var, values=["Todos", "MORADOR", "VISITANTE", "PRESTADOR", "AVISADO", "SEM CONTATO"], state="readonly")
    status_combo.grid(row=0, column=3, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_1", 4), sticky="ew")

    presets = _get_filter_presets()
    build_label(top_row, "Preset", font=theme_font("font_sm")).grid(row=0, column=4, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")
    preset_combo = ttk.Combobox(top_row, textvariable=preset_var, values=["Preset (opcional)"] + sorted(presets.keys()), state="readonly")
    preset_combo.grid(row=0, column=5, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_1", 4), sticky="ew")

    btn_apply = build_primary_button(top_row, "Aplicar", apply_filters)
    btn_apply.grid(row=0, column=6, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="e")
    btn_clear = build_secondary_warning_button(top_row, "Limpar", clear_filters)
    btn_clear.grid(row=0, column=7, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="e")
    auto_apply_chk = tk.Checkbutton(top_row, text="Aplicar automaticamente", variable=auto_apply_var, bg=UI_THEME["surface"], fg=UI_THEME.get("on_surface", UI_THEME["text"]), activebackground=UI_THEME["surface"], activeforeground=UI_THEME.get("on_surface", UI_THEME["text"]), selectcolor=UI_THEME.get("surface_alt", UI_THEME["surface"]))
    auto_apply_chk.grid(row=0, column=9, padx=(theme_space("space_1", 4), 0), pady=theme_space("space_1", 4), sticky="e")

    btn_save_preset = build_secondary_button(actions_row, "Salvar preset", _save_preset)
    btn_rename_preset = build_secondary_button(actions_row, "Renomear preset", _rename_selected_preset)
    btn_delete_preset = build_secondary_danger_button(actions_row, "Excluir preset", _delete_selected_preset)
    btn_default_preset = build_secondary_button(actions_row, "Fixar preset da aba", _set_default_preset_for_tab)
    btn_undo_filter = build_secondary_button(actions_row, "Desfazer", _undo_last_filter)
    btn_advanced = build_secondary_button(actions_row, "Filtros avançados", _toggle_advanced)
    quick_today_btn = build_secondary_button(actions_row, "Hoje", lambda: _quick_filter("today"), padx=8)
    quick_sem_contato_btn = build_secondary_button(actions_row, "Sem contato", lambda: _quick_filter("sem_contato"), padx=8)
    quick_alta_btn = build_secondary_button(actions_row, "Alta", lambda: _quick_filter("alta"), padx=8)

    build_label(actions_row, "Ações", font=theme_font("font_sm"), muted=True).grid(row=0, column=0, padx=(0, theme_space("space_1", 4)), sticky="w")
    btn_save_preset.grid(row=0, column=1, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")
    btn_rename_preset.grid(row=0, column=2, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")
    btn_delete_preset.grid(row=0, column=3, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")
    btn_default_preset.grid(row=0, column=4, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")
    btn_undo_filter.grid(row=0, column=5, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")

    quick_group = tk.Frame(actions_row, bg=UI_THEME["surface_alt"], highlightbackground=UI_THEME["border"], highlightthickness=1)
    quick_group.grid(row=0, column=6, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_1", 4), sticky="w")
    build_label(quick_group, "Rápidos", muted=True, bg=UI_THEME["surface_alt"], font=theme_font("font_sm")).pack(side=tk.LEFT, padx=(theme_space("space_1", 4), theme_space("space_1", 4)))
    quick_today_btn.pack(in_=quick_group, side=tk.LEFT, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4))
    quick_sem_contato_btn.pack(in_=quick_group, side=tk.LEFT, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4))
    quick_alta_btn.pack(in_=quick_group, side=tk.LEFT, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4))
    btn_advanced.grid(row=0, column=7, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")

    if isinstance(target_widget, ttk.Treeview):
        col_menu_btn = build_secondary_button(actions_row, "Colunas", lambda: None)
        col_menu_btn.grid(row=0, column=8, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_1", 4), sticky="w")

        def _get_tree_columns_state():
            all_cols = list(target_widget["columns"])
            prefs_local = _load_prefs()
            order_saved = prefs_local.get("control_column_order") or []
            order = [c for c in order_saved if c in all_cols] + [c for c in all_cols if c not in order_saved]
            visible_saved = prefs_local.get("control_column_visible") or {}
            visible = {c: bool(visible_saved.get(c, True)) for c in all_cols}
            return all_cols, order, visible

        def _save_tree_columns_state(order, visible):
            _persist_ui_state({"control_column_order": list(order), "control_column_visible": {k: bool(v) for k, v in visible.items()}})

        def _apply_tree_columns(order, visible):
            shown = [c for c in order if visible.get(c, True)]
            if not shown and order:
                shown = [order[0]]
            target_widget.configure(displaycolumns=tuple(shown or order))

        def _toggle_column(col):
            _all, order, visible = _get_tree_columns_state()
            visible[col] = not visible.get(col, True)
            _save_tree_columns_state(order, visible)
            _apply_tree_columns(order, visible)

        def _move_column(direction):
            col_name = simpledialog.askstring("Reordenar coluna", f"Coluna atual ({direction}): {', '.join(target_widget['columns'])}", parent=bar.winfo_toplevel())
            col_name = str(col_name or "").strip()
            if not col_name:
                return
            _all, order, visible = _get_tree_columns_state()
            if col_name not in order:
                _flash_feedback("Coluna inválida", "warning")
                return
            idx = order.index(col_name)
            tgt = idx - 1 if direction == "esquerda" else idx + 1
            if tgt < 0 or tgt >= len(order):
                return
            order[idx], order[tgt] = order[tgt], order[idx]
            _save_tree_columns_state(order, visible)
            _apply_tree_columns(order, visible)

        menu = tk.Menu(col_menu_btn, tearoff=0)
        cols_all, cols_order, cols_visible = _get_tree_columns_state()
        _apply_tree_columns(cols_order, cols_visible)
        for col in cols_all:
            menu.add_checkbutton(label=col, onvalue=True, offvalue=False, variable=tk.BooleanVar(value=cols_visible.get(col, True)), command=lambda c=col: _toggle_column(c))
        menu.add_separator()
        menu.add_command(label="Mover coluna para esquerda", command=lambda: _move_column("esquerda"))
        menu.add_command(label="Mover coluna para direita", command=lambda: _move_column("direita"))
        col_menu_btn.configure(command=lambda m=menu, b=col_menu_btn: m.tk_popup(b.winfo_rootx(), b.winfo_rooty() + b.winfo_height()))

    attach_tooltip(btn_apply, "Aplica os filtros atuais")
    attach_tooltip(btn_clear, "Limpa todos os filtros")
    attach_tooltip(btn_save_preset, "Salva os filtros como preset")
    attach_tooltip(btn_default_preset, "Define o preset selecionado como padrão da aba")
    attach_tooltip(btn_undo_filter, "Restaura o último conjunto de filtros")
    attach_tooltip(quick_today_btn, "Filtra registros do dia atual")
    attach_tooltip(quick_sem_contato_btn, "Mostra apenas status sem contato")
    attach_tooltip(quick_alta_btn, "Busca ocorrências de alta severidade")

    build_label(advanced_frame, "Ordem", font=theme_font("font_sm")).grid(row=0, column=0, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_2", 8), sticky="w")
    order_combo = ttk.Combobox(advanced_frame, textvariable=order_var, values=["Mais recentes", "Mais antigas"], state="readonly")
    order_combo.grid(row=0, column=1, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_2", 8), sticky="ew")

    build_label(advanced_frame, "Data", font=theme_font("font_sm")).grid(row=0, column=2, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_2", 8), sticky="w")
    date_mode_combo = ttk.Combobox(advanced_frame, textvariable=date_mode_var, values=["Mais recentes", "Específica"], state="readonly")
    date_mode_combo.grid(row=0, column=3, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_2", 8), sticky="ew")
    date_entry.grid(in_=advanced_frame, row=0, column=4, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_2", 8), sticky="w")

    build_label(advanced_frame, "Hora", font=theme_font("font_sm")).grid(row=0, column=5, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_2", 8), sticky="w")
    time_mode_combo = ttk.Combobox(advanced_frame, textvariable=time_mode_var, values=["Mais recentes", "Específica"], state="readonly")
    time_mode_combo.grid(row=0, column=6, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_2", 8), sticky="ew")
    time_entry.grid(in_=advanced_frame, row=0, column=7, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_2", 8), sticky="w")

    build_label(advanced_frame, "Bloco", font=theme_font("font_sm")).grid(row=0, column=8, padx=(0, theme_space("space_1", 4)), pady=theme_space("space_2", 8), sticky="w")
    bloco_combo = ttk.Combobox(advanced_frame, textvariable=bloco_var, values=["Todos"] + [str(i) for i in range(1, 31)], state="readonly")
    bloco_combo.grid(row=0, column=9, padx=(0, theme_space("space_2", 8)), pady=theme_space("space_2", 8), sticky="ew")

    preset_combo.bind("<<ComboboxSelected>>", _load_preset, add="+")

    _filter_controls[filter_key] = [order_combo, date_mode_combo, date_entry, time_mode_combo, time_entry, query_entry, status_combo, bloco_combo, preset_combo, auto_apply_chk]
    for control in _filter_controls[filter_key]:
        bind_focus_ring(control)

    tab_order = [query_entry, status_combo, preset_combo, btn_apply, btn_clear, auto_apply_chk, btn_save_preset, btn_rename_preset, btn_delete_preset, btn_default_preset, btn_undo_filter, quick_today_btn, quick_sem_contato_btn, quick_alta_btn, btn_advanced, order_combo, date_mode_combo, date_entry, time_mode_combo, time_entry, bloco_combo]
    for idx, widget in enumerate(tab_order):
        nxt = tab_order[(idx + 1) % len(tab_order)]
        widget.bind("<Tab>", lambda _e, w=nxt: (w.focus_set(), "break"), add="+")

    top_row.grid_columnconfigure(1, weight=3)
    top_row.grid_columnconfigure(3, weight=1)
    top_row.grid_columnconfigure(5, weight=1)
    top_row.grid_columnconfigure(8, weight=1)
    top_row.grid_columnconfigure(9, weight=1)

    for c in (1, 3, 6, 9):
        advanced_frame.grid_columnconfigure(c, weight=1)

    date_mode_var.trace_add("write", lambda *_: (update_entry_state(), _set_apply_dirty_state()))
    time_mode_var.trace_add("write", lambda *_: (update_entry_state(), _set_apply_dirty_state()))
    query_var.trace_add("write", lambda *_: (_update_filter_badge(), _set_apply_dirty_state(), _schedule_auto_apply()))
    status_var.trace_add("write", lambda *_: (_update_filter_badge(), _set_apply_dirty_state(), _schedule_auto_apply()))
    bloco_var.trace_add("write", lambda *_: (_update_filter_badge(), _set_apply_dirty_state(), _schedule_auto_apply()))
    preset_var.trace_add("write", lambda *_: _set_apply_dirty_state())
    auto_apply_var.trace_add("write", _save_auto_apply_pref)

    update_entry_state()
    if filter_key not in _filter_state:
        _filter_state[filter_key] = _default_filters()
    _apply_payload(_filter_state.get(filter_key) or _default_filters())
    default_preset = _get_filter_default_preset(filter_key)
    if default_preset:
        presets_now = _get_filter_presets()
        if default_preset in presets_now:
            preset_var.set(default_preset)
            _apply_payload(presets_now.get(default_preset) or {})
            apply_filters()
    _update_filter_badge()
    _set_apply_dirty_state()
    return bar

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


def _apply_hover_record(text_widget, rec_tag, hover_tag):
    if text_widget in _text_edit_lock or not rec_tag:
        return False
    try:
        ranges = text_widget.tag_ranges(rec_tag)
        if not ranges or len(ranges) < 2:
            return False
        text_widget.config(state="normal")
        text_widget.tag_add(hover_tag, ranges[0], ranges[1])
        text_widget.config(state="disabled")
        return True
    except Exception:
        return False

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
    token = _hover_state.get(text_widget)
    if not token:
        return
    if isinstance(token, str) and token.startswith("tag:"):
        rec_tag = token[4:]
        if _apply_hover_record(text_widget, rec_tag, hover_tag):
            return
        _hover_state[text_widget] = None
        return
    line = token
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
        tag_names = text_widget.tag_names(index)
        rec_tag = next((t for t in tag_names if "_record_" in t), None)
        if rec_tag:
            num_map = _record_num_tag_map.get(text_widget, {})
            prev_token = _hover_state.get(text_widget)
            prev_tag = prev_token[4:] if isinstance(prev_token, str) and prev_token.startswith("tag:") else None
            if prev_tag and prev_tag != rec_tag:
                prev_num = num_map.get(prev_tag)
                try:
                    prev_idx = int(str(prev_tag).rsplit("_", 1)[1])
                except Exception:
                    prev_idx = None
                if prev_num:
                    text_widget.tag_configure(prev_num, foreground=UI_THEME.get("muted_text", "#A6A6A6"))
            cur_num = num_map.get(rec_tag)
            if cur_num:
                text_widget.tag_configure(cur_num, foreground=UI_THEME.get("muted_text", "#A6A6A6"))
            try:
                hover_idx = int(str(rec_tag).rsplit("_", 1)[1])
            except Exception:
                hover_idx = None
            _text_hover_marker[text_widget] = hover_idx
            token = f"tag:{rec_tag}"
            if _hover_state.get(text_widget) == token:
                return
            _clear_hover_line(text_widget, hover_tag)
            if _apply_hover_record(text_widget, rec_tag, hover_tag):
                _hover_state[text_widget] = token
            return
        if _text_hover_marker.get(text_widget) is not None:
            prev_token = _hover_state.get(text_widget)
            prev_tag = prev_token[4:] if isinstance(prev_token, str) and prev_token.startswith("tag:") else None
            prev_num = (_record_num_tag_map.get(text_widget, {}) or {}).get(prev_tag) if prev_tag else None
            if prev_num:
                try:
                    prev_idx = int(str(prev_tag).rsplit("_", 1)[1])
                except Exception:
                    prev_idx = None
                text_widget.tag_configure(prev_num, foreground=UI_THEME.get("muted_text", "#A6A6A6"))
            _text_hover_marker[text_widget] = None
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

    def _on_leave(_event):
        prev_token = _hover_state.get(text_widget)
        prev_tag = prev_token[4:] if isinstance(prev_token, str) and prev_token.startswith("tag:") else None
        prev_num = (_record_num_tag_map.get(text_widget, {}) or {}).get(prev_tag) if prev_tag else None
        if prev_num:
            try:
                prev_idx = int(str(prev_tag).rsplit("_", 1)[1])
            except Exception:
                prev_idx = None
            text_widget.tag_configure(prev_num, foreground=UI_THEME.get("muted_text", "#A6A6A6"))
        _clear_hover_line(text_widget, hover_tag)
        if _text_hover_marker.get(text_widget) is not None:
            _text_hover_marker[text_widget] = None

    text_widget.bind("<Leave>", _on_leave)

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

    edit_badge = build_badge(action_frame, text="MODO EDIÇÃO ATIVO", tone="warning")
    edit_badge.pack_forget()
    edit_status_var = tk.StringVar(value="")
    edit_status = tk.Label(action_frame, textvariable=edit_status_var, bg=UI_THEME["surface"], fg=UI_THEME.get("muted_text", UI_THEME["text"]), anchor="w", font=theme_font("font_sm"))
    edit_status.pack_forget()

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
            edit_badge.configure(bg=UI_THEME.get("warning", "#D29922"), fg=UI_THEME.get("on_warning", "#111827"))
            edit_badge.pack(fill=tk.X, padx=8, pady=(6, 2), before=action_frame.winfo_children()[0] if action_frame.winfo_children() else None)
            edit_status_var.set("Editando…")
            edit_status.configure(bg=UI_THEME["surface"], fg=UI_THEME.get("muted_text", UI_THEME["text"]))
            edit_status.pack(fill=tk.X, padx=8, pady=(0, 4), before=action_frame.winfo_children()[1] if len(action_frame.winfo_children()) > 1 else None)
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
            edit_status.pack_forget()
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
        edit_status_var.set("Edição cancelada")
        try:
            edit_badge.configure(bg=UI_THEME.get("warning", "#D29922"), fg=UI_THEME.get("on_warning", UI_THEME.get("text", "#111827")))
        except Exception:
            pass
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

        edit_status_var.set("Salvando…")
        try:
            edit_status.configure(bg=UI_THEME["surface"], fg=UI_THEME.get("info", "#2563EB"))
            edit_status.pack(fill=tk.X, padx=8, pady=(0, 4), before=action_frame.winfo_children()[1] if len(action_frame.winfo_children()) > 1 else None)
        except Exception:
            pass

        target["texto"] = new_text
        strict, inferred = build_structured_fields(new_text) if build_structured_fields else ({}, {})
        target["campos_extraidos_confirmados"] = strict
        target["campos_extraidos_inferidos"] = inferred
        target["campos_extraidos"] = _extract_multi_fields(new_text)
        try:
            _atomic_write(path, {"registros": registros})
        except Exception as exc:
            report_status("ux_metrics", "ERROR", stage="edit_save_error", details={"error": str(exc)})
            raise
        report_status("ux_metrics", "OK", stage="edit_save", details={"path": os.path.basename(path), "screen": "monitor"})
        if log_audit_event:
            log_audit_event("texto_editado", os.path.basename(path), new_text)
            log_audit_event("campos_reextraidos", os.path.basename(path), new_text)

        edit_status_var.set("Salvo com sucesso")
        try:
            edit_badge.configure(bg=UI_THEME.get("success", "#2DA44E"), fg=UI_THEME.get("on_success", UI_THEME.get("text", "#E6EDF3")))
        except Exception:
            pass
        _finish_editing(reload_text=True)

    build_secondary_button(action_frame, "Editar", enable_edit, padx=18).pack(side=tk.LEFT, expand=True, padx=10, pady=8)
    build_primary_button(action_frame, "Salvar", save_edit, padx=18).pack(side=tk.LEFT, expand=True, padx=10, pady=8)
    build_secondary_button(action_frame, "Cancelar", cancel_edit, padx=18).pack(side=tk.LEFT, expand=True, padx=10, pady=8)

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
    prefs = _restore_ui_state()
    _apply_light_theme(container)
    apply_ttk_theme_styles(container)
    style = ttk.Style(container)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Dark.TNotebook", background=UI_THEME["bg"], borderwidth=0, relief="flat", highlightthickness=0, bordercolor=UI_THEME.get("bg", "#1E1E1E"), lightcolor=UI_THEME.get("bg", "#1E1E1E"), darkcolor=UI_THEME.get("bg", "#1E1E1E"))
    style.layout("Monitor.Tabless.TNotebook.Tab", [])
    style.configure("Monitor.Tabless.TNotebook", background=UI_THEME["surface"], borderwidth=0, relief="flat", highlightthickness=0, bordercolor=UI_THEME["surface"], lightcolor=UI_THEME["surface"], darkcolor=UI_THEME["surface"])
    style.configure(
        "Dark.TNotebook.Tab",
        background=UI_THEME.get("surface_alt", UI_THEME["surface"]),
        foreground=UI_THEME.get("on_surface", UI_THEME["text"]),
        padding=(12, 4),
        relief="flat",
        borderwidth=1,
        highlightthickness=1,
        bordercolor=UI_THEME.get("border", UI_THEME["surface_alt"]),
        focuscolor=UI_THEME.get("surface_alt", UI_THEME["surface"]),
    )
    style.map(
        "Dark.TNotebook.Tab",
        background=[("selected", UI_THEME.get("surface_alt", UI_THEME["surface"])), ("active", UI_THEME.get("border", UI_THEME["surface_alt"]))],
        foreground=[("selected", UI_THEME.get("on_surface", UI_THEME["text"])), ("active", UI_THEME.get("on_surface", UI_THEME["text"]))],
        focuscolor=[("selected", UI_THEME.get("surface_alt", UI_THEME["surface"])), ("active", UI_THEME.get("border", UI_THEME["surface_alt"]))],
        padding=[("selected", (12, 4)), ("active", (12, 4))],
    )
    style.configure("Encomenda.Text", background=UI_THEME["surface"], foreground=UI_THEME.get("on_surface", UI_THEME["text"]))
    report_status("ux_metrics", "OK", stage="theme_contrast_check", details=validate_theme_contrast())
    style.configure("Control.Treeview", background=UI_THEME["surface"], fieldbackground=UI_THEME["surface"], foreground=UI_THEME.get("on_surface", UI_THEME["text"]), bordercolor=UI_THEME["border"], rowheight=28)
    style.configure("Control.Treeview.Heading", background=UI_THEME["surface_alt"], foreground=UI_THEME.get("on_surface", UI_THEME["text"]), relief="flat", font=theme_font("font_md"))
    style.map("Control.Treeview", background=[("selected", UI_THEME.get("selection_bg", UI_THEME["primary"]))], foreground=[("selected", UI_THEME.get("selection_fg", UI_THEME.get("on_primary", UI_THEME["text"])))])

    info_label = tk.Label(container, text=f"Arquivo: {ARQUIVO}", bg=UI_THEME["bg"], fg=UI_THEME["muted_text"], font=theme_font("font_sm"))
    top_toggle_bar = tk.Frame(container, bg=UI_THEME.get("surface_alt", UI_THEME["bg"]), relief="flat", bd=0, highlightthickness=0)
    top_toggle_bar.pack(fill=tk.X, padx=0, pady=(0, 0))
    btn_eye = tk.Button(
        top_toggle_bar,
        text="👁",
        command=lambda: None,
        bg=UI_THEME.get("surface_alt", UI_THEME["bg"]),
        fg=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")),
        activebackground=UI_THEME.get("border", UI_THEME.get("surface_alt", "#2D2D2D")),
        activeforeground=UI_THEME.get("on_surface", UI_THEME.get("text", "#E6EDF3")),
        relief="flat",
        bd=0,
        font=theme_font("font_xl", "bold"),
        anchor="center",
        padx=0,
        pady=4,
    )
    btn_eye.pack(fill=tk.X)
    top_separator = tk.Frame(container, bg="#000000", height=1)
    top_separator.pack(fill=tk.X, padx=0, pady=(0, 0))

    theme_bar = tk.Frame(container, bg=UI_THEME["bg"])
    theme_bar.pack(fill=tk.X, padx=10, pady=(6, 0))
    theme_bar.pack_forget()
    btn_top_theme = build_secondary_button(theme_bar, "🎨 Tema", lambda: None)
    btn_top_theme.pack(side=tk.LEFT, padx=(6, 0))
    details_visible = tk.BooleanVar(value=False)
    btn_top_details = build_secondary_button(theme_bar, "🧾 Detalhes", lambda: None)
    btn_top_details.pack(side=tk.LEFT, padx=(12, 0))
    btn_top_export = build_secondary_button(theme_bar, "📤 Exportar CSV", lambda: None)
    btn_top_export.pack(side=tk.LEFT, padx=(6, 0))
    btn_top_save_view = build_secondary_button(theme_bar, "💾 Salvar visão", lambda: None)
    btn_top_save_view.pack(side=tk.LEFT, padx=(6, 0))
    _legacy_reset_columns_label = "Resetar colunas"
    btn_top_reload = build_secondary_button(theme_bar, "🔄 Recarregar", lambda: None)
    btn_top_reload.pack(side=tk.LEFT, padx=(6, 0))
    btn_top_clear = build_secondary_danger_button(theme_bar, "🧹 Limpar", lambda: None)
    btn_top_clear.pack(side=tk.LEFT, padx=(6, 0))
    btn_top_toggle_filters = build_secondary_button(theme_bar, "🧰 ⌃ Mostrar filtros", lambda: None)
    btn_top_toggle_filters.pack(side=tk.LEFT, padx=(6, 0))
    op_mode_defaults = bool((_load_prefs().get("operation_mode") or False))
    op_mode_var = tk.BooleanVar(value=op_mode_defaults)
    op_mode_chk = tk.Checkbutton(theme_bar, text="Modo Operação", variable=op_mode_var, bg=UI_THEME["bg"], fg=UI_THEME.get("on_surface", UI_THEME["text"]), selectcolor=UI_THEME["surface"], activebackground=UI_THEME["bg"])
    op_mode_chk.pack(side=tk.LEFT, padx=(12, 0))
    focus_mode_var = tk.BooleanVar(value=False)
    focus_mode_chk = tk.Checkbutton(theme_bar, text="Focus mode", variable=focus_mode_var, bg=UI_THEME["bg"], fg=UI_THEME.get("on_surface", UI_THEME["text"]), selectcolor=UI_THEME["surface"], activebackground=UI_THEME["bg"])
    focus_mode_chk.pack(side=tk.LEFT, padx=(8, 0))

    def _refresh_theme_in_place():
        try:
            container.configure(bg=UI_THEME["bg"])
            theme_bar.configure(bg=UI_THEME["bg"])
            info_label.configure(bg=UI_THEME["bg"], fg=UI_THEME["muted_text"])
        except Exception:
            pass
        refresh_theme(container, context="interfacetwo")
        apply_ttk_theme_styles(container)
        try:
            style_local = ttk.Style(container)
            style_local.configure("Dark.TNotebook", background=UI_THEME["bg"], borderwidth=0, relief="flat", highlightthickness=0, bordercolor=UI_THEME.get("bg", "#1E1E1E"), lightcolor=UI_THEME.get("bg", "#1E1E1E"), darkcolor=UI_THEME.get("bg", "#1E1E1E"))
            style_local.layout("Monitor.Tabless.TNotebook.Tab", [])
            style_local.configure("Monitor.Tabless.TNotebook", background=UI_THEME["surface"], borderwidth=0, relief="flat", highlightthickness=0, bordercolor=UI_THEME["surface"], lightcolor=UI_THEME["surface"], darkcolor=UI_THEME["surface"])
            style_local.configure("Dark.TNotebook.Tab", background=UI_THEME.get("surface_alt", UI_THEME["surface"]), foreground=UI_THEME.get("on_surface", UI_THEME["text"]), padding=(12, 4), relief="flat", borderwidth=1, highlightthickness=1, bordercolor=UI_THEME.get("border", UI_THEME["surface_alt"]), focuscolor=UI_THEME.get("surface_alt", UI_THEME["surface"]))
            style_local.map(
                "Dark.TNotebook.Tab",
                background=[("selected", UI_THEME.get("surface_alt", UI_THEME["surface"])), ("active", UI_THEME.get("border", UI_THEME["surface_alt"]))],
                foreground=[("selected", UI_THEME.get("on_surface", UI_THEME["text"])), ("active", UI_THEME.get("on_surface", UI_THEME["text"]))],
                focuscolor=[("selected", UI_THEME.get("surface_alt", UI_THEME["surface"])), ("active", UI_THEME.get("border", UI_THEME["surface_alt"]))],
                padding=[("selected", (12, 4)), ("active", (12, 4))],
            )
            style_local.configure("Control.Treeview", background=UI_THEME["surface"], fieldbackground=UI_THEME["surface"], foreground=UI_THEME.get("on_surface", UI_THEME["text"]), bordercolor=UI_THEME["border"], rowheight=28)
            style_local.configure("Control.Treeview.Heading", background=UI_THEME["surface_alt"], foreground=UI_THEME.get("on_surface", UI_THEME["text"]), relief="flat", font=theme_font("font_md"))
            style_local.map("Control.Treeview", background=[("selected", UI_THEME.get("selection_bg", UI_THEME["primary"]))], foreground=[("selected", UI_THEME.get("selection_fg", UI_THEME.get("on_primary", UI_THEME["text"])))])
        except Exception:
            pass
        for target in list(_monitor_sources.keys()):
            try:
                _populate_text(target, info_label)
            except Exception:
                pass
        _update_status_cards()

    table_trees = []
    cards_widgets = []

    def _apply_density(_mode_label=None):
        global _layout_density_mode
        _layout_density_mode = "confortavel"
        rowheight = 30
        gap = theme_space("space_2", 8)
        try:
            ttk.Style(container).configure("Control.Treeview", rowheight=rowheight)
        except Exception:
            pass
        try:
            cards_row.pack_configure(pady=(gap, 0))
            hints.pack_configure(pady=(theme_space("space_1", 4), 0))
            info_label.pack_configure(pady=(theme_space("space_1", 4), 0))
            notebook.pack_configure(pady=(gap, theme_space("space_3", 10)))
        except Exception:
            pass
        for card in cards_widgets:
            try:
                card.set_density(_layout_density_mode)
            except Exception:
                pass
        for tree in table_trees:
            try:
                tree.configure(height=14)
            except Exception:
                pass
        for w in (btn_top_details, btn_top_export, btn_top_save_view, btn_top_reload, btn_top_clear, btn_top_toggle_filters):
            try:
                w.configure(padx=12, pady=4)
            except Exception:
                pass
        _persist_ui_state({"layout_density": _layout_density_mode})

    def _on_theme_change(_event=None):
        selected = apply_theme("principal")
        report_status("ux_metrics", "OK", stage="theme_switch", details={"theme": selected})
        _persist_ui_state({"theme": selected})
        _refresh_theme_in_place()
        _apply_density()

    def _toggle_operation_mode(*_args):
        global _operation_mode_enabled, _runtime_refresh_ms
        _operation_mode_enabled = bool(op_mode_var.get())
        if _operation_mode_enabled:
            apply_theme("principal")
            _runtime_refresh_ms = 1000
            
            focus_mode_var.set(True)
            report_status("ux_metrics", "OK", stage="operation_mode_enabled", details={"theme": get_active_theme_name(), "refresh_ms": _runtime_refresh_ms})
            try:
                hints.pack_forget()
            except Exception:
                pass
            try:
                _status_bar.set("Modo Operação: refresh acelerado e foco em alertas críticos", tone="warning")
            except Exception:
                pass
        else:
            _runtime_refresh_ms = REFRESH_MS
            focus_mode_var.set(False)
            try:
                hints.pack(padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4), 0), anchor="w")
            except Exception:
                pass
            report_status("ux_metrics", "OK", stage="operation_mode_disabled", details={"refresh_ms": _runtime_refresh_ms})
        _persist_ui_state({"operation_mode": _operation_mode_enabled})
        _refresh_theme_in_place()
        _apply_density()

    def _toggle_focus_mode(*_args):
        enabled = bool(focus_mode_var.get())
        try:
            if enabled:
                hints.pack_forget()
                info_label.pack_forget()
            else:
                info_label.pack(padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4), 0), anchor="w")
                if not _operation_mode_enabled:
                    hints.pack(padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4), 0), anchor="w")
        except Exception:
            pass
        report_status("ux_metrics", "OK", stage="focus_mode_toggle", details={"enabled": enabled})

    btn_top_theme.configure(command=_on_theme_change)
    op_mode_var.trace_add("write", _toggle_operation_mode)
    focus_mode_var.trace_add("write", _toggle_focus_mode)

    title_row = tk.Frame(container, bg=UI_THEME["bg"])
    title_row.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4), 0))
    title = build_section_title(title_row, "Painel Operacional")
    title.configure(font=theme_font("font_xl", "bold"))
    title.pack(side=tk.LEFT, fill=tk.X, expand=True)
    global _control_filtered_count_var
    _control_filtered_count_var = tk.StringVar(value="Registros filtrados: 0 / 0")
    filtered_label = build_label(title_row, "", muted=True, bg=UI_THEME["bg"], font=theme_font("font_sm"))
    filtered_label.configure(textvariable=_control_filtered_count_var)
    filtered_label.pack(side=tk.RIGHT)

    cards_row = tk.Frame(container, bg=UI_THEME["bg"])
    cards_row.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(theme_space("space_2", 8), 0))
    global _ux_cards, _status_bar
    _ux_cards = {
        "ativos": AppMetricCard(cards_row, "Ativos", tone="info", icon="📦"),
        "pendentes": AppMetricCard(cards_row, "Pendentes", tone="warning", icon="⏳"),
        "sem_contato": AppMetricCard(cards_row, "Sem contato", tone="danger", icon="☎"),
        "avisado": AppMetricCard(cards_row, "Avisado", tone="success", icon="✅"),
    }
    cards_tooltips = {
        "ativos": "Total de avisos atualmente ativos no sistema.",
        "pendentes": "Soma de alertas pendentes + status pendente.",
        "sem_contato": "Registros com status marcado como SEM CONTATO.",
        "avisado": "Registros com status marcado como AVISADO.",
    }
    card_gap = theme_space("space_1", 4)
    for idx, key in enumerate(["ativos", "pendentes", "sem_contato", "avisado"]):
        card = _ux_cards[key]
        right_gap = card_gap if idx < 3 else 0
        card.grid(row=0, column=idx, padx=(0, right_gap), pady=(0, 0), ipady=11, sticky="nsew")
        cards_row.grid_columnconfigure(idx, weight=1, uniform="metric_cards")
        cards_widgets.append(card)
        attach_tooltip(card, cards_tooltips.get(key, ""))
        try:
            card.set_donut_visibility(False)
        except Exception:
            pass

    def _play_metric_cards_intro_animation():
        order = ["ativos", "pendentes", "sem_contato", "avisado"]
        duration_ms = 780
        steps = 20

        def _animate_donuts_sync():
            for key in order:
                card = _ux_cards.get(key)
                if card is None:
                    continue
                try:
                    card.animate_capacity_fill()
                except Exception:
                    continue

        def _play_next(pos=0):
            if pos >= len(order):
                _animate_donuts_sync()
                return
            card = _ux_cards.get(order[pos])
            if card is None:
                _play_next(pos + 1)
                return
            try:
                card.animate_accent_growth(duration_ms=duration_ms, steps=steps, on_done=lambda: _play_next(pos + 1))
            except Exception:
                _play_next(pos + 1)

        _play_next(0)

    consumo_header = tk.Frame(container, bg=UI_THEME["bg"])
    consumo_header.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(theme_space("space_3", 16), 0))
    consumo_title = build_label(consumo_header, "Consumo por dia", bg=UI_THEME["bg"], font=theme_font("font_lg", "bold"))
    consumo_title.pack(side=tk.LEFT)
    consumo_day_var = tk.StringVar(value="")
    consumo_day_label = build_label(consumo_header, "", muted=True, bg=UI_THEME["bg"], font=theme_font("font_sm"))
    consumo_day_label.configure(textvariable=consumo_day_var)
    consumo_day_label.pack(side=tk.RIGHT)

    consumo_graph_frame = tk.Frame(container, bg=UI_THEME["bg"], highlightthickness=0, bd=0)
    consumo_graph_frame.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(theme_space("space_2", 8), theme_space("space_3", 16)))

    consumo_hint = build_label(consumo_graph_frame, "Cada ponto representa um dia e serve para editar o consumo diário.", muted=True, bg=UI_THEME["bg"], font=theme_font("font_sm"))
    consumo_hint.pack(fill=tk.X, pady=(0, theme_space("space_1", 4)), anchor="w")

    consumo_days_canvas = tk.Canvas(consumo_graph_frame, bg=UI_THEME["bg"], height=180, highlightthickness=0, bd=0)
    consumo_days_canvas.pack(fill=tk.X, padx=0, pady=(0, theme_space("space_2", 8)))

    _load_consumo_24h_data()
    consumo_selected_day = max(_consumo_24h_por_dia.keys()) if _consumo_24h_por_dia else datetime.now().strftime("%Y-%m-%d")

    def _save_day_points(day_key: str, points: list[int]):
        _consumo_24h_por_dia[day_key] = _normalizar_24h(points)
        _save_consumo_24h_data()

    def _update_day_total(day_key: str, target_total: int):
        src = _carregar_consumo_24h(day_key)
        target_total = max(0, min(2400, int(target_total)))
        current_total = sum(src)
        if current_total <= 0:
            base = target_total // 24
            rem = target_total % 24
            out = [base] * 24
            for i in range(rem):
                out[i] += 1
            _save_day_points(day_key, out)
            return

        factor = target_total / float(current_total)
        scaled = [max(0, min(100, int(round(v * factor)))) for v in src]
        delta = target_total - sum(scaled)
        idx = 0
        guard = 0
        while delta != 0 and guard < 5000:
            if delta > 0 and scaled[idx] < 100:
                scaled[idx] += 1
                delta -= 1
            elif delta < 0 and scaled[idx] > 0:
                scaled[idx] -= 1
                delta += 1
            idx = (idx + 1) % 24
            guard += 1
        _save_day_points(day_key, scaled)

    def _draw_days_timeline(_event=None):
        nonlocal consumo_selected_day
        consumo_days_canvas.delete("all")
        day_keys = sorted(_consumo_24h_por_dia.keys())
        if not day_keys:
            return
        if consumo_selected_day not in _consumo_24h_por_dia:
            consumo_selected_day = day_keys[-1]

        width = max(360, int(consumo_days_canvas.winfo_width() or 360))
        height = max(140, int(consumo_days_canvas.winfo_height() or 140))
        margin_x = 18
        margin_y = 18
        plot_w = max(10, width - margin_x * 2)
        plot_h = max(10, height - margin_y * 2)
        step = plot_w / max(1, len(day_keys) - 1)
        totals = [sum(_carregar_consumo_24h(day)) for day in day_keys]
        min_total, max_total = min(totals), max(totals)

        coords = []
        for idx, day_key in enumerate(day_keys):
            x = margin_x + idx * step
            total = totals[idx]
            if max_total == min_total:
                y = margin_y + (plot_h * 0.5)
            else:
                ratio = (total - min_total) / (max_total - min_total)
                y = margin_y + plot_h * (1 - ratio)
            coords.append((x, y, day_key, total))

        def _on_day_click(day_key: str):
            nonlocal consumo_selected_day
            current_total = sum(_carregar_consumo_24h(day_key))
            value = simpledialog.askinteger(
                "Editar consumo diário",
                f"Informe o total de consumo do dia {day_key} (0-2400):",
                parent=container.winfo_toplevel(),
                minvalue=0,
                maxvalue=2400,
                initialvalue=current_total,
            )
            if value is None:
                return
            _update_day_total(day_key, int(value))
            consumo_selected_day = day_key
            consumo_day_var.set(f"Dia selecionado: {day_key} • Total: {sum(_carregar_consumo_24h(day_key))}")
            _draw_days_timeline()

        for x, y, day_key, total in coords:
            is_selected = day_key == consumo_selected_day
            radius = 6 if is_selected else 5
            item = consumo_days_canvas.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="#FFFFFF",
                outline="#FFFFFF",
                width=2 if is_selected else 1,
            )
            consumo_days_canvas.tag_bind(item, "<Button-1>", lambda _evt, d=day_key: _on_day_click(d))
            consumo_days_canvas.tag_bind(item, "<Enter>", lambda _evt, d=day_key, t=total: consumo_days_canvas.itemconfigure("hoverday", text=f"{d} total: {t}"))

        consumo_days_canvas.create_text(width - 8, 10, text="", anchor="ne", tags="hoverday", fill="#FFFFFF", font=theme_font("font_sm"))
        consumo_day_var.set(f"Dia selecionado: {consumo_selected_day} • Total: {sum(_carregar_consumo_24h(consumo_selected_day))}")

    consumo_days_canvas.bind("<Configure>", _draw_days_timeline, add="+")
    container.after(80, _draw_days_timeline)

    global _metrics_accessibility_var
    _metrics_accessibility_var = tk.StringVar(value="Métricas: carregando")
    metrics_accessibility_label = build_label(container, "", muted=True, bg=UI_THEME["bg"], font=theme_font("font_sm"))
    metrics_accessibility_label.configure(textvariable=_metrics_accessibility_var)

    hints = build_label(container, "Atalhos: Ctrl+F buscar • Ctrl+Enter aplicar • Ctrl+Shift+L limpar • Alt+1..4 abas • Alt+E exportar • Alt+V salvar visão", muted=True, bg=UI_THEME["bg"], font=theme_font("font_sm"))

    def _toggle_details_panel():
        details_visible.set(not details_visible.get())
        visible = details_visible.get()
        widgets = (metrics_accessibility_label, hints, info_label)
        for widget in widgets:
            try:
                if visible:
                    widget.pack(padx=theme_space("space_3", 10), pady=(theme_space("space_1", 4), 0), anchor="w")
                else:
                    widget.pack_forget()
            except Exception:
                pass

    btn_top_details.configure(command=_toggle_details_panel)

    def _toggle_top_controls():
        if theme_bar.winfo_manager():
            theme_bar.pack_forget()
        else:
            theme_bar.pack(fill=tk.X, padx=10, pady=(6, 0), before=title_row)

    btn_eye.configure(command=_toggle_top_controls)

    _status_bar = AppStatusBar(container, text="UX: aguardando eventos")
    global _feedback_banner
    _feedback_banner = AppFeedbackBanner(container, text="")

    records_panel = tk.Frame(container, bg=UI_THEME["surface"])
    records_panel.pack(fill=tk.BOTH, expand=True, padx=theme_space("space_3", 10), pady=(theme_space("space_4", 20), theme_space("space_3", 10)))

    tab_button_bar = tk.Frame(records_panel, bg=UI_THEME["surface"])
    tab_button_bar.pack(fill=tk.X, padx=0, pady=(0, 0))

    notebook = ttk.Notebook(records_panel, style="Monitor.Tabless.TNotebook")
    notebook.pack(padx=0, pady=(0, 0), fill=tk.BOTH, expand=True)
    notebook.configure(padding=0)

    controle_frame = tk.Frame(notebook, bg=UI_THEME["surface"])
    encomendas_frame = tk.Frame(notebook, bg=UI_THEME["surface"])
    orientacoes_frame = tk.Frame(notebook, bg=UI_THEME["surface"])
    observacoes_frame = tk.Frame(notebook, bg=UI_THEME["surface"])

    notebook.add(controle_frame, text="CONTROLE")
    notebook.add(encomendas_frame, text="ENCOMENDAS")
    notebook.add(orientacoes_frame, text="ORIENTAÇÕES")
    notebook.add(observacoes_frame, text="OBSERVAÇÕES")

    def _select_tab(index: int):
        try:
            notebook.select(index)
        except Exception:
            pass

    tab_buttons = []
    tab_button_frames = []
    tab_button_bottom_borders = []
    tab_border_color = UI_THEME.get("border", UI_THEME.get("on_surface", UI_THEME["text"]))
    tab_button_normal_bg = UI_THEME.get("bg", UI_THEME["surface"])
    tab_button_selected_bg = UI_THEME.get("surface", UI_THEME["bg"])
    tab_button_hover_bg = UI_THEME.get("border", tab_button_normal_bg)
    for idx, label in enumerate(["CONTROLE", "ENCOMENDAS", "ORIENTAÇÕES", "OBSERVAÇÕES"]):
        btn_frame = tk.Frame(tab_button_bar, bg=tab_border_color)
        btn_tab = build_secondary_button(btn_frame, label, lambda i=idx: _select_tab(i), padx=12)
        try:
            btn_tab.configure(
                font=theme_font("font_md"),
                pady=theme_space("space_1", 4),
                bg=tab_button_normal_bg,
                activebackground=tab_button_normal_bg,
                highlightbackground=tab_border_color,
                highlightcolor=tab_border_color,
                highlightthickness=0,
                bd=0,
                relief="flat",
            )
        except Exception:
            pass
        try:
            def _on_tab_enter(_e, b=btn_tab):
                b.configure(bg=tab_button_hover_bg, activebackground=tab_button_hover_bg)

            def _on_tab_leave(_e):
                _refresh_tab_button_state()

            btn_tab.bind("<Enter>", _on_tab_enter, add="+")
            btn_tab.bind("<Leave>", _on_tab_leave, add="+")
        except Exception:
            pass
        btn_tab.pack(fill=tk.BOTH, expand=True, padx=1, pady=(1, 0))
        btn_bottom = tk.Frame(btn_frame, height=1, bg=tab_border_color)
        btn_bottom.pack(fill=tk.X, side=tk.BOTTOM)
        btn_frame.pack(side=tk.LEFT, padx=(0, 0), pady=(0, 0), fill=tk.BOTH, expand=True)
        tab_button_frames.append(btn_frame)
        tab_buttons.append(btn_tab)
        tab_button_bottom_borders.append(btn_bottom)

    def _refresh_tab_button_state(*_):
        try:
            selected = notebook.index(notebook.select())
        except Exception:
            selected = 0
        for idx, (btn_frame, btn, btn_bottom) in enumerate(zip(tab_button_frames, tab_buttons, tab_button_bottom_borders)):
            try:
                is_selected = idx == selected
                target_bg = tab_button_selected_bg if is_selected else tab_button_normal_bg
                frame_bg = tab_button_selected_bg if is_selected else tab_border_color
                btn_frame.configure(bg=frame_bg)
                btn.configure(bg=target_bg, activebackground=target_bg)
                btn_bottom.configure(bg=tab_button_selected_bg if is_selected else tab_border_color)
            except Exception:
                continue

    notebook.bind("<<NotebookTabChanged>>", _refresh_tab_button_state, add="+")
    _refresh_tab_button_state()

    try:
        root_win = container.winfo_toplevel()
        def _show_shortcuts(_e=None):
            messagebox.showinfo(
                "Atalhos do monitor",
                "Ctrl+F: foco na busca\nCtrl+Enter: aplicar filtros\nCtrl+Shift+L: limpar filtros\nAlt+1..4: trocar abas\nF1: ajuda de atalhos",
                parent=root_win,
            )
            return "break"
        root_win.bind("<Alt-Key-1>", lambda _e: (report_status("ux_metrics", "OK", stage="shortcut_used", details={"shortcut": "Alt+1"}), _select_tab(0), "break")[2], add="+")
        root_win.bind("<Alt-Key-2>", lambda _e: (report_status("ux_metrics", "OK", stage="shortcut_used", details={"shortcut": "Alt+2"}), _select_tab(1), "break")[2], add="+")
        root_win.bind("<Alt-Key-3>", lambda _e: (report_status("ux_metrics", "OK", stage="shortcut_used", details={"shortcut": "Alt+3"}), _select_tab(2), "break")[2], add="+")
        root_win.bind("<Alt-Key-4>", lambda _e: (report_status("ux_metrics", "OK", stage="shortcut_used", details={"shortcut": "Alt+4"}), _select_tab(3), "break")[2], add="+")
        root_win.bind("<F1>", _show_shortcuts, add="+")
    except Exception:
        pass

    monitor_widgets = []

    def _apply_filter_visibility(source_key: str):
        filter_bar = _filter_bars.get(source_key)
        if not filter_bar:
            return
        if _filter_toggle_state.get("visible", False):
            try:
                filter_bar.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(0, theme_space("space_2", 8)), before=filter_bar._filter_target_widget)
            except Exception:
                try:
                    filter_bar.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(0, theme_space("space_2", 8)))
                except Exception:
                    return
        else:
            try:
                filter_bar.pack_forget()
            except Exception:
                return

    def _sync_filter_toggle_labels():
        visible = _filter_toggle_state.get("visible", False)
        label = "🧰 ⌄ Ocultar filtros" if visible else "🧰 ⌃ Mostrar filtros"
        for btn in [btn_top_toggle_filters]:
            try:
                btn.configure(text=label)
            except Exception:
                continue

    def _toggle_filters(source_key: str = "global"):
        _filter_toggle_state["visible"] = not _filter_toggle_state.get("visible", False)
        for key in list(_filter_bars.keys()):
            _apply_filter_visibility(key)
        _sync_filter_toggle_labels()
        report_status("ux_metrics", "OK", stage="filter_banner_toggle", details={"source": source_key, "visible": _filter_toggle_state["visible"]})

    tab_configs = [
        (controle_frame, ARQUIVO, format_creative_entry, "controle"),
        (encomendas_frame, ENCOMENDAS_ARQUIVO, format_encomenda_entry, "encomendas"),
        (orientacoes_frame, ORIENTACOES_ARQUIVO, format_orientacao_entry, "orientacoes"),
        (observacoes_frame, OBSERVACOES_ARQUIVO, format_observacao_entry, "observacoes"),
    ]

    def _control_filtered_records():
        registros = _load_safe(ARQUIVO)
        filters = _filter_state.get("controle", {})
        return _apply_filters(registros, filters)

    def _export_control_csv():
        try:
            out = os.path.join(BASE_DIR, f"controle_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            rows = _control_filtered_records()
            with open(out, "w", encoding="utf-8") as f:
                f.write("id,data_hora,nome,sobrenome,bloco,apartamento,placa,modelo,cor,status,texto\n")
                for rec in rows:
                    cols = [
                        _record_original_id(rec),
                        str(rec.get("DATA_HORA") or ""),
                        str(rec.get("NOME") or ""),
                        str(rec.get("SOBRENOME") or ""),
                        str(rec.get("BLOCO") or ""),
                        str(rec.get("APARTAMENTO") or ""),
                        str(rec.get("PLACA") or ""),
                        str(rec.get("MODELO") or ""),
                        str(rec.get("COR") or ""),
                        str(rec.get("STATUS") or ""),
                        format_creative_entry(rec),
                    ]
                    safe_cols = [str(v).replace('"', "''") for v in cols]
                    f.write(','.join(f'"{v}"' for v in safe_cols) + "\n")
            _announce_feedback(f"CSV exportado: {os.path.basename(out)}", "success")
        except Exception as exc:
            _announce_feedback(f"Falha ao exportar CSV: {exc}", "danger")

    def _save_control_view():
        try:
            _persist_ui_state({
                "control_view": {
                    "filters": dict(_filter_state.get("controle") or {}),
                    "as_text": True,
                }
            })
            _announce_feedback("Visão da aba CONTROLE salva", "success")
        except Exception as exc:
            _announce_feedback(f"Falha ao salvar visão: {exc}", "danger")

    btn_top_export.configure(command=lambda: (report_status("ux_metrics", "OK", stage="toolbar_export_csv", details={"source": "controle"}), _export_control_csv()))
    btn_top_save_view.configure(command=lambda: (report_status("ux_metrics", "OK", stage="toolbar_save_view", details={"source": "controle"}), _save_control_view()))
    btn_top_reload.configure(command=lambda: forcar_recarregar(monitor_widgets, info_label))
    btn_top_clear.configure(command=lambda: limpar_dados(monitor_widgets, info_label, btn_top_clear))
    btn_top_toggle_filters.configure(command=lambda: _toggle_filters("global"))
    attach_tooltip(btn_top_reload, "Recarrega todos os dados do monitor")
    attach_tooltip(btn_top_clear, "Cria backup e limpa os registros exibidos")

    try:
        root_win.bind("<Alt-e>", lambda _e: (btn_top_export.invoke(), "break")[1], add="+")
        root_win.bind("<Alt-v>", lambda _e: (btn_top_save_view.invoke(), "break")[1], add="+")
    except Exception:
        pass

    for frame, arquivo, formatter, filter_key in tab_configs:
        sticky_var = tk.StringVar(value="Sem registros visíveis")
        sticky_label = build_label(
            frame,
            "",
            muted=False,
            bg=UI_THEME["surface"],
            font=theme_font("font_md")
        )
        sticky_label.configure(textvariable=sticky_var, anchor="w", justify="left", padx=0)
        sticky_label.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(0, 0))

        records_top_line = tk.Frame(frame, bg="#000000", height=2)
        records_top_line.pack(fill=tk.X, padx=0, pady=(0, 0))

        text_widget = tk.Text(
            frame,
            wrap="word",
            bg=UI_THEME["surface"],
            fg=UI_THEME.get("on_surface", UI_THEME["text"]),
            insertbackground=UI_THEME.get("on_surface", UI_THEME["text"]),
            relief="flat",
            bd=0,
            highlightthickness=0,
            undo=True,
            autoseparators=True,
            maxundo=-1,
        )
        filter_bar = _build_filter_bar(frame, filter_key, info_label, target_widget=text_widget)
        filter_bar._filter_target_widget = text_widget
        _filter_bars[str(filter_key)] = filter_bar
        _apply_filter_visibility(str(filter_key))
        if formatter == format_encomenda_entry:
            text_widget.tag_configure("status_avisado", foreground=UI_THEME["status_avisado_text"])
            text_widget.tag_configure("status_sem_contato", foreground=UI_THEME["status_sem_contato_text"])
            text_widget.tag_configure("encomenda_selected", background=UI_THEME.get("selection_bg", UI_THEME["focus_bg"]), foreground=UI_THEME.get("selection_fg", UI_THEME["focus_text"]))
        if filter_key == "controle":
            text_widget.tag_configure("controle_selected", background=UI_THEME.get("selection_bg", UI_THEME["focus_bg"]), foreground=UI_THEME.get("selection_fg", UI_THEME["focus_text"]))
        text_widget.pack(padx=theme_space("space_3", 10), pady=(0, theme_space("space_2", 8)), fill=tk.BOTH, expand=True)
        text_widget.config(state="disabled")
        _sticky_header_state[text_widget] = {"var": sticky_var, "formatter": formatter}
        _bind_sticky_header_updates(text_widget)
        _bind_hover_highlight(text_widget)
        if formatter == format_encomenda_entry:
            _build_encomenda_actions(frame, text_widget, info_label)
        elif formatter in (format_orientacao_entry, format_observacao_entry):
            _build_text_actions(frame, text_widget, info_label, arquivo)
        if filter_key == "controle":
            details_var = tk.StringVar(value="Selecione um registro para ver detalhes.")
            details = tk.Label(frame, textvariable=details_var, bg=UI_THEME["surface_alt"], fg=UI_THEME.get("on_surface", UI_THEME["text"]), anchor="w", justify="left", padx=theme_space("space_3", 10), pady=theme_space("space_2", 8), font=theme_font("font_md"))
            details.pack(fill=tk.X, padx=theme_space("space_3", 10), pady=(0, theme_space("space_3", 10)))
            _control_details_var[text_widget] = details_var
        monitor_widgets.append(text_widget)
        _monitor_sources[text_widget] = {"path": arquivo, "formatter": formatter, "filter_key": filter_key, "widget": text_widget}

    if not prefs.get("onboarding_seen"):
        _announce_feedback("Use Ctrl+F para busca e Alt+1..4 para trocar abas", "info")
        _persist_ui_state({"onboarding_seen": True})

    _apply_density()
    if op_mode_var.get():
        _toggle_operation_mode()
    try:
        container.after(3000, _play_metric_cards_intro_animation)
    except Exception:
        pass
    _update_status_cards()
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
