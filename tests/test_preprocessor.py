import unittest

import preprocessor


class PreprocessorModuleTests(unittest.TestCase):
    def test_tokens_and_status_detection(self):
        txt = "ABC1234 ONIX PRETO MORADOR NAO ATENDIDO"
        toks = preprocessor.tokens(txt)
        self.assertIn("ABC1234", [t.upper() for t in toks])

        status, _ = preprocessor.detectar_status(txt)
        self.assertTrue(isinstance(status, str))

    def test_remover_status_and_extract(self):
        txt = "JOAO SILVA BL A AP 101 ABC1234 ONIX PRETO MORADOR NAO ATENDIDO"
        cleaned = preprocessor.remover_status(txt)
        self.assertNotEqual(cleaned.strip(), "")

        data = preprocessor.extrair_tudo_consumo(txt)
        for k in ("NOME_RAW", "PLACA", "BLOCO", "APARTAMENTO", "MODELOS", "STATUS"):
            self.assertIn(k, data)


if __name__ == "__main__":
    unittest.main()
