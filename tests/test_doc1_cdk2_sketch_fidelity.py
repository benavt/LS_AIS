"""The optional all-pair sketch accounts for every feature exactly once."""

import importlib.util
from pathlib import Path
import unittest

import numpy as np


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/doc1_cdk2/sketch_fidelity_pilot.py'
spec = importlib.util.spec_from_file_location('doc1_cdk2_sketch_pilot', SOURCE)
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


class AllPairSketch(unittest.TestCase):
    def test_every_pair_has_one_signed_bucket_and_seed_is_reproducible(self):
        first, buckets, signs = pilot.sketch_map(17, 5, 42)
        second, repeat_buckets, repeat_signs = pilot.sketch_map(17, 5, 42)
        np.testing.assert_array_equal(np.diff(first.indptr), np.ones(17))
        np.testing.assert_array_equal(buckets, repeat_buckets)
        np.testing.assert_array_equal(signs, repeat_signs)
        np.testing.assert_array_equal(first.toarray(), second.toarray())
        self.assertEqual(set(map(int, signs)), {-1, 1})
        vector = np.arange(1, 18, dtype=np.float32)
        expected = np.bincount(buckets, weights=vector * signs, minlength=5)
        np.testing.assert_array_equal(vector @ first, expected)

    def test_identical_geometry_has_exact_fidelity_even_with_ties(self):
        features = np.array([[0., 0.], [0., 0.], [1., 0.],
                             [0., 1.], [2., 2.]], dtype=np.float32)
        result = pilot.fidelity(features, features.copy(), 2)
        self.assertEqual(result['relative_distance_error_p95'], 0.)
        self.assertEqual(result['neighbor_recall_at_2_mean'], 1.)


if __name__ == '__main__':
    unittest.main()
