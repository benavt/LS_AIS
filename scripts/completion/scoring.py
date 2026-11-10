"""Approved variable-cardinality native Model6 scoring for the current4006 cohort."""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,os,sys,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
from execution_utils import *

SETTINGS=dict(n_samples=16,t_min=0.0,t_max=0.15,batch_size=16,
 template_self_condition=True,inference_self_condition=False,ensemble_size=0,
 mask_sequence=False,score_norm_energy=False,primary_time_index=10,seed=215600,chunk_size=100)

def span(count,chunk):
    require(count in (1000,6) and type(chunk) is int and 0<=chunk<(count+99)//100,'Invalid scoring chunk')
    return chunk*100,min((chunk+1)*100,count)

def validate_grid(np,energy,partial,count):
    require(energy.shape==(16,count) and partial.shape==(16,count,234)
        and np.isfinite(energy).all() and np.isfinite(partial).all()
        and np.allclose(partial.sum(-1),energy,rtol=2e-6,atol=2e-5),'Invalid complete energy grid')

def group_dir(plan,index):
    require(type(index) is int and 0<=index<5,'Invalid scoring group')
    p=Path(plan['run_root'])/'02_design'/'ProteinEBM'/plan['groups'][index]['id']
    p.mkdir(parents=True,exist_ok=True);return p

def input_rows(plan,index):
    rows=read(Path(plan['data_root'])/'inputs.json');lookup={x['model_id']:x for x in rows}
    return [lookup[x] for x in plan['groups'][index]['model_ids']]

def native(plan,device):
    require(plan['settings']==SETTINGS,'Scoring settings differ')
    binding=plan['native']
    for name,digest in binding['files'].items():checked(Path(binding['native_source'])/name,digest)
    for name,digest in binding['runtime_identity'].items():checked(name,digest)
    checked(binding['checkpoint']['path'],binding['checkpoint']['sha256'])
    checked(binding['config']['path'],binding['config']['sha256'])
    folder=Path(plan['library_source'])/'scripts/proteinebm_complex'
    sys.path.insert(0,str(folder))
    spec=importlib.util.spec_from_file_location('_frozen_complex_worker',folder/'worker.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.SETTINGS==SETTINGS,'Pinned native recipe differs')
    np,torch,model,augment=module.native({'native_source':binding['native_source'],
        'checkpoint':binding['checkpoint'],'config':binding['config']},device)
    for name,module in list(sys.modules.items()):
        if name.startswith('protein_ebm.') and getattr(module,'__file__',None):
            require(Path(module.__file__).resolve().is_relative_to(Path(binding['native_source'])),'ProteinEBM import escaped frozen source')
    return np,torch,model,augment

def p2_ready(plan):
    finished(plan,'P2')
    marker=read(Path(plan['run_root'])/'02_design/P2-acceptance.json')
    require(marker['status']=='validated' and marker['models']==4006 and
       marker['plan_sha256']==plan['P2_plan_sha256'] and
       marker['input_manifest_sha256']==sha(Path(plan['data_root'])/'inputs.json'),'P2 cohort differs')
    return marker

def prepare(plan,digest,index):
    p2_ready(plan)
    require(not os.environ.get('SLURM_JOB_GPUS') and not os.environ.get('CUDA_VISIBLE_DEVICES'),'CPU preparation requires no GPU')
    np,torch,model,augment=native(plan,'cpu');del model
    from protein_ebm.data.protein_utils import residues_to_features,restypes
    from features import native_complex_features
    rows=input_rows(plan,index);count=len(rows);require(count==plan['groups'][index]['count'],'Group cardinality differs')
    atoms=[];aa=[];idx=[];chains=[]
    for row in rows:
        checked(row['path'],row['sha256'])
        positions,amino,indices,ce=native_complex_features(row['path'],row['chains'],residues_to_features)
        sequence=''.join(restypes[int(a)] for a in amino)
        require(sequence==plan['sequence']*2 and positions.shape==(234,3),'Native full-dimer features differ')
        atoms.append(positions);aa.append(amino);idx.append(indices);chains.append(torch.tensor(ce,dtype=torch.long))
    atoms,aa,idx,chains=map(torch.stack,(atoms,aa,idx,chains))
    torch.manual_seed(SETTINGS['seed']);np.random.seed(SETTINGS['seed'])
    times=torch.linspace(0.,.15,16)
    coords=torch.stack([augment(atoms,torch.ones((count,234))) for _ in times])
    arrays=dict(coords=coords.numpy(),aatype=aa.numpy(),idx=idx.numpy(),chain_ids=chains.numpy(),times=times.numpy())
    root=group_dir(plan,index);cache=root/'features.npz'
    with cache.open('xb') as stream:np.savez(stream,**arrays)
    with np.load(cache,allow_pickle=False) as actual:
        require(all(np.array_equal(v,actual[k]) for k,v in arrays.items()),'Lossy feature-cache roundtrip')
    save(root/'ready.json',{'status':'validated','models':count,'residues':234,'CPU_only':True,
       'plan_sha256':digest,'feature_sha256':sha(cache),'native_cpu_strict_load':True,
       'model_ids':[r['model_id'] for r in rows],'native_sha256':[r['sha256'] for r in rows]})
    print('CPU native cache accepted',plan['groups'][index]['id'],count,flush=True)

def ready(plan,digest,index):
    proof=finished(plan,'E0',index);root=group_dir(plan,index);marker=read(root/'ready.json')
    require(marker['status']=='validated' and marker['CPU_only'] and marker['native_cpu_strict_load'] and
        marker['plan_sha256']==digest and marker['models']==plan['groups'][index]['count'],'CPU cache not accepted')
    checked(root/'features.npz',marker['feature_sha256']);return root,proof

def gpu(plan,digest,index,chunk):
    count=plan['groups'][index]['count'];begin,end=span(count,chunk);n=end-begin
    root,proof=ready(plan,digest,index)
    if chunk:
        for group in range(5):finished(plan,'E2',group)
        marker=read(root/'pilot-gate.json');require(marker['status']=='validated' and marker['plan_sha256']==digest,'Pilot gate not accepted')
        checked(root/'chunk-00.npz',marker['pilot_sha256'])
    np,torch,model,_=native(plan,'cuda')
    torch.cuda.manual_seed_all(SETTINGS['seed']);start=time.monotonic()
    with np.load(root/'features.npz',allow_pickle=False) as f:cache={k:f[k] for k in f.files}
    aa=torch.from_numpy(cache['aatype'][begin:end]).cuda()
    idx=torch.from_numpy(cache['idx'][begin:end]).cuda()
    ce=torch.from_numpy(cache['chain_ids'][begin:end]).cuda()
    require(set(ce[0].tolist())=={0,1},'Chain encoding lost')
    with torch.no_grad():
        require(torch.equal(model.rel_pos(idx[:1],ce[:1]),model.rel_pos(idx[:1],1-ce[:1])),'Native pair features not chain-relabel invariant')
        energies=[];residues=[];calls=0
        for ti,t in enumerate(cache['times']):
            level=[];partial=[]
            for offset in range(0,n,16):
                stop=min(offset+16,n);size=stop-offset
                coords=torch.from_numpy(cache['coords'][ti,begin+offset:begin+stop]).cuda()
                a,indices,chain_ids=aa[offset:stop],idx[offset:stop],ce[offset:stop]
                mask=torch.ones(a.shape,device='cuda')
                result=model.compute_energy(dict(aatype=a,residue_idx=indices,mask=mask,
                    chain_encoding=chain_ids,external_contacts=torch.ones_like(a),
                    selfcond_coords=coords,r_noisy=coords,atom_mask=mask,
                    t=torch.full((size,),float(t),device='cuda')))
                values=result['energy'].cpu().numpy();per=result['per_residue_energy'].cpu().numpy()
                require(np.isfinite(values).all() and np.isfinite(per).all() and
                    np.allclose(per.sum(-1),values,rtol=2e-6,atol=2e-5),'Nonfinite/inconsistent native energy')
                level.append(values);partial.append(per);calls+=1
                require(torch.cuda.max_memory_allocated()<56*2**30,'GPU memory budget exceeded')
                del coords,result
            energies.append(np.concatenate(level));residues.append(np.concatenate(partial))
    energy=np.stack(energies);per=np.stack(residues);validate_grid(np,energy,per,n)
    output=root/f'chunk-{chunk:02d}.npz'
    with output.open('xb') as f:np.savez(f,energy=energy,per_residue_energy=per,times=cache['times'])
    save(output.with_suffix('.json'),{'status':'validated','plan_sha256':digest,'chunk':chunk,'models':n,
      'energies':16*n,'GPU_native_batch_calls':calls,'output_sha256':sha(output),
      'chain_relabel_pair_features_exact':True,'CPU_resource_evidence':proof,
      'seconds':time.monotonic()-start,'peak_gpu_bytes':torch.cuda.max_memory_allocated()})
    print('Native GPU chunk accepted',index,chunk,n,calls,flush=True)

def gate(plan,digest,index):
    evidence=finished(plan,'E1',index);root=group_dir(plan,index)
    import numpy as np
    result=read(root/'chunk-00.json');count=min(100,plan['groups'][index]['count'])
    require(result['status']=='validated' and result['models']==count and result['plan_sha256']==digest
       and result['chain_relabel_pair_features_exact'],'Counted pilot failed')
    checked(root/'chunk-00.npz',result['output_sha256'])
    with np.load(root/'chunk-00.npz',allow_pickle=False) as f:validate_grid(np,f['energy'],f['per_residue_energy'],count)
    save(root/'pilot-gate.json',{'status':'validated','models':count,'plan_sha256':digest,
      'pilot_sha256':sha(root/'chunk-00.npz'),'finished_resource_evidence':evidence})

def accept(plan,digest,index):
    import numpy as np
    root=group_dir(plan,index);count=plan['groups'][index]['count']
    evidence={'prepare':finished(plan,'E0',index),'pilot':finished(plan,'E1',index),'gate':finished(plan,'E2',index)}
    if index<4:evidence['production']=[finished(plan,'E3',index*9+i) for i in range(9)]
    energies=[];hashes=[];calls=0
    for chunk in range((count+99)//100):
        begin,end=span(count,chunk);output=root/f'chunk-{chunk:02d}.npz';r=read(output.with_suffix('.json'))
        require(r['status']=='validated' and r['plan_sha256']==digest and r['chunk']==chunk and r['models']==end-begin,'Wrong chunk')
        checked(output,r['output_sha256'])
        with np.load(output,allow_pickle=False) as f:
            validate_grid(np,f['energy'],f['per_residue_energy'],end-begin)
            require(np.allclose(f['times'],np.linspace(0,.15,16),atol=2e-8,rtol=0),'Changed score levels')
            energies.append(f['energy'].copy())
        hashes.append(sha(output));calls+=r['GPU_native_batch_calls']
    values=np.concatenate(energies,axis=1);rows=input_rows(plan,index)
    output=root/'energy-rankings.csv'
    with output.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['model_id','method','sha256','energy_t010']+[f'energy_t{j:02d}' for j in range(16)])
        writer.writeheader()
        for i,row in enumerate(rows):writer.writerow(dict(model_id=row['model_id'],method=row['method'],sha256=row['sha256'],
            energy_t010=float(values[10,i]),**{f'energy_t{j:02d}':float(values[j,i]) for j in range(16)}))
    save(root/'acceptance.json',{'status':'validated','models':count,'energies':16*count,'plan_sha256':digest,
       'csv_sha256':sha(output),'chunk_sha256':hashes,'resource_evidence':evidence,'GPU_native_batch_calls':calls})

def join(plan,digest):
    import numpy as np
    all_rows=[];calls=0;evidence=[]
    for index in range(5):
        evidence.append(finished(plan,'E4',index));root=group_dir(plan,index);r=read(root/'acceptance.json')
        require(r['status']=='validated' and r['plan_sha256']==digest,'Wrong accepted scoring identity')
        checked(root/'energy-rankings.csv',r['csv_sha256'])
        with (root/'energy-rankings.csv').open() as f:all_rows.extend(csv.DictReader(f))
        calls+=r['GPU_native_batch_calls']
    original=read(Path(plan['data_root'])/'inputs.json');lookup={r['model_id']:r for r in all_rows}
    require(len(all_rows)==len(lookup)==len(original)==4006 and set(lookup)=={r['model_id'] for r in original},'Incomplete score coverage')
    values=np.asarray([[float(lookup[r['model_id']][f'energy_t{j:02d}']) for j in range(16)] for r in original])
    require(values.shape==(4006,16) and np.isfinite(values).all() and calls==4496,'Grid or native-call budget differs')
    rows=[]
    for i,r in enumerate(original):
        row=lookup[r['model_id']];require(row['sha256']==r['sha256'] and row['method']==r['method'],'Score source identity differs')
        rows.append(dict(row,rank_t010=1+int((values[:,10]<values[i,10]).sum())))
    root=Path(plan['run_root'])/'04_analysis';root.mkdir(exist_ok=True)
    output=root/'current4006-energy-rankings.csv'
    with output.open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with (root/'current4006-energy-grid.npz').open('xb') as f:np.savez(f,energy=values,model_ids=np.asarray([r['model_id'] for r in original]),times=np.linspace(0,.15,16))
    save(root/'E5-acceptance.json',{'status':'validated','models':4006,'energies':64096,'per_residue_values':14998464,
        'GPU_native_batch_calls':calls,'plan_sha256':digest,'csv_sha256':sha(output),
        'grid_sha256':sha(root/'current4006-energy-grid.npz'),'resource_evidence':evidence,
        'units':'Arbitrary learned units;not binding energies','primary_time_index':10,'residues':234,
        'input_manifest_sha256':sha(Path(plan['data_root'])/'inputs.json')})

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=['E0','E1','E2','E3','E4','E5'])
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True)
    a=p.parse_args();plan=load(a.plan,a.plan_sha256)
    require(plan['settings']==SETTINGS,'Settings differ from approved Model6 recipe')
    task=int(os.environ['SLURM_ARRAY_TASK_ID']) if a.phase!='E5' else None
    if a.phase=='E0':prepare(plan,a.plan_sha256,task)
    elif a.phase=='E1':gpu(plan,a.plan_sha256,task,0)
    elif a.phase=='E2':gate(plan,a.plan_sha256,task)
    elif a.phase=='E3':
        require(0<=task<36,'Invalid production task');gpu(plan,a.plan_sha256,task//9,task%9+1)
    elif a.phase=='E4':accept(plan,a.plan_sha256,task)
    else:join(plan,a.plan_sha256)
if __name__=='__main__':main()
