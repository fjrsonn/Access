#!/usr/bin/env python3
"""Painel de testes, diagnóstico e simulador de carga de registros."""
import io
import threading
import time
import traceback
import unittest
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import ttk

import main as app_main
import runtime_status


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

        ttk.Label(top, text="TPM:").pack(side="left", padx=(8, 2))
        self.entry_tpm = ttk.Entry(top, width=6)
        self.entry_tpm.insert(0, "30")
        self.entry_tpm.pack(side="left")

        ttk.Label(top, text="Limite (opcional):").pack(side="left", padx=(8, 2))
        self.entry_limit = ttk.Entry(top, width=8)
        self.entry_limit.pack(side="left")

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

    def start(self):
        self.btn_run.config(state="disabled")
        self.btn_sim.config(state="disabled")
        self.progress.start(8)
        self.lbl_status.config(text="Executando testes...")
        t = self._thread_factory(self._run_all)
        t.start()

    def start_simulator(self):
        self.btn_run.config(state="disabled")
        self.btn_sim.config(state="disabled")
        self.progress.start(8)
        self.lbl_status.config(text="Executando simulador...")
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
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.btn_sim.config(state="normal"))

    def _run_simulator(self):
        try:
            from interfaceone import save_text
            import interfaceone
            import ia

            tpm = self._parse_tpm()
            limit = self._parse_limit()
            interval_s = 60.0 / tpm
            combo_file = Path(__file__).resolve().parent / "combinacoes.txt"
            regs = self._load_records(combo_file, limit=limit)
            total = len(regs)

            self.root.after(0, self.log, f"Simulador iniciado: {total} registros | TPM={tpm:.2f} | intervalo={interval_s:.2f}s")

            ok = 0
            fail = 0
            bottleneck = 0

            original_has_ia = getattr(interfaceone, "HAS_IA_MODULE", False)
            interfaceone.HAS_IA_MODULE = False
            try:
                for idx, rec in enumerate(regs, start=1):
                    started = time.perf_counter()
                    try:
                        entry = _SimulatedEntry(rec)
                        save_text(entry_widget=entry, btn=None)
                        ia.processar()
                        if not entry.deleted:
                            raise RuntimeError("entrada não foi consumida pela barra digitadora")
                        elapsed = time.perf_counter() - started
                        if elapsed > (interval_s * 1.5):
                            bottleneck += 1
                            self.root.after(0, self.log, f"[GARGALO] #{idx}/{total} {elapsed:.2f}s | {rec}")
                        else:
                            self.root.after(0, self.log, f"[OK] #{idx}/{total} | {rec}")
                        ok += 1
                    except Exception as e:
                        fail += 1
                        self.root.after(0, self.log, f"[ERRO] #{idx}/{total} | {rec} | erro={e}")

                    remaining = interval_s - (time.perf_counter() - started)
                    if remaining > 0:
                        time.sleep(remaining)
            finally:
                interfaceone.HAS_IA_MODULE = original_has_ia

            self.root.after(0, self.log, f"Simulador finalizado. OK={ok} | ERRO={fail} | GARGALO={bottleneck}")
            status_text = "Simulador concluído com sucesso" if fail == 0 else "Simulador concluído com erros"
            self.root.after(0, lambda: self.lbl_status.config(text=status_text))
        except Exception:
            self.root.after(0, self.log, "Erro crítico no simulador:")
            self.root.after(0, self.log, traceback.format_exc())
            self.root.after(0, lambda: self.lbl_status.config(text="Erro crítico no simulador"))
        finally:
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.btn_run.config(state="normal"))
            self.root.after(0, lambda: self.btn_sim.config(state="normal"))


def main():
    root = tk.Tk()
    app = TestPanelApp(root)
    app.log("Painel pronto. Clique para iniciar o sistema e rodar os testes.")
    app._poll_runtime_status()
    root.mainloop()


if __name__ == "__main__":
    main()
