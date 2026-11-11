"""Bound direct full-distance UMAP feasibility before the complete atlas fits."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def run(plan_path, plan_hash, target_index):
    import numpy as np
    import umap

    require(digest(plan_path) == plan_hash, 'Frozen clustering pilot plan differs')
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_direct_full_distance_umap_feasibility' and
            plan['scientific_execution'] and plan['paid_external_calls'] == 0,
            'Wrong clustering pilot operation')
    require(digest(__file__) == plan['source_script_sha256'], 'Frozen pilot code differs')
    require(target_index in (0, 1), 'Exactly two target tasks are frozen')
    target = plan['targets'][target_index]
    receipt_path = Path(target['geometry_acceptance_path'])
    require(digest(receipt_path) == target['geometry_acceptance_sha256'],
            'Accepted geometry receipt differs')
    geometry = json.loads(receipt_path.read_text())
    require(geometry['status'] == 'validated' and
            geometry['target'] == target['id'] and
            geometry['models'] == target['models'] and
            geometry['pairs_per_model'] == target['pairs'] and
            geometry['shape'] == [target['models'], target['pairs']] and
            geometry['roster_sha256'] == target['roster_sha256'] and
            geometry['dtype'] == 'float32 little-endian' and
            geometry['pair_order'] == 'scipy pdist condensed upper triangle' and
            geometry['scope'] == 'complete native A/B/C complex',
            'Complete geometry identity differs')
    matrix_path = receipt_path.parent / 'pair-distances.f32'
    require(matrix_path.stat().st_size == geometry['matrix_bytes'] and
            digest(matrix_path) == geometry['matrix_sha256'],
            'Full pair-distance matrix differs')
    matrix = np.memmap(matrix_path, dtype='<f4', mode='r', shape=tuple(geometry['shape']))
    require(0 < plan['settings']['sample_models'] <= target['models'],
            'Invalid feasibility sample size')
    require(plan['settings']['dimensions'] == [2, 10] and
            plan['settings']['n_neighbors'] == 30 and
            plan['settings']['min_dist'] == 0 and
            plan['settings']['seed'] == 42,
            'Unreviewed UMAP feasibility settings')
    rng = np.random.default_rng(plan['settings']['seed'])
    indices = np.sort(rng.choice(target['models'], plan['settings']['sample_models'], replace=False))
    features = np.asarray(matrix[indices], dtype=np.float32)
    require(features.shape == (plan['settings']['sample_models'], target['pairs']) and
            np.isfinite(features).all(), 'Sampled full-distance features are incomplete')
    output = Path(plan['output_root']) / target['id']
    output.mkdir(parents=True, exist_ok=False)
    np.save(output / 'sample-indices.npy', indices, allow_pickle=False)
    fits = []
    for dimension in plan['settings']['dimensions']:
        started = time.monotonic()
        coords = umap.UMAP(n_components=dimension,
                           n_neighbors=plan['settings']['n_neighbors'],
                           min_dist=plan['settings']['min_dist'],
                           metric='euclidean', random_state=plan['settings']['seed'],
                           n_jobs=1, low_memory=True).fit_transform(features)
        seconds = time.monotonic() - started
        require(coords.shape == (len(indices), dimension) and np.isfinite(coords).all(),
                'Direct full-distance UMAP pilot fit failed')
        file = output / f'umap-{dimension}d.npy'
        np.save(file, coords, allow_pickle=False)
        fits.append({'dimensions': dimension, 'seconds': seconds,
                     'embedding_sha256': digest(file)})
        print('direct UMAP pilot', target['id'], dimension, 'D', round(seconds, 2), 's', flush=True)
    summary = {'status': 'validated', 'target': target['id'], 'plan_sha256': plan_hash,
               'source_geometry_sha256': geometry['matrix_sha256'],
               'sample_models': len(indices), 'full_pair_features': target['pairs'],
               'sample_indices_sha256': digest(output / 'sample-indices.npy'),
               'fits': fits,
               'scope': 'performance feasibility sample only; no full-cohort cluster claims'}
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
