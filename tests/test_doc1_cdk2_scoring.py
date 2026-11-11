"""Production scoring partitions preserve complete accepted cohort coverage."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/doc1_cdk2/proteinebm_production.py'
spec = importlib.util.spec_from_file_location('doc1_cdk2_production', SOURCE)
scoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring)
ACCEPT_SOURCE = SOURCE.with_name('accept_proteinebm.py')
accept_spec = importlib.util.spec_from_file_location('doc1_cdk2_accept_scoring', ACCEPT_SOURCE)
collector = importlib.util.module_from_spec(accept_spec)
accept_spec.loader.exec_module(collector)


class ScoringIntervals(unittest.TestCase):
    def test_both_accepted_rosters_are_covered_once(self):
        intervals = [scoring.chunk_intervals(count, 1000) for count in (57463, 75800)]
        self.assertEqual([len(part) for part in intervals], [58, 76])
        for count, parts in zip((57463, 75800), intervals):
            self.assertEqual(parts[0][0], 0)
            self.assertEqual(parts[-1][1], count)
            self.assertTrue(all(a[1] == b[0] for a, b in zip(parts, parts[1:])))
            self.assertEqual(sum(end - start for start, end in parts), count)

    def test_roster_chunk_rejects_missing_input_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'roster.jsonl'
            path.write_text(''.join(json.dumps({'model_id': str(i)}) + '\n' for i in range(3)))
            self.assertEqual([row['model_id'] for row in scoring.load_rows(path, 1, 3, 3)],
                             ['1', '2'])
            with self.assertRaisesRegex(ValueError, 'cardinality'):
                scoring.load_rows(path, 1, 3, 4)

    def test_collector_joins_every_energy_to_the_native_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audit = root / 'audit'
            audit.mkdir()
            roster = audit / 'roster.jsonl'
            roster.write_text(''.join(json.dumps({'model_id': f'm{i}', 'method': 'af3',
                                                   'native_sha256': f'h{i}'}) + '\n'
                                      for i in range(2)))
            config = root / 'target.json'
            config.write_text(json.dumps({'chains': [{'residues': 3}]}))
            output = root / 'output/example'
            chunks = []
            for index in range(2):
                folder = output / f'chunk-{index:03d}'
                folder.mkdir(parents=True)
                grid = folder / 'energy-grid.npz'
                energy = np.full((1, 16), float(index + 3), dtype=np.float32)
                partial = np.repeat((energy / 3)[:, :, None], 3, axis=-1)
                np.savez(grid, energy=energy, per_residue_energy=partial,
                         times=np.linspace(0, 0.15, 16), model_ids=np.array([f'm{index}']),
                         native_sha256=np.array([f'h{index}']))
                (folder / 'acceptance.json').write_text(json.dumps({
                    'status': 'validated', 'plan_sha256': '', 'target': 'example',
                    'chunk_index': index, 'start': index, 'end': index + 1, 'models': 1,
                    'energy_values': 16, 'residues': 3, 'grid_sha256': collector.digest(grid)}))
                chunks.append({'target_index': 0, 'chunk_index': index,
                               'start': index, 'end': index + 1})
            plan = {'operation': 'doc1_cdk2_proteinebm_complete_rosters',
                    'collector_script_sha256': collector.digest(ACCEPT_SOURCE),
                    'output_root': str(root / 'output'), 'chunks': chunks,
                    'targets': [{'id': 'example', 'audit_path': str(audit / 'audit.json'),
                                 'roster_sha256': collector.digest(roster),
                                 'config_path': str(config), 'validated_models': 2}]}
            plan_path = root / 'plan.json'
            plan_path.write_text(json.dumps(plan))
            plan_hash = collector.digest(plan_path)
            for index in range(2):
                receipt_path = output / f'chunk-{index:03d}/acceptance.json'
                receipt = json.loads(receipt_path.read_text())
                receipt['plan_sha256'] = plan_hash
                receipt_path.write_text(json.dumps(receipt))
            collector.accept(plan_path, plan_hash)
            import csv
            with (output / 'energy-rankings.csv').open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([(row['model_id'], row['native_sha256']) for row in rows],
                             [('m0', 'h0'), ('m1', 'h1')])
            self.assertEqual(json.loads((output / 'acceptance.json').read_text())['energy_values'], 32)


if __name__ == '__main__':
    unittest.main()
