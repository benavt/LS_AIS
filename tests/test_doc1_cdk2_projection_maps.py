import unittest


class ProjectionMapSummaries(unittest.TestCase):
    def test_full_cohort_variance_and_sample_median_remain_distinct(self):
        import numpy as np
        from scripts.doc1_cdk2.projection_maps import distance_summaries, symmetric_matrix

        # Four three-residue structures: the frozen median sample excludes the
        # largest distance, while the variance still includes that model.
        pairs = np.asarray([[1., 2., 3.], [2., 4., 6.],
                            [3., 6., 9.], [9., 18., 27.]], dtype=np.float32)
        median, variance = distance_summaries(pairs, np.array([0, 2]), 2)
        np.testing.assert_allclose(median, np.array([2., 4., 6.]))
        np.testing.assert_allclose(variance, np.var(pairs, axis=0, ddof=0))
        self.assertFalse(np.allclose(variance, np.var(pairs[[0, 2]], axis=0)))
        mapped = symmetric_matrix(median, 3)
        np.testing.assert_allclose(mapped, mapped.T)
        np.testing.assert_allclose(np.diag(mapped), 0)
        np.testing.assert_allclose(mapped[np.triu_indices(3, 1)], median)

    def test_rejects_duplicate_sample_indices(self):
        import numpy as np
        from scripts.doc1_cdk2.projection_maps import distance_summaries

        with self.assertRaisesRegex(ValueError, 'median sample'):
            distance_summaries(np.ones((4, 3), dtype=np.float32),
                               np.array([0, 0]), 2)


if __name__ == '__main__':
    unittest.main()
