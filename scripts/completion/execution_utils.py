"""Frozen project stage inputs and finished inner/outer producer verification."""
from pathlib import Path
import hashlib,json,os,subprocess

PLAN_SHA='b887c9c362f8dad0cc6211f83d0a33208cd69e8d05faf23594b86cfa58a067b6'
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4*1024**2),b''):h.update(b)
    return h.hexdigest()
def read(path):return json.loads(Path(path).read_text())
def checked(path,digest):require(sha(path)==digest,'Frozen file differs: '+str(path))
def save(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def load(path,digest):
    checked(path,digest);p=read(path)
    require(p['approved_plan_sha256']==PLAN_SHA,'Foreign approved scope')
    for name,value in p['source_sha256'].items():checked(name,value)
    return p
def log_check(log,monitor,gpu=False):
    checked(Path(monitor['runtime'])/'manifest.json',monitor['manifest_sha256'])
    for name,digest in read(Path(monitor['runtime'])/'manifest.json')['sha256'].items():
        require(Path(name).name==name,'Unsafe monitor member');checked(Path(monitor['runtime'])/name,digest)
    rows=[json.loads(x[11:]) for x in Path(log).read_text().splitlines() if x.startswith('[resource] {')]
    start=[x for x in rows if x.get('event')=='start'];exits=[x for x in rows if x.get('event')=='command_exit']
    require(len(start)==len(exits)==1 and exits[0]['exit_code']==0,'Producer native process failed')
    require(start[0]['device']==('mixed' if gpu else 'cpu'),'Producer monitoring device differs')
    argv=[monitor['python'],'-I','-B',str(Path(monitor['runtime'])/'check_log.py'),str(log),'--finished']
    if gpu:argv+=['--gpu']
    result=subprocess.run(argv,capture_output=True,text=True,timeout=45)
    require(result.returncode==0,'Incomplete producer log: '+result.stdout+result.stderr)
    return {'sha256':sha(log),'job_id':str(start[0]['job']),'array_task':start[0].get('array_task')}
def service_dir(plan,phase,index=None):
    if phase in plan.get('service_roots',{}):return Path(plan['service_roots'][phase])
    return Path(plan['run_root'])/'receipts'/(phase+'-user-service'+('' if index is None else '-'+str(index)))
def finished(plan,phase,index=None):
    attempt=Path(plan['attempts'][phase]);receipt=read(attempt/'submission-result.json')
    require(receipt['status']=='accepted' and receipt['scheduler_script_verified'],'Unverified producer submission')
    checked(attempt/'workload.sh',receipt['workload_sha256'])
    logs=[]
    for log in (attempt/'resources').glob('*.log'):
        starts=[json.loads(x[11:]) for x in log.read_text().splitlines() if x.startswith('[resource] {') and '"event": "start"' in x]
        if len(starts)==1 and str(starts[0].get('array_task'))==str(index):logs.append(log)
    require(len(logs)==1,'Require one non-requeued producer task log')
    gpu=phase in ('E1','E3')
    outer=log_check(logs[0],plan['monitor'],gpu)
    service=service_dir(plan,phase,index)
    worker=read(service/'worker-result.json');launcher=read(service/'launcher-result.json')
    require(worker['return_code']==launcher['return_code']==0 and worker['service_limits_verified']
            and worker['stop_reason'] is None,'Private native service failed')
    inner=log_check(service/'native-resource.log',plan['monitor'],gpu)
    require(inner['job_id']==outer['job_id'],'Inner/outer scheduler identity differs')
    return {'outer':outer,'inner':inner}
