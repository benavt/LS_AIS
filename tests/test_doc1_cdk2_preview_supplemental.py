"""The atlas accepts only intact projection/map outputs for its exact cohort."""

import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from scripts.doc1_cdk2.build_partial_preview import (
    SUPPLEMENTAL_PLAN, digest, load_supplemental,
)


class SupplementalPreviewTests(unittest.TestCase):
    def test_accepts_hash_verified_files_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'supplement'
            folder.mkdir()
            output = root / 'site'
            (output / 'figures').mkdir(parents=True)
            points = np.arange(10000, dtype=np.float32).reshape(5000, 2)
            for name, array in (
                ('pca-2d.npy', points), ('tsne-2d.npy', points + 1),
                ('median-sample-indices.npy', np.arange(5000)),
                ('median-ca-distances.npy', np.zeros((550, 550), dtype=np.float32)),
                ('variance-ca-distances.npy', np.zeros((550, 550), dtype=np.float32)),
            ):
                np.save(folder / name, array, allow_pickle=False)
            for name in ('median-ca-distances.png', 'variance-ca-distances.png'):
                (folder / name).write_bytes(b'\x89PNG\r\n\x1a\n')
            clustering = {'roster_sha256': 'a' * 64,
                          'geometry_matrix_sha256': 'b' * 64,
                          'sketch_sha256': 'c' * 64}
            receipt = {
                'status': 'validated', 'target': 'DOC1Rdimer_CDK2',
                'models': 5000, 'plan_sha256': SUPPLEMENTAL_PLAN,
                'full_construct_chain_lengths': [126, 126, 298],
                'median_sample_models': 5000, 'variance_models': 5000,
                'pca_explained_variance_ratio': [0.4, 0.3],
                'tsne_kl_divergence': 1.0,
                **clustering,
                'files': {path.name: digest(path) for path in folder.iterdir()},
            }
            (folder / 'acceptance.json').write_text(json.dumps(receipt))
            result = load_supplemental(folder, 'DOC1Rdimer_CDK2', 5000,
                                       clustering, output)
            self.assertEqual(result['pca']['x'][1], 2.0)
            self.assertEqual(result['tsne']['y'][1], 4.0)
            self.assertTrue((output / result['maps']['median']).is_file())

            with (folder / 'pca-2d.npy').open('ab') as stream:
                stream.write(b'tampered')
            with self.assertRaisesRegex(ValueError, 'SHA-256 mismatch'):
                load_supplemental(folder, 'DOC1Rdimer_CDK2', 5000,
                                  clustering, output)


if __name__ == '__main__':
    unittest.main()
