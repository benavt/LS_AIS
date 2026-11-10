"""Full-dimer positional states, fixed-cardinality MCMC/DISCO, and final gates."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,csv,gzip,hashlib,io,json,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from analysis_common import *
from complex_tm import ComplexCAStore,make_scorer,ARGUMENTS,VERSION

def protocol(plan,np,rows):
    finished(plan,'D3')
    root=Path(plan['run_root'])/'04_analysis/states';root.mkdir()
    coords=np.load(Path(plan['run_root'])/'04_analysis/HDBSCAN/canonical-ca.npy',allow_pickle=False)
    rng=np.random.default_rng(9123);toy=rng.normal(size=(234,3))*10;toy[117:]+=[30,7,-11]
    rotation=np.asarray([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    arrays={'real':coords[0],'rigid':coords[0]@rotation+[7,-3,11],'toy':toy,
            'swapped':np.vstack([toy[117:],toy[:117]]),
            'chain_shift':np.vstack([toy[:117],toy[117:]+[50,0,0]])}
    records={}
    for name,a in arrays.items():
        path=root/(name+'.cif');write_ca(path,name,a,plan['sequence']);records[name]={'model':name,'path':str(path)}
    scorer=make_scorer(None,plan['usalign'],root/'protocol-native',12,plan['usalign_sha256'])
    results=[]
    for i,(first,second,identity) in enumerate([('real','real',True),('real','rigid',True),('toy','toy',True),('toy','swapped',False),('toy','chain_shift',False)]):
        pair=[]
        for j,(a,b) in enumerate([(first,second),(second,first)]):
            result=scorer._direction(records[a],records[b],root/f'protocol-{i}-{j}.matrix')
            if identity:
                require(result['score']>.999,'Rigid/self positional protocol test failed')
                transform=result['transform']
                transformed=arrays[a]@np.asarray(transform['rotation']).T+transform['translation']
                require(np.sqrt(np.mean(np.sum((transformed-arrays[b])**2,axis=1)))<.02,'Native matrix convention differs')
            else:require(result['score']<.99,'Protocol allowed chain swapping or independent-chain fitting')
            pair.append(result)
        results.append({'inputs':[first,second],'expected_identity':identity,'directions':pair})
    require(scorer.actual_calls==10,'Protocol call budget differs')
    save(root/'S0-protocol.json',{'status':'validated','protocol':scorer.protocol,'native_calls':scorer.actual_calls,
         'full_dimer_CA':234,'tests':results,'no_independent_chain_fitting':True})

def states(plan,np,rows):
    finished(plan,'S0');root=Path(plan['run_root'])/'04_analysis/states'
    require(read(root/'S0-protocol.json')['status']=='validated','Complex protocol not accepted')
    density=read(Path(plan['run_root'])/'04_analysis/HDBSCAN/supplement/selection.json')
    primary=read(saved_path(plan,'supplement/selection.json'))
    original={r['model_id']:r for r in rows};proxy={}
    for group in primary['clusters']:
        name=group['medoid']['model'];require(group['medoid']['native_sha256']==original[name]['sha256'],'Primary medoid source differs')
        proxy[name]=proxy.get(name,0)+group['cluster_size']
    names=sorted(set(proxy)|{g['medoid']['model'] for g in density['clusters']})
    require(1<=len(names)<=294 and sum(proxy.values())==4006,'Candidate or proxy scope differs')
    coords=np.load(Path(plan['run_root'])/'04_analysis/HDBSCAN/canonical-ca.npy',allow_pickle=False)
    require(sha(Path(plan['run_root'])/'04_analysis/HDBSCAN/canonical-ca.npy')==density['canonical_CA_sha256'],'Canonical geometry changed')
    store=ComplexCAStore(rows,coords,plan['sequence'],root/'canonical')
    scorer=make_scorer(store,plan['usalign'],root/'tm-cache',110178,plan['usalign_sha256'])
    matrix=np.eye(len(names));pairs=[(i,j) for i in range(len(names)) for j in range(i+1,len(names))]
    print('Candidate directional ceiling',len(pairs)*2,flush=True)
    def score_pair(pair):
        i,j=pair;return i,j,scorer.score(names[i],names[j])['score']
    with ThreadPoolExecutor(max_workers=4) as pool:
        for k,(i,j,value) in enumerate(pool.map(score_pair,pairs),1):
            matrix[i,j]=matrix[j,i]=value
            if k%1000==0:print('Candidate pairs complete',k,flush=True)
    from src.analysis.tm_state_geometry import discover_states,assign_membership,sensitivity_memberships,preferred_forward_transform
    discovered=discover_states(names,matrix.tolist(),{name:proxy.get(name,0) for name in names},cutoff=.7,coverage_target=.9,max_states=3)
    anchors=discovered['anchors'];require(anchors,'No structural anchor; stop without inventing a state')
    model_names=[r['model_id'] for r in rows];scores=np.empty((4006,len(anchors)));poses={}
    def model_scores(name):
        values=[];pose=[]
        for anchor in anchors:
            result=scorer.score(name,anchor);values.append(result['score'])
            p=preferred_forward_transform(result);p.update(cache_key=result['key'],
                cache_sha256=sha(root/'tm-cache'/(result['key']+'.json')),anchor=anchor)
            pose.append(p)
        winner=anchors.index(name) if name in anchors and values[anchors.index(name)]==1 else min(range(len(anchors)),key=lambda j:(-values[j],anchors[j]))
        return values,pose[winner]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for i,(values,pose) in enumerate(pool.map(model_scores,model_names)):
            scores[i]=values;poses[model_names[i]]=pose
    membership=assign_membership(model_names,anchors,scores.tolist(),cutoff=.7,min_state_size=50)
    sensitivity=sensitivity_memberships(model_names,anchors,scores.tolist(),cutoffs=(.6,.7,.8),min_state_size=50)
    require(scorer.actual_calls<=110178,'Positional TM call ceiling exceeded')
    save(root/'S1-states.json',{'status':'validated','models':model_names,'candidate_models':names,'candidate_TM':matrix.tolist(),
         'primary_proxy_masses':proxy,'discovery':discovered,'membership':membership,'sensitivity':sensitivity,
         'member_anchor_TM':scores.tolist(),'poses':poses,'protocol':scorer.protocol,'native_directional_calls':scorer.actual_calls,
         'partition_sha256':sha(Path(plan['run_root'])/'04_analysis/HDBSCAN/partition.json')})

def json_value(value):
    import numpy as np
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {str(k):json_value(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [json_value(v) for v in value]
    return value

def panel_pdb(texts,names):
    """Use the pinned five-member serializer in blocks; retain one 50-MODEL panel."""
    from src.analysis.casp17_ensemble_exports import multimodel_pdb
    require(len(texts)==len(names)==len(set(names))==50,'Panel cardinality must be50 distinct originals')
    lines=[];serial=0
    for first in range(0,50,5):
        block=multimodel_pdb(texts[first:first+5],names[first:first+5])
        for line in block.splitlines():
            if line.startswith('MODEL '):
                serial+=1;lines.append(f'MODEL     {serial:4d}')
            elif line and line!='END':lines.append(line)
    require(serial==50,'Serialized panel cardinality differs')
    return '\n'.join([*lines,'END',''])

def export_panel(plan,rows,names,poses,output,label,state):
    import numpy as np
    from Bio.PDB import PDBIO,Model
    from src.analysis.casp17_ensemble_exports import all_atoms,atom_signature,pdb_compatible
    lookup={r['model_id']:r for r in rows};texts=[];members=[]
    require(len(names)==len(set(names))==50,'Panel cardinality must be50 distinct originals')
    for name in names:
        row=lookup[name];original=native_structure(row);model=Model.Model(0)
        for ci,c in enumerate(row['chains']):
            chain=original[c['id']].copy();chain.id='AB'[ci];model.add(chain)
        signature=atom_signature(model);atoms=all_atoms(model);pose=poses[name]
        root=Path(plan['run_root'])/'04_analysis/states/tm-cache';checked(root/(pose['cache_key']+'.json'),pose['cache_sha256'])
        rotation=np.asarray(pose['rotation']);translation=np.asarray(pose['translation'])
        for atom in atoms:atom.coord=np.asarray(atom.coord,dtype=float)@rotation.T+translation
        require(atom_signature(model)==signature and len(all_atoms(model))==len(atoms),'Whole-complex pose changed atom identities')
        pdb_compatible(model);writer=PDBIO();writer.set_structure(model);stream=io.StringIO();writer.save(stream);texts.append(stream.getvalue())
        members.append({'model_id':name,'native_sha256':row['sha256'],'atom_count':len(atoms),'anchor':pose['anchor'],
                        'native_pose_cache_sha256':pose['cache_sha256']})
    output.write_text(panel_pdb(texts,names))
    return {'kind':label,'state':state,'k':50,'model_ids':names,'members':members,'ensemble_file':str(output.name),
            'ensemble_sha256':sha(output),'residues_per_member':234,'chains':['A','B'],
            'pose':'One native full-dimer positional-TM transform;original files unchanged'}

def sample(plan,np,rows):
    finished(plan,'S1');root=Path(plan['run_root'])/'04_analysis/states';result=read(root/'S1-states.json')
    require(result['status']=='validated' and result['models']==[r['model_id'] for r in rows],'State identities differ')
    e=energies(plan);quartile=np.quantile(e,[.25,.75],method='linear');tau=float(quartile[1]-quartile[0])
    require(np.isfinite(tau) and tau>0,'Zero or nonfinite full-cohort energy IQR')
    from scipy.special import logsumexp
    from src.analysis.ensemble_sampling import energy_distribution
    from src.analysis.tm_state_subset import run_subset_chains,log_subset_dp,inclusion_probabilities,exact_subset_draw,disco_subset,replay_subsets
    with saved_path(plan,plan['primary_labels_relative']).open() as f:primary={r['model']:r['cluster_label'] for r in csv.DictReader(f)}
    all_names=[r['model_id'] for r in rows];hdb=read(Path(plan['run_root'])/'04_analysis/HDBSCAN/partition.json')
    priors={'Primary':([primary[n] for n in all_names],()),'HDBSCAN':(hdb['labels'],('Unassigned',))}
    from sampling_resume import copy_frozen_sampling,restore_chains
    output=root/plan.get('sampling_relative','sampling');output.mkdir();(output/'exports').mkdir()
    resume=plan.get('sampling_resume')
    if resume:copy_frozen_sampling(root,output,resume)
    distributions={}
    for name,(labels,noise) in priors.items():
        value=energy_distribution(e,labels,.5,tau,noise_labels=noise)
        require(np.isfinite(value['log_probabilities']).all() and np.all(value['probabilities']>0),'Unrepresentable full-cohort probabilities')
        distributions[name]=value
        prior_arrays={'log_probability':value['log_probabilities'],'probability':value['probabilities'],'energy':e,'model_ids':np.asarray(all_names)}
        prior_path=output/(name+'-full-prior.npz')
        if prior_path.exists():
            with np.load(prior_path,allow_pickle=False) as cached:
                require(set(cached.files)==set(prior_arrays) and all(np.array_equal(cached[k],v) for k,v in prior_arrays.items()),'Frozen full-cohort prior differs')
        else:
            with prior_path.open('xb') as f:np.savez_compressed(f,**prior_arrays)
        prior_record={'alpha':.5,'tau':tau,'tau_rule':'Full4006 energy IQR,linear quantiles',
            'group_sizes':value['cluster_sizes'],'group_probabilities':value['cluster_probabilities'],
            'original_noise_probability':value['noise_probability'],'pool_scope':4006,'noise_labels':list(noise)}
        prior_meta=output/(name+'-prior.json')
        if prior_meta.exists():require(read(prior_meta)==json_value(prior_record),'Frozen prior metadata differs')
        else:save(prior_meta,prior_record)
    conditions=[];proposal_count=0;exact_count=0;export_count=0;restored_proposals=0;restored_controls=0
    for state in sorted(result['membership']['states'],key=lambda r:r['id']):
        if not state['supported']:continue
        indices=np.asarray(state['indices'],dtype=int);names=[all_names[i] for i in indices];pool_e=e[indices]
        require(len(names)>=50,'Unsupported state entered sampling')
        for prior,(labels,noise) in priors.items():
            stream=plan['sampling_streams'][state['id']+'_'+prior];seed=stream['base']
            lp=distributions[prior]['log_probabilities'][indices];lp=lp-logsumexp(lp)
            fine=[labels[i] for i in indices];methods=[rows[i]['method'] for i in indices]
            condition=state['id']+'_'+prior;folder=output/condition
            restored=bool(resume and condition==resume['condition'])
            if restored:
                require(folder.is_dir(),'Missing frozen condition')
                chains=restore_chains(folder,lp,k=50,steps=10000,burn=1000,seed=seed,energies=pool_e,
                    labels=fine,methods=methods,noise_labels=noise)
                restored_proposals+=chains['restored_proposals']
            else:
                folder.mkdir()
                chains=run_subset_chains(lp,k=50,chains=4,steps=10000,burn=1000,seed=seed,energies=pool_e,
                    labels=fine,methods=methods,noise_labels=noise,uniform_mixture=.1)
            empirical=np.zeros(len(names));draws=0
            for ci,chain in enumerate(chains['chains']):
                arrays={k:v for k,v in chain.items() if isinstance(v,np.ndarray)}
                if not restored:
                    with (folder/f'chain-{ci}.npz').open('xb') as f:np.savez_compressed(f,**arrays)
                    meta={k:v for k,v in chain.items() if not isinstance(v,np.ndarray)}
                    save(folder/f'chain-{ci}.json',json_value(meta))
                replayed=0
                for step,panel in enumerate(replay_subsets(chain)):
                    replayed+=1
                    if step>=1000:empirical[panel]+=1;draws+=1
                require(replayed==chain['proposals'],'Saved chain replay count differs')
                proposal_count+=chain['proposals']
            dp=log_subset_dp(lp,k=50);marginal=inclusion_probabilities(lp,k=50,dp=dp)
            if restored:
                cached=read(folder/'exact-controls.json')
                require(cached['law']=='product_weight_fixed_cardinality_subset' and cached['seeds']==stream['exact_control_seeds'] and
                    cached['conditional_pool']==names and np.allclose(cached['inclusion_probabilities'],marginal,rtol=0,atol=1e-12),'Frozen exact controls differ')
                lookup={n:i for i,n in enumerate(names)}
                controls=[np.asarray([lookup[n] for n in c],dtype=int) for c in cached['panels']]
                restored_controls+=len(controls)
            else:controls=[exact_subset_draw(lp,k=50,seed=s,dp=dp) for s in stream['exact_control_seeds']]
            exact_count+=len(controls);require(len(controls)==20,'Exact control count differs')
            require(all(len(c)==len(set(c.tolist()))==50 for c in controls),'Exact control cardinality differs')
            control_ids=[[names[i] for i in c] for c in controls]
            if not restored:save(folder/'exact-controls.json',{'law':'product_weight_fixed_cardinality_subset','panels':control_ids,
                  'seeds':stream['exact_control_seeds'],'conditional_pool':names,'inclusion_probabilities':marginal.tolist()})
            production=[names[i] for i in chains['production_indices']]
            disco=disco_subset(lp,pool_e,fine,k=50,seed=stream['DISCO_seed'],noise_labels=noise,model_ids=names)
            control=[names[i] for i in disco['indices']]
            panels=[]
            for kind,ids in [('MCMC50',production),('DISCO50',control)]:
                file=output/'exports'/(condition+'_'+kind+'.pdb')
                panel=export_panel(plan,rows,ids,result['poses'],file,kind,state['id'])
                panel.update(prior=prior,condition=condition,law=chains['law'] if kind=='MCMC50' else disco['law'])
                save(file.with_suffix('.json'),panel);panels.append(panel);export_count+=50
            diagnostic={'native':chains['diagnostics'],'trace_scope':'Four ordered panel chains after1000 burn-in;no flattened model-ID diagnostics',
                'exact_inclusion_marginal_sum':float(marginal.sum()),
                'MCMC_inclusion_RMSE':float(np.sqrt(np.mean((empirical/draws-marginal)**2))) if draws else None,
                'expected_panel_mean_energy':float(np.dot(marginal,pool_e)/50),'degenerate_single_subset':len(names)==50,
                'completion_is_not_convergence':True,'poor_mixing_extension':False}
            save(folder/'diagnostics.json',json_value(diagnostic))
            conditions.append({'id':condition,'state':state['id'],'prior':prior,'pool_models':len(names),
                 'k':50,'seed_stream':stream,'transition_seeds':chains['transition_seeds'],
                 'production_chain':0,'production_iteration':10000,'panels':panels,
                 'diagnostics_file':condition+'/diagnostics.json','exact_controls_file':condition+'/exact-controls.json',
                 'noise_prior_scope':'Original full4006 cohort,conditioned on state;fine group sizes not recomputed',
                 'DISCO':json_value(disco)})
            print('Accepted sampling condition',condition,len(names),'MCMC50 and DISCO50',flush=True)
    require(proposal_count<=240000 and exact_count<=120 and export_count<=600,'Sampling budget exceeded')
    save(output/'S2-summary.json',{'status':'validated','tau':tau,'alpha':.5,'models':4006,'conditions':conditions,
         'proposals':proposal_count,'restored_proposals':restored_proposals,'new_proposals':proposal_count-restored_proposals,
         'restored_exact_control_panels':restored_controls,'exact_control_panels':exact_count,'exported_coordinate_instances':export_count,
         'unsupported_states':[r for r in result['membership']['states'] if not r['supported']],
         'uncovered_models':result['membership']['unassigned_models'],'source_states_sha256':sha(root/'S1-states.json'),
         'files_sha256':{str(p.relative_to(output)):sha(p) for p in output.rglob('*') if p.is_file()}})

def acceptance(plan,np,rows):
    finished(plan,'S2')
    root=Path(plan['run_root'])/'04_analysis';d=root/'HDBSCAN';s=root/'states'
    partition=read(d/'partition.json');selection=read(d/'supplement/selection.json');tm=read(d/'supplement/medoid-tm.json');tree=read(d/'supplement/bonsai.json')
    states=read(s/'S1-states.json');sampling_root=s/plan.get('sampling_relative','sampling');sampling=read(sampling_root/'S2-summary.json');protocol_record=read(s/'S0-protocol.json')
    for name,digest in partition['fit_files_sha256'].items():checked(d/'fits'/name,digest)
    for name,digest in sampling['files_sha256'].items():checked(sampling_root/name,digest)
    require(partition['models']==states['models']==[r['model_id'] for r in rows] and len(partition['labels'])==4006,'Cohort differs')
    require(sum(g['cluster_size'] for g in selection['clusters'])+partition['noise_models']==4006,'Noise or cluster accounting differs')
    require({r['model'] for r in tree['models']}=={r['model'] for r in selection['selected_tree']},'Native tree selection differs')
    total_calls=tm['directional_calls']+states['native_directional_calls']+protocol_record['native_calls']
    require(total_calls<=181212 and sampling['status']=='validated' and sampling['conditions'],'Scientific selection incomplete')
    from Bio.PDB import PDBParser
    from Bio.SeqUtils import seq1
    seen=0
    for condition in sampling['conditions']:
        for panel in condition['panels']:
            require(len(panel['model_ids'])==len(set(panel['model_ids']))==50,'Panel cardinality differs')
            path=sampling_root/'exports'/panel['ensemble_file'];checked(path,panel['ensemble_sha256'])
            models=list(PDBParser(QUIET=True).get_structure('panel',path));require(len(models)==50,'Ensemble conformer count differs')
            for model in models:
                require([c.id for c in model]==['A','B'],'Ensemble lost a chain')
                for chain in model:require(len(chain)==117 and ''.join(seq1(r.resname) for r in chain)==plan['sequence'],'Ensemble construct differs')
            seen+=50
    require(seen==sampling['exported_coordinate_instances']<=600,'Exported scope differs')
    files={str(p.relative_to(root)):sha(p) for p in root.rglob('*.json') if p.name!='S3-acceptance.json'}
    save(root/'S3-acceptance.json',{'status':'validated','models':4006,'residues':234,'density_clusters':partition['clusters'],
         'noise_models':partition['noise_models'],'sampling_conditions':len(sampling['conditions']),
         'native_directional_calls':total_calls,'sampling_coordinate_instances':seen,'accepted_json_sha256':files,
         'source_plan_sha256':plan['_sha256'],'publication_held':True,'browser_review':'pending'})

def delivery(plan,np,rows):
    finished(plan,'S3')
    root=Path(plan['run_root'])/'04_analysis';accepted=read(root/'S3-acceptance.json')
    require(accepted['status']=='validated','Scientific acceptance incomplete')
    for name,digest in accepted['accepted_json_sha256'].items():checked(root/name,digest)
    output=Path(plan['run_root'])/plan.get('delivery_relative','05_delivery');output.mkdir()
    from structure_clustering.privacy import privacy_check,CREDENTIAL
    def clean(value):
        if isinstance(value,dict):return {k:clean(v) for k,v in value.items() if k not in
           {'source_path','path','executable','command','stdout','stderr','report','selected_inputs','resource_evidence','CPU_resource_evidence'}}
        if isinstance(value,list):return [clean(x) for x in value]
        if isinstance(value,str) and value.startswith(('/scratch/','/home/','/gpfs/','/sys/')):return None
        return value
    sampling_root=root/'states'/plan.get('sampling_relative','sampling')
    selected=[root/'current4006-energy-rankings.csv',root/'HDBSCAN/partition.json',root/'HDBSCAN/memberships.csv',
       root/'HDBSCAN/supplement/selection.json',root/'HDBSCAN/supplement/medoid-tm.json',root/'HDBSCAN/supplement/bonsai.json',
       root/'states/S1-states.json',sampling_root/'S2-summary.json']
    for name,digest in read(sampling_root/'S2-summary.json')['files_sha256'].items():checked(sampling_root/name,digest)
    selected+=list((root/'HDBSCAN/supplement/ensembles').glob('*/alignment.json'))
    selected+=list(sampling_root.rglob('*.json'))+list(sampling_root.rglob('*.npz'))
    ensembles=list((root/'HDBSCAN/supplement/ensembles').glob('*/ensemble.pdb'))+list((sampling_root/'exports').glob('*.pdb'))
    selected+=ensembles
    source_hashes={}
    for source in sorted(set(selected)):
        relative=source.relative_to(root);destination=output/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        source_hashes[str(relative)]=sha(source)
        if source.suffix=='.json':raw=(json.dumps(clean(read(source)),indent=2,allow_nan=False)+'\n').encode()
        else:raw=source.read_bytes()
        if source.suffix=='.npz':
            from delivery_arrays import privacy_check_npz
            privacy_check_npz(raw,str(relative))
        if source.suffix in ('.json','.csv','.pdb'):
            privacy_check(raw,str(relative));require(not CREDENTIAL.search(raw.decode('utf-8',errors='replace')),'Credential-shaped delivery text')
        if source.suffix=='.pdb':
            destination=destination.with_suffix('.pdb.gz')
            with destination.open('xb') as f:
                with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as compressed:compressed.write(raw)
        else:
            with destination.open('xb') as f:f.write(raw)
    files={str(p.relative_to(output)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in output.rglob('*') if p.is_file()}
    require(sum(r['bytes'] for r in files.values())<=20*2**30,'Delivery storage budget exceeded')
    save(output/'delivery-manifest.json',{'status':'accepted_private_scientific_delivery','models':4006,'residues':234,
         'files':files,'private_source_evidence_sha256':source_hashes,'publication_held':True,
         'scope':'Accepted scientific supplements only;Pax atlas assembly/browser review and Zenodo package remain pending'})
    save(root/'X0-acceptance.json',{'status':'validated','manifest_sha256':sha(output/'delivery-manifest.json'),
         'files':len(files),'bytes':sum(r['bytes'] for r in files.values()),'publication_held':True})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['S0','S1','S2','S3','X0'])
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True);a=p.parse_args()
    plan=load(a.plan,a.plan_sha256);plan['_sha256']=a.plan_sha256;np,rows=initialize(plan,a.phase)
    {'S0':protocol,'S1':states,'S2':sample,'S3':acceptance,'X0':delivery}[a.phase](plan,np,rows)
if __name__=='__main__':main()
