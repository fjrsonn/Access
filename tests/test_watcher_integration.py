import tempfile
import unittest
from unittest import mock

import main
import runtime_status


class _FakeAnalises:
    def __init__(self):
        self.calls = []

    def build_analises_for_identity(self, ident, dados, out):
        self.calls.append(("build_analises_for_identity", ident))

    def build_analises(self, dados, out):
        self.calls.append(("build_analises", None))


class _FakeAvisos:
    def __init__(self):
        self.calls = []

    def build_avisos_for_identity(self, ident, analises, out):
        self.calls.append(("build_avisos_for_identity", ident))

    def build_avisos(self, analises, out):
        self.calls.append(("build_avisos", None))


class WatcherIntegrationTests(unittest.TestCase):
    def test_watcher_detects_changes_and_emits_status(self):
        with tempfile.TemporaryDirectory() as td:
            runtime_status.EVENTS_FILE = f"{td}/events.jsonl"
            runtime_status.LAST_STATUS_FILE = f"{td}/last.json"

            fake_a = _FakeAnalises()
            fake_v = _FakeAvisos()

            sleep_count = {"n": 0}

            def controlled_sleep(_poll):
                sleep_count["n"] += 1
                if sleep_count["n"] >= 2:
                    raise StopIteration("encerrar watcher")

            # sequência de mtime: primeira leitura baseline, segunda leitura alterada
            mtime_values = [1.0, 1.0, 2.0, 1.0]

            def fake_getmtime(_path):
                return mtime_values.pop(0) if mtime_values else 2.0

            with mock.patch.object(main.os.path, "exists", return_value=True), \
                 mock.patch.object(main.os.path, "getmtime", side_effect=fake_getmtime), \
                 mock.patch.object(main, "_get_last_record_identity", return_value="ANA|SILVA|A|1"), \
                 mock.patch.object(main.time, "sleep", side_effect=controlled_sleep):
                with self.assertRaises(StopIteration):
                    main.watcher_thread(f"{td}/dadosend.json", fake_a, fake_v, poll=0.01)

            self.assertTrue(any(c[0] == "build_analises_for_identity" for c in fake_a.calls))
            self.assertTrue(any(c[0] == "build_avisos_for_identity" for c in fake_v.calls))
            events = runtime_status.read_runtime_events(runtime_status.EVENTS_FILE)
            self.assertTrue(any(e.get("action") == "watcher" for e in events))


if __name__ == "__main__":
    unittest.main()
