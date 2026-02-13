import unittest

import json_contracts


class JsonContractsTests(unittest.TestCase):
    def test_validate_all_contracts_ok(self):
        payloads = {
            "dadosinit": {"registros": [{"id": 1, "texto": "x", "processado": False, "data_hora": "10/01/2026 10:00:00"}]},
            "dadosend": {"registros": [{"ID": 1, "BLOCO": "A", "APARTAMENTO": "1", "DATA_HORA": "10/01/2026 10:00:00", "STATUS": "MORADOR"}]},
            "encomendasinit": {"registros": []},
            "encomendasend": {"registros": []},
            "analises": {"registros": [], "encomendas_multiplas_bloco_apartamento": []},
            "avisos": {"registros": []},
            "runtime_last_status": {"timestamp": "2026-01-10 10:00:00", "action": "x", "status": "OK", "stage": "y", "details": {}},
        }
        out = json_contracts.validate_all_contracts(payloads)
        self.assertTrue(all(len(v) == 0 for v in out.values()))

    def test_validate_contracts_detects_errors(self):
        out = json_contracts.validate_all_contracts({})
        self.assertTrue(any(out[k] for k in out))

    def test_validate_contracts_detects_type_and_domain_errors(self):
        payloads = {
            "dadosinit": {"registros": [{"id": "1", "texto": 5, "processado": "no", "data_hora": "bad"}]},
            "dadosend": {"registros": [{"ID": "2", "BLOCO": "A", "APARTAMENTO": "2", "DATA_HORA": "bad", "STATUS": "XYZ"}]},
            "encomendasinit": {"registros": [{"DATA_HORA": "invalid"}]},
            "encomendasend": {"registros": []},
            "analises": {"registros": [], "encomendas_multiplas_bloco_apartamento": []},
            "avisos": {"registros": []},
            "runtime_last_status": {"timestamp": "invalid", "action": "x", "status": "BOOM", "stage": "s", "details": "oops"},
        }
        out = json_contracts.validate_all_contracts(payloads)
        self.assertIn("registro_0_id_tipo_invalido", out["dadosinit"])
        self.assertIn("registro_0_status_fora_dominio", out["dadosend"])
        self.assertIn("runtime_last_status_status_fora_dominio", out["runtime_last_status"])


if __name__ == "__main__":
    unittest.main()
