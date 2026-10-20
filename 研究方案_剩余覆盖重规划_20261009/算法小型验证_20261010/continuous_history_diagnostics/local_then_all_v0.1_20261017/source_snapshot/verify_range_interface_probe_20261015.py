"""Independent tiny-splice audits and exact cost via BFS metric + Held-Karp DP."""
from pathlib import Path
from collections import deque
from types import SimpleNamespace
import hashlib,importlib.util,json,argparse
ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
SOURCE=ALGO/'development_range_probes/v0.1_20261015'
OUT=ALGO/'development_range_probes/v0.1_20261015_verification'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def ps(c,k):return set(map(tuple,c[k]))
def metric(free,start):
    q=deque([start]);ds={start:0}
    while q:
        x,y=q.popleft()
        for p in ((x,y+1),(x+1,y),(x,y-1),(x-1,y)):
            if p in free and p not in ds:ds[p]=ds[(x,y)]+1;q.append(p)
    return ds
def optimum(free,required,start,end):
    points=sorted(required-{start,end});sources={p:metric(free,p) for p in [start]+points}
    if end not in sources[start] or any(p not in sources[start] for p in points):return None
    if not points:return sources[start][end]
    n=len(points);dp={(1<<i,i):sources[start][p] for i,p in enumerate(points)}
    for mask in range(1,1<<n):
        for i in range(n):
            if (mask,i) not in dp:continue
            for j in range(n):
                if mask>>j&1:continue
                state=(mask|1<<j,j);value=dp[(mask,i)]+sources[points[i]][points[j]]
                if value<dp.get(state,float('inf')):dp[state]=value
    return min(dp[((1<<n)-1,i)]+sources[p][end] for i,p in enumerate(points))

def main(source,out):
    assert all(sha(source/n)==h for n,h in read(source/'sha256.json').items())
    protocol=read(source/'protocol.json');assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    spec=importlib.util.spec_from_file_location('_range_audit',ALGO/'frozen_baselines/v2_20261012/source/audit.py')
    auditor=importlib.util.module_from_spec(spec);spec.loader.exec_module(auditor)
    rows=read(source/'results.json');assert len(rows)==15
    assert len({(r['case'],r['scope']) for r in rows})==15
    verified=[];lookup={};counts={'valid_routes':0,'scope_collision_rejections':0,'exact_cost_checks':0}
    for row in rows:
        c=read(source/'cases'/(row['case']+'.json'));r=row['result'];info=r['scope_info'];m=c['metadata']
        free=ps(c,'free');targets=ps(c,'targets');covered=ps(c,'covered');initial=ps(m,'initial_targets')
        old=tuple(map(tuple,c['old_route']));current=tuple(c['current']);base=tuple(c['base'])
        assert targets==ps(m,'published_targets')-ps(m,'obstacles') and targets<=free
        assert ps(m,'deferred_targets')==(ps(m,'published_targets')-covered)&ps(m,'obstacles')
        history=tuple(map(tuple,m['historical_prefix']));assert history[0]==base and history[-1]==current
        assert set(history)<=ps(m,'initial_free') and covered==set(history)&initial
        assert all(sum(abs(a[i]-b[i]) for i in (0,1))==1 for a,b in zip(history,history[1:]))
        assert old[0]==current and old[-1]==base and set(old)<=ps(m,'initial_free') and initial-covered<=set(old)
        for b in c['blocks']:
            assert tuple(b['service'][0])==old[b['entry_index']] and tuple(b['service'][-1])==old[b['exit_index']]
        expected_right=(c['blocks'][2]['entry_index'] if row['scope']=='AB' else
                        c['blocks'][3]['entry_index'] if row['scope']=='ABC' else len(old)-1)
        assert info['left']==0 and info['right']==expected_right
        suffix=old[expected_right:];prefix=old[:1];req=((targets-covered)&set(old[:expected_right]))|(targets-covered-set(prefix)-set(suffix))
        req-=set(prefix)
        assert ps(info,'required')==req and tuple(info['join'])==old[expected_right]
        assert tuple(map(tuple,info['suffix']))==suffix and tuple(map(tuple,info['prefix']))==prefix
        invalid=[i for i in range(expected_right,len(old)) if old[i] not in free]
        assert invalid==info['invalid_preserved_indices']
        if invalid:
            assert r['route'] is None and r['status']=='scope_rejected_preserved_collision'
            counts['scope_collision_rejections']+=1
        else:
            cost=optimum(free,req,current,old[expected_right]);counts['exact_cost_checks']+=1
            assert cost is not None and r['patch_steps']==cost
            route=tuple(map(tuple,r['route']));patch=tuple(map(tuple,r['patch']))
            assert route==patch+suffix[1:] and req<=set(patch)
            assert patch[0]==current and patch[-1]==old[expected_right]
            s=SimpleNamespace(free=free,targets=targets,covered=covered,current=current,base=base,radius=0,distance_budget=c['distance_budget'])
            check=auditor.audit(s,route);assert check['valid'] and r['steps']==check['length']==cost+len(suffix)-1
            assert r['resource_satisfied'];counts['valid_routes']+=1
            if row['scope']=='ALL':assert r['steps']==optimum(free,targets-covered,current,base)
        lookup[row['case'],row['scope']]=r.get('steps')
        verified.append(dict(case=row['case'],scope=row['scope'],status=r['status'],steps=r.get('steps'),valid=r['route'] is not None))
    checks=dict(AB_sufficient=lookup['loop_AB_sufficient','AB']==lookup['loop_AB_sufficient','ALL'],
        widening_ABC_helps=lookup['open_boundary_tradeoff','ABC']<lookup['open_boundary_tradeoff','AB'],
        broken_tail_rejected=lookup['return_tail_broken','AB'] is None and lookup['return_tail_broken','ALL'] is not None)
    assert all(checks.values()),checks
    out.mkdir(parents=True,exist_ok=False)
    summary=dict(status='independently_verified_tiny_splice',runs=15,**counts,mechanism_checks=checks,
        baseline_solve_called=False,holdout_used=False,range_selector_implemented=False,
        caveat='Constructed tiny examples and exact constrained costs, not equal-budget superiority or generalization.',verifier_sha256=sha(Path(__file__)))
    write(out/'summary.json',summary);write(out/'per_scope_checks.json',verified)
    write(out/'sha256.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})
    print(json.dumps(summary,ensure_ascii=False));print(json.dumps(verified,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=SOURCE);p.add_argument('--out',type=Path,default=OUT)
    a=p.parse_args();main(a.source,a.out)
