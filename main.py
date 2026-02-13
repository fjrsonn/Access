
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
import threading
import traceback

try:
    from runtime_status import report_status
except Exception:
    def report_status(*args, **kwargs):
        return None

BASE = os.path.dirname(os.path.abspath(__file__))
DADOSEND = os.path.join(BASE, "dadosend.json")
ANALISES_JSON = os.path.join(BASE, "analises.json")
AVISOS_JSON = os.path.join(BASE, "avisos.json")
ENCOMENDASEND = os.path.join(BASE, "encomendasend.json")

POLL_INTERVAL = 1.0  # segundos entre verificações de mtime

# Estruturas pré-definidas (conformes com o que geramos anteriormente)
_ANALISES_TEMPLATE = {"registros": [], "encomendas_multiplas_bloco_apartamento": []}
_AVISOS_TEMPLATE = {"registros": [], "ultimo_aviso_ativo": None}

def ensure_file(path, template):
    """Cria o arquivo com template JSON se não existir ou estiver vazio/ inválido."""
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            print(f"[main] Criado: {path}")
        except Exception as e:
            print("[main] Falha ao criar", path, e)
    else:
        # tenta ler para validar; se inválido, reescreve com template
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("conteúdo inválido")
        except Exception:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(template, f, ensure_ascii=False, indent=2)
                print(f"[main] Recriado (template aplicado): {path}")
            except Exception as e:
                print("[main] Falha ao recriar", path, e)

def _identity_from_record(rec):
    """Gera identidade 'NOME|SOBRENOME|BLOCO|APARTAMENTO' a partir de um registro (robusto)."""
    def _v(k):
        return (rec.get(k, "") or "").strip().upper()
    nome = _v("NOME")
    sobrenome = _v("SOBRENOME")
    bloco = _v("BLOCO")
    ap = _v("APARTAMENTO")
    return f"{nome}|{sobrenome}|{bloco}|{ap}"

def _get_last_record_identity(dadosend_path):
    """Retorna identity da última gravação detectável em dadosend.json (por ID ou DATA_HORA)."""
    try:
        with open(dadosend_path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception:
        return None
    regs = []
    if isinstance(d, dict) and "registros" in d:
        regs = d.get("registros") or []
    elif isinstance(d, list):
        regs = d
    if not regs:
        return None
    # tentar por ID (maior ID), senão por DATA_HORA (mais recente), senão último item
    try:
        regs_with_id = [r for r in regs if isinstance(r.get("ID"), int)]
        if regs_with_id:
            last = max(regs_with_id, key=lambda r: int(r.get("ID") or 0))
            return _identity_from_record(last)
    except Exception:
        pass
    # tentativa por DATA_HORA parseável (mais recente)
    def _dt_key(rec):
        s = rec.get("DATA_HORA") or rec.get("data_hora") or ""
        try:
            # formato esperado "dd/mm/YYYY HH:MM:SS"
            from datetime import datetime
            for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
                try:
                    return datetime.strptime(s, fmt)
                except:
                    pass
        except:
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
    # fallback: último item do array
    try:
        return _identity_from_record(regs[-1])
    except Exception:
        return None

def watcher_thread(dadosend_path, analises_mod, avisos_mod, poll=POLL_INTERVAL):
    """Monitora mtime de dadosend.json e encomendasend.json e atualiza analises/avisos."""
    print("[main] Watcher iniciado para", dadosend_path, "e", ENCOMENDASEND)
    last_mtime_dadosend = None
    last_mtime_encomendas = None
    while True:
        try:
            dados_changed = False
            encomendas_changed = False

            if os.path.exists(dadosend_path):
                m_dados = os.path.getmtime(dadosend_path)
                if last_mtime_dadosend is None:
                    last_mtime_dadosend = m_dados
                elif m_dados != last_mtime_dadosend:
                    last_mtime_dadosend = m_dados
                    dados_changed = True

            if os.path.exists(ENCOMENDASEND):
                m_encomendas = os.path.getmtime(ENCOMENDASEND)
                if last_mtime_encomendas is None:
                    last_mtime_encomendas = m_encomendas
                elif m_encomendas != last_mtime_encomendas:
                    last_mtime_encomendas = m_encomendas
                    encomendas_changed = True

            if dados_changed:
                report_status("watcher", "STARTED", stage="dadosend_changed")
                print("[main] Alteração detectada em dadosend.json — iniciando análise incremental...")
                ident = _get_last_record_identity(dadosend_path)
                if ident:
                    try:
                        analises_mod.build_analises_for_identity(ident, dadosend_path, ANALISES_JSON)
                        report_status("watcher", "OK", stage="build_analises_for_identity", details={"identidade": ident})
                    except Exception:
                        report_status("watcher", "ERROR", stage="build_analises_for_identity", details={"identidade": ident, "error": traceback.format_exc()})
                        print("[main] erro build_analises_for_identity:", traceback.format_exc())
                        try:
                            analises_mod.build_analises(dadosend_path, ANALISES_JSON)
                            report_status("watcher", "OK", stage="build_analises_full")
                        except Exception:
                            print("[main] erro build_analises (fallback):", traceback.format_exc())
                    try:
                        avisos_mod.build_avisos_for_identity(ident, ANALISES_JSON, AVISOS_JSON)
                        report_status("watcher", "OK", stage="build_avisos_for_identity", details={"identidade": ident})
                    except Exception:
                        report_status("watcher", "ERROR", stage="build_avisos_for_identity", details={"identidade": ident, "error": traceback.format_exc()})
                        print("[main] erro build_avisos_for_identity:", traceback.format_exc())
                        try:
                            avisos_mod.build_avisos(ANALISES_JSON, AVISOS_JSON)
                            report_status("watcher", "OK", stage="build_avisos_full")
                        except Exception:
                            print("[main] erro build_avisos (fallback):", traceback.format_exc())
                else:
                    print("[main] não foi possível identificar registro — recalculando tudo")
                    try:
                        analises_mod.build_analises(dadosend_path, ANALISES_JSON)
                        report_status("watcher", "OK", stage="build_analises_full")
                    except Exception:
                        print("[main] erro build_analises:", traceback.format_exc())
                    try:
                        avisos_mod.build_avisos(ANALISES_JSON, AVISOS_JSON)
                        report_status("watcher", "OK", stage="build_avisos_full")
                    except Exception:
                        print("[main] erro build_avisos:", traceback.format_exc())

            if encomendas_changed and not dados_changed:
                report_status("watcher", "STARTED", stage="encomendas_changed")
                print("[main] Alteração detectada em encomendasend.json — recalculando análises/avisos...")
                try:
                    analises_mod.build_analises(dadosend_path, ANALISES_JSON)
                    report_status("watcher", "OK", stage="build_analises_full")
                except Exception:
                    report_status("watcher", "ERROR", stage="build_analises_full", details={"error": traceback.format_exc()})
                    print("[main] erro build_analises (encomendas):", traceback.format_exc())
                try:
                    avisos_mod.build_avisos(ANALISES_JSON, AVISOS_JSON)
                    report_status("watcher", "OK", stage="build_avisos_full")
                except Exception:
                    report_status("watcher", "ERROR", stage="build_avisos_full", details={"error": traceback.format_exc()})
                    print("[main] erro build_avisos (encomendas):", traceback.format_exc())
        except Exception:
            print("[main] watcher erro:", traceback.format_exc())
        time.sleep(poll)

def initialize_system(start_watcher=True):
    """Inicializa infraestrutura e builds iniciais. Retorna thread watcher (ou None)."""
    # 1) garante arquivos de infraestrutura
    ensure_file(ANALISES_JSON, _ANALISES_TEMPLATE)
    ensure_file(AVISOS_JSON, _AVISOS_TEMPLATE)
    if not os.path.exists(DADOSEND):
        # cria dadosend.json vazio por segurança
        try:
            with open(DADOSEND, "w", encoding="utf-8") as f:
                json.dump({"registros": []}, f, ensure_ascii=False, indent=2)
            print("[main] Criado dadosend.json vazio.")
        except Exception:
            print("[main] Falha ao criar dadosend.json:", traceback.format_exc())

    # 2) importa módulos analises/avisos (assume que analises.py e avisos.py existem no mesmo dir)
    try:
        import analises
        import avisos
    except Exception as e:
        print("[main] Falha ao importar analises/avisos:", e)
        raise

    # 3) inicializa análises/avisos completos no startup (garantia)
    try:
        print("[main] Executando build_analises() inicial...")
        analises.build_analises(DADOSEND, ANALISES_JSON)
    except Exception:
        print("[main] build_analises falhou:", traceback.format_exc())
    try:
        print("[main] Executando build_avisos() inicial...")
        avisos.build_avisos(ANALISES_JSON, AVISOS_JSON)
    except Exception:
        print("[main] build_avisos falhou:", traceback.format_exc())

    # 4) start watcher (opcional)
    watcher = None
    if start_watcher:
        watcher = threading.Thread(target=watcher_thread, args=(DADOSEND, analises, avisos, POLL_INTERVAL), daemon=True)
        watcher.start()

    return watcher


def main():
    initialize_system(start_watcher=True)

    # 5) inicia interface grafica (bloqueante)
    try:
        import interfaceone
        print("[main] Inicializando interface grafica (interfaceone)...")
        interfaceone.iniciar_interface_principal()
    except Exception:
        print("[main] Falha ao iniciar interfaceone:", traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
