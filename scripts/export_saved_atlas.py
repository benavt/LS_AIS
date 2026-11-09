"""Serialize accepted saved results into the shared atlas and compact dataset; no fitting."""
import argparse,csv,hashlib,json,math,os,re,shutil,sys
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-root',type=Path,required=True);parser.add_argument('--vendor-dir',type=Path,required=True);args=parser.parse_args()
ROOT=args.run_root.resolve();SOURCE=ROOT/'source/Structure_Clustering';sys.path[:0]=[str(SOURCE),str(SOURCE/'scripts')]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,v):
 Path(p).parent.mkdir(parents=True,exist_ok=True)
 with Path(p).open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
plan=read(ROOT/'00_input/execution-plan.json');assert sha(ROOT/'00_input/execution-plan.json')=='4c643f8a64d9b56f7906b285221712542f3f445659914764b370a10f6ab9389a'
for n,h in read(ROOT/'receipts/source-extraction.json')['files_sha256'].items():assert sha(SOURCE/n)==h
done=read(ROOT/'receipts/analysis-completion.json');assert sha(done['manifest'])==done['manifest_sha256'];workflow=read(done['manifest']);supp=ROOT/'supplement';accepted=read(supp/'acceptance.json');assert accepted['status']=='verified'
for n,h in accepted['files_sha256'].items():assert sha(supp/n)==h
import numpy as np
from src.analysis.atlas_presentation import ASSETS,validate_views
from structure_clustering.publication import render_project_html,inspect_artifact
from src.analysis.confidence_ranking import confidence_value
from zenodo_model_deposition import prepare as prepare_dataset,verify as verify_dataset
native={r['model_id']:r for r in read(ROOT/'00_input/atlas-inventory.json')['models']};scores={r['model_id']:r['scores']for r in read(ROOT/'00_input/atlas-scores.json')['models']}
projections={};names=None
for method in ['pca','umap','tsne']:
 with np.load(workflow['clustering'][method]['embeddings'],allow_pickle=False)as a:
  current=a['filenames'].astype(str).tolist();xy=a['embeddings'];assert len(current)==4006 and set(current)==set(native)and xy.shape==(4006,2)and np.isfinite(xy).all()
  assert names is None or names==current;names=current
  projections[method]=dict(xy=xy.tolist(),axes=[method.upper()+' 1',method.upper()+' 2'])
  if method=='pca':
   ratios=workflow['clustering'][method].get('explained_variance_ratio')
   if ratios:projections[method].update(explained_variance_ratio=ratios,axes=[f'PC{i+1} ({100*v:.1f}% variance)'for i,v in enumerate(ratios[:2])])
with Path(workflow['knn_clustering']['labels_csv']).open()as f:labels={r['model']:r for r in csv.DictReader(f)}
assert set(labels)==set(names);groups=read(supp/'selection.json')['clusters'];grid=read(supp/'medoid-tm.json');assert [g['cluster_label']for g in groups]==grid['labels']
delivery=ROOT/'delivery';delivery.mkdir(exist_ok=False);target='HSPH1_12757_homodimer';folder=delivery/target;(folder/'models').mkdir(parents=True);(delivery/'assets').mkdir()
for dest,template in ASSETS.items():
 p=delivery/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(SOURCE/'src/app/templates'/template,p)
vendor=args.vendor_dir.resolve()
for n in ['3Dmol-min.js','plotly.min.js','3Dmol-min.js.LICENSE.txt']:
 if (vendor/n).exists():shutil.copyfile(vendor/n,delivery/'assets'/n)
shutil.copyfile(ROOT/'execution/ca_fallback.js',delivery/'assets/ca_fallback.js')
methods_text=('All 4,006 available native homodimers are fit jointly: AFsample2,AFcluster,SPEACH_AF and OpenDDE (1,000 each),five AFsample3 pilots and one BioEmu2 pilot. Both complete 117-residue chains and all 27,261 Cα-pair distances are included; no trimming. Native AF2-family B/C chains map consistently to canonical A/B for comparison only. PCA,UMAP and t-SNE use seed 42 and the saved shared workflow. UMAP components are preserved; subdivisions require feature silhouette ≥0.15 and repeat-seed ARI ≥0.80. Medoids use all cluster members with fixed-chain rigid CA fits; comparison ensembles contain up to 5 native-confidence-eligible members ranked by 0.8*ipTM+0.2*pTM,with an explicitly unscored structural fallback. Bonsai uses selected ensemble members plus medoids,all nonzero centered PCA axes,no whitening,kNN=10 and seed 42. The TM grid uses non-fast,bidirectional,average-length-normalized US-align with fixed A/B chain mapping. ProteinEBM scores are unavailable in this snapshot and remain blank; native confidence is not an energy or equilibrium probability. Organism and accession remain unverified; the exact construct sequence is documented in the dataset README.')
page=render_project_html((delivery/'index.html').read_bytes(),dict(title='HSPH1 construct 12757 · structure atlas',methods=methods_text),'hsph1-structure-atlas').decode()
page=page.replace('<script defer src="assets/3Dmol-min.js"></script>','<script defer src="assets/3Dmol-min.js"></script><script defer src="assets/ca_fallback.js"></script>')
page=page.replace('Distance variance highlights flexible residue pairs; marked terminal regions were excluded from clustering.','Distance variance summarizes variation across the sampled library. All 117 residues of both chains were retained; no terminal regions were excluded.')
page=page.replace('<nav id="targets"','<p class="hint">4,006 native models · full homodimer · ProteinEBM energies unavailable. <a href="dataset/README.md">Dataset methods</a> · <a href="dataset/scores.csv" download>Native scalar scores</a></p><nav id="targets"')
(delivery/'index.html').write_text(page)
js=(delivery/'app.js').read_text()
helper="""function canonicalizeAtlasModel(model,mapping){
 if(!mapping)return model;const atoms=model.selectedAtoms({}),chains=[...new Set(atoms.map(a=>a.chain))];
 if(chains.length!==Object.keys(mapping).length||chains.some(c=>!Object.hasOwn(mapping,c)))throw Error('Native chains differ from the verified model mapping.');
 for(const atom of atoms){atom.native_chain=atom.chain;atom.chain=mapping[atom.chain]}return model;
}
"""
js=helper+js
assert js.count('$3Dmol.createViewer(')==3;js=js.replace('$3Dmol.createViewer(','AtlasStructureRenderer.createViewer(')
before="viewer._aisModels=ensemble?viewer.addModels(cluster.ensemble_text,'pdb'):[viewer.addModel(coordinate,cluster.format)];viewer._aisDescriptor=cluster;viewer._aisEnsemble=!!ensemble;"
after=before+"if(!ensemble)viewer._aisModels.forEach(model=>canonicalizeAtlasModel(model,current.model_chain_maps?.[cluster.model]));"
assert js.count(before)==1;js=js.replace(before,after)
needle="v._aisModels=[v.addModel(text,c.format)];";assert js.count(needle)==1;js=js.replace(needle,"v._aisModels=[canonicalizeAtlasModel(v.addModel(text,c.format),data.model_chain_maps?.[c.model])];")
needle="ghost=pairViewers[0].addModel(descriptor.coordinate_text,descriptor.format)";assert js.count(needle)==1;js=js.replace(needle,"ghost=canonicalizeAtlasModel(pairViewers[0].addModel(descriptor.coordinate_text,descriptor.format),data.model_chain_maps?.[descriptor.model])")
js=js.replace("$('title').textContent=data.target;","$('title').textContent=data.target_label||data.target;")
js=js.replace("type:'scattergl'","type:'scatter'")  # Display-only SVG projections; identical saved coordinates and memberships.
js=js.replace('Plotly.relayout(','AtlasResponsive.relayout(').replace("$('structure').href=modelDownloadURL;","$('structure').href=cluster.file;").replace("$('ensemblePdb').href=ensembleDownloadURL;","$('ensemblePdb').href=cluster.ensemble_file;")
(delivery/'app.js').write_text(js)
responsive=(delivery/'responsive.js').read_text()
wrapper=""" function relayout(node,update){
  if(typeof node==='string')node=document.getElementById(node);
  const previous=queues.get(node)||Promise.resolve();
  const task=previous.catch(()=>{}).then(()=>root.Plotly.relayout(node,update));
  queues.set(node,task);return task;
 }
"""
responsive=responsive.replace('return root.Plotly.relayout(node,update)}','return relayout(node,update)}').replace(' async function react(node,traces,layout,config){',wrapper+' async function react(node,traces,layout,config){').replace('root.AtlasResponsive={react,resizeAll','root.AtlasResponsive={react,relayout,resizeAll')
(delivery/'responsive.js').write_text(responsive)
method_config=read(ROOT/'00_input/model-types.json');method_info={r['key'].removeprefix('hsph1_'):r for r in method_config['rules']};method_names=[method_info[native[n]['method']]['name']for n in names];palette={r['name']:r['color']for r in method_info.values()}
colors={labels[n]['cluster_label']:labels[n]['color']for n in names};cluster_values=[labels[n]['cluster_label']for n in names]
schemes=[dict(key='clusters',name='Clusters',type='categorical',values=cluster_values,colors=colors),dict(key='methods',name='Sampling method',type='categorical',values=method_names,colors=palette)]
for key,title in [('iptm','Native ipTM'),('ptm','Native pTM'),('mean_plddt','Native mean pLDDT · 0–100'),('ranking_score','Native AF3/OpenDDE ranking score')]:
 values=[scores[n].get(key)for n in names];finite=[v for v in values if v is not None];schemes.append(dict(key=key,name=title,type='continuous',values=values,colorscale='Viridis',range=[min(finite),max(finite)],unavailable=False))
schemes.append(dict(key='protein_ebm_energy_t10',name='ProteinEBM energy · t=0.10',type='continuous',values=[None]*4006,colorscale='Viridis',range=[0,1],unavailable=True,time_index=10,time_value=.1,model_version=6,units='arbitrary',lower_is_better=True,primary=True,metric_scope_count=234))
for i,n in enumerate(names):
 p=ROOT/'00_input/native'/(n+Path(native[n]['native_path']).suffix.lower());assert sha(p)==native[n]['native_sha256'];body=p.read_bytes();inspect_artifact(body,p.name);os.link(p,folder/'models'/p.name)
 if (i+1)%1000==0:print('Verified export originals',i+1,flush=True)
shutil.copytree(supp/'ensembles',folder/'ensembles');shutil.copyfile(supp/'bonsai.json',folder/'bonsai.json')
representatives=[]
for g in groups:
 r=g['medoid'];n=r['model'];ext=Path(native[n]['native_path']).suffix.lower();alignments=g['aligned_members'];ensemble_prefix=target+'/'+g['ensemble_file']
 representatives.append(dict(cluster=g['cluster_label'],count=g['cluster_size'],model=n,method=method_info[native[n]['method']]['name'],color=g['color'],file=f'{target}/models/{n}{ext}',format=ext[1:],sha256=r['native_sha256'],ensemble_file=ensemble_prefix,ensemble_members=[dict(model=a['model'],file=target+'/'+a['aligned_file'],sha256=a['aligned_sha256'],is_medoid=a['model']==n)for a in alignments],ensemble_metadata=dict(file=target+'/'+str(Path(g['ensemble_file']).with_name('alignment.json'))),selection_method=g['selection_method']))
heatmaps=[]
for image in workflow.get('visualize_distogram',{}).get('images',[]):
 p=Path(image);dest=folder/'figures'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest);heatmaps.append(dict(name=p.stem.replace('_',' '),file=str(dest.relative_to(delivery))))
grid_csv=folder/'medoid-tm.csv'
with grid_csv.open('x',newline='')as f:
 w=csv.writer(f);w.writerow(['cluster',*grid['labels']]);w.writerows([label,*row]for label,row in zip(grid['labels'],grid['matrix']))
combined_hash=hashlib.sha256((plan['target']['sequence']*2).encode()).hexdigest();membership=folder/'memberships-and-scores.csv'
with membership.open('x',newline='')as f:
 fields=['model_id','method','cluster','ptm','iptm','mean_plddt','ranking_confidence','ranking_score','protein_ebm_energy_t010','model_file','sha256'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for n in names:w.writerow(dict(model_id=n,method=native[n]['method'],cluster=labels[n]['cluster_label'],**{k:scores[n].get(k)for k in fields[3:8]},protein_ebm_energy_t010=None,model_file='models/'+n+Path(native[n]['native_path']).suffix.lower(),sha256=native[n]['native_sha256']))
data=dict(target=target,target_label='HSPH1 construct 12757',view_id='whole',view_title='Complete homodimer · UMAP KNN',models=names,residues=234,methods=method_names,clusters=cluster_values,projections=projections,schemes=schemes,representatives=representatives,views=[dict(id='whole',name='UMAP KNN',data=target+'/primary.json')],membership_file=str(membership.relative_to(delivery)),heatmaps=heatmaps,model_files=[f'{target}/models/{n}'+Path(native[n]['native_path']).suffix.lower()for n in names],model_sha256=[native[n]['native_sha256']for n in names],model_chain_maps=read(ROOT/'00_input/chain-map.json'),structure_confidence=dict(kind='unavailable',note='No complete atom-confidence provenance catalog is declared;native scalar confidence remains available on the maps.'),representative_kind='full-cluster structural medoid',representative_policy='Exact whole-cluster fixed-chain C-alpha medoid;separate comparison ensemble uses up to 5 confidence-eligible members or unscored structural fallback.',ensemble_kind='saved aligned comparison ensemble',mask_note='All117 residues of each chain;234 canonical C-alpha positions,no trimming.',clustering_method_note='Joint all-residue C-alpha distance features;PCA/UMAP/t-SNE seed 42. UMAP components with subdivisions validated by feature silhouette ≥0.15 and repeat-seed ARI ≥0.80;one membership partition across projections.',medoid_tm=dict(labels=grid['labels'],matrix=grid['matrix'],models=[g['medoid']['model']for g in groups],csv=str(grid_csv.relative_to(delivery))),medoid_tm_note='Full-complex fixed A/B chain mapping;mean of both non-fast US-align directions with average-length normalization. Medoids use every cluster member.',bonsai=dict(file=f'{target}/bonsai.json',sha256=sha(folder/'bonsai.json'),selected_models=accepted['selected']),provenance=dict(source_commit=plan['library_commit'],approved_plan_sha256=sha(ROOT/'00_input/execution-plan.json'),sequence_sha256=combined_hash,chain_sequence_sha256=plan['target']['sequence_sha256'],models=4006,all_residues=True,sampling_counts=plan['immediate_methods'],energy_status='unavailable;no accepted scores',Bonsai_scope=read(supp/'bonsai.json')['scope']))
save(folder/'primary.json',data);save(delivery/'atlas.json',dict(targets=[dict(id=target,label='HSPH1 construct 12757',data=f'{target}/primary.json')]))
scope=dict(chain='A,B',chains=[dict(chain=c,expected_ca_count=117)for c in ['A','B']],sequence_sha256=combined_hash,expected_ca_count=234,canonical_positions=list(range(1,235)),analysis_uses_full_construct=True,regions_verified=False,reference_ranges='A1–117 and B1–117',note='Complete two-chain construct. Display-only native B/C→A/B mapping is verified per model;original downloads are unchanged.')
save(delivery/'clustering-residues.json',dict(schema_version=1,targets={target:dict(views=dict(whole=scope))}))
context=dict(title='HSPH1 construct 12757',record_summary='Two identical 117-residue chains,including the supplied tag. Organism and accession remain unverified.',project_writeup=dict(status='Exact construct and native-model scope verified',biological_relevance='The construct label is retained from its native run records;no full-length protein or biological oligomeric-state assignment is inferred.',ensemble_interpretation='4,006 generated models:four 1,000-model arms plus five AFsample3 and one BioEmu2 pilots. Unequal counts and cluster frequencies are sampling-library properties,not calibrated populations. ProteinEBM energies are unavailable.',project_citations=[]),references=[dict(label='AFsample2 · Kalakoti and Wallner (2025)',url='https://doi.org/10.1038/s42003-025-07791-9'),dict(label='AF-Cluster · Wayment-Steele et al. (2024)',url='https://doi.org/10.1038/s41586-023-06832-9'),dict(label='SPEACH_AF · Stein and Mchaourab (2022)',url='https://doi.org/10.1371/journal.pcbi.1010483'),dict(label='OpenDDE (2026 preprint)',url='https://doi.org/10.48550/arXiv.2607.03787'),dict(label='AFsample3 (2026 preprint)',url='https://doi.org/10.64898/2026.01.16.699904'),dict(label='BioEmu2 software release',url='https://github.com/microsoft/bioemu2/releases/tag/v0.1.0rc0'),dict(label='UMAP · McInnes et al.',url='https://doi.org/10.48550/arXiv.1802.03426'),dict(label='t-SNE · van der Maaten and Hinton',url='https://jmlr.org/papers/v9/vandermaaten08a.html'),dict(label='Bonsai · de Groot et al. (2026)',url='https://doi.org/10.1038/s41587-026-03220-2'),dict(label='US-align · Zhang et al. (2022)',url='https://doi.org/10.1038/s41592-022-01585-1')],provenance=dict(analysis_sequence_sha256=combined_hash))
save(delivery/'target-context.json',dict(verified_on='2026-11-09',targets={target:context}))
for name in ['residue-ranges.json','projection-metadata.json','supplementary-metadata.json','metric-overlays.json','tm-states.json','figure-supplements.json']:save(delivery/name,{})
save(delivery/'selection-highlights.json',dict(schema_version=1,enabled=False,targets={}))
# Use the established four-file helper on the unchanged native coordinates.
private=ROOT/'dataset/private';private.mkdir(parents=True);readme=ROOT/'execution/dataset-README.md';fasta=private/'sequence.fasta';fasta.write_text(''.join('>HSPH1_12757_chain_'+c+' copies_of_same_construct\n'+plan['target']['sequence']+'\n'for c in ['A','B']))
inventory=private/'inventory.csv';fields=['source_path','model_file','model_id','method','ptm','iptm','mean_plddt','ranking_confidence','ranking_score','common_multimer_ranking_confidence','protein_ebm_energy_t010','native_chain_ids','sampling_phase','physical_filter_flag','sha256']
with inventory.open('x',newline='')as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for n in names:
  r=native[n];ext=Path(r['native_path']).suffix.lower();v=confidence_value(scores[n],'ranking_confidence');w.writerow(dict(source_path=n+ext,model_file=r['method']+'/'+n+ext,model_id=n,method=r['method'],**{k:scores[n].get(k)for k in fields[4:9]},common_multimer_ranking_confidence=float(v)if math.isfinite(v)else None,protein_ebm_energy_t010=None,native_chain_ids='B,C'if r['method']in ['afsample2','afcluster','speachaf']else'A,B',sampling_phase='pilot'if r['method']in ['afsample3','bioemu2']else'complete_arm',physical_filter_flag=r.get('native_row',{}).get('native_physicality',''),sha256=r['native_sha256']))
package=ROOT/'dataset/package';seal=private/'seal.json';result=prepare_dataset(inventory,ROOT/'00_input/native',fasta,readme,package,seal,4006);verified=verify_dataset(package,seal)
with (package/'scores.csv').open()as f:deposited=list(csv.DictReader(f))
assert len(deposited)==4006 and {r['model_id']for r in deposited}==set(names)
assert all(r['sha256']==native[r['model_id']]['native_sha256']and r['method']==native[r['model_id']]['method']for r in deposited)
assert sum(bool(r['ptm'])for r in deposited)==4005 and sum(bool(r['mean_plddt'])for r in deposited)==3000
assert not any(r['protein_ebm_energy_t010']for r in deposited)
(delivery/'dataset').mkdir()
for n in ['README.md','scores.csv','sequence.fasta']:shutil.copyfile(package/n,delivery/'dataset'/n)
for n in ['index.html','app.js']:
 inspect_artifact((delivery/n).read_bytes(),n)
for p in delivery.rglob('*'):
 if p.is_file()and p.suffix in ['.json','.csv','.md','.fasta']:inspect_artifact(p.read_bytes(),str(p.relative_to(delivery)))
views=validate_views(delivery,{str(p.relative_to(delivery))for p in delivery.rglob('*')if p.is_file()})
files=[dict(path=str(p.relative_to(delivery)),bytes=p.stat().st_size,sha256=sha(p))for p in sorted(delivery.rglob('*'))if p.is_file()]
save(ROOT/'delivery-manifest.json',dict(schema_version=1,files=files))
overlay=ROOT/'preview';overlay.mkdir();save(overlay/'presentation.json',dict(kind='saved-atlas-presentation-overlay',source_delivery=str(delivery),source_manifest_sha256=sha(ROOT/'delivery-manifest.json'),source_files=files,presentation_files=[],additional_deliveries={},prepared_by='HSPH1 thin saved-result adapter',approved_plan_sha256=sha(ROOT/'00_input/execution-plan.json')))
save(ROOT/'receipts/export-completion.json',dict(status='verified',models=4006,residues=234,clusters=len(groups),Bonsai_leaves=accepted['selected'],views=views,delivery_manifest_sha256=sha(ROOT/'delivery-manifest.json'),dataset_seal_sha256=sha(seal),dataset_verification=verified,energy_coverage=0,publications=0))
print('VERIFIED PRIVATE EXPORT',len(files),'files',4006,'models',flush=True)
