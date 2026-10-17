"""Saved-input invariants and actual-route audit for the fixed-domain diagnostics."""
import argparse
import json
from pathlib import Path
from collections import defaultdict
from audit import audit, environment_check
from scenarios import deserialize
from run_experiments import write_json


def verify(folder):
    raw = json.loads((folder/'snapshots.json').read_text(encoding='utf-8'))
    cases = {r['name']: deserialize(r) for r in raw}
    rows = json.loads((folder/'results.json').read_text(encoding='utf-8'))
    groups, errors = defaultdict(list), []
    for d in raw:
        meta, s = d['metadata'], cases[d['name']]
        domain = frozenset(map(tuple, meta['domain']))
        blocked = frozenset(map(tuple, meta['obstacles']))
        old = frozenset(map(tuple, meta['initial_targets']))
        prefix = tuple(map(tuple, meta['prefix']))
        # Independent direct Chebyshev coverage calculation, not capture_route.
        expected_coverage = frozenset(q for q in old if any(
            max(abs(q[0]-p[0]), abs(q[1]-p[1])) <= s.radius for p in prefix))
        valid = (s.free == domain-blocked and s.targets <= domain and
            s.covered == expected_coverage and not (s.targets-old) & s.covered and
            s.distance_budget == 4*len(domain) and s.current in s.free and
            s.base in s.free and prefix[-1] == s.current)
        if not valid:
            errors.append([s.name, 'snapshot_invariant'])
        key = meta['length'], meta['width'], meta['domain_kind'], meta['requested_progress']
        groups[key].append((domain, s.current, s.base, s.covered, s.old_route, prefix, old))
    for key, group in groups.items():
        if len(group) != 8 or any(row != group[0] for row in group):
            errors.append([list(key), 'shared_history_or_domain'])
    for r in rows:
        s = cases[r['case']]
        if r['route']:
            check = audit(s, tuple(map(tuple, r['route'])))
            if check != r['audit'] or not check['valid']:
                errors.append([s.name, r['algorithm'], 'route_audit'])
        elif environment_check(s) != r['reason'] or r['status'] != 'environment_infeasible':
            errors.append([s.name, r['algorithm'], 'status'])
    summary = {'snapshots_checked': len(raw), 'shared_history_groups_checked': len(groups),
               'route_records_checked': len(rows), 'errors': errors}
    write_json(folder/'saved_file_verification.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    verify(Path(p.parse_args().folder))
