import json
import os
import tempfile
import unittest

import analises


class AnalisesModuleTests(unittest.TestCase):
    def test_parse_datetime_accepts_common_formats(self):
        self.assertIsNotNone(analises._parse_datetime("10/01/2026 12:30:15"))
        self.assertIsNotNone(analises._parse_datetime("10/01/2026 12:30"))
        self.assertIsNone(analises._parse_datetime("2026-01-10"))

    def test_build_analises_groups_identity_and_orders(self):
        with tempfile.TemporaryDirectory() as td:
            dados_path = os.path.join(td, "dadosend.json")
            out_path = os.path.join(td, "analises.json")
            encomendas_path = os.path.join(td, "encomendasend.json")

            dados = {
                "registros": [
                    {"ID": 2, "NOME": "Ana", "SOBRENOME": "Silva", "BLOCO": "A", "APARTAMENTO": "10", "DATA_HORA": "10/01/2026 12:00:00"},
                    {"ID": 1, "NOME": "Ana", "SOBRENOME": "Silva", "BLOCO": "A", "APARTAMENTO": "10", "DATA_HORA": "09/01/2026 12:00:00"},
                    {"ID": 3, "NOME": "Bruno", "SOBRENOME": "Lima", "BLOCO": "B", "APARTAMENTO": "20", "DATA_HORA": "10/01/2026 12:00:00"},
                ]
            }
            with open(dados_path, "w", encoding="utf-8") as f:
                json.dump(dados, f, ensure_ascii=False)
            with open(encomendas_path, "w", encoding="utf-8") as f:
                json.dump({"registros": []}, f, ensure_ascii=False)

            old = analises.ENCOMENDASEND
            analises.ENCOMENDASEND = encomendas_path
            try:
                result = analises.build_analises(dados_path, out_path, min_group_size=2)
            finally:
                analises.ENCOMENDASEND = old

            self.assertEqual(len(result["registros"]), 1)
            grupo = result["registros"][0]
            self.assertEqual(grupo["identidade"], "ANA|SILVA|A|10")
            self.assertEqual(grupo["registros"][0]["ID"], 1)
            self.assertEqual(grupo["registros"][1]["ID"], 2)


if __name__ == "__main__":
    unittest.main()
