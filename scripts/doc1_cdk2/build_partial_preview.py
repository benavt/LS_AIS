"""Package accepted DOC1/CDK2 geometry outputs as a private partial atlas view.

This is presentation-only: it never fits, filters, or relabels scientific data.
"""

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

import numpy as np


TARGETS = {
    'DOC1Rdimer_CDK2': ('DOC1R dimer–CDK2', 57463, '24c734481c2e6b42e074983a2a9c8b20ab6d819476f3b917a8385d090465756d'),
    'DOC1dimer_CDK2': ('DOC1 dimer–CDK2', 75800, 'c6f7be99d0a5edc2d1bd9dc275fd3ae31f0b4d26861ee255450e853bfca687e3'),
}
PLAN = '76024b0e0cff251ca7b6cc2dfb309e26fa1d92192d860df2dcc7eb33ff99bc6c'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def checked(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f'{path.name}: SHA-256 mismatch, {actual}')


def run(inputs, output, vendor):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    (output / 'assets').mkdir()
    (output / 'data').mkdir()
    (output / 'downloads').mkdir()
    shutil.copyfile(vendor / 'plotly.min.js', output / 'assets' / 'plotly.min.js')
    shutil.copyfile(vendor / '3Dmol-min.js', output / 'assets' / '3Dmol-min.js')
    shutil.copyfile(vendor / 'ca_fallback.js', output / 'assets' / 'ca_fallback.js')
    shutil.copyfile(vendor.parent / 'style.css', output / 'assets' / 'atlas.css')
    summary = []
    for slug, (title, count, receipt_hash) in TARGETS.items():
        folder = inputs / slug
        checked(folder / 'acceptance.json', receipt_hash)
        receipt = json.loads((folder / 'acceptance.json').read_text())
        if (receipt['status'], receipt['target'], receipt['models'], receipt['plan_sha256']) != ('validated', slug, count, PLAN):
            raise ValueError(f'{slug}: unexpected acceptance receipt')
        expected = {
            'roster.jsonl': receipt['roster_sha256'],
            'model-index.jsonl': receipt['model_index_sha256'],
            'umap-2d-seed-42.npy': next(x['embedding_sha256'] for x in receipt['umap_fits'] if x['dimensions'] == 2 and x['seed'] == 42),
            'umap-knn-labels.npy': receipt['umap_knn_labels_sha256'],
            'hdbscan-leaf-seed-42.npz': next(x['labels_sha256'] for x in receipt['hdbscan_fits'] if x['method'] == 'leaf' and x['seed'] == 42),
            'hdbscan-eom-seed-42.npz': next(x['labels_sha256'] for x in receipt['hdbscan_fits'] if x['method'] == 'eom' and x['seed'] == 42),
        }
        for name, sha in expected.items():
            checked(folder / name, sha)
        coords = np.load(folder / 'umap-2d-seed-42.npy', allow_pickle=False)
        knn = np.load(folder / 'umap-knn-labels.npy', allow_pickle=False)
        with np.load(folder / 'hdbscan-leaf-seed-42.npz', allow_pickle=False) as fit:
            leaf, leaf_probability = fit['labels'], fit['probabilities']
        with np.load(folder / 'hdbscan-eom-seed-42.npz', allow_pickle=False) as fit:
            eom, eom_probability = fit['labels'], fit['probabilities']
        if coords.shape != (count, 2) or not np.isfinite(coords).all():
            raise ValueError(f'{slug}: invalid UMAP coordinates')
        if any(array.shape != (count,) for array in (knn, leaf, leaf_probability, eom, eom_probability)):
            raise ValueError(f'{slug}: cluster array length mismatch')
        if any(not np.isfinite(array).all() for array in (leaf_probability, eom_probability)):
            raise ValueError(f'{slug}: invalid membership strengths')
        if any(((array < 0) | (array > 1)).any() for array in (leaf_probability, eom_probability)):
            raise ValueError(f'{slug}: membership strength outside [0, 1]')
        for key, array in (('leaf', leaf), ('eom', eom)):
            fit = next(x for x in receipt['hdbscan_fits'] if x['method'] == key and x['seed'] == 42)
            if int(np.sum(array == -1)) != fit['unassigned_models'] or len(set(array) - {-1}) != fit['clusters']:
                raise ValueError(f'{slug}: cluster counts differ from receipt')
        index_rows = [json.loads(line) for line in (folder / 'model-index.jsonl').open()]
        roster_rows = [json.loads(line) for line in (folder / 'roster.jsonl').open()]
        if len(index_rows) != count or len(roster_rows) != count:
            raise ValueError(f'{slug}: roster length mismatch')
        for i, (index, model) in enumerate(zip(index_rows, roster_rows)):
            if (index['index'], index['model_id'], index['native_sha256']) != (i, model['model_id'], model['native_sha256']):
                raise ValueError(f'{slug}: model order differs at row {i}')
        checked(folder / 'example.pdb', roster_rows[0]['native_sha256'])
        shutil.copyfile(folder / 'example.pdb', output / 'data' / f'{slug}-example.pdb')
        methods = [row['method'] for row in roster_rows]
        export = {
            'target': slug,
            'title': title,
            'models': count,
            'method_counts': dict(sorted(Counter(methods).items())),
            'x': np.round(coords[:, 0], 5).tolist(),
            'y': np.round(coords[:, 1], 5).tolist(),
            'model_id': [row['model_id'] for row in roster_rows],
            'method': methods,
            'knn': knn.tolist(),
            'leaf': leaf.tolist(),
            'eom': eom.tolist(),
            'leaf_probability': np.round(leaf_probability, 5).tolist(),
            'eom_probability': np.round(eom_probability, 5).tolist(),
            'example_model': roster_rows[0]['model_id'],
            'counts': {name: dict(sorted(Counter(int(v) for v in array).items())) for name, array in [('knn', knn), ('leaf', leaf), ('eom', eom)]},
            'receipt_sha256': receipt_hash,
        }
        (output / 'data' / f'{slug}.json').write_text(json.dumps(export, separators=(',', ':')))
        with (output / 'downloads' / f'{slug}-geometry-memberships.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['model_id', 'native_sha256', 'method', 'umap_1', 'umap_2', 'umap_knn_group', 'hdbscan_leaf_cluster', 'hdbscan_leaf_strength', 'hdbscan_eom_cluster', 'hdbscan_eom_strength'])
            for i, model in enumerate(roster_rows):
                writer.writerow([model['model_id'], model['native_sha256'], model['method'], float(coords[i, 0]), float(coords[i, 1]), int(knn[i]), int(leaf[i]), float(leaf_probability[i]), int(eom[i]), float(eom_probability[i])])
        summary.append({'slug': slug, 'title': title, 'models': count, 'chains': 'A/B/C', 'example_model': roster_rows[0]['model_id'], 'receipt_sha256': receipt_hash,
                        'knn_groups': receipt['umap_knn_clusters'], 'leaf_clusters': next(x['clusters'] for x in receipt['hdbscan_fits'] if x['method'] == 'leaf' and x['seed'] == 42),
                        'leaf_unassigned': int(np.sum(leaf == -1)), 'eom_clusters': next(x['clusters'] for x in receipt['hdbscan_fits'] if x['method'] == 'eom' and x['seed'] == 42), 'eom_unassigned': int(np.sum(eom == -1))})
    (output / 'data' / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    source = Path(__file__).resolve().parent / 'partial_preview_assets'
    for name in ('index.html', 'app.js', 'style.css'):
        shutil.copyfile(source / name, output / name)
    files = []
    for path in sorted(output.rglob('*')):
        if path.is_file():
            files.append({'path': path.relative_to(output).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)})
    (output / 'export-manifest.json').write_text(json.dumps({'kind': 'private-partial-geometry-preview', 'files': files}, indent=2) + '\n')
    (output.parent / 'delivery-manifest.json').write_text(json.dumps({'kind': 'private-partial-geometry-preview', 'files': files, 'source_plan_sha256': PLAN}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vendor', type=Path, required=True)
    args = parser.parse_args()
    run(args.inputs, args.output, args.vendor)
