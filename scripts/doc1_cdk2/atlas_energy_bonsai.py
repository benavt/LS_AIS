"""Native Bonsai trees for accepted energy-selected DOC1/CDK2 representatives.

Scientific execution requires a separately approved, hash-frozen Mimas plan.
Each view selects its own lowest-ProteinEBM-energy cluster representatives and
explicit unassigned examples, then
uses the accepted residue-mask-specific all-pair sketch geometry.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(path, expected):
    require(digest(path) == expected, f'SHA-256 mismatch: {Path(path).name}')


def load_plan(path, expected):
    checked(path, expected)
    plan = json.loads(Path(path).read_text())
    require(plan['operation'] == 'doc1_cdk2_energy_representative_bonsai'
            and plan['scientific_execution'] is True
            and plan['paid_external_calls'] == 0
            and len(plan['views']) == 12
            and plan['selection_policy'] == 'minimum accepted full-complex ProteinEBM '
                 'Model 6 t=0.10 energy per assigned cluster; tie by lexicographic '
                 'model ID; preserve five lowest-energy members and up to five '
                 'lowest-energy unassigned examples; if fewer than three selected '
                 'models, add the second-lowest-energy member of each cluster'
            and plan['geometry'] == 'accepted 4096-dimensional all-pair sketch '
                 'for the active full/core residue mask; nonzero PCA without whitening',
            'Unapproved Bonsai operation or selection')
    for name, source in (('source', __file__), ('runtime_python', sys.executable),
                         ('library_geometry', plan['library_geometry_path']),
                         ('library_layout', plan['library_layout_path']),
                         ('library_native', plan['library_native_path'])):
        checked(source, plan[name + '_sha256'])
    root = Path(plan['library_native_path']).parents[1]
    sys.path[:0] = [str(root), str(root / 'scripts')]
    os.environ['BONSAI_ROOT'] = plan['bonsai_root']
    from src.analysis.bonsai_runtime import runtime_compatibility_metadata
    compatible = runtime_compatibility_metadata(Path(plan['bonsai_root']))
    compatible_hash = hashlib.sha256(json.dumps(compatible, sort_keys=True).encode()).hexdigest()
    require(compatible_hash == plan['bonsai_runtime_compatibility_sha256'],
            'Bonsai engine compatibility differs')
    plan['_sha256'] = expected
    return plan


def selected_models(selection, view):
    require(selection['status'] == 'validated'
            and selection['operation'] == 'energy_cluster_representatives'
            and selection['plan_sha256'] == view['energy_selection_plan_sha256']
            and selection['view'] == view['id']
            and selection['target'] == view['target']
            and selection['range'] == view['range']
            and selection['partition'] == view['partition']
            and selection['first_retained_ab'] == view['first_retained_ab']
            and len(selection['clusters']) == view['clusters']
            and selection['models'] == view['models'],
            'Bonsai energy selection differs')
    chosen = []
    for group in selection['clusters']:
        model = group['representative']
        require(group['lowest_energy_members'][0] == model,
                'Cluster energy representative differs from ranking')
        chosen.append({'model_id': model['model_id'],
                       'native_sha256': model['native_sha256'],
                       'cluster_label': int(group['cluster']),
                       'role': 'energy_selected_representative',
                       'protein_ebm_full_complex_energy_t010':
                           model['protein_ebm_full_complex_energy_t010']})
    for model in selection['unassigned_examples'][:5]:
        chosen.append({'model_id': model['model_id'],
                       'native_sha256': model['native_sha256'],
                       'cluster_label': -1, 'role': 'unassigned_example',
                       'protein_ebm_full_complex_energy_t010':
                           model['protein_ebm_full_complex_energy_t010']})
    if len(chosen) < 3:
        for group in selection['clusters']:
            if len(group['lowest_energy_members']) > 1:
                model = group['lowest_energy_members'][1]
                chosen.append({'model_id': model['model_id'],
                               'native_sha256': model['native_sha256'],
                               'cluster_label': int(group['cluster']),
                               'role': 'second_lowest_energy_member',
                               'protein_ebm_full_complex_energy_t010':
                                   model['protein_ebm_full_complex_energy_t010']})
            if len(chosen) >= 3:
                break
    require(3 <= len(chosen) == view['selected_models'] <= view['clusters'] + 5 + 1
            and len({row['model_id'] for row in chosen}) == len(chosen),
            'Invalid Bonsai view-specific selection')
    return chosen


def run(plan, task):
    import numpy as np
    from src.analysis.bonsai_geometry import (nonzero_pca_features,
                                              record_input_audit, native_tree_groups)
    from src.app.shared.bonsai_ensemble_workflow import export_tree_layouts
    import bonsai_clustering as native

    require(0 <= task < len(plan['views']), 'Invalid Bonsai task')
    view = plan['views'][task]
    for name in ('selection', 'model_index', 'sketch', 'clustering_receipt'):
        checked(view[name + '_path'], view[name + '_sha256'])
    selection = json.loads(Path(view['selection_path']).read_text())
    receipt = json.loads(Path(view['clustering_receipt_path']).read_text())
    require(selection['plan_sha256'] == plan['energy_selection_plan_sha256']
            and receipt['status'] == 'validated'
            and receipt['target'] == view['target']
            and receipt['models'] == view['models']
            and receipt['sketch_sha256'] == view['sketch_sha256'],
            'Bonsai accepted source identity differs')
    chosen = selected_models(selection, view)
    index = [json.loads(line) for line in Path(view['model_index_path']).read_text().splitlines()]
    require(len(index) == view['models']
            and len({row['model_id'] for row in index}) == len(index),
            'Bonsai model order differs')
    lookup = {row['model_id']: i for i, row in enumerate(index)}
    require(all(row['model_id'] in lookup
                and index[lookup[row['model_id']]]['native_sha256'] == row['native_sha256']
                for row in chosen), 'Bonsai selected native hashes differ')
    require(Path(view['sketch_path']).stat().st_size == view['models']*4096*4,
            'Bonsai sketch byte count differs')
    sketch = np.memmap(view['sketch_path'], dtype='<f4', mode='r',
                       shape=(view['models'], 4096))
    matrix = np.asarray(sketch[[lookup[row['model_id']] for row in chosen]],
                        dtype=np.float64)
    require(matrix.shape == (len(chosen), 4096) and np.isfinite(matrix).all(),
            'Bonsai selected sketch rows differ')
    scores, projection = nonzero_pca_features(matrix)
    require(projection['distance_geometry_preserved']
            and projection['retained_components'] <= len(chosen)-1,
            'Bonsai sketch geometry was truncated')
    output = Path(plan['output_root']) / view['id']
    output.mkdir(parents=True, exist_ok=False)
    names = [row['model_id'] for row in chosen]
    annotation = [{'cellID': row['model_id'],
                   'original_umap_cluster': row['cluster_label'],
                   'selection_role': row['role']} for row in chosen]
    written = native.write_bonsai_input_files(scores, names, output,
                                              annotation_rows=annotation)
    audit = record_input_audit(output, matrix, scores, names, projection,
                               source={'kind': 'accepted_all_pair_sketch',
                                       'sketch_sha256': view['sketch_sha256'],
                                       'model_index_sha256': view['model_index_sha256'],
                                       'selection_sha256': view['selection_sha256'],
                                       'residue_scope': view['range'],
                                       'first_retained_ab': view['first_retained_ab'],
                                       'limitations': 'The frozen 4096-dimensional sketch '
                                                      'approximates the exact all-pair '
                                                      'Euclidean geometry.'})
    use_knn = 10 if len(chosen) > 64 else -1
    native.run_bonsai_subprocesses(
        results_dir=output, input_dir=written['input_dir'],
        identifier=view['id'], annotation_dir=written['annotation_dir'],
        status_callback=lambda message: print(message, flush=True),
        rescale_by_var=False, use_knn=use_knn, preprocess=False)
    tree = output / f'final_bonsai_zscore{native.DEFAULT_ZSCORE_CUTOFF}' / 'tree.nwk'
    require(tree.is_file(), 'Native Bonsai tree missing')
    grouping = native_tree_groups(tree, names, native.bonsai_submodule_root())
    (output / 'tree_groups.json').write_text(json.dumps(grouping, indent=2) + '\n')
    colors = grouping['assignments']
    display = []
    for row in chosen:
        assigned = colors[row['model_id']]
        display.append({'model': row['model_id'],
                        'original_cluster_label': row['cluster_label'],
                        'selection_role': row['role'],
                        'original_color': '#808080',
                        'bonsai_group': assigned['bonsai_group'],
                        'bonsai_color': assigned['bonsai_color'],
                        'cluster_label': assigned['bonsai_group'],
                        'color': assigned['bonsai_color'],
                        'display_label': f"Cluster {row['cluster_label']} · {row['role']}"})
    native.write_annotation_csv(written['annotation_dir'], names,
                                [{'cellID': row['model'],
                                  'cluster': row['bonsai_group'],
                                  'original_umap_cluster': row['original_cluster_label'],
                                  'selection_role': row['selection_role']}
                                 for row in display])
    native.preprocess_bonsai_results(output, annotation_dir=written['annotation_dir'],
                                     status_callback=lambda message: print(message, flush=True))
    panels = export_tree_layouts(output, display)
    result = {'status': 'validated', 'plan_sha256': plan['_sha256'],
              'view': view['id'], 'target': view['target'],
              'range': view['range'], 'partition': view['partition'],
              'selection_sha256': view['selection_sha256'],
              'sketch_sha256': view['sketch_sha256'],
              'model_index_sha256': view['model_index_sha256'],
              'selected_representatives': view['clusters'],
              'selected_models': chosen, 'projection': projection,
              'tree_sha256': digest(tree), 'tree_grouping': grouping,
              'input_audit': audit, 'panels': panels['panels'],
              'native_engine': str(native.bonsai_submodule_root()),
              'method': 'Native Bonsai on lowest-ProteinEBM-energy representative '
                        'per assigned active-view cluster and explicit low-energy '
                        'unassigned examples; 4096-dimensional accepted '
                        'all-pair sketch; nonzero PCA axes; no variance scaling'}
    (output / 'acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'view': view['id'], 'models': len(chosen),
                      'tree_sha256': result['tree_sha256'],
                      'receipt_sha256': digest(output / 'acceptance.json')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--task', type=int, required=True)
    arguments = parser.parse_args()
    run(load_plan(arguments.plan, arguments.plan_sha256), arguments.task)
