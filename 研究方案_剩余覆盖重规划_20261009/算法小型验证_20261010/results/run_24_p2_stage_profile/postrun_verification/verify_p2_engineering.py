"""Independent result/provenance checks for stage audit and paired cache trial."""
from pathlib import Path
from collections import Counter
import hashlib,json,statistics
from scenarios import deserialize
from audit import audit,environment_check

ROOT=Path(__file__).resolve().parent

def verify(folder,profile=False):
    out=ROOT/'results'/folder
    load=lambda name:json.loads((out/name).read_text(encoding='utf-8'))
    errors=[];manifest=load('manifest.json');raw=load('snapshots.json')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if digest(out/'snapshots.json')!=manifest['input_sha256']:errors.append('input hash')
    for name,value in manifest['source_sha256'].items():
        if digest(out/'source_snapshot'/name)!=value:errors.append('source hash '+name)
    snapshots={d['name']:deserialize(d) for d in raw}
    for d in raw:
        s=snapshots[d['name']];m=d['metadata']
        prefix=list(map(tuple,m['prefix']));old=set(map(tuple,m['initial_targets']))
        pub=set(map(tuple,m['published_targets']));obs=set(map(tuple,m['obstacles']))
        deferred=set(map(tuple,m['deferred_targets']));domain=set(map(tuple,m['domain']))
        if s.radius!=0 or set(prefix)&old!=set(s.covered) or prefix[-1]!=s.current:errors.append('history '+s.name)
        if not set(prefix)<=domain or any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(prefix,prefix[1:])):errors.append('prefix '+s.name)
        if set(s.free)!=domain-obs or deferred!=(pub-set(s.covered))&obs or set(s.targets)!=pub-deferred:errors.append('ledger '+s.name)
        if environment_check(s):errors.append('environment '+s.name)
    previous=json.loads((ROOT/'results/run_23_budget_quality/results.json').read_text(encoding='utf-8'))
    refs={r['case']:r['route'] for r in previous if r['algorithm']=='P2_SHARED' and r['budget']==20 and r['repeat']==0}
    rows=load('results.json');summary=load('summary.json');seen=set();same=0
    for r in rows:
        s=snapshots[r['case']];check=audit(s,tuple(map(tuple,r['route'])))
        if not check['valid'] or check!=r['audit']:errors.append('route '+r['case'])
        if profile or r['budget'] in (5,20):
            if r['route']!=refs[r['case']]:errors.append('route equivalence '+r['case'])
            else:same+=1
        key=r['case'] if profile else (r['case'],r['algorithm'],r['repeat'],r['budget'])
        if key in seen:errors.append('duplicate '+str(key))
        seen.add(key)
        if profile:
            incumbent=None;last=-1
            for event in r['events']:
                if event['time']<last:errors.append('event time '+r['case'])
                last=event['time'];n=event['length']
                improves=bool(event['valid'] and (incumbent is None or n<incumbent))
                if improves:incumbent=n
                if improves!=event['improved'] or incumbent!=event['incumbent_length']:errors.append('incumbent '+r['case'])
            if incumbent!=check['length']:errors.append('final incumbent '+r['case'])
            if sum(t['seconds'] for t in r['stages'])>r['seconds']+.001:errors.append('stage timing '+r['case'])
            c=r['counts']
            if c['path_calls']!=c['cached_path_calls']+c['uncached_path_calls'] or c['uncached_path_calls']!=r['Astar_searches']:errors.append('counter consistency '+r['case'])
    if profile:
        if seen!=set(snapshots):errors.append('case coverage')
        grouped=Counter()
        for r in rows:
            for st in r['stages']:
                n=st['name'];category=('nearest' if n.endswith('_nearest') else '2opt' if n.endswith('_2opt') else 'route_validation' if n.endswith('_validate') else 'route_expansion' if n.endswith('_expand') else 'candidate_generation' if n.endswith('_candidates') else n)
                grouped[category]+=st['seconds']
        if dict(grouped)!=summary['stage_seconds']:errors.append('stage summary')
        if dict(sum((Counter(r['counts']) for r in rows),Counter()))!=summary['counts']:errors.append('counter summary')
    else:
        expected={(c,a,rep,b) for c in snapshots for a in manifest['implementations'] for rep in range(2) for b in manifest['budgets_seconds']}
        if seen!=expected:errors.append('execution coverage')
        by={(r['case'],r['algorithm'],r['repeat'],r['budget']):r for r in rows}
        for b in manifest['budgets_seconds']:
            q=summary[str(b)]
            for a in manifest['implementations']:
                group=[r for r in rows if r['algorithm']==a and r['budget']==b];t=q[a]
                if t['valid']!=len(group) or t['steps_total']!=sum(r['audit']['length'] for r in group) or t['statuses']!=dict(Counter(r['status'] for r in group)):errors.append('group summary '+str((a,b)))
                if t['seconds_median']!=statistics.median(r['seconds'] for r in group) or t['seconds_total']!=sum(r['seconds'] for r in group) or t['seconds_max']!=max(r['seconds'] for r in group):errors.append('timing summary '+str((a,b)))
                if t['overruns_gt_10ms']!=sum(r['seconds']>b+.01 for r in group):errors.append('overrun '+str((a,b)))
            counts=Counter();persistent=Counter();saved=0
            for c in snapshots:
                outcomes=[]
                for rep in range(2):
                    delta=by[c,'P2_ASTAR',rep,b]['audit']['length']-by[c,'P2_BFS',rep,b]['audit']['length'];saved+=delta
                    label='BFS_shorter' if delta>0 else 'equal' if delta==0 else 'ASTAR_shorter'
                    counts[label]+=1;outcomes.append(label)
                persistent[outcomes[0] if outcomes[0]==outcomes[1] else 'mixed']+=1
            if dict(counts)!=q['paired_counts'] or saved!=q['BFS_steps_saved'] or dict(persistent)!=q['case_repeat_consistency']:errors.append('paired summary '+str(b))
    result={'records':len(rows),'snapshots':len(snapshots),'valid_routes':len(rows)-sum(e.startswith('route ') for e in errors),'routes_equal_to_prior_20s':same,'errors':errors,'scope':'archived hashes, actual coverage ledger and route audit, execution completeness, route equivalence, independently rebuilt summaries; timing is measured, not independently reproducible proof'}
    (out/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(folder,json.dumps(result,ensure_ascii=False));assert not errors

if __name__=='__main__':
    verify('run_24_p2_stage_profile',True)
    verify('run_25_optimized_p2_baseline')
