"""Audit full three-chain PDB cohorts before any scientific calculation.

The private run retains complete sequences on Mimas. Standard output contains
only aggregate counts and hashes; source configuration contains sequence hashes.
"""

import argparse
from collections import Counter, OrderedDict
import hashlib
import json
import math
from pathlib import Path
import re


AA = {
    b'ALA': 'A', b'ARG': 'R', b'ASN': 'N', b'ASP': 'D', b'CYS': 'C',
    b'GLN': 'Q', b'GLU': 'E', b'GLY': 'G', b'HIS': 'H', b'ILE': 'I',
    b'LEU': 'L', b'LYS': 'K', b'MET': 'M', b'PHE': 'F', b'PRO': 'P',
    b'SER': 'S', b'THR': 'T', b'TRP': 'W', b'TYR': 'Y', b'VAL': 'V',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def inspect_pdb(raw, expected):
    residues = {row['id']: OrderedDict() for row in expected}
    model_records = 0
    for line in raw.splitlines():
        if line.startswith(b'MODEL '):
            model_records += 1
        if not line.startswith(b'ATOM  ') or line[12:16].strip() != b'CA':
            continue
        if len(line) < 66:
            raise ValueError('truncated CA record')
        chain = line[21:22].decode('ascii')
        if chain not in residues:
            raise ValueError('unexpected chain')
        if line[16:17] not in (b' ', b'A') or line[26:27] != b' ':
            raise ValueError('ambiguous alternate or insertion')
        number = int(line[22:26])
        aa = AA.get(line[17:20])
        if aa is None:
            raise ValueError('nonstandard CA residue')
        xyz = [float(line[i:i+8]) for i in (30, 38, 46)]
        if not all(math.isfinite(x) for x in xyz):
            raise ValueError('nonfinite CA coordinate')
        if number in residues[chain]:
            raise ValueError('duplicate chain/residue CA')
        residues[chain][number] = aa
    if model_records > 1:
        raise ValueError('multiple coordinate models')
    sequences = {}
    for row in expected:
        chain = row['id']
        values = residues[chain]
        if list(values) != list(range(1, row['residues'] + 1)):
            raise ValueError('incomplete or noncanonical chain numbering')
        sequence = ''.join(values.values())
        if sha(sequence.encode()) != row['sequence_sha256']:
            raise ValueError('chain sequence differs from construct')
        sequences[chain] = sequence
    return sequences


def validate(config_path, intake_root, output):
    config = json.loads(config_path.read_text())
    target = config['id']
    source = intake_root / 'inputs' / target
    receipt = json.loads((source / 'acceptance.json').read_text())
    if receipt['status'] != 'validated' or receipt['archive_sha256'] != config['cohort']['archive_sha256']:
        raise ValueError('Frozen archive intake differs')
    listing = source / 'pdb-sha256.jsonl'
    if sha_file(listing) != receipt['manifest_sha256']:
        raise ValueError('Extracted file manifest differs')
    output.mkdir()
    counts = Counter()
    seen_names = set()
    seen_hashes = set()
    duplicates = 0
    rejected = 0
    private_sequences = None
    with listing.open() as rows, (output / 'roster.jsonl').open('x') as accepted, (output / 'rejections.jsonl').open('x') as failures:
        for line in rows:
            entry = json.loads(line)
            name = entry.get('name', '<missing>')
            try:
                if Path(name).name != name or not name.endswith('.pdb') or name in seen_names:
                    raise ValueError('unsafe or duplicate model name')
                seen_names.add(name)
                path = source / 'pdb' / name
                raw = path.read_bytes()
                if len(raw) != entry['bytes'] or sha(raw) != entry['sha256']:
                    raise ValueError('native PDB hash or size differs')
                sequences = inspect_pdb(raw, config['chains'])
                if private_sequences is None:
                    private_sequences = sequences
                stem = Path(name).stem
                match = re.fullmatch(r'(.+)_([0-9]+)', stem)
                if match is None:
                    raise ValueError('unrecognized model filename')
                method = match.group(1)
                accepted.write(json.dumps({'model_id': stem, 'method': method, 'name': name,
                                           'path': str(path), 'native_sha256': entry['sha256']}, separators=(',', ':')) + '\n')
                counts[method] += 1
                if entry['sha256'] in seen_hashes:
                    duplicates += 1
                seen_hashes.add(entry['sha256'])
            except (KeyError, OSError, UnicodeError, ValueError) as error:
                rejected += 1
                failures.write(json.dumps({'name': name, 'reason': str(error)}, separators=(',', ':')) + '\n')
    total = sum(counts.values()) + rejected
    if total != receipt['models'] or total != config['cohort']['expected_models']:
        raise ValueError('Manifest cardinality differs from frozen cohort')
    if private_sequences is not None:
        private = output / 'private-construct.json'
        private.write_text(json.dumps({'target': target, 'sequences': private_sequences}, separators=(',', ':')) + '\n')
        private.chmod(0o600)
    summary = {
        'status': 'validated' if rejected == 0 else 'rejected',
        'target': target, 'input_models': total, 'validated_models': sum(counts.values()),
        'rejected_models': rejected, 'duplicate_native_hashes': duplicates,
        'methods': dict(sorted(counts.items())), 'source_manifest_sha256': receipt['manifest_sha256'],
        'target_config_sha256': sha_file(config_path),
        'roster_sha256': sha_file(output / 'roster.jsonl'),
        'private_construct_sha256': sha_file(output / 'private-construct.json') if private_sequences is not None else None,
    }
    (output / 'audit.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'methods'}), flush=True)
    if rejected:
        raise ValueError('PDB cohort contains rejected models; inspect private rejections and freeze a new selection')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--intake-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    validate(args.config, args.intake_root, args.output)


if __name__ == '__main__':
    main()
