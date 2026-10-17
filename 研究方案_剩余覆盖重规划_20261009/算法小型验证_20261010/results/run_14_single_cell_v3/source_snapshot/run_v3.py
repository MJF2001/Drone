"""Fresh single-cell snapshots and P1/P2 comparison; no historical files overwritten."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
from scenarios_v3 import all_cases_v3
from scenarios import serialize
from planners import solve
from audit import audit, environment_check
from run_experiments import write_json


def run(out):
    root = Path(__file__).resolve().parent
    out.mkdir(parents=True, exist_ok=False)
    archive = out/'source_snapshot'
    archive.mkdir()
    sources = list(root.glob('*.py'))
    sources.append(root.parent/'论文资料汇总_三篇文献与论文主题_20261009'/'19_单格正下方采集与障碍遮挡设定_20261010.md')
    hashes = {}
    for p in sources:
        data = p.read_bytes()
        (archive/p.name).write_bytes(data)
        hashes[p.name] = hashlib.sha256(data).hexdigest()
    write_json(out/'manifest.json', {'model': 'v0.3 single-cell downward; blocked unfinished targets deferred',
        'python': sys.version, 'source_sha256': hashes, 'held_out': False,
        'algorithms': ['P1', 'P2'], 'capture_radius': 0, 'time_limit_seconds': 5,
        'repetitions': 1, 'budget': '4 * fixed D cardinality',
        'initial_history_regenerated': True, 'physical_calibration': None})
    cases = list(all_cases_v3())
    write_json(out/'snapshots.json', [serialize(s, meta) for s, meta in cases])
    rows, failures = [], []
    for index, (s, meta) in enumerate(cases):
        reason = environment_check(s)
        for name in (('P1', 'P2') if index%2 == 0 else ('P2', 'P1')):
            result = solve(s, name, 5)
            check = audit(s, result.route) if result.route else None
            correct = (result.status == 'environment_infeasible' and result.reason == reason) if reason else bool(
                check and check['valid'] and result.status in ('planned', 'planned_at_timeout'))
            row = {'case': s.name, 'family': meta['family'], 'domain_kind': meta['domain_kind'],
                'algorithm': name, 'status': result.status, 'reason': result.reason,
                'seconds': result.seconds, 'searches': result.searches,
                'route': result.route, 'audit': check, 'expected_case_handled': correct,
                'deferred_count': meta['deferred_count'],
                'active_pending_count': meta['active_pending_count']}
            rows.append(row)
            if not correct:
                failures.append({k: row[k] for k in ('case', 'algorithm', 'status', 'reason')})
        write_json(out/'results.json', rows)
        print(s.name+': '+', '.join(f'{r["algorithm"]}={r["audit"]["length"] if r["audit"] else r["status"]}'
            for r in rows[-2:])+f', deferred={meta["deferred_count"]}', flush=True)
    pairs = defaultdict(dict)
    for r in rows:
        if r['audit'] and r['audit']['valid']:
            pairs[r['case']][r['algorithm']] = r['audit']['length']
    wins, families = Counter(), defaultdict(Counter)
    totals = Counter()
    for s, meta in cases:
        pair = pairs[s.name]
        if len(pair) == 2:
            key = 'P1_shorter' if pair['P1'] < pair['P2'] else 'P2_shorter' if pair['P2'] < pair['P1'] else 'equal'
            wins[key] += 1
            families[meta['family']][key] += 1
            totals.update(pair)
    summary = {'snapshot_count': len(cases), 'execution_count': len(rows), 'failures': failures,
        'wins': dict(wins), 'by_family': dict(families), 'paired_step_totals': dict(totals),
        'statuses': dict(Counter(r['status'] for r in rows)),
        'environment_reasons': dict(Counter(str(environment_check(s)) for s, meta in cases)),
        'cases_with_deferred_targets': sum(meta['deferred_count'] > 0 for s, meta in cases),
        'deferred_counts_across_snapshots': sum(meta['deferred_count'] for s, meta in cases),
        'old_route_collision_count': sum(meta['old_route_collision'] for s, meta in cases),
        'remaining_target_components': dict(Counter(meta['remaining_target_components'] for s, meta in cases)),
        'timing': {name: {'median_seconds': statistics.median(r['seconds'] for r in rows if r['algorithm'] == name),
            'max_seconds': max(r['seconds'] for r in rows if r['algorithm'] == name)} for name in ('P1', 'P2')},
        'held_out': False}
    write_json(out/'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    run(Path(p.parse_args().output))
