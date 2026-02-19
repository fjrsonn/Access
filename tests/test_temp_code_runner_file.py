import importlib
import importlib.util
import os
import unittest


class TempCodeRunnerFileTests(unittest.TestCase):
    def test_module_imports_without_nameerror_for_os(self):
        try:
            module = importlib.import_module("tempCodeRunnerFile")
        except ModuleNotFoundError:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            module_path = os.path.join(base_dir, "tempCodeRunnerFile.py")
            spec = importlib.util.spec_from_file_location("tempCodeRunnerFile", module_path)
            self.assertIsNotNone(spec)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
        self.assertTrue(hasattr(module, "os"))
        self.assertTrue(hasattr(module, "DADOSEND"))


if __name__ == "__main__":
    unittest.main()
