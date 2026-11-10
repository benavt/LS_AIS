"""Validate only project source and the saved hash roster; never run science."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    atlas = json.loads((ROOT / 'config/atlas-project.json').read_text())
    registry = json.loads((ROOT / 'config/targets.json').read_text())
    assert atlas['project'] == registry['project'] == 'LS_AIS'
    assert atlas['visibility'] == registry['visibility'] == 'private'
    ids = [entry['id'] for entry in registry['targets']]
    assert ids and len(ids) == len(set(ids))
    for entry in registry['targets']:
        target_config = json.loads((ROOT / entry['config']).read_text())
        assert target_config['id'] == entry['id']
    study = json.loads((ROOT / 'config/study.json').read_text())
    roster_path = ROOT / 'config/model-roster.json'
    roster = json.loads(roster_path.read_text())
    rows = roster['models']
    assert hashlib.sha256(roster_path.read_bytes()).hexdigest() == study['available_snapshot']['roster_sha256']
    assert len(rows) == len({r['model_id'] for r in rows}) == len({r['sha256'] for r in rows}) == study['available_snapshot']['models']
    assert dict(collections.Counter(r['method'] for r in rows)) == study['available_snapshot']['methods']
    target = study['target']
    assert len(target['sequence']) == target['residues_per_chain'] == 117
    assert target['copies'] == 2 and target['chains'] == ['A', 'B']
    assert hashlib.sha256(target['sequence'].encode()).hexdigest() == target['sequence_sha256']
    assert study['requested_additions'] == {'afsample3': 1000, 'bioemu2': 1000}
    coverage = json.loads((ROOT / 'config/workflow-coverage.json').read_text())
    assert coverage['cohort_models'] == len(rows)
    assert coverage['model_roster_sha256'] == study['available_snapshot']['roster_sha256']
    assert coverage['authoritative_skill']['commit'] == study['library_commit']
    spec = json.loads((ROOT / 'config/target-spec.json').read_text())
    assert spec['analysis']['alternative_clusterings'] == ['HDBSCAN']
    assert spec['analysis']['sampling']['methods'] == ['MCMC', 'DISCO']
    incomplete = [r for r in coverage['requirements'] if r['status'] != 'verified']
    if incomplete:
        assert not coverage['release_ready'] and coverage['publication_hold']
        assert study['publication']['hold']
    assert study['publication']['hold'] and study['publication']['status'] in {'held_incomplete_workflow', 'private_atlas_reviewed_publication_separate'}
    print(json.dumps(dict(status='source_and_roster_verified', project='LS_AIS', targets=ids, private=True, available_models=len(rows),
                          requested_arm_models=2000, remaining_models=study['requested_total']-len(rows),
                          workflow_status=coverage['status'], incomplete_requirements=len(incomplete),
                          publication_held=coverage['publication_hold'], check_runs_science=False)))

if __name__ == '__main__':
    main()

