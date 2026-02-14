#!/usr/bin/env python3
"""Painel de testes, diagnóstico e simulador de carga de registros."""
import io
import json
import re
import threading
import time
import traceback
import unittest
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, ttk

import main as app_main
import runtime_status




def _norm_text_for_compare(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().upper())


def _is_valid_encomenda_name_token(v: str) -> bool:
    up = _norm_text_for_compare(v)
    if not up or up in {"-", ""}:
        return False
    if re.match(r"^(BL|BLO|BLOCO|BLCO|BLC|B)\d+$", up):
        return False
    if re.match(r"^(AP|APT|APART|APTA|APARTAMEN|APARTAMENTO|A)\d+[A-Z]?$", up):
        return False
    if re.match(r"^(?=.*\d)[A-Z0-9]{10,}$", up):
        return False
    return bool(re.match(r"^[A-ZÀ-ÖØ-Ý][A-ZÀ-ÖØ-Ý\s\-]{1,}$", up))


def validate_encomenda_pipeline_record(raw_text: str, init_rec: dict | None, end_rec: dict | None) -> tuple[str, list[str]]:
    """Valida se uma linha de encomenda percorreu corretamente init -> end.

    Retorna (status, problemas):
    - OK: registro processado e campos coerentes
    - FALHOU: registro processado mas com dados inconsistentes
    - GARGALO: registro não chegou ao fim do pipeline
    """
    issues: list[str] = []
    if not init_rec:
        return "GARGALO", ["ausente_em_encomendasinit"]
    if not init_rec.get("processado"):
        return "GARGALO", ["registro_nao_processado_em_encomendasinit"]
    if not end_rec:
        return "GARGALO", ["ausente_em_encomendasend"]

    expected_text = _norm_text_for_compare(raw_text)
    init_text = _norm_text_for_compare(init_rec.get("texto") or init_rec.get("texto_original") or "")
    if init_text and expected_text and init_text != expected_text:
        issues.append("texto_init_divergente")

    required = ("NOME", "SOBRENOME", "BLOCO", "APARTAMENTO", "TIPO", "LOJA", "IDENTIFICACAO", "DATA_HORA", "ID", "_entrada_id")
    for k in required:
        v = end_rec.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            issues.append(f"campo_obrigatorio_ausente:{k}")

    if str(end_rec.get("_entrada_id", "")).strip() != str(init_rec.get("id", "")).strip():
        issues.append("entrada_id_divergente")

    if str(end_rec.get("BLOCO", "")).strip() in {"", "-"}:
        issues.append("bloco_invalido")
    if str(end_rec.get("APARTAMENTO", "")).strip() in {"", "-"}:
        issues.append("apartamento_invalido")

    if not _is_valid_encomenda_name_token(end_rec.get("NOME", "")):
        issues.append("nome_invalido")
    if not _is_valid_encomenda_name_token(end_rec.get("SOBRENOME", "")):
        issues.append("sobrenome_invalido")

    if str(end_rec.get("TIPO", "")).strip() in {"", "-"}:
        issues.append("tipo_invalido")
    if str(end_rec.get("LOJA", "")).strip() in {"", "-"}:
        issues.append("loja_invalida")

    ident = _norm_text_for_compare(end_rec.get("IDENTIFICACAO", ""))
    if ident in {"", "-"}:
        issues.append("identificacao_invalida")
    elif not re.match(r"^(?=.*\d)[A-Z0-9]{6,}$", ident):
        issues.append("identificacao_formato_invalido")

    return ("OK", []) if not issues else ("FALHOU", issues)


def generate_encomenda_simulation_report(records_report: list[dict], report_path: Path) -> dict:
    summary = {"OK": 0, "FALHOU": 0, "GARGALO": 0}
    for item in records_report:
        status = item.get("status", "FALHOU")
        summary[status] = summary.get(status, 0) + 1

    payload = {
        "resumo": summary,
        "total": len(records_report),
        "registros": records_report,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


class _SimulatedEntry:
    def __init__(self, text: str):
        self._text = text
        self.deleted = False

    def get(self):
        return self._text

    def delete(self, *_args, **_kwargs):
        self.deleted = True
        self._text = ""

    def after(self, _ms, fn):
        fn()


class TestPanelApp:
    def __init__(self, root: tk.Tk, status_store: runtime_status.RuntimeStatusStore | None = None, test_loader=None, test_runner_factory=None, thread_factory=None):
        self.root = root
        self.root.title("Painel de Testes - Access")
        self.root.geometry("1100x760")

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")

        self.btn_run = ttk.Button(top, text="Iniciar sistema + Rodar testes", command=self.start)
        self.btn_run.pack(side="left")

        self.btn_sim = ttk.Button(top, text="Simulador", command=self.start_simulator)
        self.btn_sim.pack(side="left", padx=8)

        self.btn_pause = ttk.Button(top, text="Pausar", command=self.pause_simulator, state="disabled")
        self.btn_pause.pack(side="left", padx=4)

        self.btn_resume = ttk.Button(top, text="Retomar", command=self.resume_simulator, state="disabled")
        self.btn_resume.pack(side="left", padx=4)

        ttk.Label(top, text="TPM:").pack(side="left", padx=(8, 2))
        self.entry_tpm = ttk.Entry(top, width=6)
        self.entry_tpm.insert(0, "30")
        self.entry_tpm.pack(side="left")

        ttk.Label(top, text="Limite (opcional):").pack(side="left", padx=(8, 2))
        self.entry_limit = ttk.Entry(top, width=8)
        self.entry_limit.pack(side="left")

        ttk.Label(top, text="TXT simulador:").pack(side="left", padx=(8, 2))
        self.entry_txt_file = ttk.Entry(top, width=34)
        self.entry_txt_file.insert(0, str((Path(__file__).resolve().parent / "combinacoes.txt").name))
        self.entry_txt_file.pack(side="left")
        self.btn_txt_file = ttk.Button(top, text="Escolher TXT", command=self.select_txt_file)
        self.btn_txt_file.pack(side="left", padx=(4, 0))

        self.lbl_status = ttk.Label(top, text="Pronto")
        self.lbl_status.pack(side="left", padx=12)

        self.progress = ttk.Progressbar(top, mode="indeterminate", length=220)
        self.progress.pack(side="right")

        stats = ttk.Frame(root, padding=(8, 0, 8, 8))
        stats.pack(fill="x")

        self.lbl_total = ttk.Label(stats, text="Total: 0")
        self.lbl_ok = ttk.Label(stats, text="Sucesso: 0")
        self.lbl_fail = ttk.Label(stats, text="Falhas: 0")
        self.lbl_err = ttk.Label(stats, text="Erros: 0")

        for w in (self.lbl_total, self.lbl_ok, self.lbl_fail, self.lbl_err):
            w.pack(side="left", padx=10)

        sim_stats = ttk.Frame(root, padding=(8, 0, 8, 8))
        sim_stats.pack(fill="x")
        self.lbl_sim_progress = ttk.Label(sim_stats, text="Simulador: parado")
        self.lbl_sim_progress.pack(side="left", padx=10)
        self.lbl_sim_ok = ttk.Label(sim_stats, text="OK: 0")
        self.lbl_sim_ok.pack(side="left", padx=10)
        self.lbl_sim_fail = ttk.Label(sim_stats, text="FALHOU: 0")
        self.lbl_sim_fail.pack(side="left", padx=10)
        self.lbl_sim_bottleneck = ttk.Label(sim_stats, text="GARGALO: 0")
        self.lbl_sim_bottleneck.pack(side="left", padx=10)

        self.text = tk.Text(root, wrap="word")
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        self.text.configure(state="disabled")
        self._last_status_fingerprint = ""
        self._status_store = status_store or runtime_status.RuntimeStatusStore(
            events_file=runtime_status.EVENTS_FILE,
            last_status_file=runtime_status.LAST_STATUS_FILE,
        )
        self._test_loader = test_loader or unittest.defaultTestLoader
        self._test_runner_factory = test_runner_factory or (lambda stream: unittest.TextTestRunner(stream=stream, verbosity=2))
        self._thread_factory = thread_factory or (lambda target: threading.Thread(target=target, daemon=True))
        self._sim_pause_requested = False
        self._sim_running = False
        self._sim_index = 0
        self._sim_total = 0
        self._sim_ok_count = 0
        self._sim_fail_count = 0
        self._sim_bottleneck_count = 0
        self._sim_current_record = ""

    def log(self, msg: str):
        self.text.configure(state="normal")
        self.text.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.text.see("end")
        self.text.configure(state="disabled")

    def _set_stats(self, result: unittest.TestResult):
        total = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        ok = total - failures - errors

        self.lbl_total.config(text=f"Total: {total}")
        self.lbl_ok.config(text=f"Sucesso: {ok}")
        self.lbl_fail.config(text=f"Falhas: {failures}")
        self.lbl_err.config(text=f"Erros: {errors}")

    def _poll_runtime_status(self):
        try:
            st = self._status_store.get_last_status()
            if isinstance(st, dict) and st:
                fp = f"{st.get('timestamp')}|{st.get('action')}|{st.get('status')}|{st.get('stage')}"
                if fp != self._last_status_fingerprint:
                    self._last_status_fingerprint = fp
                    self.log(f"[RUNTIME] {st.get('action')} -> {st.get('status')} ({st.get('stage')}) {st.get('details', {})}")
        except Exception:
            pass
        self.root.after(1000, self._poll_runtime_status)

    def _parse_tpm(self) -> float:
        raw = (self.entry_tpm.get() or "").strip()
        try:
            val = float(raw)
            return val if val > 0 else 30.0
        except Exception:
            return 30.0

    def _parse_limit(self) -> int | None:
        raw = (self.entry_limit.get() or "").strip()
        if not raw:
            return None
        try:
            val = int(raw)
            return val if val > 0 else None
        except Exception:
            return None

    @staticmethod
    def _load_records(path: Path, limit: int | None = None) -> list[str]:
        lines = []
        for ln in path.read_text(encoding="utf-8").splitlines():
            item = (ln or "").strip()
            if item:
                lines.append(item)
        if limit is not None:
            lines = lines[:limit]
        return lines

    def _resolve_simulator_file(self) -> Path:
        raw = (self.entry_txt_file.get() or "").strip()
        base_dir = Path(__file__).resolve().parent
        if not raw:
            return base_dir / "combinacoes.txt"
        p = Path(raw)
        if not p.is_absolute():
            p = base_dir / p
        return p

    def select_txt_file(self):
        initial_dir = str(Path(__file__).resolve().parent)
        selected = filedialog.askopenfilename(
            title="Selecionar arquivo TXT para simulação",
            initialdir=initial_dir,
            filetypes=(("Arquivos TXT", "*.txt"), ("Todos os arquivos", "*.*")),
        )
        if selected:
            self.entry_txt_file.delete(0, tk.END)
            self.entry_txt_file.insert(0, selected)
            self.log(f"Arquivo de simulação selecionado: {selected}")


    def _set_sim_stats(self):
        processed = self._sim_ok_count + self._sim_fail_count
        remaining = max(0, self._sim_total - processed)
        pos = self._sim_index if self._sim_index else 0
        txt = f"Simulador: processados={processed}/{self._sim_total} | faltam={remaining} | último_idx={pos}"
        if self._sim_current_record:
            txt += f" | atual='{self._sim_current_record[:60]}'"
        self.lbl_sim_progress.config(text=txt)
        self.lbl_sim_ok.config(text=f"OK: {self._sim_ok_count}")
        self.lbl_sim_fail.config(text=f"FALHOU: {self._sim_fail_count}")
        self.lbl_sim_bottleneck.config(text=f"GARGALO: {self._sim_bottleneck_count}")

    def pause_simulator(self):
        if not self._sim_running:
            return
        self._sim_pause_requested = True
        self.btn_pause.config(state="disabled")
        self.btn_resume.config(state="normal")
        self.lbl_status.config(text=f"Simulador pausado no registro #{self._sim_index}")
        self.log(f"[SIM] PAUSADO no registro #{self._sim_index}/{self._sim_total}: {self._sim_current_record}")

    def resume_simulator(self):
        if not self._sim_running:
            return
        self._sim_pause_requested = False
        self.btn_pause.config(state="normal")
        self.btn_resume.config(state="disabled")
        self.lbl_status.config(text=f"Simulador retomado do registro #{self._sim_index}")
        self.log(f"[SIM] RETOMADO do registro #{self._sim_index}/{self._sim_total}")

    def start(self):
        self.btn_run.config(state="disabled")
        self.btn_sim.config(state="disabled")
        self.btn_pause.config(state="disabled")
        self.btn_resume.config(state="disabled")
        self.progress.start(8)
        self.lbl_status.config(text="Executando testes...")
        t = self._thread_factory(self._run_all)
        t.start()

    def start_simulator(self):
        self.btn_run.config(state="disabled")
        self.btn_sim.config(state="disabled")
        self.btn_pause.config(state="normal")
        self.btn_resume.config(state="disabled")
        self.progress.start(8)
        self.lbl_status.config(text="Executando simulador...")
        self._sim_pause_requested = False
        self._sim_running = True
        self._sim_index = 0
        self._sim_total = 0
        self._sim_ok_count = 0
        self._sim_fail_count = 0
        self._sim_bottleneck_count = 0
        self._sim_current_record = ""
        self._set_sim_stats()
        t = self._thread_factory(self._run_simulator)
        t.start()

    def _run_all(self):
        try:
            self.root.after(0, self.log, "Inicializando sistema principal (sem UI de produção)...")
            app_main.initialize_system(start_watcher=True)
            self.root.after(0, self.log, "Sistema inicializado. Iniciando suite de testes.")

            suite = self._test_loader.discover("tests")
            stream = io.StringIO()
            runner = self._test_runner_factory(stream)
            result = runner.run(suite)

            self.root.after(0, self._set_stats, result)
            self.root.after(0, self.log, "===== RESULTADO DA EXECUÇÃO =====")
            for line in stream.getvalue().splitlines():
                self.root.after(0, self.log, line)

            if result.failures:
                self.root.after(0, self.log, "----- Falhas detalhadas -----")
                for test, tb in result.failures:
                    self.root.after(0, self.log, f"FALHA: {test.id()}")
                    self.root.after(0, self.log, tb)

            if result.errors:
                self.root.after(0, self.log, "----- Erros detalhados -----")
                for test, tb in result.errors:
                    self.root.after(0, self.log, f"ERRO: {test.id()}")
                    self.root.after(0, self.log, tb)

            if result.wasSuccessful():
                self.root.after(0, lambda: self.lbl_status.config(text="Concluído com sucesso"))
            else:
                self.root.after(0, lambda: self.lbl_status.config(text="Concluído com falhas/erros"))
        except Exception:
            self.root.after(0, self.log, "Erro crítico no painel de testes:")
            self.root.after(0, self.log, traceback.format_exc())
            self.root.after(0, lambda: self.lbl_status.config(text="Erro crítico"))
        finally:
            self._sim_running = False
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.btn_sim.config(state="normal"))
            self.root.after(0, lambda: self.btn_pause.config(state="disabled"))
            self.root.after(0, lambda: self.btn_resume.config(state="disabled"))
            self.root.after(0, self._set_sim_stats)

    def _run_simulator(self):
        try:
            from interfaceone import save_text
            import interfaceone
            import ia

            tpm = self._parse_tpm()
            limit = self._parse_limit()
            interval_s = 60.0 / tpm
            combo_file = self._resolve_simulator_file()
            if not combo_file.exists():
                raise FileNotFoundError(f"Arquivo de simulação não encontrado: {combo_file}")
            regs = self._load_records(combo_file, limit=limit)
            total = len(regs)

            self.root.after(0, self.log, f"Simulador iniciado: {total} registros | TPM={tpm:.2f} | intervalo={interval_s:.2f}s")

            ok = 0
            fail = 0
            bottleneck = 0
            detailed_results: list[dict] = []
            encomendas_mode = combo_file.name.lower() == "encomendas.txt"
            self._sim_total = total
            self.root.after(0, self._set_sim_stats)

            original_has_ia = getattr(interfaceone, "HAS_IA_MODULE", False)
            interfaceone.HAS_IA_MODULE = False
            try:
                for idx, rec in enumerate(regs, start=1):
                    self._sim_index = idx
                    self._sim_current_record = rec
                    while self._sim_pause_requested:
                        time.sleep(0.1)
                    started = time.perf_counter()
                    try:
                        entry = _SimulatedEntry(rec)
                        save_text(entry_widget=entry, btn=None)
                        ia.processar()
                        if not entry.deleted:
                            raise RuntimeError("entrada não foi consumida pela barra digitadora")

                        elapsed = time.perf_counter() - started
                        if encomendas_mode:
                            init_data = interfaceone._read_json(interfaceone.ENCOMENDAS_IN_FILE)
                            end_data = interfaceone._read_json(interfaceone.ENCOMENDAS_DB_FILE)
                            init_regs = (init_data or {}).get("registros", []) if isinstance(init_data, dict) else []
                            end_regs = (end_data or {}).get("registros", []) if isinstance(end_data, dict) else []

                            init_candidates = [r for r in init_regs if _norm_text_for_compare(r.get("texto") or "") == _norm_text_for_compare(rec)]
                            init_rec = init_candidates[-1] if init_candidates else None
                            end_rec = None
                            if init_rec is not None:
                                eid = init_rec.get("id")
                                for er in end_regs:
                                    if str(er.get("_entrada_id", "")).strip() == str(eid).strip():
                                        end_rec = er
                                        break

                            status, issues = validate_encomenda_pipeline_record(rec, init_rec, end_rec)
                            detailed_results.append({
                                "indice": idx,
                                "texto": rec,
                                "status": status,
                                "problemas": issues,
                                "entrada_id": init_rec.get("id") if isinstance(init_rec, dict) else None,
                            })
                            if status == "OK":
                                ok += 1
                                self._sim_ok_count = ok
                                self.root.after(0, self.log, f"[OK] #{idx}/{total} | {rec}")
                            elif status == "GARGALO":
                                bottleneck += 1
                                self._sim_bottleneck_count = bottleneck
                                self.root.after(0, self.log, f"[GARGALO] #{idx}/{total} | {rec} | problemas={issues}")
                            else:
                                fail += 1
                                self._sim_fail_count = fail
                                self.root.after(0, self.log, f"[FALHOU] #{idx}/{total} | {rec} | problemas={issues}")
                        else:
                            if elapsed > (interval_s * 1.5):
                                bottleneck += 1
                                self._sim_bottleneck_count = bottleneck
                                self.root.after(0, self.log, f"[GARGALO] #{idx}/{total} {elapsed:.2f}s | {rec}")
                            else:
                                self.root.after(0, self.log, f"[OK] #{idx}/{total} | {rec}")
                            ok += 1
                            self._sim_ok_count = ok
                    except Exception as e:
                        fail += 1
                        self._sim_fail_count = fail
                        self.root.after(0, self.log, f"[ERRO] #{idx}/{total} | {rec} | erro={e}")

                    self.root.after(0, self._set_sim_stats)
                    remaining = interval_s - (time.perf_counter() - started)
                    if remaining > 0:
                        time.sleep(remaining)
            finally:
                interfaceone.HAS_IA_MODULE = original_has_ia

            if encomendas_mode:
                report_file = Path(__file__).resolve().parent / "logs" / "encomendas_simulation_report.json"
                payload = generate_encomenda_simulation_report(detailed_results, report_file)
                self.root.after(0, self.log, f"Relatório encomendas salvo em: {report_file}")
                self.root.after(0, self.log, f"Resumo encomendas: {payload.get('resumo', {})}")

            self.root.after(0, self.log, f"Simulador finalizado. OK={ok} | FALHOU={fail} | GARGALO={bottleneck}")
            status_text = "Simulador concluído com sucesso" if fail == 0 and bottleneck == 0 else "Simulador concluído com falhas/gargalos"
            self.root.after(0, lambda: self.lbl_status.config(text=status_text))
        except Exception:
            self.root.after(0, self.log, "Erro crítico no simulador:")
            self.root.after(0, self.log, traceback.format_exc())
            self.root.after(0, lambda: self.lbl_status.config(text="Erro crítico no simulador"))
        finally:
            self._sim_running = False
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.btn_sim.config(state="normal"))
            self.root.after(0, lambda: self.btn_pause.config(state="disabled"))
            self.root.after(0, lambda: self.btn_resume.config(state="disabled"))
            self.root.after(0, self._set_sim_stats)


def main():
    root = tk.Tk()
    app = TestPanelApp(root)
    app.log("Painel pronto. Clique para iniciar o sistema e rodar os testes.")
    app._poll_runtime_status()
    root.mainloop()


if __name__ == "__main__":
    main()
