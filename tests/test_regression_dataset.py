import unittest

from tests.regression import run_regression


class RegressionDatasetTests(unittest.TestCase):
    def test_regression_dataset_matches_baseline(self):
        current = run_regression.run_cases()
        ok, _baseline = run_regression.check_against_baseline(current)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
