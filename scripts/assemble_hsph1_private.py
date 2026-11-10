"""Adapt the accepted saved HSPH1 bytes to the shared explorer; no scientific fits."""
import argparse
import collections
import copy
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
TARGET = 'HSPH1_12757_homodimer'
DELIVERY_SHA = 'a9b5c44b6a25c0d142c073e624c078c67d99f63826fcaca0f8203e4ac9d4ce13'
BASE_SHA = '4daf9e1fd8cf651d716015f033602047854ea565aa41fd7498f9c063ada77da7'
LIBRARY = 'f3063757460303e1a4a4ba0b3629fe81776c58c4'


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unlink a saved hard link before writing a successor presentation artifact.
    if path.exists():
        path.unlink()
    with path.open('xb') as stream:
        stream.write(raw)


def save(path, value):
    put(path, (json.dumps(value, indent=2, allow_nan=False) + '\n').encode())


def compact_hash(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def csv_bytes(fields, rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode()


def verified(root, rows):
    if isinstance(rows, dict):
        rows = [dict(path=name, **row) for name, row in rows.items()]
    for row in rows:
        name = row['path']
        need(not Path(name).is_absolute() and '..' not in Path(name).parts, 'Unsafe saved path')
        path = root / name
        need(path.is_file() and not path.is_symlink(), 'Missing regular artifact: ' + name)
        need(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Saved bytes changed: ' + name)
    return rows


def build(base, supplements, output):
    import numpy as np
    from src.analysis.atlas_presentation import validate_views
    from structure_clustering.publication import render_project_html

    need(not output.exists(), 'Use a fresh private output directory')
    need(shutil.disk_usage(output.parent if output.parent.exists() else ROOT).free > 52 * 2**30,
         'Need 2 GiB output allowance plus 50 GiB free reserve')
    baseline = ROOT / 'config/publication-candidate.json'
    need(sha(baseline) == BASE_SHA, 'Baseline review manifest changed')
    base_rows = verified(base, read(baseline)['files'])
    manifest = supplements / 'delivery-manifest.json'
    need(sha(manifest) == DELIVERY_SHA, 'Accepted scientific delivery differs')
    delivery = read(manifest)
    need(delivery['status'] == 'accepted_private_scientific_delivery', 'Unaccepted supplements')
    verified(supplements, delivery['files'])
    output.mkdir(parents=True)
    for row in base_rows:
        destination = output / row['path']
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.link(base / row['path'], destination)

    data = read(output / TARGET / 'primary.json')
    names = data['models']
    need(len(names) == len(set(names)) == 4006, 'Wrong base population')
    lookup = {name: index for index, name in enumerate(names)}
    native_sha = dict(zip(names, data['model_sha256']))
    native_file = dict(zip(names, data['model_files']))
    with (supplements / 'current4006-energy-rankings.csv').open() as stream:
        energy_rows = list(csv.DictReader(stream))
    energies = {row['model_id']: row for row in energy_rows}
    need(set(energies) == set(names), 'Incomplete energy join')
    for name in names:
        row = energies[name]
        need(row['sha256'] == native_sha[name], 'Energy/native hash mismatch')
        need(all(math.isfinite(float(row[f'energy_t{i:02d}'])) for i in range(16)), 'Nonfinite energy')
    energy = [float(energies[name]['energy_t010']) for name in names]
    score = next(row for row in data['schemes'] if row['key'] == 'protein_ebm_energy_t10')
    score.update(values=energy, range=[min(energy), max(energy)], unavailable=False,
                 provenance=dict(model_commit='2abfc58571e6528edf0919daf37a6c74bcf77f67',
                                 scores_sha256=sha(supplements / 'current4006-energy-rankings.csv'),
                                 unit_note='Learned arbitrary units; not physical free energy or confidence.'))
    data.update(view_id='primary', view_title='Complete homodimer · UMAP KNN')
    data['provenance'].update(energy_status='Accepted: all 4006 models, 16 time indices',
                              scientific_delivery_sha256=DELIVERY_SHA)
    data['native_data_links'] = dict(methods=f'{TARGET}/dataset/README.md',
                                    scores=f'{TARGET}/dataset/scores.csv',
                                    energies=f'{TARGET}/science/current4006-energy-rankings.csv',
                                    sampling=f'{TARGET}/science/states/sampling_002/S2-summary.json',
                                    diagnostics=f'{TARGET}/dataset/sampling.html')

    # Native scientific supplements are namespaced per target. Numeric NPZ files
    # are losslessly serialized as typed JSON arrays, allowing the unchanged
    # shared text/container privacy gate to inspect every browser download.
    trace_inventory = []
    for name, record in delivery['files'].items():
        source = supplements / name
        relative = f'{TARGET}/science/{name}'
        if source.suffix == '.npz':
            with np.load(source, allow_pickle=False) as arrays:
                payload = dict(source_sha256=record['sha256'], arrays={})
                for key in arrays.files:
                    array = arrays[key]
                    need(array.dtype.kind in 'biufUS', 'Unsupported native trace dtype')
                    if array.dtype.kind in 'f':
                        need(np.isfinite(array).all(), 'Nonfinite native trace')
                    values = array.tolist()
                    # Round-trip verifies that presentation serialization changes no numeric value.
                    need(np.array_equal(np.asarray(values, dtype=array.dtype), array), 'Trace serialization differs')
                    payload['arrays'][key] = dict(dtype=str(array.dtype), shape=list(array.shape), values=values)
            raw = (json.dumps(payload, separators=(',', ':'), allow_nan=False) + '\n').encode()
            relative = relative[:-4] + '.json.gz'
            put(output / relative, gzip.compress(raw, mtime=0))
            trace_inventory.append(dict(file=relative, native_npz_sha256=record['sha256'], sha256=sha(output / relative)))
        else:
            put(output / relative, source.read_bytes())

    partition = read(supplements / 'HDBSCAN/partition.json')
    selection = read(supplements / 'HDBSCAN/supplement/selection.json')
    need(set(partition['models']) == set(names) and partition['clusters'] == 68 and partition['noise_models'] == 1386,
         'Unexpected density population')
    index = {name: i for i, name in enumerate(partition['models'])}
    density = copy.deepcopy(data)
    density.update(view_id='density', view_title='Complete homodimer · HDBSCAN',
                   clusters=[partition['labels'][index[name]] for name in names],
                   density_strengths=[partition['strengths'][index[name]] for name in names],
                   density_raw_labels=[partition['raw_labels'][index[name]] for name in names],
                   density_noise_examples=selection['noise_examples'])
    density['schemes'][0].update(values=density['clusters'], colors=partition['colors'])
    density['schemes'].append(dict(key='hdbscan_membership', name='HDBSCAN membership strength',
                                  type='continuous', values=density['density_strengths'], range=[0, 1], colorscale='Viridis'))
    density['clustering_method_note'] = ('Geometry-only HDBSCAN on the saved 10D UMAP, seed42 leaf; '
        'n_neighbors30, min_dist0, min_cluster_size15, min_samples11. Six seed/leaf/EOM fits retained. '
        'All4006 models are displayed, including1386 Unassigned models. Colors reuse the saved2D projections; no projection refits.')
    density['representatives'] = []
    for group in selection['clusters']:
        medoid = group['medoid']; name = medoid['model']
        need(medoid['native_sha256'] == native_sha[name], 'Density medoid/native hash mismatch')
        members = group['selected']
        for row in members:
            need(row['native_sha256'] == native_sha[row['model']], 'Density selected member hash mismatch')
        ensemble = f'{TARGET}/science/HDBSCAN/supplement/{group["ensemble_file"]}.gz'
        need(hashlib.sha256(gzip.decompress((output / ensemble).read_bytes())).hexdigest() == group['ensemble_sha256'],
             'Density ensemble bytes differ')
        plain_ensemble = ensemble[:-3]
        put(output / plain_ensemble, gzip.decompress((output / ensemble).read_bytes()))
        density['representatives'].append(dict(cluster=group['cluster_label'], count=group['cluster_size'], model=name,
            method=data['methods'][lookup[name]], color=group['color'], file=native_file[name],
            format=Path(native_file[name]).suffix[1:], sha256=native_sha[name], ensemble_file=plain_ensemble,
            ensemble_members=[dict(model=row['model'], file=native_file[row['model']], sha256=native_sha[row['model']],
                                   is_medoid=row['model'] == name, coordinate_scope='unchanged native original') for row in members],
            ensemble_metadata=dict(file=f'{TARGET}/science/HDBSCAN/supplement/ensembles/{group["cluster_label"]}/alignment.json'),
            selection_method=group['selection_method']))
    grid = read(supplements / 'HDBSCAN/supplement/medoid-tm.json')
    need(grid['labels'] == [row['cluster'] for row in density['representatives']], 'Density grid/medoid order differs')
    matrix_csv = f'{TARGET}/density-medoid-tm.csv'
    rows = [dict(zip(['cluster', *grid['labels']], [label, *values])) for label, values in zip(grid['labels'], grid['matrix'])]
    put(output / matrix_csv, csv_bytes(['cluster', *grid['labels']], rows))
    density['medoid_tm'] = dict(labels=grid['labels'], matrix=grid['matrix'],
                              models=[row['model'] for row in density['representatives']], csv=matrix_csv)
    density['bonsai'] = dict(file=f'{TARGET}/science/HDBSCAN/supplement/bonsai.json',
                            sha256=sha(supplements / 'HDBSCAN/supplement/bonsai.json'), selected_models=402)
    density['provenance'].update(HDBSCAN_partition_sha256=sha(supplements / 'HDBSCAN/partition.json'),
                                  HDBSCAN_fit=partition['settings'], Bonsai_scope=read(supplements / 'HDBSCAN/supplement/bonsai.json')['scope'])

    views = [dict(id='primary', name='UMAP KNN', data=f'{TARGET}/primary.json'),
             dict(id='density', name='HDBSCAN', data=f'{TARGET}/density.json')]
    fields = ['model_id', 'method', 'cluster', 'ptm', 'iptm', 'mean_plddt', 'ranking_confidence',
              'ranking_score', 'protein_ebm_energy_t010', 'model_file', 'sha256', 'hdbscan_strength']
    with (base / TARGET / 'memberships-and-scores.csv').open() as stream:
        old_rows = {row['model_id']: row for row in csv.DictReader(stream)}
    for entry in [data, density]:
        entry['views'] = views
        memberships = f'{TARGET}/{entry["view_id"]}-memberships-and-scores.csv'
        entry['membership_file'] = memberships
        rows = []
        for i, name in enumerate(names):
            row = {key: old_rows[name].get(key, '') for key in fields}
            row.update(cluster=entry['clusters'][i], protein_ebm_energy_t010=energy[i],
                       hdbscan_strength=density['density_strengths'][i] if entry is density else '')
            rows.append(row)
        put(output / memberships, csv_bytes(fields, rows))
        save(output / TARGET / (entry['view_id'] + '.json'), entry)

    scope = read(base / 'clustering-residues.json')['targets'][TARGET]['views']['whole']
    scope['note'] += ' Canonical positions1–117 map to A1–117 and118–234 map to B1–117.'
    scoped_views = {v: scope for v in ['primary', 'density']}
    save(output / 'clustering-residues.json', dict(schema_version=1, targets={TARGET: dict(
        views=scoped_views, ranges={'all': {'views': scoped_views}})}))
    bindings = [dict(**view, available=True, source_view_id=view['id'], source_data_sha256=sha(output / view['data']),
                     canonical_positions=list(range(1, 235)), asset_root='') for view in views]
    ranges = dict(residue_ranges=[dict(id='all', name='Complete homodimer · A1–117 + B1–117', available=True,
        data=f'{TARGET}/primary.json', asset_root='', default_view='density', views=bindings)])
    save(output / 'residue-ranges.json', dict(schema_version=1, targets={TARGET: ranges}))
    save(output / 'atlas.json', dict(targets=[dict(id=TARGET, label='HSPH1 construct12757', data=f'{TARGET}/primary.json')]))

    states = read(supplements / 'states/S1-states.json')
    summary = read(supplements / 'states/sampling_002/S2-summary.json')
    need(set(states['models']) == set(names) and len(states['membership']['states']) == 3, 'Wrong state cohort')
    state_index = {name: i for i, name in enumerate(states['models'])}
    payload = dict(schema_version=1, kind='tm_state_selection_payload', target=TARGET, effective_scope_id='full-dimer',
        models=names, model_order_sha256=compact_hash(names), sequence_sha256=data['provenance']['sequence_sha256'],
        model_sha256=data['model_sha256'], chain='A,B', chains=[dict(chain=c, residues=117) for c in ['A', 'B']],
        construct_residues=234, canonical_positions=list(range(1, 235)), mask_sha256=compact_hash(list(range(1, 235))),
        tm_threshold=.7, run=dict(plan_sha256='619841c5a734696ea30f571596e5f5a7c3bb734899f35360051c00c6d2463d06',
            source_commit=LIBRARY, conditioning_t=.1, alpha=.5, tau_iqr_multiplier=1, tau=summary['tau'],
            subset_law='product-weight', subset_size=50, production_chain=0, production_iteration=10000,
            burn_in=1000, chains=4, proposals_per_chain=10000, exact_controls_per_condition=20,
            noise_policy='Keep full4006 fine-group and noise masses, then condition on the supported state.'),
        ranges=dict(all=dict(effective_scope_id='full-dimer', views={v['id']: dict(source_data_sha256=v['source_data_sha256']) for v in bindings})),
        states=[], coverage=dict(assigned_models=2184, unassigned_models=1822),
        flags=dict(incomplete_coverage=True, short_core=False), discovery=states['discovery'], sensitivity=states['sensitivity'])
    for state in states['membership']['states']:
        members = [states['models'][i] for i in state['indices']]
        entry = dict(id=state['id'], representative=dict(index=lookup[state['representative']], model=state['representative']),
                     members=[dict(index=lookup[name], model=name, tm_score=states['membership']['best_tm'][state_index[name]],
                                   sha256=native_sha[name]) for name in members], selections=dict(all={}))
        for raw_view, prior in [('primary', 'Primary'), ('density', 'HDBSCAN')]:
            condition = next(c for c in summary['conditions'] if c['state'] == state['id'] and c['prior'] == prior)
            diagnostics = read(supplements / 'states/sampling_002' / condition['id'] / 'diagnostics.json')
            choice = dict(prior_procedure=prior, diagnostics=diagnostics['native'], seed_stream=condition['seed_stream'])
            for method in ['mcmc50', 'disco50']:
                panel = next(p for p in condition['panels'] if p['kind'].lower() == method)
                need(len(panel['model_ids']) == len(set(panel['model_ids'])) == 50 and set(panel['model_ids']) <= set(members), 'Invalid saved panel')
                for row in panel['members']:
                    need(row['native_sha256'] == native_sha[row['model_id']], 'Panel/native hash differs')
                src = supplements / 'states/sampling_002/exports' / (panel['ensemble_file'] + '.gz')
                raw = gzip.decompress(src.read_bytes())
                need(hashlib.sha256(raw).hexdigest() == panel['ensemble_sha256'], 'Native panel changed')
                route = f'tm-state-ensembles/{TARGET}/all/{raw_view}/{state["id"]}/{method}.pdb'
                put(output / route, raw)
                choice[method] = dict(indices=[lookup[name] for name in panel['model_ids']], models=panel['model_ids'],
                    native_sha256=[native_sha[name] for name in panel['model_ids']],
                    ensemble=dict(file=route, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
            entry['selections']['all'][raw_view] = choice
        payload['states'].append(entry)
    state_file = f'tm-states/{TARGET}/full-dimer.json'
    save(output / state_file, payload)
    catalog_entry = dict(file=state_file, sha256=sha(output / state_file), state_count=3, available=True,
                         short_core=False, incomplete_coverage=True)
    save(output / 'tm-states.json', dict(schema_version=1, kind='tm_state_selection_catalog', targets={TARGET: dict(
        model_count=4006, model_order_sha256=compact_hash(names), sequence_sha256=payload['sequence_sha256'],
        ranges=dict(all=dict(effective_scope_id='full-dimer', views={v['id']: dict(**catalog_entry,
            source_data_sha256=v['source_data_sha256']) for v in bindings})))}))
    save(output / TARGET / 'science/trace-inventory.json', trace_inventory)

    # Give each target its own dataset namespace and update the saved score table.
    for name in ['sequence.fasta', 'README.md']:
        put(output / TARGET / 'dataset' / name, (base / 'dataset' / name).read_bytes())
    with (base / 'dataset/scores.csv').open() as stream:
        reader = csv.DictReader(stream); fields = list(reader.fieldnames); rows = list(reader)
    for row in rows:
        row['protein_ebm_energy_t010'] = energies[row['model_id']]['energy_t010']
        need(row['sha256'] == native_sha[row['model_id']], 'Dataset score hash mismatch')
    put(output / TARGET / 'dataset/scores.csv', csv_bytes(fields, rows))
    readme = """# HSPH1 construct 12757 · accepted private atlas

The snapshot contains 4,006 exact native homodimers: 1,000 each AFsample2, AFcluster, SPEACH_AF and OpenDDE; five AFsample3 pilots and one BioEmu2 pilot. Both complete 117-residue chains, including the supplied tag, are retained. Organism and UniProt accession remain unverified. The supplied construct sequence appears in sequence.fasta. Original downloads retain native chain IDs; comparison-only canonical mapping is A/B.

## Geometry and clustering

All 234 Cα positions and 27,261 pair distances are included, without trimming. Saved seed-42 PCA, UMAP and t-SNE coordinates display every model. UMAP KNN has 27 clusters, with subdivisions validated by feature silhouette ≥0.15 and repeat-seed ARI ≥0.80. Geometry-only HDBSCAN uses the saved 10D UMAP seed-42 leaf result: n_neighbors=30, min_dist=0, min_cluster_size=15, min_samples=11. It has 68 clusters and 1,386 Unassigned models. Six seed/leaf/EOM fits are retained in the scientific run.

Each partition has its own exact full-cluster fixed-chain Cα medoids, full-atom comparison ensembles and complete native bidirectional US-align medoid TM grid with average-length normalization. Comparison ensembles use up to five common-native-confidence eligible members, or an explicitly unscored structural fallback. Bonsai uses each view's saved selected ensemble members plus medoids (161 UMAP KNN and 402 HDBSCAN leaves), all nonzero centered PCA axes, no whitening, kNN=10, and three saved layouts. Five explicit HDBSCAN noise examples are included.

## ProteinEBM and native confidence

ProteinEBM model 6 scores all 4,006 exact native coordinate hashes at 16 time indices. The primary score is index 10, t=0.10. The model commit is 2abfc58571e6528edf0919daf37a6c74bcf77f67. Scoring used template sidechains, mask_sequence=false, inference_sidechains=false and normalization=false. Values are learned arbitrary units, not physical binding energy. scores.csv joins the primary energy to native scalar confidence; the energy CSV provides all 16 levels. Native pTM/ipTM cover 4,005 models; native mean pLDDT covers 3,000. Missing values remain blank. Confidence and energy are distinct quantities.

## Structural states, MCMC and DISCO

Fixed-chain, full-dimer positional TM≥0.70 state memberships use the accepted medoid discovery anchors. Three supported states contain 1,280, 563 and 341 models; 1,822 remain outside them. They are representative-relative neighborhoods, not all-pairs certificates or biological populations. Sensitivities at 0.60, 0.70 and 0.80 are retained.

Each Primary/HDBSCAN fine-view prior has one MCMC50 and one DISCO50 panel for each state: 12 panels and 600 coordinate instances, with 50 distinct native models within each panel. Priors retain full-cohort group/noise masses before conditioning on a state, with alpha=0.5 and tau equal to the full-4,006 energy IQR, 78.0931396484375. Fixed-cardinality product-weight MH includes the full Hastings ratio. Each condition has four 10,000-proposal chains, 1,000 burn-in proposals and 20 exact control panels; chain 0's final panel was prespecified. DISCO uses the accepted fine-group energy/coverage control. Seeds, protocols, priors, accepted trace values and diagnostics are linked beside the atlas.

Every full-atom panel uses one native whole-complex pose; chains are not fit independently. Completion and energy-level R̂/ESS do not establish convergence. All group, noise, method and exact-control diagnostics remain available. Library frequencies are not calibrated equilibrium populations.

## Provenance and delivery

The accepted scientific supplement manifest SHA256 is a9b5c44b6a25c0d142c073e624c078c67d99f63826fcaca0f8203e4ac9d4ce13. The pinned analysis/presentation library is f3063757460303e1a4a4ba0b3629fe81776c58c4. Native hashes identify every plotted or downloaded model. Scientific JSON and native results remain preserved. Typed JSON trace downloads retain source NPZ hashes, dtypes, shapes and exact values.

This is a private review atlas. No public Zenodo record or DOI has been issued; data licensing and public release remain separate decisions. Additional queued generation models are outside this frozen cohort.
"""
    put(output / TARGET / 'dataset/README.md', readme.encode())
    links = []
    for c in summary['conditions']:
        folder = f'../science/states/sampling_002/{c["id"]}'
        diag = read(supplements / 'states/sampling_002' / c['id'] / 'diagnostics.json')['native']['panel_mean_energy']
        links.append(f'<li>{c["id"]}: R̂ {diag["rhat"]:.4f}, bulk ESS {diag["ess_bulk"]:.1f}, tail ESS {diag["ess_tail"]:.1f}. '
                     f'<a href="{folder}/diagnostics.json">All diagnostics</a> · <a href="{folder}/exact-controls.json">Exact controls</a> · '
                     + ' '.join(f'<a href="{folder}/chain-{i}.json.gz">Chain{i} trace</a>' for i in range(4)) + '</li>')
    put(output / TARGET / 'dataset/sampling.html', ('<!doctype html><meta charset="utf-8"><title>HSPH1 sampling diagnostics</title>'
        '<h1>HSPH1 construct12757 · saved sampling diagnostics</h1><p>Each panel has50 distinct native homodimers. '
        'Each condition has four10000-step chains and1000-step burn-in. These exploratory diagnostics do not establish convergence. '
        'Trace JSON preserves native dtypes, shapes and numeric values; the source NPZ SHA256 is recorded.</p><ul>' + ''.join(links) + '</ul>').encode())
    for path in (output / 'dataset').iterdir():
        path.unlink()
    (output / 'dataset').rmdir()
    context = read(output / 'target-context.json')
    context['targets'][TARGET]['project_writeup']['ensemble_interpretation'] = (
        '4006 generated homodimers, complete117-residue chains including the supplied tag. ProteinEBM covers all4006 models; '
        '68 HDBSCAN clusters plus1386 Unassigned models and27 UMAP KNN clusters. Three supported TM states cover2184 models; '
        '1822 remain uncovered. Library frequencies and exploratory selected panels are not calibrated biological populations.')
    save(output / 'target-context.json', context)

    page = (output / 'index.html').read_bytes()
    methods = ('Each target links its exact construct, cohort, methods and accepted scientific evidence. Select a target, residue range and clustering view. Each view uses its own saved medoids, native comparison ensembles, TM matrix and Bonsai. ProteinEBM energies remain distinct from native confidence. Saved MCMC50 and DISCO50 panels use the recorded state membership, prior, seeds and diagnostics; completion does not establish convergence. See Target methods and Saved sampling protocol for target-specific settings.')
    page = render_project_html(page, dict(title='LS AIS · structure atlas', methods=methods), 'LS_AIS').decode()
    start = page.index('<p class="hint">4,006 native models')
    end = page.index('<nav id="targets"', start)
    page = page[:start] + '<p class="hint">Private LS AIS atlas · choose a target below.</p><p id="lsDownloads" class="hint"></p>' + page[end:]
    page = page.replace('</head>', '<script defer src="ls_atlas.js"></script></head>')
    page = page.replace('All 117 residues of both chains were retained; no terminal regions were excluded.', 'The selected target documents its exact retained residue scope.')
    put(output / 'index.html', page.encode())
    app = (output / 'app.js').read_text()
    app = app.replace("a.textContent=t.id.replace(/_bmr\\d+$/i,'')", "a.textContent=t.label||t.id.replace(/_bmr\\d+$/i,'')")
    app = "function isUnassignedCluster(label){return label==='Unassigned'||label.endsWith('.unassigned')}\n" + app.replace("label.endsWith('.unassigned')", "isUnassignedCluster(label)").replace("x.endsWith('.unassigned')", "isUnassignedCluster(x)")
    app = app.replace('Member PDBs (${members.length} selected)', 'Member structures (${members.length} selected)')
    put(output / 'app.js', app.encode())
    put(output / 'ls_atlas.js', (ROOT / 'site/ls_atlas.js').read_bytes())
    js = (output / 'tm_states.js').read_text()
    before = "p.chain==='A'&&Number.isInteger(p.construct_residues)"
    after = "(p.chain==='A'||(p.chain==='A,B'&&p.construct_residues===234&&JSON.stringify(p.chains)===JSON.stringify([{chain:'A',residues:117},{chain:'B',residues:117}])&&Array.isArray(p.model_sha256)&&p.model_sha256.length===data.model_sha256.length&&p.model_sha256.every((v,i)=>v===data.model_sha256[i])))&&Number.isInteger(p.construct_residues)"
    need(js.count(before) == 1, 'Pinned homodimer compatibility boundary changed')
    js = js.replace(before, after).replace('PSE sessions preserve the saved native display.', 'The saved PDB downloads preserve the native full-dimer pose.')
    put(output / 'tm_states.js', js.encode())
    print('Saved target assets assembled; hashing manifest', flush=True)
    files = [dict(path=p.relative_to(output).as_posix(), bytes=p.stat().st_size, sha256=sha(p))
             for p in sorted(output.rglob('*')) if p.is_file()]
    need(sum(r['bytes'] for r in files) < 2 * 2**30, 'Private output budget exceeded')
    # The subsequent shared exporter performs the complete blocking privacy scan.
    checked_views = validate_views(output, {r['path'] for r in files})
    for name, row in checked_views.items():
        row['unassigned'] = sum(v == 'Unassigned' or v.endswith('.unassigned') for v in read(output / name)['clusters'])
    save(output.parent / 'delivery-manifest.json', dict(schema_version=1, project='LS_AIS', renderer='saved', files=files))
    save(output.parent / 'assembly-receipt.json', dict(status='saved_assembly_awaiting_export_privacy',
        scientific_execution=False, source_review_manifest_sha256=BASE_SHA, scientific_delivery_sha256=DELIVERY_SHA,
        models=4006, energies=4006, views=checked_views, states=3, panels=12, private_only=True,
        library_commit=LIBRARY, files=len(files), bytes=sum(r['bytes'] for r in files)))
    print(json.dumps(read(output.parent / 'assembly-receipt.json')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--supplements', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.base.resolve(), args.supplements.resolve(), args.output.resolve())
