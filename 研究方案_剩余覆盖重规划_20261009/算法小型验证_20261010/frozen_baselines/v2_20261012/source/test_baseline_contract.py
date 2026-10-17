import unittest
from dataclasses import replace
from model import Snapshot
from audit import audit
from baseline_suite import solve,METHODS

class ContractTests(unittest.TestCase):
    def test_empty_targets_valid_return_and_illegal_return(self):
        s=Snapshot('empty',frozenset({(0,0),(1,0)}),frozenset(),frozenset(),(1,0),(0,0),(),0)
        a=audit(s,((1,0),(0,0)))
        self.assertTrue(a['valid']);self.assertEqual(a['coverage_fraction'],1)
        self.assertFalse(audit(s,((1,0),))['valid'])
        for m in METHODS:
            r=solve(s,set(),m,.5,0,{'monotone_seconds':[.01]})
            self.assertTrue(r['independent_audit']['valid']);self.assertGreaterEqual(r['seconds'],0)
    def test_blocked_targets_are_not_silently_dropped(self):
        s=Snapshot('bad',frozenset({(0,0)}),frozenset({(1,0)}),frozenset(),(0,0),(0,0),(),0)
        for m in METHODS:
            with self.assertRaises(ValueError):solve(s,{(1,0)},m,.5,0,{})

if __name__=='__main__':unittest.main()
