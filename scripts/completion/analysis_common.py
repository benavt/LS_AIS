"""Full-dimer geometry, original identities and accepted saved-energy access."""
from pathlib import Path
import csv,hashlib,os,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from execution_utils import *

def initialize(plan,phase):
    root=Path(plan['run_root'])
    for key in ['NUMBA_CACHE_DIR','MPLCONFIGDIR','XDG_CACHE_HOME','TMPDIR']:
        path=root/'runtime/phase-cache'/phase/key.lower();path.mkdir(parents=True,exist_ok=True);os.environ[key]=str(path)
    os.environ.update(PYTHONDONTWRITEBYTECODE='1',NUMBA_NUM_THREADS='1',OMP_NUM_THREADS='1',
       OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',MPLBACKEND='Agg',
       BONSAI_ROOT=plan['bonsai_source'])
    sys.path[:0]=[plan['library_source'],str(Path(plan['library_source'])/'scripts')]
    import numpy as np
    runtime=read(root/'runtime/analysis-environment.json')
    require(runtime['status']=='validated' and runtime['plan_sha256']==plan['runtime_plan_sha256'],'Analysis runtime not accepted')
    require(sys.prefix==plan['analysis_prefix'],'Wrong analysis interpreter')
    for name,digest in runtime['runtime_sha256'].items():checked(name,digest)
    rows=read(Path(plan['data_root'])/'inputs.json')
    require(len(rows)==4006 and len({r['model_id'] for r in rows})==4006,'Changed analysis cohort')
    return np,rows

def saved_path(plan,relative):
    return Path(plan['data_root'])/'saved'/relative

def terminal(plan):
    return read(saved_path(plan,plan['workflow_relative']))['terminal_detection']

def features(plan,names,dtype):
    import numpy as np
    records=read(Path(plan['data_root'])/'saved-files.json')
    lookup={Path(r['relative_path']).stem:r for r in records if r['relative_path'].endswith('.bin')}
    require(len(lookup)==4006,'Missing saved features')
    arrays=[]
    for name in names:
        record=lookup[name];p=Path(plan['data_root'])/record['relative_path'];checked(p,record['sha256'])
        array=np.fromfile(p,dtype='<f2');require(array.shape==(27261,) and np.isfinite(array).all(),'Invalid complete features')
        arrays.append(array)
    return np.asarray(arrays,dtype=dtype)

def energies(plan):
    import numpy as np
    finished(plan,'E5')
    root=Path(plan['run_root'])/'04_analysis';marker=read(root/'E5-acceptance.json')
    require(marker['status']=='validated' and marker['plan_sha256']==plan['scoring_plan_sha256'] and
       marker['models']==4006 and marker['energies']==64096,'Unaccepted energy coverage')
    checked(root/'current4006-energy-grid.npz',marker['grid_sha256'])
    with np.load(root/'current4006-energy-grid.npz',allow_pickle=False) as f:
        names=f['model_ids'].tolist();e=f['energy'][:,10].copy()
    rows=read(Path(plan['data_root'])/'inputs.json')
    require(names==[r['model_id'] for r in rows] and np.isfinite(e).all(),'Energy identities differ')
    return e

def native_structure(row):
    from Bio.PDB import MMCIFParser,PDBParser
    p=Path(row['path']);checked(p,row['sha256'])
    return (MMCIFParser(QUIET=True) if p.suffix.lower() in ('.cif','.mmcif') else PDBParser(QUIET=True)).get_structure(row['model_id'],str(p))[0]

def ca_array(row,model=None):
    import numpy as np
    model=native_structure(row) if model is None else model
    a=np.asarray([r['CA'].coord for c in row['chains'] for r in model[c['id']]],dtype=np.float64)
    require(a.shape==(234,3) and np.isfinite(a).all(),'Incomplete dimer coordinates')
    return a

def canonical_full(row,output):
    """Native atom values preserved as float32-roundtripping CIF numbers."""
    from Bio.PDB import MMCIFIO
    model=native_structure(row)
    keys=['group_PDB','id','type_symbol','label_atom_id','label_alt_id','label_comp_id','label_asym_id',
          'label_entity_id','label_seq_id','pdbx_PDB_ins_code','Cartn_x','Cartn_y','Cartn_z','occupancy','B_iso_or_equiv',
          'auth_seq_id','auth_asym_id','pdbx_PDB_model_num']
    data={'data_':row['model_id'],**{'_atom_site.'+k:[] for k in keys}};count=0
    for ci,c in enumerate(row['chains']):
        chain='AB'[ci]
        for ri,res in enumerate(model[c['id']],1):
            for atom in res.get_unpacked_list():
                count+=1
                vals=['ATOM',str(count),atom.element,atom.name,atom.altloc.strip() or '.',res.resname,chain,str(ci+1),
                  str(ri),'?',*[format(float(v),'.9g') for v in atom.coord],str(atom.occupancy),str(atom.bfactor),str(ri),chain,'1']
                for key,value in zip(keys,vals):data['_atom_site.'+key].append(value)
    writer=MMCIFIO();writer.set_dict(data);writer.save(str(output))
    return count

def write_ca(path,name,coords,sequence):
    import numpy as np
    from Bio.SeqUtils import seq3
    a=np.asarray(coords,dtype=np.float64);require(a.shape==(234,3) and np.isfinite(a).all(),'Invalid canonical dimer')
    with Path(path).open('x') as f:
        f.write('data_'+name+'\n#\nloop_\n')
        for k in ['group_PDB','id','type_symbol','label_atom_id','label_alt_id','label_comp_id','label_asym_id','label_entity_id',
                  'label_seq_id','pdbx_PDB_ins_code','Cartn_x','Cartn_y','Cartn_z','occupancy','B_iso_or_equiv','auth_seq_id','auth_asym_id','pdbx_PDB_model_num']:
            f.write('_atom_site.'+k+'\n')
        for i,xyz in enumerate(a):
            chain='AB'[i//117];res=i%117+1
            f.write('ATOM %d C CA . %s %s %d %d ? %.17g %.17g %.17g 1 0 %d %s 1\n'%(
                i+1,seq3(sequence[i%117]).upper(),chain,i//117+1,res,*xyz,res,chain))
        f.write('#\n')
