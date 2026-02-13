#!/usr/bin/env python3
"""Compatibilidade: encaminha para o executor oficial run_tests.py.

Alguns ambientes/chamadas antigas usam o nome `run_yesys.py`.
Este arquivo mantém retrocompatibilidade e evita erro de caminho inexistente.
"""

from run_tests import main


if __name__ == "__main__":
    raise SystemExit(main())
