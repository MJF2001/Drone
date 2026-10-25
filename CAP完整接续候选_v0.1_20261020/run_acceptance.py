import sys,json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H/'runtime'))
from candidate import solve
from audit import audit
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    protocol=read(H/'protocol.json')
    for f,h in protocol['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
    output=[]
    def run(name,c,expected='complete',**kw):
        r=solve(c,**kw)
        item=dict(name=name,input=c,result=r);output.append(item)
        (H/'micro.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
        item['check']=audit(c,r);assert r['status']==expected,(name,r['status'],r['error'])
        return r
    cells=[(x,y) for x in range(3) for y in range(2)]
    def case(targets,**extra):
        return dict(free=cells,targets=list(targets),covered=[],current=(0,0),base=(0,0),distance_budget=100,**extra)
    for mask in range(64):run('grid_subset_'+str(mask),case([p for k,p in enumerate(cells) if mask>>k&1]))
    c=case([(2,0),(2,1)],cap_resume_target=dict(point=(0,0),reference='synthetic_covered_external_interface'))
    run('external_resume',c)
    run('resource_prefix',dict(case([(2,1)]),distance_budget=0),expected='resource_exceeded')
    run('deferred',dict(case([(2,1)]),published_targets=[(2,1),(9,9)],deferred_targets=[(9,9)]))
    run('history',dict(case([(1,0),(2,0)]),covered=[(1,0)]))
    run('unreachable',dict(free=[(0,0),(2,0)],targets=[(2,0)],covered=[],current=(0,0),base=(0,0),distance_budget=100),expected='unreachable')
    # Discover observed checkpoints on a multi-region flow, then inject a single
    # deterministic deadline at each observed stage (no sleeps or timed luck).
    dc=case([(0,1),(2,0),(2,1)]);seen=[]
    run('deadline_discovery',dc,hook=lambda s:seen.append(s))
    for stage in sorted(set(seen)):
        class Clock:
            value=0
            def __call__(self):return self.value
        clock=Clock()
        def hook(s):
            if s==stage:clock.value=2
        run('deadline_'+stage,dc,expected='deadline',budget=1,clock=clock,hook=hook)
    (H/'micro.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8')
    # Gate: only after all preceding cases pass, execute each developer input
    # once for correctness, not a paired performance or superiority comparison.
    roads=[]
    for job in protocol['roads']:
        c=read(Path(job['input']));r=solve(c,budget=20);check=audit(c,r)
        roads.append(dict(case_id=job['case_id'],input=c,result=r,check=check))
        (H/'roads.json').write_text(json.dumps(roads,ensure_ascii=False,indent=2),encoding='utf-8')
        assert r['status']=='complete',(job['case_id'],r['status'],r['error'])
    print(json.dumps(dict(micro_calls=len(output),deadline_stages=len(set(seen)),road_calls=len(roads),road_complete=sum(x['result']['status']=='complete' for x in roads),performance_ranking_calls=0)))
if __name__=='__main__':main()
