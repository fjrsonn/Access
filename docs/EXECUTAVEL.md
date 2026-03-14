# Gerar executável do Controle de Acesso

Este projeto já possui automação para gerar executável com logo.

## Logo do app
A logo é gerada automaticamente pelo script `tools/create_logo.py` com:
- fundo preto;
- triângulo branco;
- letra **A** preta em primeiro plano.

Arquivos gerados:
- `assets/access_logo.png`
- `assets/access_logo.ico`

## Passo a passo (Windows)
1. Abra o terminal na raiz do projeto.
2. Execute o build:
   ```bash
   python tools/build_executable.py
   ```
3. Ao final, o PyInstaller cria o app em `dist/ControleAcesso/`.
4. Dentro dessa pasta, localize o executável `ControleAcesso.exe`.
5. Clique com botão direito no `.exe` > **Enviar para > Área de Trabalho (criar atalho)**.
6. Pronto: ao clicar no atalho da área de trabalho, o sistema inicia.

## Somente visualizar comando final (sem compilar)
```bash
python tools/build_executable.py --dry-run
```

## Observações
- O build instala automaticamente dependências de empacotamento (`pyinstaller` e `pillow`).
- O executável é nativo do sistema operacional onde o build foi rodado.
- Para gerar `.exe`, rode o build no Windows.
