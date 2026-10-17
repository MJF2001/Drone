"""Frozen-pool exact-order diagnostics; never calls its value coverage-optimal."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import sys
from collections import Counter, defaultdict
from model import Geometry, DeadlineExceeded
from planners import candidates, nearest, two_opt, sequence_cost
from exact_order import held_karp
from mechanisms import strict_expand
from scenarios import deserialize
from audit import audit
from run_experiments import write_json


def trace_p2(s):
    """Same geometric call sequence as rebuild; no extra distance queries."""
    g = Geometry(s)
    pools = []
    demand = s.targets-s.covered-g.views[s.current]
    for direction in ('H', 'V'):
        points = candidates(g, demand, direction)
        orders = []
        def add(label, order):
            route = g.expand(order)
            orders.append({'label': label, 'visits': list(order), 'original_route': route,
                           'original_audit': audit(s, route)})
        add('snake', points)
        nn = nearest(g, points)
        add('nearest', nn)
        add('snake_2opt', two_opt(g, points))
        add('nearest_2opt', two_opt(g, nn))
        pools.append({'direction': direction, 'points': points, 'heuristics': orders})
    return pools


def score_order(s, order, metric):
    # Strict and coverage-aware executions have separate fresh A* caches.
    proxy = sequence_cost(metric, order)
    strict = strict_expand(Geometry(s), order)
    actual = Geometry(s).expand(order)
    a, b = audit(s, strict), audit(s, actual)
    if not a['valid'] or not b['valid'] or a['length'] != proxy:
        raise AssertionError(('invalid_scoring', s.name, a, b, proxy))
    return {'proxy': proxy, 'strict_route': strict, 'strict_audit': a,
            'actual_route': actual, 'actual_audit': b}


def run(source, output):
    root = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=False)
    archive = output/'source_snapshot'
    archive.mkdir()
    hashes = {}
    for p in sorted(root.glob('*.py'))+[root/'config.json', root/'EXACT_ORDER_PROTOCOL.md']:
        data = p.read_bytes()
        (archive/p.name).write_bytes(data)
        hashes[p.name] = hashlib.sha256(data).hexdigest()
    raw = json.loads((source/'snapshots.json').read_text(encoding='utf-8'))
    previous = json.loads((source/'results.json').read_text(encoding='utf-8'))
    old_p2 = {r['case']: r['audit']['length'] for r in previous if r['algorithm'] == 'P2' and r['audit']}
    write_json(output/'snapshots.json', raw)
    write_json(output/'manifest.json', {'source': str(source.resolve()),
        'input_sha256': hashlib.sha256((source/'snapshots.json').read_bytes()).hexdigest(),
        'source_sha256': hashes, 'python': sys.version, 'max_pool_points': 14,
        'oracle_timeout_seconds': 30, 'held_out': False, 'stage': 'exploratory diagnostic',
        'oracle_objective': 'fixed visits shortest-distance sum, fixed start and base'})
    records, cases, failures = [], [], []
    for d in raw:
        s = deserialize(d)
        pools = trace_p2(s)
        old_check = audit(s, s.old_route)
        original_lengths = [r['original_audit']['length'] for p in pools for r in p['heuristics']
                            if r['original_audit']['valid']]
        if old_check['valid']:
            original_lengths.append(old_check['length'])
        trace_length = min(original_lengths)
        if trace_length != old_p2[s.name]:
            failures.append([s.name, 'p2_trace_mismatch', trace_length, old_p2[s.name]])
        normalized, augmented = [], []
        if old_check['valid']:
            normalized.append(old_check['length'])
            augmented.append(old_check['length'])
        for p in pools:
            metric = Geometry(s)
            for h in p['heuristics']:
                h.update(score_order(s, h['visits'], metric))
            best_proxy = min(h['proxy'] for h in p['heuristics'])
            best_actual = min(h['actual_audit']['length'] for h in p['heuristics'])
            normalized.append(best_actual)
            augmented.append(best_actual)
            r = {'case': s.name, 'direction': p['direction'], 'points': p['points'],
                 'point_count': len(p['points']), 'heuristics': p['heuristics'],
                 'best_heuristic_proxy': best_proxy, 'best_heuristic_actual': best_actual}
            if len(p['points']) > 14:
                r['oracle_status'] = 'size_limit'
            else:
                begin = time.perf_counter()
                try:
                    exact_g = Geometry(s, begin+30)
                    points = p['points']
                    start = [exact_g.distance(s.current, q) for q in points]
                    between = [[exact_g.distance(a,b) for b in points] for a in points]
                    end = [exact_g.distance(q,s.base) for q in points]
                    indices, optimum = held_karp(start, between, end, exact_g.check_time,
                                                empty_cost=exact_g.distance(s.current,s.base))
                    elapsed = time.perf_counter()-begin
                    visits = [points[i] for i in indices]
                    score = score_order(s, visits, Geometry(s))
                    if score['proxy'] != optimum or best_proxy < optimum:
                        failures.append([s.name, p['direction'], 'oracle_cost_inconsistent'])
                    r.update(oracle_status='optimal', oracle_seconds=elapsed,
                        exact_indices=indices, exact_visits=visits, exact=score,
                        proxy_gap=best_proxy-optimum,
                        actual_delta=score['actual_audit']['length']-best_actual)
                    augmented.append(score['actual_audit']['length'])
                except DeadlineExceeded:
                    r.update(oracle_status='timeout', oracle_seconds=time.perf_counter()-begin)
            records.append(r)
        cases.append({'case': s.name, 'stored_p2_length': old_p2[s.name],
            'traced_p2_length': trace_length, 'normalized_p2_candidates_length': min(normalized),
            'with_exact_proxy_candidate_length': min(augmented),
            'eligible_pools': sum(r['oracle_status'] == 'optimal' for r in records if r['case'] == s.name)})
        write_json(output/'pool_results.json', records)
        write_json(output/'case_results.json', cases)
        print(s.name+': '+', '.join(f'{r["direction"]} n={r["point_count"]} {r["oracle_status"]}'+
              (f' proxy_gap={r["proxy_gap"]}, actual_delta={r["actual_delta"]}' if r['oracle_status']=='optimal' else '')
              for r in records[-2:]), flush=True)
    exact = [r for r in records if r['oracle_status'] == 'optimal']
    summary = {'snapshot_count': len(cases), 'pool_count': len(records),
        'oracle_statuses': dict(Counter(r['oracle_status'] for r in records)),
        'pool_size_distribution': dict(Counter(r['point_count'] for r in records)),
        'proxy_gap_counts': dict(Counter('equal' if r['proxy_gap']==0 else 'heuristic_longer' for r in exact)),
        'actual_exact_vs_best_heuristic': dict(Counter('equal' if r['actual_delta']==0 else
            'exact_shorter' if r['actual_delta']<0 else 'exact_longer' for r in exact)),
        'max_proxy_gap': max((r['proxy_gap'] for r in exact), default=None),
        'candidate_addition_improved_cases': sum(c['with_exact_proxy_candidate_length']<c['normalized_p2_candidates_length'] for c in cases),
        'affected_normalized_vs_original_cases': sum(c['normalized_p2_candidates_length']!=c['stored_p2_length'] for c in cases),
        'trace_all_matches': not any(f[1] == 'p2_trace_mismatch' for f in failures),
        'failures': failures, 'held_out': False}
    write_json(output/'summary.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', required=True)
    p.add_argument('--output', required=True)
    args = p.parse_args()
    run(Path(args.source), Path(args.output))
