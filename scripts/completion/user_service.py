"""Job-owned transient user service; preserve Slurm placement and bounded lifetime.

Only the new service's limits are set. No shared unit, Slurm setting or other job
is changed. The native monitor runs inside the service as well as the outer
Fleet monitor. A launcher-identity watcher ends the service when its Slurm parent
vanishes, and systemd enforces a finite runtime and kills remaining descendants.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

PLAN_SHA = 'b887c9c362f8dad0cc6211f83d0a33208cd69e8d05faf23594b86cfa58a067b6'
MONITOR_SHA = '206e0891dd533f808955c347716ac90d98f9c505d2a680f134fc94ab5a0a823a'
STOP = False


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    with Path(path).open('x') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def parent_alive(snapshot, proc_root=Path('/proc')):
    try:
        proc = proc_root / str(snapshot['launcher_pid'])
        start = proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19]
        return (proc.stat().st_uid == os.getuid()
                and start == snapshot['launcher_start_ticks']
                and ('job_' + snapshot['job_id'] + '/') in proc.joinpath('cgroup').read_text() + '/')
    except (OSError, ValueError, KeyError, IndexError):
        return False


def preserved_environment(environment):
    keys = {'PATH', 'LD_LIBRARY_PATH', 'CUDA_VISIBLE_DEVICES', 'CUDA_DEVICE_ORDER',
            'SLURM_JOB_ID', 'SLURM_ARRAY_JOB_ID', 'SLURM_ARRAY_TASK_ID',
            'SLURM_JOB_GPUS', 'SLURM_STEP_GPUS', 'SLURM_GPUS_ON_NODE',
            'SLURM_CPUS_PER_TASK', 'SLURM_RESTART_COUNT', 'SLURM_MEM_PER_NODE',
            'SLURM_MEM_PER_CPU'}
    result = {k: v for k, v in environment.items() if k in keys}
    result.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', PYTHONNOUSERSITE='1')
    return result


def service_command(request_path, request, python, source):
    unit = request['unit']
    if not re.fullmatch(r'hsph1-[0-9]+-[a-z0-9-]+', unit):
        raise ValueError('Unsafe job-private unit')
    if not 0 < request['memory_bytes'] <= 64 * 2**30 or not 0 < request['tasks'] <= 64:
        raise ValueError('Resource envelope exceeded')
    if not 0 < request['runtime_seconds'] <= 43200:
        raise ValueError('Runtime envelope exceeded')
    affinity = sorted(request['allocation']['affinity'])
    if not affinity or any(type(x) is not int or x < 0 for x in affinity):
        raise ValueError('Invalid saved CPU affinity')
    argv = ['/usr/bin/systemd-run', '--user', '--quiet', '--wait', '--pipe', '--collect',
            '--service-type=exec', '--unit=' + unit,
            '--working-directory=' + request['cwd']]
    properties = {'MemoryMax':str(request['memory_bytes']), 'MemorySwapMax':'0',
                  'TasksMax':str(request['tasks']), 'CPUAffinity':' '.join(map(str,affinity)),
                  'RuntimeMaxSec':str(request['runtime_seconds']), 'TimeoutStopSec':'5',
                  'KillMode':'control-group', 'OOMPolicy':'kill', 'UMask':'0077',
                  'MemoryAccounting':'yes', 'TasksAccounting':'yes'}
    argv += ['--property=' + k + '=' + v for k, v in properties.items()]
    argv += ['--setenv=' + k + '=' + v for k,v in request['environment'].items()]
    monitor = Path(request['monitor']) / 'log_slurm_resources.py'
    return argv + [python, '-I', '-B', str(monitor), '--log-file', request['native_log'],
                   '--stage', 'whole-job-user-service', '--device', 'cpu', '--interval', '15',
                   '--', python, '-I', '-B', str(source), 'worker', '--request', str(request_path)]


def import_canary(path):
    spec = importlib.util.spec_from_file_location('_hsph1_canary', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(request_path):
    request = json.loads(request_path.read_text())
    if request['approved_plan_sha256'] != PLAN_SHA:
        raise ValueError('Foreign approved plan')
    for path, expected in request['source_hashes'].items():
        if sha(path) != expected:
            raise ValueError('Frozen source differs: ' + path)
    if not parent_alive(request['allocation']):
        raise ValueError('Original Slurm launcher is absent')
    canary = import_canary(request['canary'])
    rows = canary.collect_rows()
    if (canary.finite_min(rows, 'memory.max') != request['memory_bytes']
            or canary.finite_min(rows, 'pids.max') != request['tasks']
            or canary.finite_min(rows, 'memory.swap.max') != 0
            or os.sched_getaffinity(0) != set(request['allocation']['affinity'])):
        raise ValueError('Actual private service limits or CPU affinity differ')
    monitor = Path(request['monitor'])
    if sha(monitor/'manifest.json') != MONITOR_SHA:
        raise ValueError('Monitor manifest differs')
    for name, expected in json.loads((monitor/'manifest.json').read_text())['sha256'].items():
        if Path(name).name != name or sha(monitor/name) != expected:
            raise ValueError('Frozen monitor file differs')
    child = subprocess.Popen(request['command'], stdin=subprocess.DEVNULL, start_new_session=True)
    began = time.monotonic()
    stop_reason = None
    global STOP
    def stop(signum, frame):
        global STOP
        STOP = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while child.poll() is None:
        if STOP or not parent_alive(request['allocation']) or time.monotonic()-began >= request['runtime_seconds']-5:
            stop_reason = 'Slurm launcher ended, signal received, or runtime exhausted'
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=2)
            break
        time.sleep(.25)
    write_new(request['worker_result'], {'return_code':child.returncode,
              'stop_reason':stop_reason, 'parent_alive_at_exit':parent_alive(request['allocation']),
              'service_limits_verified':True, 'scientific_execution':False})
    return child.returncode if child.returncode is not None and child.returncode >= 0 else 125


def launch(output, command):
    job = os.environ.get('SLURM_JOB_ID', '')
    if not job.isdigit():
        raise ValueError('Launch only within the approved Slurm allocation')
    canary_path = Path(__file__).with_name('containment_canary.py')
    canary = import_canary(canary_path)
    rows = canary.collect_rows()
    cgroup = next(line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines()
                  if line.startswith('0::'))
    if ('job_' + job + '/') not in cgroup + '/':
        raise ValueError('Launcher is outside its original Slurm allocation')
    allocation = {'job_id':job, 'launcher_pid':os.getpid(),
                  'launcher_start_ticks':Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19],
                  'cgroup':cgroup, 'affinity':sorted(os.sched_getaffinity(0)),
                  'allocated_cpus':sorted(next(canary.cpus(row['cpuset.cpus.effective'])
                       for row in rows if row.get('cpuset.cpus.effective')))}
    output.mkdir(exist_ok=False)
    allocation_path = output/'allocation.json'
    write_new(allocation_path, allocation)
    command += ['--allocation-evidence',str(allocation_path),'--allocation-sha256',sha(allocation_path)]
    request = {'approved_plan_sha256':PLAN_SHA, 'unit':'hsph1-' + job + '-p0-repair',
               'allocation':allocation, 'memory_bytes':2*2**30, 'tasks':64,
               'runtime_seconds':540, 'cwd':str(output.parent), 'canary':str(canary_path),
               'environment':preserved_environment(os.environ),
               'monitor':'<private-monitor-path>',
               'source_hashes':{str(canary_path):sha(canary_path),str(Path(__file__).resolve()):sha(__file__)},
               'native_log':str(output/'native-resource.log'),
               'worker_result':str(output/'worker-result.json'), 'command':command}
    monitor = Path(request['monitor'])
    if sha(monitor/'manifest.json') != MONITOR_SHA:
        raise ValueError('Monitor manifest differs before service launch')
    for name, expected in json.loads((monitor/'manifest.json').read_text())['sha256'].items():
        if Path(name).name != name or sha(monitor/name) != expected:
            raise ValueError('Monitor differs before service launch')
    request_path = output/'request.json'
    write_new(request_path,request)
    env = os.environ.copy()
    env['XDG_RUNTIME_DIR']='/run/user/'+str(os.getuid())
    env['DBUS_SESSION_BUS_ADDRESS']='unix:path='+env['XDG_RUNTIME_DIR']+'/bus'
    argv = service_command(request_path,request,'/usr/bin/python3',Path(__file__).resolve())
    proc = subprocess.Popen(argv,stdin=subprocess.DEVNULL,env=env)
    def stop(signum,frame):
        subprocess.run(['/usr/bin/systemctl','--user','stop',request['unit']],env=env,timeout=10)
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    code = proc.wait()
    write_new(output/'launcher-result.json', {'return_code':code,'unit':request['unit'],
              'approved_plan_sha256':PLAN_SHA,'resource_model':'Slurm placement plus job-private delegated user service',
              'memory_bytes':request['memory_bytes'],'tasks':64,'swap_bytes':0})
    return code


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('launch');a.add_argument('--output',type=Path,required=True);a.add_argument('command',nargs=argparse.REMAINDER)
    a=sub.add_parser('worker');a.add_argument('--request',type=Path,required=True)
    a=p.parse_args()
    if a.mode=='worker':return worker(a.request)
    command=a.command[1:] if a.command[:1]==['--'] else a.command
    if not command:raise ValueError('Explicit frozen command is required')
    return launch(a.output,command)


if __name__=='__main__':raise SystemExit(main())
