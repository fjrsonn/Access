import os
import tempfile
import unittest

import runtime_status


class RuntimeStatusTests(unittest.TestCase):
    def test_report_and_get_last_status(self):
        with tempfile.TemporaryDirectory() as td:
            events = os.path.join(td, "events.jsonl")
            last = os.path.join(td, "last.json")

            old_events = runtime_status.EVENTS_FILE
            old_last = runtime_status.LAST_STATUS_FILE
            runtime_status.EVENTS_FILE = events
            runtime_status.LAST_STATUS_FILE = last
            try:
                runtime_status.report_status("user_input", "ok", stage="classification", details={"destino": "dados"})
                payload = runtime_status.get_last_status()
            finally:
                runtime_status.EVENTS_FILE = old_events
                runtime_status.LAST_STATUS_FILE = old_last

            self.assertEqual(payload.get("action"), "user_input")
            self.assertEqual(payload.get("status"), "OK")
            self.assertEqual(payload.get("stage"), "classification")
            self.assertEqual(payload.get("details", {}).get("destino"), "dados")


if __name__ == "__main__":
    unittest.main()
