import unittest

import interfacetwo


class InterfaceTwoTests(unittest.TestCase):
    def test_infer_model_color_from_text(self):
        modelo, cor = interfacetwo._infer_model_color_from_text("ABC1234 ONIX PRETO MORADOR")
        self.assertTrue(modelo.upper().startswith("ONIX"))
        self.assertTrue(cor.upper().startswith("PRETO"))

    def test_format_line_contains_core_fields(self):
        line = interfacetwo.format_line(
            {
                "DATA_HORA": "10/01/2026 10:10:10",
                "NOME": "Ana",
                "SOBRENOME": "Silva",
                "BLOCO": "A",
                "APARTAMENTO": "101",
                "PLACA": "ABC1234",
                "MODELO": "Onix",
                "COR": "Preto",
            }
        )
        self.assertIn("BLOCO A", line)
        self.assertIn("APARTAMENTO 101", line)
        self.assertIn("PLACA ABC1234", line)


if __name__ == "__main__":
    unittest.main()
