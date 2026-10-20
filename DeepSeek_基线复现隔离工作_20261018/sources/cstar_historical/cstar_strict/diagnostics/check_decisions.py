"""Read-only baseline decision audit. Does not modify the C* implementation.

Independent Dijkstra checks A* costs. Held-Karp checks small fixed-endpoint
TSP instances; its oracle is restricted to exactly the supplied known graph.
This is a consistency audit, not a proof of paper-equivalent graph generation.
"""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import heapq
import json
import math
import hashlib
import planner
from geometry import World
from run import scenarios


def dijkstra(edges,start):
    costs={start:0.};queue=[(0.,start)]
    while queue:
        g,p=heapq.heappop(queue)
        if g>costs[p]+1e-9:
            continue
        for q,w in edges[p].items():
            ng=g+w
            if ng<costs.get(q,math.inf)-1e-9:
                costs[q]=ng;heapq.heappush(queue,(ng,q))
    return costs


def exact_tsp(points,start,end,cost):
    nodes=sorted(set(points)-{start}-({end} if end is not None else set()))
    if not nodes:
        return 0. if end is None else cost[start,end]
    dp={(1<<j,j):cost[start,p] for j,p in enumerate(nodes)}
    full=(1<<len(nodes))-1
    for mask in range(1,full+1):
        for j in range(len(nodes)):
            if (mask,j) not in dp:
                continue
            for k in range(len(nodes)):
                if not mask>>k&1:
                    key=(mask|1<<k,k)
                    value=dp[mask,j]+cost[nodes[j],nodes[k]]
                    dp[key]=min(dp.get(key,math.inf),value)
    return min(dp[full,j]+(0. if end is None else cost[p,end])
               for j,p in enumerate(nodes))


def main():
    records=[];active={}
    original=planner.optimize_tsp
    class AuditedCStar(planner.CStar):
        def select_goal(self):
            result=super().select_goal()
            goal,route,retreat=result
            if retreat:
                distances=dijkstra(self.graph.edges,self.current)
                candidates=sorted(self.retreat-{self.current})
                best=min(distances[q] for q in candidates)
                assert abs(distances[goal]-best)<1e-8
                assert abs(sum(self.graph.edges[a][b] for a,b in zip(route,route[1:]))-best)<1e-8
                records.append(dict(type='retreat',**active['case'],current=self.current,
                    goal=goal,candidate_count=len(candidates),nearest_cost=best,
                    independent_dijkstra_agrees=True))
            return result
        def cover_holes(self,holes,goal):
            active['graph']=self.graph
            return super().cover_holes(holes,goal)
    def audit_tsp(points,start,end,cost):
        graph=active['graph']
        for a in points:
            distances=dijkstra(graph.edges,a)
            assert all(abs(cost[a,b]-distances[b])<1e-8 for b in points)
        order,before,after=original(points,start,end,cost)
        assert set(order)==set(points) and order[0]==start
        assert end is None or order[-1]==end
        assert after<=before+1e-8
        exact=exact_tsp(points,start,end,cost) if len(points)<=14 else None
        if exact is not None:
            assert after>=exact-1e-8
        records.append(dict(type='tsp',**active['case'],targets=len(points),start=start,end=end,
            nn_cost=before,two_opt_cost=after,exact_cost=exact,
            gap=None if exact is None else max(0.,after-exact),
            independent_dijkstra_agrees=True))
        return order,before,after
    planner.optimize_tsp=audit_tsp
    statuses=[]
    try:
        for seed in range(3):
            for name,free,start,_,_ in scenarios(seed):
                if seed and name!='clutter':
                    continue
                for holes in (True,False):
                    active['case']=dict(map=name,seed=seed,holes=holes)
                    p=AuditedCStar(start,World(free,5).observe,seed=seed,holes=holes).run()
                    assert p.status=='graph_exhausted',getattr(p,'error',p.status)
                    statuses.append(dict(**active['case'],status=p.status))
    finally:
        planner.optimize_tsp=original
    small=[r for r in records if r['type']=='tsp' and r['exact_cost'] is not None]
    summary=dict(runs=len(statuses),retreats=sum(r['type']=='retreat' for r in records),
                 tsp_events=sum(r['type']=='tsp' for r in records),
                 exact_tsp_checked=len(small),exact_tsp_positive_gaps=sum(r['gap']>1e-8 for r in small))
    output=dict(summary=summary,scope='Decision consistency only; no global inefficiency attribution.',
                source_sha256={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest()
                               for n in ('planner.py','geometry.py','rcg.py')},
                runs=statuses,decisions=records)
    (Path(__file__).parent/'decision_audit.json').write_text(json.dumps(output,indent=2),encoding='utf8')
    print(json.dumps(summary))


if __name__=='__main__':
    main()
