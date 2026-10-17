"""Post-run certificates using BFS; never calls a route planner or GLNS."""
from collections import deque
import hashlib
import json
from pathlib import Path
from audit import audit
from scenarios import deserialize

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results/run_17_frozen_partition_ablation'


def main():
    load = lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
    manifest = load('manifest.json')
    errors = []
    for name,digest in manifest['source_sha256'].items():
        if hashlib.sha256((OUT/'source_snapshot'/name).read_bytes()).hexdigest()!=digest:
            errors.append('source hash '+name)
    for name,digest in manifest['input_sha256'].items():
        if hashlib.sha256((OUT/('input_'+name)).read_bytes()).hexdigest()!=digest:
            errors.append('input hash '+name)
    snapshots = {d['name']:(deserialize(d),d['metadata']) for d in load('input_snapshots.json')}
    original = {(r['case'],r['algorithm']):r for r in load('input_results.json')}
    rows = load('results.json')
    seen = set()
    checks = both_exact = 0
    for r in rows:
        identity = r['case'],r['algorithm']
        if identity in seen:
            errors.append('duplicate '+str(identity))
        seen.add(identity)
        s,meta = snapshots[r['case']]
        detail = original[identity]['detail']
        packed = [tuple(map(tuple,b['path'])) for b in detail['blocks']]
        split = [tuple(map(tuple,b['cells'])) for b in detail['ranks']]
        if set(p for b in split for p in b)!=s.targets-s.covered:
            errors.append('frozen partition '+str(identity))
        cache = {}
        def dist(a,b):
            if a not in cache:
                ds = {a:0}
                q = deque([a])
                while q:
                    x,y = q.popleft()
                    for t in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                        if t in s.free and t not in ds:
                            ds[t]=ds[x,y]+1
                            q.append(t)
                cache[a]=ds
            return cache[a][b]
        for mode,blocks in (('packed',packed),('split',split)):
            arm = r[mode]
            route = tuple(map(tuple,arm['route']))
            check = audit(s,route)
            if not check['valid'] or check!=arm['audit']:
                errors.append('route audit '+str(identity)+mode)
            if set(route)&set(map(tuple,meta['deferred_targets'])):
                errors.append('deferred target flown '+str(identity)+mode)
            n = len(blocks)
            states = [p for b in blocks for p in (b,tuple(reversed(b)))]+[(s.current,),(s.base,)]
            order = arm['order']
            if len(order)!=n+2 or order[0]!=2*n or order[-1]!=2*n+1 or sorted(v//2 for v in order[1:-1])!=list(range(n)):
                errors.append('state selection '+str(identity)+mode)
                continue
            value = sum(len(states[a])-1+dist(states[a][-1],states[b][0]) for a,b in zip(order,order[1:]))
            if value!=arm['length'] or value!=len(route)-1:
                errors.append('BFS cost '+str(identity)+mode)
            if arm['exact'] is not None and arm['gap']!=value-arm['exact']:
                errors.append('gap '+str(identity)+mode)
            checks+=1
        if r['packed']['exact'] is not None and r['split']['exact'] is not None:
            both_exact+=1
            if r['split']['exact']>r['packed']['exact']:
                errors.append('nested optimum '+str(identity))
    if len(seen)!=128:
        errors.append('expected 128 paired partitions')
    result = {'paired_partitions':len(rows),'routes_checked':checks,'both_exact_pairs':both_exact,'errors':errors,
        'scope':'saved route validity, ledger, frozen partition, independently rebuilt BFS costs and input/source hashes; exact optima computed separately by runner subset DP'}
    (OUT/'independent_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    assert not errors


if __name__=='__main__':
    main()
