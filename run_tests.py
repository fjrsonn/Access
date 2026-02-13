#!/usr/bin/env python3
"""Executor único de testes do projeto Access."""
from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> int:
    print(f"\n>>> {' '.join(cmd)}")
    p = subprocess.run(cmd)
    return p.returncode


def main() -> int:
    steps = [
        ["python", "-m", "py_compile", "interfaceone.py", "interfacetwo.py", "text_classifier.py", "tests_text_classifier.py"],
        ["python", "-m", "unittest", "tests_text_classifier.py"],
        ["python", "smoke_test.py"],
    ]

    for step in steps:
        code = run(step)
        if code != 0:
            print(f"\n[run_tests] Falhou: {' '.join(step)} (exit={code})")
            return code

    print("\n[run_tests] Todos os testes passaram ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
