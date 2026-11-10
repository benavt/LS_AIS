from pathlib import Path
import hashlib,importlib.util,sys,tempfile,unittest
from unittest.mock import patch
import numpy as np
from Bio.PDB import Atom,Residue,Chain,Model,PDBParser

SOURCE=Path(__file__).resolve().parents[1]/'scripts/completion'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('sampling_states_test',SOURCE/'states.py')
states=importlib.util.module_from_spec(spec);spec.loader.exec_module(states)

class SamplingPanelExport(unittest.TestCase):
    def fixture(self,folder):
        model=Model.Model(0)
        for ci,cid in enumerate('BC'):
            chain=Chain.Chain(cid);model.add(chain)
            for i in range(1,118):
                residue=Residue.Residue((' ',i,' '),'ALA',' ');chain.add(residue)
                residue.add(Atom.Atom('CA',np.asarray([i*.1,ci*20.,i*.2],dtype=np.float32),50.,1.,' ',' CA ',i,'C'))
        names=[f'model-{i:02d}' for i in range(50)]
        rows=[{'model_id':n,'sha256':hashlib.sha256(n.encode()).hexdigest(),'chains':[{'id':'B'},{'id':'C'}]} for n in names]
        cache=folder/'04_analysis/states/tm-cache';cache.mkdir(parents=True);(cache/'fixture.json').write_text('{}')
        rotation=np.asarray([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]);translation=np.asarray([7.,-3.,11.])
        poses={n:{'cache_key':'fixture','cache_sha256':hashlib.sha256(b'{}').hexdigest(),'rotation':rotation.tolist(),'translation':translation.tolist(),'anchor':names[0]} for n in names}
        return model,names,rows,poses,rotation,translation

    def test_exports_fifty_distinct_complete_dimers_with_one_global_pose(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);model,names,rows,poses,rotation,translation=self.fixture(folder)
            original=np.asarray([a.coord.copy() for a in model.get_atoms()]);output=folder/'panel.pdb'
            with patch.object(states,'native_structure',return_value=model):
                result=states.export_panel({'run_root':str(folder)},rows,names,poses,output,'MCMC50','S1')
            text=output.read_text();parsed=list(PDBParser(QUIET=True).get_structure('panel',output))
            self.assertEqual(len(parsed),50)
            self.assertEqual([m.serial_num for m in parsed],list(range(1,51)))
            self.assertEqual([line.removeprefix('REMARK 950 SAVED_MODEL ') for line in text.splitlines() if line.startswith('REMARK 950 SAVED_MODEL ')],names)
            self.assertEqual(text.splitlines().count('END'),1)
            for member in parsed:
                self.assertEqual([c.id for c in member],['A','B'])
                self.assertEqual([len(c) for c in member],[117,117])
                self.assertTrue(np.allclose(np.asarray([a.coord for a in member.get_atoms()]),original@rotation.T+translation,atol=.0006))
            self.assertTrue(np.array_equal(original,np.asarray([a.coord for a in model.get_atoms()])))
            self.assertEqual(result['model_ids'],names)
            self.assertEqual([m['native_sha256'] for m in result['members']],[r['sha256'] for r in rows])

    def test_rejects_wrong_cardinality_and_duplicate_originals(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);model,names,rows,poses,_,_=self.fixture(folder)
            for bad in [names[:-1],names[:-1]+[names[0]]]:
                with self.subTest(count=len(bad)),self.assertRaisesRegex(ValueError,'50 distinct originals'):
                    states.export_panel({'run_root':str(folder)},rows,bad,poses,folder/'bad.pdb','MCMC50','S1')

if __name__=='__main__':unittest.main()
