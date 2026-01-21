from groq import Groq
import json
import re
import os
from dotenv import load_dotenv
from preprocessor import (
    extrair_status,
    separar_modelos,
    extrair_endereco,
    extrair_cor,
    corrigir_nome,
    remover_status
)

# =========================
# Carregar variáveis do .env
# =========================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("Variável de ambiente GROQ_API_KEY não encontrada!")

client = Groq(api_key=GROQ_API_KEY)

# =========================
# Arquivos
# =========================
ENTRADA = "dadosinit.json"
SAIDA = "dadosend.json"
PROMPT_PATH = "prompts/v4_producao_portaria.txt"

# =========================
# Funções utilitárias
# =========================
def carregar(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"registros": []}

def salvar(path, dados):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

def carregar_prompt():
    with open(PROMPT_PATH, "r", encoding="utf-8") as f:
        return f.read()

# =========================
# Função principal
# =========================
def processar():
    entrada = carregar(ENTRADA)
    saida = carregar(SAIDA)
    prompt_base = carregar_prompt()

    for r in entrada.get("registros", []):
        if r.get("processado"):
            continue

        texto_original = r["texto"]

        # ===== Pré-processamento =====
        status = extrair_status(texto_original)
        texto_sem_modelo, modelos = separar_modelos(texto_original)
        endereco = extrair_endereco(texto_original)
        cor = extrair_cor(texto_original)
        texto_limpo = remover_status(texto_sem_modelo)

        prompt = prompt_base + "\nTexto:\n" + texto_limpo

        # ===== Chamada da IA =====
        resposta = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        conteudo = resposta.choices[0].message.content
        match = re.search(r"\{.*\}", conteudo, re.DOTALL)

        if not match:
            print(f"IA não retornou JSON válido para registro {r['id']}")
            continue

        dados = json.loads(match.group())

        # ===== Pós-processamento FORTE =====
        dados["STATUS"] = status or "DESCONHECIDO"
        dados["BLOCO"] = endereco.get("BLOCO") or dados.get("BLOCO", "")
        dados["APARTAMENTO"] = endereco.get("APARTAMENTO") or dados.get("APARTAMENTO", "")
        dados["PLACA"] = endereco.get("PLACA") or dados.get("PLACA", "")
        dados["MODELO"] = modelos[0].title() if modelos else dados.get("MODELO", "")
        dados["COR"] = cor or dados.get("COR", "")

        # Corrigir NOME e SOBRENOME
        nome_completo = corrigir_nome(dados.get("NOME", ""))
        if " " in nome_completo:
            partes = nome_completo.split()
            dados["NOME"] = partes[0].title()
            dados["SOBRENOME"] = " ".join(partes[1:]).title() if len(partes) > 1 else "-"
        else:
            dados["NOME"] = nome_completo.title()
            dados["SOBRENOME"] = "-"

        dados["ID"] = r["id"]
        dados["DATA_HORA"] = r["data_hora"]

        # Evitar campos vazios
        for k in ["NOME","SOBRENOME","BLOCO","APARTAMENTO","PLACA","MODELO","COR","STATUS"]:
            if not dados.get(k):
                dados[k] = "-"

        saida.setdefault("registros", []).append(dados)
        r["processado"] = True

    salvar(ENTRADA, entrada)
    salvar(SAIDA, saida)

# =========================
# Execução
# =========================
if __name__ == "__main__":
    processar()
