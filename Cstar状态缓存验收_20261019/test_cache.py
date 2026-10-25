import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime'))
from history_adapter import HistoryCStar
from history_core.public_map import PublicMap
from history_core.planner import WallClockCap
def planner():
    m=PublicMap();m.update({(x,0):True for x in range(5)})
    return HistoryCStar((1,0),m,{(0,0),(4,0)},set())
class Cache(unittest.TestCase):
    def test_unchanged_hit_no_search(self):
        p=planner();before=dict(p.protection_cache_stats)
        with patch.object(p.graph,'path',side_effect=AssertionError('cache hit searched')):p.sync_task_protection()
        self.assertEqual(p.protection_cache_stats['hits'],before['hits']+1)
    def check_miss(self,mutate):
        p=planner();b=p.protection_cache_stats['rebuilds'];mutate(p);p.sync_task_protection()
        self.assertEqual(p.protection_cache_stats['rebuilds'],b+1)
        payload=(set(p.acquisition_anchors),set(p.transit_anchors),set(p.graph.task_protected))
        p._protection_cache=None;p.sync_task_protection()
        self.assertEqual(payload,(p.acquisition_anchors,p.transit_anchors,p.graph.task_protected))
    def test_current_invalidates(self):self.check_miss(lambda p:setattr(p,'current',(2,0)))
    def test_pending_invalidates(self):self.check_miss(lambda p:p.pending.remove((0,0)))
    def test_covered_invalidates(self):self.check_miss(lambda p:p.covered.add((0,0)))
    def test_map_version_invalidates(self):self.check_miss(lambda p:p.map.update({(8,8):False}))
    def test_edge_weight_invalidates(self):
        def change(p):p.graph.edges[(1,0)][(2,0)]=p.graph.edges[(2,0)][(1,0)]=2.0
        self.check_miss(change)
    def test_edge_removal_invalidates(self):self.check_miss(lambda p:p.graph.remove_edge((1,0),(2,0)))
    def test_new_node_invalidates(self):self.check_miss(lambda p:p.graph.insert((8,8),'link'))
    def test_payload_mutation_cannot_poison(self):
        p=planner();old=set(p.graph.task_protected);p.graph.task_protected.clear();p.acquisition_anchors.clear();p.sync_task_protection()
        self.assertEqual(p.graph.task_protected,old);self.assertTrue(p.acquisition_anchors)
    def test_hit_still_checks_deadline(self):
        p=planner();p.deadline=1;p._clock=lambda:1
        with self.assertRaises(WallClockCap):p.sync_task_protection()
if __name__=='__main__':unittest.main()
