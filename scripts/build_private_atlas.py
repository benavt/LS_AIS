"""Compose verified saved targets into one private atlas; never run science."""
import argparse
import errno
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = {'residue-ranges.json', 'clustering-residues.json', 'target-context.json',
            'projection-metadata.json', 'supplementary-metadata.json', 'metric-overlays.json',
            'selection-highlights.json', 'tm-states.json', 'view-policy.json'}


def placeholder_html(entry, target):
    if (entry['id'] != target['id'] or entry['stage'] != 'placeholder' or
            entry['page'] not in {'targets/cdk2-doc1-monomer/', 'targets/cdk2-doc1t-monomer/'} or
            entry['source_url'] != 'https://benavt.github.io/cdk2-doc1-afs3/#' + entry['id']):
        raise ValueError('Unverified placeholder identity or destination')
    views = target['cohort_views']
    if ([v['id'] for v in views] != ['afsample3_saved', 'afsample2_bioemu2_new'] or
            [v['models'] for v in views] != [1000, 4000] or
            views[0]['status'] != 'verified_saved_external' or
            views[1]['status'] != 'scoring_submitted_clustering_pending'):
        raise ValueError('Placeholder cohort statuses differ from saved verification')
    saved = target['existing_afsample3_snapshot']
    if (saved['source_url'] != entry['source_url'] or
            saved['commit'] != 'd672ba45d8a7723ac07041f41410b1150a2b33e6'):
        raise ValueError('AFsample3 publication identity changed')
    title = html.escape(entry['name'])
    source = html.escape(entry['source_url'], quote=True)
    scope = html.escape(target['primary_residue_scope'])
    physicality = ('The 1,000 BioEMU2 frames include 999 flagged native physicality failures; '
                   'those labels will remain visible in the new cohort.' if entry['id'] == 'CDK2_DOC1'
                   else 'All 1,000 BioEMU2 frames passed the recorded native physicality check.')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · LS_AIS</title><style>
body{{font:16px/1.55 system-ui,sans-serif;max-width:760px;margin:0 auto;padding:2rem 1.2rem;color:#17243a;background:#f7f9fc}}
a{{color:#1554a0}}nav{{margin-bottom:2.5rem}}main{{background:white;padding:1.6rem;border:1px solid #dce4ee;border-radius:12px}}
.tag{{display:inline-block;background:#e8f0fc;color:#244d88;border-radius:999px;padding:.15rem .65rem;font-size:.85rem}}
section{{border-top:1px solid #e3e8ef;margin-top:1.5rem;padding-top:.5rem}}small{{color:#52627a}}
</style></head><body><nav><a href="../../">LS_AIS atlas</a></nav><main>
<span class="tag">Placeholder · saved AFsample3 cohort</span><h1>{title}</h1>
<p>CDK2 and one DOC1 chain · complete residue scope {scope}.</p>
<section><h2>AFsample3 · 1,000 models</h2>
<p>The existing, hash-verified AFsample3 atlas has ProteinEBM scores, clustering views, structures and Bonsai.</p>
<p><a href="{source}">Open the existing AFsample3 target atlas</a></p>
<small>Saved publication commit {html.escape(saved['commit'])}.</small></section>
<section><h2>AFsample2 + BioEMU2 · 4,000 models</h2>
<p>This is a separate model cohort: 3,000 AFsample2 models (1,000 each from multimer weights v1, v2 and v3) plus 1,000 BioEMU2 frames. ProteinEBM scoring is submitted; the cohort's own geometry clustering and atlas views are pending validation.</p>
<p>{html.escape(physicality)}</p></section>
<p><small>This page will be replaced by the reviewed LS_AIS target explorer when the new cohort's analyses are accepted.</small></p>
</main></body></html>'''


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_verified_file(source, stage, row):
    from structure_clustering.publication import safe_file
    name = row['path']
    path = source / name if name == '.nojekyll' else safe_file(source, name)
    if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
        raise ValueError('Saved target hash/size differs: ' + name)
    destination = stage / name
    if destination.exists():
        if sha(destination) != row['sha256']:
            raise ValueError('Target artifact or shared renderer collision: ' + name)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(path, destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.copy2(path, destination)


def add_placeholders(stage, targets):
    placeholders = [row for row in targets if row.get('stage') == 'placeholder']
    if not placeholders:
        return
    linked = [dict(id=config['id'], label=config['name'], href=config['page'])
              for config in placeholders]
    for config in placeholders:
        target = read(ROOT / config['config'])
        path = stage / config['page'] / 'index.html'
        if path.exists():
            raise ValueError('Placeholder page collides with saved artifact')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(placeholder_html(config, target))
    navigation = '''(() => {\n  const links = ''' + json.dumps(linked, ensure_ascii=False) + ''';\n  function sync() {\n    const menu = document.getElementById('targets');\n    if (!menu) return;\n    for (const item of links) {\n      let anchor = [...menu.querySelectorAll('a[data-linked-target]')].find(a => a.dataset.linkedTarget === item.id);\n      if (!anchor) { anchor = document.createElement('a'); anchor.dataset.linkedTarget = item.id; }\n      anchor.href = item.href; anchor.textContent = item.label; menu.append(anchor);\n    }\n  }\n  window.addEventListener('atlas:cohort', sync);\n  document.addEventListener('DOMContentLoaded', sync);\n})();\n'''
    (stage / 'placeholder_nav.js').write_text(navigation)
    index = stage / 'index.html'
    markup = index.read_text()
    if '</head>' not in markup or 'placeholder_nav.js' in markup:
        raise ValueError('Saved atlas shell cannot receive placeholder navigation')
    replacement = index.with_name('index.html.new')
    replacement.write_text(markup.replace('</head>', '<script defer src="placeholder_nav.js"></script></head>', 1))
    replacement.replace(index)  # Never modify a hard-linked saved source.


def compose(registry, sources, output):
    from structure_clustering.publication import export, safe_file
    from src.analysis.atlas_presentation import validate_views
    targets = registry['targets']
    ids = [row['id'] for row in targets]
    saved_targets = [row for row in targets if row.get('stage') != 'placeholder']
    placeholders = [row for row in targets if row.get('stage') == 'placeholder']
    if len(ids) != len(set(ids)) or set(sources) != {row['id'] for row in saved_targets}:
        raise ValueError('Supply exactly one verified saved delivery for every registered target that is not a placeholder')
    if output.exists():
        raise ValueError('Use a fresh output directory')
    if shutil.disk_usage(ROOT).free < 52 * 2**30:
        raise ValueError('Need2GiB working allowance and50GiB reserve')
    output.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ls-ais-compose-', dir=ROOT / 'local') as temporary:
        stage = Path(temporary) / 'source'; stage.mkdir()
        catalogs, atlas_targets = {}, []
        for config in saved_targets:
            target = config['id']; source = sources[target].resolve()
            manifest = source.parent / 'delivery-manifest.json'
            entries = read(manifest)['files']
            atlas = read(source / 'atlas.json')
            if [t['id'] for t in atlas['targets']] != [target]:
                raise ValueError('Saved delivery must contain exactly its registered target')
            entry = dict(atlas['targets'][0], label=config['name'])
            atlas_targets.append(entry)
            for row in entries:
                name = row['path']
                if name == '.nojekyll':
                    path = source / name
                    if not path.is_file() or path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
                        raise ValueError('Saved target hash/size differs: ' + name)
                    continue
                path = safe_file(source, name)
                if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
                    raise ValueError('Saved target hash/size differs: ' + name)
                if name in {'atlas.json', '.nojekyll', 'export-manifest.json'}:
                    continue
                if name in CATALOGS:
                    value = read(path)
                    if not value:
                        continue
                    if set(value.get('targets', {})) - {target}:
                        raise ValueError('Catalog crosses its target namespace')
                    if name not in catalogs:
                        catalogs[name] = {key: val for key, val in value.items() if key != 'targets'}
                        catalogs[name]['targets'] = {}
                    if {k: v for k, v in value.items() if k != 'targets'} != {k: v for k, v in catalogs[name].items() if k != 'targets'}:
                        raise ValueError('Incompatible target catalog headers: ' + name)
                    catalogs[name]['targets'].update(value.get('targets', {}))
                    continue
                copy_verified_file(source, stage, row)
        add_placeholders(stage, targets)
        (stage / 'atlas.json').write_text(json.dumps(dict(targets=atlas_targets), indent=2) + '\n')
        for name in CATALOGS:
            (stage / name).write_text(json.dumps(catalogs.get(name, {}), indent=2) + '\n')
        files = [dict(path=p.relative_to(stage).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
                 for p in sorted(stage.rglob('*')) if p.is_file()]
        if sum(row['bytes'] for row in files) > 2 * 2**30:
            raise ValueError('Private atlas exceeds the approved2GiB output cap')
        validate_views(stage, {r['path'] for r in files})
        publication = dict(schema_version=1, project='LS_AIS', renderer='saved', files=files)
        manifest = Path(temporary) / 'private-manifest.json'
        manifest.write_text(json.dumps(publication, indent=2) + '\n')
        record = export(manifest, stage, output)
        (output.parent / 'private-manifest.json').write_bytes(manifest.read_bytes())
        (output.parent / 'delivery-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(dict(project='LS_AIS', private_only=True, targets=ids, placeholders=[r['id'] for r in placeholders], files=len(record['files']), scientific_execution=False)))
        return record


def augment_saved(registry, source, output):
    """Add registered placeholders to an unchanged, hash-verified multi-target export."""
    from structure_clustering.publication import export
    from src.analysis.atlas_presentation import validate_views
    targets = registry['targets']
    saved_ids = [row['id'] for row in targets if row.get('stage') != 'placeholder']
    placeholder_ids = [row['id'] for row in targets if row.get('stage') == 'placeholder']
    if len({row['id'] for row in targets}) != len(targets) or not placeholder_ids:
        raise ValueError('Expected unique registered targets and at least one placeholder')
    if output.exists():
        raise ValueError('Use a fresh output directory')
    if shutil.disk_usage(ROOT).free < 52 * 2**30:
        raise ValueError('Need 2 GiB working allowance and 50 GiB reserve')
    source = source.resolve()
    manifest_path = source.parent / 'delivery-manifest.json'
    entries = read(manifest_path)['files']
    names = [row['path'] for row in entries]
    if len(names) != len(set(names)) or 'atlas.json' not in names or 'index.html' not in names:
        raise ValueError('Saved delivery file inventory is incomplete or duplicated')
    atlas = read(source / 'atlas.json')
    if [row['id'] for row in atlas['targets']] != saved_ids:
        raise ValueError('Saved atlas target order does not match the registered targets')
    output.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ls-ais-augment-', dir=ROOT / 'local') as temporary:
        stage = Path(temporary) / 'source'; stage.mkdir()
        for row in entries:
            copy_verified_file(source, stage, row)
            if row['path'] in {'.nojekyll', 'export-manifest.json'}:
                (stage / row['path']).unlink()  # The saved-file exporter generates these afresh.
        add_placeholders(stage, targets)
        files = [dict(path=p.relative_to(stage).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
                 for p in sorted(stage.rglob('*')) if p.is_file()]
        if sum(row['bytes'] for row in files) > 2 * 2**30:
            raise ValueError('Private atlas exceeds the approved 2 GiB output cap')
        validate_views(stage, {row['path'] for row in files})
        publication = dict(schema_version=1, project='LS_AIS', renderer='saved',
                           source_delivery_sha256=sha(manifest_path), files=files)
        manifest = Path(temporary) / 'private-manifest.json'
        manifest.write_text(json.dumps(publication, indent=2) + '\n')
        record = export(manifest, stage, output)
        (output.parent / 'private-manifest.json').write_bytes(manifest.read_bytes())
        (output.parent / 'delivery-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(dict(project='LS_AIS', private_only=True, saved_targets=saved_ids,
                              placeholders=placeholder_ids, files=len(record['files']),
                              scientific_execution=False)))
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-source', action='append', metavar='ID=DELIVERY')
    parser.add_argument('--base-delivery', type=Path, help='Verified saved multi-target delivery to augment')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if bool(args.base_delivery) == bool(args.target_source):
        parser.error('Supply either --base-delivery or --target-source')
    if args.base_delivery:
        augment_saved(read(ROOT / 'config/targets.json'), args.base_delivery, args.output.resolve())
        raise SystemExit(0)
    sources = {}
    for value in args.target_source:
        target, path = value.split('=', 1)
        if target in sources:
            parser.error('Duplicate target source')
        sources[target] = Path(path)
    compose(read(ROOT / 'config/targets.json'), sources, args.output.resolve())
