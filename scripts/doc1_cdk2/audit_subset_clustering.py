"""Read-only integrity audit of accepted DOC1/CDK2 A/B-core cluster outputs."""

import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit_target(plan, target, index, parent_job_id):
    root = Path(plan['output_root']).parent
    output = Path(plan['output_root']) / target['id']
    receipt_path = output / 'acceptance.json'
    receipt = json.loads(receipt_path.read_text())
    require(receipt['status'] == 'validated' and
            receipt['target'] == target['id'] and
            receipt['plan_sha256'] == digest(root / 'plan.json') and
            receipt['models'] == target['models'] and
            receipt['first_retained_ab'] == target['first_retained'] and
            receipt['subset_pairs_per_model'] == target['subset_pairs'] and
            receipt['roster_sha256'] == target['roster_sha256'] and
            receipt['geometry_matrix_sha256'] == target['geometry_matrix_sha256'] and
            receipt['subset_pilot_acceptance_sha256'] ==
            target['subset_pilot_acceptance_sha256'],
            'Full-cohort receipt identity or fit scope differs')
    files = {
        'model-index.jsonl': receipt['model_index_sha256'],
        'subset-pair-sketch.f32': receipt['sketch_sha256'],
        'umap-knn-labels.npy': receipt['umap_knn_labels_sha256'],
        'umap-knn-selection.json': receipt['umap_knn_selection_sha256'],
    }
    for fit in receipt['umap_fits']:
        files[f"umap-{fit['dimensions']}d-seed-{fit['seed']}.npy"] = fit['embedding_sha256']
    for fit in receipt['hdbscan_fits']:
        files[f"hdbscan-{fit['method']}-seed-{fit['seed']}.npz"] = fit['labels_sha256']
    require(len(receipt['umap_fits']) == 4 and len(receipt['hdbscan_fits']) == 6,
            'Incomplete UMAP or HDBSCAN fit count')
    for name, sha256 in files.items():
        require(digest(output / name) == sha256, 'Output hash differs: ' + name)
    pilot = json.loads(Path(target['subset_pilot_acceptance_path']).read_text())
    primary = next(row for row in pilot['masks']
                   if row['first_retained'] == target['first_retained'])
    require(receipt['pair_columns_sha256'] == primary['pair_columns_sha256'] and
            digest(output / 'buckets.npy') == primary['buckets_sha256'] and
            digest(output / 'signs.npy') == primary['signs_sha256'],
            'Pilot pair mapping differs from full fit')
    events = list((root / 'completion-events').glob(f'task-{index}-job-*.json'))
    require(len(events) == 1, 'Missing or ambiguous completion event')
    event = json.loads(events[0].read_text())
    require(event['protocol'] == 'fleet-slurm-completion-v1' and
            event['parent_job_id'] == parent_job_id and
            event['task_id'] == str(index) and event['exit_code'] == 0,
            'Completion event did not pass')
    logs = list((root / 'resources').glob(f'resource-{parent_job_id}_{index}-*.log'))
    require(len(logs) == 1, 'Missing or ambiguous resource monitor log')
    records = [json.loads(line.removeprefix('[resource] '))
               for line in logs[0].read_text().splitlines()
               if line.startswith('[resource] ')]
    summaries = [row for row in records if row.get('event') == 'summary']
    exits = [row for row in records if row.get('event') == 'command_exit']
    require(len(summaries) == len(exits) == 1 and
            summaries[0]['status'] == 'finished' and
            summaries[0]['exit_code'] == exits[0]['exit_code'] == 0,
            'Whole-job resource monitor did not finish cleanly')
    primary_density = [row for row in receipt['hdbscan_fits']
                       if row['seed'] == 42]
    return {'target': target['id'], 'receipt_sha256': digest(receipt_path),
            'models': target['models'], 'first_retained_ab': target['first_retained'],
            'subset_pairs': target['subset_pairs'], 'verified_output_files': len(files) + 2,
            'umap_knn_groups': receipt['umap_knn_clusters'],
            'hdbscan_seed_42': {row['method']: {'groups': row['clusters'],
                                               'unassigned': row['unassigned_models']}
                                  for row in primary_density},
            'elapsed_seconds': summaries[0]['elapsed_seconds'],
            'peak_rss_mib': summaries[0]['peak_sampled_cpu_rss_mib_approx']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--parent-job-id', required=True)
    args = parser.parse_args()
    require(digest(args.plan) == args.plan_sha256, 'Frozen plan hash differs')
    plan = json.loads(args.plan.read_text())
    require(plan['operation'] == 'doc1_cdk2_ab_core_full_clustering' and
            len(plan['targets']) == 2, 'Wrong subset plan')
    report = [audit_target(plan, target, index, args.parent_job_id)
              for index, target in enumerate(plan['targets'])]
    print(json.dumps({'status': 'verified', 'plan_sha256': args.plan_sha256,
                      'targets': report}, indent=2))


if __name__ == '__main__':
    main()
