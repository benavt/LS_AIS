import importlib.util
from pathlib import Path
import tempfile
import unittest
import os

p=Path(__file__).resolve().parents[1]/'scripts/completion/user_service.py'
spec=importlib.util.spec_from_file_location('user_service',p)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class UserService(unittest.TestCase):
    def request(self):
        return {'unit':'hsph1-123-p0-repair','memory_bytes':2*2**30,'tasks':64,
                'runtime_seconds':540,'allocation':{'affinity':[7,55]},
                'cwd':'/tmp/private','environment':{'SLURM_JOB_ID':'123'},
                'monitor':'/tmp/monitor','native_log':'/tmp/resource.log'}
    def test_exact_private_limits_and_cpu_affinity(self):
        argv=module.service_command(Path('/tmp/request'),self.request(),'/usr/bin/python3',Path('/tmp/source'))
        for option in ['--property=MemoryMax=2147483648','--property=MemorySwapMax=0','--property=TasksMax=64',
                       '--property=CPUAffinity=7 55','--property=RuntimeMaxSec=540','--property=KillMode=control-group']:
            self.assertIn(option,argv)
        self.assertIn('--user',argv);self.assertIn('--wait',argv)
        self.assertLess(argv.index('/tmp/monitor/log_slurm_resources.py'),argv.index('/tmp/source'))
    def test_rejects_shared_or_unbounded_units(self):
        for key,value in [('unit','user.slice'),('memory_bytes',0),('tasks',65),('runtime_seconds',0)]:
            d=self.request();d[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                module.service_command(Path('/tmp/r'),d,'/usr/bin/python3',Path('/tmp/s'))
    def test_environment_excludes_native_hooks_and_credentials(self):
        d=module.preserved_environment({'SLURM_JOB_ID':'123','PYTHONPATH':'hook','FLEET_MASK_RECIPE':'x',
                                         'API_TOKEN':'secret','CUDA_VISIBLE_DEVICES':'0'})
        self.assertEqual(d['SLURM_JOB_ID'],'123');self.assertEqual(d['CUDA_VISIBLE_DEVICES'],'0')
        self.assertNotIn('PYTHONPATH',d);self.assertNotIn('FLEET_MASK_RECIPE',d);self.assertNotIn('API_TOKEN',d)
    def test_parent_pid_reuse_and_wrong_job_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);proc=root/'10';proc.mkdir()
            fields=['S']+['0']*18+['77'];(proc/'stat').write_text('10 (name) '+' '.join(fields))
            (proc/'cgroup').write_text('0::/slurm/job_123/step_batch')
            s={'launcher_pid':10,'launcher_start_ticks':'77','job_id':'123'}
            self.assertTrue(module.parent_alive(s,root))
            self.assertFalse(module.parent_alive({**s,'launcher_start_ticks':'88'},root))
            self.assertFalse(module.parent_alive({**s,'job_id':'456'},root))

if __name__=='__main__':unittest.main()
