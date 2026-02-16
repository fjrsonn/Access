import unittest
from unittest import mock

import interfaceone


class InterfaceOneTests(unittest.TestCase):
    def test_encomenda_text_detection(self):
        txt = "PACOTE SHOPEE BLOCO A AP 101"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

        txt2 = "ABC1234 ONIX PRETO BLOCO A AP 101"
        self.assertFalse(interfaceone._is_encomenda_text(txt2, parsed={"PLACA": "ABC1234"}))

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

    def test_non_encomenda_person_record_not_forced(self):
        txt = "JOAO PEREIRA BLOCO 13 AP 111"
        self.assertFalse(interfaceone._is_encomenda_text(txt, parsed={}))

    def test_non_encomenda_lowercase_long_word_not_identificacao(self):
        txt = "texto qualquer"
        self.assertFalse(interfaceone._is_encomenda_text(txt, parsed={}))


if __name__ == "__main__":
    unittest.main()
