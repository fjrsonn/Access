import json
import os
import tempfile
import unittest

import runtime_status


class _NonSerializable:
    pass


class TelemetryAnalysisTests(unittest.TestCase):
    def test_stage_order_and_non_serializable_details(self):
        with tempfile.TemporaryDirectory() as td:
            events = os.path.join(td, "events.jsonl")
            last = os.path.join(td, "last.json")
            runtime_status.EVENTS_FILE = events
            runtime_status.LAST_STATUS_FILE = last

            runtime_status.report_status("user_input", "STARTED", stage="save_text", details={"obj": _NonSerializable()})
            runtime_status.report_status("user_input", "OK", stage="saved_dadosinit", details={"id": 1})

            evs = runtime_status.read_runtime_events(events)
            self.assertGreaterEqual(len(evs), 2)
            self.assertEqual(evs[0].get("status"), "STARTED")
            self.assertEqual(evs[1].get("status"), "OK")
            # details serializado em string quando não serializável
            self.assertIsInstance(evs[0].get("details"), str)

    def test_analisar_saude_pipeline(self):
        with tempfile.TemporaryDirectory() as td:
            events = os.path.join(td, "events.jsonl")
            rows = [
                {"timestamp": "2026-01-10 10:00:00", "action": "ia_pipeline", "status": "STARTED", "stage": "process_registro", "details": {}},
                {"timestamp": "2026-01-10 10:00:01", "action": "ia_pipeline", "status": "ERROR", "stage": "llm_call_failed", "details": {"error": "timeout"}},
                {"timestamp": "2026-01-10 10:00:02", "action": "db_append", "status": "STARTED", "stage": "prepare_record", "details": {}},
                {"timestamp": "2026-01-10 10:00:03", "action": "db_append", "status": "OK", "stage": "persisted", "details": {}},
            ]
            with open(events, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")

            out = runtime_status.analisar_saude_pipeline(events)
            self.assertEqual(out["total_events"], 4)
            self.assertIn("llm_call_failed", out["error_rate_by_stage"])
            self.assertTrue(len(out["top_5_errors"]) >= 1)

    def test_detectar_conflitos_e_relatorio(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "dadosinit.json"), "w", encoding="utf-8") as f:
                json.dump({"registros": [{"id": 1, "processado": True}]}, f)
            with open(os.path.join(td, "dadosend.json"), "w", encoding="utf-8") as f:
                json.dump({"registros": [{"_entrada_id": 2, "NOME": "ONIX", "MODELO": "ONIX", "ID": 99}]}, f)
            with open(os.path.join(td, "encomendasend.json"), "w", encoding="utf-8") as f:
                json.dump({"registros": [{"ID": 5, "STATUS_ENCOMENDA": "INVALIDO"}]}, f)
            with open(os.path.join(td, "analises.json"), "w", encoding="utf-8") as f:
                json.dump({"registros": [{"identidade": "ANA|SILVA|A|1"}], "encomendas_multiplas_bloco_apartamento": []}, f)
            with open(os.path.join(td, "avisos.json"), "w", encoding="utf-8") as f:
                json.dump({"registros": [{"identidade": "X|Y|Z|1"}]}, f)

            events = os.path.join(td, "events.jsonl")
            with open(events, "w", encoding="utf-8") as f:
                f.write(json.dumps({"timestamp": "2099-01-01 10:00:00", "action": "watcher", "status": "ERROR", "stage": "build_analises_full", "details": {"error": "x"}}) + "\n")

            conflitos = runtime_status.detectar_conflitos_dados(td)
            self.assertIn(1, conflitos["processed_without_saida"])
            self.assertTrue(conflitos["avisos_sem_analise"])
            self.assertTrue(conflitos["nome_modelo_conflicts"])
            self.assertTrue(conflitos["status_encomenda_conflicts"])

            rel = runtime_status.gerar_relatorio_diagnostico_diario(td, events)
            self.assertIn("suggestions", rel)


if __name__ == "__main__":
    unittest.main()
