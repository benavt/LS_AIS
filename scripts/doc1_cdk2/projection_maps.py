"""Frozen full-cohort PCA/t-SNE and C-alpha distance summaries for DOC1/CDK2.

This is scientific execution. It must run only under an explicitly approved,
hash-bound plan; the private atlas builder never invokes it.
"""

import argparse
import hashlib
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


def symmetric_matrix(values, residues):
    import numpy as np

    rows, columns = np.triu_indices(residues, 1)
    require(len(values) == len(rows), 'Condensed pair count differs from residue scope')
    result = np.zeros((residues, residues), dtype=np.float32)
    result[rows, columns] = values
    result[columns, rows] = values
    require(np.isfinite(result).all() and np.array_equal(result, result.T),
            'Distance summary is not finite and symmetric')
    return result


def distance_summaries(matrix, sample_indices, block_models):
    """Exact cohort population variance; exact median on the frozen sample."""
    import numpy as np

    count, pairs = matrix.shape
    require(1 < len(sample_indices) <= count and
            np.array_equal(sample_indices, np.unique(sample_indices)) and
            sample_indices[0] >= 0 and sample_indices[-1] < count,
            'Invalid frozen median sample')
    mean = np.zeros(pairs, dtype=np.float64)
    m2 = np.zeros(pairs, dtype=np.float64)
    observed = 0
    for start in range(0, count, block_models):
        block = np.asarray(matrix[start:start + block_models], dtype=np.float64)
        require(np.isfinite(block).all() and np.all(block >= 0),
                'Nonfinite or negative C-alpha pair distance')
        block_mean = block.mean(axis=0)
        block_m2 = np.sum((block - block_mean) ** 2, axis=0)
        amount = len(block)
        delta = block_mean - mean
        total = observed + amount
        mean += delta * amount / total
        m2 += block_m2 + delta * delta * observed * amount / total
        observed = total
    require(observed == count, 'Incomplete full-cohort variance pass')
    variance = np.asarray(m2 / count, dtype=np.float32)
    # Restrict the temporary selection to the declared sample, not all models.
    sample = np.asarray(matrix[sample_indices], dtype=np.float32)
    require(sample.shape == (len(sample_indices), pairs) and np.isfinite(sample).all(),
            'Incomplete median sample')
    median = np.asarray(np.median(sample, axis=0), dtype=np.float32)
    require(np.isfinite(median).all() and np.isfinite(variance).all() and
            np.all(median >= 0) and np.all(variance >= 0),
            'Invalid distance summary')
    return median, variance


def render_map(matrix, chain_lengths, path, *, title, colorbar):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots(figsize=(9, 8), dpi=180, layout='constrained')
    image = ax.imshow(matrix, cmap='viridis' if colorbar == 'Å' else 'magma',
                      interpolation='nearest', origin='upper', vmin=0)
    breaks = np.cumsum(chain_lengths)[:-1]
    for boundary in breaks:
        ax.axhline(boundary - .5, color='white', linestyle='--', linewidth=1.1)
        ax.axvline(boundary - .5, color='white', linestyle='--', linewidth=1.1)
    centers = np.cumsum(chain_lengths) - np.asarray(chain_lengths) / 2 - .5
    ax.set_xticks(centers, ['A', 'B', 'C'])
    ax.set_yticks(centers, ['A', 'B', 'C'])
    ax.set_xlabel('Cα residue · chain')
    ax.set_ylabel('Cα residue · chain')
    ax.set_title(title)
    fig.colorbar(image, ax=ax, label=colorbar)
    fig.savefig(path)
    plt.close(fig)


def run(plan_path, plan_hash, target_index):
    import numpy as np
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE

    require(digest(plan_path) == plan_hash, 'Frozen projection/map plan differs')
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_pca_tsne_ca_maps' and
            plan['scientific_execution'] is True and plan['paid_external_calls'] == 0 and
            target_index in (0, 1), 'Wrong operation or target index')
    require(digest(__file__) == plan['source_script_sha256'], 'Frozen execution code differs')
    settings = plan['settings']
    require(settings == {'pca_components': 50, 'pca_seed': 42,
                         'tsne_perplexity': 30.0, 'tsne_seed': 42,
                         'tsne_max_iter': 1000, 'tsne_method': 'barnes_hut',
                         'median_sample_models': 5000, 'median_sample_seed': 42,
                         'variance_block_models': 512}, 'Unreviewed analysis settings')
    target = plan['targets'][target_index]
    count, pairs = target['models'], target['pairs']
    chain_lengths = target['chain_lengths']
    require(len(chain_lengths) == 3 and sum(chain_lengths) * (sum(chain_lengths) - 1) // 2 == pairs,
            'Invalid full-construct A/B/C residue scope')
    for name in ('geometry', 'clustering', 'target_config'):
        require(digest(target[name + '_path']) == target[name + '_sha256'],
                'Frozen ' + name + ' receipt differs')
    geometry = json.loads(Path(target['geometry_path']).read_text())
    clustering = json.loads(Path(target['clustering_path']).read_text())
    config = json.loads(Path(target['target_config_path']).read_text())
    require(geometry['status'] == clustering['status'] == 'validated' and
            geometry['target'] == clustering['target'] == config['id'] == target['id'] and
            geometry['shape'] == [count, pairs] and
            geometry['matrix_sha256'] == clustering['geometry_matrix_sha256'] == target['matrix_sha256'] and
            clustering['sketch_sha256'] == target['sketch_sha256'] and
            clustering['roster_sha256'] == geometry['roster_sha256'] == target['roster_sha256'] and
            clustering['sketch_dimensions'] == 4096 and
            [(chain['id'], chain['residues']) for chain in config['chains']] ==
            list(zip('ABC', chain_lengths)) and
            geometry['pair_order'] == 'scipy pdist condensed upper triangle' and
            geometry['scope'] == 'complete native A/B/C complex',
            'Accepted input identity or residue scope differs')
    matrix_path = Path(target['geometry_path']).parent / 'pair-distances.f32'
    sketch_path = Path(target['clustering_path']).parent / 'all-pair-sketch.f32'
    require(matrix_path.stat().st_size == count * pairs * 4 and
            sketch_path.stat().st_size == count * 4096 * 4 and
            digest(matrix_path) == target['matrix_sha256'] and
            digest(sketch_path) == target['sketch_sha256'],
            'Frozen complete feature bytes differ')
    matrix = np.memmap(matrix_path, dtype='<f4', mode='r', shape=(count, pairs))
    sketch = np.memmap(sketch_path, dtype='<f4', mode='r', shape=(count, 4096))
    output = Path(plan['output_root']) / target['id']
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    # The same full-cohort PCA basis supplies the plot and t-SNE's 50-D input.
    pca = PCA(n_components=50, svd_solver='randomized', random_state=42,
              whiten=False)
    principal = np.asarray(pca.fit_transform(sketch), dtype=np.float32)
    require(principal.shape == (count, 50) and np.isfinite(principal).all() and
            np.isfinite(pca.explained_variance_ratio_).all(), 'PCA fit incomplete')
    np.save(output / 'pca-2d.npy', principal[:, :2], allow_pickle=False)
    pca_seconds = time.monotonic() - started
    started = time.monotonic()
    tsne = TSNE(n_components=2, perplexity=30.0, random_state=42,
                init='pca', learning_rate='auto', max_iter=1000,
                method='barnes_hut', angle=.5, n_jobs=8)
    coordinates = np.asarray(tsne.fit_transform(principal), dtype=np.float32)
    require(coordinates.shape == (count, 2) and np.isfinite(coordinates).all(),
            't-SNE fit incomplete')
    np.save(output / 'tsne-2d.npy', coordinates, allow_pickle=False)
    tsne_seconds = time.monotonic() - started
    started = time.monotonic()
    sample = np.sort(np.random.default_rng(42).choice(count, 5000, replace=False))
    np.save(output / 'median-sample-indices.npy', sample, allow_pickle=False)
    median, variance = distance_summaries(matrix, sample, 512)
    residues = sum(chain_lengths)
    median_matrix = symmetric_matrix(median, residues)
    variance_matrix = symmetric_matrix(variance, residues)
    np.save(output / 'median-ca-distances.npy', median_matrix, allow_pickle=False)
    np.save(output / 'variance-ca-distances.npy', variance_matrix, allow_pickle=False)
    render_map(median_matrix, chain_lengths, output / 'median-ca-distances.png',
               title=f"{target['id']} · median Cα distance · 5,000 sampled models", colorbar='Å')
    render_map(variance_matrix, chain_lengths, output / 'variance-ca-distances.png',
               title=f"{target['id']} · Cα distance variance · all {count:,} models", colorbar='Å²')
    map_seconds = time.monotonic() - started
    files = {path.name: digest(path) for path in sorted(output.iterdir()) if path.is_file()}
    receipt = {'status': 'validated', 'target': target['id'], 'plan_sha256': plan_hash,
               'models': count, 'roster_sha256': target['roster_sha256'],
               'geometry_matrix_sha256': target['matrix_sha256'],
               'sketch_sha256': target['sketch_sha256'], 'full_construct_chain_lengths': chain_lengths,
               'pca_explained_variance_ratio': pca.explained_variance_ratio_[:2].tolist(),
               'tsne_kl_divergence': float(tsne.kl_divergence_),
               'median_sample_models': len(sample), 'variance_models': count,
               'seconds': {'pca': pca_seconds, 'tsne': tsne_seconds, 'maps': map_seconds},
               'files': files, 'units': {'median': 'angstrom', 'variance': 'angstrom squared'},
               'scope': 'full-construct A/B/C; PCA and t-SNE fit all accepted models; '
                        'median uses frozen uniform sample; variance uses full cohort'}
    (output / 'acceptance.json').write_text(json.dumps(receipt, indent=2, allow_nan=False) + '\n')
    print(json.dumps(receipt, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    run(args.plan, args.plan_sha256, int(os.environ['SLURM_ARRAY_TASK_ID']))


if __name__ == '__main__':
    main()
