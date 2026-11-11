"""Identity and diagnostic checks for full DOC1/CDK2 cluster acceptance."""

import json
from pathlib import Path
import sys
import tempfile
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts' / 'doc1_cdk2'))
from full_clustering import load_roster, seed_agreement  # noqa: E402


class FullClusteringTests(unittest.TestCase):
    def test_roster_preserves_exact_order_and_rejects_duplicate_ids(self):
        rows = [{'model_id': 'model-b', 'native_sha256': 'b' * 64},
                {'model_id': 'model-a', 'native_sha256': 'a' * 64}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'roster.jsonl'
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            ids, hashes = load_roster(path, 2)
            self.assertEqual(ids, ['model-b', 'model-a'])
            self.assertEqual(hashes, ['b' * 64, 'a' * 64])
            rows[1]['model_id'] = 'model-b'
            path.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            with self.assertRaisesRegex(ValueError, 'Invalid accepted model roster'):
                load_roster(path, 2)

    def test_seed_agreement_retains_noise_diagnostics(self):
        import numpy as np

        report = seed_agreement(np.array([0, 0, 1, -1]),
                                np.array([1, 1, -1, -1]))
        self.assertEqual(report['jointly_assigned_models'], 2)
        self.assertEqual(report['jointly_assigned_fraction'], .5)
        self.assertEqual(report['noise_status_agreement'], .75)
        self.assertIsNotNone(report['ari_including_noise'])


if __name__ == '__main__':
    unittest.main()
