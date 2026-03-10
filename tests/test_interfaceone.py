import unittest
from unittest import mock

import interfaceone


class InterfaceOneTests(unittest.TestCase):
    def test_encomenda_text_detection(self):
        txt = "PACOTE SHOPEE BLOCO A AP 101"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

        txt2 = "ABC1234 ONIX PRETO BLOCO A AP 101"
        self.assertFalse(interfaceone._is_encomenda_text(txt2, parsed={"PLACA": "ABC1234"}))

    def test_encomenda_nao_bloqueia_por_placa_ruidosa_do_parser(self):
        txt = "APT111 88SG4RSHNA8BR ENV RIACHUELO BLO13 JOAO PEREIRA"
        parsed = {"PLACA": "APT111", "MODELOS": ["RIACHUELO"], "STATUS": "DESCONHECIDO"}
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed=parsed))

    def test_encomenda_bloqueia_quando_ha_sinal_real_de_pessoa(self):
        txt = "PACOTE SHOPEE BLOCO 1 AP 22"
        parsed = {"PLACA": "ABC1234", "MODELOS": ["ONIX"], "STATUS": "VISITANTE"}
        self.assertFalse(interfaceone._is_encomenda_text(txt, parsed=parsed))

    def test_token_common_prefix_len(self):
        self.assertEqual(interfaceone.token_common_prefix_len("MARIA SILVA", "MARIA SOUZA"), 7)
        self.assertEqual(interfaceone.token_common_prefix_len("ANA", "BRUNO"), 0)

    def test_match_store_token_without_rapidfuzz(self):
        with mock.patch.object(interfaceone, "rf_process", None), mock.patch.object(interfaceone, "rf_fuzz", None):
            self.assertFalse(interfaceone._match_encomenda_store_token(["SHOPEE"]))

    def test_encomenda_aliases_detected(self):
        txt = "APT111 88SG4RSHNA8BR ENV RIACHUELO BLO13 JOAO PEREIRA"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_encomenda_alias_shop_detected(self):
        txt = "EVELOPE SHOP BRUNO RIBEIRO BLOCO13 APARTAMEN109"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_encomenda_when_only_tipo_signal(self):
        txt = "ENVELOPE JOAO SILVA BLOCO 1 AP 22"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_encomenda_when_only_loja_signal(self):
        txt = "SHOPEE JOAO SILVA BLOCO 1 AP 22"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_encomenda_when_only_identificacao_signal(self):
        txt = "OSIJEVXTKTOTI JOAO SILVA BLOCO 1 AP 22"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_encomenda_com_status_parser_contaminado_ainda_detecta_encomenda(self):
        txt = "ENVELOPE 768853798203 MARIA LIMA APTA73 M LIVRE BLOCO3"
        parsed = {"PLACA": "APTA73", "MODELOS": ["LIMA", "LIVRE"], "STATUS": "MORADOR"}
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed=parsed))

    def test_non_encomenda_person_record_not_forced(self):
        txt = "JOAO PEREIRA BLOCO 13 AP 111"
        self.assertFalse(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_non_encomenda_lowercase_long_word_not_identificacao(self):
        txt = "texto qualquer"
        self.assertFalse(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_orientacao_texto_livre_nao_deve_virar_encomenda(self):
        txt = "Registrando ocorrencia de clamacao de barulho vindo do bloco 10 aparamneto 10, morador Flavio Junior foi orientado"
        self.assertFalse(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_orientacao_texto_livre_do_usuario_com_pontuacao_nao_deve_virar_encomenda(self):
        txt = "Registrando ocorrencia de clamacao de barulho vindo do bloco 10 aparamneto 10, morador Flavio Junior foi orientado."
        self.assertFalse(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_formalize_notes_text_corrige_termos_basicos(self):
        txt = "orientacao no aparamneto 10 sobre clamacao"
        out = interfaceone._formalize_notes_text(txt, "ORIENTACAO")
        self.assertIn("orientação", out.lower())
        self.assertIn("apartamento", out.lower())
        self.assertIn("reclamação", out.lower())


if __name__ == "__main__":
    unittest.main()
