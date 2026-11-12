"""Repackage accepted DOC1/CDK2 results in the established LS_AIS private viewer.

This is presentation wiring only: it never fits, scores, clusters, or selects.
Native representative coordinates are supplied separately and hash-checked.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'local/previews/2026-11-11_doc1-cdk2_core_figures_001/site'
SELECTIONS = ROOT / 'local/plans/2026-11-11_doc1-cdk2-energy-representatives_001/results'
ROSTERS = ROOT / 'local/previews/2026-11-11_doc1-cdk2_partial_001/inputs'
SELECTION_PLAN_SHA256 = '539144399567a5bf0ee0411375e3b8259fc0fe3c9aaa0598132f3da4f7246369'
BONSAI_PLAN_SHA256 = '8af294897bf37685e8410ffc8cd43a5a2f461b9775526ff5152e5185c3742d47'
TARGETS = ('DOC1Rdimer_CDK2', 'DOC1dimer_CDK2')
PARTITIONS = {'leaf': ('density', 'HDBSCAN leaf'),
              'eom': ('eom', 'HDBSCAN EOM'),
              'knn': ('primary', 'UMAP KNN')}
PALETTE = ('#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
           '#8c564b', '#e377c2', '#17becf', '#bcbd22', '#4c78a8')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    # The HSPH1 source is hard-linked; replace edited catalog files atomically.
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, separators=(',', ':')) + '\n')
    temporary.replace(path)


def labels(values):
    return ['Unassigned' if int(value) == -1 else f'Cluster {int(value)}'
            for value in values]


def roster_for(target):
    rows = [json.loads(line) for line in
            (ROSTERS / target / 'roster.jsonl').open()]
    return {row['model_id']: row for row in rows}


def build(output, base_site):
    if output.exists():
        raise ValueError('Use a fresh private output directory')
    accepted = json.loads((SELECTIONS / 'acceptance.json').read_text())
    if (accepted['status'], accepted['plan_sha256'], accepted['views'],
        accepted['representatives']) != ('validated', SELECTION_PLAN_SHA256, 12, 3173):
        raise ValueError('Energy-representative acceptance differs')
    for filename, expected in accepted['files'].items():
        if digest(SELECTIONS / filename) != expected:
            raise ValueError('Accepted representative output changed: ' + filename)
    shutil.copytree(base_site, output, copy_function=shutil.copy2)
    # Existing archived diagnostics are opt-in, even for inherited HSPH1 data.
    for name in ('primary', 'density'):
        path = output / 'HSPH1_12757_homodimer' / f'{name}.json'
        data = json.loads(path.read_text())
        data['heatmaps'] = [row for row in data['heatmaps']
                            if row['name'] not in
                            ('box summary 3d', 'pair distribution detail')]
        write_json(path, data)

    atlas = json.loads((output / 'atlas.json').read_text())
    ranges_catalog = json.loads((output / 'residue-ranges.json').read_text())
    residues_catalog = json.loads((output / 'clustering-residues.json').read_text())
    context_catalog = json.loads((output / 'target-context.json').read_text())
    required_native = {}
    coverage = {}
    for target in TARGETS:
        full = json.loads((SOURCE / 'data' / f'{target}.json').read_text())
        models, methods, scores = full['model_id'], full['method'], full['energy']['values']
        n = len(models)
        if n != full['models'] or len(methods) != n or len(scores) != n or any(
                not isinstance(value, (int, float)) for value in scores):
            raise ValueError(f'Incomplete accepted ProteinEBM coverage: {target}')
        roster = roster_for(target)
        model_index = {model: i for i, model in enumerate(models)}
        if len(roster) != n or any(roster[model]['method'] != method
                                   for model, method in zip(models, methods)):
            raise ValueError(f'Native roster order/identity mismatch: {target}')
        coverage[target] = n
        full_lengths = full['maps']['chain_lengths']
        if len(full_lengths) != 3:
            raise ValueError('Expected verified A/B/C chains')
        target_ranges = []
        target_views = {}
        for scope in ('full', 'core'):
            geo = full if scope == 'full' else json.loads(
                (SOURCE / 'data' / f'{target}-core.json').read_text())
            if any(len(geo[key]) != n for key in ('x', 'y', 'knn', 'leaf', 'eom')):
                raise ValueError(f'Projection/label count mismatch: {target} {scope}')
            chain_lengths = geo['maps']['chain_lengths']
            if scope == 'full':
                positions = list(range(1, sum(full_lengths) + 1))
                mask = f'A1–{full_lengths[0]} + B1–{full_lengths[1]} + C1–{full_lengths[2]}'
            else:
                start = 65 if target.startswith('DOC1R') else 60
                positions = (list(range(start, full_lengths[0] + 1)) +
                             list(range(full_lengths[0] + start,
                                        full_lengths[0] + full_lengths[1] + 1)) +
                             list(range(sum(full_lengths[:2]) + 1, sum(full_lengths) + 1)))
                mask = geo['range_label']
            if len(positions) != sum(chain_lengths):
                raise ValueError(f'Core residue mask mismatch: {target}')
            view_bindings = []
            for partition, (view_id, view_name) in PARTITIONS.items():
                selected = json.loads((SELECTIONS / f'{target}-{scope}-{partition}.json').read_text())
                if (selected['status'], selected['target'], selected['range'],
                    selected['partition'], selected['models']) != (
                        'validated', target, scope, partition, n):
                    raise ValueError(f'Selection receipt mismatch: {target} {scope} {partition}')
                cluster_labels = labels(geo[partition])
                counts = Counter(cluster_labels)
                selected_labels = {f"Cluster {group['cluster']}" for group in selected['clusters']}
                if (set(counts) - {'Unassigned'}) != selected_labels:
                    raise ValueError(f'Representative coverage mismatch: {target} {scope} {partition}')
                colors = {label: PALETTE[int(label.split()[-1]) % len(PALETTE)]
                          for label in sorted(selected_labels)}
                colors['Unassigned'] = '#98a3aa'
                representatives = []
                for group in selected['clusters']:
                    rep, label = group['representative'], f"Cluster {group['cluster']}"
                    model = rep['model_id']
                    if (counts[label] != group['size'] or model not in roster or
                        roster[model]['native_sha256'] != rep['native_sha256'] or
                        scores[model_index[model]] != rep['protein_ebm_full_complex_energy_t010'] or
                        cluster_labels[model_index[model]] != label):
                        raise ValueError(f'Representative identity/score mismatch: {target} {label}')
                    native = roster[model]
                    relative_native = f"{target}/pdb/{native['name']}"
                    required_native[relative_native] = rep['native_sha256']
                    representatives.append({
                        'cluster': label, 'count': group['size'], 'model': model,
                        'method': rep['method'], 'color': colors[label],
                        'file': f'{target}/models/{native["name"]}',
                        'format': 'pdb', 'sha256': rep['native_sha256'],
                        'energy': rep['protein_ebm_full_complex_energy_t010']})
                membership = f'downloads/{target}{"-core" if scope == "core" else ""}-geometry-memberships.csv'
                schemes = [
                    {'key': 'clusters', 'name': 'Clusters', 'type': 'categorical',
                     'values': cluster_labels, 'colors': colors},
                    {'key': 'methods', 'name': 'Generation method', 'type': 'categorical',
                     'values': methods, 'colors': {m: PALETTE[i % len(PALETTE)]
                                                  for i, m in enumerate(sorted(set(methods)))}},
                    {'key': 'protein_ebm_energy_t10',
                     'name': 'ProteinEBM Model 6 t=0.10 · full A/B/C',
                     'short_name': 'ProteinEBM t=0.10', 'type': 'continuous',
                     'values': scores, 'range': [min(scores), max(scores)],
                     'colorscale': 'Viridis'},
                ]
                heatmaps = [
                    {'name': f'Cα median distance (Å) · {geo["maps"]["median_models"]:,} sampled models',
                     'file': geo['maps']['median']},
                    {'name': f'Cα distance variance (Å²) · {geo["maps"]["variance_models"]:,} models',
                     'file': geo['maps']['variance']},
                ]
                projections = {
                    'umap': {'xy': list(map(list, zip(geo['x'], geo['y']))),
                             'axes': ['UMAP 1', 'UMAP 2']},
                    'pca': {'xy': list(map(list, zip(geo['pca']['x'], geo['pca']['y']))),
                            'axes': ['PC1', 'PC2'],
                            'explained_variance_ratio': geo['pca']['explained_variance_ratio'],
                            'scope_label': mask},
                    'tsne': {'xy': list(map(list, zip(geo['tsne']['x'], geo['tsne']['y']))),
                             'axes': ['t-SNE 1', 't-SNE 2']},
                }
                name = f'{scope}-{view_id}.json'
                view_bindings.append({'id': view_id, 'name': view_name,
                                      'data': f'{target}/{name}'})
                payload = {
                    'target': target, 'target_label': target, 'view_id': view_id,
                    'view_title': f'{target} · {view_name} · {mask}',
                    'models': models, 'residues': len(positions), 'methods': methods,
                    'clusters': cluster_labels, 'projections': projections,
                    'schemes': schemes, 'representatives': representatives,
                    'membership_file': membership, 'heatmaps': heatmaps,
                    'structure_confidence': 'Native model confidence is separate from ProteinEBM energy.',
                    'representative_kind': 'ProteinEBM energy-selected representative',
                    'representative_policy': selected['selection_policy'] +
                        '. These are not structural medoids. All accepted models are scored; '
                        'core views reuse full A/B/C complex energy.',
                    'mask_note': f'Clustering geometry: {mask}. ProteinEBM energy uses full A/B/C.',
                    'clustering_method_note': f'{view_name} on accepted {scope} geometry; '
                                              f'{n:,}/{n:,} models have accepted ProteinEBM values.',
                    'provenance': {'clustering_receipt_sha256': geo['receipt_sha256'],
                                   'energy_receipt_sha256': full['energy']['receipt_sha256'],
                                   'representative_plan_sha256': selected['plan_sha256'],
                                   'representative_kind': 'energy-selected, not RMSD medoid',
                                   'scored_models': n, 'total_models': n},
                    'native_data_links': {'energies': full['energy']['download'],
                                          'memberships': membership},
                }
                write_json(output / target / name, payload)
                range_id = 'all' if scope == 'full' else 'core'
                target_views.setdefault(range_id, {'views': {}})['views'][view_id] = {
                    'chain': 'A,B,C',
                    'chains': [{'chain': chain, 'expected_ca_count': length}
                               for chain, length in zip('ABC', full_lengths)],
                    'expected_ca_count': sum(full_lengths),
                    'canonical_positions': positions,
                    'analysis_uses_full_construct': scope == 'full',
                    'reference_ranges': mask,
                    'note': f'Native A/B/C PDB retained. Clustering used {mask}.'}
            for binding in view_bindings:
                path = output / binding['data']
                data = json.loads(path.read_text())
                data['views'] = view_bindings
                write_json(path, data)
            range_id = 'all' if scope == 'full' else 'core'
            target_ranges.append({'id': range_id, 'name': mask, 'available': True,
                                  'data': f'{target}/{scope}-density.json',
                                  'default_view': 'density'})
        atlas['targets'].append({'id': target, 'label': target,
                                 'data': f'{target}/full-density.json',
                                 'residue_ranges': target_ranges})
        ranges_catalog['targets'][target] = {'residue_ranges': target_ranges}
        residues_catalog['targets'][target] = {'ranges': target_views}
        context_catalog['targets'][target] = {
            'title': target,
            'record_summary': f'{n:,} accepted A/B/C models; ProteinEBM Model 6 t=0.10 '
                              'covers every model. Assigned cluster representatives '
                              'are lowest-energy members, not structural medoids.'}
    for name, data in [('atlas.json', atlas), ('residue-ranges.json', ranges_catalog),
                       ('clustering-residues.json', residues_catalog),
                       ('target-context.json', context_catalog)]:
        write_json(output / name, data)
    for folder in ('figures', 'downloads'):
        shutil.copytree(SOURCE / folder, output / folder, dirs_exist_ok=True,
                        copy_function=os.link)
    # The established layout is preserved. Large cohorts use the same projection
    # semantics with Plotly WebGL so every accepted model remains visible.
    app = output / 'app.js'
    code = app.read_text()
    original = "out.push({type:'scatter',mode:'markers',name:label==='valid'?s.name:label"
    replacement = "out.push({type:data.models.length>10000?'scattergl':'scatter',mode:'markers',name:label==='valid'?s.name:label"
    if code.count(original) != 1:
        raise ValueError('Pinned atlas projection renderer changed')
    code = code.replace(original, replacement)
    anchor = " for(const [label,indices] of groups){const numeric=s.type==='continuous'&&label==='valid'"
    bulk = """ if(s.type==='categorical'&&groups.size>50){
  const indices=data.models.map((_,i)=>i),selected=effectiveSelectionHighlight();
  return [{type:'scattergl',mode:'markers',name:'All categories',
   x:xy.map(p=>p[0]),y:xy.map(p=>p[1]),customdata:indices,
   text:indices.map(i=>`${escapeText(data.models[i])}<br>${escapeText(data.clusters[i])}<br>${escapeText(data.methods[i])}`),
   hovertemplate:'%{text}<extra></extra>',
   marker:{size:4.5,color:indices.map(i=>s.colors[String(s.values[i]??'Unspecified')]||'#808080'),
    opacity:indices.map(i=>visibleCluster(data.clusters[i])?(selected.active?(selected.indices.has(i)?.85:.09):.7):.06)},
   meta:{legendKey:'All categories',bulk:true,numeric:false},showlegend:false}];
 }
"""
    if code.count(anchor) != 1:
        raise ValueError('Pinned atlas categorical renderer changed')
    code = code.replace(anchor, bulk + anchor)
    legend_anchor = "const marker={...trace.marker,size:8,opacity:1};"
    if code.count(legend_anchor) != 1:
        raise ValueError('Pinned atlas legend renderer changed')
    code = code.replace(legend_anchor,
                        "const marker={...trace.marker,size:8,opacity:1,color:trace.meta.bulk?'#657885':trace.marker.color};")
    legend_start = " const legend=$('projectionLegend');const legendCount=projectionLegendTraces().length;"
    legend_end = " updateTMStateControls();updateSelectionControls();showProjection();"
    if code.count(legend_start) != 1 or code.count(legend_end) != 1:
        raise ValueError('Pinned atlas shared-legend renderer changed')
    start = code.index(legend_start)
    end = code.index(legend_end, start)
    original_legend = code[start:end]
    large_legend = """ const legend=$('projectionLegend');
 if(data.models.length>10000){
  const s=scheme(),panel=$('legendPanel');panel.open=true;
  $('legendSummary').textContent='Shared color legend · '+(s.short_name||s.name);
  legend.replaceChildren();
  if(s.type==='continuous'){
   const finite=s.values.filter(Number.isFinite),range=s.range||[Math.min(...finite),Math.max(...finite)];
   const note=document.createElement('p');note.textContent=finite.length.toLocaleString()+'/'+data.models.length.toLocaleString()+' models scored · '+s.name;
   const bar=document.createElement('div');bar.setAttribute('role','img');bar.setAttribute('aria-label','Continuous ProteinEBM energy scale from '+range[0].toFixed(1)+' to '+range[1].toFixed(1));bar.style.cssText='height:14px;max-width:560px;border-radius:3px;background:linear-gradient(90deg,#440154,#414487,#2a788e,#22a884,#7ad151,#fde725)';
   const ticks=document.createElement('div');ticks.style.cssText='display:flex;justify-content:space-between;width:560px;max-width:100%;font-size:11px';const low=document.createElement('span'),high=document.createElement('span');low.textContent=range[0].toFixed(1);high.textContent=range[1].toFixed(1);ticks.append(low,high);
   legend.append(note,bar,ticks);
  }else{
   const note=document.createElement('p');note.textContent='Colors show '+s.name.toLowerCase()+'. Select a cluster or use Filter clusters to inspect individual categories.';legend.append(note);
  }
 }else{
""" + original_legend + "\n }\n"
    code = code[:start] + large_legend + code[end:]
    numeric_anchor = "for(const [label,indices] of groups){const numeric=s.type==='continuous'&&label==='valid',marker={size:4.5,opacity:indices.map(i=>visibleCluster(data.clusters[i])?(effectiveSelectionHighlight().active?(effectiveSelectionHighlight().indices.has(i) ? .85 : .09):.7):.06)};"
    numeric_fast = "for(const [label,indices] of groups){const numeric=s.type==='continuous'&&label==='valid',plain=!familyPrefix&&!chosenClusters&&!effectiveSelectionHighlight().active,marker={size:4.5,opacity:plain?.7:indices.map(i=>visibleCluster(data.clusters[i])?(effectiveSelectionHighlight().active?(effectiveSelectionHighlight().indices.has(i) ? .85 : .09):.7):.06)};"
    if code.count(numeric_anchor) != 1:
        raise ValueError('Pinned atlas point-opacity renderer changed')
    code = code.replace(numeric_anchor, numeric_fast)
    # Update the small shared legend promptly; large numeric WebGL plots continue
    # rendering without delaying the score-range disclosure.
    projection_start = " await Promise.all(['pca','umap','tsne'].map(async method=>"
    p_start = code.index(projection_start)
    p_end = code.index('\n', p_start)
    projection_draw = code[p_start:p_end]
    code = code[:p_start] + code[p_end+1:]
    if code.count(legend_end) != 1:
        raise ValueError('Pinned atlas projection completion hook changed')
    code = code.replace(legend_end, projection_draw + '\n' + legend_end)
    app.write_text(code)
    html = output / 'index.html'
    content = html.read_text().replace('Each view uses its own saved medoids, native comparison ensembles, TM matrix and Bonsai.',
        'Each view displays its own accepted analyses and saved representatives; unavailable supplements are identified in the view.')
    html.write_text(content)
    required = [{'path': key, 'sha256': value} for key, value in sorted(required_native.items())]
    write_json(output.parent / 'required-representatives.json',
               {'models': len(required), 'files': required, 'energy_coverage': coverage})
    print(json.dumps({'status': 'assembled', 'targets': coverage,
                      'unique_representative_pdbs': len(required),
                      'output': str(output)}))


def finalize(output, archive):
    required = json.loads((output.parent / 'required-representatives.json').read_text())
    expected = {row['path']: row['sha256'] for row in required['files']}
    seen = set()
    with tarfile.open(archive, 'r:gz') as bundle:
        for member in bundle:
            if not member.isfile() or member.name not in expected or member.name in seen:
                raise ValueError(f'Unexpected native member: {member.name}')
            seen.add(member.name)
            target, pdb_dir, name = member.name.split('/')
            if pdb_dir != 'pdb' or member.size > 20 * 1024 * 1024:
                raise ValueError(f'Unexpected native path/size: {member.name}')
            destination = output / target / 'models' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            h = hashlib.sha256()
            with bundle.extractfile(member) as source, destination.open('wb') as sink:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    h.update(block)
                    sink.write(block)
            if h.hexdigest() != expected[member.name]:
                raise ValueError(f'Native SHA-256 mismatch: {member.name}')
    if seen != set(expected):
        raise ValueError(f'Missing {len(set(expected) - seen)} native PDBs')
    manifest_only(output)


def attach_bonsai(output, base_site, bonsai_dir):
    """Attach twelve accepted native Bonsai exports to a fresh private bundle."""
    if output.exists():
        raise ValueError('Use a fresh private output directory')
    source_manifest = json.loads((base_site / 'export-manifest.json').read_text())
    if source_manifest.get('kind') != 'private-standard-doc1-cdk2-preview':
        raise ValueError('Bonsai attachment requires a verified standard preview')
    shutil.copytree(base_site, output, copy_function=os.link)
    shutil.copy2(base_site.parent / 'required-representatives.json',
                 output.parent / 'required-representatives.json')
    coverage = {}
    for target in TARGETS:
        for scope in ('full', 'core'):
            for partition, (view_id, _) in PARTITIONS.items():
                identity = f'{target}-{scope}-{partition}'
                selection = json.loads((SELECTIONS / f'{identity}.json').read_text())
                source = bonsai_dir / identity / 'bonsai.json'
                bonsai = json.loads(source.read_text())
                receipt_sha = digest(bonsai_dir / identity / 'acceptance.json')
                receipt = json.loads((bonsai_dir / identity / 'acceptance.json').read_text())
                if (bonsai['provenance']['acceptance_sha256'] != receipt_sha or
                    receipt['status'] != 'validated' or
                    receipt['plan_sha256'] != BONSAI_PLAN_SHA256 or
                    bonsai['provenance']['plan_sha256'] != BONSAI_PLAN_SHA256 or
                    (receipt['view'], receipt['target'], receipt['range'],
                     receipt['partition']) != (identity, target, scope, partition) or
                    receipt['selection_sha256'] != digest(SELECTIONS / f'{identity}.json') or
                    bonsai['provenance']['selection_sha256'] != receipt['selection_sha256'] or
                    bonsai['provenance']['sketch_sha256'] != receipt['sketch_sha256'] or
                    len(bonsai['layouts']) != 3 or
                    len(bonsai['models']) != len(receipt['selected_models'])):
                    raise ValueError('Bonsai receipt or layout differs: ' + identity)
                representatives = {group['representative']['model_id']
                                   for group in selection['clusters']}
                leaf_models = {row['model'] for row in bonsai['models']}
                role_models = {row['model'] for row in bonsai['models']
                               if row['selection_role'] == 'energy_selected_representative'}
                if (role_models != representatives or len(role_models) != len(representatives)
                    or len(leaf_models) != len(bonsai['models']) or
                    leaf_models != {row['model_id'] for row in receipt['selected_models']}):
                    raise ValueError('Bonsai leaves differ from energy representatives: ' + identity)
                relative = f'{target}/{scope}-{view_id}-bonsai.json'
                shutil.copy2(source, output / relative)
                view_path = output / target / f'{scope}-{view_id}.json'
                view = json.loads(view_path.read_text())
                view['bonsai'] = {'file': relative, 'sha256': digest(output / relative),
                                  'selected_models': len(leaf_models),
                                  'selection_scope': bonsai['scope']}
                write_json(view_path, view)
                coverage[identity] = {'representatives': len(representatives),
                                      'selected_models': len(leaf_models)}
    manifest_only(output)
    write_json(output.parent / 'bonsai-coverage.json', coverage)
    print(json.dumps({'status': 'bonsai_attached', 'views': len(coverage),
                      'selected_models': sum(v['selected_models'] for v in coverage.values()),
                      'output': str(output)}))


def manifest_only(output):
    required = json.loads((output.parent / 'required-representatives.json').read_text())
    for row in required['files']:
        target, pdb_dir, name = row['path'].split('/')
        path = output / target / 'models' / name
        if not path.is_file() or digest(path) != row['sha256']:
            raise ValueError('Representative PDB missing or changed: ' + row['path'])
    # The verified source manifest is local only; the private handler allowlists
    # every served file and rechecks bytes if a file changes.
    entries = []
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.name != 'export-manifest.json':
            entries.append({'path': path.relative_to(output).as_posix(),
                            'bytes': path.stat().st_size, 'sha256': digest(path)})
    manifest = {'kind': 'private-standard-doc1-cdk2-preview',
                'scientific_execution': False, 'files': entries}
    write_json(output / 'export-manifest.json', manifest)
    write_json(output.parent / 'delivery-manifest.json', manifest)
    print(json.dumps({'status': 'verified', 'files': len(entries),
                      'representative_pdbs': len(required['files']),
                      'energy_coverage': required['energy_coverage'],
                      'manifest_sha256': digest(output / 'export-manifest.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--base-site', type=Path,
                        help='Reviewed HSPH1 atlas site (required for assembly)')
    parser.add_argument('--finalize-with', type=Path)
    parser.add_argument('--manifest-only', action='store_true')
    parser.add_argument('--attach-bonsai-from', type=Path)
    args = parser.parse_args()
    if args.attach_bonsai_from:
        if not args.base_site:
            parser.error('--base-site is required to attach Bonsai')
        attach_bonsai(args.output.resolve(), args.base_site.resolve(),
                      args.attach_bonsai_from.resolve())
    elif args.manifest_only:
        manifest_only(args.output.resolve())
    elif args.finalize_with:
        finalize(args.output.resolve(), args.finalize_with.resolve())
    else:
        if not args.base_site:
            parser.error('--base-site is required for assembly')
        build(args.output.resolve(), args.base_site.resolve())
