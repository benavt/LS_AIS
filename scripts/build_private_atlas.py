"""Compose verified saved targets into one private atlas; never run science."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = {'residue-ranges.json', 'clustering-residues.json', 'target-context.json',
            'projection-metadata.json', 'supplementary-metadata.json', 'metric-overlays.json',
            'selection-highlights.json', 'tm-states.json', 'view-policy.json'}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compose(registry, sources, output):
    from structure_clustering.publication import export, safe_file
    from src.analysis.atlas_presentation import validate_views
    targets = registry['targets']
    ids = [row['id'] for row in targets]
    if len(ids) != len(set(ids)) or set(sources) != set(ids):
        raise ValueError('Supply exactly one verified saved delivery for every registered target')
    if output.exists():
        raise ValueError('Use a fresh output directory')
    if shutil.disk_usage(ROOT).free < 52 * 2**30:
        raise ValueError('Need2GiB working allowance and50GiB reserve')
    output.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / 'local').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ls-ais-compose-', dir=ROOT / 'local') as temporary:
        stage = Path(temporary) / 'source'; stage.mkdir()
        catalogs, atlas_targets = {}, []
        for config in targets:
            target = config['id']; source = sources[target].resolve()
            manifest = source.parent / 'delivery-manifest.json'
            entries = read(manifest)['files']
            atlas = read(source / 'atlas.json')
            if [t['id'] for t in atlas['targets']] != [target]:
                raise ValueError('Saved delivery must contain exactly its registered target')
            entry = dict(atlas['targets'][0], label=config['name'])
            atlas_targets.append(entry)
            for row in entries:
                name = row['path']; path = safe_file(source, name)
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
                destination = stage / name
                if destination.exists():
                    if sha(destination) != row['sha256']:
                        raise ValueError('Target artifact or shared renderer collision: ' + name)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.link(path, destination)
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
        print(json.dumps(dict(project='LS_AIS', private_only=True, targets=ids, files=len(record['files']), scientific_execution=False)))
        return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target-source', action='append', required=True, metavar='ID=DELIVERY')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sources = {}
    for value in args.target_source:
        target, path = value.split('=', 1)
        if target in sources:
            parser.error('Duplicate target source')
        sources[target] = Path(path)
    compose(read(ROOT / 'config/targets.json'), sources, args.output.resolve())
