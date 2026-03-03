# Quality Gates (QA/DevEx)

Este projeto possui quatro gates principais:

1. **Coverage gate por módulo crítico**
   - Comando: `python tools/coverage_gate.py`
   - Relatório: `artifacts/coverage_gate.json`
   - Thresholds iniciais:
     - `ia.py >= 18%`
     - `interfaceone.py >= 10%`
     - `main.py >= 35%`

2. **Mutation testing (smoke)**
   - Comando: `python tools/mutation_smoke.py`
   - Relatório: `artifacts/mutation_smoke.json`
   - Objetivo: detectar falso positivo com mutantes de alto risco em módulos críticos.

3. **Regressão por dataset versionado**
   - Dataset: `tests/regression/data/v1/cases.json`
   - Baseline: `tests/regression/baseline/v1/summary.json`
   - Check: `python tests/regression/run_regression.py --check`
   - Update baseline: `python tests/regression/run_regression.py --update-baseline --reason "<motivo>"`
   - Governança: registrar alteração no `tests/regression/BASELINE_CHANGELOG.md`.

4. **Smoke UI headless (sem Tk real)**
   - Teste: `tests/test_ui_smoke.py`
   - Executado no `unittest discover`.

## Execução unificada

```bash
python tools/run_quality_gates.py
```

## Riscos remanescentes

- O mutation gate atual é *smoke* e não substitui mutação exaustiva.
- Coverage usa `trace` da stdlib (estimativa por linhas candidatas); útil como gate incremental, mas menos preciso que `coverage.py`.
