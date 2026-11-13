"""Add accepted joint 5,000-model views to a saved LS_AIS private atlas.

This adapter only checks and serializes completed scientific results. It never
fits a projection, chooses a representative, or submits a scientific job.
"""

import argparse
import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
import re
import shutil
import sys
import tempfile

import numpy as np


TARGETS = ('CDK2_DOC1', 'CDK2_DOC1t')
ROOT = Path(__file__).resolve().parents[2]
VIEWS = {'knn': ('primary', 'UMAP KNN'),
         'leaf': ('density', 'HDBSCAN leaf'),
         'eom': ('eom', 'HDBSCAN EOM · diagnostic')}
JOINT_PLAN_SHA = '7b824af271fe9b31e4aa0cba4559e447d2f405a7b53e00096f49980f46b0377c'
SUPPLEMENT_PLAN_SHA = '66750dcf56843a40fcd262f74e82ee16d1e65f25bf5d985f1abea594373bb4dc'
BONSAI_PLAN_SHA = 'acf354ed7c8990fa6a04318b256417bcbb83b24e2ac121f2228ed845431f99f8'
TM_PLAN_SHA = 'e504bce45db4014c90b156ee7edada73fa53c0649526db52560230a0d189fd52'
BONSAI_RECEIPTS = {
    'CDK2_DOC1': {'leaf': 'e9f942f1f93cb88d81117dcdcb5a7288179d27336d7e6be7efcfc154d5e5d434',
                  'eom': '9a7af689affccdb3a14ce394f1941f92e40a81fa73d6decbb426250607431acc',
                  'knn': 'ed72fb6ca31245ffd7f5ac47e0847c30715f5167aafc1755e07c7b51793dfc59'},
    'CDK2_DOC1t': {'leaf': '624de8dada202eef921f9256ec8b5cc4ae2e02ade7bac49993fcbe111619b2b9',
                   'eom': '767d54262a1ce0c44c38483093813c174d256afeffeed06540ae2c591d3bf2ac',
                   'knn': 'a7ae02514559a98d18030ab4f1c7e35a22d242fed8a1c8d6d702e54b0fc77b13'}}
BONSAI_EXPORTS = {
    'CDK2_DOC1': {'leaf': 'fb31ca269c7afc9c6f74118e5db9bdb6f5c1550b80a2dd4c2ca251a864dfb2cd',
                  'eom': '6d3dc578a86d2f406f2a8dfd44e39d5c05400ed3fce7ec1ce18ecce56789f531',
                  'knn': '65118cb67655d42e97a53dc1f94ee680ceb995766528d0207c395ad5ca2f49d5'},
    'CDK2_DOC1t': {'leaf': '7ee8c39f8700e732636e3c86e7ffa4c151186a8f9de74eee3847c6c3d714cd9e',
                   'eom': '8e26bdb9106748de41b2ba30401d4bc5219176ac7965df2f6b437ff5c940b74f',
                   'knn': '84cd1e017a718dea666d38e7226baba1bd7bbb732b281a0e7c218fdc6effb5aa'}}
OPTIONAL_PLOTS = ('box_summary_3d', 'pair_distribution_detail')
METHODS = {'afsample2_v1': 'AFsample2 · v1 weights',
           'afsample2_v2': 'AFsample2 · v2 weights',
           'afsample2_v3': 'AFsample2 · v3 weights',
           'afsample3': 'AFsample3', 'bioemu2': 'BioEMU2'}
METHOD_COLORS = {'AFsample2 · v1 weights': '#3454a4',
                 'AFsample2 · v2 weights': '#477bc0',
                 'AFsample2 · v3 weights': '#75a8d0',
                 'AFsample3': '#d98b35', 'BioEMU2': '#8b56aa'}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n')
    temporary.replace(path)  # The saved source may be hard-linked into the stage.


def omit_optional_plots(stage):
    """Remove inherited opt-in figures from this stage, preserving the saved source."""
    missing = object()

    def optional(value):
        return isinstance(value, str) and any(name in value for name in OPTIONAL_PLOTS)

    def remove(value):
        if isinstance(value, dict):
            if any(optional(value.get(key)) for key in
                   ('file', 'path', 'url', 'image', 'href', 'data')):
                return missing
            cleaned = {}
            for key, item in value.items():
                if key == 'optional_plots_excluded_from_view':
                    continue
                kept = remove(item)
                if kept is not missing:
                    cleaned[key] = kept
            return cleaned
        if isinstance(value, list):
            return [kept for item in value if (kept := remove(item)) is not missing]
        return missing if optional(value) else value

    for path in Path(stage).rglob('*.json'):
        source = path.read_bytes()
        if b'box_summary_3d' in source or b'pair_distribution_detail' in source:
            write(path, remove(json.loads(source)))
    for path in Path(stage).rglob('*'):
        if path.is_file() and any(name in path.name for name in OPTIONAL_PLOTS):
            path.unlink()
    require(not any(any(name in str(path) for name in OPTIONAL_PLOTS)
                    for path in Path(stage).rglob('*') if path.is_file()),
            'Optional plot file remains in preview stage')
    require(not any(any(name.encode() in path.read_bytes() for name in OPTIONAL_PLOTS)
                    for path in Path(stage).rglob('*.json')),
            'Optional plot link remains in preview JSON')


def accepted(folder, expected_sha, target, kind):
    folder = Path(folder)
    receipt_path = folder / 'acceptance.json'
    require(digest(receipt_path) == expected_sha,
            f'{kind} receipt hash differs at {receipt_path}: expected {expected_sha}, '
            f'found {digest(receipt_path)}')
    value = read(receipt_path)
    require(value['status'] == 'validated' and value['target'] == target and
            value['models'] == 5000 and
            value['plan_sha256'] == (JOINT_PLAN_SHA if kind == 'joint' else SUPPLEMENT_PLAN_SHA),
            kind + ' acceptance identity differs')
    if kind == 'supplement':
        require(value['energy_count'] == value['median_models'] == value['variance_models'] == 5000 and
                value['representative_views'] == ['leaf', 'eom', 'knn'] and
                value['representative_kind'] == 'lowest-energy member, not structural medoid',
                'Supplement scope differs')
        require(set(value['files']) == {
            'pca-2d.npy', 'tsne-2d.npy',
            'median-ca-distances.npy', 'variance-ca-distances.npy',
            'median-ca-distances.png', 'variance-ca-distances.png',
            'representatives-leaf.json', 'representatives-eom.json',
            'representatives-knn.json'}, 'Supplement file inventory differs')
        for name, expected in value['files'].items():
            require(digest(folder / name) == expected, 'Supplement file differs: ' + name)
    return value


def checked_array(path, expected, shape, *, finite=True):
    require(digest(path) == expected, 'Accepted numeric file differs: ' + Path(path).name)
    array = np.load(path, allow_pickle=False)
    require(array.shape == shape and (not finite or np.isfinite(array).all()),
            'Invalid accepted numeric shape or values: ' + Path(path).name)
    return array


def roster(folder, acceptance):
    path = Path(folder) / 'model-index.jsonl'
    require(digest(path) == acceptance['model_index_sha256'], 'Joint model index differs')
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    require(len(rows) == 5000 and all(row['index'] == i for i, row in enumerate(rows)) and
            len({row['model_id'] for row in rows}) == 5000 and
            len({row['native_sha256'] for row in rows}) == 5000 and
            all(np.isfinite(row['energy_t010']) and
                re.fullmatch(r'[A-Za-z0-9_.-]+', row['model_id']) for row in rows),
            'Joint model identities or energies differ')
    labels = [row['method'] + ('_' + row['weights_version'] if row['method'] == 'afsample2' else '')
              for row in rows]
    require(Counter(labels) == acceptance['method_counts'] == dict.fromkeys(METHODS, 1000),
            'Joint method/weights counts differ')
    return rows, labels


def view_arrays(folder, acceptance):
    folder = Path(folder)
    umap = next(row for row in acceptance['umap_fits']
                if row['dimensions'] == 2 and row['seed'] == 42)
    xy = checked_array(folder / 'umap-2d-seed-42.npy', umap['embedding_sha256'], (5000, 2))
    labels = {'knn': checked_array(folder / 'umap-knn-labels.npy',
                                   acceptance['umap_knn_labels_sha256'], (5000,))}
    strengths = {}
    for view in ('leaf', 'eom'):
        row = next(item for item in acceptance['hdbscan_fits']
                   if item['method'] == view and item['seed'] == 42)
        path = folder / f'hdbscan-{view}-seed-42.npz'
        require(digest(path) == row['labels_sha256'], view + ' labels differ')
        with np.load(path, allow_pickle=False) as saved:
            require(set(saved.files) == {'labels', 'probabilities'}, view + ' fields differ')
            labels[view] = saved['labels'].copy()
            strengths[view] = saved['probabilities'].copy()
        require(labels[view].shape == strengths[view].shape == (5000,) and
                np.isfinite(strengths[view]).all() and
                np.all((0 <= strengths[view]) & (strengths[view] <= 1)) and
                len(set(labels[view]) - {-1}) == row['clusters'] and
                int(np.sum(labels[view] == -1)) == row['unassigned_models'],
                view + ' accepted counts/strengths differ')
    require(labels['knn'].dtype.kind in 'iu' and all(x.dtype.kind in 'iu' for x in labels.values()) and
            len(set(labels['knn'])) == acceptance['umap_knn_clusters'],
            'Cluster labels must be integers')
    return xy, labels, strengths


def color(label):
    # Stable display palette; this does not change any scientific label.
    seed = int(hashlib.sha256(label.encode()).hexdigest()[:6], 16)
    import colorsys
    red, green, blue = colorsys.hsv_to_rgb((seed % 360) / 360, .58, .76)
    return '#%02x%02x%02x' % (round(red * 255), round(green * 255), round(blue * 255))


def cluster_label(view, value):
    return 'Unassigned' if int(value) == -1 else f'{VIEWS[view][1]} {int(value)}'


def verified_representatives(folder, target, view, labels, rows):
    selection = read(Path(folder) / f'representatives-{view}.json')
    require(selection['status'] == 'validated' and selection['target'] == target and
            selection['view'] == view and selection['models'] == 5000 and
            selection['plan_sha256'] == SUPPLEMENT_PLAN_SHA and
            selection['representative_kind'] == 'energy-selected, not structural medoid',
            'Representative selection identity differs')
    found = {int(group['cluster']): group for group in selection['clusters']}
    require(set(found) == set(map(int, labels)) - {-1} and
            selection['unassigned_count'] == int(np.sum(labels == -1)),
            'Representative cluster coverage differs')
    by_id = {row['model_id']: row for row in rows}
    for label, group in found.items():
        members = [rows[i] for i in np.flatnonzero(labels == label)]
        winner = min(members, key=lambda row: (row['energy_t010'], row['model_id']))
        chosen = group['representative']
        require(group['size'] == len(members) and
                chosen['model_id'] == winner['model_id'] and
                chosen['native_sha256'] == winner['native_sha256'] and
                chosen['energy_t010'] == winner['energy_t010'] and
                by_id[chosen['model_id']] is winner,
                'Saved representative differs from accepted energy selection')
    return found


def accepted_bonsai(fit_root, export_root, target, view, joint_folder, joint,
                    joint_sha, supplement_folder, labels, rows, selections):
    name = f'{target}-joint-{view}'
    receipt_path = Path(fit_root) / name / 'acceptance.json'
    viewer_path = Path(export_root) / name / 'bonsai.json'
    receipt_sha = BONSAI_RECEIPTS[target][view]
    viewer_sha = BONSAI_EXPORTS[target][view]
    require(digest(receipt_path) == receipt_sha, 'Bonsai fit receipt differs: ' + name)
    require(digest(viewer_path) == viewer_sha, 'Bonsai viewer export differs: ' + name)
    fit, viewer = read(receipt_path), read(viewer_path)
    selection_sha = digest(Path(supplement_folder) / f'representatives-{view}.json')
    require(fit['status'] == 'validated' and fit['target'] == target and
            fit['view'] == view and fit['plan_sha256'] == BONSAI_PLAN_SHA and
            fit['joint_receipt_sha256'] == joint_sha and
            fit['selection_sha256'] == selection_sha and
            fit['sketch_sha256'] == joint['joint_sketch_sha256'] and
            fit['model_index_sha256'] == joint['model_index_sha256'] and
            fit['residue_scope'] == joint['residue_scope'],
            'Bonsai accepted fit provenance differs: ' + name)
    selected = fit['selected_models']
    expected_reps = {group['representative']['model_id'] for group in selections.values()}
    selected_ids = [model['model_id'] for model in selected]
    require(len(selected_ids) == len(set(selected_ids)) == len(viewer['models']) and
            fit['selected_representatives'] == len(expected_reps) and
            expected_reps <= set(selected_ids) and
            len(selected_ids) == viewer['provenance']['selected_models'],
            'Bonsai selected-model coverage differs: ' + name)
    by_id = {row['model_id']: (i, row) for i, row in enumerate(rows)}
    for saved, plotted in zip(selected, viewer['models']):
        identifier = saved['model_id']
        require(identifier in by_id, 'Bonsai model outside accepted cohort: ' + identifier)
        index, row = by_id[identifier]
        require(all(saved[key] == row[key] for key in
                    ('native_sha256', 'method', 'weights_version',
                     'native_physicality_status', 'energy_t010')) and
                saved['cluster_label'] == int(labels[index]) and
                plotted['model'] == identifier and
                plotted['original_cluster_label'] == saved['cluster_label'] and
                plotted['selection_role'] == saved['role'] and
                all(plotted[key] == saved[key] for key in
                    ('method', 'weights_version', 'native_physicality_status', 'energy_t010')),
                'Bonsai model identity or cluster label differs: ' + identifier)
    provenance = viewer['provenance']
    require(viewer['schema_version'] == 1 and
            provenance['acceptance_sha256'] == receipt_sha and
            provenance['plan_sha256'] == BONSAI_PLAN_SHA and
            all(provenance[key] == fit[key] for key in
                ('selection_sha256', 'sketch_sha256', 'model_index_sha256',
                 'tree_sha256', 'hdf_sha256')) and
            len(viewer['layouts']) == 3 and
            {layout['key'] for layout in viewer['layouts']} ==
                {'ly_eq_angle', 'ly_eq_daylight', 'ly_dendrogram_ladderized'},
            'Bonsai viewer provenance or layouts differ: ' + name)
    for layout in viewer['layouts']:
        nodes = np.asarray(layout['nodes'], dtype=float)
        require(nodes.ndim == 2 and nodes.shape[1] == 2 and
                np.isfinite(nodes).all() and
                all(0 <= model['vertex'] < len(nodes) for model in viewer['models']),
                'Bonsai layout vertices differ: ' + name)
    return viewer_path, viewer_sha, selected_ids


def accepted_tm(folder, receipt_sha, target, view, supplement_folder, selections,
                labels):
    folder = Path(folder)
    receipt_path = folder / 'acceptance.json'
    require(digest(receipt_path) == receipt_sha, 'TM-grid receipt differs: ' + target)
    receipt = read(receipt_path)
    require(receipt['status'] == 'validated' and receipt['target'] == target and
            receipt['models'] == 5000 and receipt['plan_sha256'] == TM_PLAN_SHA and
            receipt['protocol'] == 'USalign -mol prot -ter 1 -TMscore 2 -a T; fixed CDK2 A/DOC1 B; no chain swapping',
            'TM-grid accepted identity or protocol differs: ' + target)
    json_name = f'tm-grid-{view}.json'
    csv_name = f'tm-grid-{view}.csv'
    for name in (json_name, csv_name):
        require(digest(folder / name) == receipt['files'][name],
                'TM-grid accepted file differs: ' + name)
    grid = read(folder / json_name)
    groups = read(Path(supplement_folder) / f'representatives-{view}.json')['clusters']
    expected = selections
    matrix = np.asarray(grid['matrix'], dtype=float)
    n = len(groups)
    require(grid['target'] == target and grid['view'] == view and
            grid['models_fit'] == 5000 and
            grid['method'] == 'fixed-chain whole-complex bidirectional average-length USalign TM' and
            grid['representatives_source_sha256'] ==
                digest(Path(supplement_folder) / f'representatives-{view}.json') and
            grid['groups'] == [{key: group[key] for key in
                                ('cluster', 'size', 'representative')} for group in groups] and
            set(int(group['cluster']) for group in groups) == set(expected) and
            grid['unassigned_count'] == int(np.sum(labels == -1)) and
            receipt['view_counts'][view]['clusters'] == n and
            receipt['view_counts'][view]['unordered_pairs'] == n * (n - 1) // 2 and
            receipt['physicality_rejected_representatives'][view] ==
                sum(group['representative']['native_physicality_status'] == 'rejected'
                    for group in groups) and
            matrix.shape == (n, n) and np.isfinite(matrix).all() and
            np.all((matrix >= 0) & (matrix <= 1)) and
            np.array_equal(matrix, matrix.T) and np.all(np.diag(matrix) == 1),
            'TM-grid correspondence or numeric matrix differs: ' + target + '/' + view)
    return grid, csv_name, receipt['files'][json_name], receipt['files'][csv_name]


def source_coordinate(root, row):
    source = Path(row['native_path'])
    suffix = source.suffix.lower()
    require(suffix in {'.pdb', '.cif', '.mmcif'}, 'Unsupported native coordinate format')
    staged = Path(root) / (row['model_id'] + suffix)
    require(staged.is_file() and digest(staged) == row['native_sha256'],
            'Representative coordinate missing or changed: ' + row['model_id'])
    return staged, suffix


def canonical_afsample2_pdb(raw, target):
    """Map native AFsample2 B/C to display A/B without changing other PDB bytes."""
    expected = {b'B': 298, b'C': 115 if target == 'CDK2_DOC1' else 55}
    mapped = {b'B': b'A', b'C': b'B'}
    ca = Counter()
    lines = []
    for line in raw.splitlines(keepends=True):
        if line.startswith((b'ATOM  ', b'HETATM', b'ANISOU', b'SIGATM', b'SIGUIJ', b'TER   ')):
            require(len(line) > 21 and line[21:22] in mapped,
                    'AFsample2 native PDB has an unexpected coordinate chain')
            native = line[21:22]
            if line.startswith(b'ATOM  ') and line[12:16] == b' CA ':
                ca[native] += 1
            line = line[:21] + mapped[native] + line[22:]
        lines.append(line)
    require(ca == expected, 'AFsample2 PDB Cα chain counts differ from full construct')
    display = b''.join(lines)
    display_ca = Counter(line[21:22] for line in display.splitlines()
                         if line.startswith(b'ATOM  ') and line[12:16] == b' CA ')
    require(display_ca == {b'A': expected[b'B'], b'B': expected[b'C']},
            'Display-only PDB chain counts differ')
    return display


def copy_representatives(stage, target, selections, rows, coordinate_root,
                         extra_selected=()):
    selected = {group['representative']['model_id'] for groups in selections.values()
                for group in groups.values()} | set(extra_selected)
    by_id = {row['model_id']: row for row in rows}
    files = {}
    for model in sorted(selected):
        row = by_id[model]
        source, suffix = source_coordinate(coordinate_root, row)
        raw = source.read_bytes()
        relative = f'{target}/joint-models/{model}{suffix}.gz'
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
        descriptor = dict(file=relative,
                          format='cif' if suffix == '.mmcif' else suffix.removeprefix('.'))
        if row['method'] == 'afsample2':
            require(suffix == '.pdb', 'AFsample2 representative is not a native PDB')
            display = canonical_afsample2_pdb(raw, target)
            display_name = f'{target}/joint-display/{model}.pdb.gz'
            display_path = stage / display_name
            display_path.parent.mkdir(parents=True, exist_ok=True)
            display_path.write_bytes(gzip.compress(display, compresslevel=9, mtime=0))
            descriptor.update(display_file=display_name,
                              display_sha256=hashlib.sha256(display).hexdigest())
        files[model] = descriptor
    return files


def view_payload(target, view, rows, methods, labels, strengths, projections,
                 supplement, selection, coordinates, downloads, joint_sha, supplement_sha,
                 physicality, bonsai, bonsai_models, tm_grid=None):
    names = [row['model_id'] for row in rows]
    cluster_names = [cluster_label(view, label) for label in labels]
    palette = {label: color(label) for label in set(cluster_names)}
    reps = []
    for label, group in sorted(selection.items()):
        chosen = group['representative']
        model = chosen['model_id']
        coordinate = coordinates[model]
        flagged = chosen['native_physicality_status'] not in {'pass', 'passed', 'not_assessed', ''}
        method = METHODS[chosen['method'] + ('_' + chosen['weights_version']
                           if chosen['method'] == 'afsample2' else '')]
        if flagged:
            method += ' · flagged native physicality failure'
        reps.append(dict(cluster=cluster_label(view, label), count=group['size'],
                         model=model, method=method, color=palette[cluster_label(view, label)],
                         **coordinate, sha256=chosen['native_sha256'],
                         native_physicality_status=chosen['native_physicality_status'],
                         energy_t010=chosen['energy_t010']))
    energy = [row['energy_t010'] for row in rows]
    schemes = [dict(key='clusters', name='Clusters', type='categorical',
                    values=cluster_names, colors=palette),
               dict(key='methods', name='Generation method / AFsample2 weights',
                    type='categorical', values=methods, colors=METHOD_COLORS),
               dict(key='protein_ebm_energy_t10', name='ProteinEBM energy · t=0.10',
                    type='continuous', values=energy, colorscale='Viridis',
                    range=[min(energy), max(energy)], unavailable=False,
                    units='learned arbitrary units', lower_is_better=True),
               dict(key='native_physicality', name='Native physicality status',
                    type='categorical', values=[row['native_physicality_status'] for row in rows],
                    colors={'': '#868e9a', 'pass': '#37845a', 'passed': '#37845a',
                            'rejected': '#c24b42', 'not_assessed': '#868e9a'})]
    if view in strengths:
        schemes.append(dict(key='hdbscan_strength', name='HDBSCAN membership strength',
                            type='continuous', values=strengths[view].tolist(),
                            colorscale='Viridis', range=[0, 1], unavailable=False))
    note = ('DOC1t EOM seed diagnostic is unstable: seed 42 found 39 clusters; '
            'seeds 7 and 123 found 21 and 55. Treat EOM groups as exploratory.'
            if target == 'CDK2_DOC1t' and view == 'eom' else '')
    payload = dict(target=target, target_label=('CDK2–DOC1' if target == 'CDK2_DOC1' else 'CDK2–DOC1t') +
                ' · joint 5,000-model cohort', view_id=VIEWS[view][0],
                view_title=f'{target} · {VIEWS[view][1]} · joint five-method cohort',
                models=names, residues=sum(supplement['chain_lengths']), methods=methods,
                clusters=cluster_names, projections=projections, schemes=schemes,
                representatives=reps,
                bonsai=bonsai,
                bonsai_models=bonsai_models,
                views=[dict(id=key, name=name, data=f'{target}/joint-{key}.json')
                       for key, name in [('density', 'HDBSCAN leaf'),
                                         ('primary', 'UMAP KNN'),
                                         ('eom', 'HDBSCAN EOM · diagnostic')]],
                membership_file=downloads,
                heatmaps=[dict(name='Median Cα distance · 5,000 models',
                               file=f'{target}/joint-figures/median-ca-distances.png'),
                          dict(name='Cα distance variance · 5,000 models',
                               file=f'{target}/joint-figures/variance-ca-distances.png')],
                representative_kind='lowest-ProteinEBM-energy cluster member, not a structural medoid',
                representative_policy=('One accepted lowest-ProteinEBM-energy model per assigned '
                    'cluster; tied energies resolve by model ID. Physicality-rejected BioEMU2 '
                    'frames are retained and explicitly flagged. These are exploratory geometry '
                    'groups, not validated native states. ' + note),
                mask_note=('Full construct A1–298 + B1–115' if target == 'CDK2_DOC1' else
                           'Full construct A1–298 + B1–55') +
                          '; all residues retained; 5,000 models fit and displayed.',
                clustering_method_note=('Accepted full-construct 4,096-D all-pair sketch, 2-D/10-D '
                    'UMAP, UMAP KNN and 10-D HDBSCAN (leaf/EOM), seed 42. ProteinEBM is an overlay, '
                    'not a fit feature. BioEMU2 native physicality flags are retained. '
                    'Bonsai uses accepted native trees of energy-selected representatives '
                    'and explicit unassigned examples. ' +
                    ('Exact whole-complex TM similarity compares one energy-selected '
                     'representative per cluster. ' if tm_grid is not None else
                     'Between-cluster TM similarity is pending. ') +
                    'Validated structural state '
                    'assignments and MCMC/DISCO sampling '
                    'are pending for this joint cohort. ' + note),
                provenance=dict(joint_fit_receipt_sha256=joint_sha,
                                supplement_receipt_sha256=supplement_sha,
                                bonsai_fit_receipt_sha256=bonsai['fit_receipt_sha256'],
                                fit_models=5000, display_models=5000,
                                geometry_scope='full two-chain construct',
                                method_counts=dict.fromkeys(METHODS, 1000),
                                bioemu2_physicality_counts=physicality,
                                energy='accepted ProteinEBM Model 6, t=0.10, full complex',
                                unavailable=([] if tm_grid is not None else
                                             ['between-cluster TM similarity']) +
                                            ['MCMC/DISCO sampling', 'validated structural states']))
    if tm_grid is not None:
        grid, csv_path, grid_sha, csv_sha = tm_grid
        payload['medoid_tm'] = dict(
            title='TM similarity across energy-selected cluster representatives',
            labels=[cluster_label(view, group['cluster']) for group in grid['groups']],
            matrix=grid['matrix'], csv=csv_path,
            note=('Whole-complex fixed-chain bidirectional USalign TM, average-length '
                  'normalization, one lowest-ProteinEBM-energy model per assigned cluster. '
                  'These are representative similarities, not cluster-wide distributions '
                  'or structural medoids. Physicality-rejected BioEMU2 representatives '
                  'remain flagged in the cluster table.'))
        payload['native_data_links'] = dict(representative_tm_grid=csv_path)
        payload['provenance']['tm_grid_json_sha256'] = grid_sha
        payload['provenance']['tm_grid_csv_sha256'] = csv_sha
    return payload


def patch_curated_eom(stage):
    path = stage / 'app.js'
    old = "range.views.filter(view=>['primary','density'].includes(view.id))"
    body = path.read_text()
    require(body.count(old) == 1, 'Saved explorer curated-view seam differs')
    raw = "current.representatives=raw.representatives.map(row=>{const out={...row};for(const key of ['file','ensemble_file','ensemble_pse'])"
    displayed = "current.representatives=raw.representatives.map(row=>{const out={...row};for(const key of ['file','display_file','ensemble_file','ensemble_pse'])"
    fetch_old = "const response=await fetch(descriptor.file,{cache:'no-cache',signal:AbortSignal.timeout(15000)});"
    fetch_new = "const display=descriptor.display_file||descriptor.file;const response=await fetch(display,{cache:'no-cache',signal:AbortSignal.timeout(15000)});"
    unzip_old = "if(descriptor.file.endsWith('.pdb.gz')||descriptor.file.endsWith('.cif.gz')){"
    unzip_new = "if(display.endsWith('.pdb.gz')||display.endsWith('.cif.gz')){"
    hash_old = "if(digest!==descriptor.sha256)throw Error('Original coordinate hash does not match the selected model.');"
    hash_new = "if(digest!==(descriptor.display_sha256||descriptor.sha256))throw Error('Display coordinate hash does not match the selected model.');"
    chosen_old = 'const current=data,exact=modelIndex!==null,cluster=exact?pointModelDescriptor(current,modelIndex):current.representatives.find(x=>x.cluster===label);'
    chosen_new = 'const current=data,exact=modelIndex!==null,cluster=exact?(bonsaiModelDescriptor(current,modelIndex)||pointModelDescriptor(current,modelIndex)):current.representatives.find(x=>x.cluster===label);'
    bonsai_old = "onChoose:(cluster,model)=>choose(cluster,data.model_files?data.models.indexOf(model):null).catch(fail)"
    bonsai_new = "onChoose:(cluster,model)=>choose(cluster,data.bonsai_models?.[model]?data.models.indexOf(model):data.model_files?data.models.indexOf(model):null).catch(fail)"
    bonsai_insert = '''function bonsaiModelDescriptor(current,index){
 const model=current.models[index],saved=current.bonsai_models?.[model];if(!saved)return null;
 const label=current.clusters[index],palette=current.schemes.find(s=>s.key==='clusters')?.colors||{};
 if(saved.model!==model||!saved.file||!saved.sha256)throw Error('Bonsai model coordinate descriptor differs.');
 return {...saved,cluster:label,count:current.clusters.filter(value=>value===label).length,color:palette[label]||'#808080',exact_model_index:index};
}
'''
    point_anchor = 'function pointModelDescriptor(current,index){'
    range_old = "if(Array.isArray(raw.model_files))current.model_files=raw.model_files.map(path=>rangeAssetPath(path,range));"
    range_new = range_old + "\n if(raw.bonsai_models)current.bonsai_models=Object.fromEntries(Object.entries(raw.bonsai_models).map(([model,row])=>[model,{...row,file:rangeAssetPath(row.file,range),display_file:row.display_file?rangeAssetPath(row.display_file,range):undefined}]));"
    pair_fetch_old = "if(!text){const r=await fetch(c.file,{signal:AbortSignal.timeout(15000)});if(!r.ok)throw Error('Medoid file unavailable');text=await r.text();c.coordinate_text=text}"
    pair_fetch_new = "if(!text)text=await savedCoordinate(c);"
    pair_note_old = ' · medoids of the displayed ensembles`'
    pair_note_new = ' · energy-selected cluster representatives`'
    for needle in (raw, fetch_old, unzip_old, hash_old, chosen_old,
                   bonsai_old, point_anchor, range_old, pair_fetch_old,
                   pair_note_old):
        require(body.count(needle) == 1, 'Saved coordinate display seam differs')
    for before, after in ((old, "range.views.filter(view=>['primary','density','eom'].includes(view.id))"),
                          (raw, displayed), (fetch_old, fetch_new),
                          (unzip_old, unzip_new), (hash_old, hash_new),
                          (chosen_old, chosen_new), (bonsai_old, bonsai_new),
                          (range_old, range_new), (point_anchor, bonsai_insert + point_anchor),
                          (pair_fetch_old, pair_fetch_new),
                          (pair_note_old, pair_note_new)):
        body = body.replace(before, after, 1)
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(body)
    temporary.replace(path)  # Do not edit the hard-linked saved source.


def patch_representative_labels(stage):
    """Use accurate shared labels for both medoids and energy-selected models."""
    path = Path(stage) / 'index.html'
    body = path.read_text()
    for original, generic in (
        ('<th>Medoid method</th>', '<th>Representative method</th>'),
        ('<summary><span>Selected medoid pair</span></summary>',
         '<summary><span>Selected representative pair</span></summary>'),
        ('>Download medoid TM matrix CSV</a>',
         '>Download representative TM matrix CSV</a>'),
        ('>Medoid TM similarity</span>', '>Representative TM similarity</span>'),
    ):
        require(body.count(original) == 1, 'Saved representative label seam differs')
        body = body.replace(original, generic, 1)
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(body)
    temporary.replace(path)


def add_range_catalogs(stage, target, views, supplement):
    ranges_path = stage / 'residue-ranges.json'
    catalog = read(ranges_path)
    target_entry = catalog.setdefault('targets', {}).setdefault(target, {})
    old = target_entry.get('residue_ranges')
    require(not old or not any(item['id'] == 'joint' for item in old),
            'Joint range already exists')
    all_range = dict(id='all', name='AFsample3 · 1,000 models · full construct',
                     available=True, data=f'{target}/primary.json',
                     asset_root='', default_view='whole')
    mask_name = ('A1–298 + B1–115' if target == 'CDK2_DOC1' else 'A1–298 + B1–55')
    joint = dict(id='joint', name='AFsample2 v1/v2/v3 + AFsample3 + BioEMU2 · '
                 '5,000 models · ' + mask_name, available=True,
                 data=f'{target}/joint-density.json', asset_root='', default_view='density',
                 views=[dict(id=view_id, name=VIEWS[view][1], available=True,
                             data=f'{target}/joint-{view_id}.json', source_view_id=view_id,
                             source_data_sha256=digest(stage / target / f'joint-{view_id}.json'),
                             asset_root='')
                        for view, (view_id, _) in VIEWS.items()])
    target_entry['residue_ranges'] = [all_range, joint]
    write(ranges_path, catalog)
    scope_path = stage / 'clustering-residues.json'
    scopes = read(scope_path)
    target_scope = scopes['targets'][target]
    original = target_scope['views']['whole']
    require(original['expected_ca_count'] == sum(supplement['chain_lengths']) and
            [row['expected_ca_count'] for row in original['chains']] == supplement['chain_lengths'],
            'Joint range and saved construct differ')
    target_scope.setdefault('ranges', {})['joint'] = {'views':
        {view_id: {**original, 'reference_ranges': mask_name,
                   'note': 'Full construct; joint 5,000-model cohort; no residue trimming.'}
         for view_id, _ in views.values()}}
    write(scope_path, scopes)


def build_view_set(stage, target, joint_folder, joint_sha, supplement_folder,
                   supplement_sha, coordinate_root, bonsai_root, tm_folder,
                   tm_receipt_sha, *, state_ready=False):
    joint = accepted(joint_folder, joint_sha, target, 'joint')
    supplement = accepted(supplement_folder, supplement_sha, target, 'supplement')
    require(supplement['joint_fit_acceptance_sha256'] == joint_sha and
            joint['residue_scope'] == ('A1-298+B1-115' if target == 'CDK2_DOC1'
                                       else 'A1-298+B1-55'),
            'Supplement and joint fit scopes differ')
    rows, groups = roster(joint_folder, joint)
    xy, labels, strengths = view_arrays(joint_folder, joint)
    if target == 'CDK2_DOC1t':
        eom_seeds = {row['seed']: row['clusters'] for row in joint['hdbscan_fits']
                     if row['method'] == 'eom'}
        require(eom_seeds == {42: 39, 7: 21, 123: 55},
                'DOC1t EOM stability caveat differs from accepted diagnostics')
    pca = checked_array(Path(supplement_folder) / 'pca-2d.npy',
                        supplement['files']['pca-2d.npy'], (5000, 2))
    tsne = checked_array(Path(supplement_folder) / 'tsne-2d.npy',
                         supplement['files']['tsne-2d.npy'], (5000, 2))
    projections = {'pca': {'xy': pca.tolist(), 'axes': ['PC1', 'PC2'],
                           'explained_variance_ratio': supplement['pca_explained_variance_ratio']},
                   'umap': {'xy': xy.tolist(), 'axes': ['UMAP 1', 'UMAP 2']},
                   'tsne': {'xy': tsne.tolist(), 'axes': ['t-SNE 1', 't-SNE 2']}}
    selections = {view: verified_representatives(supplement_folder, target, view,
                                                labels[view], rows) for view in VIEWS}
    if target == 'CDK2_DOC1':
        flagged_leaf = sum(group['representative']['native_physicality_status'] == 'rejected'
                           for group in selections['leaf'].values())
        require(flagged_leaf == 8,
                'DOC1 leaf physicality warning differs from accepted representatives')
    bonsai = {view: accepted_bonsai(bonsai_root, bonsai_root, target, view,
                                   joint_folder, joint, joint_sha, supplement_folder,
                                   labels[view], rows, selections[view]) for view in VIEWS}
    bonsai_ids = {model for _, _, selected in bonsai.values() for model in selected}
    coordinates = copy_representatives(stage, target, selections, rows, coordinate_root,
                                       bonsai_ids)
    by_id = {row['model_id']: row for row in rows}
    bonsai_models = {}
    for model in sorted(bonsai_ids):
        row = by_id[model]
        method = METHODS[row['method'] + ('_' + row['weights_version']
                         if row['method'] == 'afsample2' else '')]
        if row['native_physicality_status'] not in {'pass', 'passed', 'not_assessed', ''}:
            method += ' · flagged native physicality failure'
        bonsai_models[model] = dict(model=model, method=method,
                                   sha256=row['native_sha256'],
                                   native_physicality_status=row['native_physicality_status'],
                                   energy_t010=row['energy_t010'], **coordinates[model])
    figure_root = stage / target / 'joint-figures'
    figure_root.mkdir(parents=True, exist_ok=True)
    for name in ('median-ca-distances.png', 'variance-ca-distances.png'):
        shutil.copyfile(Path(supplement_folder) / name, figure_root / name)
    csv_path = stage / target / 'joint-memberships-and-scores.csv.gz'
    with tempfile.TemporaryFile(mode='w+', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['model_id', 'native_sha256', 'method', 'afsample2_weights_version',
                         'native_physicality_status', 'protein_ebm_energy_t010',
                         'umap_1', 'umap_2', 'pca_1', 'pca_2', 'tsne_1', 'tsne_2',
                         'umap_knn_group', 'hdbscan_leaf_cluster', 'hdbscan_leaf_strength',
                         'hdbscan_eom_cluster', 'hdbscan_eom_strength'])
        for i, row in enumerate(rows):
            writer.writerow([row['model_id'], row['native_sha256'], row['method'],
                             row['weights_version'], row['native_physicality_status'],
                             row['energy_t010'], *xy[i], *pca[i], *tsne[i],
                             int(labels['knn'][i]), int(labels['leaf'][i]),
                             float(strengths['leaf'][i]), int(labels['eom'][i]),
                             float(strengths['eom'][i])])
        stream.seek(0)
        csv_path.write_bytes(gzip.compress(stream.read().encode(), compresslevel=9, mtime=0))
    methods = [METHODS[group] for group in groups]
    for view, (view_id, _) in VIEWS.items():
        viewer_path, viewer_sha, selected = bonsai[view]
        relative = f'{target}/joint-{view_id}-bonsai.json'
        shutil.copyfile(viewer_path, stage / relative)
        bonsai_descriptor = dict(file=relative, sha256=viewer_sha,
                                 fit_receipt_sha256=BONSAI_RECEIPTS[target][view],
                                 selected_models=len(selected),
                                 method='native Bonsai on energy-selected cluster representatives')
        tm_grid = accepted_tm(tm_folder, tm_receipt_sha, target, view,
                              supplement_folder, selections[view], labels[view])
        grid_path = f'{target}/joint-tm-grid-{view}.json'
        csv_path_tm = f'{target}/joint-tm-grid-{view}.csv'
        shutil.copyfile(Path(tm_folder) / f'tm-grid-{view}.json', stage / grid_path)
        shutil.copyfile(Path(tm_folder) / f'tm-grid-{view}.csv', stage / csv_path_tm)
        tm_display = (tm_grid[0], csv_path_tm, tm_grid[2], tm_grid[3])
        payload = view_payload(target, view, rows, methods, labels[view], strengths,
                               projections, supplement, selections[view], coordinates,
                               str(csv_path.relative_to(stage)), joint_sha, supplement_sha,
                               supplement['bioemu2_physicality_counts'], bonsai_descriptor,
                               {model: bonsai_models[model] for model in selected},
                               tm_display)
        payload['provenance']['tm_grid_receipt_sha256'] = tm_receipt_sha
        if state_ready:
            payload['model_sha256'] = [row['native_sha256'] for row in rows]
        write(stage / target / f'joint-{view_id}.json', payload)
    add_range_catalogs(stage, target, VIEWS, supplement)


def checked_joint_state_inputs(target, joint_folder, joint_sha, supplement_folder,
                               tm_folder, state_folder, state_sha,
                               sampling_folder, sampling_sha,
                               state_plan_sha, sampling_plan_sha):
    """Read accepted state/panel outputs; never infer or calculate a state."""
    require(all(re.fullmatch(r'[a-f0-9]{64}', value) for value in
                (state_sha, sampling_sha, state_plan_sha, sampling_plan_sha)),
            'Exact state and sampling plan/receipt hashes are required')
    state_folder, sampling_folder = Path(state_folder), Path(sampling_folder)
    require(digest(state_folder / 'acceptance.json') == state_sha and
            digest(sampling_folder / 'acceptance.json') == sampling_sha,
            'Accepted state or sampling receipt hash differs')
    state_receipt = read(state_folder / 'acceptance.json')
    sample_receipt = read(sampling_folder / 'acceptance.json')
    require(state_receipt['status'] == sample_receipt['status'] == 'validated' and
            state_receipt['target'] == sample_receipt['target'] == target and
            state_receipt['models'] == sample_receipt['models'] == 5000 and
            state_receipt['plan_sha256'] == state_plan_sha and
            sample_receipt['plan_sha256'] == sampling_plan_sha and
            sample_receipt['publication_held'] is True and
            state_receipt['scope'] == 'fixed-chain whole 1:1 complex; no chain swapping',
            'State/sampling accepted identity or scope differs')
    for name in ('states.json', 'member-anchor-tm.npy', 'poses.jsonl'):
        require(digest(state_folder / name) == state_receipt['files'][name],
                'Accepted state artifact differs: ' + name)
    require(digest(sampling_folder / 'sampling-summary.json') ==
            sample_receipt['files']['sampling-summary.json'],
            'Accepted sampling summary differs')
    states = read(state_folder / 'states.json')
    sampling = read(sampling_folder / 'sampling-summary.json')
    joint = accepted(joint_folder, joint_sha, target, 'joint')
    rows, _ = roster(joint_folder, joint)
    names = [row['model_id'] for row in rows]
    by_id = {name: (i, rows[i]) for i, name in enumerate(names)}
    membership = states['membership']
    groups = membership['states']
    supported = [group for group in groups if group['supported']]
    require(states['status'] == sampling['status'] == 'validated' and
            states['target'] == sampling['target'] == target and
            states['models'] == names and
            sampling['models'] == 5000 and
            states['anchors'] == state_receipt['anchors'] and
            len(states['anchors']) in (1, 2, 3) and
            membership['anchors'] == states['anchors'] and
            membership['cutoff'] == 0.7 and
            membership['min_state_size'] == 50 and
            len(membership['labels']) == len(membership['best_tm']) == 5000 and
            membership['assigned_models'] + membership['unassigned_models'] == 5000 and
            state_receipt['supported_states'] == sampling['supported_state_count'] ==
                sample_receipt['supported_states'] == len(supported) and
            state_receipt['unassigned_models'] == sampling['unassigned_models'] ==
                membership['unassigned_models'] and
            sampling['state_receipt_sha256'] == state_sha and
            states['leaf_representatives_sha256'] ==
                digest(Path(supplement_folder) / 'representatives-leaf.json') and
            states['leaf_bonsai_receipt_sha256'] == BONSAI_RECEIPTS[target]['leaf'] and
            states['tm_grid_leaf_sha256'] ==
                read(Path(tm_folder) / 'acceptance.json')['files']['tm-grid-leaf.json'],
            'Accepted state membership or source links differ')
    scores = checked_array(state_folder / 'member-anchor-tm.npy',
                           state_receipt['files']['member-anchor-tm.npy'],
                           (5000, len(states['anchors'])))
    require(np.all((scores >= 0) & (scores <= 1)) and
            np.allclose(scores.max(axis=1), membership['best_tm'], atol=1e-10, rtol=0),
            'Saved member-anchor TM values differ from accepted membership')
    seen = set()
    for group in groups:
        indices = group['indices']
        require(group['id'] in {'S1', 'S2', 'S3'} and
                group['anchor'] == states['anchors'][int(group['id'][1:]) - 1] and
                group['representative'] == group['anchor'] and
                group['count'] == len(indices) == len(set(indices)) and
                group['supported'] == (group['count'] >= 50) and
                group['eligible_for_sampling'] == group['supported'] and
                all(type(i) is int and 0 <= i < 5000 and i not in seen and
                    membership['labels'][i] == group['id'] and
                    membership['best_tm'][i] >= .7 for i in indices),
                'Saved state support or member indices differ')
        seen.update(indices)
    require(len(seen) == membership['assigned_models'] and
            set(membership['unassigned_indices']) == set(range(5000)) - seen and
            all(membership['labels'][i] is None for i in membership['unassigned_indices']),
            'Saved state assignment accounting differs')
    poses = [json.loads(line) for line in (state_folder / 'poses.jsonl').read_text().splitlines()]
    require(len(poses) == 5000 and all(pose['index'] == i and
            pose['model_id'] == names[i] and
            pose['native_sha256'] == rows[i]['native_sha256'] for i, pose in enumerate(poses)),
            'Saved state pose order or native identity differs')
    condition_by_key = {record['condition']: record for record in sampling['conditions']}
    expected_conditions = {group['id'] + '_' + prior for group in supported
                           for prior in ('UMAP_KNN', 'HDBSCAN_leaf')}
    require(set(condition_by_key) == expected_conditions and
            len(sampling['conditions']) == sample_receipt['conditions'] ==
                2 * len(supported) and
            sampling['exact_control_panels'] == sample_receipt['exact_control_panels'] ==
                20 * len(expected_conditions) and
            sampling['exported_coordinate_instances'] ==
                sample_receipt['exported_coordinate_instances'] ==
                100 * len(expected_conditions),
            'Accepted sampling conditions or panel counts differ')
    panels = {}
    for condition, record in condition_by_key.items():
        state_id, prior = condition.split('_', 1)
        group = next(group for group in supported if group['id'] == state_id)
        require(record['state'] == state_id and record['prior'] == prior and
                record['pool_models'] == group['count'] and
                record['production_chain'] == 0 and
                record['production_iteration'] == 10000 and
                record['controls'] == 20 and
                {item['kind'] for item in record['exports']} == {'MCMC50', 'DISCO50'},
                'Saved sampling policy or export inventory differs')
        selected = {}
        for item in record['exports']:
            kind = item['kind']
            method = kind.lower()
            model_ids = item['model_ids']
            require(item['state'] == state_id and item['prior'] == prior and
                    item['models'] == len(model_ids) == len(set(model_ids)) == 50 and
                    set(model_ids) <= {names[i] for i in group['indices']} and
                    item['pdb_file'] == method + '.pdb' and
                    len(item['members']) == 50 and
                    all(member['model_id'] == name and
                        member['native_sha256'] == by_id[name][1]['native_sha256']
                        for member, name in zip(item['members'], model_ids)),
                    'Saved 50-model panel identity or state membership differs')
            source = sampling_folder / condition / item['pdb_file']
            relative = condition + '/' + item['pdb_file']
            require(sample_receipt['files'][relative] == item['pdb_sha256'] ==
                    digest(source) and source.stat().st_size <= 64 * 2**20,
                    'Saved panel coordinate hash or size differs: ' + relative)
            selected[method] = (model_ids, source, item['pdb_sha256'])
        panels[condition] = selected
    return states, sampling, rows, supported, panels


def joint_panel_path(target, prior, state_id, method):
    directory = {'UMAP_KNN': 'primary', 'HDBSCAN_leaf': 'density'}[prior]
    return f'tm-state-ensembles/{target}/joint/{directory}/{state_id}/{method}.pdb'


def add_joint_states(stage, inputs, tm_inputs, state_inputs, state_plan_sha,
                     sampling_plan_sha):
    require(state_plan_sha and sampling_plan_sha and
            set(state_inputs) == set(TARGETS),
            'Both targets and exact approved state/sampling plans are required')
    catalog_path = Path(stage) / 'tm-states.json'
    catalog = read(catalog_path)
    require(catalog['kind'] == 'tm_state_selection_catalog' and
            catalog['schema_version'] in (1, 2) and
            not any(target in catalog['targets'] for target in TARGETS),
            'Saved state catalog differs or joint targets already exist')
    catalog['schema_version'] = 3
    ranges = read(Path(stage) / 'residue-ranges.json')['targets']
    scopes = read(Path(stage) / 'clustering-residues.json')['targets']
    for target in TARGETS:
        joint_folder, joint_sha, supplement_folder, _ = inputs[target]
        tm_folder, _ = tm_inputs[target]
        state_folder, state_sha, sampling_folder, sampling_sha = state_inputs[target]
        states, sampling, rows, supported, panels = checked_joint_state_inputs(
            target, joint_folder, joint_sha, supplement_folder, tm_folder,
            state_folder, state_sha, sampling_folder, sampling_sha,
            state_plan_sha, sampling_plan_sha)
        names = [row['model_id'] for row in rows]
        lookup = {name: i for i, name in enumerate(names)}
        model_hash = hashlib.sha256(json.dumps(names, separators=(',', ':')).encode()).hexdigest()
        lengths = [298, 115 if target == 'CDK2_DOC1' else 55]
        positions = list(range(1, sum(lengths) + 1))
        mask_hash = hashlib.sha256(json.dumps(positions, separators=(',', ':')).encode()).hexdigest()
        sequence_hash = scopes[target]['views']['whole']['sequence_sha256']
        joint_range = next(item for item in ranges[target]['residue_ranges'] if item['id'] == 'joint')
        views = {item['id']: item for item in joint_range['views']}
        require(set(views) == {'primary', 'density', 'eom'} and
                all(views[view]['source_data_sha256'] == digest(Path(stage) / views[view]['data'])
                    for view in views), 'Joint state view hashes differ from saved catalog')
        output_states = []
        for state in supported:
            members = [dict(index=i, model=names[i],
                            tm_score=states['membership']['best_tm'][i],
                            sha256=rows[i]['native_sha256']) for i in state['indices']]
            selections = {'joint': {}}
            for view, prior in [('primary', 'UMAP_KNN'),
                                ('density', 'HDBSCAN_leaf'),
                                ('eom', 'HDBSCAN_leaf')]:
                condition = state['id'] + '_' + prior
                selection = {'prior': prior}
                for method in ('mcmc50', 'disco50'):
                    ids, source, sha = panels[condition][method]
                    relative = joint_panel_path(target, prior, state['id'], method)
                    destination = Path(stage) / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if not destination.exists():
                        shutil.copyfile(source, destination)
                    require(digest(destination) == sha, 'Copied state panel differs')
                    selection[method] = dict(indices=[lookup[name] for name in ids],
                                             models=ids,
                                             ensemble=dict(file=relative, sha256=sha,
                                                           bytes=destination.stat().st_size))
                selections['joint'][view] = selection
            output_states.append(dict(id=state['id'],
                                      representative=dict(index=lookup[state['anchor']],
                                                          model=state['anchor']),
                                      members=members, selections=selections))
        count = sum(state['count'] for state in supported)
        unsupported = [dict(id=state['id'], representative=state['anchor'],
                            count=state['count']) for state in
                       states['membership']['states'] if not state['supported']]
        payload = dict(schema_version=3, kind='tm_state_selection_payload',
                       target=target, effective_scope_id='joint-full-complex',
                       models=names, model_order_sha256=model_hash,
                       model_sha256=[row['native_sha256'] for row in rows],
                       sequence_sha256=sequence_hash, chain='A,B',
                       chains=[dict(chain='AB'[i], residues=length) for i, length in
                               enumerate(lengths)], construct_residues=sum(lengths),
                       canonical_positions=positions, mask_sha256=mask_hash,
                       tm_threshold=.7,
                       run=dict(plan_sha256=state_plan_sha,
                                state_receipt_sha256=state_sha,
                                sampling_plan_sha256=sampling_plan_sha,
                                sampling_receipt_sha256=sampling_sha,
                                source_commit='f3063757460303e1a4a4ba0b3629fe81776c58c4'),
                       selection_prior=dict(conditioning_t=.1, alpha=.5,
                            tau_iqr_multiplier=1, subset_law='product-weight',
                            subset_size=50, production_chain=0,
                            production_iteration=10000,
                            per_view=dict(primary='UMAP_KNN',
                                          density='HDBSCAN_leaf', eom='HDBSCAN_leaf')),
                       ranges={'joint': dict(effective_scope_id='joint-full-complex',
                            views={view: dict(source_data_sha256=entry['source_data_sha256'])
                                   for view, entry in views.items()})},
                       states=output_states,
                       coverage=dict(assigned_models=count,
                                     unassigned_models=5000-count),
                       membership_coverage=dict(
                            tm_assigned_models=states['membership']['assigned_models'],
                            uncovered_models=states['membership']['unassigned_models'],
                            unsupported_state_models=sum(row['count'] for row in unsupported),
                            unsupported_states=unsupported),
                       flags=dict(incomplete_coverage=count<5000, short_core=False),
                       discovery_scope=states['discovery_scope'],
                       interpretation=sampling['interpretation'])
        relative = f'tm-states/{target}/joint-full-complex.json'
        destination = Path(stage) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        write(destination, payload)
        catalog['targets'][target] = dict(model_count=5000,
            model_order_sha256=model_hash, sequence_sha256=sequence_hash,
            ranges={'joint': dict(effective_scope_id='joint-full-complex',
                views={view: dict(file=relative, sha256=digest(destination),
                    state_count=len(output_states), available=True,
                    short_core=False, incomplete_coverage=count<5000,
                    source_data_sha256=entry['source_data_sha256'])
                    for view, entry in views.items()})})
    write(catalog_path, catalog)


def patch_joint_state_browser(stage):
    """Add the joint schema validator without changing legacy HSPH1 validation."""
    html = Path(stage) / 'index.html'
    body = html.read_text()
    needle = '<script defer src="tm_states.js"></script>'
    require(body.count(needle) == 1, 'Saved state script seam differs')
    temporary = html.with_name(html.name + '.new')
    temporary.write_text(body.replace(needle,
        '<script defer src="joint_tm_states.js"></script>' + needle, 1))
    temporary.replace(html)
    shutil.copyfile(ROOT / 'site/joint_tm_states.js', Path(stage) / 'joint_tm_states.js')
    script = Path(stage) / 'tm_states.js'
    body = script.read_text()
    changes = (
        ('[1,2].includes(catalog?.schema_version)',
         '[1,2,3].includes(catalog?.schema_version)'),
        ('function validatePayload(p,entry,target,data){',
         'function validatePayload(p,entry,target,data){\n'
         ' if(p?.schema_version===3)return root.AISJointTMStates.validate(p,entry,target,data,{sourceBinding,sha256});'),
    )
    for old, new in changes:
        require(body.count(old) == 1, 'Saved state validator seam differs')
        body = body.replace(old, new, 1)
    # The legacy ternary above remains intact; add a joint-specific note before it.
    anchor = " details+=s.method==='mcmc50'?"
    require(body.count(anchor) == 1, 'Saved state sampling detail seam differs')
    body = body.replace(anchor,
        " if(payload.schema_version===3)details='Fixed-chain whole-complex TM states; each saved 50-model PDB uses one rigid alignment to its state anchor. The MCMC50 and DISCO50 panels are exploratory coverage selections, not equilibrium populations. ';\n" + anchor, 1)
    old = 'The saved PDB downloads preserve the native full-dimer pose. On-screen filters and colors never change downloaded files.'
    new = "'+(payload.schema_version===3?'The saved PDB downloads are full-atom 1:1 complexes aligned to their state anchor. ':'The saved PDB downloads preserve the native full-dimer pose. ')+'On-screen filters and colors never change downloaded files."
    require(body.count(old) == 1, 'Saved state panel pose description seam differs')
    body = body.replace(old, new, 1)
    temporary = script.with_name(script.name + '.new')
    temporary.write_text(body)
    temporary.replace(script)


def assemble(base, inputs, coordinate_roots, bonsai_root, tm_inputs, output,
             state_inputs=None, state_plan_sha=None, sampling_plan_sha=None):
    sys.path.insert(0, str(ROOT / 'scripts'))
    from build_private_atlas import copy_verified_file
    from src.analysis.atlas_presentation import validate_views
    from structure_clustering.publication import export

    base = Path(base).resolve()
    output = Path(output).resolve()
    require(not output.exists(), 'Use a fresh output directory')
    source = read(base / 'export-manifest.json')
    require(source.get('project') == 'LS_AIS', 'Saved source is not LS_AIS')
    old = {row['path'] for row in source['files']}
    require({f'{target}/primary.json' for target in TARGETS} <= old and
            not any('/joint-' in name for name in old),
            'Saved monomer source is incomplete or already augmented')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ls-ais-joint-preview-', dir=output.parent) as temp:
        stage = Path(temp) / 'source'
        stage.mkdir()
        for row in source['files']:
            if row['path'] not in {'.nojekyll', 'export-manifest.json'}:
                copy_verified_file(base, stage, row)
        omit_optional_plots(stage)
        patch_curated_eom(stage)
        patch_representative_labels(stage)
        menu = Path(__file__).resolve().parents[2] / 'site/cohort_menu.js'
        menu_destination = stage / 'cohort_menu.js'
        menu_new = menu_destination.with_name('cohort_menu.js.new')
        menu_new.write_bytes(menu.read_bytes())
        menu_new.replace(menu_destination)
        for target in TARGETS:
            build_view_set(stage, target, *inputs[target], coordinate_roots[target],
                           bonsai_root, *tm_inputs[target], state_ready=state_inputs is not None)
        if state_inputs is not None:
            add_joint_states(stage, inputs, tm_inputs, state_inputs,
                             state_plan_sha, sampling_plan_sha)
            patch_joint_state_browser(stage)
        names = {str(path.relative_to(stage)) for path in stage.rglob('*') if path.is_file()}
        validate_views(stage, names)
        validate_views(stage, names, selected_views={
            f'{target}/joint-{view_id}.json': target
            for target in TARGETS for view_id, _ in VIEWS.values()})
        manifest = Path(temp) / 'private-manifest.json'
        rows = [dict(path=name, bytes=(stage / name).stat().st_size,
                     sha256=digest(stage / name)) for name in sorted(names)]
        require(sum(row['bytes'] for row in rows) <= 2 * 2**30,
                'Private atlas exceeds the 2 GiB preview ceiling')
        manifest_data = dict(schema_version=1, project='LS_AIS',
            renderer='saved', source_export_sha256=digest(base / 'export-manifest.json'),
            joint_fit_plan_sha256=JOINT_PLAN_SHA,
            supplement_plan_sha256=SUPPLEMENT_PLAN_SHA,
            bonsai_plan_sha256=BONSAI_PLAN_SHA,
            tm_grid_plan_sha256=TM_PLAN_SHA, files=rows)
        if state_inputs is not None:
            manifest_data.update(state_plan_sha256=state_plan_sha,
                                 sampling_plan_sha256=sampling_plan_sha)
        manifest.write_text(json.dumps(manifest_data, indent=2) + '\n')
        record = export(manifest, stage, output)
        (output.parent / 'private-manifest.json').write_bytes(manifest.read_bytes())
        (output.parent / 'delivery-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    for target in TARGETS:
        key = target.lower().replace('_', '-')
        parser.add_argument(f'--{key}-joint', type=Path, required=True)
        parser.add_argument(f'--{key}-joint-sha256', required=True)
        parser.add_argument(f'--{key}-supplement', type=Path, required=True)
        parser.add_argument(f'--{key}-supplement-sha256', required=True)
        parser.add_argument(f'--{key}-coordinates', type=Path, required=True)
        parser.add_argument(f'--{key}-tm', type=Path, required=True)
        parser.add_argument(f'--{key}-tm-sha256', required=True)
        parser.add_argument(f'--{key}-states', type=Path)
        parser.add_argument(f'--{key}-states-sha256')
        parser.add_argument(f'--{key}-sampling', type=Path)
        parser.add_argument(f'--{key}-sampling-sha256')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bonsai-root', type=Path, required=True)
    parser.add_argument('--joint-state-plan-sha256')
    parser.add_argument('--joint-sampling-plan-sha256')
    args = parser.parse_args()
    inputs = {}
    roots = {}
    tm_inputs = {}
    state_inputs = {}
    for target in TARGETS:
        key = target.lower().replace('_', '-')
        inputs[target] = (getattr(args, key.replace('-', '_') + '_joint'),
                          getattr(args, key.replace('-', '_') + '_joint_sha256'),
                          getattr(args, key.replace('-', '_') + '_supplement'),
                          getattr(args, key.replace('-', '_') + '_supplement_sha256'))
        roots[target] = getattr(args, key.replace('-', '_') + '_coordinates')
        tm_inputs[target] = (getattr(args, key.replace('-', '_') + '_tm'),
                             getattr(args, key.replace('-', '_') + '_tm_sha256'))
        values = tuple(getattr(args, key.replace('-', '_') + suffix) for suffix in
                       ('_states', '_states_sha256', '_sampling', '_sampling_sha256'))
        if any(value is not None for value in values):
            require(all(value is not None for value in values),
                    'State/sampling target inputs must be complete')
            state_inputs[target] = values
    optional = [bool(state_inputs), bool(args.joint_state_plan_sha256),
                bool(args.joint_sampling_plan_sha256)]
    require(not any(optional) or
            (all(optional) and set(state_inputs) == set(TARGETS)),
            'Both target state/sampling inputs and approved plan hashes are required')
    assemble(args.base, inputs, roots, args.bonsai_root, tm_inputs, args.output,
             state_inputs or None, args.joint_state_plan_sha256,
             args.joint_sampling_plan_sha256)
