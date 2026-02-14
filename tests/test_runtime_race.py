import multiprocessing as mp
import os
import tempfile
import threading
import unittest

import runtime_status


def _writer_proc(events_path: str, last_path: str, n: int):
    import runtime_status as rs
    rs.EVENTS_FILE = events_path
    rs.LAST_STATUS_FILE = last_path
    for i in range(n):
        rs.report_status("proc_writer", "STARTED" if i % 2 == 0 else "OK", stage="loop", details={"i": i})


class RuntimeRaceTests(unittest.TestCase):
    def test_multithread_runtime_events(self):
        with tempfile.TemporaryDirectory() as td:
            runtime_status.EVENTS_FILE = os.path.join(td, "events.jsonl")
            runtime_status.LAST_STATUS_FILE = os.path.join(td, "last.json")

            def worker(base):
                for i in range(50):
                    runtime_status.report_status("thread_writer", "OK", stage="t", details={"i": base + i})

            threads = [threading.Thread(target=worker, args=(k * 100,)) for k in range(6)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            evs = runtime_status.read_runtime_events(runtime_status.EVENTS_FILE)
            self.assertGreaterEqual(len(evs), 300)
            self.assertTrue(runtime_status.get_last_status())

    def test_multiprocess_runtime_events(self):
        with tempfile.TemporaryDirectory() as td:
            events = os.path.join(td, "events.jsonl")
            last = os.path.join(td, "last.json")
            procs = [mp.Process(target=_writer_proc, args=(events, last, 40)) for _ in range(4)]
            for p in procs:
                p.start()
            for p in procs:
                p.join(timeout=10)
            for p in procs:
                self.assertEqual(p.exitcode, 0)

            evs = runtime_status.read_runtime_events(events)
            self.assertGreaterEqual(len(evs), 120)


if __name__ == "__main__":
    unittest.main()
