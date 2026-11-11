"""Hash-frozen fidelity pilot for symmetric DOC1/CDK2 A/B terminal masks.

This scientific job only evaluates saved accepted models. It does not submit
jobs, alter native PDBs, or produce full-cohort cluster labels.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def frozen_module(name, path, expected_sha256):
    require(digest(path) == expected_sha256, 'Frozen source differs: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_columns(chain_lengths, first_retained):
    """Condensed-pdist columns with both endpoints in A/B core or all C."""
    import numpy as np

    require(len(chain_lengths) == 3 and chain_lengths[0] == chain_lengths[1],
            'Expected identical-length A/B chains and C')
    a, _, c = chain_lengths
    require(1 < first_retained <= a, 'Invalid one-based A/B starting residue')
    residues = 2 * a + c
    selected = np.zeros(residues, dtype=bool)
    selected[first_retained - 1:a] = True
    selected[a + first_retained - 1:2 * a] = True
    selected[2 * a:] = True
    row, col = np.triu_indices(residues, 1)
    columns = np.flatnonzero(selected[row] & selected[col]).astype(np.int32)
    kept = 2 * (a - first_retained + 1) + c
    require(len(columns) == kept * (kept - 1) // 2 and
            np.array_equal(columns, np.unique(columns)),
            'Incomplete or repeated retained pair columns')
    return columns, row[columns], col[columns]


def nearest_neighbors(reference, count):
    import numpy as np
    from scipy.spatial.distance import pdist, squareform

    distance = squareform(pdist(reference, metric='euclidean'))
    np.fill_diagonal(distance, np.inf)
    return np.argsort(distance, axis=1, kind='stable')[:, :count]


def compare_neighbors(left, right):
    import numpy as np

    require(left.shape == right.shape, 'Neighbor comparison shape differs')
    return float(np.mean([len(set(a) & set(b)) / len(a)
                          for a, b in zip(left, right)]))


def run(plan_path, plan_sha256, target_index):
    import numpy as np
    from scipy.spatial.distance import pdist

    require(digest(plan_path) == plan_sha256, 'Frozen subset pilot plan differs')
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_ab_core_sketch_fidelity' and
            plan['scientific_execution'] is True and
            plan['paid_external_calls'] == 0 and target_index in (0, 1),
            'Wrong scientific operation or target')
    require(digest(__file__) == plan['source_script_sha256'], 'Pilot code differs')
    settings = plan['settings']
    require(settings == {'sample_models': 5000, 'evaluation_models': 256,
                         'neighbors': 15, 'sketch_dimensions': 4096,
                         'sketch_seed': 42, 'block_models': 64,
                         'required_neighbor_recall': 0.95,
                         'maximum_p95_relative_error': 0.03},
            'Unreviewed pilot settings')
    target = plan['targets'][target_index]
    geometry_path = Path(target['geometry_acceptance_path'])
    pilot_path = Path(target['direct_pilot_acceptance_path'])
    fidelity_path = Path(target['full_fidelity_acceptance_path'])
    roster_path = Path(target['roster_path'])
    config_path = Path(target['config_path'])
    for path, expected in ((geometry_path, target['geometry_acceptance_sha256']),
                           (pilot_path, target['direct_pilot_acceptance_sha256']),
                           (fidelity_path, target['full_fidelity_acceptance_sha256']),
                           (roster_path, target['roster_sha256']),
                           (config_path, target['config_sha256'])):
        require(digest(path) == expected, 'Frozen input hash differs: ' + str(path))
    geometry = json.loads(geometry_path.read_text())
    pilot = json.loads(pilot_path.read_text())
    fidelity = json.loads(fidelity_path.read_text())
    config = json.loads(config_path.read_text())
    count = target['models']
    chains = target['chain_lengths']
    full_pairs = sum(chains) * (sum(chains) - 1) // 2
    require(geometry['status'] == pilot['status'] == fidelity['status'] == 'validated' and
            geometry['target'] == pilot['target'] == fidelity['target'] ==
            config['id'] == target['id'] and
            geometry['shape'] == [count, full_pairs] and
            geometry['matrix_sha256'] == pilot['source_geometry_sha256'] ==
            fidelity['geometry_matrix_sha256'] == target['matrix_sha256'] and
            geometry['roster_sha256'] == target['roster_sha256'] and
            geometry['pair_order'] == 'scipy pdist condensed upper triangle' and
            pilot['sample_indices_sha256'] == target['sample_indices_sha256'] and
            fidelity['evaluation_sample_sha256'] == target['evaluation_positions_sha256'] and
            [(c['id'], c['residues']) for c in config['chains']] ==
            list(zip('ABC', chains)), 'Accepted source identity differs')
    matrix_path = geometry_path.parent / 'pair-distances.f32'
    sample_path = pilot_path.parent / 'sample-indices.npy'
    evaluation_path = fidelity_path.parent / 'evaluation-sample-positions.npy'
    require(matrix_path.stat().st_size == geometry['matrix_bytes'] and
            digest(matrix_path) == target['matrix_sha256'] and
            digest(sample_path) == target['sample_indices_sha256'] and
            digest(evaluation_path) == target['evaluation_positions_sha256'],
            'Accepted complete matrix or sample bytes differ')
    sample = np.load(sample_path, allow_pickle=False)
    evaluation = np.load(evaluation_path, allow_pickle=False)
    require(sample.shape == (5000,) and evaluation.shape == (256,) and
            np.array_equal(sample, np.unique(sample)) and
            np.array_equal(evaluation, np.unique(evaluation)) and
            sample[0] >= 0 and sample[-1] < count and
            evaluation[0] >= 0 and evaluation[-1] < len(sample),
            'Invalid accepted sample indexes')
    sketch_module = frozen_module('frozen_sketch', plan['sketch_source_path'],
                                  plan['sketch_source_sha256'])
    geometry_module = frozen_module('frozen_geometry', plan['geometry_source_path'],
                                    plan['geometry_source_sha256'])
    matrix = np.memmap(matrix_path, mode='r', dtype='<f4', shape=(count, full_pairs))
    roster = [json.loads(line) for line in roster_path.read_text().splitlines()]
    require(len(roster) == count and len({row['model_id'] for row in roster}) == count,
            'Accepted roster count or IDs differ')
    output = Path(plan['output_root']) / target['id']
    output.mkdir(parents=True, exist_ok=False)
    starts = target['candidate_first_retained']
    require(starts == sorted(set(starts)) and
            target['primary_first_retained'] in starts and len(starts) == 3,
            'Wrong pilot masks')
    reports = []
    baseline_neighbors = None
    for first in starts:
        columns, endpoint_i, endpoint_j = selected_columns(chains, first)
        prefix = output / ('first-' + str(first))
        prefix.mkdir()
        np.save(prefix / 'pair-columns.npy', columns, allow_pickle=False)
        # Verify selected source columns against native coordinates in three
        # distant roster positions, including both chain boundaries.
        for model_index in (0, count // 2, count - 1):
            row = roster[model_index]
            raw = Path(row['path']).read_bytes()
            require(hashlib.sha256(raw).hexdigest() == row['native_sha256'],
                    'Native PDB hash differs during pair verification')
            xyz = geometry_module.ca_coordinates(raw, config['chains'])
            direct = np.linalg.norm(xyz[endpoint_i] - xyz[endpoint_j], axis=1)
            require(np.allclose(direct, matrix[model_index, columns],
                                rtol=2e-6, atol=2e-4),
                    'Masked column map differs from native C-alpha distances')
        reference = np.asarray(matrix[np.ix_(sample[evaluation], columns)],
                               dtype=np.float32)
        require(np.isfinite(reference).all(), 'Nonfinite selected distances')
        exact_neighbors = nearest_neighbors(reference, settings['neighbors'])
        projection, buckets, signs = sketch_module.sketch_map(
            len(columns), settings['sketch_dimensions'],
            settings['sketch_seed'] + target_index)
        np.save(prefix / 'buckets.npy', buckets, allow_pickle=False)
        np.save(prefix / 'signs.npy', signs, allow_pickle=False)
        sketch_path = prefix / 'sketch.f32'
        sketch = np.memmap(sketch_path, mode='w+', dtype='<f4',
                           shape=(len(sample), settings['sketch_dimensions']))
        for block_start in range(0, len(sample), settings['block_models']):
            block_end = min(len(sample), block_start + settings['block_models'])
            values = np.asarray(matrix[np.ix_(sample[block_start:block_end], columns)],
                                dtype=np.float32)
            require(np.isfinite(values).all(), 'Nonfinite pilot pair block')
            sketch[block_start:block_end] = values @ projection
        sketch.flush()
        scores = sketch_module.fidelity(reference,
                                        np.asarray(sketch[evaluation]),
                                        settings['neighbors'])
        exact_overlap = None if baseline_neighbors is None else compare_neighbors(
            baseline_neighbors, exact_neighbors)
        if first == target['primary_first_retained']:
            baseline_neighbors = exact_neighbors
        report = {'first_retained': first, 'pairs': len(columns),
                  'pair_columns_sha256': digest(prefix / 'pair-columns.npy'),
                  'buckets_sha256': digest(prefix / 'buckets.npy'),
                  'signs_sha256': digest(prefix / 'signs.npy'),
                  'sketch_sha256': digest(sketch_path),
                  'exact_neighbor_overlap_with_previous_primary': exact_overlap,
                  **scores}
        report['fidelity_pass'] = (
            scores['neighbor_recall_at_15_mean'] >= settings['required_neighbor_recall']
            and scores['relative_distance_error_p95'] <=
            settings['maximum_p95_relative_error'])
        reports.append(report)
        del sketch
        print(target['id'], first, report, flush=True)
    # The starts are ascending and the primary is central; compare both
    # neighboring masks to that primary exact-neighbor partition.
    primary = next(row for row in reports if row['first_retained'] ==
                   target['primary_first_retained'])
    primary_columns, _, _ = selected_columns(chains, target['primary_first_retained'])
    primary_reference = np.asarray(matrix[np.ix_(sample[evaluation], primary_columns)],
                                   dtype=np.float32)
    primary_neighbors = nearest_neighbors(primary_reference, settings['neighbors'])
    for row in reports:
        columns, _, _ = selected_columns(chains, row['first_retained'])
        other = np.asarray(matrix[np.ix_(sample[evaluation], columns)], dtype=np.float32)
        row['exact_neighbor_overlap_with_primary'] = compare_neighbors(
            primary_neighbors, nearest_neighbors(other, settings['neighbors']))
        row.pop('exact_neighbor_overlap_with_previous_primary')
    receipt = {'status': 'validated' if primary['fidelity_pass'] else 'fidelity_failed',
               'target': target['id'], 'plan_sha256': plan_sha256,
               'models': count, 'sample_models': len(sample),
               'evaluation_models': len(evaluation),
               'roster_sha256': target['roster_sha256'],
               'geometry_matrix_sha256': target['matrix_sha256'],
               'sample_indices_sha256': target['sample_indices_sha256'],
               'evaluation_positions_sha256': target['evaluation_positions_sha256'],
               'primary_first_retained': target['primary_first_retained'],
               'masks': reports, 'scope': 'A/B terminal masks, C complete; sampled fidelity only'}
    (output / 'acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    require(primary['fidelity_pass'], 'Primary subset projection failed fidelity gate')
    print(json.dumps(receipt, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    run(args.plan, args.plan_sha256, int(os.environ['SLURM_ARRAY_TASK_ID']))


if __name__ == '__main__':
    main()
