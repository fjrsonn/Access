#!/usr/bin/env python3
"""Painel de testes e diagnóstico do sistema."""
import io
import threading
import traceback
import unittest
from datetime import datetime

import tkinter as tk
from tkinter import ttk

import main as app_main


class TestPanelApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Painel de Testes - Access")
        self.root.geometry("1000x700")

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")

        self.btn_run = ttk.Button(top, text="Iniciar sistema + Rodar testes", command=self.start)
        self.btn_run.pack(side="left")

        self.lbl_status = ttk.Label(top, text="Pronto")
        self.lbl_status.pack(side="left", padx=12)

        self.progress = ttk.Progressbar(top, mode="indeterminate", length=200)
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

    def start(self):
        self.btn_run.config(state="disabled")
        self.progress.start(8)
        self.lbl_status.config(text="Executando...")
        t = threading.Thread(target=self._run_all, daemon=True)
        t.start()

    def _run_all(self):
        try:
            self.root.after(0, self.log, "Inicializando sistema principal (sem UI de produção)...")
            app_main.initialize_system(start_watcher=True)
            self.root.after(0, self.log, "Sistema inicializado. Iniciando suite de testes.")

            suite = unittest.defaultTestLoader.discover("tests")
            stream = io.StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=2)
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


def main():
    root = tk.Tk()
    app = TestPanelApp(root)
    app.log("Painel pronto. Clique para iniciar o sistema e rodar os testes.")
    root.mainloop()


if __name__ == "__main__":
    main()
