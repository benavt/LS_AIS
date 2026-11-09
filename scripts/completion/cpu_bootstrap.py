"""P1: offline, hash-locked CPU environment and synthetic source validation only."""
from __future__ import annotations
import argparse
import ast
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

PLAN_SHA = 'b887c9c362f8dad0cc6211f83d0a33208cd69e8d05faf23594b86cfa58a067b6'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(4*1024**2), b''):
            h.update(block)
    return h.hexdigest()

def write_new(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')

def verify_files(root, files):
    for relative, row in files.items():
        p = Path(relative)
        if p.is_absolute() or '..' in p.parts or not (root/p).is_file() or (root/p).is_symlink():
            raise ValueError('Unsafe or absent frozen file: ' + relative)
        if (root/p).stat().st_size != row['bytes'] or sha(root/p) != row['sha256']:
            raise ValueError('Frozen file differs: ' + relative)

def fixture(plan, directory):
    import importlib.util
    import numpy as np
    import scipy
    import sklearn
    import umap
    import numba
    import h5py
    import pandas
    import plotly
    from sklearn.cluster import HDBSCAN
    root = Path(plan['stage_directory'])
    sys.path[:0] = [str(root/'source/library'), str(root/'source/bonsai')]
    from src.analysis.ensemble_sampling import energy_distribution
    from src.analysis.tm_state_subset import exact_subset_draw, inclusion_probabilities
    from src.analysis.complex_ensemble import chain_sequence
    from bonsai import bonsai_helpers, bonsai_treeHelpers, bonsai_dataprocessing
    density_path = root/'source/extensions/hd_density_experiment.py'
    spec = importlib.util.spec_from_file_location('src.analysis.hd_density_experiment',density_path)
    density = importlib.util.module_from_spec(spec);spec.loader.exec_module(density)
    assert density.named_children(np.array([1,1,-1,0]), ['a','b','c','d'],'C')[0] == ['C.1','C.1','C.unassigned','C.2']
    for p in (root/'source').rglob('*.py'):
        ast.parse(p.read_bytes(), filename=str(p))
    versions = {r['name']: importlib.metadata.version(r['name']) for r in plan['packages']}
    assert all(versions[r['name']] == r['version'] for r in plan['packages'])
    assert sys.prefix == plan['environment_prefix'] and sys.base_prefix != sys.prefix
    random = np.random.default_rng(8)
    x = np.vstack([random.normal(0,.01,(16,4)),random.normal(5,.01,(16,4))]).astype(np.float32)
    labels = HDBSCAN(min_cluster_size=5,min_samples=3,n_jobs=1).fit_predict(x)
    assert set(labels) == {0,1}
    embedding = umap.UMAP(n_components=2,n_neighbors=5,min_dist=0,init='random',
                          n_epochs=10,random_state=42,n_jobs=1).fit_transform(x)
    assert embedding.shape == (32,2) and np.isfinite(embedding).all()
    assert numba.get_num_threads() == 1
    d = energy_distribution(np.array([1.,2.,3.,4.]), ['a','a','b','noise'],.5,1.,noise_labels=['noise'])
    assert np.isclose(np.asarray(d['probabilities']).sum(),1)
    weights = np.log(np.array([1.,2.,3.,4.]))
    chosen = exact_subset_draw(weights,k=2,seed=1)
    assert len(set(map(int,chosen))) == 2
    marginals = inclusion_probabilities(weights,k=2)
    assert np.isclose(np.asarray(marginals).sum(),2)
    native = subprocess.run([str(root/'bin/USalign'),'-h'],text=True,capture_output=True,timeout=20)
    if '-TMscore' not in native.stdout + native.stderr:
        raise ValueError('Pinned native USalign help unavailable')
    write_new(directory/'fixtures.json', {'status':'passed','scope':'synthetic only; no target models',
        'versions':versions,'python':sys.version,'python_sha256':sha(sys.executable),
        'density_helper_import':True,'Bonsai_core_imports':True,'USalign_help':True,
        'UMAP_shape':[32,2],'HDBSCAN_synthetic_groups':2,
        'fixed_cardinality_sampler':True,'numeric_threads':1,
        'scientific_target_models_processed':0})

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--plan-sha256',required=True)
    p.add_argument('--fixtures',action='store_true')
    a=p.parse_args()
    if sha(a.plan) != a.plan_sha256:
        raise ValueError('Exact P1 execution plan differs')
    plan=json.loads(a.plan.read_text())
    assert plan['approved_plan_sha256']==PLAN_SHA and plan['stage']=='P1'
    stage=Path(plan['stage_directory']);run=Path(plan['run_root'])
    prefix=Path(plan['environment_prefix']);result=Path(plan['result_directory'])
    assert stage.is_relative_to(run/'01_staging') and prefix==run/'runtime/cpu' and result.is_relative_to(run/'receipts')
    for name in ('PIP_CACHE_DIR','TMPDIR','NUMBA_CACHE_DIR','MPLCONFIGDIR','XDG_CACHE_HOME'):
        os.environ[name]=str(run/'runtime/cache'/name.lower())
        Path(os.environ[name]).mkdir(parents=True,exist_ok=True)
    os.environ.update(PIP_DISABLE_PIP_VERSION_CHECK='1',PIP_NO_INPUT='1',PYTHONNOUSERSITE='1',
        NUMBA_NUM_THREADS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        NUMEXPR_NUM_THREADS='1',MPLBACKEND='Agg')
    verify_files(stage,plan['files'])
    if a.fixtures:
        fixture(plan,result)
        return
    if prefix.exists() or result.exists():
        raise ValueError('Preserve earlier attempt; prefix and result must be new')
    assert shutil.disk_usage(run).free>=50*2**30
    assert sha(plan['base_python'])==plan['base_python_sha256']
    previous=json.loads((stage/'P0-acceptance.json').read_text())
    assert previous['status']=='passed' and previous['job_id']=='25458'
    result.mkdir(parents=True)
    subprocess.run([plan['base_python'],'-I','-B','-m','venv','--copies',str(prefix)],check=True,timeout=300)
    python=str(prefix/'bin/python')
    subprocess.run([python,'-I','-B','-m','pip','install','--no-index','--no-cache-dir',
        '--find-links',str(stage/'wheelhouse'),'--only-binary=:all:','--require-hashes',
        '-r',str(stage/'cpu-requirements.lock')],check=True,timeout=900)
    subprocess.run([python,'-I','-B','-m','pip','check'],check=True,timeout=30)
    subprocess.run([python,'-I','-B',str(stage/'cpu_bootstrap.py'),'--plan',str(a.plan),
        '--plan-sha256',a.plan_sha256,'--fixtures'],check=True,timeout=1800)
    actual=sum(f.stat().st_size for f in (run/'runtime').rglob('*') if f.is_file())
    assert actual <= 8*2**30 and shutil.disk_usage(run).free>=50*2**30
    write_new(result/'acceptance.json', {'status':'passed','stage':'P1',
        'approved_plan_sha256':PLAN_SHA,'execution_plan_sha256':a.plan_sha256,
        'environment_prefix':str(prefix),'environment_bytes':actual,
        'packages':len(plan['packages']),'CPU_only':True,
        'monitor_finished_check':'required externally before P2',
        'scientific_target_models_processed':0})
    print(json.dumps({'status':'P1_environment_and_synthetic_fixtures_passed','packages':len(plan['packages'])}))

if __name__=='__main__':
    main()
