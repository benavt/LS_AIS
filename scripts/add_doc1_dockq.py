"""Add accepted 0865 DockQ scores to saved monomer views; never run science."""
import argparse
import csv
import gzip
import io
import json
from pathlib import Path
import tempfile

from build_private_atlas import copy_verified_file, sha


TARGETS = ('CDK2_DOC1', 'CDK2_DOC1t')
REFERENCE = 'CDK2_DOC1__afsample3__0865'
REFERENCE_SHA = '5503da4081c1e0d6483a54da3c22d93a13abe84d03d22de9ec2f5e43c6997c17'
SCORES_SHA = 'fc321f809ab9977948bf49a70bd6abfd3334ce3a681ad8ca531293f28be2b62f'
PLAN_SHA = 'df4aa04eb8b422a38bb041281097693e38782e3698d22a55db3b2a02c7f5b1ef'
SOURCE_EXPORT_SHA = 'a628fff496871d38f713e76403afe1f6e193c59362b276fc94dabbe5d8a4ea50'


def checked_scores(scores, acceptance):
    receipt = json.loads(acceptance.read_text())
    if (sha(scores) != SCORES_SHA or receipt.get('scores_sha256') != SCORES_SHA or
            receipt.get('plan_sha256') != PLAN_SHA or receipt.get('status') != 'validated' or
            receipt.get('scored') != 9999 or receipt.get('dockq_error_ids') != [] or
            receipt.get('reference_native_sha256') != REFERENCE_SHA or
            receipt.get('target_counts') != {'CDK2_DOC1': 4999, 'CDK2_DOC1t': 5000}):
        raise ValueError('DockQ acceptance or score-table identity differs')
    rows = list(csv.DictReader(scores.open(newline='')))
    if len(rows) != 9999 or len({r['model_id'] for r in rows}) != 9999:
        raise ValueError('DockQ comparison roster is incomplete or duplicated')
    for row in rows:
        expected_scope = {'CDK2_DOC1': 'full_115', 'CDK2_DOC1t': 'doc1t_55'}.get(row['target'])
        if (expected_scope is None or row['reference_scope'] != expected_scope or
                row['reference_id'] != REFERENCE or row['reference_native_sha256'] != REFERENCE_SHA or
                row['status'] != 'scored' or row['error'] or not 0 <= float(row['dockq']) <= 1):
            raise ValueError('DockQ target, scope, or numeric result differs')
    return {r['model_id']: r for r in rows}


def replace(path, contents):
    temporary = path.with_name(path.name + '.new')
    temporary.write_bytes(contents)
    temporary.replace(path)  # Do not mutate a hard-linked saved input.


def target_csv(stage, target, rows):
    fields = ('target', 'model_id', 'method', 'weights_version', 'physicality_status',
              'native_sha256', 'reference_id', 'reference_scope', 'dockq', 'status')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for model in sorted(rows):
        row = rows[model]
        writer.writerow({key: row.get(key, '') for key in fields})
    raw = stream.getvalue().encode()
    name = f'downloads/{target}-dockq-vs-0865.csv.gz'
    destination = stage / name
    destination.parent.mkdir(exist_ok=True)
    destination.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
    return name, len(rows)


def augment(base, scores, acceptance, output):
    from structure_clustering.publication import export
    from src.analysis.atlas_presentation import validate_views

    base, scores, acceptance, output = map(lambda p: Path(p).resolve(),
                                           (base, scores, acceptance, output))
    if output.exists() or sha(base / 'export-manifest.json') != SOURCE_EXPORT_SHA:
        raise ValueError('Use the exact published LS_AIS bundle and a fresh output')
    indexed = checked_scores(scores, acceptance)
    base_manifest = json.loads((base / 'export-manifest.json').read_text())
    source_names = {row['path'] for row in base_manifest['files']}
    if base_manifest.get('project') != 'LS_AIS':
        raise ValueError('Not an LS_AIS saved atlas')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ls-ais-dockq-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'source'
        stage.mkdir()
        for row in base_manifest['files']:
            if row['path'] not in {'.nojekyll', 'export-manifest.json'}:
                copy_verified_file(base, stage, row)
        for target in TARGETS:
            primary = json.loads((stage / target / 'primary.json').read_text())
            if len(primary['models']) != 1000 or len(primary['model_sha256']) != 1000:
                raise ValueError('Saved AFsample3 model roster differs: ' + target)
            target_rows = {model: row for model, row in indexed.items()
                           if row['target'] == target}
            if target == 'CDK2_DOC1':
                if REFERENCE in target_rows:
                    raise ValueError('Reference was unexpectedly scored in the full grid')
                target_rows[REFERENCE] = dict(target=target, model_id=REFERENCE,
                    method='afsample3', weights_version='', physicality_status='',
                    native_sha256=REFERENCE_SHA, reference_id=REFERENCE,
                    reference_scope='full_115', dockq='1.0', status='reference_self')
            if len(target_rows) != 5000:
                raise ValueError('Target does not have exactly 5,000 DockQ observations')
            name, _ = target_csv(stage, target, target_rows)
            for view in ('primary', 'density'):
                path = stage / target / f'{view}.json'
                data = json.loads(path.read_text())
                models = data['models']
                if models != primary['models'] or data['model_sha256'] != primary['model_sha256']:
                    raise ValueError('Saved view model identities differ: ' + target)
                if any(s['key'] == 'dockq_vs_0865' for s in data['schemes']):
                    raise ValueError('DockQ metric already exists')
                for model, digest in zip(models, data['model_sha256']):
                    row = target_rows.get(model)
                    if row is None or row['native_sha256'] != digest:
                        raise ValueError('DockQ native-coordinate identity differs: ' + model)
                label = 'full DOC1' if target == 'CDK2_DOC1' else 'DOC1t · reference DOC1 61–115'
                data['schemes'].append(dict(key='dockq_vs_0865',
                    name='DockQ vs 0865 · ' + label, short_name='DockQ vs 0865',
                    type='continuous', values=[float(target_rows[m]['dockq']) for m in models],
                    colorscale='Viridis', range=[0, 1], unavailable=False))
                links = data.setdefault('native_data_links', {})
                if 'dockq' in links:
                    raise ValueError('DockQ download link already exists')
                links['dockq'] = name
                data['provenance']['dockq_vs_0865'] = dict(reference=REFERENCE,
                    reference_native_sha256=REFERENCE_SHA, reference_scope=target_rows[models[0]]['reference_scope'],
                    all_other_scores_sha256=SCORES_SHA, accepted_plan_sha256=PLAN_SHA,
                    scored_target_models=4999 if target == 'CDK2_DOC1' else 5000,
                    total_target_models=5000, displayed_afsample3_models=1000,
                    software='DockQ 2.1.4', chain_mapping='AB:AB', sequence_alignment=False)
                replace(path, (json.dumps(data, separators=(',', ':')) + '\n').encode())
        script = stage / 'ls_atlas.js'
        original = script.read_text()
        old = "diagnostics:'Sampling diagnostics + traces'"
        if original.count(old) != 1:
            raise ValueError('Saved download menu is unsupported')
        replace(script, original.replace(old, old+", dockq:'DockQ vs 0865 · all 5,000 target models'").encode())
        if not {f'{t}/primary.json' for t in TARGETS} <= source_names:
            raise ValueError('Published atlas is missing the monomer views')
        files = [dict(path=p.relative_to(stage).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
                 for p in sorted(stage.rglob('*')) if p.is_file()]
        validate_views(stage, {r['path'] for r in files})
        manifest = Path(temporary) / 'private-manifest.json'
        manifest.write_text(json.dumps(dict(schema_version=1, project='LS_AIS',
            renderer='saved', source_export_sha256=SOURCE_EXPORT_SHA,
            dockq_scores_sha256=SCORES_SHA, files=files), indent=2) + '\n')
        record = export(manifest, stage, output)
        (output.parent / 'private-manifest.json').write_bytes(manifest.read_bytes())
        (output.parent / 'delivery-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(dict(status='private_review_ready', targets=TARGETS,
            scored_other_models=9999, source_export_sha256=SOURCE_EXPORT_SHA,
            dockq_scores_sha256=SCORES_SHA, export_sha256=sha(output / 'export-manifest.json'),
            files=len(record['files']))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--scores', type=Path, required=True)
    parser.add_argument('--acceptance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    augment(args.base, args.scores, args.acceptance, args.output)
