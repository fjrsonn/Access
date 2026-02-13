import unittest

import json_contracts


class JsonContractsTests(unittest.TestCase):
    def test_validate_all_contracts_ok(self):
        payloads = {
            "dadosinit": {"registros": [{"id": 1, "texto": "x", "processado": False, "data_hora": "10/01/2026 10:00:00"}]},
            "dadosend": {"registros": [{"ID": 1, "BLOCO": "A", "APARTAMENTO": "1", "DATA_HORA": "10/01/2026 10:00:00"}]},
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


if __name__ == "__main__":
    unittest.main()
