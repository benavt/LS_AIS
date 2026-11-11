"""Three-chain intake invariants for the new CDK2 atlas targets."""

import hashlib
import importlib.util
from pathlib import Path
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/doc1_cdk2/validate_roster.py'
spec = importlib.util.spec_from_file_location('doc1_cdk2_roster', SOURCE)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def row(serial, chain, number, aa):
    return (f'ATOM  {serial:5d}  CA  {aa:3s} {chain}{number:4d}    '
            f'{float(number):8.3f}{0.0:8.3f}{0.0:8.3f}{1.0:6.2f}{50.0:6.2f}           C\n').encode()


class ThreeChainRoster(unittest.TestCase):
    def setUp(self):
        self.raw = b''.join([row(1, 'A', 1, 'ALA'), row(2, 'A', 2, 'GLY'),
                             row(3, 'B', 1, 'ALA'), row(4, 'B', 2, 'GLY'),
                             row(5, 'C', 1, 'LYS')])
        self.chains = [
            {'id': 'A', 'residues': 2, 'sequence_sha256': hashlib.sha256(b'AG').hexdigest()},
            {'id': 'B', 'residues': 2, 'sequence_sha256': hashlib.sha256(b'AG').hexdigest()},
            {'id': 'C', 'residues': 1, 'sequence_sha256': hashlib.sha256(b'K').hexdigest()},
        ]

    def test_complete_three_chain_complex(self):
        self.assertEqual(validator.inspect_pdb(self.raw, self.chains), {'A': 'AG', 'B': 'AG', 'C': 'K'})

    def test_missing_chain_residue_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            validator.inspect_pdb(self.raw.replace(row(4, 'B', 2, 'GLY'), b''), self.chains)

    def test_sequence_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'sequence differs'):
            validator.inspect_pdb(self.raw.replace(row(5, 'C', 1, 'LYS'), row(5, 'C', 1, 'ALA')), self.chains)


if __name__ == '__main__':
    unittest.main()
