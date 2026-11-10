"""Approved geometry-only HDBSCAN and its own exact native supplements."""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,io,json,math,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analysis_common import *

def density(plan,np,rows):
    energies(plan);finished(plan,'R0')
    names=[r['model_id'] for r in rows];matrix=features(plan,names,np.float32)
    root=Path(plan['run_root'])/'04_analysis/HDBSCAN';root.mkdir()
    module_path=Path(plan['density_native'])
    spec=importlib.util.spec_from_file_location('src.analysis.hd_density_experiment',module_path)
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    settings=dict(seeds=[42,7,123],n_neighbors=30,min_dist=0,min_cluster_size=15,min_samples=11,workers=8)
    native.fit_selection(matrix,names,np.arange(4006),10,settings,root/'fits',lambda s:print(s,flush=True))
    with np.load(root/'fits/leaf-seed-42.npz',allow_pickle=False) as f:raw=f['labels'].copy();strength=f['probabilities'].copy()
    require(raw.shape==strength.shape==(4006,) and np.isfinite(strength).all() and np.all((strength>=0)&(strength<=1)),'Invalid density partition')
    groups=sorted(set(raw)-{-1},key=lambda c:(-int(np.sum(raw==c)),min(n for n,x in zip(names,raw) if x==c)))
    require(len(groups)<=267,'Density cluster bound exceeded')
    mapping={c:'Cluster '+str(i+1) for i,c in enumerate(groups)}
    labels=[mapping.get(x,'Unassigned') for x in raw]
    import matplotlib
    colors={label:matplotlib.colors.to_hex(matplotlib.colormaps['tab20']((i%20)/19)) for i,label in enumerate(mapping.values())}
    colors['Unassigned']='#888888'
    result={'status':'validated','models':names,'raw_labels':raw.tolist(),'labels':labels,'strengths':strength.tolist(),
       'colors':colors,'clusters':len(groups),'noise_models':int(np.sum(raw==-1)),'settings':settings,'dimensions':10,
       'primary':'seed42 leaf','geometry_only':True,'features':27261,
       'fit_result_sha256':sha(root/'fits/result.json'),
       'fit_files_sha256':{p.name:sha(p) for p in (root/'fits').iterdir() if p.is_file()},
       'feature_sha256':hashlib.sha256(matrix.tobytes()).hexdigest(),'plan_sha256':plan['_sha256']}
    save(root/'partition.json',result)
    with (root/'memberships.csv').open('x',newline='') as f:
        w=csv.writer(f);w.writerow(['model_id','native_sha256','raw_label','cluster_label','strength'])
        w.writerows((r['model_id'],r['sha256'],int(raw[i]),labels[i],float(strength[i])) for i,r in enumerate(rows))

def select(plan,np,rows):
    finished(plan,'D0');root=Path(plan['run_root'])/'04_analysis/HDBSCAN'
    partition=read(root/'partition.json');require(partition['status']=='validated' and partition['models']==[r['model_id'] for r in rows],'Partition identity differs')
    from src.analysis.cluster_ensembles import structural_medoid,rigid_fit
    from src.analysis.confidence_ranking import confidence_value
    from src.analysis.casp17_ensemble_exports import all_atoms,atom_signature,pdb_compatible,multimodel_pdb
    from src.analysis.structure_io import get_structure
    from Bio.PDB import PDBIO
    scores={r['model_id']:r['scores'] for r in read(saved_path(plan,'00_input/atlas-scores.json'))['models']}
    e=energies(plan);labels=partition['labels'];assigned=sorted(set(labels)-{'Unassigned'},key=lambda x:int(x.split()[-1]))
    require(assigned,'No assigned density clusters; stop without fabricating a supplement')
    counts=[labels.count(label) for label in assigned]
    require(sum(n*(n-1)//2 for n in counts)<=8022015 and sum(n*n for n in counts)<=16048036,'Exact medoid budget exceeded')
    print('Exact full-cluster medoid unordered pairs',sum(n*(n-1)//2 for n in counts),flush=True)
    output=root/'supplement';output.mkdir();canonical=output/'canonical';canonical.mkdir();(output/'ensembles').mkdir()
    arrays=np.stack([ca_array(r) for r in rows]);np.save(root/'canonical-ca.npy',arrays,allow_pickle=False)
    lookup={r['model_id']:i for i,r in enumerate(rows)};tree={};groups=[];records={}
    def record(index,label,color):
        row=rows[index];name=row['model_id']
        if name not in records:
            path=canonical/(name+'.cif');atoms=canonical_full(row,path)
            confidence=confidence_value(scores[name],'ranking_confidence')
            records[name]=dict(model=name,source_path=str(path),sha256=sha(path),native_sha256=row['sha256'],method=row['method'],
                confidence=float(confidence) if math.isfinite(confidence) else None,atom_count=atoms,cluster_label=label,color=color)
        return dict(records[name])
    for label in assigned:
        indices=sorted((i for i,x in enumerate(labels) if x==label),key=lambda i:rows[i]['model_id'])
        block=arrays[indices];mi,mean=structural_medoid(block);index=indices[mi]
        medoid=dict(record(index,label,partition['colors'][label]),rank=1,state=1,mean_ca_rmsd=mean)
        eligible=[]
        for i in indices:
            confidence=confidence_value(scores[rows[i]['model_id']],'ranking_confidence')
            if math.isfinite(confidence):eligible.append((float(confidence),rows[i]['model_id'],i))
        if eligible:
            chosen=[dict(record(i,label,partition['colors'][label]),rank=rank,state=rank)
                    for rank,(_,_,i) in enumerate(sorted(eligible,key=lambda x:(-x[0],x[1]))[:5],1)]
            policy='top5_common_multimer_confidence_eligible'
        else:
            nearest=sorted((rigid_fit(arrays[i],arrays[index])[2],rows[i]['model_id'],i) for i in indices if i!=index)[:4]
            chosen=[dict(medoid)]+[dict(record(i,label,partition['colors'][label]),rank=rank,state=rank) for rank,(_,_,i) in enumerate(nearest,2)]
            policy='unscored_structural_medoid_then_nearest'
        folder=output/'ensembles'/label;folder.mkdir();texts=[];alignment=[]
        for rec in chosen:
            mobile=arrays[lookup[rec['model']]];rotation,translation,rmsd=rigid_fit(mobile,arrays[index])
            model=get_structure(rec['source_path'])[0].copy();signature=atom_signature(model)
            for atom in all_atoms(model):atom.coord=np.asarray(atom.coord,dtype=float)@rotation+translation
            require(atom_signature(model)==signature and len(all_atoms(model))==rec['atom_count'],'Atom loss during alignment')
            pdb_compatible(model);writer=PDBIO();writer.set_structure(model);stream=io.StringIO();writer.save(stream)
            text=stream.getvalue();texts.append(text);path=folder/(rec['model']+'.pdb');path.write_text(text)
            alignment.append(dict(model=rec['model'],native_sha256=rec['native_sha256'],aligned_sha256=sha(path),
              aligned_file=str(path.relative_to(output)),CA_RMSD=rmsd,atom_count=rec['atom_count']))
        ensemble=folder/'ensemble.pdb';ensemble.write_text(multimodel_pdb(texts,[r['model'] for r in chosen]))
        save(folder/'alignment.json',{'reference':medoid['model'],'residues':234,'members':alignment,'policy':policy,'ensemble_sha256':sha(ensemble)})
        groups.append(dict(cluster_label=label,cluster_size=len(indices),color=partition['colors'][label],cluster_type='prediction',
          medoid=medoid,selected=chosen,selection_method=policy,ensemble_file=str(ensemble.relative_to(output)),ensemble_sha256=sha(ensemble)))
        for rec in [medoid,*chosen]:tree.setdefault(rec['model'],rec)
        print('Accepted density medoid/ensemble',label,len(indices),medoid['model'],flush=True)
    noise=sorted((i for i,x in enumerate(labels) if x=='Unassigned'),key=lambda i:(e[i],rows[i]['model_id']))[:5]
    for i in noise:tree.setdefault(rows[i]['model_id'],record(i,'Unassigned','#888888'))
    require(len(tree)<=1607,'Bonsai leaf budget exceeded')
    save(output/'selection.json',dict(status='validated',target='HSPH1_12757_homodimer',models=4006,residues=234,
         clusters=groups,selected_tree=list(tree.values()),noise_examples=[rows[i]['model_id'] for i in noise],
         partition_sha256=sha(root/'partition.json'),canonical_CA_sha256=sha(root/'canonical-ca.npy'),
         unordered_RMSD_pairs=sum(n*(n-1)//2 for n in counts),ordered_RMSD_cells=sum(n*n for n in counts)))

def grid(plan,np,rows):
    finished(plan,'D1');root=Path(plan['run_root'])/'04_analysis/HDBSCAN';s=read(root/'supplement/selection.json')
    from src.analysis.cluster_medoid_tm import calculate_medoid_tm
    groups=s['clusters'];require(len(groups)*(len(groups)-1)<=71022,'Density TM call budget exceeded')
    for group in groups:checked(group['medoid']['source_path'],group['medoid']['sha256'])
    p=dict(identifier='HSPH1_12757_homodimer_HDBSCAN',clusters=[dict(g,selected=[g['medoid']]) for g in groups],
       terminal_detection=terminal(plan),fixed_chain_mapping={'A':'A','B':'B'},report=str(root/'supplement/selection.json'))
    result=calculate_medoid_tm(p,Path(plan['usalign']),workers=4,log=lambda s:print(s,flush=True))
    values=np.asarray(result['matrix']);require(values.shape==(len(groups),len(groups)) and np.isfinite(values).all() and np.array_equal(values,values.T),'Invalid density medoid grid')
    result.update(partition_sha256=sha(root/'partition.json'),directional_calls=2*len(result['comparisons']))
    save(root/'supplement/medoid-tm.json',result)

def bonsai(plan,np,rows):
    finished(plan,'D2');root=Path(plan['run_root'])/'04_analysis/HDBSCAN';s=read(root/'supplement/selection.json')
    from src.analysis.bonsai_geometry import nonzero_pca_features,record_input_audit,native_tree_groups
    from src.analysis.bonsai_interactive import export_saved_bonsai
    import bonsai_clustering as native
    selected=s['selected_tree'];names=[r['model'] for r in selected]
    require(10<len(names)<=1607,'Selection cannot support the approved native kNN10 tree')
    matrix=features(plan,names,np.float16);transformed,projection=nonzero_pca_features(matrix)
    output=root/'supplement/bonsai';settings=dict(schema_version=2,max_components=None,rescale_by_var=False,use_knn=10,
       grouping='native_min_pairwise_distance_silhouette_2_to_7',input_archive=None)
    source=dict(kind='frozen_models_by_features',terminal_detection=terminal(plan),dtype='float16',
       equivalence='Exact saved all27261 full-dimer distances for this partition selection;no mask or projection refit')
    written=native.write_bonsai_input_files(transformed,names,output,annotation_rows=[dict(cellID=r['model'],original_umap_cluster=r['cluster_label'],confidence=r['confidence']) for r in selected])
    audit=record_input_audit(output,matrix,transformed,names,projection,source=source)
    native.run_bonsai_subprocesses(results_dir=output,input_dir=written['input_dir'],identifier='HSPH1_12757_HDBSCAN_selected',
       annotation_dir=written['annotation_dir'],status_callback=lambda s:print(s,flush=True),rescale_by_var=False,use_knn=10,preprocess=False)
    path=output/('final_bonsai_zscore'+str(native.DEFAULT_ZSCORE_CUTOFF))/'tree.nwk'
    grouping=native_tree_groups(path,names,native.bonsai_submodule_root());save(output/'tree_groups.json',grouping)
    native.write_annotation_csv(written['annotation_dir'],names,[dict(cellID=r['model'],cluster=grouping['assignments'][r['model']]['bonsai_group'],
       original_umap_cluster=r['cluster_label'],confidence=r['confidence']) for r in selected])
    native.preprocess_bonsai_results(output,annotation_dir=written['annotation_dir'],status_callback=lambda s:print(s,flush=True))
    save(output/'result.json',dict(selected_models=selected,settings=settings,input_audit=audit,input_feature_count=transformed.shape[1],
       tree_grouping=grouping,model_count=len(names),zscore_cutoff=native.DEFAULT_ZSCORE_CUTOFF,feature_definition=source['equivalence']))
    result=export_saved_bonsai(output/'result.json',names,expected_retained_positions=terminal(plan)['retained_reference_positions'])
    result['scope']='This HDBSCAN selection only;full234-residue geometry;medoids,confidence members and explicit noise examples'
    result['partition_sha256']=sha(root/'partition.json');save(root/'supplement/bonsai.json',result)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['D0','D1','D2','D3']);p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
    a=p.parse_args();plan=load(a.plan,a.plan_sha256);plan['_sha256']=a.plan_sha256
    np,rows=initialize(plan,a.phase)
    {'D0':density,'D1':select,'D2':grid,'D3':bonsai}[a.phase](plan,np,rows)
if __name__=='__main__':main()
