from preprocessor import detectar_status

TESTES = {
    "VIS JOAO BLOCO 4": "VISITANTE",
    "JOAO BLOCO 4 AP 12": "VISITANTE",
    "M JOAO AP 10": "MORADOR",
    "PREST MARIA SERV LIMPEZA": "PRESTADOR DE SERVIÇO",
    "JOAO OLIVEIRA": "VISITANTE"
}


def executar():
    for texto, esperado in TESTES.items():
        status, _ = detectar_status(texto)
        assert status == esperado, f"ERRO: {texto} -> {status}"

    print("✅ TODOS OS TESTES PASSARAM")


if __name__ == "__main__":
    executar()
