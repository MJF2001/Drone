"""Verify diagnostic witnesses without calling optimisation or A*."""
from pathlib import Path
from collections import deque
import hashlib
import json
from audit import audit
from scenarios import deserialize

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results/run_19_partition_objective_diagnostic'


def main():
    load = lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    errors = []
    manifest = load('manifest.json')
    for name,digest in manifest['source_sha256'].items():
        if hashlib.sha256((OUT/'source_snapshot'/name).read_bytes()).hexdigest()!=digest:
            errors.append('source hash '+name)
    for name,digest in manifest['input_sha256'].items():
        if hashlib.sha256((OUT/('input_'+name+'.json')).read_bytes()).hexdigest()!=digest:
            errors.append('input hash '+name)
    snapshots = {d['name']:(deserialize(d),d['metadata']) for d in load('input_snapshots.json')}
    rows = load('results.json')
    if len(rows)!=64 or len({r['case'] for r in rows})!=64:
        errors.append('case count')
    routes = 0
    for row in rows:
        s,meta = snapshots[row['case']]
        ds_cache = {}
        def distance(a,b):
            if a not in ds_cache:
                ds={a:0}
                queue=deque([a])
                while queue:
                    x,y=queue.popleft()
                    for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                        if p in s.free and p not in ds:
                            ds[p]=ds[x,y]+1
                            queue.append(p)
                ds_cache[a]=ds
            return ds_cache[a][b]
        for axis,v in row['candidates'].items():
            if v['status']!='planned':
                continue
            blocks=[tuple(map(tuple,r['cells'])) for r in v['ranks']]
            points=[p for b in blocks for p in b]
            if len(points)!=len(set(points)) or set(points)!=s.targets-s.covered:
                errors.append('partition '+row['case']+axis)
            for block,r in zip(blocks,v['ranks']):
                if r['axis']!=axis or any((q[0]-p[0],q[1]-p[1])!=((1,0) if axis=='H' else (0,1)) for p,q in zip(block,block[1:])):
                    errors.append('straight rank '+row['case']+axis)
            states=[p for b in blocks for p in (b,tuple(reversed(b)))]+[(s.current,),(s.base,)]
            order=v['order']
            n=len(blocks)
            if len(order)!=n+2 or order[0]!=2*n or order[-1]!=2*n+1 or sorted(k//2 for k in order[1:-1])!=list(range(n)):
                errors.append('order '+row['case']+axis)
                continue
            cost=sum(len(states[a])-1+distance(states[a][-1],states[b][0]) for a,b in zip(order,order[1:]))
            if cost!=v['full_length']:
                errors.append('BFS cost '+row['case']+axis)
            for mode in ('full','skip'):
                route=tuple(map(tuple,v[mode+'_route']))
                check=audit(s,route)
                if not check['valid'] or check!=v[mode+'_audit'] or len(route)-1!=v[mode+'_length']:
                    errors.append('route '+row['case']+axis+mode)
                if set(route)&set(map(tuple,meta['deferred_targets'])):
                    errors.append('deferred target '+row['case']+axis+mode)
                routes+=1
            seen=set(s.covered)|{s.current}
            route=list(map(tuple,v['skip_route']))
            cursor=0
            for p in (p for node in order[1:-1] for p in states[node]):
                if p in seen:
                    continue
                while cursor<len(route)-1 and route[cursor]!=p:
                    cursor+=1
                    seen.add(route[cursor])
                if route[cursor]!=p:
                    errors.append('skip replay '+row['case']+axis)
            if v['skip_length']>v['full_length']:
                errors.append('worse skip '+row['case']+axis)
        expected=min([row['reference']['skip_length'],row['common_fallback_length']]+[v['skip_length'] for v in row['candidates'].values() if v['status']=='planned'])
        if row['combined_final_length']!=expected:
            errors.append('selection '+row['case'])
    result={'cases':len(rows),'routes_checked':routes,'errors':errors,
        'scope':'route audit, straight exact partitions, fixed-order skip legality, independent BFS full-service cost, inputs and source hashes; exact values computed by runner independent subset DP'}
    (OUT/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not errors


if __name__=='__main__':
    main()
