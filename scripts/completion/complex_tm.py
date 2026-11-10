"""Fixed-chain full-dimer TMscore2 adaptation of the pinned native cache engine."""
from pathlib import Path
import hashlib,json,threading
from execution_utils import require,sha,save
from analysis_common import write_ca

ARGUMENTS=('-mol','prot','-ter','1','-TMscore','2','-a','T')
VERSION='canonical-A1-117-B1-117-TMscore2-bidirectional-v1'

class ComplexCAStore:
    def __init__(self,rows,coordinates,sequence,output):
        self.rows={r['model_id']:r for r in rows};self.order={r['model_id']:i for i,r in enumerate(rows)}
        self.coordinates=coordinates;self.sequence=sequence;self.output=Path(output);self.output.mkdir(parents=True,exist_ok=True)
        self._records={};self._lock=threading.RLock()
    def canonical_record(self,name):
        with self._lock:
            row=self.rows[name];require(sha(row['path'])==row['sha256'],'Original native coordinates changed')
            path=self.output/(name+'.cif')
            if name not in self._records:
                require(not path.exists(),'Use a fresh canonical CA store; no implicit recovery')
                write_ca(path,name,self.coordinates[self.order[name]],self.sequence)
                self._records[name]={'model':name,'path':str(path),'sha256':sha(path),'source_sha256':row['sha256'],
                    'canonical_positions':list(range(1,235)),'sequence_sha256':hashlib.sha256((self.sequence*2).encode()).hexdigest()}
            r=self._records[name];require(sha(path)==r['sha256'],'Canonical CA file changed')
            return dict(r)

def make_scorer(store,executable,output,budget,expected_sha):
    from src.analysis import tm_state_geometry as native
    class ComplexScorer(native.NativeTMScorer):
        def __init__(self):
            super().__init__(store,executable,output,budget,executable_sha256=expected_sha,timeout=180)
            self.protocol={'version':VERSION,'executable_sha256':expected_sha,'arguments':list(ARGUMENTS),
                'correspondence':'same canonical chain A/B and per-chain residue1-117;234 C-alpha positions',
                'normalization':'average length','aggregation':'mean of two directions',
                'native_matrix_formula':'y[i] = t[i] + sum_j u[i][j] * x[j]'}
            self.protocol_sha256=native.digest(self.protocol)
        def _direction(self,first,second,matrix_path):
            import subprocess,re
            self.check_cancel()
            require(not self.failed.is_set(),'Prior native failure')
            require(sha(self.executable)==self.protocol['executable_sha256'],'Native executable changed')
            command=[str(self.executable),first['path'],second['path'],*ARGUMENTS,'-m',str(matrix_path)]
            with self._lock:
                require(self.calls<self.maximum_directional_calls,'Native directional-call budget exhausted')
                self.calls+=1
            self.on_call(command)
            result=self.runner(command,capture_output=True,text=True,timeout=self.timeout,check=True)
            aligned=re.findall(r'Aligned length=\s*(\d+)',result.stdout)
            require(aligned==['234'],'Native positional comparison lost a chain or residue')
            text=Path(matrix_path).read_text()
            return {'source_model':first['model'],'target_model':second['model'],'score':native.parse_average_length_tm(result.stdout),
                'transform':native.parse_transform(text),'matrix_text':text,'matrix_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'stdout':result.stdout,'stdout_sha256':hashlib.sha256(result.stdout.encode()).hexdigest(),
                'stderr':result.stderr,'stderr_sha256':hashlib.sha256(result.stderr.encode()).hexdigest(),'command':command}
        def _validate_cached(self,value,key,fingerprint):
            require(value.get('key')==key and value.get('fingerprint')==fingerprint and value.get('protocol')==self.protocol,'Foreign complex TM cache')
            identities=fingerprint['original_and_canonical_sha256'];identical=identities[0][1]==identities[1][1]
            require(value.get('identical_canonical_input')==identical and value.get('native_calls')==(0 if identical else 2),'Wrong native-call evidence')
            for direction in ['forward','reverse']:
                row=value[direction]
                for raw,recorded in [('matrix_text','matrix_sha256'),('stdout','stdout_sha256'),('stderr','stderr_sha256')]:
                    require(hashlib.sha256(row[raw].encode()).hexdigest()==row[recorded],'Native evidence hash differs')
                require(native.parse_transform(row['matrix_text'])==row['transform'],'Native transform differs')
                parsed=1. if identical else native.parse_average_length_tm(row['stdout'])
                require(parsed==row['score'],'Native directional score differs')
                if not identical:require(len(row['command'])==13 and row['command'][3:-2]==list(ARGUMENTS) and row['command'][-2]=='-m','Wrong complex correspondence')
            require(value['score']==(value['forward']['score']+value['reverse']['score'])/2,'Invalid bidirectional mean')
            return value
    return ComplexScorer()
