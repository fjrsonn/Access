#!/usr/bin/env python3
"""Compat wrapper.

Mantém compatibilidade para ambientes que ainda executam `tests_unificados.py`.
A suíte oficial está em `test_unificados.py`.
"""

import unittest
from test_unificados import *  # noqa: F401,F403 - compatibilidade com unittest


if __name__ == "__main__":
    unittest.main(module="test_unificados", verbosity=2)
