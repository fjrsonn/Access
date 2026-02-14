import sys
import unittest
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
REGRESSION_DIR = THIS_DIR / "regression"
if str(REGRESSION_DIR) not in sys.path:
    sys.path.insert(0, str(REGRESSION_DIR))

import run_regression


class RegressionDatasetTests(unittest.TestCase):
    def test_regression_dataset_matches_baseline(self):
        current = run_regression.run_cases()
        ok, _baseline = run_regression.check_against_baseline(current)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
