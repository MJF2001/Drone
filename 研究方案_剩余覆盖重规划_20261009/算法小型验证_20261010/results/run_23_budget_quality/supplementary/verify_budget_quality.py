"""Independently audit all budget results, failures and feasible references."""
from pathlib import Path
from collections import Counter,deque
import hashlib,json
from scenarios import deserialize
from audit import audit,environment_check

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_23_budget_quality'


def main():
    load=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    errors=[];manifest=load('manifest.json')
    if hashlib.sha256((OUT/'snapshots.json').read_bytes()).hexdigest()!=manifest['input_sha256']:
        errors.append('input hash')
    for name,digest in manifest['source_sha256'].items():
        if hashlib.sha256((OUT/'source_snapshot'/name).read_bytes()).hexdigest()!=digest:
            errors.append('source hash '+name)
    raw=load('snapshots.json');snapshots={d['name']:(deserialize(d),d['metadata']) for d in raw}
    bounds={}
    for name,(s,m) in snapshots.items():
        prefix=list(map(tuple,m['prefix']));old=set(map(tuple,m['initial_targets']))
        published=set(map(tuple,m['published_targets']));blocked=set(map(tuple,m['obstacles']))
        deferred=set(map(tuple,m['deferred_targets']));domain=set(map(tuple,m['domain']))
        if s.radius!=0 or set(prefix)&old!=set(s.covered) or prefix[-1]!=s.current:
            errors.append('history '+name)
        if not set(prefix)<=domain or any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(prefix,prefix[1:])):
            errors.append('prefix movement '+name)
        if set(s.free)!=domain-blocked or deferred!=(published-set(s.covered))&blocked or set(s.targets)!=published-deferred:
            errors.append('ledger '+name)
        if environment_check(s):errors.append('environment '+name)
        def bfs(a):
            ds={a:0};queue=deque([a])
            while queue:
                x,y=queue.popleft()
                for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if p in s.free and p not in ds:
                        ds[p]=ds[x,y]+1;queue.append(p)
            return ds
        todo=s.targets-s.covered;dc,db=bfs(s.current),bfs(s.base)
        bound=min(dc[p] for p in todo)+len(todo)-1+min(db[p] for p in todo) if todo else dc[s.base]
        parity=(sum(s.current)-sum(s.base))%2
        bound+=(bound-parity)%2
        bounds[name]=bound
    rows=load('results.json');summary=load('summary.json');seen=set();refs={};certificates={};valid=failed=0
    for r in rows:
        key=r['case'],r['algorithm'],r['repeat'],r['budget']
        if key in seen:errors.append('duplicate '+str(key))
        seen.add(key);s,m=snapshots[r['case']]
        if r['route']:
            route=tuple(map(tuple,r['route']));check=audit(s,route)
            if not check['valid'] or check!=r['audit']:errors.append('route '+str(key))
            if set(route)&set(map(tuple,m['deferred_targets'])):errors.append('deferred flown '+str(key))
            if check['length']<bounds[r['case']]:errors.append('lower bound '+str(key))
            valid+=1
            if r['case'] not in refs or check['length']<refs[r['case']]:
                refs[r['case']]=check['length'];certificates[r['case']]={'record_key':key,'length':check['length'],'route':route,'lower_bound':bounds[r['case']]}
        else:
            failed+=1
            if r['audit'] is not None or r['status'] not in ('timeout','planning_failure','environment_infeasible'):
                errors.append('missing route status '+str(key))
    expected={(name,a,rep,budget) for name in snapshots for a in manifest['algorithms'] for rep in range(2) for budget in manifest['budgets_seconds']}
    if seen!=expected:errors.append('missing/unexpected records')
    if refs!=summary['pooled_feasible_reference']:errors.append('reference minima')
    long_refs={}
    for r in rows:
        if r['budget']==20 and r['audit'] and r['audit']['valid']:
            c=r['case'];long_refs[c]=min(long_refs.get(c,float('inf')),r['audit']['length'])
    if long_refs!=summary['20s_feasible_reference']:errors.append('20s reference minima')
    for group,stats in summary['groups'].items():
        alg,budget=group.split('@');budget=float(budget)
        selected=[r for r in rows if r['algorithm']==alg and r['budget']==budget]
        good=[r for r in selected if r['audit'] and r['audit']['valid']]
        if stats['valid_complete_routes']!=len(good) or stats['valid_step_total']!=sum(r['audit']['length'] for r in good):
            errors.append('group '+group)
        if stats['statuses']!=dict(Counter(r['status'] for r in selected)) or stats['excess_steps_vs_pooled']!=sum(r['audit']['length']-refs[r['case']] for r in good):
            errors.append('group status/gap '+group)
    by={(r['case'],r['algorithm'],r['repeat'],r['budget']):r for r in rows}
    for name,stats in summary['same_method_same_seed_vs_20s'].items():
        alg,budget=name.split('@');budget=float(budget);counts=Counter();delta=0
        for case in snapshots:
            for rep in range(2):
                a=by[case,alg,rep,budget]['audit'];b=by[case,alg,rep,20.]['audit']
                if not a or not a['valid']:counts['short_no_valid_route']+=1
                elif not b or not b['valid']:counts['long_no_valid_route']+=1
                else:
                    gap=a['length']-b['length'];delta+=gap
                    counts['short_worse' if gap>0 else 'equal' if gap==0 else 'short_better']+=1
        if dict(counts)!=stats['counts'] or delta!=stats['paired_step_difference_short_minus_20s']:
            errors.append('paired accounting '+name)
    payload={'snapshots':len(snapshots),'records':len(rows),'valid_complete_routes':valid,
        'no_route_records_retained':failed,'errors':errors,
        'lower_bound_total':sum(bounds.values()),'pooled_feasible_upper_bound_total':sum(refs.values()),
        'cases_proven_optimal_by_bound':sum(refs[c]==bounds[c] for c in refs),
        'scope':'route/ledger/hash checks, full factorial executions and failures, independently rebuilt feasible reference minima and parity-adjusted cardinality bound'}
    (OUT/'independent_verification.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'feasible_reference_certificates.json').write_text(json.dumps(certificates,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(payload,ensure_ascii=False,indent=2));assert not errors


if __name__=='__main__':main()
