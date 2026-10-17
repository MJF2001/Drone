"""Declared exploratory mechanism and model sensitivity checks."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import argparse
import hashlib
import json
import sys
from audit import audit, environment_check
from model import capture_route
from mechanisms import run_diagnostic
from planners import solve
from scenarios import deserialize, serialize, flight_domain
from run_experiments import write_json


def sensitivity_snapshot(original, meta, radius, margin):
    old_targets = frozenset(map(tuple, meta['initial_targets']))
    prefix = tuple(map(tuple, meta['prefix']))
    obstacles = set(map(tuple, meta['obstacles']))
    free = frozenset((flight_domain(original.targets, margin)|{(1, 3), (2, 3)})-obstacles)
    return replace(original, name=original.name+f'_r{radius}_m{margin}',
        free=free, radius=radius, covered=capture_route(prefix, old_targets, radius))


def run(source, output):
    root = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=False)
    archive = output/'source_snapshot'
    archive.mkdir()
    hashes = {}
    for p in sorted(root.glob('*.py'))+[root/'config.json', root/'MECHANISM_PROTOCOL.md']:
        data = p.read_bytes()
        (archive/p.name).write_bytes(data)
        hashes[p.name] = hashlib.sha256(data).hexdigest()
    data = json.loads((source/'snapshots.json').read_text(encoding='utf-8'))
    write_json(output/'snapshots.json', data)
    write_json(output/'manifest.json', {'source': str(source.resolve()),
        'snapshot_sha256': hashlib.sha256((source/'snapshots.json').read_bytes()).hexdigest(),
        'source_sha256': hashes, 'python': sys.version, 'held_out': False,
        'time_limit_seconds': 5, 'passes': 8, 'timing_repetitions': 1})
    records, failures = [], []
    for d in data:
        s = deserialize(d)
        for kind in ('G', 'S'):
            for locked in (False, True):
                r = run_diagnostic(s, kind, locked)
                r.update(case=s.name, algorithm=kind+('_locked' if locked else '_free'))
                reason = environment_check(s)
                correct = (r['status'] == 'environment_infeasible' and r['reason'] == reason
                           if reason else bool(r['audit']['valid'] and r['skipped_audit']['valid']
                                              and r['ordering_constraint_valid']))
                r['expected_case_handled'] = correct
                if not correct:
                    failures.append((s.name, r['algorithm'], r['status']))
                records.append(r)
        write_json(output/'mechanism_results.json', records)
        print(s.name+': '+', '.join(f'{r["algorithm"]}={r["audit"]["length"] if r["audit"] else r["reason"]}'
              for r in records[-4:]), flush=True)
    comparisons = {}
    for kind in ('G', 'S'):
        counts = Counter()
        for d in data:
            pair = {r['algorithm']: r for r in records if r['case'] == d['name'] and r['audit'] and r['audit']['valid']}
            if kind+'_free' not in pair or kind+'_locked' not in pair:
                continue
            a, b = pair[kind+'_free']['audit']['length'], pair[kind+'_locked']['audit']['length']
            counts['free_shorter' if a < b else 'locked_shorter' if b < a else 'equal'] += 1
        comparisons[kind] = dict(counts)
    sensitivity, variants = [], []
    for d in data:
        original = deserialize(d)
        if environment_check(original):
            continue
        meta = d['metadata']
        for radius in (1, 2):
            for margin in (1, 2, 3):
                s = sensitivity_snapshot(original, meta, radius, margin)
                variants.append(serialize(s, {'source_case': original.name, 'radius': radius, 'margin': margin}))
                if s.current not in s.free:
                    sensitivity.append({'case': s.name, 'source_case': original.name,
                        'radius': radius, 'margin': margin, 'status': 'incompatible_current', 'route': ()})
                    continue
                result = solve(s, 'P2', 5)
                check = audit(s, result.route) if result.route else None
                sensitivity.append({'case': s.name, 'source_case': original.name,
                    'radius': radius, 'margin': margin, 'status': result.status,
                    'reason': result.reason, 'route': result.route, 'audit': check,
                    'seconds': result.seconds, 'covered_count': len(s.covered),
                    'environment_reason': environment_check(s)})
        write_json(output/'sensitivity_snapshots.json', variants)
        write_json(output/'sensitivity_results.json', sensitivity)
        print('sensitivity '+original.name, flush=True)
    # Replay both strict and skipped routes, then all sensitivity paths.
    cases = {d['name']: deserialize(d) for d in data}
    replay_errors = []
    for r in records:
        if r['route']:
            for route_key, audit_key in [('route', 'audit'), ('skipped_route', 'skipped_audit')]:
                check = audit(cases[r['case']], r[route_key])
                if check != r[audit_key] or not check['valid']:
                    replay_errors.append((r['case'], r['algorithm'], route_key))
    variant_cases = {d['name']: deserialize(d) for d in variants}
    for r in sensitivity:
        s = variant_cases[r['case']]
        if r['route']:
            check = audit(s, r['route'])
            if check != r['audit'] or not check['valid']:
                replay_errors.append((r['case'], 'P2'))
        elif r['status'] == 'environment_infeasible':
            if environment_check(s) != r['reason']:
                replay_errors.append((r['case'], 'infeasible_mismatch'))
        elif r['status'] != 'incompatible_current':
            failures.append((r['case'], 'sensitivity', r['status']))
    summary = {'comparisons': comparisons, 'mechanism_records': len(records),
        'failures': failures, 'replay_errors': replay_errors,
        'mechanism_statuses': dict(Counter(r['status'] for r in records)),
        'sensitivity_records': len(sensitivity),
        'sensitivity_statuses': dict(Counter(r['status'] for r in sensitivity)),
        'skip_reductions': {kind: sum(r['audit']['length'] > r['skipped_audit']['length']
            for r in records if r['algorithm'] == kind and r['route'])
            for kind in ('G_free', 'G_locked', 'S_free', 'S_locked')}}
    write_json(output/'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures or replay_errors:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    run(Path(args.source), Path(args.output))
