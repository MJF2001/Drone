"""Different exact formulation: free-map BFS distances + metric Held-Karp."""
from pathlib import Path
from collections import defaultdict
import json,hashlib,time
from scenarios import deserialize
from audit import audit,environment_check
from exact_grid_coverage import independent_metric_optimum

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_22_structural_stress'


def main():
    begin=time.perf_counter()
    load=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    errors=[]
    manifest=load('manifest.json')
    if hashlib.sha256((OUT/'snapshots.json').read_bytes()).hexdigest()!=manifest['snapshots_sha256']:
        errors.append('snapshots hash')
    for name,digest in manifest['source_sha256'].items():
        if hashlib.sha256((OUT/'source_snapshot'/name).read_bytes()).hexdigest()!=digest:
            errors.append('source hash '+name)
    snapshots={d['name']:(deserialize(d),d['metadata']) for d in load('snapshots.json')}
    optima={}
    for name,(s,m) in snapshots.items():
        prefix=list(map(tuple,m['prefix']))
        published=set(map(tuple,m['published_targets']))
        old=set(map(tuple,m['initial_targets']))
        blocked=set(map(tuple,m['obstacles']))
        deferred=set(map(tuple,m['deferred_targets']))
        domain=set(map(tuple,m['domain']))
        if s.radius!=0 or (set(prefix)&old)!=set(s.covered) or prefix[-1]!=s.current:
            errors.append('history '+name)
        if set(s.free)!=domain-blocked or deferred!=(published-set(s.covered))&blocked or set(s.targets)!=published-deferred:
            errors.append('ledger '+name)
        if not set(prefix)<=domain or any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(prefix,prefix[1:])):
            errors.append('prefix movement '+name)
        if environment_check(s):
            errors.append('environment '+name)
        optima[name]=independent_metric_optimum(s)
    records=load('results.json')
    seen=set()
    common=defaultdict(set)
    checked=0
    for r in records:
        key=r['case'],r['algorithm']
        if key in seen:
            errors.append('duplicate '+str(key))
        seen.add(key)
        s,m=snapshots[r['case']]
        route=tuple(map(tuple,r['route']))
        result=audit(s,route)
        if not result['valid'] or result!=r['audit']:
            errors.append('route '+str(key))
        if set(route)&set(map(tuple,m['deferred_targets'])):
            errors.append('deferred flown '+str(key))
        optimum=optima[r['case']]
        if r['algorithm']=='EXACT_GRID':
            if r['status']!='optimal' or result['length']!=optimum or r['length']!=optimum:
                errors.append('exact formulations disagree '+str(key))
            if not r['budget_feasible']:
                errors.append('exact budget infeasible '+str(key))
        else:
            if r['gap']!=result['length']-optimum or r['gap']<0:
                errors.append('gap '+str(key))
            common[r['case']].add(r['detail'].get('common_length'))
        checked+=1
    if len(snapshots)!=96 or len(seen)!=384 or any(len(v)!=1 for v in common.values()):
        errors.append('count/common incumbent mismatch')
    payload={'snapshots':len(snapshots),'records':len(records),'valid_routes':checked,
        'independent_exact_matches':len(optima),'errors':errors,'seconds':time.perf_counter()-begin,
        'scope':'grid-state BFS optimum equals independently computed metric Held-Karp optimum; legal complete routes, history, ledger, hashes and heuristic gaps'}
    (OUT/'independent_verification.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'independent_optima.json').write_text(json.dumps(optima,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2))
    assert not errors


if __name__=='__main__':
    main()
