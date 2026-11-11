"""Three-chain intake invariants for the new CDK2 atlas targets."""

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
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

    def test_frozen_empty_source_is_excluded_without_dropping_valid_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'inputs/example'
            (source / 'pdb').mkdir(parents=True)
            (source / 'pdb/valid_1.pdb').write_bytes(self.raw)
            (source / 'pdb/empty_2.pdb').write_bytes(b'')
            entries = [
                {'name': 'valid_1.pdb', 'bytes': len(self.raw), 'sha256': validator.sha(self.raw)},
                {'name': 'empty_2.pdb', 'bytes': 0, 'sha256': validator.sha(b'')},
            ]
            listing = source / 'pdb-sha256.jsonl'
            listing.write_text(''.join(json.dumps(entry) + '\n' for entry in entries))
            (source / 'acceptance.json').write_text(json.dumps({
                'status': 'validated', 'archive_sha256': 'archive', 'manifest_sha256': validator.sha_file(listing),
                'models': 2,
            }))
            config = root / 'target.json'
            config.write_text(json.dumps({
                'id': 'example', 'chains': self.chains,
                'cohort': {'archive_sha256': 'archive', 'expected_models': 2,
                           'source_exclusions': [{'name': 'empty_2.pdb', 'sha256': validator.sha(b''),
                                                  'bytes': 0, 'reason': 'zero-byte source PDB'}]},
            }))
            result = validator.validate(config, root, root / 'result')
            self.assertEqual((result['status'], result['validated_models'], result['excluded_models']),
                             ('validated', 1, 1))
            self.assertEqual(json.loads((root / 'result/roster.jsonl').read_text())['model_id'], 'valid_1')
            self.assertEqual((root / 'result/rejections.jsonl').read_text(), '')


if __name__ == '__main__':
    unittest.main()
