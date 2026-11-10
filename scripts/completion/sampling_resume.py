"""Restore hash-bound saved transitions without drawing new MH proposals."""
from pathlib import Path
from execution_utils import checked,require,read,sha

def copy_frozen_sampling(root,output,record):
    require(sha(root/'S1-states.json')==record['source_states_sha256'],'Resume states differ')
    source=root/record['source_sampling_relative']
    require(source.resolve().is_relative_to(root.resolve()) and source!=output,'Invalid resume source')
    require(sum(r['bytes'] for r in record['files'].values())<=2*2**20,'Resume snapshot exceeds bounded scope')
    for relative,row in record['files'].items():
        path=Path(relative)
        require(not path.is_absolute() and '..' not in path.parts,'Unsafe resume member')
        checked(source/path,row['sha256']);require((source/path).stat().st_size==row['bytes'],'Resume size differs')
    for relative,row in record['files'].items():
        destination=output/relative;destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('xb') as f:f.write((source/relative).read_bytes())
        checked(destination,row['sha256'])

def restore_chains(folder,log_weights,*,k,steps,burn,seed,energies,labels,methods,noise_labels=()):
    import numpy as np
    from src.analysis.tm_state_subset import LAW,proposal_probabilities,replay_subsets
    from src.analysis.ensemble_sampling import chain_diagnostics
    n=len(log_weights);actual=0 if n==k else steps
    require(n>=k and 0<=burn<steps,'Resume panel or burn scope differs')
    e=np.asarray(energies);ranking=np.argsort(e,kind='stable');groups=sorted(set(labels));method_keys=sorted(set(methods))
    group_codes=np.asarray([groups.index(x) for x in labels]);method_codes=np.asarray([method_keys.index(x) for x in methods])
    noise=np.isin(np.asarray(labels,dtype=object),list(noise_labels));runs=[]
    for ci in range(4):
        chain=read(folder/f'chain-{ci}.json')
        with np.load(folder/f'chain-{ci}.npz',allow_pickle=False) as arrays:
            require(not set(chain)&set(arrays.files),'Overlapping saved chain fields')
            chain.update({name:arrays[name].copy() for name in arrays.files})
        for name,value in {'law':LAW,'k':k,'model_count':n,'requested_steps':steps,'proposals':actual,
                           'seed':seed+1000+ci,'rng_algorithm':'PCG64','uniform_mixture':.1,
                           'group_keys':groups,'method_keys':method_keys}.items():
            require(chain[name]==value,'Saved chain metadata differs: '+name)
        if ci==0:initial=ranking[:k]
        elif ci==1:initial=ranking[-k:]
        elif ci==2:initial=np.linspace(0,n-1,k,dtype=np.int64)
        elif n==k:initial=np.arange(n)
        else:initial=np.random.Generator(np.random.PCG64(seed+100+ci)).choice(n,size=k,replace=False)
        require(np.array_equal(chain['initial'],np.sort(initial)),'Saved initial subset differs')
        require(np.allclose(chain['proposal_probabilities'],proposal_probabilities(log_weights,k,.1),rtol=0,atol=1e-13),'Saved proposal law differs')
        for name,shape in {'panel_log_weight':(actual,),'panel_mean_energy':(actual,),
                           'group_counts':(actual,len(groups)),'method_counts':(actual,len(method_keys)),
                           'noise_counts':(actual,),'log_acceptance_ratio':(actual,)}.items():
            require(chain[name].shape==shape and np.isfinite(chain[name]).all(),'Saved trace shape/values differ: '+name)
        replayed=0
        for t,panel in enumerate(replay_subsets(chain)):
            replayed+=1
            require(np.isclose(chain['panel_mean_energy'][t],np.mean(e[panel]),rtol=0,atol=1e-10),'Saved energy trace differs')
            require(np.array_equal(chain['group_counts'][t],np.bincount(group_codes[panel],minlength=len(groups))) and
                    np.array_equal(chain['method_counts'][t],np.bincount(method_codes[panel],minlength=len(method_keys))) and
                    chain['noise_counts'][t]==noise[panel].sum(),'Saved count trace differs')
        require(replayed==actual,'Saved replay count differs');runs.append(chain)
    def diagnostic(values):
        if actual==0:return {'status':'unavailable_single_subset','rhat':None,'ess_bulk':None,'ess_tail':None}
        return chain_diagnostics(values)
    stacked=lambda name:np.stack([r[name][burn:] for r in runs])
    counts=stacked('group_counts');meth=stacked('method_counts')
    diagnostics={'panel_log_weight':diagnostic(stacked('panel_log_weight')),'noise_count':diagnostic(stacked('noise_counts')),
                 'group_counts':{label:diagnostic(counts[:,:,j]) for j,label in enumerate(groups)},
                 'method_counts':{label:diagnostic(meth[:,:,j]) for j,label in enumerate(method_keys)},
                 'panel_mean_energy':diagnostic(stacked('panel_mean_energy'))}
    return {'law':LAW,'chains':runs,'production_indices':runs[0]['final'].copy(),
            'transition_seeds':[seed+1000+i for i in range(4)],'diagnostics':diagnostics,
            'restored_proposals':sum(r['proposals'] for r in runs)}
