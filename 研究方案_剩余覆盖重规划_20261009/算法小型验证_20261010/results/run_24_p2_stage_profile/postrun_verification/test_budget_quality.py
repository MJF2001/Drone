import unittest
from run_budget_quality import summarize


class BudgetSummaryTests(unittest.TestCase):
    def row(self,budget,length,algorithm='P2_SHARED'):
        return {'case':'a','algorithm':algorithm,'repeat':0,'budget':budget,
            'audit':None if length is None else {'valid':True,'length':length},
            'seconds':budget,'status':'timeout' if length is None else 'planned',
            'source':None if length is None else 'test'}

    def test_missing_route_is_failure_not_zero_cost_comparison(self):
        result=summarize([self.row(.1,None),self.row(.5,12),self.row(20.,10),self.row(20.,8,'STRIP_HV')])
        group=result['groups']['P2_SHARED@0.1']
        self.assertEqual(group['valid_complete_routes'],0)
        self.assertEqual(group['matched_to_pooled_reference'],0)
        self.assertEqual(result['same_method_same_seed_vs_20s']['P2_SHARED@0.1']['counts'],{'short_no_valid_route':1})
        self.assertEqual(result['same_method_same_seed_vs_20s']['P2_SHARED@0.5']['paired_step_difference_short_minus_20s'],2)
        self.assertEqual(result['pooled_feasible_reference']['a'],8)

    def test_shorter_budget_can_return_better_route_without_hiding_it(self):
        result=summarize([self.row(2.,9),self.row(20.,10)])
        self.assertEqual(result['same_method_same_seed_vs_20s']['P2_SHARED@2.0']['counts'],{'short_better':1})
        self.assertFalse(result['reference_is_proven_optimal'])


if __name__=='__main__':
    unittest.main()
