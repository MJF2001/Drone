import unittest
from scenarios_stress import cases
from audit import environment_check


class StressSceneTests(unittest.TestCase):
    def test_full_factorial_histories_and_ledger(self):
        rows=list(cases())
        self.assertEqual(len(rows),96)
        self.assertEqual(len({s.name for s,m in rows}),96)
        self.assertEqual(len({m['history_group'] for s,m in rows}),24)
        for s,m in rows:
            self.assertIsNone(environment_check(s))
            published=set(map(tuple,m['published_targets']))
            blocked=set(map(tuple,m['obstacles']))
            deferred=set(map(tuple,m['deferred_targets']))
            self.assertEqual(deferred,(published-set(s.covered))&blocked)
            self.assertEqual(set(s.targets),published-deferred)
            self.assertLessEqual(len(s.targets-s.covered),12)
            self.assertNotIn(s.current,blocked)
            self.assertNotIn(s.base,blocked)

    def test_generation_is_deterministic(self):
        a=list(cases());b=list(cases())
        self.assertEqual(a,b)


if __name__=='__main__':
    unittest.main()
