import os
import json
import tempfile
import unittest
from unittest import mock

import ia


class IAModuleTests(unittest.TestCase):
    def test_uppercase_dict_values(self):
        data = {"nome": "ana", "nested": {"sobrenome": "silva"}, "arr": ["x", "y"]}
        out = ia.uppercase_dict_values(data)
        self.assertEqual(out["nome"], "ANA")
        self.assertEqual(out["nested"]["sobrenome"], "SILVA")
        self.assertEqual(out["arr"], ["X", "Y"])

    def test_apply_agent_prompt_template(self):
        old = os.environ.get("USE_AGENT_PROMPT")
        try:
            os.environ["USE_AGENT_PROMPT"] = "1"
            ia._AGENT_PROMPT_ATIVO = "Template\n<<TEMPLATE_RESPOSTA>>\nRESPOSTA: {RESPOSTA_BASE}"
            out = ia._apply_agent_prompt_template("OK")
            self.assertIn("RESPOSTA:", out)
            self.assertIn("OK", out)
        finally:
            if old is None:
                os.environ.pop("USE_AGENT_PROMPT", None)
            else:
                os.environ["USE_AGENT_PROMPT"] = old
            ia._AGENT_PROMPT_ATIVO = ""

    def test_handle_input_text_commands(self):
        ia.IN_IA_MODE = False
        changed, msg = ia.handle_input_text("IA")
        self.assertTrue(changed)
        self.assertTrue(ia.IN_IA_MODE)
        self.assertTrue(isinstance(msg, str) and msg)

        changed, msg = ia.handle_input_text("SAIR")
        self.assertTrue(changed)
        self.assertFalse(ia.IN_IA_MODE)
        self.assertTrue(isinstance(msg, str) and msg)


    def test_parse_encomenda_nome_sem_ruido_de_endereco(self):
        txt = "APT111 88SG4RSHNA8BR ENV RIACHUELO BLO13 JOAO PEREIRA"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["NOME"], "JOÃO")
        self.assertEqual(out["SOBRENOME"], "PEREIRA")
        self.assertEqual(out["BLOCO"], "13")
        self.assertEqual(out["APARTAMENTO"], "111")

    def test_parse_encomenda_identificacao_alfanumerica_sem_digitos(self):
        txt = "JADLOG BL13 CAIX APARTAMEN11 BRUNO SOUZA OSIJEVXTKTOTI"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["IDENTIFICACAO"], "OSIJEVXTKTOTI")
        self.assertEqual(out["LOJA"], "JADLOG")
        self.assertEqual(out["TIPO"], "CAIXA")

    def test_parse_encomenda_with_aliases(self):
        txt = "SED 9C3R4DUHASD BEATRIZ LOPES BLCO7 APARTAMENTO86 ENVELOP"
        out = ia._parse_encomenda_text(txt)
        self.assertEqual(out["TIPO"], "ENVELOPE")
        self.assertEqual(out["LOJA"], "CORREIOS")
        self.assertEqual(out["BLOCO"], "7")
        self.assertEqual(out["APARTAMENTO"], "86")
        self.assertEqual(out["IDENTIFICACAO"], "9C3R4DUHASD")

    def test_append_or_update_saida_reusa_registro_com_dados_iguais_exceto_data_hora(self):
        with tempfile.TemporaryDirectory() as td:
            saida = os.path.join(td, "dadosend.json")
            with open(saida, "w", encoding="utf-8") as f:
                json.dump({"registros": []}, f)

            a = {"NOME": "ANA", "SOBRENOME": "SILVA", "BLOCO": "A", "APARTAMENTO": "101", "PLACA": "ABC1234", "MODELO": "ONIX", "COR": "PRETO", "STATUS": "MORADOR", "DATA_HORA": "10/01/2026 10:00:00"}
            b = {"NOME": "ANA", "SOBRENOME": "SILVA", "BLOCO": "A", "APARTAMENTO": "101", "PLACA": "ABC1234", "MODELO": "ONIX", "COR": "PRETO", "STATUS": "MORADOR", "DATA_HORA": "10/01/2026 10:05:00"}

            with mock.patch.object(ia, "SAIDA", saida):
                ia.append_or_update_saida(a, entrada_id=10)
                ia.append_or_update_saida(b, entrada_id=11)

            with open(saida, "r", encoding="utf-8") as f:
                regs = (json.load(f) or {}).get("registros") or []
            self.assertEqual(len(regs), 1)
            self.assertEqual(regs[0].get("ID"), 1)


if __name__ == "__main__":
    unittest.main()
