"""Losslessly package the reviewed DOC1/CDK2 saved preview for GitHub Pages.

This changes only presentation labels and transport compression. It does not
calculate science or alter accepted coordinate, membership, or energy values.
"""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from structure_clustering.publication import inspect_artifact, relative_name


TARGETS = ('DOC1Rdimer_CDK2', 'DOC1dimer_CDK2')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one presentation marker: {old[:60]}')
    return text.replace(old, new)


def package(source, output, expected_manifest_sha256):
    if output.exists():
        raise FileExistsError(output)
    manifest_raw = (source / 'export-manifest.json').read_bytes()
    if sha(manifest_raw) != expected_manifest_sha256:
        raise ValueError('Source preview differs from the reviewed manifest')
    source_files = json.loads(manifest_raw)['files']
    expected = {row['path'] for row in source_files}
    actual = {path.relative_to(source).as_posix() for path in source.rglob('*') if path.is_file()}
    if expected != actual - {'export-manifest.json'}:
        raise ValueError('Preview has missing or unrecorded files')
    output.mkdir(parents=True)
    files = []
    for entry in source_files:
        name = relative_name(entry['path'])
        raw = (source / name).read_bytes()
        if len(raw) != entry['bytes'] or sha(raw) != entry['sha256']:
            raise ValueError(f'Source preview hash differs: {name}')
        if name == 'index.html':
            text = raw.decode('utf-8')
            text = replace_once(text, '<html lang="en">', '<html lang="en" data-public-bundle="true">')
            text = replace_once(text, 'DOC1/CDK2 structure atlas preview', 'DOC1/CDK2 structure atlas')
            text = replace_once(text, 'Private LS AIS atlas preview · accepted DOC1/CDK2 saved analyses.',
                                'LS AIS structure atlas · preliminary DOC1/CDK2 results.')
            text = replace_once(text, 'href="https://benavt.github.io/LS_AIS/"', 'href="../"')
            text = replace_once(text, 'All model memberships and saved projection coordinates (CSV)',
                                'All model memberships and saved projection coordinates (CSV.gz)')
            text = replace_once(text, 'Download accepted 16-level ProteinEBM scores (CSV)',
                                'Download accepted 16-level ProteinEBM scores (CSV.gz)')
            raw = text.encode('utf-8')
        if name.endswith('.csv') and name.startswith('downloads/'):
            name += '.gz'
            raw = gzip.compress(raw, compresslevel=9, mtime=0)
        elif name.startswith('data/') and name.endswith('.json') and name != 'data/summary.json':
            if not any(name == f'data/{slug}{suffix}.json' for slug in TARGETS for suffix in ('', '-core')):
                raise ValueError(f'Unrecognized target JSON: {name}')
            name += '.gz'
            raw = gzip.compress(raw, compresslevel=9, mtime=0)
        destination = output / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        inspect_artifact(raw, name)
        files.append({'path': name, 'bytes': len(raw), 'sha256': sha(raw)})
    release = {'kind': 'public-preliminary-doc1-cdk2-atlas', 'scientific_execution': False,
               'source_preview_manifest_sha256': expected_manifest_sha256, 'files': sorted(files, key=lambda row: row['path'])}
    (output / 'export-manifest.json').write_text(json.dumps(release, indent=2) + '\n')
    print(json.dumps({'status': 'privacy_checked', 'files': len(files),
                      'bytes': sum(row['bytes'] for row in files),
                      'manifest_sha256': sha((output / 'export-manifest.json').read_bytes())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-manifest-sha256', required=True)
    args = parser.parse_args()
    package(args.source, args.output, args.source_manifest_sha256)
