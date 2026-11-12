"""Serialize accepted energy-selected DOC1/CDK2 Bonsai for the atlas viewer.

This reads a completed native run; it never fits a tree. Execute only as part
of a separately approved, hash-frozen scientific export plan.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys


LAYOUTS = (('ly_eq_angle', 'Equal-angle'),
           ('ly_eq_daylight', 'Equal-daylight'),
           ('ly_dendrogram_ladderized', 'Ladderized dendrogram'))


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def need(ok, message):
    if not ok:
        raise ValueError(message)


def export(receipt_path, expected_receipt_sha256, output):
    import h5py
    import numpy as np
    import pandas as pd

    receipt_path = Path(receipt_path)
    output = Path(output)
    need(not output.exists(), 'Use a fresh Bonsai export path')
    need(sha(receipt_path) == expected_receipt_sha256, 'Bonsai acceptance hash differs')
    receipt = json.loads(receipt_path.read_text())
    need(receipt['status'] == 'validated' and receipt['plan_sha256']
         and receipt['selection_sha256'] and receipt['sketch_sha256'],
         'Bonsai run was not accepted')
    root = receipt_path.parent
    selected = receipt['selected_models']
    need(sum(row['role'] == 'energy_selected_representative' for row in selected)
         == receipt['selected_representatives'],
         'Energy-selected representative count differs')
    names = [row['model_id'] for row in selected]
    need(len(names) >= 3 and len(names) == len(set(names)),
         'Bonsai selection is empty or duplicated')
    files = receipt['input_audit']['files_sha256']
    required = {'input_audit/model_order.json',
                'input_audit/source_models_by_features.npy',
                'input_audit/bonsai_models_by_features.npy',
                'input/features.txt', 'input/cellID.txt', 'input/geneID.txt'}
    need(required.issubset(files), 'Incomplete native input audit')
    for relative, digest in files.items():
        path = (root / relative).resolve()
        need(path.is_relative_to(root.resolve()) and sha(path) == digest,
             'Native input audit hash differs')
    need(json.loads((root / 'input_audit/model_order.json').read_text()) == names,
         'Native input model order differs')
    tree_paths = list(root.glob('final_bonsai_zscore*/tree.nwk'))
    need(len(tree_paths) == 1 and sha(tree_paths[0]) == receipt['tree_sha256']
         == receipt['tree_grouping']['tree_sha256'],
         'Accepted native tree differs')
    hdf = root / 'bonsai_vis_data.hdf'
    cells = pd.read_hdf(hdf, key='cell_info/cell_info_dict')
    need(cells.index.is_unique and set(cells.index) == set(names),
         'Native Bonsai cell identities differ')
    vertices = []
    for name in names:
        value = cells.loc[name, 'cell_ind_to_vert_ind']
        need(np.isfinite(value) and int(value) == value and value >= 0,
             'Native Bonsai vertex is invalid')
        vertices.append(int(value))
    layouts = []
    with h5py.File(hdf, 'r') as source:
        need(json.loads(source.attrs['metadata_json'])['cellIds'] == names,
             'Native Bonsai HDF model order differs')
        for key, title in LAYOUTS:
            nodes = source['layout_coords/node_coords/' + key][()]
            edges = source['layout_coords/edge_coords/' + key][()]
            need(nodes.ndim == 2 and nodes.shape[1] == 2 and np.isfinite(nodes).all()
                 and all(vertex < len(nodes) for vertex in vertices),
                 'Native Bonsai node geometry is invalid')
            need(edges.ndim == 3 and edges.shape[2] == 2 and edges.shape[1] >= 2
                 and np.isfinite(edges).all(), 'Native Bonsai edge geometry is invalid')
            layouts.append({'key': key, 'title': title,
                            'nodes': nodes.tolist(), 'edges': edges.tolist()})
    assignments = receipt['tree_grouping']['assignments']
    need(set(assignments) == set(names), 'Native Bonsai group identities differ')
    payload = {'schema_version': 1,
               'models': [{'model': name, 'vertex': vertex,
                           'bonsai_group': assignments[name]['bonsai_group'],
                           'original_cluster_label': row['cluster_label'],
                           'selection_role': row['role']}
                          for name, vertex, row in zip(names, vertices, selected, strict=True)],
               'layouts': layouts,
               'method': 'Native Bonsai on one lowest-ProteinEBM-energy model per '
                         'assigned cluster plus explicit low-energy unassigned '
                         'examples, using accepted 4096-dimensional all-pair '
                         'sketch rows; all nonzero PCA axes; no whitening or variance scaling. '
                         'The sketch approximates exact all-pair Euclidean distances.',
               'scope': (f"{receipt['target']} · {receipt['range']} · {receipt['partition']}; "
                         'lowest full-complex ProteinEBM Model 6 t=0.10 energy '
                         'per assigned cluster and up to five low-energy unassigned '
                         'examples; active full/core geometry only. '
                         'Energy selection does not imply structural centrality.'),
               'group_count': receipt['tree_grouping']['selected']['k'],
               'provenance': {'acceptance_sha256': expected_receipt_sha256,
                              'plan_sha256': receipt['plan_sha256'],
                              'selection_sha256': receipt['selection_sha256'],
                              'sketch_sha256': receipt['sketch_sha256'],
                              'model_index_sha256': receipt['model_index_sha256'],
                              'hdf_sha256': sha(hdf), 'tree_sha256': receipt['tree_sha256'],
                              'model_order_sha256': files['input_audit/model_order.json'],
                              'selected_models': len(names),
                              'retained_first_ab': receipt['input_audit']['source']['first_retained_ab']}}
    output.parent.mkdir(parents=True, exist_ok=False)
    output.write_text(json.dumps(payload, separators=(',', ':'), allow_nan=False) + '\n')
    print(json.dumps({'view': receipt['view'], 'selected_models': len(names),
                      'output_sha256': sha(output)}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--view-index', type=int, required=True)
    args = parser.parse_args()
    need(sha(args.plan) == args.plan_sha256, 'Frozen Bonsai export plan differs')
    plan = json.loads(args.plan.read_text())
    need(plan['operation'] == 'doc1_cdk2_energy_representative_bonsai'
         and plan['scientific_export'] is True and plan['paid_external_calls'] == 0
         and len(plan['views']) == 12
         and 0 <= args.view_index < len(plan['views']),
         'Unexpected Bonsai export operation or view')
    need(sha(__file__) == plan['export_source_sha256']
         and sha(sys.executable) == plan['runtime_python_sha256'],
         'Bonsai export source or runtime differs')
    view = plan['views'][args.view_index]
    receipt_path = Path(plan['output_root']) / view['id'] / 'acceptance.json'
    receipt = json.loads(receipt_path.read_text())
    need(receipt['plan_sha256'] == args.plan_sha256
         and receipt['view'] == view['id']
         and receipt['selection_sha256'] == view['selection_sha256']
         and receipt['sketch_sha256'] == view['sketch_sha256'],
         'Native Bonsai receipt differs from approved view')
    export(receipt_path, sha(receipt_path),
           Path(plan['export_output_root']) / view['id'] / 'bonsai.json')
