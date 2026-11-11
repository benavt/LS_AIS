"""Score accepted DOC1/CDK2 three-chain cohorts with frozen ProteinEBM Model 6.

Each Slurm array task owns one disjoint source-roster interval. Native coordinates
and complete construct sequences stay on Mimas. The output is a hash-joined
scientific score grid, not an atlas export or publication.
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
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


def checked(path, expected):
    require(digest(path) == expected, 'Frozen file hash differs: ' + str(path))


def chunk_intervals(count, width):
    require(type(count) is int and count > 0 and type(width) is int and width > 0,
            'Invalid cohort cardinality or chunk width')
    return [(start, min(start + width, count)) for start in range(0, count, width)]


def load_rows(roster_path, start, end, expected_count):
    selected = []
    total = 0
    with roster_path.open() as stream:
        for total, line in enumerate(stream, start=1):
            if start <= total - 1 < end:
                selected.append(json.loads(line))
    require(total == expected_count and len(selected) == end - start,
            'Roster cardinality or chunk interval differs')
    return selected


def load_inputs(plan, target, start, end):
    root = Path(plan['intake_root'])
    config_path = Path(target['config_path'])
    checked(config_path, target['config_sha256'])
    config = json.loads(config_path.read_text())
    require(config['id'] == target['id'], 'Target configuration differs')
    audit_path = Path(target['audit_path'])
    checked(audit_path, target['audit_sha256'])
    audit = json.loads(audit_path.read_text())
    require(audit['status'] == 'validated' and
            audit['validated_models'] == target['validated_models'] and
            audit['roster_sha256'] == target['roster_sha256'] and
            audit['private_construct_sha256'] == target['private_construct_sha256'],
            'Accepted model roster differs')
    roster = audit_path.parent / 'roster.jsonl'
    checked(roster, target['roster_sha256'])
    rows = load_rows(roster, start, end, target['validated_models'])
    require(len({r['model_id'] for r in rows}) == len(rows), 'Duplicate model ID in chunk')
    private = audit_path.parent / 'private-construct.json'
    checked(private, target['private_construct_sha256'])
    sequences = json.loads(private.read_text())['sequences']
    require(list(sequences) == [chain['id'] for chain in config['chains']],
            'Private chain order differs')
    for chain in config['chains']:
        sequence = sequences[chain['id']]
        require(len(sequence) == chain['residues'] and
                hashlib.sha256(sequence.encode()).hexdigest() == chain['sequence_sha256'],
                'Private construct sequence hash differs')
    native_root = root / 'inputs' / target['id'] / 'pdb'
    for row in rows:
        require(Path(row['path']).is_relative_to(native_root),
                'Original PDB escaped accepted intake')
        checked(row['path'], row['native_sha256'])
    return config, sequences, rows


def load_model(plan):
    native = plan['native']
    source = Path(native['native_source'])
    for name, value in native['files'].items():
        checked(source / name, value)
    for name, value in native['runtime_identity'].items():
        checked(name, value)
    checked(native['checkpoint']['path'], native['checkpoint']['sha256'])
    checked(native['config']['path'], native['config']['sha256'])
    folder = Path(plan['library_source']) / 'scripts/proteinebm_complex'
    for name, value in plan['library_files_sha256'].items():
        checked(folder / name, value)
    sys.path.insert(0, str(folder))
    from worker import native as load_native
    from features import native_complex_features
    import torch
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1,
            'One monitored CUDA GPU required; CPU inference fallback forbidden')
    np, torch, model, augment = load_native(native, 'cuda')
    from protein_ebm.data.protein_utils import residues_to_features, restypes
    return np, torch, model, augment, native_complex_features, residues_to_features, restypes


def run(plan_path, plan_hash, task):
    checked(plan_path, plan_hash)
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_proteinebm_complete_rosters' and
            plan['scientific_execution'] is True and plan['paid_external_calls'] == 0,
            'Wrong scoring operation')
    checked(__file__, plan['source_script_sha256'])
    require(type(task) is int and 0 <= task < len(plan['chunks']), 'Array task outside frozen plan')
    chunk = plan['chunks'][task]
    target = plan['targets'][chunk['target_index']]
    expected = chunk_intervals(target['validated_models'], plan['settings']['chunk_size'])
    require((chunk['start'], chunk['end']) == expected[chunk['chunk_index']],
            'Frozen chunk boundary differs')
    for pilot in plan['pilot_gate']:
        checked(pilot['receipt_path'], pilot['receipt_sha256'])
        receipt = json.loads(Path(pilot['receipt_path']).read_text())
        require(receipt['status'] == 'validated' and
                receipt['plan_sha256'] == plan['pilot_plan_sha256'] and
                receipt['target'] == pilot['target'] and
                receipt['energy_values'] == 16 and
                receipt['chain_relabel_pair_features_exact'],
                'Three-chain compatibility pilot is not accepted')
        checked(Path(pilot['receipt_path']).parent / 'energy-grid.npz', receipt['energy_grid_sha256'])
    config, sequences, rows = load_inputs(plan, target, chunk['start'], chunk['end'])
    np, torch, model, augment, native_features, converter, restypes = load_model(plan)
    residues = sum(c['residues'] for c in config['chains'])
    expected_chains = [{'id': c['id'], 'sequence': sequences[c['id']]}
                       for c in config['chains']]
    expected_sequence = ''.join(c['sequence'] for c in expected_chains)
    times = torch.linspace(plan['settings']['t_min'], plan['settings']['t_max'],
                           plan['settings']['n_samples'])
    require(len(times) == 16 and abs(float(times[10]) - 0.10) < 1e-7,
            'Wrong native score time grid')
    energies = np.empty((len(rows), 16), dtype=np.float32)
    partials = np.empty((len(rows), 16, residues), dtype=np.float32)
    ids, native_hashes = [], []
    started = time.monotonic()
    with torch.no_grad():
        for local_index, row in enumerate(rows):
            positions, amino, indices, chain_ids = native_features(
                row['path'], expected_chains, converter)
            sequence = ''.join(restypes[int(value)] for value in amino)
            require(positions.shape == (residues, 3) and
                    sequence == expected_sequence and set(chain_ids) == {0, 1, 2},
                    'Native complete three-chain features differ')
            aa = amino.unsqueeze(0).cuda()
            idx = indices.unsqueeze(0).cuda()
            ce = torch.tensor([chain_ids], dtype=torch.long, device='cuda')
            if local_index == 0:
                require(torch.equal(model.rel_pos(idx, ce), model.rel_pos(idx, 2-ce)),
                        'Native pair features depend on chain labels')
            coordinates = positions.unsqueeze(0).cuda()
            mask = torch.ones((1, residues), device='cuda')
            seed = plan['settings']['seed'] + chunk['start'] + local_index
            torch.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            for level, t in enumerate(times):
                noisy = augment(coordinates, mask)
                result = model.compute_energy(dict(
                    aatype=aa, residue_idx=idx, mask=mask, chain_encoding=ce,
                    external_contacts=torch.ones_like(aa), selfcond_coords=noisy,
                    r_noisy=noisy, atom_mask=mask,
                    t=torch.full((1,), float(t), device='cuda')))
                energy = result['energy'].detach().cpu().numpy()
                partial = result['per_residue_energy'].detach().cpu().numpy()
                require(energy.shape == (1,) and partial.shape == (1, residues) and
                        np.isfinite(energy).all() and np.isfinite(partial).all() and
                        np.allclose(partial.sum(-1), energy, rtol=2e-6, atol=2e-5),
                        'Native energy is nonfinite or inconsistent')
                energies[local_index, level] = energy[0]
                partials[local_index, level] = partial[0]
                del noisy, result
            ids.append(row['model_id']); native_hashes.append(row['native_sha256'])
            if (local_index + 1) % 100 == 0:
                print('scored', target['id'], chunk['chunk_index'], local_index + 1,
                      'of', len(rows), flush=True)
        torch.cuda.synchronize()
    elapsed = time.monotonic() - started
    peak = torch.cuda.max_memory_allocated()
    require(math.isfinite(elapsed) and peak < plan['resources']['max_gpu_bytes'] and
            np.isfinite(energies).all() and np.isfinite(partials).all() and
            np.allclose(partials.sum(-1), energies, rtol=2e-6, atol=2e-5),
            'Full scoring chunk failed resource or grid acceptance')
    output = Path(plan['output_root']) / target['id'] / ('chunk-%03d' % chunk['chunk_index'])
    output.mkdir(parents=True, exist_ok=False)
    grid = output / 'energy-grid.npz'
    with grid.open('xb') as stream:
        np.savez(stream, energy=energies, per_residue_energy=partials,
                 times=times.numpy(), model_ids=np.asarray(ids),
                 native_sha256=np.asarray(native_hashes))
    receipt = {'status': 'validated', 'target': target['id'], 'chunk_index': chunk['chunk_index'],
               'start': chunk['start'], 'end': chunk['end'], 'models': len(rows),
               'energy_values': 16 * len(rows), 'residues': residues,
               'plan_sha256': plan_hash, 'grid_sha256': digest(grid),
               'first_model_id': ids[0], 'last_model_id': ids[-1],
               'seconds': elapsed, 'peak_gpu_bytes': peak,
               'units': 'learned arbitrary units; not binding energy'}
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
