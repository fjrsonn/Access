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


if __name__ == "__main__":
    unittest.main()
