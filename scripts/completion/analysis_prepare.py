"""Complete the pinned native Bonsai export runtime, offline in a new prefix."""
from pathlib import Path
import argparse,importlib.metadata,json,os,subprocess,sys,shutil
sys.path.insert(0,str(Path(__file__).resolve().parent))
from execution_utils import *

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--plan-sha256',required=True);p.add_argument('--fixtures',action='store_true')
    a=p.parse_args();plan=load(a.plan,a.plan_sha256);run=Path(plan['run_root']);prefix=Path(plan['analysis_prefix'])
    for name in ['TMPDIR','PIP_CACHE_DIR','MPLCONFIGDIR','XDG_CACHE_HOME','NUMBA_CACHE_DIR']:
        path=run/'runtime/R0-cache'/name.lower();path.mkdir(parents=True,exist_ok=True);os.environ[name]=str(path)
    os.environ.update(PIP_DISABLE_PIP_VERSION_CHECK='1',PIP_NO_INPUT='1',PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',
        NUMBA_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MPLBACKEND='Agg',BONSAI_ROOT=plan['bonsai_source'])
    if a.fixtures:
        require(sys.prefix==str(prefix),'Wrong isolated analysis runtime')
        versions={r['name']:importlib.metadata.version(r['name']) for r in plan['packages']}
        require(all(versions[r['name']]==r['version'] for r in plan['packages']),'Installed version mismatch')
        sys.path[:0]=[plan['library_source'],str(Path(plan['library_source'])/'scripts'),plan['bonsai_source']]
        import numpy,scipy,umap,sklearn.cluster,tables,natsort,numexpr,yaml,h5py,pandas,ruamel.yaml
        import bonsai_clustering
        from bonsai import bonsai_helpers,bonsai_treeHelpers,bonsai_dataprocessing
        from bonsai_scout import bonsai_scout_helpers,my_tree_layout
        from src.analysis import bonsai_interactive,cluster_medoid_tm,tm_state_geometry,tm_state_subset
        from src.analysis.bonsai_runtime import runtime_compatibility_metadata
        compatibility=runtime_compatibility_metadata(Path(plan['bonsai_source']))
        output=run/'runtime/R0-cache/HDF-fixture.h5'
        frame=pandas.DataFrame({'vertex':[0,1]},index=['a','b']);frame.to_hdf(output,key='cells',mode='w',format='table')
        require(pandas.read_hdf(output,key='cells').equals(frame),'Native PyTables roundtrip failed')
        paths={Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m,'__file__',None) and
               Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(prefix)}
        for line in Path('/proc/self/maps').read_text().splitlines():
            fields=line.split()
            if len(fields)>=6 and fields[-1].startswith('/'):
                path=Path(fields[-1])
                if path.is_file() and path.resolve().is_relative_to(prefix):paths.add(path.resolve())
        save(run/'runtime/analysis-environment.json',{'status':'validated','plan_sha256':a.plan_sha256,
            'versions':versions,'python_sha256':sha(sys.executable),'native_compatibility':compatibility,
            'runtime_sha256':{str(p):sha(p) for p in sorted(paths)},'target_models_processed':0})
        print('Complete analysis runtime and native HDF export imports accepted',flush=True);return
    finished(plan,'E5')
    marker=read(run/'04_analysis/E5-acceptance.json')
    require(marker['status']=='validated' and marker['plan_sha256']==plan['scoring_plan_sha256'],'Energy coverage prerequisite differs')
    require(not prefix.exists() and shutil.disk_usage(run).free>=50*2**30,'Use a fresh runtime with free reserve')
    for row in plan['packages']:checked(Path(row['wheelhouse'])/row['filename'],row['sha256'])
    checked(plan['base_python'],plan['base_python_sha256'])
    subprocess.run([plan['base_python'],'-I','-B','-m','venv','--copies',str(prefix)],check=True,timeout=300)
    python=str(prefix/'bin/python')
    argv=[python,'-I','-B','-m','pip','install','--no-index','--no-cache-dir','--only-binary=:all:','--require-hashes']
    for folder in sorted({r['wheelhouse'] for r in plan['packages']}):argv+=['--find-links',folder]
    argv+=['-r',plan['requirements']]
    subprocess.run(argv,check=True,timeout=1200)
    subprocess.run([python,'-I','-B','-m','pip','check'],check=True,timeout=30)
    subprocess.run([python,'-I','-B',str(Path(__file__).resolve()),'--plan',str(a.plan),'--plan-sha256',a.plan_sha256,'--fixtures'],check=True,timeout=1200)
    require(sum(p.stat().st_size for p in (run/'runtime').rglob('*') if p.is_file())<=8*2**30,'Runtime storage cap exceeded')
if __name__=='__main__':main()
