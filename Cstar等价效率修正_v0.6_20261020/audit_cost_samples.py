"""Separate bounded oracle check AFTER timing batch, no full planner calls."""
import hashlib,json,math,random,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'runtime'))
from history_core.rcg import RCG,Node
from history_core.public_map import PublicMap
from history_core.planner import optimize_tsp,WallClockCap
from equivalent_tsp import CertifiedCosts,optimize_equivalent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def graph(snapshot):
    g=RCG(PublicMap());g.nodes={tuple(n[:2]):Node(n[2]) for n in snapshot['nodes']};g.edges={p:{} for p in g.nodes}
    for a,b in snapshot['edges']:
        a,b=tuple(a),tuple(b);g.edges[a][b]=g.edges[b][a]=math.hypot(a[0]-b[0],a[1]-b[1])
    return g
def main():
    assert (HERE/'road_summary.json').exists();out=HERE/'cost_oracle';out.mkdir(exist_ok=True)
    assert not (out/'protocol.json').exists(),'no retries'
    protocol=read(HERE/'protocol.json')
    for f,h in protocol['sources'].items():assert sha(HERE/f)==h
    jobs=[j for j in protocol['jobs'] if j['kind']=='road' and j['seed']==20261018]
    files=[HERE/'evidence/results'/(j['run_id']+'.json') for j in jobs]
    save(out/'protocol.json',dict(solver_calls=0,states=20,seed=20261018,per_state='first prepared TSP event only, execution may be interrupted; up to48 unique deterministic pairs, canonical original A* oracle for first3 NN decisions (all remaining challengers)',
        sources=protocol['sources'],outputs={str(p):sha(p) for p in files},
        additional='nonlattice triangle full matrix/tour, long-edge lattice fixture, 3 direct utility deadline probes at tsp_2opt_resolve',timing=False))
    rows=[]
    for job,rp in zip(jobs,files):
        r=read(rp)['result'];events=[e for e in r['events'] if e['type']=='tsp']
        if not events:rows.append(dict(case=job['name'],skipped='no prepared TSP event'));continue
        e=events[0];g=graph(e['graph_before_tour']);points=sorted(map(tuple,e['dense_nodes']));cost=CertifiedCosts(g,points,lambda _:None)
        pairs={(points[0],points[0]),(points[0],points[-1])};rng=random.Random(20261018)
        while len(pairs)<min(48,len(points)*(len(points)+1)//2):pairs.add(tuple(sorted(rng.sample(points,2))))
        maxerr=0.
        for a,b in sorted(pairs):
            path,value=g.path(a,b);error=abs(value-cost.approx(a,b));assert error<=cost.error(a,b);maxerr=max(maxerr,error)
            assert cost.value(a,b)==value and cost.path(a,b)==path
        start=tuple(e['start']);end=tuple(e['end']) if e['end'] is not None else None
        remaining=set(points)-{start}
        if end is not None:remaining.discard(end)
        current=start;nn=[];queries=0
        for _ in range(min(3,len(remaining))):
            exact={}
            for q in sorted(remaining):
                a,b=sorted((current,q));_,exact[q]=g.path(a,b);queries+=1
            expected=min(remaining,key=lambda q:(exact[q],q));actual=cost.nearest(current,remaining);assert expected==actual
            nn.append(actual);remaining.remove(actual);current=actual
        rows.append(dict(case=job['name'],nodes=len(g.nodes),points=len(points),pairs=len(pairs),max_error=maxerr,nn_choices=nn,nn_oracle_queries=queries,tight=cost.tight))
    # Valid Euclidean graph outside native unit-diagonal lattice: loose bound.
    fixtures=[[(0,0),(1,2),(4,0),(4,3)],[(0,0),(0,1000000),(1,1000000),(1,999999),(2,999999)]]
    extras=[]
    for pts in fixtures:
        g=RCG(PublicMap());g.nodes={p:Node() for p in pts};g.edges={p:{} for p in pts}
        for a in pts:
            for b in pts:
                if a!=b:g.edges[a][b]=math.hypot(a[0]-b[0],a[1]-b[1])
        old={}
        for a in sorted(pts):
            for b in sorted(pts):
                if (a,b) not in old:_,v=g.path(a,b);old[a,b]=old[b,a]=v
        c=CertifiedCosts(g,set(pts),lambda _:None)
        assert optimize_tsp(set(pts),pts[0],None,old)==optimize_equivalent(set(pts),pts[0],None,c,lambda _:None)
        for a in pts:
            for b in pts:assert abs(old[a,b]-c.approx(a,b))<=c.error(a,b)
        extras.append(dict(points=len(pts),tight=c.tight,stats=c.stats))
    deadlines=[]
    # Force the documented conservative fallback so the normally dormant
    # exact 2-opt comparison checkpoint is tested, not pretended covered by
    # the main 75 synthetic full-planner tests.
    for relation,t in [('before',2-1e-6),('equal',2.),('after',2+1e-6)]:
        g=graph(read(files[0])['result']['events'][0]['graph_before_tour'])
        points=sorted(g.nodes)[:4];state={'time':0.,'hit':False}
        def check(stage):
            if stage=='tsp_2opt_resolve':state.update(time=t,hit=True)
            if state['time']>=2:raise WallClockCap('direct utility deadline')
        c=CertifiedCosts(g,points,check);c.tight=False;c.bound=1e6
        try:c.improves([points[0],points[1],points[2],points[3]],1,2);status='returned'
        except WallClockCap:status='deadline'
        assert state['hit'];assert status==('returned' if relation=='before' else 'deadline')
        deadlines.append(dict(relation=relation,status=status))
    save(out/'checks.json',dict(rows=rows,extras=extras,utility_deadlines=deadlines,solver_calls=0,pass_all=True))
    print('oracle PASS',len(rows),'states',sum(x.get('pairs',0) for x in rows),'pairs',sum(x.get('nn_oracle_queries',0) for x in rows),'NN queries')
if __name__=='__main__':main()
