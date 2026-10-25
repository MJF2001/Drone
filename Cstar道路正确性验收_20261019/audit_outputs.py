"""Independent route/task/prune checks; no exponential exact-grid search."""
import sys,json
from pathlib import Path
from audit_inputs import pts,legal
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3'))
from audit_special import ledger,prune_checks,hole_checks
def audit(c,r,budget):
    ledger(c,r)
    accepted=r['status']=='task_complete'
    if accepted:
        route=r['route'];legal(c['free'],route)
        assert route[0]==c['current'] and route[-1]==c['base']
        assert pts(c['targets'])<=pts(c['covered'])|pts(route)
        assert len(route)-1<=c['distance_budget']
        assert 0<=r['seconds']<budget
        assert not r['pending'] and not r['completion_tsp']
        hole_checks(c,r)
    else:assert not r['route']
    completed,interrupted=prune_checks(r,accepted)
    return dict(accepted=accepted,status=r['status'],seconds=r['seconds'],steps=len(r['route'])-1 if accepted else None,completed_prunes=completed,interrupted_prunes=interrupted)
