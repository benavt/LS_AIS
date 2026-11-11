"""Production scoring partitions preserve complete accepted cohort coverage."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / 'scripts/doc1_cdk2/proteinebm_production.py'
spec = importlib.util.spec_from_file_location('doc1_cdk2_production', SOURCE)
scoring = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoring)


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


if __name__ == '__main__':
    unittest.main()
