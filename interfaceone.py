import tkinter as tk
import json
from datetime import datetime
import subprocess

ARQUIVO = "dadosinit.json"


def carregar():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"registros": []}


def salvar_texto(event=None):
    texto = entrada.get().strip()
    if not texto:
        return

    dados = carregar()
    novo_id = len(dados["registros"]) + 1

    dados["registros"].append({
        "id": novo_id,
        "texto": texto,
        "processado": False,
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    })

    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=4)

    entrada.delete(0, tk.END)
    subprocess.Popen(["python", "ia.py"])


def abrir_dados():
    subprocess.Popen(["python", "interfacetwo.py"])


janela = tk.Tk()
janela.title("Controle de Acesso")

entrada = tk.Entry(janela, width=80)
entrada.pack(padx=10, pady=10)
entrada.bind("<Return>", salvar_texto)

tk.Button(janela, text="SALVAR", command=salvar_texto).pack()
tk.Button(janela, text="DADOS", command=abrir_dados).pack()

janela.mainloop()
