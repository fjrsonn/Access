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

    def test_filters_are_active_detection(self):
        self.assertFalse(interfacetwo._filters_are_active({"status": "Todos", "bloco": "Todos", "query": ""}))
        self.assertTrue(interfacetwo._filters_are_active({"status": "SEM CONTATO"}))
        self.assertTrue(interfacetwo._filters_are_active({"date_mode": "Específica", "date_value": "01/01/2026"}))

    def test_normalize_record_aliases_for_monitor(self):
        raw = {
            "nome": "Carlos",
            "sobrenome": "Souza",
            "bloco": "B",
            "apartamento": "202",
            "placa": "XYZ1234",
            "modelo": "Civic",
            "cor": "Prata",
            "status": "VISITANTE",
            "data_hora": "18/02/2026 11:22:33",
        }
        normalized = interfacetwo._normalize_record_for_monitor(raw)
        self.assertEqual(normalized.get("NOME"), "Carlos")
        self.assertEqual(normalized.get("SOBRENOME"), "Souza")
        self.assertEqual(normalized.get("BLOCO"), "B")
        self.assertEqual(normalized.get("APARTAMENTO"), "202")
        self.assertEqual(normalized.get("PLACA"), "XYZ1234")
        self.assertEqual(normalized.get("STATUS"), "VISITANTE")
        self.assertEqual(normalized.get("DATA_HORA"), "18/02/2026 11:22:33")

    def test_load_safe_accepts_dict_map_payload(self):
        import json, tempfile, os
        payload = {
            "1": {"nome": "ALICE", "bloco": "1", "apartamento": "101", "status": "MORADOR", "data_hora": "18/02/2026 10:00:00"},
            "2": {"nome": "BRUNO", "bloco": "2", "apartamento": "202", "status": "VISITANTE", "data_hora": "18/02/2026 10:05:00"},
        }
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0].get('NOME'), 'ALICE')
        self.assertEqual(registros[1].get('STATUS'), 'VISITANTE')

    def test_load_safe_accepts_wrapped_entries_payload(self):
        import json, tempfile, os
        payload = {
            "payload": {
                "entries": [
                    {"nome": "CARLA", "bloco": "3", "apartamento": "303", "status": "PRESTADOR", "data_hora": "18/02/2026 11:00:00"}
                ]
            }
        }
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0].get('NOME'), 'CARLA')
        self.assertEqual(registros[0].get('APARTAMENTO'), '303')

    def test_load_safe_accepts_utf8_bom_payload(self):
        import json, tempfile, os
        payload = [{"nome": "DANIEL", "bloco": "7", "apartamento": "707", "status": "MORADOR", "data_hora": "18/02/2026 12:00:00"}]
        with tempfile.NamedTemporaryFile('w', encoding='utf-8-sig', suffix='.json', delete=False) as tf:
            json.dump(payload, tf, ensure_ascii=False)
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0].get('NOME'), 'DANIEL')

    def test_load_safe_accepts_latin1_payload(self):
        import os, tempfile
        raw = '[{"nome":"JOSÉ","bloco":"8","apartamento":"808","status":"VISITANTE","data_hora":"18/02/2026 12:10:00"}]'
        with tempfile.NamedTemporaryFile('wb', suffix='.json', delete=False) as tf:
            tf.write(raw.encode('latin-1'))
            path = tf.name
        try:
            registros = interfacetwo._load_safe(path)
        finally:
            os.remove(path)
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0].get('NOME'), 'JOSÉ')


if __name__ == "__main__":
    unittest.main()
