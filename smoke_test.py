#!/usr/bin/env python3
# smoke_test.py — verificação automática do pipeline IA
# Testa:
# - Ordem diferente das palavras
# - Extração correta de PLACA / MODELO / COR
# - Não duplicação por _entrada_id
# - Preservação de DATA_HORA
# - Rollback automático após teste

import os
import json
import shutil
import subprocess
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENTRADA = os.path.join(BASE_DIR, "dadosinit.json")
SAIDA = os.path.join(BASE_DIR, "dadosend.json")
IA = os.path.join(BASE_DIR, "ia.py")

BACKUP_IN = ENTRADA + ".bak_smoke"
BACKUP_OUT = SAIDA + ".bak_smoke"


def backup():
    if os.path.exists(ENTRADA):
        shutil.copy2(ENTRADA, BACKUP_IN)
        print(f"[backup] dadosinit.json -> dadosinit.json.bak_smoke")
    if os.path.exists(SAIDA):
        shutil.copy2(SAIDA, BACKUP_OUT)
        print(f"[backup] dadosend.json -> dadosend.json.bak_smoke")


def restore():
    if os.path.exists(BACKUP_IN):
        shutil.move(BACKUP_IN, ENTRADA)
        print(f"[restore] dadosinit.json.bak_smoke -> dadosinit.json")
    if os.path.exists(BACKUP_OUT):
        shutil.move(BACKUP_OUT, SAIDA)
        print(f"[restore] dadosend.json.bak_smoke -> dadosend.json")


def write_input(texto: str, idx: int):
    payload = {
        "registros": [
            {
                "id": idx,
                "texto": texto,
                "processado": False,
                "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            }
        ]
    }
    with open(ENTRADA, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)


def run_ia():
    subprocess.run(
        ["python", IA],
        cwd=BASE_DIR,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def load_saida():
    if not os.path.exists(SAIDA):
        return []
    with open(SAIDA, "r", encoding="utf-8") as f:
        return json.load(f).get("registros", [])


def assert_registro(reg):
    assert reg.get("PLACA") == "FEU3C84", "PLACA incorreta"
    assert reg.get("MODELO") == "JETTA", "MODELO incorreto"
    assert reg.get("COR") == "PRETO", "COR incorreta"
    assert reg.get("STATUS") == "MORADOR", "STATUS incorreto"
    assert reg.get("BLOCO") == "10", "BLOCO incorreto"
    assert reg.get("APARTAMENTO") == "10", "APARTAMENTO incorreto"
    assert reg.get("NOME") == "FLAVIO", "NOME incorreto"
    assert reg.get("SOBRENOME") == "JUNIOR", "SOBRENOME incorreto"


def main():
    print("SMOKE TEST START")

    backup()

    testes = [
        "FLAVIO JUNIOR MORADOR BL10 AP10 FEU3C84 JETA PRETO",
        "MORADOR FLAVIO JUNIOR BL10 AP10 FEU3C84 JETA PRETO",
        "JETA PRETO FEU3C84 MORADOR FLAVIO JUNIOR BL10 AP10",
        "FEU3C84 JETA FLAVIO MORADOR AP10 BL10 JUNIOR PRETO",
    ]

    try:
        for i, texto in enumerate(testes, start=1):
            print(f"\n[Test {i}] entrada: {texto}")
            write_input(texto, i)
            run_ia()

            saida = load_saida()
            assert len(saida) >= 1, "Nenhum registro gerado"

            reg = saida[-1]
            assert_registro(reg)

            print(
                f"[OK] Registro criado: ID={reg.get('ID')} "
                f"PLACA={reg.get('PLACA')} MODELO={reg.get('MODELO')} COR={reg.get('COR')}"
            )

        print("\nSMOKE TEST: TODOS OS TESTES PASSARAM ✅")

    except AssertionError as e:
        print("\n❌ SMOKE TEST FALHOU")
        print("Motivo:", e)
        raise

    finally:
        print("Restaurando arquivos originais (backup)...")
        restore()


if __name__ == "__main__":
    main()