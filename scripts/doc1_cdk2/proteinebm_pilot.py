"""Hash-bound, one-model-per-target ProteinEBM Model 6 compatibility pilot.

The full construct sequence and coordinate files remain on Mimas. This runner
does not publish, rank, or cluster the cohort; it measures finite native scores,
GPU memory, and wall time before production resources are selected.
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


def run(plan_path, plan_hash, index):
    checked(plan_path, plan_hash)
    plan = json.loads(Path(plan_path).read_text())
    require(plan['operation'] == 'doc1_cdk2_proteinebm_one_model_per_target_pilot' and
            plan['scientific_execution'] is True and plan['paid_external_calls'] == 0,
            'Wrong pilot operation')
    checked(__file__, plan['pilot_script_sha256'])
    require(index in (0, 1), 'Exactly two frozen pilot targets are required')
    target = plan['targets'][index]
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
            'Accepted roster differs')
    roster_path = audit_path.parent / 'roster.jsonl'
    checked(roster_path, target['roster_sha256'])
    selection = [json.loads(line) for line in roster_path.open()
                 if json.loads(line)['model_id'] == target['model_id']]
    require(len(selection) == 1 and selection[0]['native_sha256'] == target['native_sha256'],
            'Selected original model differs')
    row = selection[0]
    require(Path(row['path']).is_relative_to(root / 'inputs' / target['id'] / 'pdb'),
            'Selected model escaped frozen intake')
    checked(row['path'], row['native_sha256'])
    private_path = audit_path.parent / 'private-construct.json'
    checked(private_path, target['private_construct_sha256'])
    sequences = json.loads(private_path.read_text())['sequences']
    require(list(sequences) == [c['id'] for c in config['chains']], 'Private chain order differs')
    for chain in config['chains']:
        sequence = sequences[chain['id']]
        require(len(sequence) == chain['residues'] and
                hashlib.sha256(sequence.encode()).hexdigest() == chain['sequence_sha256'],
                'Construct sequence hash differs')

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
    import numpy as np
    import torch
    require(torch.cuda.is_available() and torch.cuda.device_count() == 1,
            'Pilot requires one monitored CUDA GPU')
    np, torch, model, augment = load_native(native, 'cuda')
    from protein_ebm.data.protein_utils import residues_to_features, restypes

    expected = [{'id': c['id'], 'sequence': sequences[c['id']]} for c in config['chains']]
    positions, amino, indices, chain_ids = native_complex_features(
        row['path'], expected, residues_to_features)
    residues = sum(c['residues'] for c in config['chains'])
    sequence = ''.join(restypes[int(aa)] for aa in amino)
    require(positions.shape == (residues, 3) and
            sequence == ''.join(sequences[c['id']] for c in config['chains']) and
            set(chain_ids) == {0, 1, 2}, 'Full three-chain features differ')
    aa = amino.unsqueeze(0).cuda()
    idx = indices.unsqueeze(0).cuda()
    ce = torch.tensor([chain_ids], dtype=torch.long, device='cuda')
    with torch.no_grad():
        require(torch.equal(model.rel_pos(idx, ce), model.rel_pos(idx, 2-ce)),
                'Pair features are chain-label dependent')
        torch.manual_seed(plan['settings']['seed'])
        torch.cuda.manual_seed_all(plan['settings']['seed'])
        times = torch.linspace(plan['settings']['t_min'], plan['settings']['t_max'],
                               plan['settings']['n_samples'])
        coordinates = positions.unsqueeze(0).cuda()
        mask = torch.ones((1, residues), device='cuda')
        energies, partials = [], []
        started = time.monotonic()
        for t in times:
            noisy = augment(coordinates, mask)
            result = model.compute_energy(dict(
                aatype=aa, residue_idx=idx, mask=mask, chain_encoding=ce,
                external_contacts=torch.ones_like(aa), selfcond_coords=noisy,
                r_noisy=noisy, atom_mask=mask, t=torch.full((1,), float(t), device='cuda')))
            energy = result['energy'].detach().cpu().numpy()
            partial = result['per_residue_energy'].detach().cpu().numpy()
            require(energy.shape == (1,) and partial.shape == (1, residues) and
                    np.isfinite(energy).all() and np.isfinite(partial).all() and
                    np.allclose(partial.sum(-1), energy, rtol=2e-6, atol=2e-5),
                    'Native energy is nonfinite or inconsistent')
            energies.append(energy); partials.append(partial)
            del noisy, result
        torch.cuda.synchronize()
        elapsed = time.monotonic() - started
    peak = torch.cuda.max_memory_allocated()
    require(math.isfinite(elapsed) and peak < plan['resources']['max_gpu_bytes'],
            'Pilot exceeded GPU resource bound')
    output = Path(plan['output_root']) / target['id']
    output.mkdir(parents=True, exist_ok=False)
    matrix = output / 'energy-grid.npz'
    with matrix.open('xb') as stream:
        np.savez(stream, energy=np.stack(energies), per_residue_energy=np.stack(partials),
                 times=times.cpu().numpy())
    receipt = {'status': 'validated', 'target': target['id'], 'model_id': row['model_id'],
               'native_sha256': row['native_sha256'], 'plan_sha256': plan_hash,
               'energy_grid_sha256': digest(matrix), 'residues': residues,
               'energy_values': len(energies), 'seconds': elapsed,
               'peak_gpu_bytes': peak, 'chain_relabel_pair_features_exact': True,
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
