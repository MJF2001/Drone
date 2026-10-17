"""Saved-file replay, BFS distances and independent top-down exact recurrence."""
from pathlib import Path
import argparse
import json
from collections import deque
from functools import lru_cache
from audit import audit
from scenarios import deserialize
from run_experiments import write_json


def verify(folder):
    raw = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
    cases = {d['name']: deserialize(d) for d in raw}
    pools = json.loads((folder/'pool_results.json').read_text(encoding='utf-8'))
    errors, checked_routes, exact_checks = [], 0, 0
    bfs_cache, exact_cache = {}, {}
    def distance(s, a, b):
        key = s.name, a
        if key not in bfs_cache:
            distances, queue = {a: 0}, deque([a])
            while queue:
                x,y = queue.popleft()
                for q in ((x+1,y), (x-1,y), (x,y+1), (x,y-1)):
                    if q in s.free and q not in distances:
                        distances[q] = distances[x,y]+1
                        queue.append(q)
            bfs_cache[key] = distances
        return bfs_cache[key][b]
    def route_check(s, route, expected, label):
        nonlocal checked_routes
        result = audit(s, tuple(map(tuple, route)))
        checked_routes += 1
        if result != expected or not result['valid']:
            errors.append([s.name, label, 'route_audit'])
    def score_check(s, visits, score, label):
        points = list(map(tuple, visits))
        chain = [s.current]+points+[s.base]
        independent_proxy = sum(distance(s,a,b) for a,b in zip(chain, chain[1:]))
        if independent_proxy != score['proxy']:
            errors.append([s.name, label, 'proxy_distance'])
        route_check(s, score['strict_route'], score['strict_audit'], label+'_strict')
        route_check(s, score['actual_route'], score['actual_audit'], label+'_actual')
        if score['strict_audit']['length'] != independent_proxy or not set(points) <= set(map(tuple, score['strict_route'])):
            errors.append([s.name, label, 'required_visits'])
    for r in pools:
        s = cases[r['case']]
        points = list(map(tuple, r['points']))
        for h in r['heuristics']:
            route_check(s, h['original_route'], h['original_audit'], h['label']+'_original')
            score_check(s, h['visits'], h, h['label'])
            if sorted(map(tuple, h['visits'])) != sorted(points):
                errors.append([s.name, h['label'], 'pool_changed'])
        if r['oracle_status'] == 'optimal':
            exact_checks += 1
            score_check(s, r['exact_visits'], r['exact'], 'exact')
            indices = r['exact_indices']
            if sorted(indices) != list(range(len(points))) or [points[i] for i in indices] != list(map(tuple, r['exact_visits'])):
                errors.append([s.name, r['direction'], 'oracle_permutation'])
            # Canonical point-set order also verifies equal-point pools together.
            ordered = tuple(sorted(points))
            key = s.name, ordered
            if key not in exact_cache:
                n = len(ordered)
                @lru_cache(None)
                def remainder(last, mask):
                    current = s.current if last == n else ordered[last]
                    if mask == 0:
                        return distance(s, current, s.base)
                    return min(distance(s, current, ordered[k])+remainder(k, mask ^ (1<<k))
                               for k in range(n) if mask & (1<<k))
                exact_cache[key] = remainder(n, (1<<n)-1)
                remainder.cache_clear()
            if exact_cache[key] != r['exact']['proxy']:
                errors.append([s.name, r['direction'], 'independent_exact_mismatch'])
        elif r['oracle_status'] == 'size_limit' and len(points) <= 14:
            errors.append([s.name, 'unexpected_size_exclusion'])
    summary = {'pool_records_checked': len(pools), 'actual_routes_checked': checked_routes,
               'optimal_pool_records_checked': exact_checks,
               'distinct_fixed_point_problems_recomputed': len(exact_cache), 'errors': errors}
    write_json(folder/'saved_file_verification.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    verify(Path(p.parse_args().folder))
