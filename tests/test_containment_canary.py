"""Synthetic guard checks only; no scheduler, cgroups or scientific engine calls."""
import importlib.util
from pathlib import Path
import unittest

source = Path(__file__).resolve().parents[1] / 'scripts/completion/containment_canary.py'
spec = importlib.util.spec_from_file_location('containment_canary', source)
canary = importlib.util.module_from_spec(spec)
spec.loader.exec_module(canary)


class Containment(unittest.TestCase):
    def row(self, memory='max', pids='max', swap='max', cpuset='3'):
        return {'memory.max':memory,'pids.max':pids,'memory.swap.max':swap,'cpuset.cpus.effective':cpuset}

    def test_rejects_unlimited_task_and_machine_sized_parent(self):
        result = canary.evaluate([self.row(), self.row(str(1024*2**30),'1384119')], {3}, 1)
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['proceed_to_P1'])

    def test_accepts_finite_enforced_ancestor(self):
        result = canary.evaluate([self.row(), self.row(str(2*2**30),'64','0')], {3}, 1)
        self.assertEqual(result['status'], 'passed')
        self.assertFalse(result['ready_for_scientific_work'])

    def test_rejects_memory_only_or_missing_pids(self):
        for pids in ['max',None,'65']:
            with self.subTest(pids=pids):
                result = canary.evaluate([self.row(str(2*2**30),pids,'0')], {3}, 1)
                self.assertEqual(result['status'], 'blocked')

    def test_rejects_swap_and_cpu_escape(self):
        self.assertEqual(canary.evaluate([self.row(str(2*2**30),'64','1')],{3},1)['status'],'blocked')
        self.assertEqual(canary.evaluate([self.row(str(2*2**30),'64','0')],{4},1)['status'],'blocked')
        self.assertEqual(canary.evaluate([self.row(str(2*2**30),'64','0','3-4')],{3,4},1)['status'],'blocked')

    def test_one_allocated_core_may_include_two_smt_siblings(self):
        rows = [self.row(str(2*2**30),'64','0','7,55')]
        result = canary.evaluate(rows, {7,55}, 1, {7:(0,9),55:(0,9)})
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['affinity_physical_cores'], 1)

    def test_rejects_cpuset_escape_even_when_affinity_is_small(self):
        rows = [self.row(str(2*2**30),'64','0','1-4')]
        result = canary.evaluate(rows, {1}, 1, {i:(0,i) for i in range(1,5)})
        self.assertEqual(result['status'], 'blocked')

    def test_parses_cpu_ranges_and_retains_missing_limits(self):
        self.assertEqual(canary.cpus('1-3,7'), {1,2,3,7})
        self.assertIsNone(canary.finite_min([self.row()], 'memory.max'))
        with self.assertRaises(ValueError):canary.cpus('4-2')


if __name__ == '__main__':
    unittest.main()
