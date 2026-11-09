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

    def test_parses_cpu_ranges_and_retains_missing_limits(self):
        self.assertEqual(canary.cpus('1-3,7'), {1,2,3,7})
        self.assertIsNone(canary.finite_min([self.row()], 'memory.max'))
        with self.assertRaises(ValueError):canary.cpus('4-2')


if __name__ == '__main__':
    unittest.main()
