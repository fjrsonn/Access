# ia.py — versão final com modo IA interativo e NORMALIZAÇÃO PARA MAIÚSCULAS
import json
import re
import os
import sys
import tempfile
import time
import traceback
from typing import Optional, Tuple, Any
from dotenv import load_dotenv

try:
    from groq import Groq
except Exception:
    Groq = None  # se groq não estiver instalado, mantém fallback

from preprocessor import (
    extrair_tudo_consumo,
    VEICULOS_MAP,
    remover_status,
)
from logger import log_forense

# =========================
# PATHS / ENV
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    GROQ_API_KEY = GROQ_API_KEY.strip().strip('"').strip("'")
    print(f"[ia.py] GROQ_API_KEY carregada: {GROQ_API_KEY[:6]}... (mascarada)")
else:
    print("[ia.py] AVISO: GROQ_API_KEY não encontrada. IA remota desativada.")

if GROQ_API_KEY and not GROQ_API_KEY.startswith("gsk_"):
    print("[ia.py] AVISO: a chave não parece ser Groq (não começa com 'gsk_').")

client = None
if GROQ_API_KEY and Groq is not None:
    try:
        client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"[ia.py] Erro ao criar cliente Groq: {e}")
        client = None

ENTRADA = os.path.join(BASE_DIR, "dadosinit.json")
SAIDA = os.path.join(BASE_DIR, "dadosend.json")
PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "prompt_llm.txt")
LOCK_FILE = os.path.join(BASE_DIR, "process.lock")


# =========================
# Utilitários IO
# =========================
def carregar(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"registros": data}
            if isinstance(data, dict) and "registros" in data:
                return data
            return {"registros": []}
    except FileNotFoundError:
        return {"registros": []}
    except json.JSONDecodeError:
        try:
            bak = f"{path}.corrupted.{int(time.time())}.bak"
            os.replace(path, bak)
            print(f"[ia.py] JSON corrompido, backup criado: {bak}")
        except Exception:
            pass
        return {"registros": []}
    except Exception as e:
        print(f"[ia.py] Erro ao carregar {path}: {e}")
        return {"registros": []}


def salvar_atomico(path: str, dados):
    os.makedirs(os.path.dirname(path) or BASE_DIR, exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=os.path.dirname(path),
            prefix=".tmp_",
            suffix=".json",
            delete=False,
        ) as f:
            tmp = f.name
            json.dump(dados, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        print(f"[ia.py] Arquivo salvo: {path} (registros={len(dados.get('registros', []))})")
    except Exception:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
        raise


def carregar_prompt():
    try:
        with open(PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return (
            "Retorne SOMENTE este JSON:\n"
            '{ "NOME": "", "SOBRENOME": "", "MODELO": "", "COR": "" }'
        )


def extrair_json_seguro(texto: str):
    if not texto:
        return None
    texto_limpo = re.sub(r"```(?:json)?", "", texto)
    blocos = re.findall(r"\{[\s\S]*?\}", texto_limpo)
    if not blocos:
        return None
    for bloco in reversed(blocos):
        try:
            return json.loads(bloco)
        except json.JSONDecodeError:
            continue
    return None


# =========================
# Lock simples (arquivo)
# =========================
def acquire_lock(timeout: int = 10) -> bool:
    start = time.time()
    while True:
        try:
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except FileExistsError:
            if (time.time() - start) > timeout:
                return False
            time.sleep(0.1)


def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


# =========================
# Desabilitar client em caso de auth failure
# =========================
def _disable_client_due_to_auth():
    global client, GROQ_API_KEY
    print("[ia.py] Desativando Groq client devido a erro de autenticação. Atualize GROQ_API_KEY e reinicie.")
    client = None
    GROQ_API_KEY = None


# =========================
# Validação híbrida de MODELO (mais permissiva)
# =========================
def validar_modelo_str(s: str) -> Optional[str]:
    if not s:
        return None

    s_original = str(s).strip()
    s_norm = re.sub(r"[^\w\d\s\-]", " ", s_original).upper()

    # tenta mapear pelo VEICULOS_MAP
    for modelo_key, abrevs in VEICULOS_MAP.items():
        if re.search(rf"\b{re.escape(modelo_key.upper())}\b", s_norm):
            return modelo_key
        for ab in abrevs:
            if re.search(rf"\b{re.escape(ab.upper())}\b", s_norm):
                return modelo_key

    # se não mapeou, mas parece um nome válido (evitar placas e números puros)
    if (
        len(s_original) >= 3
        and not re.fullmatch(r"[A-Z]{3}\d{4}", s_norm)  # placa
        and not re.fullmatch(r"\d+", s_norm)  # só número
    ):
        # remover descritores comuns de cor/acabamento que sujam o modelo
        limpo = re.sub(
            r"\b(preto|preta|branco|branca|prata|cinza|vermelho|azul|verde|amarelo|dourado|bege|marrom|vinho)\b",
            "",
            s_original,
            flags=re.I,
        ).strip()
        if limpo:
            return limpo.title()

    return None


# =========================
# NORMALIZAÇÃO PARA MAIÚSCULAS
# =========================
def _uppercase_value(v: Any) -> Any:
    """
    Transforma strings em maiúsculas e elementos de listas também.
    Mantém outros tipos inalterados.
    """
    if isinstance(v, str):
        return v.upper()
    if isinstance(v, list):
        return [_uppercase_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _uppercase_value(val) for k, val in v.items()}
    return v


def uppercase_dict_values(d: dict) -> dict:
    """
    Retorna cópia do dict com todas as strings transformadas em MAIÚSCULAS.
    """
    out = {}
    for k, v in d.items():
        out[k] = _uppercase_value(v)
    return out


# =========================
# PROCESSAMENTO PRINCIPAL
# =========================
def processar():
    if not acquire_lock(timeout=5):
        print("[ia.py] Outro processo em execução. Abortando.")
        return

    try:
        entrada = carregar(ENTRADA)
        saida = carregar(SAIDA)
        prompt_base = carregar_prompt()

        for r in entrada.get("registros", []):
            if r.get("processado"):
                continue

            texto_original = r.get("texto", "")
            # try/except defensivo para evitar crash por preprocessor
            try:
                pre = extrair_tudo_consumo(texto_original)
            except Exception as e:
                print(f"[ia.py] Erro ao extrair dados (id={r.get('id')}): {e}")
                traceback.print_exc()
                pre = {
                    "TEXTO_LIMPO": texto_original or "",
                    "COR": "",
                    "PLACA": "",
                    "BLOCO": "",
                    "APARTAMENTO": "",
                    "MODELOS": [],
                    "NOME_RAW": "",
                }

            status = pre.get("STATUS", "DESCONHECIDO")
            modelos_pre = pre.get("MODELOS", []) or []
            endereco = {
                "BLOCO": pre.get("BLOCO", ""),
                "APARTAMENTO": pre.get("APARTAMENTO", ""),
                "PLACA": pre.get("PLACA", ""),
            }
            cor_pre = pre.get("COR", "") or ""
            # normalizar cor_pre defensivamente
            if isinstance(cor_pre, list):
                cor_pre = next((c for c in cor_pre if isinstance(c, str) and c.strip()), " ".join(map(str, cor_pre)))
            cor_pre = str(cor_pre).strip()

            texto_limpo = pre.get("TEXTO_LIMPO") or pre.get("NOME_RAW") or remover_status(texto_original)

            prompt = (
                prompt_base
                + "\n\nTexto:\n"
                + texto_limpo
                + "\n\nResponda SOMENTE com JSON válido seguindo o schema:\n"
                '{ "NOME": "", "SOBRENOME": "", "MODELO": "", "COR": "" }'
            )

            dados_ia = None
            conteudo = ""

            if client:
                try:
                    resposta = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0,
                    )
                    conteudo = (
                        resposta.choices[0].message.content
                        if hasattr(resposta, "choices") and resposta.choices
                        else str(resposta)
                    )
                    dados_ia = extrair_json_seguro(conteudo)
                    # se a IA devolveu, normalizamos esse conteúdo para maiúsculas já aqui
                    if isinstance(dados_ia, dict):
                        dados_ia = uppercase_dict_values(dados_ia)
                except Exception as e:
                    err_msg = str(e).lower()
                    print(f"⚠️ Falha IA (fallback ativo): {e}")
                    traceback.print_exc()
                    if "invalid_api_key" in err_msg or "401" in err_msg:
                        _disable_client_due_to_auth()
                    # mantém dados_ia = None para fallback local

            # Estrutura default (strings em maiúsculas)
            dados = {"NOME": "-", "SOBRENOME": "-", "MODELO": "-", "COR": cor_pre.upper() if cor_pre else "-"}

            # Prioriza dados da IA se existirem (dados_ia já uppercase se vier do LLM)
            if dados_ia:
                # garantir que os valores sejam strings antes de operar
                n = dados_ia.get("NOME") if isinstance(dados_ia.get("NOME"), str) else None
                sn = dados_ia.get("SOBRENOME") if isinstance(dados_ia.get("SOBRENOME"), str) else None
                if n:
                    dados["NOME"] = n.upper()
                if sn:
                    dados["SOBRENOME"] = sn.upper()

                modelo_from_ia = dados_ia.get("MODELO") if isinstance(dados_ia.get("MODELO"), str) else ""
                modelo_validado = validar_modelo_str(modelo_from_ia) if modelo_from_ia else None
                if modelo_validado:
                    dados["MODELO"] = modelo_validado.upper()
                # cor: preferir valor da IA quando presente
                cor_ia = dados_ia.get("COR") if isinstance(dados_ia.get("COR"), str) else ""
                if cor_ia:
                    dados["COR"] = cor_ia.upper()

            # se ainda não há modelo, tenta modelos pré-extraídos (preprocessor)
            if dados.get("MODELO") in (None, "", "-"):
                if modelos_pre:
                    candidato = modelos_pre[0]
                    if candidato:
                        candidato_val = validar_modelo_str(candidato)
                        if candidato_val:
                            dados["MODELO"] = candidato_val.upper()
                        else:
                            dados["MODELO"] = str(candidato).upper()

            # fallback para nome quando IA não retornou
            if dados.get("NOME") in (None, "", "-"):
                nome_raw = pre.get("NOME_RAW", "") or ""
                if nome_raw:
                    parts = nome_raw.split()
                    if parts:
                        dados["NOME"] = parts[0].upper()
                        dados["SOBRENOME"] = " ".join(parts[1:]).upper() if len(parts) > 1 else "-"

            # preencher demais campos (em maiúsculas)
            dados["PLACA"] = (endereco.get("PLACA", "") or "-").upper()
            dados["BLOCO"] = (endereco.get("BLOCO", "") or "-").upper()
            dados["APARTAMENTO"] = (endereco.get("APARTAMENTO", "") or "-").upper()
            dados["STATUS"] = (status or "DESCONHECIDO").upper()

            # garantir formatos mínimos e uppercase geral (reaplicar para segurança)
            for k in ["NOME", "SOBRENOME", "BLOCO", "APARTAMENTO", "PLACA", "MODELO", "COR", "STATUS"]:
                v = dados.get(k)
                if v is None or (isinstance(v, str) and v.strip() == ""):
                    dados[k] = "-"
                elif isinstance(v, str):
                    dados[k] = v.upper()

            dados["ID"] = r.get("id")
            # DATA_HORA também é string — vamos converter para maiúsculas também (se for string)
            dh = r.get("data_hora")
            dados["DATA_HORA"] = dh.upper() if isinstance(dh, str) else dh

            # finalmente adicionar ao saida (dados já uppercase)
            saida.setdefault("registros", []).append(dados)
            r["processado"] = True

            log_forense(r.get("id"), texto_original, dados.get("STATUS"), "ia.py")

        salvar_atomico(ENTRADA, entrada)
        salvar_atomico(SAIDA, saida)

    finally:
        release_lock()


# =========================
# Consulta ad-hoc (respond_query)
# =========================
def respond_query(user_query: str, db_path: str = SAIDA, model: str = "llama-3.1-8b-instant", temperature: float = 0.0, timeout: int = 15) -> str:
    """
    Retorna resposta da IA (se habilitada) ou fallback.
    Todas as strings retornadas por aqui também são convertidas para MAIÚSCULAS,
    para manter consistência visual.
    """
    db = carregar(db_path).get("registros", []) or []
    try:
        db_json = json.dumps(db, ensure_ascii=False)
    except Exception:
        db_json = str(db)[:20000]

    system_msg = (
        "Você é uma assistente cujo único objetivo é responder perguntas consultando estritamente o banco de "
        "dados JSON fornecido (chamado 'DATABASE' abaixo). NÃO invente informações e responda apenas com base no DATABASE. "
        "Formate a resposta de forma clara e profissional, liste resultados relevantes (uma linha por registro) e, quando fizer sentido, "
        "forneça um breve resumo. Se a consulta solicitar filtros por bloco, data, nome, status, etc., busque esses registros no DATABASE."
    )

    user_msg = f"Pergunta do usuário: {user_query}\n\nDATABASE:\n{db_json}"

    if client:
        try:
            resposta = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=temperature,
            )
            content = (
                resposta.choices[0].message.content
                if hasattr(resposta, "choices") and resposta.choices
                else str(resposta)
            )
            return content.upper() if isinstance(content, str) else content
        except Exception as e:
            err_msg = str(e).lower()
            print(f"[ia.respond_query] Erro ao consultar LLM: {e}")
            traceback.print_exc()
            if "invalid_api_key" in err_msg or "401" in err_msg:
                _disable_client_due_to_auth()

    # Fallback local: busca simples por tokens (resultados formatados em MAIÚSCULAS)
    try:
        q = user_query.lower()
        results = []

        m = re.search(r"bloco\s*(\d+)", q)
        block = m.group(1) if m else None

        m2 = re.search(r"(\d{1,2}/\d{1,2}(?:/\d{2,4})?)", q)
        date_filter = m2.group(1) if m2 else None

        if "visit" in q or "visitante" in q:
            st = "VISITANTE"
        elif "morador" in q or "moradores" in q:
            st = "MORADOR"
        else:
            st = None

        for r in db:
            ok = True
            if block:
                if str(r.get("BLOCO", "")).lower() != str(block).lower():
                    ok = False
            if date_filter:
                dh = r.get("DATA_HORA", "") or ""
                if date_filter not in dh:
                    ok = False
            if st:
                if (r.get("STATUS") or "").lower() != st.lower():
                    ok = False
            if ok:
                results.append(r)

        if not results:
            return "NENHUM REGISTRO ENCONTRADO COM OS FILTROS SIMPLES APLICADOS (FALLBACK). SE DESEJAR RESPOSTAS MAIS FLEXÍVEIS, CONFIGURE GROQ_API_KEY PARA USAR A IA.".upper()

        lines = []
        for rec in results[:200]:
            # garantir que os campos sejam string e uppercase (dados gravados já estão uppercase)
            dh = rec.get("DATA_HORA", "-")
            nome = rec.get("NOME", "-")
            sobrenome = rec.get("SOBRENOME", "-")
            bloco = rec.get("BLOCO", "-")
            ap = rec.get("APARTAMENTO", "-")
            placa = rec.get("PLACA", "-")
            status = rec.get("STATUS", "-")
            lines.append(f"{str(dh).upper()} | {str(nome).upper()} {str(sobrenome).upper()} | BLOCO {str(bloco).upper()} AP {str(ap).upper()} | PLACA {str(placa).upper()} | {str(status).upper()}")
        summary = f"RESULTADOS ({len(results)}):\n" + "\n".join(lines)
        return summary
    except Exception as e:
        return f"ERRO AO PROCESSAR CONSULTA (FALLBACK): {e}".upper()


# =========================
# MODO IA: controle simples
# =========================
IN_IA_MODE = False


def _normalize_cmd(text: str) -> str:
    if text is None:
        return ""
    return str(text).strip().upper()


def is_enter_ia_command(text: str) -> bool:
    t = _normalize_cmd(text)
    return t in ("IA", "AI")


def is_exit_ia_command(text: str) -> bool:
    t = _normalize_cmd(text).lstrip("/")
    return t in ("SAIR", "EXIT", "QUIT")


def enter_ia_mode() -> str:
    global IN_IA_MODE
    IN_IA_MODE = True
    return "MODO IA ATIVADO — ESCREVA SUA PERGUNTA. PARA SAIR, DIGITE 'SAIR'.".upper()


def exit_ia_mode() -> str:
    global IN_IA_MODE
    IN_IA_MODE = False
    return "MODO IA DESATIVADO. VOCÊ PODE CONTINUAR DIGITANDO NORMALMENTE.".upper()


def handle_input_text(text: str, *, respond_fn=respond_query) -> Tuple[bool, str]:
    """
    Handler para entradas de usuário (p.ex. quando o usuário aperta Enter).
    - Retorna (True, resposta): a entrada foi tratada aqui (IA ativada/saída/consulta).
    - Retorna (False, text): não foi tratada (entrada normal).
    """
    global IN_IA_MODE
    if not text:
        return False, ""

    # comando para entrar no modo IA
    if is_enter_ia_command(text) and not IN_IA_MODE:
        return True, enter_ia_mode()

    # se estivermos no modo IA
    if IN_IA_MODE:
        if is_exit_ia_command(text):
            return True, exit_ia_mode()
        # mandar para a IA (pode ser bloqueante)
        try:
            resp = respond_fn(text)
            # normalizar resposta também para MAIÚSCULAS
            return True, resp.upper() if isinstance(resp, str) else resp
        except Exception as e:
            print(f"[handle_input_text] Erro ao chamar IA: {e}")
            traceback.print_exc()
            return True, f"ERRO AO CONSULTAR IA: {e}".upper()

    # não tratado aqui
    return False, text.upper() if isinstance(text, str) else text


# =========================
# CLI interativo (opcional) — rode: python ia.py cli
# =========================
def _cli_repl():
    print("REPL IA — digite 'ia' para ativar modo IA; 'sair' para sair do modo IA; 'quit' para encerrar.".upper())
    while True:
        try:
            txt = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nENCERRANDO REPL.".upper())
            break

        if txt is None:
            continue
        t = txt.strip()
        if t.lower() in ("quit", "q", "sair_tudo"):
            print("ENCERRANDO.".upper())
            break

        handled, resp = handle_input_text(t)
        if handled:
            # resposta tratada pela IA / sistema (já em uppercase)
            print(resp)
        else:
            # fluxo normal do app: agora exibimos em MAIÚSCULAS como solicitado
            print(f"[ENTRADA NORMAL] {resp}")

if __name__ == "__main__":
    # Se o usuário passou 'cli' como argumento, inicia o REPL para testes interativos
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("cli", "interactive", "repl"):
        _cli_repl()
    else:
        processar()
