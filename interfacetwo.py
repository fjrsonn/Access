import tkinter as tk
import json

ARQUIVO = "dadosend.json"


def carregar():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f).get("registros", [])
    except:
        return []


def safe(v):
    return v if v else "-"


def atualizar():
    lista.delete(0, tk.END)

    for r in carregar():
        linha = (
            f'{safe(r.get("DATA_HORA"))} | '
            f'{safe(r.get("NOME"))} {safe(r.get("SOBRENOME"))} | '
            f'BLOCO {safe(r.get("BLOCO"))} AP {safe(r.get("APARTAMENTO"))} | '
            f'PLACA {safe(r.get("PLACA"))} | '
            f'{safe(r.get("MODELO"))} | '
            f'{safe(r.get("COR"))} | '
            f'{safe(r.get("STATUS"))}'
        )
        lista.insert(tk.END, linha)

    janela.after(2000, atualizar)


janela = tk.Tk()
janela.title("Monitor de Acessos")

lista = tk.Listbox(janela, width=200)
lista.pack(padx=10, pady=10)

atualizar()
janela.mainloop()
