"""Read-only evidence verification. Imports no planner or probe module."""
import hashlib
import itertools
import json
from pathlib import Path
from collections import Counter, deque

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def read(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parts(cells):
    if not cells:
        yield []
        return
    p = min(cells)
    for axis, dx, dy in [('H', 1, 0), ('V', 0, 1)]:
        q, segment = p, []
        while q in cells:
            segment.append(q)
            for tail in parts(cells - set(segment)):
                yield [(axis, tuple(segment))] + tail
            q = q[0]+dx, q[1]+dy


def measure(part, old, cells):
    endpoints = lambda pp: {(a, side, seg[i]) for a, seg in pp for side, i in [(0, 0), (1, -1)]}
    before = {e for e in endpoints(old) if e[2] in cells}
    after = endpoints(part)
    directions = {p: a for a, seg in part for p in seg}
    changed = len(after-before) + sum(directions[p] == a for a, side, p in before-after)/2
    return len(part), changed


def main():
    result, plan = read('probe_results.json'), read('planned_inputs.json')
    assert len(plan) == 10
    cases = {c['case_id']: c for c in plan}
    expected_runs = {f'{c}_cap{cap}_repair{repair}' for c in cases for cap in (0,1,2,6) for repair in (0,1)}
    assert {r['run_id'] for r in result['rank']} == expected_runs
    assert len(result['rank']) == len(expected_runs) == 80
    for r in result['rank']:
        case = cases[r['case_id']]
        cells = {tuple(p) for p in case['cells']}
        old = [(a, tuple(map(tuple, seg))) for a,seg in case['old']]
        values = []
        for part in parts(cells):
            m, bound = measure(part, old, cells)
            if bound <= r['cap']:
                values.append(m + bound/(r['cap']+1))
        expected = min(values) if values else None
        assert r['oracle']['objective'] == expected
        if 'ranks' in r['actual']:
            part = [(a, tuple(map(tuple, seg))) for a,seg in r['actual']['ranks']]
            flat = [p for a,seg in part for p in seg]
            assert Counter(flat) == Counter(cells)
            for axis, seg in part:
                dx,dy = (1,0) if axis == 'H' else (0,1)
                assert all((b[0]-a[0],b[1]-a[1]) == (dx,dy) for a,b in zip(seg,seg[1:]))
            m,bound = measure(part,old,cells)
            assert bound <= r['cap'] and abs(m+bound/(r['cap']+1)-expected) < 1e-7
            match = True
        else:
            match = expected is None and r['actual']['status'] == 'infeasible'
        assert match == r['matches_physical_oracle']
    exceptions = [r['run_id'] for r in result['rank'] if not r['matches_physical_oracle']]
    assert exceptions == ['line_expanded_cap1_repair0']
    assert sum(bool(r['actual'].get('certification_repair')) for r in result['rank']) == 1
    history = result['history']
    assert [r['native_keys_equal'] for r in history['roundtrips']] == [True,False,False,False]
    for row in history['roundtrips']:
        targets = Counter(tuple(p) for a,seg in row['native'] for p in seg)
        recovered = Counter(tuple(p) for a,seg in row['recovered'] for p in seg)
        assert recovered == targets
    assert history['connector']['preserves_exact_path'] and history['connector']['blocked_connector_splits']
    for r in result['gtsp']:
        route = list(map(tuple,r['route']))
        assert route[0] == (0,4) and route[-1] == (4,4)
        assert all(0<=x<5 and 0<=y<5 and (x,y)!=(2,3) for x,y in route)
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a,b in zip(route,route[1:]))
        assert {tuple(p) for block in r['blocks'] for p in block['path']} <= set(route)
        assert r['cost'] == r['brute_cost'] == len(route)-1
        assert r['matches_brute'] and r['physical_valid']
        def distance(a,b):
            queue, seen = deque([(a,0)]), {a}
            while queue:
                (x,y), steps = queue.popleft()
                if (x,y) == b:
                    return steps
                for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if 0<=q[0]<5 and 0<=q[1]<5 and q!=(2,3) and q not in seen:
                        seen.add(q)
                        queue.append((q,steps+1))
            raise AssertionError('unreachable verifier fixture')
        options = []
        groups = len(r['blocks'])
        for order in itertools.permutations(range(groups)):
            for direction in itertools.product((0,1), repeat=groups):
                cursor, length = (0,4), 0
                for k in order:
                    service = list(map(tuple,r['blocks'][k]['path']))
                    if direction[k]:
                        service.reverse()
                    length += distance(cursor,service[0]) + len(service)-1
                    cursor = service[-1]
                options.append(length + distance(cursor,(4,4)))
        assert min(options) == r['cost'] and len(options) == r['enumerated_orders']
    events = [json.loads(line) for line in (HERE/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    starts, ends = {}, {}
    active = set()
    for e in events:
        table = starts if e['event'] == 'start' else ends
        assert e['run_id'] not in table
        table[e['run_id']] = e
        if e['event'] == 'start':
            if e.get('kind') == 'scip_optimize':
                assert e['parent'] in active
            active.add(e['run_id'])
        else:
            assert e['run_id'] in active
            active.remove(e['run_id'])
    assert not active
    assert starts.keys() == ends.keys()
    assert not any('error' in e for e in ends.values())
    kinds = Counter(e['kind'] for e in starts.values())
    assert kinds == {'rank_replan':80,'scip_optimize':81,'exact_gtsp':4}
    assert set(e['run_id'] for e in starts.values() if e['kind']=='rank_replan') == expected_runs
    for e in starts.values():
        if e['kind'] == 'scip_optimize':
            assert e['parent'] in expected_runs
    before, after = read('frozen_before.json'), read('frozen_after.json')
    assert before == after
    assert all(digest(ROOT/p) == value for p,value in before.items())
    assert all(digest(HERE/p) == value for p,value in read('pre_run_seal.json').items())
    summary = result['summary']
    assert summary['rank_top_level_calls'] == kinds['rank_replan']
    assert summary['scip_optimize_calls'] == kinds['scip_optimize']
    assert summary['exact_gtsp_calls'] == kinds['exact_gtsp']
    assert summary['strict_oracle_matches'] == 39 and summary['repair_enabled_oracle_matches'] == 40
    assert summary['performance_calls'] == summary['glns_calls'] == 0
    if (HERE/'delivery_manifest.json').exists():
        assert all(digest(HERE/p) == value for p,value in read('delivery_manifest.json').items())
    print(json.dumps({'verification':'PASS','paired_ledger_entries':len(starts),
                      'rank_cases':80,'scip_optimize':81,'exact_gtsp':4,
                      'known_strict_model_decoder_rejection':exceptions,
                      'protected_sources':len(before),'new_planner_calls':0},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
