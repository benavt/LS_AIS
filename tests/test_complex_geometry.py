from pathlib import Path
import importlib.util,sys,tempfile,unittest
SOURCE=Path(__file__).resolve().parents[1]/'scripts/completion';sys.path.insert(0,str(SOURCE))
spec=importlib.util.spec_from_file_location('analysis_common_test',SOURCE/'analysis_common.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ComplexGeometry(unittest.TestCase):
    def test_preserves_two_complete_chains_and_coordinate_values(self):
        import numpy as np
        from Bio.PDB import Atom,Residue,Chain,Model,MMCIFParser
        model=Model.Model(0)
        for ci,chain_id in enumerate('BC'):
            chain=Chain.Chain(chain_id);model.add(chain)
            for i in range(1,118):
                r=Residue.Residue((' ',i,' '),'ALA',' ');chain.add(r)
                r.add(Atom.Atom('CA',np.asarray([i*.1234567,ci*20.1234567,i*.9876543],dtype=np.float32),50.,1.,' ',' CA ',i,'C'))
        row={'model_id':'synthetic','chains':[{'id':'B'},{'id':'C'}]}
        old=m.native_structure;m.native_structure=lambda _:model
        try:
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'complete.cif';count=m.canonical_full(row,path)
                actual=MMCIFParser(QUIET=True).get_structure('check',path)[0]
                self.assertEqual(count,234);self.assertEqual([c.id for c in actual],['A','B'])
                self.assertTrue(np.array_equal(np.asarray([r['CA'].coord for c in actual for r in c]),m.ca_array(row,model).astype(np.float32)))
                ca=Path(folder)/'ca.cif';m.write_ca(ca,'test',m.ca_array(row,model),'A'*117)
                reread=MMCIFParser(QUIET=True).get_structure('test',ca)[0]
                self.assertEqual(sum(len(c) for c in reread),234)
        finally:m.native_structure=old
if __name__=='__main__':unittest.main()
