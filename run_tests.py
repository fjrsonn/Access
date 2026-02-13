#!/usr/bin/env python3
"""Executor único de testes do projeto Access.

- Executa a suíte unificada tests_unificados.py.
- Em caso de falha, grava log detalhado e tenta abrir painel (Tkinter).
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
TEST_LOG = os.path.join(LOG_DIR, "test_errors.log")


def _write_error_log(output: str) -> str:
    os.makedirs(LOG_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    with open(TEST_LOG, "w", encoding="utf-8") as f:
        f.write(f"[TEST FAILURE] {stamp}\n\n")
        f.write(output)
    return TEST_LOG


def _try_open_log_panel(log_path: str) -> None:
    try:
        import tkinter as tk
        from tkinter.scrolledtext import ScrolledText

        root = tk.Tk()
        root.title("Painel de Log de Erros de Teste")
        root.geometry("1100x700")

        txt = ScrolledText(root, wrap="word", font=("Consolas", 10))
        txt.pack(fill="both", expand=True)
        with open(log_path, "r", encoding="utf-8") as f:
            txt.insert("1.0", f.read())
        txt.configure(state="disabled")
        root.mainloop()
    except Exception as exc:
        print(f"[run_tests] Painel gráfico indisponível ({exc}). Log salvo em: {log_path}")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print(f"\n>>> {' '.join(cmd)}")
    return subprocess.run(cmd, text=True, capture_output=True)


def main() -> int:
    steps = [
        ["python", "-m", "py_compile", "preprocessor.py", "ia.py", "chat.py", "text_classifier.py", "main.py", "tests_unificados.py"],
        ["python", "-m", "unittest", "-v", "tests_unificados.py"],
    ]

    for step in steps:
        result = run(step)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        if result.returncode != 0:
            joined = f"$ {' '.join(step)}\n\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n"
            log_path = _write_error_log(joined)
            _try_open_log_panel(log_path)
            print(f"\n[run_tests] Falhou: {' '.join(step)} (exit={result.returncode})")
            return result.returncode

    print("\n[run_tests] Todos os testes passaram ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
