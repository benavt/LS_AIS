"""Measure all-pair signed-hash sketch fidelity on the accepted UMAP samples.

Every original pair-distance column contributes once to every projection. This
pilot does not fit or label the full model cohorts.
"""

import argparse
import hashlib
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


def sketch_map(pairs, dimensions, seed):
    import numpy as np
    from scipy.sparse import csr_matrix

    require(pairs > 0 and dimensions > 0, 'Invalid all-pair sketch shape')
    rng = np.random.default_rng(seed)
    buckets = rng.integers(0, dimensions, size=pairs, dtype=np.int32)
    signs = (rng.integers(0, 2, size=pairs, dtype=np.int8) * 2 - 1).astype(np.float32)
    projection = csr_matrix((signs, (np.arange(pairs), buckets)),
                            shape=(pairs, dimensions), dtype=np.float32)
    require(projection.nnz == pairs and
            (np.diff(projection.indptr) == 1).all(),
            'Every source pair must have exactly one signed destination')
    return projection, buckets, signs.astype(np.int8)


def fidelity(reference, projected, neighbors):
    import numpy as np
    from scipy.spatial.distance import pdist, squareform

    require(reference.shape[0] == projected.shape[0] and
            reference.shape[0] > neighbors + 1 and
            np.isfinite(reference).all() and np.isfinite(projected).all(),
            'Invalid paired fidelity sample')
    original = squareform(pdist(reference, metric='euclidean'))
    sketch = squareform(pdist(projected, metric='euclidean'))
    triangle = np.triu_indices(len(original), k=1)
    denominator = np.maximum(original[triangle], 1e-6)
    relative = np.abs(sketch[triangle] - original[triangle]) / denominator
    np.fill_diagonal(original, np.inf)
    np.fill_diagonal(sketch, np.inf)
    original_neighbors = np.argsort(original, axis=1, kind='stable')[:, :neighbors]
    sketch_neighbors = np.argsort(sketch, axis=1, kind='stable')[:, :neighbors]
    recall = [len(set(left) & set(right)) / neighbors
              for left, right in zip(original_neighbors, sketch_neighbors)]
    return {'comparison_pairs': len(relative),
            'relative_distance_error_median': float(np.median(relative)),
            'relative_distance_error_p95': float(np.quantile(relative, .95)),
            f'neighbor_recall_at_{neighbors}_mean': float(np.mean(recall)),
            f'neighbor_recall_at_{neighbors}_p10': float(np.quantile(recall, .1))}


def run(plan_path, plan_hash, target_index):
    import numpy as np

    require(digest(plan_path) == plan_hash, 'Frozen sketch pilot plan differs')
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_all_pair_sketch_fidelity_pilot' and
            plan['scientific_execution'] and plan['paid_external_calls'] == 0,
            'Wrong sketch pilot operation')
    require(digest(__file__) == plan['source_script_sha256'], 'Frozen sketch code differs')
    require(target_index in (0, 1), 'Exactly two target tasks are frozen')
    target = plan['targets'][target_index]
    geometry_path = Path(target['geometry_acceptance_path'])
    pilot_path = Path(target['direct_pilot_acceptance_path'])
    require(digest(geometry_path) == target['geometry_acceptance_sha256'] and
            digest(pilot_path) == target['direct_pilot_acceptance_sha256'],
            'Frozen geometry or direct-pilot receipt differs')
    geometry = json.loads(geometry_path.read_text())
    pilot = json.loads(pilot_path.read_text())
    require(geometry['status'] == pilot['status'] == 'validated' and
            geometry['target'] == pilot['target'] == target['id'] and
            geometry['shape'] == [target['models'], target['pairs']] and
            geometry['matrix_sha256'] == target['geometry_matrix_sha256'] and
            pilot['source_geometry_sha256'] == geometry['matrix_sha256'] and
            pilot['sample_models'] == plan['settings']['sample_models'] and
            pilot['full_pair_features'] == target['pairs'],
            'Accepted complete-pair sample identity differs')
    matrix_path = geometry_path.parent / 'pair-distances.f32'
    sample_path = pilot_path.parent / 'sample-indices.npy'
    require(matrix_path.stat().st_size == geometry['matrix_bytes'] and
            digest(matrix_path) == geometry['matrix_sha256'] and
            digest(sample_path) == pilot['sample_indices_sha256'],
            'Accepted matrix or deterministic sample differs')
    indices = np.load(sample_path, allow_pickle=False)
    require(indices.shape == (plan['settings']['sample_models'],) and
            np.array_equal(np.unique(indices), indices) and
            indices[0] >= 0 and indices[-1] < target['models'],
            'Invalid accepted sample indices')
    matrix = np.memmap(matrix_path, dtype='<f4', mode='r', shape=tuple(geometry['shape']))
    settings = plan['settings']
    require(settings['dimensions'] == [2048, 4096] and
            settings['evaluation_models'] == 256 and
            settings['neighbors'] == 15 and
            settings['seed'] == 42 and
            settings['block_models'] == 128,
            'Unreviewed all-pair fidelity settings')
    output = Path(plan['output_root']) / target['id']
    output.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(settings['seed'] + target_index)
    evaluation = np.sort(rng.choice(len(indices), settings['evaluation_models'], replace=False))
    np.save(output / 'evaluation-sample-positions.npy', evaluation, allow_pickle=False)
    reference = np.asarray(matrix[indices[evaluation]], dtype=np.float32)
    require(np.isfinite(reference).all(), 'Nonfinite original full-pair evaluation features')
    comparisons = []
    for dimensions in settings['dimensions']:
        projection, buckets, signs = sketch_map(target['pairs'], dimensions,
                                                 settings['seed'] + target_index)
        np.save(output / f'buckets-{dimensions}.npy', buckets, allow_pickle=False)
        np.save(output / f'signs-{dimensions}.npy', signs, allow_pickle=False)
        sketch_path = output / f'sketch-{dimensions}.f32'
        sketch = np.memmap(sketch_path, dtype='<f4', mode='w+',
                           shape=(len(indices), dimensions))
        for start in range(0, len(indices), settings['block_models']):
            end = min(len(indices), start + settings['block_models'])
            block = np.asarray(matrix[indices[start:end]], dtype=np.float32)
            require(np.isfinite(block).all(), 'Nonfinite original full-pair feature block')
            projected = np.asarray(block @ projection, dtype=np.float32)
            require(projected.shape == (end-start, dimensions) and
                    np.isfinite(projected).all(), 'Invalid all-pair projection block')
            sketch[start:end] = projected
        sketch.flush()
        scores = fidelity(reference, np.asarray(sketch[evaluation]), settings['neighbors'])
        del sketch
        row = {'dimensions': dimensions, 'all_pairs': target['pairs'],
               'sketch_sha256': digest(sketch_path),
               'buckets_sha256': digest(output / f'buckets-{dimensions}.npy'),
               'signs_sha256': digest(output / f'signs-{dimensions}.npy'), **scores}
        comparisons.append(row)
        print('all-pair sketch fidelity', target['id'], row, flush=True)
    summary = {'status': 'validated', 'target': target['id'],
               'plan_sha256': plan_hash, 'geometry_matrix_sha256': geometry['matrix_sha256'],
               'direct_pilot_acceptance_sha256': target['direct_pilot_acceptance_sha256'],
               'sample_models': len(indices), 'evaluation_models': len(evaluation),
               'evaluation_sample_sha256': digest(output / 'evaluation-sample-positions.npy'),
               'comparisons': comparisons,
               'scope': 'sampled fidelity only; no full-cohort projection or cluster claims'}
    (output / 'acceptance.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    run(args.plan, args.plan_sha256, int(os.environ['SLURM_ARRAY_TASK_ID']))


if __name__ == '__main__':
    main()
