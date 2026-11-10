from pathlib import Path
import importlib.util,sys,unittest
SOURCE=Path(__file__).resolve().parents[1]/'scripts/completion'
sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('scoring',SOURCE/'scoring.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ScoringContract(unittest.TestCase):
    def test_six_models_never_padded_or_repeated(self):
        self.assertEqual(m.span(6,0),(0,6))
        with self.assertRaises(ValueError):m.span(6,1)
        self.assertEqual([m.span(1000,i) for i in range(10)],[(i*100,(i+1)*100) for i in range(10)])
        with self.assertRaises(ValueError):m.span(1001,0)
    def test_exact_approved_native_call_count(self):
        calls=4*10*16*((100+15)//16)+16*((6+15)//16)
        self.assertEqual(calls,4496)
        self.assertEqual(4006*16*234,14998464)
    def test_incomplete_nonfinite_and_inconsistent_grids_rejected(self):
        import numpy as np
        e=np.ones((16,6));r=np.full((16,6,234),1/234)
        m.validate_grid(np,e,r,6)
        for energy,partial in [(e[:,:5],r),(e,np.zeros_like(r)),(e,np.full_like(r,np.nan))]:
            with self.subTest(shape=energy.shape),self.assertRaises(ValueError):m.validate_grid(np,energy,partial,6)
if __name__=='__main__':unittest.main()
