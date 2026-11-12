"""Independently check saved 0865 DockQ contact fractions from native PDBs.

This read-only audit accepts the user-supplied AFsample3 PDB exports. It never
invokes DockQ or updates the atlas. A mismatch is an error, including a shifted
residue index or chain swap.
"""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


SCORES_SHA = 'fc321f809ab9977948bf49a70bd6abfd3334ce3a681ad8ca531293f28be2b62f'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atoms(path):
    chains = {'A': defaultdict(list), 'B': defaultdict(list)}
    residue_names = {'A': {}, 'B': {}}
    for line in Path(path).open():
        if not line.startswith('ATOM  ') or line[21] not in chains:
            continue
        chain = line[21]
        residue = int(line[22:26])
        name = line[17:20].strip()
        previous = residue_names[chain].setdefault(residue, name)
        if name != previous:
            raise ValueError(f'{path}: inconsistent residue {chain}{residue}')
        if line[76:78].strip() in ('H', 'D'):
            continue
        coord = tuple(float(line[i:i + 8]) for i in (30, 38, 46))
        chains[chain][residue].append(coord)
    for chain, length in (('A', 298), ('B', 115)):
        if sorted(chains[chain]) != list(range(1, length + 1)):
            raise ValueError(f'{path}: {chain} residue indices are not 1–{length}')
    return chains, residue_names


def contacts(chains):
    # A 5 Å spatial hash gives the same residue-pair criterion as a full
    # heavy-atom cross product without depending on DockQ's parser.
    cells = defaultdict(list)
    for residue, coords in chains['B'].items():
        for xyz in coords:
            cell = tuple(int(x // 5) for x in xyz)
            cells[cell].append((residue, xyz))
    result = set()
    for a_residue, coords in chains['A'].items():
        for xyz in coords:
            cell = tuple(int(x // 5) for x in xyz)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        for b_residue, other in cells.get((cell[0] + dx,
                                                           cell[1] + dy,
                                                           cell[2] + dz), ()):
                            if sum((x - y) ** 2 for x, y in zip(xyz, other)) < 25:
                                result.add((a_residue, b_residue))
    return result


def audit(reference, models, scores, expected_hashes):
    if digest(scores) != SCORES_SHA:
        raise ValueError('Accepted DockQ score table SHA-256 differs')
    reference_chains, reference_names = atoms(reference)
    if digest(reference) != expected_hashes['reference']:
        raise ValueError('Reference PDB SHA-256 differs')
    native_contacts = contacts(reference_chains)
    if len(native_contacts) != 23:
        raise ValueError('0865 reference contact count differs')
    saved = {row['model_id']: row for row in csv.DictReader(Path(scores).open())}
    output = []
    for model_id, path in models.items():
        if digest(path) != expected_hashes[model_id]:
            raise ValueError(f'{model_id}: PDB SHA-256 differs')
        model_chains, model_names = atoms(path)
        if model_names != reference_names:
            raise ValueError(f'{model_id}: chain sequence or residue indexing differs')
        pairs = contacts(model_chains)
        recovered = len(native_contacts & pairs)
        independent = recovered / len(native_contacts)
        reported = float(saved[model_id]['fnat'])
        if abs(independent - reported) > 0.0005:
            raise ValueError(f'{model_id}: independent fnat {independent:.3f} '
                             f'!= saved {reported:.3f}')
        output.append(dict(model_id=model_id, native_contacts=len(native_contacts),
                           model_contacts=len(pairs), recovered=recovered,
                           independent_fnat=round(independent, 3),
                           reported_fnat=reported, status='matched'))
    return output


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--reference', type=Path, required=True)
    cli.add_argument('--model', action='append', nargs=2, metavar=('MODEL_ID', 'PDB'), required=True)
    cli.add_argument('--scores', type=Path, required=True)
    cli.add_argument('--hashes', type=Path, required=True,
                     help='JSON object: reference and model IDs to SHA-256 digests')
    args = cli.parse_args()
    models = {model_id: Path(path) for model_id, path in args.model}
    if len(models) != len(args.model):
        raise ValueError('Duplicate model ID')
    for row in audit(args.reference, models, args.scores,
                     json.loads(args.hashes.read_text())):
        print(json.dumps(row, sort_keys=True))


if __name__ == '__main__':
    main()
