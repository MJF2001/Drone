"""Independent route, partition and directed-tour cost audit, with BFS metric oracle."""
from collections import Counter, deque
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys


def verify(folder):
    raw = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
    rows = json.loads((folder/'results.json').read_text(encoding='utf-8'))
    cases = {d['name']:d for d in raw}
    errors, exact_checks = [], []
    proposed = 0
    for r in rows:
        d = cases[r['case']]
        free,target,covered = (set(map(tuple,d[k])) for k in ('free','targets','covered'))
        route = list(map(tuple,r['route']))
        good = (route and route[0] == tuple(d['current']) and route[-1] == tuple(d['base'])
            and set(route) <= free and target <= covered|set(route)
            and len(route)-1 <= d['distance_budget'] and r['audit']['valid']
            and len(route)-1 == r['audit']['length'] and all(
                abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(route,route[1:])))
        if not good:
            errors.append([r['case'],r['algorithm'],'chosen_route'])
        deferred = set(map(tuple,d['metadata']['deferred_targets']))
        if deferred & (covered|set(route)):
            errors.append([r['case'],r['algorithm'],'deferred_claimed'])
        detail = r['detail']
        if 'tour' not in detail:
            continue
        proposed += 1
        ranks = detail['ranks']
        rank_keys, flat = [], []
        for rank in ranks:
            cells = list(map(tuple,rank['cells']))
            flat.extend(cells)
            rank_keys.append((rank['axis'],cells[0],cells[-1]))
            dx,dy = (1,0) if rank['axis']=='H' else (0,1)
            if any((b[0]-a[0],b[1]-a[1]) != (dx,dy) for a,b in zip(cells,cells[1:])):
                errors.append([r['case'],r['algorithm'],'rank_geometry'])
        if len(flat) != len(set(flat)) or set(flat) != target-covered:
            errors.append([r['case'],r['algorithm'],'rank_partition'])
        metric = detail['rank']['metrics']
        if len(ranks) != metric['rank_count'] or metric['new_rank_count'] > detail['rank_cap']:
            errors.append([r['case'],r['algorithm'],'rank_budget'])
        if detail['variant']==2 and metric['endpoint_bound'] > detail['rank_cap']:
            errors.append([r['case'],r['algorithm'],'endpoint_budget'])
        blocks = detail['blocks']
        used,states = [], []
        old_route = list(map(tuple,d['old_route']))
        for b in blocks:
            path = tuple(map(tuple,b['path']))
            keys = [(k[0],tuple(k[1]),tuple(k[2])) for k in b['rank_keys']]
            used.extend(keys)
            if not set(path) <= free or any(abs(a[0]-q[0])+abs(a[1]-q[1]) != 1 for a,q in zip(path,path[1:])):
                errors.append([r['case'],r['algorithm'],'block_geometry'])
            if b['kind']=='path' and not any(old_route[i:i+len(path)] == list(path) for i in range(len(old_route))):
                errors.append([r['case'],r['algorithm'],'packet_not_old_subpath'])
            states.extend((path,tuple(reversed(path))))
        if Counter(used) != Counter(rank_keys):
            errors.append([r['case'],r['algorithm'],'block_rank_assignment'])
        start,end = len(states),len(states)+1
        states.extend(((tuple(d['current']),),(tuple(d['base']),)))
        sets = [[2*k,2*k+1] for k in range(len(blocks))]+[[start],[end]]
        @lru_cache(None)
        def distances(p):
            q,cost = deque([p]),{p:0}
            while q:
                x,y = q.popleft()
                for v in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                    if v in free and v not in cost:
                        cost[v] = cost[x,y]+1
                        q.append(v)
            return cost
        def edge(i,j):
            return len(states[i])-1+distances(states[i][-1])[states[j][0]]
        order = detail['tour']['order']
        if order[0]!=start or order[-1]!=end or len(order)!=len(sets) or any(
            sum(v in group for v in order)!=1 for group in sets):
            errors.append([r['case'],r['algorithm'],'GTSP_order'])
        cost = sum(edge(a,b) for a,b in zip(order,order[1:]))
        if cost != detail['tour']['length']:
            errors.append([r['case'],r['algorithm'],'GTSP_BFS_cost'])
        if len(blocks) <= 12:
            @lru_cache(None)
            def dp(mask,last):
                if mask == (1<<len(blocks))-1:
                    return edge(last,end)
                return min(edge(last,node)+dp(mask|1<<k,node)
                    for k in range(len(blocks)) if not mask>>k & 1
                    for node in (2*k,2*k+1))
            optimum = dp(0,start)
            if cost < optimum:
                errors.append([r['case'],r['algorithm'],'below_exact_GTSP'])
            exact_checks.append({'case':r['case'],'algorithm':r['algorithm'],
                'groups':len(blocks),'GLNS_cost':cost,'exact_GTSP_cost':optimum,'gap':cost-optimum})
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['source_sha256'].items():
        if hashlib.sha256((folder/'source_snapshot'/name).read_bytes()).hexdigest()!=expected:
            errors.append([name,'archived_hash'])
    if hashlib.sha256((folder/'snapshots.json').read_bytes()).hexdigest()!=manifest['input_sha256']:
        errors.append(['snapshot_hash'])
    if hashlib.sha256((folder/'baseline_results.json').read_bytes()).hexdigest()!=manifest['baseline_sha256']:
        errors.append(['baseline_hash'])
    counts = Counter((r['case'],r['algorithm']) for r in rows)
    if len(rows)!=128 or any(counts[name,alg]!=1 for name in cases for alg in ('OARP_CORE_1','OARP_CORE_2')):
        errors.append(['record_count'])
    summary = {'snapshots':len(raw),'selected_routes':len(rows),'proposed_tours':proposed,
        'exact_GTSP_checks':len(exact_checks),'exact_GTSP_gaps':dict(Counter(r['gap'] for r in exact_checks)),
        'errors':errors}
    (folder/'independent_verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'exact_GTSP_checks.json').write_text(json.dumps(exact_checks,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if errors:
        raise SystemExit(1)


if __name__=='__main__':
    verify(Path(sys.argv[1]))
