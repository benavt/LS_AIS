"""Accept complete native ProteinEBM score coverage for both DOC1/CDK2 rosters."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def accept(plan_path, plan_hash):
    import numpy as np

    require(digest(plan_path) == plan_hash, 'Frozen plan hash differs')
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_proteinebm_complete_rosters',
            'Wrong acceptance operation')
    require(digest(__file__) == plan['collector_script_sha256'],
            'Frozen collector code hash differs')
    root = Path(plan['output_root'])
    by_target = {target['id']: [] for target in plan['targets']}
    for chunk in plan['chunks']:
        by_target[plan['targets'][chunk['target_index']]['id']].append(chunk)
    for target in plan['targets']:
        target_id = target['id']
        roster = Path(target['audit_path']).parent / 'roster.jsonl'
        require(digest(roster) == target['roster_sha256'], 'Accepted roster hash differs')
        output = root / target_id
        csv_path = output / 'energy-rankings.csv'
        seen_ids, grids = set(), []
        total, energy_values = 0, 0
        with roster.open() as roster_stream, csv_path.open('x', newline='') as stream:
            expected = (json.loads(line) for line in roster_stream)
            fields = ['model_id', 'method', 'native_sha256', 'protein_ebm_energy_t010'] + [
                f'energy_t{level:02d}' for level in range(16)]
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for chunk in by_target[target_id]:
                folder = output / ('chunk-%03d' % chunk['chunk_index'])
                receipt_path = folder / 'acceptance.json'
                receipt = json.loads(receipt_path.read_text())
                require(receipt['status'] == 'validated' and
                        receipt['plan_sha256'] == plan_hash and
                        receipt['target'] == target_id and
                        receipt['chunk_index'] == chunk['chunk_index'] and
                        (receipt['start'], receipt['end']) == (chunk['start'], chunk['end']) and
                        receipt['models'] == chunk['end'] - chunk['start'],
                        'Missing or mismatched scoring chunk')
                grid = folder / 'energy-grid.npz'
                require(digest(grid) == receipt['grid_sha256'], 'Scoring grid hash differs')
                with np.load(grid, allow_pickle=False) as payload:
                    values = payload['energy']
                    partials = payload['per_residue_energy']
                    names = payload['model_ids']
                    hashes = payload['native_sha256']
                    times = payload['times']
                    require(values.shape == (receipt['models'], 16) and
                            partials.shape == (receipt['models'], 16, receipt['residues']) and
                            names.shape == hashes.shape == (receipt['models'],) and
                            np.isfinite(values).all() and np.isfinite(partials).all() and
                            np.allclose(partials.sum(-1), values, rtol=2e-6, atol=2e-5) and
                            np.allclose(times, np.linspace(0, 0.15, 16), atol=2e-8, rtol=0),
                            'Native scoring grid is incomplete or inconsistent')
                    for index in range(receipt['models']):
                        source = next(expected, None)
                        require(source is not None and
                                source['model_id'] == str(names[index]) and
                                source['native_sha256'] == str(hashes[index]) and
                                source['model_id'] not in seen_ids,
                                'Scoring model ID or native hash differs from accepted roster')
                        seen_ids.add(source['model_id'])
                        row = {'model_id': source['model_id'], 'method': source['method'],
                               'native_sha256': source['native_sha256'],
                               'protein_ebm_energy_t010': float(values[index, 10])}
                        row.update({f'energy_t{level:02d}': float(values[index, level])
                                    for level in range(16)})
                        writer.writerow(row)
                    total += receipt['models']
                    energy_values += receipt['energy_values']
                grids.append({'chunk_index': chunk['chunk_index'],
                              'receipt_sha256': digest(receipt_path),
                              'grid_sha256': receipt['grid_sha256']})
            require(next(expected, None) is None and total == target['validated_models'] and
                    energy_values == 16 * total, 'Incomplete full-roster score coverage')
        summary = {'status': 'validated', 'target': target_id,
                   'models': total, 'energy_values': energy_values,
                   'residues': sum(c['residues'] for c in json.loads(Path(target['config_path']).read_text())['chains']),
                   'primary_time_index': 10, 'primary_t': 0.10,
                   'plan_sha256': plan_hash, 'roster_sha256': target['roster_sha256'],
                   'csv_sha256': digest(csv_path), 'chunks': grids,
                   'units': 'learned arbitrary units; not binding energy'}
        (output / 'acceptance.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps({key: value for key, value in summary.items() if key != 'chunks'},
                         sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    accept(args.plan, args.plan_sha256)


if __name__ == '__main__':
    main()
