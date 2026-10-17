"""Independent saved-input, ledger and unit-step route checks; no planner import."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path


def verify(folder):
    raw = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
    records = json.loads((folder/'results.json').read_text(encoding='utf-8'))
    cases = {d['name']: d for d in raw}
    groups, errors = defaultdict(list), []
    unfinished = []
    for d in raw:
        sets = {k: set(map(tuple, d[k])) for k in ('free', 'targets', 'covered')}
        m = d['metadata']
        domain, blocked, published, deferred, initial = (set(map(tuple, m[k])) for k in
            ('domain', 'obstacles', 'published_targets', 'deferred_targets', 'initial_targets'))
        prefix = list(map(tuple, m['prefix']))
        history = set(prefix) & initial
        valid = (d['radius'] == 0 and sets['free'] == domain-blocked
            and sets['covered'] == history and deferred == (published-history) & blocked
            and sets['targets'] == published-deferred and history <= published
            and not deferred & sets['targets'] and d['distance_budget'] == 4*len(domain)
            and tuple(d['current']) == prefix[-1]
            and not (published-initial) & history
            and len(deferred) == m['deferred_count']
            and len(sets['targets']-history) == m['active_pending_count']
            and len(history)/len(initial) >= m['requested_progress']
            and len(set(prefix[:-1]) & initial)/len(initial) < m['requested_progress'])
        valid = valid and all(p in domain for p in prefix) and all(
            abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(prefix,prefix[1:]))
        if not valid:
            errors.append([d['name'], 'input_or_ledger'])
        key = m['length'], m['width'], m['domain_kind'], m['requested_progress']
        groups[key].append((domain, history, prefix, d['current'], d['old_route'], initial))
    for key, group in groups.items():
        if len(group) != 8 or any(row != group[0] for row in group):
            errors.append([str(key), 'shared_history'])
    for r in records:
        d = cases[r['case']]
        free, target, history = (set(map(tuple, d[k])) for k in ('free', 'targets', 'covered'))
        path = list(map(tuple, r['route']))
        if not path:
            if r['status'] not in ('timeout', 'budget_infeasible', 'environment_infeasible') or r['audit'] is not None:
                errors.append([r['case'], r['algorithm'], 'invalid_empty_route_status'])
            unfinished.append([r['case'], r['algorithm'], r['status']])
            continue
        seen = set(path) & free
        good = (path and path[0] == tuple(d['current']) and path[-1] == tuple(d['base'])
            and set(path) <= free and target <= (history | seen)
            and len(path)-1 <= d['distance_budget'] and r['audit'] and r['audit']['valid']
            and len(path)-1 == r['audit']['length']
            and r['status'] in ('planned', 'planned_at_timeout')
            and all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(path,path[1:])))
        if not good:
            errors.append([r['case'], r['algorithm'], 'route'])
        # Deferred ground must remain physically unvisited and must not be completed.
        deferred = set(map(tuple, d['metadata']['deferred_targets']))
        if deferred & (history | seen):
            errors.append([r['case'], r['algorithm'], 'deferred_claimed'])
    counts = defaultdict(list)
    for r in records:
        counts[r['case']].append(r['algorithm'])
    if len(cases) != 64 or len(records) != 128 or any(sorted(counts[k]) != ['P1', 'P2'] for k in cases):
        errors.append(['record_cardinality'])
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['source_sha256'].items():
        if hashlib.sha256((folder/'source_snapshot'/name).read_bytes()).hexdigest() != expected:
            errors.append([name, 'archived_source_hash'])
    summary = {'snapshots_checked': len(raw), 'route_records_checked': len(records),
        'shared_history_groups_checked': len(groups), 'unfinished_records': unfinished, 'errors': errors}
    (folder/'independent_verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    verify(Path(p.parse_args().folder))
