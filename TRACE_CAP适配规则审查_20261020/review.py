"""Bounded semantic review. No alternative algorithm search or road re-solving."""
import json,sys,hashlib,inspect,itertools
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'TRACE_CAP适配复现_20261020'
sys.path.insert(0,str(OLD));sys.path.insert(0,str(OLD/'runtime'))
from planners import solve
from primitives import Metric
from audit import audit
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
assert not (HERE/'protocol.json').exists(),'Do not overwrite a review run'
fixtures=[]
for method in ('CAP','TRACE'):
    for offset in (1,2):
        targets=[(x,0) for x in (offset,offset+1,offset+2,offset+4)]
        c=dict(name=f'{method}_line_offset{offset}',free=[(x,0) for x in range(offset+5)],targets=targets,covered=[],current=[0,0],base=[0,0],published_targets=targets,distance_budget=100)
        fixtures.append((method,c));save(HERE/'inputs'/(c['name']+'.json'),c)
sources={str(p.relative_to(OLD)):sha(p) for p in sorted((OLD/'runtime').glob('*.py'))}
sources.update({p:sha(OLD/p) for p in ('audit.py','sources/TRACE_2609.21777v1.txt','sources/CAP_2503.00647v1.txt','delivery_manifest.json')})
save(HERE/'protocol.json',dict(scope='public-map endpoint and entry pipeline review only',budget_seconds=5,planned_solver_calls=8,fixtures=[c['name'] for _,c in fixtures],method='one uninstrumented and one matrix-observed call per fixture; compare full semantics; exact permutations only for the fixed one-dimensional endpoint sensitivity example',no_road_rerun=True,no_ranking=True,sources=sources,review_script_sha256=sha(Path(__file__))))
checks=[]
original=Metric.matrix
for method,c in fixtures:
    r=solve(c,method,5,20261020);a=audit(c,r);assert r['status']=='complete'
    save(HERE/'results'/(c['name']+'__plain.json'),r)
    calls=[]
    def observed(self,terminals):
        frame=inspect.currentframe().f_back;before=self.rows
        value=original(self,terminals)
        calls.append(dict(caller_file=Path(frame.f_code.co_filename).name,caller_function=frame.f_code.co_name,caller_line=frame.f_lineno,terminals=terminals,terminal_count=len(terminals),bfs_rows=self.rows-before))
        return value
    Metric.matrix=observed
    try:s=solve(c,method,5,20261020)
    finally:Metric.matrix=original
    audit(c,s);assert s['status']=='complete';save(HERE/'results'/(c['name']+'__observed.json'),s)
    x=dict(r);y=dict(s);x.pop('seconds');y.pop('seconds');assert x==y
    save(HERE/'observations'/(c['name']+'.json'),calls)
    checks.append(dict(name=c['name'],method=method,plain=a,observed_semantics_identical=True,initial_endpoint=r['plans'][0]['end'],initial_endpoint_source=r['plans'][0]['end_source'],initial_tsp_start=r['plans'][0]['start'],first_region=r['plans'][0]['required'],initial_order=r['plans'][0]['order'],initial_executed_order=r['plans'][0]['executed_order'],matrix_calls=calls))
save(HERE/'micro_checks.json',checks)
# Exact finite illustration: change ONLY the first local fixed endpoint, keep
# current position, region order, all four targets and return base unchanged.
region=[(1,0),(2,0),(3,0)];start=(0,0);next_region=(5,0);base=(0,0)
dist=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
example=[]
for end in ((1,0),(3,0)):
    candidates=[]
    for mid in itertools.permutations([p for p in region if p!=end]):
        route=[start,*mid,end];local=sum(dist(a,b) for a,b in zip(route,route[1:]))
        candidates.append((local,route))
    cost,route=min(candidates)
    example.append(dict(endpoint=end,exact_local_cost=cost,exact_local_route=route,next_region=next_region,complete_cost_same_region_order=cost+dist(end,next_region)+dist(next_region,base)))
save(HERE/'endpoint_sensitivity_exact.json',dict(purpose='demonstrate adaptation choice affects routes, NOT choose an endpoint policy by performance',enumerated_orders=4,variants=example))
# Read-only accounting of all existing 80 saved roads; no new road solve.
road=[];counter={m:Counter() for m in ('TRACE','CAP')}
for p in sorted((OLD/'road_evidence/results').glob('*.json')):
    r=read(p);assert r['status']=='complete'
    for k,plan in enumerate(r['plans']):
        area=set(map(tuple,plan['required']));s=tuple(plan['start'])
        minimum=min(dist(s,v) for v in area)
        condition='inside' if minimum==0 else 'adjacent' if minimum==1 else 'nonadjacent'
        counter[r['method']][plan['end_source']]+=1;counter[r['method']]['entry_'+condition]+=1
        road.append(dict(result=p.name,method=r['method'],plan=k,source=plan['end_source'],entry_condition=condition,required_count=len(area),plan_start=plan['start'],end=plan['end']))
save(HERE/'saved_road_plan_review.json',road)
summary=dict(new_solver_calls=8,new_road_calls=0,micro_outputs_audited=8,observed_plain_semantic_pairs=4,saved_road_outputs_read_only=80,road_plan_counts={m:dict(c) for m,c in counter.items()},endpoint_sensitivity_exact=example,all_local_checks_pass=True)
save(HERE/'summary.json',summary)
for p,h in sources.items():assert sha(OLD/p)==h
print(json.dumps(summary,ensure_ascii=False,indent=2))
