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


class _FakeEntryWidget(_FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = ""

    def insert(self, _idx, text):
        self.value = str(text)

    def get(self):
        return self.value


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
            Entry=_FakeEntryWidget,
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
        self.assertEqual(app.btn_sim.kwargs.get("text"), "Simulador")

    def test_simulator_runs_records_and_logs_ok(self):
        root = _FakeRoot()

        fake_interfaceone = types.SimpleNamespace(HAS_IA_MODULE=True)

        def _save_text(entry_widget=None, btn=None):
            if entry_widget is not None:
                entry_widget.delete(0, "end")

        fake_interfaceone.save_text = _save_text
        fake_ia = types.SimpleNamespace(processar=lambda: None)

        with self._patch_tk(), \
             mock.patch.object(main_tests.app_main, "initialize_system", return_value=None), \
             mock.patch.object(main_tests.TestPanelApp, "_load_records", return_value=["A B C", "D E F"]), \
             mock.patch.object(main_tests.time, "sleep", return_value=None), \
             mock.patch.dict("sys.modules", {"interfaceone": fake_interfaceone, "ia": fake_ia}):
            app = main_tests.TestPanelApp(
                root,
                status_store=_FakeStore(),
                test_loader=mock.Mock(discover=mock.Mock(return_value=object())),
                test_runner_factory=lambda stream: _FakeRunner(stream),
                thread_factory=lambda target: _FakeThread(target),
            )
            app.entry_tpm.insert(0, "120")
            app.start_simulator()

        joined = "".join(app.text.buffer)
        self.assertIn("Simulador iniciado", joined)
        self.assertIn("[OK] #1/2", joined)
        self.assertIn("[OK] #2/2", joined)
        self.assertIn("Simulador finalizado", joined)

    def test_pause_and_resume_update_status(self):
        root = _FakeRoot()
        with self._patch_tk(),              mock.patch.object(main_tests.app_main, "initialize_system", return_value=None):
            app = main_tests.TestPanelApp(
                root,
                status_store=_FakeStore(),
                test_loader=mock.Mock(discover=mock.Mock(return_value=object())),
                test_runner_factory=lambda stream: _FakeRunner(stream),
                thread_factory=lambda target: _FakeThread(target),
            )
            app._sim_running = True
            app._sim_total = 10
            app._sim_index = 4
            app._sim_current_record = "REG TESTE"
            app.pause_simulator()
            self.assertTrue(app._sim_pause_requested)
            self.assertEqual(app.btn_resume.kwargs.get("state"), "normal")
            app.resume_simulator()
            self.assertFalse(app._sim_pause_requested)
            self.assertEqual(app.btn_pause.kwargs.get("state"), "normal")


if __name__ == "__main__":
    unittest.main()
