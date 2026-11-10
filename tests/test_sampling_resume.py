from pathlib import Path
import hashlib,json,sys,tempfile,unittest
from unittest.mock import patch
import numpy as np
SOURCE=Path(__file__).resolve().parents[1]/'scripts/completion';sys.path.insert(0,str(SOURCE))
from sampling_resume import restore_chains,copy_frozen_sampling
from states import json_value
from src.analysis import tm_state_subset as native

class SamplingResume(unittest.TestCase):
    def fixture(self,root):
        lp=np.log(np.arange(1,13,dtype=float));energies=np.linspace(-2,3,12)
        kwargs=dict(k=5,steps=30,burn=5,seed=17,energies=energies,labels=['g'+str(i//4) for i in range(12)],methods=['m'+str(i%2) for i in range(12)],noise_labels=('g2',))
        result=native.run_subset_chains(lp,chains=4,**kwargs)
        for i,chain in enumerate(result['chains']):
            arrays={k:v for k,v in chain.items() if isinstance(v,np.ndarray)}
            np.savez_compressed(root/f'chain-{i}.npz',**arrays)
            (root/f'chain-{i}.json').write_text(json.dumps(json_value({k:v for k,v in chain.items() if not isinstance(v,np.ndarray)})))
        return lp,kwargs,result

    def test_restores_native_production_panel_and_diagnostics_without_new_transitions(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);lp,kwargs,expected=self.fixture(folder)
            with patch.object(native,'subset_mh',side_effect=AssertionError('No new transition sampler allowed')):
                actual=restore_chains(folder,lp,**kwargs)
            self.assertTrue(np.array_equal(actual['production_indices'],expected['production_indices']))
            self.assertEqual(actual['transition_seeds'],expected['transition_seeds'])
            self.assertEqual(actual['restored_proposals'],120)
            self.assertEqual(json_value(actual['diagnostics']),json_value(expected['diagnostics']))
            for a,e in zip(actual['chains'],expected['chains']):
                for key,value in e.items():
                    if isinstance(value,np.ndarray):self.assertTrue(np.array_equal(a[key],value),key)

    def test_rejects_seed_mismatch(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);lp,kwargs,_=self.fixture(folder)
            p=folder/'chain-0.json';value=json.loads(p.read_text());value['seed']+=1;p.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'seed'):restore_chains(folder,lp,**kwargs)

    def test_frozen_copy_checks_all_hashes_before_copying(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'S1-states.json').write_text('{}');source=root/'sampling';source.mkdir()
            (source/'prior.json').write_text('original');output=root/'sampling_002';output.mkdir()
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            record={'source_states_sha256':sha(root/'S1-states.json'),'source_sampling_relative':'sampling',
                    'files':{'prior.json':{'sha256':sha(source/'prior.json'),'bytes':8}}}
            (source/'prior.json').write_text('changed!')
            with self.assertRaisesRegex(ValueError,'Frozen file differs'):copy_frozen_sampling(root,output,record)
            self.assertFalse(list(output.iterdir()))
            (source/'prior.json').write_text('original');copy_frozen_sampling(root,output,record)
            self.assertEqual((output/'prior.json').read_bytes(),(source/'prior.json').read_bytes())

if __name__=='__main__':unittest.main()
