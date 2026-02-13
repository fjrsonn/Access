#!/usr/bin/env python3
"""Suíte unificada de testes do projeto Access.

- Consolida os testes antigos em um único arquivo.
- Inclui cenários com entradas reais de portaria/encomenda.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime

import chat
import ia
import logger
import main
import preprocessor
from text_classifier import (
    _is_notification_intent,
    classificar_destino_texto,
    extract_fields_heuristic,
    extract_fields_strict,
)


class PreprocessorTests(unittest.TestCase):
    def test_detectar_status(self):
        casos = {
            "VIS JOAO BLOCO 4": "VISITANTE",
            "JOAO BLOCO 4 AP 12": "DESCONHECIDO",
            "M JOAO AP 10": "MORADOR",
            "PREST MARIA SERV LIMPEZA": "PRESTADOR DE SERVIÇO",
            "JOAO OLIVEIRA": "DESCONHECIDO",
        }
        for texto, esperado in casos.items():
            status, _ = preprocessor.detectar_status(texto)
            self.assertEqual(status, esperado)

    def test_remover_status(self):
        texto = "MORADOR FLAVIO JUNIOR BL10 AP10 FEU3C84 JETA PRETO"
        limpo = preprocessor.remover_status(texto)
        self.assertNotIn("MORADOR", limpo)

    def test_extrair_tudo_consumo_com_entradas_reais(self):
        entradas = [
            "FLAVIO JUNIOR BL10 AP10 FEU3C84 JETA PRETO MORADOR",
            "REGIANE MENEZES BL10 AP10 FJS0701 NIVUS CINZA VISITANTE",
            "FLAVIO JUNIOR MORADOR BL10 AP10 FEU3C84 JETA PRETO",
            "MORADOR FLAVIO JUNIOR BL10 AP10 FEU3C84 JETA PRETO",
            "JETA PRETO FEU3C84 MORADOR FLAVIO JUNIOR BL10 AP10",
            "FEU3C84 JETA FLAVIO MORADOR AP10 BL10 JUNIOR PRETO",
            "POLO PRETO JOAO SOUZA AP2 BL2 PTF2569 PREST",
        ]
        for texto in entradas:
            out = preprocessor.extrair_tudo_consumo(texto)
            self.assertTrue(out.get("BLOCO"))
            self.assertTrue(out.get("APARTAMENTO"))
            self.assertTrue(out.get("STATUS"))
            self.assertTrue(out.get("PLACA"))


class IATests(unittest.TestCase):
    def test_parse_encomenda_texto_digitacao_real(self):
        e1 = ia._parse_encomenda_text("juliana santos bl5 ap1 pct shopee 109329084")
        self.assertEqual(e1["NOME"], "JULIANA")
        self.assertEqual(e1["SOBRENOME"], "SANTOS")
        self.assertEqual(e1["BLOCO"], "5")
        self.assertEqual(e1["APARTAMENTO"], "1")
        self.assertEqual(e1["LOJA"], "SHOPEE")
        self.assertEqual(e1["IDENTIFICACAO"], "109329084")

        e2 = ia._parse_encomenda_text("joao cesar bl4 ap10 amanzon 3358721451BR")
        self.assertEqual(e2["NOME"], "JOÃO")
        self.assertEqual(e2["BLOCO"], "4")
        self.assertEqual(e2["APARTAMENTO"], "10")
        self.assertIn("3358721451", e2["IDENTIFICACAO"])

    def test_append_or_update_saida(self):
        old_saida = ia.SAIDA
        try:
            with tempfile.TemporaryDirectory() as tmp:
                ia.SAIDA = os.path.join(tmp, "dadosend.json")
                primeiro = {
                    "NOME": "FLAVIO",
                    "SOBRENOME": "JUNIOR",
                    "BLOCO": "10",
                    "APARTAMENTO": "10",
                    "PLACA": "FEU3C84",
                    "MODELO": "JETTA",
                    "COR": "PRETO",
                    "STATUS": "MORADOR",
                    "DATA_HORA": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                }
                self.assertTrue(ia.append_or_update_saida(primeiro, entrada_id=1))
                self.assertTrue(ia.append_or_update_saida(primeiro, entrada_id=1))
                regs = ia.carregar(ia.SAIDA)["registros"]
                self.assertEqual(len(regs), 1)
                self.assertEqual(regs[0]["_entrada_id"], 1)
        finally:
            ia.SAIDA = old_saida


class ChatAndClassifierTests(unittest.TestCase):
    def test_chat_pipeline_funcoes_base(self):
        tokens = chat._query_tokens("qual foi a primeira encomenda do joao no bloco 4")
        self.assertIn("primeira", tokens)
        self.assertNotIn("qual", tokens)

        notice = chat._build_partial_context_notice(
            {
                "contexto_recente": {
                    "dadosend.json__meta": {
                        "registros_totais": 120,
                        "registros_recentes_enviados": 30,
                    }
                }
            }
        )
        self.assertIn("recente", notice.lower())

        masked = chat._shrink_value({"telefone": "11999998888"})
        self.assertIn("***", masked["telefone"])
        self.assertIsNotNone(chat._parse_timestamp("09/02/2026 23:54"))

    def test_chat_contexto_ambiguo(self):
        full_sources = {
            "dadosend.json": [
                {
                    "NOME": "Joao",
                    "SOBRENOME": "Silva",
                    "BLOCO": "2",
                    "APARTAMENTO": "10",
                    "DATA_HORA": "09/02/2026 10:00",
                },
                {
                    "NOME": "Joao",
                    "SOBRENOME": "Silva",
                    "BLOCO": "5",
                    "APARTAMENTO": "3",
                    "DATA_HORA": "09/02/2026 11:00",
                },
            ],
            "encomendasend.json": [],
            "avisos.json": [],
        }
        consolidated = chat._build_consolidated_context(full_sources)
        self.assertIn("joao silva", consolidated.get("nomes_ambiguos", {}))

    def test_classificacao_texto(self):
        out1 = classificar_destino_texto(
            "Avisar encomendas quando chegar bloco 10 apartamento 10 no nome do Flavio"
        )
        self.assertEqual(out1["destino"], "observacoes")

        out2 = classificar_destino_texto(
            "Relato de ocorrencia: orientar morador e avisar sindico sobre o ocorrido"
        )
        self.assertEqual(out2["destino"], "orientacoes")

        out3 = classificar_destino_texto(
            "avisa encomendas qndo chegarr bloco 2 ap 31"
        )
        self.assertIn(out3["destino"], {"observacoes", "encomendas"})

        self.assertTrue(_is_notification_intent("avisar o morador quando chegar encomenda"))

    def test_extract_fields(self):
        txt = "morador Flavio Junior bloco 10 apartamento 10 placa FEU3C84"
        strict = extract_fields_strict(txt)
        heur = extract_fields_heuristic(txt)
        self.assertTrue(strict.get("BLOCO"))
        self.assertIn("BLOCO", heur)


class InfraTests(unittest.TestCase):
    def test_main_helpers(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "novo.json")
            main.ensure_file(p, {"registros": []})
            self.assertTrue(os.path.exists(p))

            dados = {
                "registros": [
                    {
                        "NOME": "Juliana",
                        "SOBRENOME": "Santos",
                        "BLOCO": "5",
                        "APARTAMENTO": "1",
                        "ID": 2,
                        "DATA_HORA": "10/02/2026 12:00:00",
                    }
                ]
            }
            with open(p, "w", encoding="utf-8") as f:
                json.dump(dados, f)

            ident = main._get_last_record_identity(p)
            self.assertEqual(ident, "JULIANA|SANTOS|5|1")

    def test_logger_log_forense(self):
        old_file = logger.LOG_FILE
        try:
            with tempfile.TemporaryDirectory() as tmp:
                logger.LOG_FILE = os.path.join(tmp, "forense.log")
                logger.log_forense(1, "texto teste", "OK", "TESTE")
                with open(logger.LOG_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("ID:1", content)
                self.assertIn("TEXTO:texto teste", content)
        finally:
            logger.LOG_FILE = old_file


if __name__ == "__main__":
    unittest.main(verbosity=2)
