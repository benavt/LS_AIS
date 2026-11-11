"""Check that subset columns retain exactly the intended A/B/C pairs."""

import importlib.util
from pathlib import Path
import unittest

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/doc1_cdk2/subset_sketch_pilot.py'
SPEC = importlib.util.spec_from_file_location('subset_sketch_pilot', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SubsetColumns(unittest.TestCase):
    def test_proposed_masks_match_condensed_pair_order(self):
        for chains, first, expected in (([126, 126, 298], 65, 88831),
                                        ([115, 115, 298], 60, 83845)):
            with self.subTest(chains=chains):
                columns, left, right = MODULE.selected_columns(chains, first)
                self.assertEqual(len(columns), expected)
                self.assertTrue(np.all(np.diff(columns) > 0))
                self.assertTrue(np.all(left < right))
                self.assertTrue(np.all((left >= chains[0] * 2) |
                                       (left % chains[0] >= first - 1)))
                self.assertTrue(np.all((right >= chains[0] * 2) |
                                       (right % chains[0] >= first - 1)))
                n = sum(chains)
                expected_columns = left * (2 * n - left - 1) // 2 + right - left - 1
                np.testing.assert_array_equal(columns, expected_columns)

    def test_rejects_non_symmetric_chain_lengths(self):
        with self.assertRaises(ValueError):
            MODULE.selected_columns([126, 115, 298], 65)


if __name__ == '__main__':
    unittest.main()
