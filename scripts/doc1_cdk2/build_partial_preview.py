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
SUPPLEMENTAL_PLAN = '8f2b26e94195a55327cbd3d5d3d341352019eb5cdebe06f3172c6ad4fe78360d'
CORE_PLAN = 'dcec61046f7b836a4ee86e56263ab2d8c2994554cab7edac693c021202222145'
ENERGY_PLAN = 'c8eead144f40b7f9ca972473998e9946c20b986564b87a74153bbdb23c863195'
CORE_RECEIPTS = {
    'DOC1Rdimer_CDK2': ('b1a1f6c42e55c854e28b7bb869ce38031e6efe297e75c90c3a5f6de933d9577d', 65, 88831),
    'DOC1dimer_CDK2': ('d13deb318f13ec6fe3e81ad353900d3c08e39cefcf9d05e258f3a115073adf56', 60, 83845),
}


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


def load_supplemental(folder, slug, count, clustering_receipt, output):
    receipt_path = folder / 'acceptance.json'
    receipt = json.loads(receipt_path.read_text())
    if (receipt['status'], receipt['target'], receipt['models'], receipt['plan_sha256'],
            receipt['roster_sha256'], receipt['geometry_matrix_sha256'],
            receipt['sketch_sha256']) != ('validated', slug, count, SUPPLEMENTAL_PLAN,
                                         clustering_receipt['roster_sha256'],
                                         clustering_receipt['geometry_matrix_sha256'],
                                         clustering_receipt['sketch_sha256']):
        raise ValueError(f'{slug}: supplemental receipt identity differs')
    if set(receipt['files']) != {'pca-2d.npy', 'tsne-2d.npy', 'median-sample-indices.npy',
                                  'median-ca-distances.npy', 'variance-ca-distances.npy',
                                  'median-ca-distances.png', 'variance-ca-distances.png'}:
        raise ValueError(f'{slug}: supplemental file set differs')
    for name, expected in receipt['files'].items():
        checked(folder / name, expected)
    pca = np.load(folder / 'pca-2d.npy', allow_pickle=False)
    tsne = np.load(folder / 'tsne-2d.npy', allow_pickle=False)
    sample = np.load(folder / 'median-sample-indices.npy', allow_pickle=False)
    lengths = receipt['full_construct_chain_lengths']
    expected_lengths = [126, 126, 298] if slug == 'DOC1Rdimer_CDK2' else [115, 115, 298]
    if (pca.shape != (count, 2) or tsne.shape != (count, 2) or
            not np.isfinite(pca).all() or not np.isfinite(tsne).all() or
            len(sample) != 5000 or not np.array_equal(sample, np.unique(sample)) or
            sample[0] < 0 or sample[-1] >= count or
            lengths != expected_lengths or receipt['median_sample_models'] != 5000 or
            receipt['variance_models'] != count or
            len(receipt['pca_explained_variance_ratio']) != 2 or
            any(not 0 <= float(value) <= 1 for value in receipt['pca_explained_variance_ratio']) or
            not np.isfinite(receipt['tsne_kl_divergence'])):
        raise ValueError(f'{slug}: supplemental projection/sample validation failed')
    for name in ('median-ca-distances.npy', 'variance-ca-distances.npy'):
        array = np.load(folder / name, allow_pickle=False)
        if (array.shape != (sum(lengths), sum(lengths)) or not np.isfinite(array).all() or
                (array < 0).any() or not np.array_equal(array, array.T) or
                not np.array_equal(np.diag(array), np.zeros(sum(lengths)))):
            raise ValueError(f'{slug}: {name} invalid')
    figures = {}
    for name in ('median-ca-distances.png', 'variance-ca-distances.png'):
        destination = output / 'figures' / f'{slug}-{name}'
        shutil.copyfile(folder / name, destination)
        figures[name] = f'figures/{destination.name}'
    return {'pca': {'x': pca[:, 0].tolist(), 'y': pca[:, 1].tolist(),
                    'explained_variance_ratio': receipt['pca_explained_variance_ratio']},
            'tsne': {'x': tsne[:, 0].tolist(), 'y': tsne[:, 1].tolist()},
            'maps': {'median': figures['median-ca-distances.png'],
                     'variance': figures['variance-ca-distances.png'],
                     'median_models': 5000, 'variance_models': count, 'chain_lengths': lengths},
            'supplemental_receipt_sha256': digest(receipt_path)}


def load_core(folder, slug, count, full_receipt, full_index, roster_rows, output, energy_values=None):
    receipt_hash, first_ab, pair_count = CORE_RECEIPTS[slug]
    receipt_path = folder / 'acceptance.json'
    checked(receipt_path, receipt_hash)
    receipt = json.loads(receipt_path.read_text())
    if (receipt['status'], receipt['target'], receipt['models'], receipt['plan_sha256'],
            receipt['first_retained_ab'], receipt['subset_pairs_per_model'],
            receipt['roster_sha256'], receipt['geometry_matrix_sha256']) != (
            'validated', slug, count, CORE_PLAN, first_ab, pair_count,
            full_receipt['roster_sha256'], full_receipt['geometry_matrix_sha256']):
        raise ValueError(f'{slug}: core receipt identity or scope differs')
    expected = {
        'model-index.jsonl': receipt['model_index_sha256'],
        'umap-2d-seed-42.npy': next(x['embedding_sha256'] for x in receipt['umap_fits'] if x['dimensions'] == 2 and x['seed'] == 42),
        'umap-knn-labels.npy': receipt['umap_knn_labels_sha256'],
        'hdbscan-leaf-seed-42.npz': next(x['labels_sha256'] for x in receipt['hdbscan_fits'] if x['method'] == 'leaf' and x['seed'] == 42),
        'hdbscan-eom-seed-42.npz': next(x['labels_sha256'] for x in receipt['hdbscan_fits'] if x['method'] == 'eom' and x['seed'] == 42),
    }
    for name, sha in expected.items():
        checked(folder / name, sha)
    if digest(folder / 'model-index.jsonl') != digest(full_index):
        raise ValueError(f'{slug}: core model order differs from full fit')
    coords = np.load(folder / 'umap-2d-seed-42.npy', allow_pickle=False)
    knn = np.load(folder / 'umap-knn-labels.npy', allow_pickle=False)
    with np.load(folder / 'hdbscan-leaf-seed-42.npz', allow_pickle=False) as fit:
        leaf, leaf_probability = fit['labels'], fit['probabilities']
    with np.load(folder / 'hdbscan-eom-seed-42.npz', allow_pickle=False) as fit:
        eom, eom_probability = fit['labels'], fit['probabilities']
    if coords.shape != (count, 2) or not np.isfinite(coords).all():
        raise ValueError(f'{slug}: invalid core UMAP coordinates')
    if any(array.shape != (count,) for array in (knn, leaf, leaf_probability, eom, eom_probability)):
        raise ValueError(f'{slug}: core label length mismatch')
    if any(not np.isfinite(array).all() or ((array < 0) | (array > 1)).any()
           for array in (leaf_probability, eom_probability)):
        raise ValueError(f'{slug}: invalid core membership strengths')
    for key, array in (('leaf', leaf), ('eom', eom)):
        fit = next(x for x in receipt['hdbscan_fits'] if x['method'] == key and x['seed'] == 42)
        if int(np.sum(array == -1)) != fit['unassigned_models'] or len(set(array) - {-1}) != fit['clusters']:
            raise ValueError(f'{slug}: core cluster counts differ from receipt')
    last_ab = receipt['chain_lengths'][0]
    export = {
        'range': 'core', 'range_label': f'A{first_ab}–{last_ab} + B{first_ab}–{last_ab} + C1–298',
        'receipt_sha256': receipt_hash, 'pair_count': pair_count,
        'x': np.round(coords[:, 0], 5).tolist(), 'y': np.round(coords[:, 1], 5).tolist(),
        'knn': knn.tolist(), 'leaf': leaf.tolist(), 'eom': eom.tolist(),
        'leaf_probability': np.round(leaf_probability, 5).tolist(),
        'eom_probability': np.round(eom_probability, 5).tolist(),
        'counts': {name: dict(sorted(Counter(int(v) for v in array).items()))
                   for name, array in [('knn', knn), ('leaf', leaf), ('eom', eom)]},
    }
    (output / 'data' / f'{slug}-core.json').write_text(json.dumps(export, separators=(',', ':')))
    with (output / 'downloads' / f'{slug}-core-geometry-memberships.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['model_id', 'native_sha256', 'method', 'umap_1', 'umap_2',
                         'umap_knn_group', 'hdbscan_leaf_cluster', 'hdbscan_leaf_strength',
                         'hdbscan_eom_cluster', 'hdbscan_eom_strength'] +
                        (['protein_ebm_full_complex_energy_t010'] if energy_values is not None else []))
        for i, model in enumerate(roster_rows):
            row = [model['model_id'], model['native_sha256'], model['method'],
                             float(coords[i, 0]), float(coords[i, 1]), int(knn[i]),
                             int(leaf[i]), float(leaf_probability[i]), int(eom[i]),
                             float(eom_probability[i])]
            if energy_values is not None:
                row.append(energy_values[i])
            writer.writerow(row)
    return {'range_label': export['range_label'], 'receipt_sha256': receipt_hash,
            'knn_groups': receipt['umap_knn_clusters'],
            'leaf_clusters': next(x['clusters'] for x in receipt['hdbscan_fits'] if x['method'] == 'leaf' and x['seed'] == 42),
            'eom_clusters': next(x['clusters'] for x in receipt['hdbscan_fits'] if x['method'] == 'eom' and x['seed'] == 42)}


def load_energy(folder, slug, count, roster_sha256, roster_rows, output):
    """Package accepted native full-complex scores without changing their values."""
    receipt_path = folder / 'acceptance.json'
    receipt = json.loads(receipt_path.read_text())
    expected_residues = 550 if slug == 'DOC1Rdimer_CDK2' else 528
    if (receipt['status'], receipt['target'], receipt['models'], receipt['energy_values'],
            receipt['residues'], receipt['primary_time_index'], receipt['primary_t'],
            receipt['plan_sha256'], receipt['roster_sha256'], len(receipt['chunks'])) != (
            'validated', slug, count, 16 * count, expected_residues, 10, 0.10,
            ENERGY_PLAN, roster_sha256, 58 if slug == 'DOC1Rdimer_CDK2' else 76):
        raise ValueError(f'{slug}: ProteinEBM receipt identity or coverage differs')
    csv_path = folder / 'energy-rankings.csv'
    checked(csv_path, receipt['csv_sha256'])
    fields = ['model_id', 'method', 'native_sha256', 'protein_ebm_energy_t010'] + [
        f'energy_t{level:02d}' for level in range(16)]
    values = []
    with csv_path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != fields:
            raise ValueError(f'{slug}: ProteinEBM CSV columns differ')
        for i, row in enumerate(reader):
            if i >= count:
                raise ValueError(f'{slug}: too many ProteinEBM rows')
            source = roster_rows[i]
            if (row['model_id'], row['native_sha256'], row['method']) != (
                    source['model_id'], source['native_sha256'], source['method']):
                raise ValueError(f'{slug}: ProteinEBM identity differs at row {i}')
            scores = np.asarray([float(row[f'energy_t{level:02d}']) for level in range(16)])
            primary = float(row['protein_ebm_energy_t010'])
            if not np.isfinite(scores).all() or not np.isfinite(primary) or primary != scores[10]:
                raise ValueError(f'{slug}: invalid ProteinEBM score at row {i}')
            values.append(primary)
    if len(values) != count:
        raise ValueError(f'{slug}: incomplete ProteinEBM roster')
    scores = np.asarray(values, dtype=np.float64)
    shutil.copyfile(csv_path, output / 'downloads' / f'{slug}-proteinebm-full-complex.csv')
    return {'values': scores.tolist(),
            'limits': np.quantile(scores, [0.02, 0.5, 0.98]).tolist(),
            'minimum': float(np.min(scores)), 'maximum': float(np.max(scores)),
            'receipt_sha256': digest(receipt_path), 'csv_sha256': receipt['csv_sha256'],
            'model': 'ProteinEBM Model 6 frozen native Cα expert',
            'primary_t': 0.10, 'primary_time_index': 10,
            'scoring_scope': 'full A/B/C construct',
            'units': 'learned arbitrary units; not binding energy',
            'download': f'downloads/{slug}-proteinebm-full-complex.csv'}


def run(inputs, output, vendor, supplements=None, core_inputs=None, energies=None):
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    (output / 'assets').mkdir()
    (output / 'data').mkdir()
    (output / 'downloads').mkdir()
    (output / 'figures').mkdir()
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
            'range': 'full',
            'range_label': f'A1–{126 if slug == "DOC1Rdimer_CDK2" else 115} + B1–{126 if slug == "DOC1Rdimer_CDK2" else 115} + C1–298',
        }
        energy = load_energy(energies / slug, slug, count, receipt['roster_sha256'], roster_rows, output) if energies is not None else None
        if energy is not None:
            export['energy'] = energy
        if supplements is not None:
            extra = load_supplemental(supplements / slug, slug, count, receipt, output)
            export.update(extra)
        (output / 'data' / f'{slug}.json').write_text(json.dumps(export, separators=(',', ':')))
        with (output / 'downloads' / f'{slug}-geometry-memberships.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            columns = ['model_id', 'native_sha256', 'method', 'umap_1', 'umap_2', 'umap_knn_group', 'hdbscan_leaf_cluster', 'hdbscan_leaf_strength', 'hdbscan_eom_cluster', 'hdbscan_eom_strength']
            if supplements is not None:
                columns += ['pca_1', 'pca_2', 'tsne_1', 'tsne_2']
            if energy is not None:
                columns += ['protein_ebm_full_complex_energy_t010']
            writer.writerow(columns)
            for i, model in enumerate(roster_rows):
                row = [model['model_id'], model['native_sha256'], model['method'], float(coords[i, 0]), float(coords[i, 1]), int(knn[i]), int(leaf[i]), float(leaf_probability[i]), int(eom[i]), float(eom_probability[i])]
                if supplements is not None:
                    row += [float(extra['pca']['x'][i]), float(extra['pca']['y'][i]),
                            float(extra['tsne']['x'][i]), float(extra['tsne']['y'][i])]
                if energy is not None:
                    row.append(energy['values'][i])
                writer.writerow(row)
        core_summary = load_core(core_inputs / slug, slug, count, receipt, folder / 'model-index.jsonl', roster_rows, output,
                                 energy['values'] if energy is not None else None) if core_inputs is not None else None
        summary.append({'slug': slug, 'title': title, 'models': count, 'chains': 'A/B/C', 'example_model': roster_rows[0]['model_id'], 'receipt_sha256': receipt_hash, 'core': core_summary,
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
    (output.parent / 'delivery-manifest.json').write_text(json.dumps({'kind': 'private-partial-geometry-preview', 'files': files, 'source_plan_sha256': PLAN,
                                                                    'supplemental_plan_sha256': SUPPLEMENTAL_PLAN if supplements is not None else None,
                                                                    'core_plan_sha256': CORE_PLAN if core_inputs is not None else None,
                                                                    'energy_plan_sha256': ENERGY_PLAN if energies is not None else None}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vendor', type=Path, required=True)
    parser.add_argument('--supplements', type=Path)
    parser.add_argument('--core-inputs', type=Path)
    parser.add_argument('--energies', type=Path)
    args = parser.parse_args()
    run(args.inputs, args.output, args.vendor, args.supplements, args.core_inputs, args.energies)
