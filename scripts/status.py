"""Validate only project source and the saved hash roster; never run science."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    study = json.loads((ROOT / 'config/study.json').read_text())
    roster_path = ROOT / 'config/model-roster.json'
    roster = json.loads(roster_path.read_text())
    rows = roster['models']
    assert hashlib.sha256(roster_path.read_bytes()).hexdigest() == study['available_snapshot']['roster_sha256']
    assert len(rows) == len({r['model_id'] for r in rows}) == len({r['sha256'] for r in rows}) == 4000
    assert dict(collections.Counter(r['method'] for r in rows)) == study['available_snapshot']['methods']
    target = study['target']
    assert len(target['sequence']) == target['residues_per_chain'] == 117
    assert target['copies'] == 2 and target['chains'] == ['A', 'B']
    assert hashlib.sha256(target['sequence'].encode()).hexdigest() == target['sequence_sha256']
    assert study['requested_additions'] == {'afsample3': 1000, 'bioemu2': 1000}
    assert study['publication']['status'] == 'not_published'
    print(json.dumps(dict(status='source_and_roster_verified', available_models=len(rows),
                          requested_additional_models=2000, science_executed=False)))

if __name__ == '__main__':
    main()

