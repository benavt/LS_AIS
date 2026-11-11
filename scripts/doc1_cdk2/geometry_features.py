"""Make complete A/B/C C-alpha pair-distance features for accepted DOC1 rosters.

The condensed pair ordering is scipy.spatial.distance.pdist order. All accepted
models and all residues are retained; no terminal trim or feature subsample is
applied. Original structures stay on Mimas.
"""

import argparse
from collections import OrderedDict
import hashlib
import json
import math
import os
from pathlib import Path
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def ca_coordinates(raw, chains):
    import numpy as np

    expected = {chain['id']: chain['residues'] for chain in chains}
    residues = {chain['id']: OrderedDict() for chain in chains}
    for line in raw.splitlines():
        if not line.startswith(b'ATOM  ') or line[12:16].strip() != b'CA':
            continue
        require(len(line) >= 54, 'Truncated native C-alpha record')
        chain = line[21:22].decode('ascii')
        require(chain in residues and line[16:17] in (b' ', b'A') and line[26:27] == b' ',
                'Unexpected chain or ambiguous C-alpha atom')
        number = int(line[22:26])
        require(number not in residues[chain], 'Duplicate native C-alpha position')
        residues[chain][number] = tuple(float(line[i:i+8]) for i in (30, 38, 46))
    arrays = []
    for chain in chains:
        current = residues[chain['id']]
        require(list(current) == list(range(1, expected[chain['id']] + 1)),
                'Incomplete native C-alpha chain')
        arrays.extend(current.values())
    coords = np.asarray(arrays, dtype=np.float64)
    require(coords.shape == (sum(expected.values()), 3) and np.isfinite(coords).all(),
            'Nonfinite or incomplete native C-alpha coordinates')
    return coords


def run(plan_path, plan_hash, target_index):
    import numpy as np
    from scipy.spatial.distance import pdist

    require(digest(plan_path) == plan_hash, 'Frozen geometry plan hash differs')
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_complete_ca_pair_features' and
            plan['scientific_execution'] and plan['paid_external_calls'] == 0,
            'Wrong geometry operation')
    require(digest(__file__) == plan['source_script_sha256'], 'Frozen geometry code differs')
    require(target_index in (0, 1), 'Exactly two frozen target tasks are required')
    target = plan['targets'][target_index]
    config_path = Path(target['config_path'])
    require(digest(config_path) == target['config_sha256'], 'Target configuration differs')
    config = json.loads(config_path.read_text())
    require(config['id'] == target['id'], 'Target identity differs')
    audit_path = Path(target['audit_path'])
    require(digest(audit_path) == target['audit_sha256'], 'Accepted audit differs')
    audit = json.loads(audit_path.read_text())
    require(audit['status'] == 'validated' and
            audit['validated_models'] == target['validated_models'] and
            audit['roster_sha256'] == target['roster_sha256'],
            'Accepted roster identity differs')
    roster = audit_path.parent / 'roster.jsonl'
    require(digest(roster) == target['roster_sha256'], 'Roster hash differs')
    count = target['validated_models']
    residues = sum(chain['residues'] for chain in config['chains'])
    pairs = residues * (residues - 1) // 2
    require(residues == target['residues'] and pairs == target['pairs'],
            'Full-construct pair scope differs')
    output = Path(plan['output_root']) / target['id']
    output.mkdir(parents=True, exist_ok=False)
    matrix_path = output / 'pair-distances.f32'
    matrix = np.memmap(matrix_path, dtype='<f4', mode='w+', shape=(count, pairs))
    started = time.monotonic()
    native_root = Path(plan['intake_root']) / 'inputs' / target['id'] / 'pdb'
    with roster.open() as stream:
        for index, line in enumerate(stream):
            require(index < count, 'Roster has excess models')
            row = json.loads(line)
            path = Path(row['path'])
            require(path.is_relative_to(native_root), 'Original PDB escaped intake')
            raw = path.read_bytes()
            require(hashlib.sha256(raw).hexdigest() == row['native_sha256'],
                    'Original PDB identity differs')
            coords = ca_coordinates(raw, config['chains'])
            distances = pdist(coords, metric='euclidean')
            require(distances.shape == (pairs,) and np.isfinite(distances).all() and
                    np.all(distances >= 0), 'Invalid complete pair-distance row')
            matrix[index] = distances.astype('<f4', copy=False)
            if (index + 1) % 1000 == 0:
                matrix.flush()
                print('geometry', target['id'], index + 1, 'of', count, flush=True)
        require(index + 1 == count, 'Roster is incomplete')
    matrix.flush()
    del matrix
    seconds = time.monotonic() - started
    require(math.isfinite(seconds) and matrix_path.stat().st_size == 4 * count * pairs,
            'Pair-distance matrix size differs')
    receipt = {'status': 'validated', 'target': target['id'], 'plan_sha256': plan_hash,
               'models': count, 'residues': residues, 'pairs_per_model': pairs,
               'shape': [count, pairs], 'dtype': 'float32 little-endian',
               'pair_order': 'scipy pdist condensed upper triangle',
               'scope': 'complete native A/B/C complex', 'roster_sha256': target['roster_sha256'],
               'matrix_sha256': digest(matrix_path), 'matrix_bytes': matrix_path.stat().st_size,
               'seconds': seconds}
    (output / 'acceptance.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, sort_keys=True), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--plan-sha256', required=True)
    args = parser.parse_args()
    run(args.plan, args.plan_sha256, int(os.environ['SLURM_ARRAY_TASK_ID']))


if __name__ == '__main__':
    main()
