import unittest

import main_tests


class MainTestsHelpers(unittest.TestCase):
    def test_validate_encomenda_pipeline_record_ok(self):
        raw = "APT111 88SG4RSHNA8BR ENV RIACHUELO BLO13 JOAO PEREIRA"
        init_rec = {"id": 77, "texto": raw, "processado": True}
        end_rec = {
            "NOME": "JOAO",
            "SOBRENOME": "PEREIRA",
            "BLOCO": "13",
            "APARTAMENTO": "111",
            "TIPO": "ENVELOPE",
            "LOJA": "RIACHUELO",
            "IDENTIFICACAO": "88SG4RSHNA8BR",
            "_entrada_id": 77,
            "DATA_HORA": "10/01/2026 10:10:10",
            "ID": 120,
        }
        status, issues = main_tests.validate_encomenda_pipeline_record(raw, init_rec, end_rec)
        self.assertEqual(status, "OK")
        self.assertEqual(issues, [])

    def test_validate_encomenda_pipeline_record_falhou(self):
        raw = "APT111 88SG4RSHNA8BR ENV RIACHUELO BLO13 JOAO PEREIRA"
        init_rec = {"id": 77, "texto": raw, "processado": True}
        end_rec = {
            "NOME": "APT111",
            "SOBRENOME": "-",
            "BLOCO": "13",
            "APARTAMENTO": "111",
            "TIPO": "-",
            "LOJA": "RIACHUELO",
            "IDENTIFICACAO": "-",
            "_entrada_id": 77,
            "DATA_HORA": "10/01/2026 10:10:10",
            "ID": 120,
        }
        status, issues = main_tests.validate_encomenda_pipeline_record(raw, init_rec, end_rec)
        self.assertEqual(status, "FALHOU")
        self.assertIn("nome_invalido", issues)
        self.assertIn("sobrenome_invalido", issues)
        self.assertIn("tipo_invalido", issues)
        self.assertIn("identificacao_invalida", issues)

    def test_validate_encomenda_pipeline_record_gargalo(self):
        raw = "APT111 88SG4RSHNA8BR ENV RIACHUELO BLO13 JOAO PEREIRA"
        init_rec = {"id": 77, "texto": raw, "processado": False}
        status, issues = main_tests.validate_encomenda_pipeline_record(raw, init_rec, None)
        self.assertEqual(status, "GARGALO")
        self.assertIn("registro_nao_processado_em_encomendasinit", issues)


if __name__ == "__main__":
    unittest.main()
