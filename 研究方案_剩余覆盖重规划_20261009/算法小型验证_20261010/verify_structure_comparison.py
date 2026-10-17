"""Independent route/ledger validation and Kruskal checks of saved Prim trees."""
from pathlib import Path
from collections import defaultdict,deque
import json
import hashlib
from scenarios import deserialize
from audit import audit,environment_check

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'results/run_20_new_structure_comparison'


def check_tree(s,edges):
    terminals=set(s.targets-s.covered)|{s.current}
    parent={p:p for p in terminals}
    def root(p):
        while parent[p]!=p:
            parent[p]=parent[parent[p]]
            p=parent[p]
        return p
    cache={}
    def distances(a):
        if a not in cache:
            ds={a:0}
            queue=deque([a])
            while queue:
                x,y=queue.popleft()
                for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if p in s.free and p not in ds:
                        ds[p]=ds[x,y]+1
                        queue.append(p)
            cache[a]=ds
        return cache[a]
    if len(edges)!=len(terminals)-1:
        return 'edge count'
    weight=0
    for raw_a,raw_b,cost in edges:
        a,b=tuple(raw_a),tuple(raw_b)
        if a not in terminals or b not in terminals or root(a)==root(b):
            return 'invalid tree edge/cycle'
        if distances(a)[b]!=cost:
            return 'edge not shortest-map metric'
        parent[root(a)]=root(b)
        weight+=cost
    if len({root(p) for p in terminals})!=1:
        return 'not spanning'
    # A different MST algorithm verifies optimum tree weight, not route optimality.
    parent={p:p for p in terminals}
    points=sorted(terminals)
    possible=[]
    for i,a in enumerate(points):
        ds=distances(a)
        possible.extend((ds[b],a,b) for b in points[i+1:])
    optimum=count=0
    for cost,a,b in sorted(possible):
        if root(a)!=root(b):
            parent[root(a)]=root(b)
            optimum+=cost
            count+=1
            if count==len(terminals)-1:
                break
    return None if weight==optimum else 'tree not MST'


def main():
    load=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    errors=[]
    manifest=load('manifest.json')
    if hashlib.sha256((OUT/'snapshots.json').read_bytes()).hexdigest()!=manifest['snapshots_sha256']:
        errors.append('snapshots hash')
    for name,digest in manifest['source_sha256'].items():
        if hashlib.sha256((OUT/'source_snapshot'/name).read_bytes()).hexdigest()!=digest:
            errors.append('source hash '+name)
    snapshots={d['name']:(deserialize(d),d['metadata']) for d in load('snapshots.json')}
    for name,(s,meta) in snapshots.items():
        published=set(map(tuple,meta['published_targets']))
        old=set(map(tuple,meta['initial_targets']))
        prefix=list(map(tuple,meta['prefix']))
        blocked=set(map(tuple,meta['obstacles']))
        domain=set(map(tuple,meta['domain']))
        deferred=set(map(tuple,meta['deferred_targets']))
        if s.radius!=0 or (set(prefix)&old)!=set(s.covered) or prefix[-1]!=s.current:
            errors.append('history '+name)
        if set(s.free)!=domain-blocked or deferred!=(published-set(s.covered))&blocked or set(s.targets)!=published-deferred:
            errors.append('ledger '+name)
        if not set(prefix)<=domain or any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(prefix,prefix[1:])):
            errors.append('prefix movement '+name)
        if environment_check(s):
            errors.append('environment '+name)
    records=load('results.json')
    bounds={r['case']:r for r in load('simple_lower_bounds.json')}
    for name,(s,meta) in snapshots.items():
        def bfs(origin):
            ds={origin:0}
            queue=deque([origin])
            while queue:
                x,y=queue.popleft()
                for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if p in s.free and p not in ds:
                        ds[p]=ds[x,y]+1
                        queue.append(p)
            return ds
        todo=s.targets-s.covered
        start_ds,base_ds=bfs(s.current),bfs(s.base)
        bound=(min(start_ds[p] for p in todo)+len(todo)-1+min(base_ds[p] for p in todo)
            if todo else start_ds[s.base])
        if bounds[name]['lower_bound']!=bound:
            errors.append('lower bound '+name)
    seen=set()
    common=defaultdict(set)
    trees=routes=0
    for r in records:
        key=r['case'],r['algorithm']
        if key in seen:
            errors.append('duplicate '+str(key))
        seen.add(key)
        s,meta=snapshots[r['case']]
        if r['route']:
            route=tuple(map(tuple,r['route']))
            check=audit(s,route)
            if not check['valid'] or check!=r['audit']:
                errors.append('route '+str(key))
            if set(route)&set(map(tuple,meta['deferred_targets'])):
                errors.append('deferred flown '+str(key))
            if check['length']>r['detail']['common_length']:
                errors.append('discarded incumbent '+str(key))
            if check['length']<bounds[r['case']]['lower_bound']:
                errors.append('violated lower bound '+str(key))
            routes+=1
        common[r['case']].add(r['detail'].get('common_length'))
        if 'tree_edges' in r['detail']:
            reason=check_tree(s,r['detail']['tree_edges'])
            if reason:
                errors.append(reason+' '+str(key))
            trees+=1
    if len(snapshots)!=24 or len(seen)!=72 or any(len(v)!=1 for v in common.values()):
        errors.append('case/record/common fallback mismatch')
    result={'snapshots':len(snapshots),'records':len(records),'valid_routes':routes,
        'MSTs_checked_by_independent_Kruskal':trees,'errors':errors,
        'scope':'coverage ledger, histories, legal complete return routes, equal common incumbent, archived hashes and metric MST certificates; no global route optimality claim'}
    (OUT/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not errors


if __name__=='__main__':
    main()
