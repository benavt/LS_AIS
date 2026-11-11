"""Fit both atlas clustering views on every accepted DOC1/CDK2 model.

The signed sketch covers every full-construct A/B/C C-alpha pair. ProteinEBM
energies are deliberately absent from these geometry-only fits.
"""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def import_frozen(name, path, expected_hash):
    require(digest(path) == expected_hash, 'Frozen dependency differs: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_roster(path, expected_count):
    entries = [json.loads(line) for line in Path(path).read_text().splitlines()]
    ids = [row['model_id'] for row in entries]
    hashes = [row['native_sha256'] for row in entries]
    require(len(entries) == expected_count and len(set(ids)) == expected_count and
            all(len(value) == 64 for value in hashes), 'Invalid accepted model roster')
    return ids, hashes


def seed_agreement(base, candidate):
    import numpy as np
    from sklearn.metrics import adjusted_rand_score

    jointly = (base >= 0) & (candidate >= 0)
    return {'ari_including_noise': float(adjusted_rand_score(base, candidate)),
            'jointly_assigned_models': int(jointly.sum()),
            'jointly_assigned_fraction': float(jointly.mean()),
            'ari_jointly_assigned': (float(adjusted_rand_score(base[jointly], candidate[jointly]))
                                     if jointly.sum() >= 2 else None),
            'noise_status_agreement': float(np.mean((base < 0) == (candidate < 0)))}


def run(plan_path, plan_hash, target_index):
    import numpy as np
    import umap
    from sklearn.cluster import HDBSCAN

    require(digest(plan_path) == plan_hash, 'Frozen full-clustering plan differs')
    plan = json.loads(Path(plan_path).read_text())
    settings = plan['settings']
    require(plan['operation'] == 'doc1_cdk2_full_geometry_clustering' and
            plan['scientific_execution'] and plan['paid_external_calls'] == 0 and
            target_index in (0, 1), 'Wrong full-clustering operation or target')
    require(digest(__file__) == plan['source_script_sha256'], 'Frozen clustering code differs')
    require(settings == {'sketch_dimensions': 4096, 'sketch_seed': 42,
                         'block_models': 128, 'umap_neighbors': 30,
                         'umap_min_dist': 0, 'umap_seeds': [42, 7, 123],
                         'hdbscan_min_cluster_size': 15,
                         'hdbscan_min_samples': 11,
                         'hdbscan_workers': 8}, 'Unreviewed clustering settings')
    sketch_module = import_frozen('frozen_sketch', plan['sketch_source_path'],
                                  plan['sketch_source_sha256'])
    knn_module = import_frozen('frozen_umap_knn', plan['knn_source_path'],
                               plan['knn_source_sha256'])
    target = plan['targets'][target_index]
    geometry_path = Path(target['geometry_acceptance_path'])
    fidelity_path = Path(target['fidelity_acceptance_path'])
    direct_pilot_path = Path(target['direct_pilot_acceptance_path'])
    roster_path = Path(target['roster_path'])
    require(digest(geometry_path) == target['geometry_acceptance_sha256'] and
            digest(fidelity_path) == target['fidelity_acceptance_sha256'] and
            digest(direct_pilot_path) == target['direct_pilot_acceptance_sha256'] and
            digest(roster_path) == target['roster_sha256'],
            'Frozen accepted source receipt or roster differs')
    geometry = json.loads(geometry_path.read_text())
    fidelity = json.loads(fidelity_path.read_text())
    count, pairs = target['models'], target['pairs']
    require(geometry['status'] == fidelity['status'] == 'validated' and
            geometry['target'] == fidelity['target'] == target['id'] and
            geometry['shape'] == [count, pairs] and
            geometry['roster_sha256'] == target['roster_sha256'] and
            geometry['matrix_sha256'] == target['geometry_matrix_sha256'] and
            fidelity['geometry_matrix_sha256'] == geometry['matrix_sha256'] and
            fidelity['direct_pilot_acceptance_sha256'] == target['direct_pilot_acceptance_sha256'] and
            fidelity['plan_sha256'] == plan['fidelity_plan_sha256'] and
            geometry['scope'] == 'complete native A/B/C complex',
            'Accepted full-construct geometry or fidelity identity differs')
    comparison = next(row for row in fidelity['comparisons']
                      if row['dimensions'] == settings['sketch_dimensions'])
    require(comparison['all_pairs'] == pairs, 'Pilot sketch scope differs')
    ids, native_hashes = load_roster(roster_path, count)
    matrix_path = geometry_path.parent / 'pair-distances.f32'
    require(matrix_path.stat().st_size == geometry['matrix_bytes'] and
            digest(matrix_path) == geometry['matrix_sha256'],
            'Full pair-distance matrix differs')
    matrix = np.memmap(matrix_path, dtype='<f4', mode='r', shape=(count, pairs))
    output = Path(plan['output_root']) / target['id']
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'model-index.jsonl').open('x') as stream:
        for index, (model_id, native_hash) in enumerate(zip(ids, native_hashes)):
            stream.write(json.dumps({'index': index, 'model_id': model_id,
                                     'native_sha256': native_hash}) + '\n')

    projection, buckets, signs = sketch_module.sketch_map(
        pairs, settings['sketch_dimensions'], settings['sketch_seed'] + target_index)
    np.save(output / 'buckets.npy', buckets, allow_pickle=False)
    np.save(output / 'signs.npy', signs, allow_pickle=False)
    require(digest(output / 'buckets.npy') == comparison['buckets_sha256'] and
            digest(output / 'signs.npy') == comparison['signs_sha256'],
            'Full-cohort sketch mapping differs from approved fidelity pilot')
    sketch_path = output / 'all-pair-sketch.f32'
    sketch = np.memmap(sketch_path, dtype='<f4', mode='w+',
                       shape=(count, settings['sketch_dimensions']))
    started = time.monotonic()
    for start in range(0, count, settings['block_models']):
        end = min(count, start + settings['block_models'])
        block = np.asarray(matrix[start:end], dtype=np.float32)
        require(np.isfinite(block).all(), 'Nonfinite complete-pair features')
        projected = np.asarray(block @ projection, dtype=np.float32)
        require(projected.shape == (end - start, settings['sketch_dimensions']) and
                np.isfinite(projected).all(), 'Invalid full-cohort sketch block')
        sketch[start:end] = projected
        if end % 10000 < settings['block_models']:
            sketch.flush()
            print('sketch', target['id'], end, 'of', count, flush=True)
    sketch.flush()
    sketch_seconds = time.monotonic() - started
    del matrix
    sample_path = Path(target['direct_pilot_acceptance_path']).parent / 'sample-indices.npy'
    pilot_sketch_path = fidelity_path.parent / 'sketch-4096.f32'
    require(digest(sample_path) == target['sample_indices_sha256'] and
            digest(pilot_sketch_path) == comparison['sketch_sha256'],
            'Accepted fidelity sample differs')
    sample_indices = np.load(sample_path, allow_pickle=False)
    pilot_sketch = np.memmap(pilot_sketch_path, dtype='<f4', mode='r',
                             shape=(len(sample_indices), settings['sketch_dimensions']))
    require(np.array_equal(np.asarray(sketch[sample_indices]), np.asarray(pilot_sketch)),
            'Full-cohort sketch disagrees with accepted 5,000-model pilot')
    del pilot_sketch
    sketch_hash = digest(sketch_path)
    print('sketch validated', target['id'], round(sketch_seconds, 1), 's', flush=True)

    fits = []
    embeddings = {}
    for dimension, seed in [(2, 42), (10, 42), (10, 7), (10, 123)]:
        started = time.monotonic()
        embedding = umap.UMAP(n_components=dimension,
                              n_neighbors=settings['umap_neighbors'],
                              min_dist=settings['umap_min_dist'], metric='euclidean',
                              random_state=seed, n_jobs=1, low_memory=True).fit_transform(sketch)
        require(embedding.shape == (count, dimension) and
                np.isfinite(embedding).all(), 'Invalid full-cohort UMAP embedding')
        path = output / f'umap-{dimension}d-seed-{seed}.npy'
        np.save(path, embedding, allow_pickle=False)
        embeddings[(dimension, seed)] = embedding
        fits.append({'dimensions': dimension, 'seed': seed,
                     'seconds': time.monotonic() - started,
                     'embedding_sha256': digest(path)})
        print('UMAP', target['id'], dimension, seed,
              round(fits[-1]['seconds'], 1), 's', flush=True)

    primary, report = knn_module.find_umap_knn_clusters(
        embeddings[(2, 42)], projection='umap')
    require(primary.shape == (count,) and np.issubdtype(primary.dtype, np.integer),
            'Invalid full-cohort UMAP KNN labels')
    np.save(output / 'umap-knn-labels.npy', primary, allow_pickle=False)
    (output / 'umap-knn-selection.json').write_text(json.dumps(report, indent=2) + '\n')
    density = []
    labels = {}
    for seed in settings['umap_seeds']:
        embedding = embeddings[(10, seed)]
        for method in ('leaf', 'eom'):
            started = time.monotonic()
            fitted = HDBSCAN(min_cluster_size=settings['hdbscan_min_cluster_size'],
                             min_samples=settings['hdbscan_min_samples'],
                             metric='euclidean', algorithm='kd_tree', leaf_size=40,
                             n_jobs=settings['hdbscan_workers'],
                             cluster_selection_method=method,
                             cluster_selection_epsilon=0., alpha=1.,
                             allow_single_cluster=False).fit(embedding)
            require(fitted.labels_.shape == (count,) and
                    fitted.probabilities_.shape == (count,) and
                    np.all(fitted.labels_ >= -1) and
                    np.isfinite(fitted.probabilities_).all() and
                    np.all((fitted.probabilities_ >= 0) &
                           (fitted.probabilities_ <= 1)),
                    'Invalid full-cohort HDBSCAN labels or strengths')
            path = output / f'hdbscan-{method}-seed-{seed}.npz'
            np.savez_compressed(path, labels=fitted.labels_,
                                probabilities=fitted.probabilities_)
            labels[(method, seed)] = fitted.labels_.copy()
            density.append({'method': method, 'seed': seed,
                            'clusters': len(set(fitted.labels_) - {-1}),
                            'unassigned_models': int(np.sum(fitted.labels_ == -1)),
                            'seconds': time.monotonic() - started,
                            'labels_sha256': digest(path)})
            print('HDBSCAN', target['id'], method, seed,
                  density[-1]['clusters'], 'clusters', flush=True)
    agreement = {method: {str(seed): seed_agreement(labels[(method, 42)],
                                                   labels[(method, seed)])
                          for seed in (7, 123)} for method in ('leaf', 'eom')}
    receipt = {'status': 'validated', 'target': target['id'],
               'plan_sha256': plan_hash, 'models': count, 'pairs_per_model': pairs,
               'geometry_matrix_sha256': geometry['matrix_sha256'],
               'roster_sha256': target['roster_sha256'],
               'fidelity_acceptance_sha256': target['fidelity_acceptance_sha256'],
               'model_index_sha256': digest(output / 'model-index.jsonl'),
               'sketch_sha256': sketch_hash, 'sketch_seconds': sketch_seconds,
               'sketch_dimensions': settings['sketch_dimensions'],
               'umap_fits': fits, 'umap_knn_clusters': int(len(set(primary))),
               'umap_knn_labels_sha256': digest(output / 'umap-knn-labels.npy'),
               'umap_knn_selection_sha256': digest(output / 'umap-knn-selection.json'),
               'hdbscan_fits': density, 'hdbscan_seed_agreement': agreement,
               'published_density_selection': 'leaf seed 42; EOM and other seeds diagnostic',
               'scope': 'all accepted full-construct A/B/C models; geometry only; no energies'}
    (output / 'acceptance.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps(receipt, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    run(args.plan, args.plan_sha256, int(os.environ['SLURM_ARRAY_TASK_ID']))


if __name__ == '__main__':
    main()
