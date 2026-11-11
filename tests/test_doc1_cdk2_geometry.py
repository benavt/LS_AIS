"""Complete three-chain geometry retains every requested C-alpha position."""

import importlib.util
from pathlib import Path
import unittest

import numpy as np
from scipy.spatial.distance import pdist


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/doc1_cdk2/geometry_features.py'
spec = importlib.util.spec_from_file_location('doc1_cdk2_geometry', SOURCE)
geometry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(geometry)


def atom(serial, chain, xyz):
    x, y, z = xyz
    return (f'ATOM  {serial:5d}  CA  ALA {chain}{1:4d}    '
            f'{x:8.3f}{y:8.3f}{z:8.3f}{1.0:6.2f}{50.0:6.2f}           C\n').encode()


class CompleteGeometry(unittest.TestCase):
    def setUp(self):
        self.chains = [{'id': chain, 'residues': 1} for chain in 'ABC']
        self.raw = b''.join((atom(1, 'A', (0, 0, 0)),
                             atom(2, 'B', (3, 0, 0)),
                             atom(3, 'C', (0, 4, 0))))

    def test_all_three_chains_and_condensed_pair_order(self):
        coords = geometry.ca_coordinates(self.raw, self.chains)
        self.assertEqual(coords.shape, (3, 3))
        np.testing.assert_allclose(pdist(coords), [3, 4, 5])

    def test_missing_chain_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            geometry.ca_coordinates(self.raw.replace(atom(3, 'C', (0, 4, 0)), b''), self.chains)


if __name__ == '__main__':
    unittest.main()
