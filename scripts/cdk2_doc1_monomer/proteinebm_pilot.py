"""Hash-bound native ProteinEBM Model 6 compatibility pilot; no site-build entrypoint."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def check(ok, message):
    if not ok:
        raise ValueError(message)


def features(path, chains, converter):
    import numpy as np
    from Bio.PDB import MMCIFParser, PDBParser
    from Bio.PDB.Polypeptide import is_aa
    from Bio.SeqUtils import seq1

    parser = MMCIFParser(QUIET=True) if path.endswith('.cif') else PDBParser(QUIET=True)
    models = list(parser.get_structure('complex', path))
    check(len(models) == 1, 'Expected one coordinate model')
    native = {chain.id: chain for chain in models[0]}
    check(set(native) == {c['native_id'] for c in chains}, 'Native chains changed')
    residues, encodings = [], []
    for encoding, chain in enumerate(chains):
        current = list(native[chain['native_id']])
        check(current and all(is_aa(r, standard=True) for r in current), 'Nonstandard residue')
        check(''.join(seq1(r.resname) for r in current) == chain['sequence'], 'Sequence changed')
        check([r.id[1] for r in current] == list(range(1, len(current) + 1)),
              'Residue numbering changed')
        check(all('CA' in r and not r.id[2].strip() for r in current), 'C-alpha missing')
        residues.extend(current)
        encodings.extend([encoding] * len(current))
    positions, mask, aa, indices = converter(residues)
    check(bool((mask[:, 1] == 1).all()) and bool(np.isfinite(positions.numpy()).all()),
          'C-alpha coordinates invalid')
    return positions[:, 1], aa, indices, encodings


def run(plan, output):
    import numpy as np
    import torch
    import yaml
    from ml_collections import ConfigDict
    sys.path.insert(0, plan['native_source'])
    from protein_ebm.data.protein_utils import residues_to_features
    from protein_ebm.model.ebm import ProteinEBM
    from protein_ebm.model.r3_diffuser import R3Diffuser
    from protein_ebm.model.boltz_utils import center_random_augmentation

    check(torch.cuda.is_available() and torch.cuda.device_count() == 1,
          'One GPU required; no CPU fallback')
    torch.set_num_threads(1)
    config = ConfigDict(yaml.safe_load(Path(plan['config']['path']).read_text()))
    check(not config.model.diffuse_sidechain and config.model.num_contact_embeddings == 3,
          'Wrong native Model 6 architecture')
    model = ProteinEBM(config.model, R3Diffuser(config.diffuser)).cuda()
    checkpoint = torch.load(plan['checkpoint']['path'], map_location='cpu', weights_only=False)
    model.load_state_dict({k[6:]: v for k, v in checkpoint['state_dict'].items()
                           if k.startswith('model.')}, strict=True)
    model.eval()
    torch.manual_seed(215600)
    torch.cuda.manual_seed_all(215600)
    np.random.seed(215600)
    results = []
    with torch.no_grad():
        for row in plan['inputs']:
            chains = [dict(chain, native_id=row['native_chain_ids'][index])
                      for index, chain in enumerate(plan['chains'])]
            coords, aa, indices, ce = features(row['path'], chains, residues_to_features)
            aa, indices = aa[None].cuda(), indices[None].cuda()
            ce = torch.tensor(ce, dtype=torch.long)[None].cuda()
            mask = torch.ones_like(aa, dtype=torch.float)
            energies = []
            for t in torch.linspace(0.0, 0.15, 16):
                noisy = center_random_augmentation(coords[None], torch.ones_like(mask.cpu())).cuda()
                result = model.compute_energy(dict(
                    aatype=aa, residue_idx=indices, mask=mask, chain_encoding=ce,
                    external_contacts=torch.ones_like(aa), selfcond_coords=noisy,
                    r_noisy=noisy, atom_mask=mask,
                    t=torch.full((1,), float(t), device='cuda')))
                energy = float(result['energy'][0])
                parts = result['per_residue_energy'][0]
                check(math.isfinite(energy) and bool(torch.isfinite(parts).all()) and
                      math.isclose(float(parts.sum()), energy, rel_tol=2e-6, abs_tol=2e-5),
                      'Nonfinite or inconsistent energy')
                check(torch.cuda.max_memory_allocated() < 56 * 2**30,
                      'GPU memory budget exceeded')
                energies.append(energy)
            results.append(dict(model_id=row['model_id'], source_sha256=row['sha256'],
                                method=row['method'], physicality=row.get('physicality'),
                                energy_t010=energies[10], energies=energies))
    with Path(output).open('x') as f:
        json.dump(dict(schema='ls-ais-ebm-pilot-result-v1', target=plan['target'],
                       count=len(results), results=results,
                       peak_gpu_bytes=torch.cuda.max_memory_allocated()), f,
                  sort_keys=True, indent=2)
        f.write('\n')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--plan', required=True)
    p.add_argument('--plan-sha256', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    check(os.environ.get('SLURM_JOB_ID'), 'Slurm job required')
    check(digest(a.plan) == a.plan_sha256, 'Plan differs from approved hash')
    plan = json.loads(Path(a.plan).read_text())
    check(plan['schema'] == 'ls-ais-ebm-pilot-v1', 'Unknown plan schema')
    check(digest(__file__) == plan['code_sha256'], 'Pilot code hash changed')
    check(plan['target'] in {'CDK2_DOC1', 'CDK2_DOC1t'}, 'Wrong target')
    check(len(plan['inputs']) in (3, 4), 'Wrong pilot size')
    check(len({x['model_id'] for x in plan['inputs']}) == len(plan['inputs']),
          'Duplicate input identity')
    check(plan['settings'] == dict(n_samples=16, t_min=0.0, t_max=0.15,
                                   batch_size=16, seed=215600, primary_time_index=10,
                                   template_self_condition=True,
                                   inference_self_condition=False, ensemble_size=0,
                                   mask_sequence=False, score_norm_energy=False),
          'Scoring settings changed')
    for k in ('checkpoint', 'config'):
        check(digest(plan[k]['path']) == plan[k]['sha256'], k + ' hash changed')
    for relative, expected in plan['native_file_sha256'].items():
        check(digest(Path(plan['native_source']) / relative) == expected,
              'Native source hash changed: ' + relative)
    for row in plan['inputs']:
        check(len(row['native_chain_ids']) == 2 and
              len(set(row['native_chain_ids'])) == 2, 'Wrong native chain mapping')
        check(digest(row['path']) == row['sha256'], row['model_id'] + ' hash changed')
    run(plan, a.output)


if __name__ == '__main__':
    main()
