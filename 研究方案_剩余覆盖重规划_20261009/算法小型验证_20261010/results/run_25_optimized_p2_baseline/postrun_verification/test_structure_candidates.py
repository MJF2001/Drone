import unittest
from model import Snapshot,Geometry
from structure_candidates import metric_tree,preorder,solve_candidate
from audit import audit


class StructureTests(unittest.TestCase):
    def test_metric_tree_line(self):
        s=Snapshot('line',frozenset((x,0) for x in range(5)),frozenset(((2,0),(4,0))),frozenset(),(0,0),(0,0),(),0,30)
        children,edges=metric_tree(Geometry(s))
        self.assertEqual(len(edges),2)
        self.assertEqual(sum(e[2] for e in edges),4)
        self.assertEqual(set(preorder(children,s.current)),{s.current,(2,0),(4,0)})

    def test_all_candidates_cover_and_return_around_obstacle(self):
        free=frozenset((x,y) for x in range(5) for y in range(4))-{(2,1),(2,2)}
        targets=free-{(0,0),(0,1)}
        s=Snapshot('blocked',free,targets,frozenset(((1,0),)),(0,0),(0,0),(),0,100)
        for algorithm in ('P2_SHARED','STRIP_HV','TREE_MST'):
            result=solve_candidate(s,algorithm,2,123)
            self.assertTrue(result['audit']['valid'],result)
            self.assertTrue(audit(s,result['route'])['valid'])
            self.assertIsNotNone(result['detail']['common_length'])


if __name__=='__main__':
    unittest.main()
