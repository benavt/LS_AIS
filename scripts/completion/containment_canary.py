"""Read actual cgroup limits once; never change limits or start scientific work."""
from __future__ import annotations
import argparse
import datetime
import json
import os
from pathlib import Path

PLAN_SHA256 = 'b887c9c362f8dad0cc6211f83d0a33208cd69e8d05faf23594b86cfa58a067b6'
P0_MEMORY_BYTES = 2 * 2**30
P0_PIDS = 64


def cpus(value):
    result = set()
    for item in value.split(','):
        if not item.strip():
            continue
        fields = item.strip().split('-')
        if len(fields) == 1:
            result.add(int(fields[0]))
        elif len(fields) == 2:
            start, stop = map(int, fields)
            if stop < start or stop - start > 65536:
                raise ValueError('Invalid bounded CPU range')
            result.update(range(start, stop + 1))
        else:
            raise ValueError('Invalid CPU range')
    return result


def finite_min(rows, key):
    values = []
    for row in rows:
        value = row.get(key)
        if value is not None and value != 'max':
            number = int(value)
            if number < 0:
                raise ValueError('Negative cgroup limit')
            values.append(number)
    return min(values) if values else None


def core_count(cpu_set, core_ids):
    if core_ids is not None and cpu_set <= set(core_ids):
        return len({tuple(core_ids[cpu]) for cpu in cpu_set})
    return len(cpu_set)


def evaluate(rows, affinity, requested_cpus, core_ids=None):
    memory = finite_min(rows, 'memory.max')
    pids = finite_min(rows, 'pids.max')
    swap = finite_min(rows, 'memory.swap.max')
    allocation_cpus = next((cpus(row['cpuset.cpus.effective']) for row in rows
                            if row.get('cpuset.cpus.effective')), set())
    checks = {
        'memory_within_2GiB': memory is not None and 0 < memory <= P0_MEMORY_BYTES,
        'descendants_at_most64': pids is not None and 0 < pids <= P0_PIDS,
        'swap_zero': swap == 0,
        'one_CPU_requested': requested_cpus == 1,
        'CPU_affinity_bounded': bool(affinity) and core_count(affinity, core_ids) <= requested_cpus,
        'allocated_cores_bounded': bool(allocation_cpus) and core_count(allocation_cpus, core_ids) <= requested_cpus,
        'CPU_affinity_in_effective_cpuset': bool(allocation_cpus) and affinity <= allocation_cpus,
    }
    return dict(status='passed' if all(checks.values()) else 'blocked', checks=checks,
                effective_memory_max=memory, effective_pids_max=pids,
                effective_swap_max=swap, affinity=sorted(affinity),
                allocation_cpuset=sorted(allocation_cpus),
                affinity_physical_cores=core_count(affinity, core_ids),
                CPU_topology_available=core_ids is not None,
                proceed_to_P1=all(checks.values()), ready_for_scientific_work=False)


def collect_rows():
    unified = [line.split('::', 1)[1] for line in Path('/proc/self/cgroup').read_text().splitlines()
               if line.startswith('0::')]
    if len(unified) != 1:
        raise RuntimeError('Expected actual unified cgroup v2 membership')
    relative = Path(unified[0])
    if '..' in relative.parts:
        raise ValueError('Invalid cgroup membership')
    root = Path('/sys/fs/cgroup')
    current = root / str(relative).lstrip('/')
    rows = []
    while True:
        if len(rows) > 32:
            raise RuntimeError('Unexpected cgroup hierarchy depth')
        row = {'path': str(current)}
        for key in ['memory.max', 'memory.swap.max', 'pids.max', 'cpuset.cpus.effective']:
            file = current / key
            row[key] = file.read_text().strip() if file.exists() else None
        rows.append(row)
        if current == root:
            return rows
        if root not in current.parents:
            raise RuntimeError('Cgroup outside actual mount')
        current = current.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        parser.error('Run only inside the approved monitored P0 allocation')
    rows = collect_rows()
    affinity = os.sched_getaffinity(0)
    allocated = next((cpus(row['cpuset.cpus.effective']) for row in rows
                      if row.get('cpuset.cpus.effective')), set())
    core_ids = {}
    try:
        for cpu in affinity | allocated:
            topology = Path('/sys/devices/system/cpu') / ('cpu' + str(cpu)) / 'topology'
            core_ids[cpu] = [int((topology / name).read_text())
                             for name in ['physical_package_id', 'core_id']]
    except (OSError, ValueError):
        core_ids = None
    result = evaluate(rows, affinity, int(os.environ.get('SLURM_CPUS_PER_TASK', '0')), core_ids)
    result.update(stage='P0', approved_plan_sha256=PLAN_SHA256,
                  recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  job_id=os.environ['SLURM_JOB_ID'], node=os.uname().nodename,
                  cgroups=rows, scientific_execution=False, limit_mutations=False)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'status':result['status'], 'job_id':result['job_id'],
                      'checks':result['checks'], 'output':str(args.output)}), flush=True)
    return 0 if result['status'] == 'passed' else 42


if __name__ == '__main__':
    raise SystemExit(main())
