"""
main.py
Inicializa o sistema:
 - garante pré-estruturas (analises.json, avisos.json)
 - dispara análise/avisos no startup
 - roda um watcher que observa alterações em dadosend.json e encomendasend.json
 - atualiza analises/avisos por identidade e por encomendas
 - inicia a UI via interfaceone.iniciar_interface_principal()
"""
import os
import time
import json
import hashlib
import threading
import traceback
from collections import deque

try:
    from runtime_status import report_status, report_log
except Exception:
    def report_status(*args, **kwargs):
        return None

    def report_log(*args, **kwargs):
        return None

BASE = os.path.dirname(os.path.abspath(__file__))
DADOSEND = os.path.join(BASE, "dadosend.json")
ANALISES_JSON = os.path.join(BASE, "analises.json")
AVISOS_JSON = os.path.join(BASE, "avisos.json")
ENCOMENDASEND = os.path.join(BASE, "encomendasend.json")

POLL_INTERVAL = 1.0
WATCHER_DEBOUNCE_WINDOW = 0.35

_ANALISES_TEMPLATE = {"registros": [], "encomendas_multiplas_bloco_apartamento": []}
_AVISOS_TEMPLATE = {"registros": [], "ultimo_aviso_ativo": None}


def _log(level: str, stage: str, message: str, **details):
    report_log("main", level, message, stage=stage, details=details)
    print(f"[main] {message}")


def ensure_file(path, template):
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            _log("OK", "ensure_file_created", f"Criado: {path}", path=path)
        except OSError as e:
            _log("ERROR", "ensure_file_create_failed", "Falha ao criar arquivo", path=path, error=str(e))
    else:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("conteúdo inválido")
        except (OSError, ValueError, json.JSONDecodeError):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(template, f, ensure_ascii=False, indent=2)
                _log("OK", "ensure_file_recreated", f"Recriado (template aplicado): {path}", path=path)
            except OSError as e:
                _log("ERROR", "ensure_file_recreate_failed", "Falha ao recriar arquivo", path=path, error=str(e))


def _identity_from_record(rec):
    def _v(k):
        return (rec.get(k, "") or "").strip().upper()

    return f"{_v('NOME')}|{_v('SOBRENOME')}|{_v('BLOCO')}|{_v('APARTAMENTO')}"


def _get_last_record_identity(dadosend_path):
    try:
        with open(dadosend_path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    regs = []
    if isinstance(d, dict) and "registros" in d:
        regs = d.get("registros") or []
    elif isinstance(d, list):
        regs = d
    if not regs:
        return None
    try:
        regs_with_id = [r for r in regs if isinstance(r.get("ID"), int)]
        if regs_with_id:
            last = max(regs_with_id, key=lambda r: int(r.get("ID") or 0))
            return _identity_from_record(last)
    except (TypeError, ValueError):
        pass

    def _dt_key(rec):
        s = rec.get("DATA_HORA") or rec.get("data_hora") or ""
        try:
            from datetime import datetime
            for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
                try:
                    return datetime.strptime(s, fmt)
                except ValueError:
                    pass
        except Exception:
            pass
        return None

    try:
        regs_with_dt = [(r, _dt_key(r)) for r in regs]
        regs_with_dt = [t for t in regs_with_dt if t[1] is not None]
        if regs_with_dt:
            last = max(regs_with_dt, key=lambda t: t[1])[0]
            return _identity_from_record(last)
    except Exception:
        pass

    try:
        return _identity_from_record(regs[-1])
    except Exception:
        return None


def _file_fingerprint(path):
    """
    Gera uma assinatura estável do conteúdo para ignorar mudanças apenas de mtime.
    """
    try:
        with open(path, "rb") as f:
            content = f.read()
        return hashlib.sha1(content).hexdigest()
    except OSError:
        return None


def _process_dadosend_change(dadosend_path, analises_mod, avisos_mod):
    report_status("watcher", "STARTED", stage="dadosend_changed")
    _log("STARTED", "dadosend_changed", "Alteração detectada em dadosend.json")
    ident = _get_last_record_identity(dadosend_path)
    if ident:
        try:
            analises_mod.build_analises_for_identity(ident, dadosend_path, ANALISES_JSON)
            report_status("watcher", "OK", stage="build_analises_for_identity", details={"identidade": ident})
        except Exception:
            report_status("watcher", "ERROR", stage="build_analises_for_identity", details={"identidade": ident, "error": traceback.format_exc()})
            try:
                analises_mod.build_analises(dadosend_path, ANALISES_JSON)
                report_status("watcher", "OK", stage="build_analises_full")
            except Exception:
                _log("ERROR", "build_analises_full_failed", "erro build_analises (fallback)", error=traceback.format_exc())

        try:
            avisos_mod.build_avisos_for_identity(ident, ANALISES_JSON, AVISOS_JSON)
            report_status("watcher", "OK", stage="build_avisos_for_identity", details={"identidade": ident})
        except Exception:
            report_status("watcher", "ERROR", stage="build_avisos_for_identity", details={"identidade": ident, "error": traceback.format_exc()})
            try:
                avisos_mod.build_avisos(ANALISES_JSON, AVISOS_JSON)
                report_status("watcher", "OK", stage="build_avisos_full")
            except Exception:
                _log("ERROR", "build_avisos_full_failed", "erro build_avisos (fallback)", error=traceback.format_exc())
    else:
        _log("WARNING", "identity_missing", "não foi possível identificar registro — recalculando tudo")
        try:
            analises_mod.build_analises(dadosend_path, ANALISES_JSON)
            report_status("watcher", "OK", stage="build_analises_full")
        except Exception:
            _log("ERROR", "build_analises_full_failed", "erro build_analises", error=traceback.format_exc())
        try:
            avisos_mod.build_avisos(ANALISES_JSON, AVISOS_JSON)
            report_status("watcher", "OK", stage="build_avisos_full")
        except Exception:
            _log("ERROR", "build_avisos_full_failed", "erro build_avisos", error=traceback.format_exc())


def _process_encomendas_change(dadosend_path, analises_mod, avisos_mod):
    report_status("watcher", "STARTED", stage="encomendas_changed")
    _log("STARTED", "encomendas_changed", "Alteração detectada em encomendasend.json")
    try:
        analises_mod.build_analises(dadosend_path, ANALISES_JSON)
        report_status("watcher", "OK", stage="build_analises_full")
    except Exception:
        report_status("watcher", "ERROR", stage="build_analises_full", details={"error": traceback.format_exc()})
        _log("ERROR", "build_analises_full_failed", "erro build_analises (encomendas)", error=traceback.format_exc())
    try:
        avisos_mod.build_avisos(ANALISES_JSON, AVISOS_JSON)
        report_status("watcher", "OK", stage="build_avisos_full")
    except Exception:
        report_status("watcher", "ERROR", stage="build_avisos_full", details={"error": traceback.format_exc()})
        _log("ERROR", "build_avisos_full_failed", "erro build_avisos (encomendas)", error=traceback.format_exc())


def watcher_thread(dadosend_path, analises_mod, avisos_mod, poll=POLL_INTERVAL, debounce_window=WATCHER_DEBOUNCE_WINDOW):
    _log("OK", "watcher_started", f"Watcher iniciado para {dadosend_path} e {ENCOMENDASEND}")
    last_mtime_dadosend = None
    last_mtime_encomendas = None
    last_fp_dadosend = None
    last_fp_encomendas = None
    pending_events = deque()
    pending_map = {}
    while True:
        now = time.time()
        try:
            if os.path.exists(dadosend_path):
                m_dados = os.path.getmtime(dadosend_path)
                if last_mtime_dadosend is None:
                    last_mtime_dadosend = m_dados
                    last_fp_dadosend = _file_fingerprint(dadosend_path)
                elif m_dados != last_mtime_dadosend:
                    last_mtime_dadosend = m_dados
                    fp_dados = _file_fingerprint(dadosend_path)
                    if fp_dados is None or fp_dados != last_fp_dadosend:
                        last_fp_dadosend = fp_dados
                        pending_map["dadosend"] = now

            if os.path.exists(ENCOMENDASEND):
                m_encomendas = os.path.getmtime(ENCOMENDASEND)
                if last_mtime_encomendas is None:
                    last_mtime_encomendas = m_encomendas
                    last_fp_encomendas = _file_fingerprint(ENCOMENDASEND)
                elif m_encomendas != last_mtime_encomendas:
                    last_mtime_encomendas = m_encomendas
                    fp_encomendas = _file_fingerprint(ENCOMENDASEND)
                    if fp_encomendas is None or fp_encomendas != last_fp_encomendas:
                        last_fp_encomendas = fp_encomendas
                        pending_map["encomendas"] = now

            for event_name, last_change_ts in list(pending_map.items()):
                if now - last_change_ts >= debounce_window:
                    pending_events.append(event_name)
                    pending_map.pop(event_name, None)

            processed_in_tick = set()
            while pending_events:
                event_name = pending_events.popleft()
                if event_name in processed_in_tick:
                    continue
                processed_in_tick.add(event_name)
                if event_name == "dadosend":
                    _process_dadosend_change(dadosend_path, analises_mod, avisos_mod)
                elif event_name == "encomendas" and "dadosend" not in processed_in_tick:
                    _process_encomendas_change(dadosend_path, analises_mod, avisos_mod)
        except Exception:
            _log("ERROR", "watcher_loop_exception", "watcher erro", error=traceback.format_exc())
        time.sleep(poll)


def initialize_system(start_watcher=True):
    ensure_file(ANALISES_JSON, _ANALISES_TEMPLATE)
    ensure_file(AVISOS_JSON, _AVISOS_TEMPLATE)
    if not os.path.exists(DADOSEND):
        try:
            with open(DADOSEND, "w", encoding="utf-8") as f:
                json.dump({"registros": []}, f, ensure_ascii=False, indent=2)
            _log("OK", "dadosend_created", "Criado dadosend.json vazio.")
        except OSError:
            _log("ERROR", "dadosend_create_failed", "Falha ao criar dadosend.json", error=traceback.format_exc())

    try:
        import analises
        import avisos
    except Exception as e:
        _log("ERROR", "module_import_failed", "Falha ao importar analises/avisos", error=str(e))
        raise

    try:
        _log("STARTED", "build_analises_initial", "Executando build_analises() inicial...")
        analises.build_analises(DADOSEND, ANALISES_JSON)
    except Exception:
        _log("ERROR", "build_analises_initial_failed", "build_analises falhou", error=traceback.format_exc())
    try:
        _log("STARTED", "build_avisos_initial", "Executando build_avisos() inicial...")
        avisos.build_avisos(ANALISES_JSON, AVISOS_JSON)
    except Exception:
        _log("ERROR", "build_avisos_initial_failed", "build_avisos falhou", error=traceback.format_exc())

    watcher = None
    if start_watcher:
        watcher = threading.Thread(
            target=watcher_thread,
            args=(DADOSEND, analises, avisos, POLL_INTERVAL, WATCHER_DEBOUNCE_WINDOW),
            daemon=True,
        )
        watcher.start()
    return watcher


def main():
    initialize_system(start_watcher=True)
    try:
        import interfaceone
        _log("STARTED", "ui_starting", "Inicializando interface grafica (interfaceone)...")
        interfaceone.iniciar_interface_principal()
    except Exception:
        _log("ERROR", "ui_start_failed", "Falha ao iniciar interfaceone", error=traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
