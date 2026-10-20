"""Common exact metric and query-order-independent connector policy, not novelty."""
from bfs_metric_geometry import BFSMetricGeometry
from model import Geometry


class UnifiedGeometry(BFSMetricGeometry):
    def path(self, a, b):
        self.check_time()
        if (a,b) not in self.cache:
            # Same endpoints always select the same shortest-path geometry,
            # irrespective of which algorithm queried a distance first.
            lo,hi=sorted((a,b))
            Geometry.path(self,lo,hi)
        return self.cache[a,b]


def single_cell_audit(s, route):
    """Linear single-cell validator; historical independent auditor is retained."""
    if s.radius != 0:
        raise ValueError('single-cell only')
    errors=[]
    if not route:
        return {'valid':False,'errors':['empty_route'],'length':None}
    if route[0]!=s.current:errors.append('wrong_start')
    if route[-1]!=s.base:errors.append('missing_return')
    if not set(route)<=s.free:errors.append('collision_or_out_of_bounds')
    if any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(route,route[1:])):
        errors.append('illegal_step')
    if s.targets-s.covered-set(route):errors.append('coverage_omission')
    if len(route)-1>s.distance_budget:errors.append('distance_budget_exceeded')
    return {'valid':not errors,'errors':errors,'length':len(route)-1}
