"""Select DOC1/CDK2 cluster representatives by accepted ProteinEBM energy.

This scientific selection runs only under an approved, hash-frozen plan. It
performs no structural comparisons, scoring, clustering, or publication.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


LABEL_FILES = {
    'leaf': 'hdbscan-leaf-seed-42.npz',
    'eom': 'hdbscan-eom-seed-42.npz',
    'knn': 'umap-knn-labels.npy',
}
ENERGY_FIELDS = ['model_id', 'method', 'native_sha256',
                 'protein_ebm_energy_t010'] + [f'energy_t{i:02d}' for i in range(16)]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(path, expected):
    require(sha256(path) == expected, f'SHA-256 mismatch: {Path(path).name}')


def load_plan(path, expected):
    checked(path, expected)
    plan = json.loads(Path(path).read_text())
    require(plan['operation'] == 'doc1_cdk2_energy_cluster_representatives'
            and plan['scientific_execution'] is True
            and plan['public_export'] is False
            and plan['paid_external_calls'] == 0
            and plan['selection_policy'] == 'minimum accepted full-complex '
                'ProteinEBM Model 6 t=0.10 energy per assigned cluster; '
                'tie by lexicographic model ID; preserve five lowest-energy '
                'members and up to five lowest-energy unassigned examples'
            and len(plan['targets']) == 2 and len(plan['views']) == 12,
            'Unexpected selection plan')
    checked(__file__, plan['source_sha256'])
    checked(sys.executable, plan['runtime_python_sha256'])
    plan['_sha256'] = expected
    return plan


def load_target(target):
    for key in ('roster', 'model_index', 'energy_csv', 'energy_receipt'):
        checked(target[key + '_path'], target[key + '_sha256'])
    receipt = json.loads(Path(target['energy_receipt_path']).read_text())
    require((receipt['status'], receipt['target'], receipt['models'],
             receipt['roster_sha256'], receipt['csv_sha256'],
             receipt['primary_time_index'], receipt['primary_t']) ==
            ('validated', target['id'], target['models'],
             target['roster_sha256'], target['energy_csv_sha256'], 10, 0.10),
            'Accepted ProteinEBM identity differs')
    roster = [json.loads(line) for line in Path(target['roster_path']).open()]
    index = [json.loads(line) for line in Path(target['model_index_path']).open()]
    require(len(roster) == len(index) == target['models'], 'Model count differs')
    require(len({row['model_id'] for row in roster}) == len(roster),
            'Duplicate native model ID')
    models = []
    with Path(target['energy_csv_path']).open(newline='') as stream:
        reader = csv.DictReader(stream)
        require(reader.fieldnames == ENERGY_FIELDS, 'Energy columns differ')
        for i, row in enumerate(reader):
            require(i < len(roster), 'Excess energy rows')
            native = roster[i]
            entry = index[i]
            require((row['model_id'], row['method'], row['native_sha256']) ==
                    (native['model_id'], native['method'], native['native_sha256'])
                    and (entry['index'], entry['model_id'], entry['native_sha256']) ==
                    (i, native['model_id'], native['native_sha256']),
                    f'Energy/native/index identity differs at row {i}')
            energy = float(row['protein_ebm_energy_t010'])
            require(math.isfinite(energy) and energy == float(row['energy_t10']),
                    f'Invalid primary energy at row {i}')
            models.append({'model_id': native['model_id'],
                           'method': native['method'],
                           'native_sha256': native['native_sha256'],
                           'protein_ebm_full_complex_energy_t010': energy})
    require(len(models) == target['models'], 'Incomplete energy coverage')
    return models


def select_view(view, models):
    for key in ('labels', 'clustering_receipt'):
        checked(view[key + '_path'], view[key + '_sha256'])
    receipt = json.loads(Path(view['clustering_receipt_path']).read_text())
    require(receipt['status'] == 'validated' and
            receipt['target'] == view['target'] and
            receipt['models'] == len(models), 'Cluster acceptance differs')
    labels_path = Path(view['labels_path'])
    require(labels_path.name == LABEL_FILES[view['partition']],
            'Cluster partition filename differs')
    if view['partition'] == 'knn':
        labels = np.load(labels_path, allow_pickle=False)
    else:
        with np.load(labels_path, allow_pickle=False) as fit:
            labels = fit['labels']
    require(labels.ndim == 1 and len(labels) == len(models) and
            np.issubdtype(labels.dtype, np.integer), 'Cluster labels differ')
    groups = {}
    unassigned = []
    for label, model in zip(labels, models):
        label = int(label)
        if label == -1:
            unassigned.append(model)
        else:
            require(label >= 0, 'Unexpected negative cluster label')
            groups.setdefault(label, []).append(model)
    require(len(groups) == view['assigned_clusters'] and
            len(unassigned) == view['unassigned_models'],
            'Accepted cluster counts differ')
    order = lambda row: (row['protein_ebm_full_complex_energy_t010'],
                         row['model_id'])
    clusters = []
    for label, members in sorted(groups.items()):
        best = sorted(members, key=order)[:5]
        clusters.append({'cluster': label, 'size': len(members),
                         'representative': best[0],
                         'lowest_energy_members': best})
    return {'status': 'validated', 'operation': 'energy_cluster_representatives',
            'view': view['id'], 'target': view['target'],
            'range': view['range'], 'partition': view['partition'],
            'first_retained_ab': view['first_retained_ab'],
            'models': len(models), 'assigned_clusters': len(groups),
            'unassigned_models': len(unassigned),
            'selection_policy': 'minimum full-complex ProteinEBM Model 6 t=0.10 energy; tie by model ID',
            'score_units': 'learned arbitrary units; not physical binding energy or confidence',
            'geometry_centrality': 'not assessed; these are energy-selected representatives, not medoids',
            'labels_sha256': view['labels_sha256'],
            'clustering_receipt_sha256': view['clustering_receipt_sha256'],
            'clusters': clusters,
            'unassigned_examples': sorted(unassigned, key=order)[:5]}


def run(plan):
    output = Path(plan['output_root'])
    require(not output.exists(), 'Selection output already exists')
    target_models = {target['id']: load_target(target) for target in plan['targets']}
    selections = []
    for view in plan['views']:
        selection = select_view(view, target_models[view['target']])
        selection['plan_sha256'] = plan['_sha256']
        selections.append(selection)
    output.mkdir(parents=True)
    rows = []
    file_hashes = {}
    for selection in selections:
        path = output / f"{selection['view']}.json"
        path.write_text(json.dumps(selection, indent=2) + '\n')
        file_hashes[path.name] = sha256(path)
        for group in selection['clusters']:
            model = group['representative']
            rows.append({'view': selection['view'], 'target': selection['target'],
                         'range': selection['range'], 'partition': selection['partition'],
                         'cluster': group['cluster'], 'size': group['size'],
                         **model})
    csv_path = output / 'energy-selected-representatives.csv'
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    file_hashes[csv_path.name] = sha256(csv_path)
    acceptance = {'status': 'validated', 'operation': plan['operation'],
                  'plan_sha256': plan['_sha256'], 'representatives': len(rows),
                  'views': len(selections), 'files': file_hashes,
                  'rmsd_comparisons': 0, 'paid_external_calls': 0}
    (output / 'acceptance.json').write_text(json.dumps(acceptance, indent=2) + '\n')
    print(json.dumps({'receipt_sha256': sha256(output / 'acceptance.json'),
                      **acceptance}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    run(load_plan(args.plan, args.plan_sha256))
