import json
import os
import tempfile
import unittest

import main


class MainModuleTests(unittest.TestCase):
    def test_ensure_file_creates_template(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "novo.json")
            tpl = {"registros": [], "ok": True}
            main.ensure_file(p, tpl)
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data, tpl)

    def test_get_last_record_identity_uses_highest_id(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "dadosend.json")
            payload = {
                "registros": [
                    {"ID": 1, "NOME": "Ana", "SOBRENOME": "Silva", "BLOCO": "A", "APARTAMENTO": "101"},
                    {"ID": 3, "NOME": "Bruno", "SOBRENOME": "Lima", "BLOCO": "B", "APARTAMENTO": "202"},
                    {"ID": 2, "NOME": "Carlos", "SOBRENOME": "Moraes", "BLOCO": "C", "APARTAMENTO": "303"},
                ]
            }
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)

            ident = main._get_last_record_identity(p)
            self.assertEqual(ident, "BRUNO|LIMA|B|202")


if __name__ == "__main__":
    unittest.main()
