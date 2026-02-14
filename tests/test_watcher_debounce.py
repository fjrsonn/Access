import tempfile
import unittest
from unittest import mock

import main


class _FakeAnalises:
    def __init__(self):
        self.calls = 0

    def build_analises_for_identity(self, ident, dados, out):
        self.calls += 1

    def build_analises(self, dados, out):
        self.calls += 1


class _FakeAvisos:
    def __init__(self):
        self.calls = 0

    def build_avisos_for_identity(self, ident, analises, out):
        self.calls += 1

    def build_avisos(self, analises, out):
        self.calls += 1


class WatcherDebounceTests(unittest.TestCase):
    def test_watcher_coalesces_burst_changes(self):
        with tempfile.TemporaryDirectory() as td:
            fake_a = _FakeAnalises()
            fake_v = _FakeAvisos()
            mtime_values = [1.0, 1.0, 2.0, 2.1, 2.2, 2.2, 2.2, 2.2]
            tick = {"n": 0}

            def fake_time():
                tick["n"] += 1
                return tick["n"] * 0.05

            def fake_sleep(_poll):
                if tick["n"] > 8:
                    raise StopIteration("end")

            def fake_getmtime(_):
                return mtime_values.pop(0) if mtime_values else 2.2

            with mock.patch.object(main.os.path, "exists", return_value=True), \
                 mock.patch.object(main.os.path, "getmtime", side_effect=fake_getmtime), \
                 mock.patch.object(main, "_get_last_record_identity", return_value="A|B|C|1"), \
                 mock.patch.object(main.time, "time", side_effect=fake_time), \
                 mock.patch.object(main.time, "sleep", side_effect=fake_sleep):
                with self.assertRaises(StopIteration):
                    main.watcher_thread(f"{td}/dadosend.json", fake_a, fake_v, poll=0.01, debounce_window=0.15)

            self.assertEqual(fake_a.calls, 1)
            self.assertEqual(fake_v.calls, 1)


if __name__ == "__main__":
    unittest.main()
