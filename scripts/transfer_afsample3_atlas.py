"""Transfer the verified, saved AFsample3 CDK2–DOC1 atlas into LS_AIS.

This composes existing files only. It never runs clustering or scoring.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from build_private_atlas import copy_verified_file, read, sha


ROOT = Path(__file__).resolve().parents[1]
MONOMERS = ('CDK2_DOC1', 'CDK2_DOC1t')
BASE_TARGETS = ('HSPH1_12757_homodimer', 'DOC1Rdimer_CDK2', 'DOC1dimer_CDK2')
PUBLISHED_AFS3_MANIFEST_SHA256 = '27dee75fac31c31de1a2560f9d9b54304b691d05afa1cf0a06bd65b9cc206504'
REDIRECTS = {'CDK2_DOC1': 'targets/cdk2-doc1-monomer/index.html',
             'CDK2_DOC1t': 'targets/cdk2-doc1t-monomer/index.html'}


def replace_text(path, value):
    """Avoid writing through a hard link to a saved source file."""
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(value)
    temporary.replace(path)


def verified_rows(source, manifest, selected=lambda name: True):
    rows = read(manifest)['files']
    names = [row['path'] for row in rows]
    if len(names) != len(set(names)):
        raise ValueError('Saved manifest has duplicate paths')
    selected_rows = []
    for row in rows:
        name = row['path']
        if not selected(name):
            continue
        path = source / name
        if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise ValueError('Saved file differs from its manifest: ' + name)
        selected_rows.append(row)
    return selected_rows


def compress_afsample3_coordinates(stage):
    """Change transport only; keep each model's original decoded SHA-256."""
    for target in MONOMERS:
        model_dir = stage / target / 'models'
        models = sorted(model_dir.glob('*.cif'))
        if len(models) != 1000 or len(list(model_dir.iterdir())) != 1000:
            raise ValueError('AFsample3 model-file count differs: ' + target)
        original_hashes = {}
        for model in models:
            raw = model.read_bytes()
            original_hashes[f'{target}/models/{model.name}'] = hashlib.sha256(raw).hexdigest()
            compressed = model.with_suffix('.cif.gz')
            compressed.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
            model.unlink()  # Remove only the staged hard link, not the saved source.
        for view in ('primary', 'density'):
            path = stage / target / (view + '.json')
            data = read(path)
            originals = data['model_files']
            if (len(originals) != 1000 or len(data['model_sha256']) != 1000 or
                    set(originals) != set(original_hashes)):
                raise ValueError('AFsample3 model inventory differs: ' + target + '/' + view)
            for original, digest in zip(originals, data['model_sha256']):
                if original_hashes[original] != digest:
                    raise ValueError('Original coordinate hash differs: ' + original)
            data['model_files'] = [name + '.gz' for name in originals]
            for representative in data['representatives']:
                original = representative['file']
                if representative['sha256'] != original_hashes[original]:
                    raise ValueError('Representative hash differs: ' + original)
                representative['file'] = original + '.gz'
            optional = {'box_summary_3d.png', 'pair_distribution_detail.png'}
            data['heatmaps'] = [row for row in data['heatmaps']
                                if Path(row['file']).name not in optional]
            if {Path(row['file']).name for row in data['heatmaps']} != {
                    'median_matrix.png', 'variance_matrix.png'}:
                raise ValueError('Required distance/variance maps differ: ' + target)
            data['provenance']['transport_compression'] = 'gzip; original CIF SHA-256 checked after decompression'
            data['provenance']['optional_plots_excluded_from_view'] = sorted(optional)
            replace_text(path, json.dumps(data, separators=(',', ':')) + '\n')


def compress_dimer_downloads(stage):
    """Retain exact CSV bytes as reproducible gzip downloads within Pages limits."""
    receipts = []
    for target in ('DOC1Rdimer_CDK2', 'DOC1dimer_CDK2'):
        for suffix in ('proteinebm-full-complex', 'geometry-memberships',
                       'core-geometry-memberships'):
            name = f'{target}-{suffix}.csv'
            original = stage / 'downloads' / name
            raw = original.read_bytes()
            compressed = original.with_suffix('.csv.gz')
            compressed.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
            original.unlink()
            receipts.append(dict(file=f'downloads/{name}.gz',
                                 original_sha256=hashlib.sha256(raw).hexdigest(),
                                 original_bytes=len(raw),
                                 compressed_sha256=sha(compressed)))
            replacements = 0
            for view in (stage / target).glob('*.json'):
                saved = view.read_text()
                if name in saved:
                    replacements += saved.count(name)
                    replace_text(view, saved.replace(name, name + '.gz'))
            if not replacements:
                raise ValueError('Dimer CSV has no saved atlas link: ' + name)
    replace_text(stage / 'downloads' / 'gzip-provenance.json',
                 json.dumps({'transport': 'gzip', 'files': receipts}, indent=2) + '\n')


def transfer(base, afs3, afs3_manifest, output, expected_manifest_sha=PUBLISHED_AFS3_MANIFEST_SHA256):
    from structure_clustering.publication import export
    from src.analysis.atlas_presentation import validate_views

    base, afs3, afs3_manifest, output = (Path(p).resolve() for p in
                                        (base, afs3, afs3_manifest, output))
    if output.exists():
        raise ValueError('Use a fresh output directory')
    if sha(afs3_manifest) != expected_manifest_sha:
        raise ValueError('AFsample3 published manifest hash differs')
    base_manifest = base.parent / 'delivery-manifest.json'
    base_rows = verified_rows(base, base_manifest)
    old_rows = verified_rows(afs3, afs3_manifest,
        lambda name: name in {'atlas.json', 'clustering-residues.json', 'target-context.json'}
        or name.startswith(tuple(target + '/' for target in MONOMERS)))
    base_atlas = read(base / 'atlas.json')
    old_atlas = read(afs3 / 'atlas.json')
    if [row['id'] for row in base_atlas['targets']] != list(BASE_TARGETS):
        raise ValueError('LS_AIS saved target identity/order differs')
    if [row['id'] for row in old_atlas['targets']] != list(MONOMERS):
        raise ValueError('AFsample3 saved target identity/order differs')
    registry = read(ROOT / 'config/targets.json')
    if [row['id'] for row in registry['targets']] != [*BASE_TARGETS, *MONOMERS]:
        raise ValueError('LS_AIS target registry identity/order differs')
    for row in registry['targets'][-2:]:
        if row.get('stage') != 'transferred_afsample3':
            raise ValueError('Monomer target is not marked as transferred')
    old_names = {row['path'] for row in old_rows}
    for target in MONOMERS:
        required = {f'{target}/primary.json', f'{target}/density.json',
                    f'{target}/bonsai.json', f'{target}/memberships-and-scores.csv',
                    f'{target}/hdbscan-memberships-and-scores.csv'}
        if not required <= old_names or len([n for n in old_names if n.startswith(target + '/')]) < 1000:
            raise ValueError('AFsample3 scientific assets are incomplete: ' + target)
        config = next(row for row in registry['targets'] if row['id'] == target)
        target_config = read(ROOT / config['config'])
        if (target_config['cohort_views'][0]['models'] != 1000 or
                target_config['cohort_views'][1]['models'] != 4000 or
                target_config['existing_afsample3_snapshot']['primary_sha256'] !=
                sha(afs3 / target / 'primary.json')):
            raise ValueError('Monomer cohort identity differs: ' + target)
    if shutil.disk_usage(ROOT).free < 52 * 2**30:
        raise ValueError('Need 50 GiB reserve')
    output.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ls-ais-afs3-transfer-', dir=ROOT / 'local') as temporary:
        stage = Path(temporary) / 'source'; stage.mkdir()
        for row in base_rows:
            name = row['path']
            if name in {'export-manifest.json', 'placeholder_nav.js'} or name in REDIRECTS.values():
                continue
            copy_verified_file(base, stage, row)
        (stage / '.nojekyll').unlink(missing_ok=True)
        for row in old_rows:
            if row['path'].startswith(tuple(target + '/' for target in MONOMERS)):
                copy_verified_file(afs3, stage, row)
        compress_afsample3_coordinates(stage)
        compress_dimer_downloads(stage)

        base_atlas['targets'].extend(dict(row, label=registry['targets'][i + len(BASE_TARGETS)]['name'])
                                     for i, row in enumerate(old_atlas['targets']))
        replace_text(stage / 'atlas.json', json.dumps(base_atlas, indent=2) + '\n')
        for name in ('clustering-residues.json', 'target-context.json'):
            merged, source = read(stage / name), read(afs3 / name)
            if set(source.get('targets', {})) != set(MONOMERS):
                raise ValueError('AFsample3 catalog target identity differs: ' + name)
            if set(merged.get('targets', {})) & set(MONOMERS):
                raise ValueError('Target catalog collision: ' + name)
            if name == 'target-context.json':
                source['targets']['CDK2_DOC1t']['title'] = 'CDK2–DOC1t AFsample3 ensemble'
            merged['targets'].update(source['targets'])
            replace_text(stage / name, json.dumps(merged, indent=2) + '\n')

        script = ROOT / 'site/cohort_menu.js'
        shutil.copy2(script, stage / 'cohort_menu.js')
        markup = (stage / 'index.html').read_text()
        if 'placeholder_nav.js' in markup:
            markup = markup.replace('<script defer src="placeholder_nav.js"></script>', '')
        if '</head>' not in markup or 'cohort_menu.js' in markup:
            raise ValueError('Saved LS_AIS shell cannot receive cohort menu')
        replace_text(stage / 'index.html', markup.replace('</head>',
                     '<script defer src="cohort_menu.js"></script></head>', 1))
        for target, relative in REDIRECTS.items():
            destination = stage / relative;destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<meta http-equiv="refresh" content="0;url=../../#{target}">'
                f'<title>{target} · LS_AIS</title></head><body>'
                f'<p>Open the <a href="../../#{target}">transferred LS_AIS atlas</a>.</p>'
                '</body></html>')
        files = [dict(path=p.relative_to(stage).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
                 for p in sorted(stage.rglob('*')) if p.is_file()]
        if sum(row['bytes'] for row in files) > 1 * 2**30:
            raise ValueError('Atlas exceeds the GitHub Pages 1 GiB output cap')
        validate_views(stage, {row['path'] for row in files})
        publication = dict(schema_version=1, project='LS_AIS', renderer='saved',
                           source_delivery_sha256=sha(base_manifest),
                           afsample3_published_manifest_sha256=sha(afs3_manifest), files=files)
        manifest = Path(temporary) / 'private-manifest.json'
        manifest.write_text(json.dumps(publication, indent=2) + '\n')
        record = export(manifest, stage, output)
        (output.parent / 'private-manifest.json').write_bytes(manifest.read_bytes())
        (output.parent / 'delivery-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(dict(project='LS_AIS', targets=[*BASE_TARGETS, *MONOMERS],
                              files=len(record['files']), scientific_execution=False, private_only=True)))
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-delivery', type=Path, required=True)
    parser.add_argument('--afsample3-source', type=Path, required=True)
    parser.add_argument('--afsample3-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    transfer(args.base_delivery, args.afsample3_source, args.afsample3_manifest, args.output)
