"""Bounded mechanism checks; writes only beside this script; -B required.

No production adapter, developer-map batch, GLNS search, or holdout is run.
The independent enumerator deliberately does not use the frozen oracle.
"""
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time
from collections import Counter, deque
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REF = ROOT / 'DeepSeek_底层算法开发比较_20261018/sources/reference_tree'
ALGO = REF / '研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
FROZEN = ALGO / 'frozen_baselines/v2_20261012'
sys.dont_write_bytecode = True
sys.path[:0] = [str(FROZEN / 'source'), str(ALGO / '.deps')]
from oarp_replan import ranks as core
from oarp_replan import tour as touring


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes():
    paths = sorted((FROZEN / 'source').rglob('*.py')) + [FROZEN / 'runtime_profile.json']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def independent_partitions(points):
    # Pick the first uncovered cell, then every positive horizontal/vertical
    # segment starting there. Every disjoint rank cover is reached once.
    if not points:
        yield ()
        return
    p = min(points)
    for axis, delta in [('H', (1, 0)), ('V', (0, 1))]:
        q, segment = p, []
        while q in points:
            segment.append(q)
            for rest in independent_partitions(points - set(segment)):
                yield ((axis, tuple(segment)),) + rest
            q = q[0] + delta[0], q[1] + delta[1]


def independent_metrics(part, old, current):
    def ends(parts):
        return {(axis, side, segment[index]) for axis, segment in parts
                for side, index in [('begin', 0), ('end', -1)]}
    previous = {e for e in ends(old) if e[2] in current}
    present = ends(part)
    direction = {p: axis for axis, segment in part for p in segment}
    alpha = len(present - previous)
    beta = sum(direction[p] == axis for axis, side, p in previous - present)
    keys = {(axis, segment[0], segment[-1]) for axis, segment in old}
    return {'rank_count': len(part), 'added': alpha, 'extended': beta,
            'bound': alpha + beta / 2,
            'new': sum((axis, seg[0], seg[-1]) not in keys for axis, seg in part)}


def independent_oracle(points, old, cap):
    best, witnesses, total = None, [], 0
    for part in independent_partitions(set(points)):
        total += 1
        m = independent_metrics(part, old, points)
        assert m['new'] <= m['bound']
        if m['bound'] > cap:
            continue
        obj = m['rank_count'] + m['bound'] / (cap + 1)
        if best is None or obj < best - 1e-9:
            best, witnesses = obj, [part]
        elif abs(obj - best) < 1e-9:
            witnesses.append(part)
    return {'objective': best, 'witnesses': witnesses, 'partitions_enumerated': total}


def define_cases():
    line = lambda n, y=0: tuple((x, y) for x in range(n))
    box = {(x, y) for x in range(3) for y in range(2)}
    return [
        ('line_unchanged', set(line(4)), [('H', line(4))]),
        ('line_blocked', {(0, 0), (2, 0)}, [('H', line(3))]),
        ('line_expanded', set(line(4)), [('H', line(3))]),
        ('square_h', {(x, y) for x in range(2) for y in range(2)},
         [('H', line(2, y)) for y in range(2)]),
        ('box_missing_top_middle', box - {(1, 1)}, [('H', line(3, y)) for y in range(2)]),
        ('L_shape', {(0, 0), (1, 0), (2, 0), (0, 1), (0, 2)},
         [('H', line(3)), ('H', ((0, 1),)), ('H', ((0, 2),))]),
        ('square_v', {(x, y) for x in range(2) for y in range(2)},
         [('V', ((x, 0), (x, 1))) for x in range(2)]),
        ('line_retained_cut', set(line(4)), [('H', line(2)), ('H', ((2, 0), (3, 0)))]),
        ('singleton_v', {(0, 0)}, [('V', ((0, 0),))]),
        ('executed_prefix', {(2, 0), (3, 0)}, [('H', line(4))]),
    ]


def json_case(case):
    name, points, old = case
    return {'case_id': name, 'cells': sorted(points), 'old': old}


def record(event):
    with (HERE / 'calls.jsonl').open('a', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


ACTIVE = None
OPTIMIZES = 0
ORIGINAL_BUILD = core._build


class LoggedModel:
    def __init__(self, model, label):
        self.model, self.label = model, label

    def __getattr__(self, key):
        return getattr(self.model, key)

    def optimize(self):
        global OPTIMIZES
        OPTIMIZES += 1
        if OPTIMIZES > 320:
            raise RuntimeError('predeclared optimize ceiling exceeded')
        key = f'scip_{OPTIMIZES:03}'
        record({'event': 'start', 'run_id': key, 'parent': ACTIVE, 'kind': 'scip_optimize', **self.label})
        try:
            self.model.optimize()
        except BaseException as exc:
            record({'event': 'end', 'run_id': key, 'error': repr(exc)})
            raise
        record({'event': 'end', 'run_id': key, 'status': str(self.model.getStatus())})


def logged_build(*args, **kwargs):
    values = ORIGINAL_BUILD(*args, **kwargs)
    label = {'integer': bool(args[4]), 'certified': bool(args[6]) if len(args) > 6 else False}
    return (LoggedModel(values[0], label),) + values[1:]


def rank_checks(cases):
    global ACTIVE
    rows = []
    for case_id, cells, old_spec in cases:
        old = tuple(core.Rank(axis, segment) for axis, segment in old_spec)
        for cap in (0, 1, 2, 6):
            expected = independent_oracle(cells, old_spec, cap)
            for repair in (False, True):
                ACTIVE = f'{case_id}_cap{cap}_repair{int(repair)}'
                record({'event': 'start', 'run_id': ACTIVE, 'kind': 'rank_replan', 'case_id': case_id,
                        'cap': cap, 'allow_repair': repair})
                started = time.perf_counter()
                try:
                    got = core.rank_replan(cells, old, cap, 2, deadline=started + 5,
                                           allow_certification_repair=repair)
                    encoded = {k: v for k, v in got.items() if k != 'ranks'}
                    if got['ranks'] is not None:
                        part = [(r.axis, r.cells) for r in got['ranks']]
                        flat = [p for axis, seg in part for p in seg]
                        m = independent_metrics(part, old_spec, cells)
                        certified = len(flat) == len(set(flat)) and set(flat) == cells and m['bound'] <= cap
                        obj = m['rank_count'] + m['bound'] / (cap + 1)
                        match = certified and expected['objective'] is not None and abs(obj - expected['objective']) < 1e-7
                        encoded.update(ranks=part, independent_metrics=m, independent_valid=certified)
                    else:
                        match = expected['objective'] is None and got['status'] == 'infeasible'
                    row = {'run_id': ACTIVE, 'case_id': case_id, 'cap': cap, 'allow_repair': repair,
                           'oracle': expected, 'actual': encoded, 'matches_physical_oracle': match}
                    rows.append(row)
                    record({'event': 'end', 'run_id': ACTIVE, 'status': got['status'], 'matches_oracle': match})
                except BaseException as exc:
                    record({'event': 'end', 'run_id': ACTIVE, 'error': repr(exc)})
                    raise
    return rows


def rank_key(axis, segment):
    return axis, segment[0], segment[-1]


def history_checks():
    specs = [
        ('horizontal_positive', [('H', ((0, 0), (1, 0))), ('H', ((0, 1), (1, 1)))],
         ((0, 0), (1, 0), (1, 1), (0, 1))),
        ('vertical_singleton', [('V', ((0, 0),))], ((0, 0),)),
        ('vertical_remaining_singleton', [('V', ((0, 1),))], ((0, 1), (0, 0))),
        ('connector_first_visits_future_rank',
         [('H', ((0, 0), (1, 0))), ('H', ((0, 2), (1, 2))), ('V', ((2, 0), (2, 1), (2, 2)))],
         ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2),
          (0, 1), (0, 0), (1, 0), (2, 0), (2, 1), (2, 2))),
    ]
    rows = []
    for case_id, spec, route in specs:
        targets = {p for axis, segment in spec for p in segment}
        assert all(abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1 for a, b in zip(route, route[1:]))
        recovered = touring.old_services(route, targets)
        native_keys = {rank_key(axis, segment) for axis, segment in spec}
        recovered_keys = {r.rank.key for r in recovered}
        rows.append({'case_id': case_id, 'native': spec, 'route': route,
                     'recovered': [(s.rank.axis, s.rank.cells) for s in recovered],
                     'native_keys_equal': native_keys == recovered_keys,
                     'exact_target_partition': Counter(p for s in recovered for p in s.rank.cells) == Counter(targets),
                     'retained_native_rank_count': len(native_keys & recovered_keys)})
    # Same retained ranks, but an obstacle on the connector must break the block.
    a = core.Rank('H', ((0, 0), (1, 0)))
    b = core.Rank('H', ((0, 2), (1, 2)))
    route = ((0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2))
    services = (touring.OldService(a, 0, 1), touring.OldService(b, 5, 6))
    intact = touring.path_sets((a, b), services, route, set(route))
    blocked = touring.path_sets((a, b), services, route, set(route) - {(2, 1)})
    return {'roundtrips': rows, 'connector': {'intact': intact, 'blocked': blocked,
            'preserves_exact_path': len(intact) == 1 and intact[0]['path'] == route,
            'blocked_connector_splits': len(blocked) == 2}}


class Grid:
    def __init__(self, free, current, base):
        self.free = set(free)
        self.s = SimpleNamespace(current=current, base=base)

    def check_time(self):
        pass

    def path(self, start, end):
        queue, prev = deque([start]), {start: None}
        while queue:
            p = queue.popleft()
            if p == end:
                route = []
                while p is not None:
                    route.append(p)
                    p = prev[p]
                return tuple(reversed(route))
            for q in sorted(((p[0]+1,p[1]),(p[0]-1,p[1]),(p[0],p[1]+1),(p[0],p[1]-1))):
                if q in self.free and q not in prev:
                    prev[q] = p
                    queue.append(q)
        raise ValueError('disconnected microfixture')

    def distance(self, a, b):
        return len(self.path(a, b)) - 1


def gtsp_checks():
    global ACTIVE
    rows = []
    for groups in (1, 2, 3, 4):
        free = {(x, y) for x in range(5) for y in range(5)} - {(2, 3)}
        grid = Grid(free, (0, 4), (4, 4))
        blocks = [{'kind': 'rank', 'path': ((1, y), (2, y), (3, y)), 'rank_keys': []}
                  for y in range(groups)]
        if groups == 4:
            blocks[-1]['path'] = ((0, 2), (0, 3), (0, 4))
        states, sets, matrix, start, end, penalty = touring.gtsp_instance(grid, blocks)
        ACTIVE = f'exact_gtsp_groups{groups}'
        record({'event': 'start', 'run_id': ACTIVE, 'kind': 'exact_gtsp'})
        try:
            value, order = touring.exact_gtsp(matrix, sets, start, end)
            route, decoded, cycle = touring.decode_tour(grid, states, sets, matrix, start, end, order, penalty)
            record({'event': 'end', 'run_id': ACTIVE, 'cost': value})
        except BaseException as exc:
            record({'event': 'end', 'run_id': ACTIVE, 'error': repr(exc)})
            raise
        brute, candidates = math.inf, 0
        for permutation in itertools.permutations(range(groups)):
            for directions in itertools.product((0, 1), repeat=groups):
                cursor, length = grid.s.current, 0
                for k in permutation:
                    path = blocks[k]['path'][::(-1 if directions[k] else 1)]
                    length += grid.distance(cursor, path[0]) + len(path) - 1
                    cursor = path[-1]
                length += grid.distance(cursor, grid.s.base)
                brute = min(brute, length)
                candidates += 1
        physical = (route[0] == grid.s.current and route[-1] == grid.s.base
                    and set(route) <= free and all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1
                    for a,b in zip(route, route[1:]))
                    and {p for b in blocks for p in b['path']} <= set(route))
        rows.append({'run_id': ACTIVE, 'blocks': blocks, 'route': route, 'cost': value,
                     'brute_cost': brute, 'enumerated_orders': candidates,
                     'matches_brute': value == brute == decoded == len(route)-1,
                     'physical_valid': physical})
    return rows


def main():
    if (HERE / 'calls.jsonl').exists():
        raise SystemExit('Refuse rerun: prior ledger exists; inspect it instead.')
    cases = define_cases()
    before = source_hashes()
    dump(HERE / 'frozen_before.json', before)
    dump(HERE / 'planned_inputs.json', [json_case(c) for c in cases])
    seal = {p.name: sha(p) for p in [HERE / '核验协议.md', Path(__file__), HERE / 'planned_inputs.json']}
    dump(HERE / 'pre_run_seal.json', seal)
    core._build = logged_build
    rank_rows = rank_checks(cases)
    history = history_checks()
    gtsp = gtsp_checks()
    after = source_hashes()
    dump(HERE / 'frozen_after.json', after)
    summary = {'rank_top_level_calls': len(rank_rows), 'scip_optimize_calls': OPTIMIZES,
               'exact_gtsp_calls': len(gtsp), 'performance_calls': 0, 'glns_calls': 0,
               'original_source_hashes_unchanged': before == after,
               'source_files_protected': len(before),
               'strict_oracle_matches': sum(r['matches_physical_oracle'] for r in rank_rows if not r['allow_repair']),
               'repair_enabled_oracle_matches': sum(r['matches_physical_oracle'] for r in rank_rows if r['allow_repair']),
               'repairs_activated': sum(bool(r['actual'].get('certification_repair')) for r in rank_rows),
               'gtsp_checks_passed': all(r['matches_brute'] and r['physical_valid'] for r in gtsp)}
    dump(HERE / 'probe_results.json', {'summary': summary, 'rank': rank_rows, 'history': history, 'gtsp': gtsp})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
