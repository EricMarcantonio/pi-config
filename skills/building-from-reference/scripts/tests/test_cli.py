import json
import os
import shutil
import tempfile
import unittest

from woodbuild import cli_main

try:                                    # `python3 -m unittest tests.test_cli`
    from tests.woodbuild_spec_fixture import SPEC
except ImportError:                     # discovered with tests/ itself on the path
    from woodbuild_spec_fixture import SPEC  # type: ignore


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.spec_path = os.path.join(self.dir, "spec.json")
        with open(self.spec_path, "w") as fh:
            json.dump(SPEC, fh)
        self.prices = os.path.join(self.dir, "prices.json")
        with open(self.prices, "w") as fh:
            json.dump({"store": "7011", "province": "ON", "fetched": "2026-09-12",
                       "items": {"2x4": {"price": 4.25, "sku": "222",
                                         "source": "hd_search"}}}, fh)
        self.out = os.path.join(self.dir, "out")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_run_produces_workbook_and_reports_numbers(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.out, "budget.html")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "cart.csv")))

    def test_invalid_spec_returns_two(self):
        bad = json.loads(json.dumps(SPEC))
        bad["roof"]["build_up"] = 171.0
        with open(self.spec_path, "w") as fh:
            json.dump(bad, fh)
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out])
        self.assertEqual(rc, 2)

    def test_missing_prices_file_is_offline_but_not_fatal(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices + ".nope",
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertIn("unpriced", open(os.path.join(self.out, "budget.html")).read())

    def test_compare_prints_delta(self):
        old = os.path.join(self.dir, "old.json")
        with open(old, "w") as fh:
            json.dump({"items": {"2x4": {"price": 3.99}}}, fh)
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--compare", old, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.out, "price-deltas.txt")))


if __name__ == "__main__":
    unittest.main()
