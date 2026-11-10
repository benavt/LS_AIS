"""P2 revalidates the approved native cohort and saved artifacts; no fitting."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from execution_utils import *

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',required=True,type=Path);p.add_argument('--plan-sha256',required=True)
    a=p.parse_args();plan=load(a.plan,a.plan_sha256)
    import numpy as np
    from Bio.PDB import MMCIFParser,PDBParser
    from Bio.SeqUtils import seq1
    import shutil
    root=Path(plan['run_root']);data=Path(plan['data_root'])
    prior=read(data/'P1-acceptance.json')
    require(prior['status']=='passed' and prior['job_id']=='25462','P1 not accepted')
    finished(plan,'P1')
    roster=read(data/'native-models.json')['models'];inputs=read(data/'inputs.json')
    require(len(roster)==len({x['model_id'] for x in roster})==len({x['sha256'] for x in roster})==4006,'Changed native cohort')
    require([x['model_id'] for x in roster]==[x['model_id'] for x in inputs],'Changed scoring order')
    for item in read(data/'saved-files.json'):
        p=data/item['relative_path'];require(p.stat().st_size==item['bytes'],'Saved file size differs');checked(p,item['sha256'])
    for i,row in enumerate(inputs):
        p=Path(row['path']);require(p.stat().st_size==row['bytes'],'Native coordinate size differs');checked(p,row['sha256'])
        parser=MMCIFParser(QUIET=True) if p.suffix.lower() in ('.cif','.mmcif') else PDBParser(QUIET=True)
        models=list(parser.get_structure(row['model_id'],str(p)));require(len(models)==1,'Native conformer count differs')
        expected=row['chains'];m=models[0];require(set(c.id for c in m)==set(c['id'] for c in expected),'Native chains differ')
        for c in expected:
            residues=list(m[c['id']])
            require(len(residues)==117 and ''.join(seq1(x.resname) for x in residues)==c['sequence'],'Incomplete construct')
            require([r.id[1] for r in residues]==list(range(1,118)) and all(not r.id[2].strip() for r in residues),'Residue numbering differs')
            require(all('CA' in r and np.isfinite(r['CA'].coord).all() for r in residues),'Invalid C-alpha')
        if i%500==0:print('Validated native',i,flush=True)
    for row in read(data/'producer-files.json'):checked(row['path'],row['sha256'])
    for row in read(data/'saved-files.json'):
        if row['relative_path'].endswith('.bin'):
            values=np.fromfile(data/row['relative_path'],dtype='<f2')
            require(values.shape==(27261,) and np.isfinite(values).all() and np.all(values>=0),'Invalid saved full-dimer features')
    require(shutil.disk_usage(root).free>=50*2**30,'Free reserve exhausted')
    saved={'status':'validated','models':4006,'residues':234,'features':27261,'plan_sha256':a.plan_sha256,
           'model_ids':[x['model_id'] for x in inputs],'native_sha256':[x['sha256'] for x in inputs],
           'input_manifest_sha256':sha(data/'inputs.json'),'saved_files_sha256':sha(data/'saved-files.json'),
           'producer_files_sha256':sha(data/'producer-files.json'),'source_roster_sha256':plan['roster_sha256'],
           'new_fits':0,'native_coordinates_changed':False,'P1_finished_telemetry':'verified'}
    save(root/'02_design/P2-acceptance.json',saved)
    print('P2 accepted all4006 native identities and saved full-dimer features',flush=True)
if __name__=='__main__':main()
