import types
import unittest
from unittest import mock

import main_tests


class _FakeWidget:
    def __init__(self, *args, **kwargs):
        self.kwargs = dict(kwargs)

    def pack(self, **_kwargs):
        return None

    def config(self, **kwargs):
        self.kwargs.update(kwargs)

    configure = config

    def start(self, *_args, **_kwargs):
        self.kwargs["started"] = True

    def stop(self, *_args, **_kwargs):
        self.kwargs["started"] = False


class _FakeText(_FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.buffer = []

    def insert(self, _where, text):
        self.buffer.append(text)

    def see(self, _where):
        return None


class _FakeRoot:
    def __init__(self):
        self.after_calls = []

    def title(self, _):
        return None

    def geometry(self, _):
        return None

    def after(self, ms, fn, *args):
        self.after_calls.append((fn, args))
        if ms == 0:
            fn(*args)


class _FakeStore:
    def __init__(self, payload=None):
        self.payload = payload or {}

    def get_last_status(self):
        return self.payload


class _FakeResult:
    testsRun = 1
    failures = []
    errors = []

    def wasSuccessful(self):
        return True


class _FakeRunner:
    def __init__(self, stream):
        self.stream = stream

    def run(self, _suite):
        self.stream.write("fake_test ... ok\n")
        return _FakeResult()


class _FakeThread:
    def __init__(self, target):
        self.target = target

    def start(self):
        self.target()


class UISmokeTests(unittest.TestCase):
    def _patch_tk(self):
        fake_ttk = types.SimpleNamespace(
            Frame=_FakeWidget,
            Button=_FakeWidget,
            Label=_FakeWidget,
            Progressbar=_FakeWidget,
        )
        return mock.patch.multiple(main_tests, tk=types.SimpleNamespace(Text=_FakeText), ttk=fake_ttk)

    def test_panel_start_runs_smoke_flow(self):
        root = _FakeRoot()
        store = _FakeStore({"timestamp": "2026-01-10 10:00:00", "action": "ui", "status": "OK", "stage": "smoke", "details": {}})

        fake_loader = mock.Mock()
        fake_loader.discover.return_value = object()

        with self._patch_tk(), \
             mock.patch.object(main_tests.app_main, "initialize_system", return_value=None):
            app = main_tests.TestPanelApp(
                root,
                status_store=store,
                test_loader=fake_loader,
                test_runner_factory=lambda stream: _FakeRunner(stream),
                thread_factory=lambda target: _FakeThread(target),
            )
            app._poll_runtime_status()
            app.start()

        joined = "".join(app.text.buffer)
        self.assertIn("[RUNTIME]", joined)
        self.assertIn("fake_test ... ok", joined)
        self.assertEqual(app.lbl_status.kwargs.get("text"), "Concluído com sucesso")


if __name__ == "__main__":
    unittest.main()
