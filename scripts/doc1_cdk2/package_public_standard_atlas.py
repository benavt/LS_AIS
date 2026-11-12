"""Package a reviewed LS AIS preview as a size-bounded public Pages site.

The only data transformation is lossless gzip transport for saved coordinates.
The browser decompresses those bytes and verifies the original SHA-256.
This script never runs scientific calculations or deploys a site.
"""

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import re

from structure_clustering.publication import inspect_artifact, relative_name


MODEL_PATH = re.compile(
    r'"((?:HSPH1_12757_homodimer|DOC1Rdimer_CDK2|DOC1dimer_CDK2)'
    r'/models/[^"/]+\.(?:pdb|cif))"'
)
MAX_PUBLIC_BYTES = 1_000_000_000
_SOURCE = None
_OUTPUT = None
_MODEL_PATHS = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one presentation marker: {old[:80]}')
    return text.replace(old, new)


def public_app(raw):
    text = raw.decode('utf-8')
    text = replace_once(
        text,
        "const extension=file.split('.').at(-1).toLowerCase();if(!['cif','mmcif','pdb'].includes(extension))",
        "const extension=file.endsWith('.pdb.gz')?'pdb':file.endsWith('.cif.gz')?'cif':file.split('.').at(-1).toLowerCase();if(!['cif','mmcif','pdb'].includes(extension))",
    )
    text = replace_once(
        text,
        "const extension=cluster.file?.split('.').at(-1)?.toLowerCase(),format=extension==='mmcif'?'CIF':extension?.toUpperCase();",
        "const extension=cluster.file?.endsWith('.pdb.gz')?'pdb.gz':cluster.file?.endsWith('.cif.gz')?'cif.gz':cluster.file?.split('.').at(-1)?.toLowerCase(),format=extension==='pdb.gz'?'PDB.gz':extension==='cif.gz'?'CIF.gz':extension==='mmcif'?'CIF':extension?.toUpperCase();",
    )
    old = """ let text;
 if(descriptor.sha256&&globalThis.crypto?.subtle){
  const bytes=await response.arrayBuffer(),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
  if(digest!==descriptor.sha256)throw Error('Original coordinate hash does not match the selected model.');text=new TextDecoder().decode(bytes);
 }else text=await response.text();
 descriptor.coordinate_text=text;return text;"""
    new = """ let bytes=new Uint8Array(await response.arrayBuffer());
 if(descriptor.file.endsWith('.pdb.gz')||descriptor.file.endsWith('.cif.gz')){
  if(typeof DecompressionStream==='undefined')throw Error('This browser cannot decompress saved coordinate files.');
  bytes=new Uint8Array(await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
 }
 if(descriptor.sha256&&globalThis.crypto?.subtle){
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
  if(digest!==descriptor.sha256)throw Error('Original coordinate hash does not match the selected model.');
 }
 const text=new TextDecoder().decode(bytes);descriptor.coordinate_text=text;return text;"""
    text = replace_once(text, old, new)
    text = replace_once(text,
                        'The private preview may have expired. Reopen the atlas with an active service.',
                        'The saved model could not be reached. Reload the atlas or try again later.')
    text = replace_once(text,
                        'Reopen the local atlas or request a fresh private preview;',
                        'Reload the published atlas;')
    return text.encode('utf-8')


def _init_worker(source, output, model_paths):
    global _SOURCE, _OUTPUT, _MODEL_PATHS
    _SOURCE, _OUTPUT, _MODEL_PATHS = source, output, model_paths


def _package_file(entry):
    name = entry['path']
    if name != '.nojekyll':
        relative_name(name)
    raw = (_SOURCE / name).read_bytes()
    if len(raw) != entry['bytes'] or sha(raw) != entry['sha256']:
        raise ValueError(f'Source preview hash differs: {name}')
    references = set()
    if name == 'index.html':
        text = raw.decode('utf-8')
        text = replace_once(text, 'Private LS AIS atlas · choose a target below.',
                            'LS AIS structure atlas · choose a target below.')
        raw = text.encode('utf-8')
    elif name == 'app.js':
        raw = public_app(raw)
    elif name.endswith('.json'):
        text = raw.decode('utf-8')
        def rewrite(match):
            path = match.group(1)
            if path not in _MODEL_PATHS:
                raise ValueError(f'Unrecorded model reference: {path}')
            references.add(path)
            return '"' + path + '.gz"'
        raw = MODEL_PATH.sub(rewrite, text).encode('utf-8')
    if name in _MODEL_PATHS:
        name += '.gz'
        raw = gzip.compress(raw, compresslevel=6, mtime=0)
    if name != '.nojekyll':
        inspect_artifact(raw, name)
    destination = _OUTPUT / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}, references


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
    model_paths = {row['path'] for row in source_files
                   if '/models/' in row['path'] and row['path'].endswith(('.pdb', '.cif'))}
    if len(model_paths) != 6072:
        raise ValueError('Reviewed model coordinate cohort differs')
    output.mkdir(parents=True)
    files = []
    references = set()
    with ProcessPoolExecutor(max_workers=8, initializer=_init_worker,
                             initargs=(source, output, model_paths)) as pool:
        for file, referenced in pool.map(_package_file, source_files, chunksize=16):
            files.append(file)
            references.update(referenced)
    if references != model_paths:
        raise ValueError(f'Model reference coverage differs: {len(references)} / {len(model_paths)}')
    total = sum(row['bytes'] for row in files)
    if total >= MAX_PUBLIC_BYTES:
        raise ValueError(f'Public bundle exceeds Pages size budget: {total}')
    release = {'kind': 'public-standard-doc1-cdk2-atlas',
               'scientific_execution': False,
               'source_preview_manifest_sha256': expected_manifest_sha256,
               'coordinate_transport': 'gzip PDB/CIF; original coordinate SHA-256 verified in browser',
               'model_coordinates': len(model_paths), 'files': sorted(files, key=lambda row: row['path'])}
    (output / 'export-manifest.json').write_text(json.dumps(release, indent=2) + '\n')
    print(json.dumps({'status': 'privacy_checked', 'files': len(files),
                      'model_coordinates': len(model_paths), 'bytes': total,
                      'manifest_sha256': sha((output / 'export-manifest.json').read_bytes())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-manifest-sha256', required=True)
    args = parser.parse_args()
    package(args.source, args.output, args.source_manifest_sha256)
