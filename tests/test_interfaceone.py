import unittest

try:
    import interfaceone
except Exception as e:  # pragma: no cover
    interfaceone = None
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None


@unittest.skipIf(interfaceone is None, "Dependência ausente para interfaceone")
class InterfaceOneTests(unittest.TestCase):
    def test_encomenda_text_detection(self):
        txt = "PACOTE SHOPEE BLOCO A AP 101"
        self.assertTrue(interfaceone._is_encomenda_text(txt, parsed={}))

        txt2 = "ABC1234 ONIX PRETO BLOCO A AP 101"
        self.assertFalse(interfaceone._is_encomenda_text(txt2, parsed={"PLACA": "ABC1234"}))

    def test_token_common_prefix_len(self):
        self.assertEqual(interfaceone.token_common_prefix_len("MARIA SILVA", "MARIA SOUZA"), 1)
        self.assertEqual(interfaceone.token_common_prefix_len("ANA", "BRUNO"), 0)


if __name__ == "__main__":
    unittest.main()
