import importlib
import unittest


class TempCodeRunnerFileTests(unittest.TestCase):
    def test_module_imports_without_nameerror_for_os(self):
        module = importlib.import_module("tempCodeRunnerFile")
        self.assertTrue(hasattr(module, "os"))
        self.assertTrue(hasattr(module, "DADOSEND"))


if __name__ == "__main__":
    unittest.main()

