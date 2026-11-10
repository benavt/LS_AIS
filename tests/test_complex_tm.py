from pathlib import Path
import hashlib,importlib.util,json,sys,tempfile,types,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/completion'))
# Pure pinned parsing/cache code, without running the native executable.
LIB=ROOT/'local/execution/2026-11-09_mimas-current4006-complete_002/P1-stage_003/source/library'
sys.path.insert(0,str(LIB))
from complex_tm import make_scorer,ARGUMENTS,VERSION
from execution_utils import sha
class ComplexProtocol(unittest.TestCase):
    def test_fixed_chain_arguments_complete_CA_and_cache_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);exe=root/'USalign';exe.write_text('synthetic test binary')
            records={}
            for name in ['a','b']:
                p=root/(name+'.cif');p.write_text(name)
                records[name]={'model':name,'path':str(p),'sha256':sha(p),'source_sha256':sha(p),
                   'canonical_positions':list(range(1,235)),'sequence_sha256':'0'*64}
            store=types.SimpleNamespace(canonical_record=lambda name:dict(records[name]))
            scorer=make_scorer(store,exe,root/'cache',2,sha(exe));calls=[]
            def run(command,**kwargs):
                calls.append(command);Path(command[-1]).write_text('0 0 1 0 0\n1 0 0 1 0\n2 0 0 0 1\n')
                return types.SimpleNamespace(stdout='Aligned length= 234, RMSD= 0\nTM-score=0.9 (normalized by average length)\n',stderr='')
            scorer.runner=run
            r=scorer.score('a','b')
            self.assertEqual(r['protocol']['version'],VERSION)
            self.assertEqual(r['score'],.9);self.assertEqual(scorer.actual_calls,2)
            self.assertEqual(calls[0][3:-2],list(ARGUMENTS))
            scorer.score('b','a');self.assertEqual(scorer.actual_calls,2)
            file=next((root/'cache').glob('*.json'))
            if file.name.endswith('.intent.json'):file=next(p for p in (root/'cache').glob('*.json') if not p.name.endswith('.intent.json'))
            value=json.loads(file.read_text());value['protocol']['arguments'][5]='1';file.write_text(json.dumps(value))
            with self.assertRaises(ValueError):scorer.score('a','b')
    def test_missing_chain_positions_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);exe=root/'USalign';exe.write_text('fake')
            scorer=make_scorer(None,exe,root/'cache',2,sha(exe))
            def run(command,**kwargs):
                Path(command[-1]).write_text('0 0 1 0 0\n1 0 0 1 0\n2 0 0 0 1\n')
                return types.SimpleNamespace(stdout='Aligned length= 117\nTM-score=1 (normalized by average length)\n',stderr='')
            scorer.runner=run
            with self.assertRaises(ValueError):scorer._direction({'model':'a','path':'a'},{'model':'b','path':'b'},root/'matrix')
if __name__=='__main__':unittest.main()
