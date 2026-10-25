"""Read-only independent checker. Slab geometry, ratio service, rational bisection.
No import of selector, main geometry, radical implementation, or any planner.
"""
from fractions import Fraction as R
from math import ceil, floor
from copy import deepcopy

class Invalid(ValueError):
    pass

def number(x):
    if not isinstance(x, dict) or set(x) != {'n', 'd'}:
        raise Invalid('rational_schema')
    if type(x['n']) != int or type(x['d']) != int or x['d'] < 1:
        raise Invalid('rational_value')
    return R(x['n'], x['d'])

def pos(x, grid=False):
    if not isinstance(x, (list, tuple)) or len(x) != 2:
        raise Invalid('coordinate_schema')
    if grid:
        if any(type(v) != int for v in x):
            raise Invalid('grid_coordinate_value')
        return tuple(R(v) for v in x)
    return tuple(number(v) for v in x)

def cellset(raw):
    if not isinstance(raw, (list, tuple)):
        raise Invalid('cellset_schema')
    values = [pos(p, True) for p in raw]
    if len(set(values)) != len(values):
        raise Invalid('duplicate_cell')
    return set(values)

def canon(n):
    if type(n) != int or n < 1:
        raise Invalid('radicand')
    # Separate division-by-prime traversal (main traverses every integer).
    factor, radical, p, work = 1, 1, 2, 0
    while n > 1 and p*p <= n:
        work += 1
        if work > 100000:
            raise Invalid('uncertain_factor')
        e = 0
        while n % p == 0:
            e += 1
            n //= p
        factor *= p**(e//2)
        if e & 1:
            radical *= p
        p = 3 if p == 2 else p+2
    return factor, radical*n

def add(a, b, sign=1):
    out = dict(a)
    for r, c in b.items():
        out[r] = out.get(r, R(0))+sign*c
        if out[r] == 0:
            del out[r]
    return out

def load(x):
    if not isinstance(x, dict) or set(x) != {'terms'} or not isinstance(x['terms'], list):
        raise Invalid('expression_schema')
    out = {}
    for t in x['terms']:
        if not isinstance(t, dict) or set(t) != {'r', 'c'}:
            raise Invalid('term_schema')
        a, b = canon(t['r'])
        out = add(out, {b: a*number(t['c'])})
    return out

def enclose(e, bits=96):
    low = high = R(0)
    for n, coefficient in e.items():
        if n == 1:
            l = u = R(1)
        else:
            l, u = R(0), R(n+1)
            for _ in range(bits+(n+1).bit_length()+1):
                m = (l+u)/2
                if m*m <= n:
                    l = m
                else:
                    u = m
        low += coefficient*(l if coefficient >= 0 else u)
        high += coefficient*(u if coefficient >= 0 else l)
    return low, high

def sign(e):
    if not e:
        return 0
    if set(e) <= {1}:
        return 1 if e[1] > 0 else -1
    for bits in (32, 64, 128, 256, 512):
        l, u = enclose(e, bits)
        if l > 0:
            return 1
        if u < 0:
            return -1
    raise Invalid('uncertain_sign')

def floor_exact(e):
    if set(e) <= {1}:
        return floor(e.get(1, R(0)))
    for bits in (32, 64, 128, 256, 512):
        l, u = enclose(e, bits)
        if floor(l) == floor(u):
            return floor(l)
    raise Invalid('uncertain_floor')

def metric(a, b, counts):
    counts['independent_distance'] += 1
    dx, dy = b[0]-a[0], b[1]-a[1]
    square = dx*dx+dy*dy
    if not square:
        return {}, square
    f, r = canon(square.numerator*square.denominator)
    return {r: R(f, square.denominator)}, square

def certified(saved, expected):
    assert load(saved['exact']) == expected, 'radical_expression_mismatch'
    low, high = number(saved['low']), number(saved['high'])
    l, u = enclose(expected, 96)
    assert low <= l <= u <= high, 'radical_interval_not_enclosing'

def intersects_box(a, b, x0, x1, y0, y1):
    lo, hi = R(0), R(1)
    for i, left, right in ((0, x0, x1), (1, y0, y1)):
        d = b[i]-a[i]
        if not d:
            if a[i] < left or a[i] > right:
                return False
        else:
            t, u = (left-a[i])/d, (right-a[i])/d
            lo, hi = max(lo, min(t, u)), min(hi, max(t, u))
            if lo > hi:
                return False
    return True

def legal(F, a, b, c):
    c['independent_geometry'] += 1
    # F was validated as integer centers; convert only its denominator-1 extrema.
    # S/a/b remain exact rational and are never rounded.
    xmin, xmax = int(min(x for x, y in F)), int(max(x for x, y in F))
    ymin, ymax = int(min(y for x, y in F)), int(max(y for x, y in F))
    half = R(1, 2)
    if any(not (xmin-half < p[0] < xmax+half and ymin-half < p[1] < ymax+half) for p in (a, b)):
        return False
    for x in range(max(xmin, ceil(min(a[0], b[0])-half)), min(xmax, floor(max(a[0], b[0])+half))+1):
        for y in range(max(ymin, ceil(min(a[1], b[1])-half)), min(ymax, floor(max(a[1], b[1])+half))+1):
            if (x, y) not in F:
                c['independent_forbidden_box_checks'] += 1
                if intersects_box(a, b, x-half, x+half, y-half, y+half):
                    return False
    return True

def hit(a, b, p, c):
    c['independent_service_intersections'] += 1
    ratios = []
    for i in (0, 1):
        if a[i] == b[i]:
            if p[i] != a[i]:
                return None
        else:
            ratios.append((p[i]-a[i])/(b[i]-a[i]))
    if not ratios:
        return R(0)
    t = ratios[0]
    return t if 0 <= t <= 1 and all(v == t for v in ratios) else None

def state(raw, c):
    if not isinstance(raw, dict) or not {'S', 'h', 'F', 'P', 'H', 'D', 'base', 'E', 'M'} <= set(raw):
        raise Invalid('missing_field')
    s = {k: cellset(raw[k]) for k in ('F', 'P', 'H', 'D')}
    # Raw inputs have a 40-bit size bound; saved certified endpoints may be larger.
    for coord in (raw['S'], raw['h']):
        if isinstance(coord, (tuple, list)):
            for value in coord:
                number(value)
                if abs(value['n']).bit_length() > 40 or value['d'].bit_length() > 40:
                    raise Invalid('rational_size_limit_40_bits')
    for key in ('E', 'M'):
        for term in raw[key].get('terms', []):
            value = term['c']
            number(value)
            if abs(value['n']).bit_length() > 40 or value['d'].bit_length() > 40:
                raise Invalid('rational_size_limit_40_bits')
    s.update(S=pos(raw['S']), h=pos(raw['h']), base=pos(raw['base'], True), E=load(raw['E']), M=load(raw['M']))
    if not s['F'] or len(s['F']) > 25:
        raise Invalid('free_cell_bound')
    if len(s['P']) > 25 or any(abs(v) > 100 for p in s['F'] | s['P'] for v in p):
        raise Invalid('fixture_domain_bound')
    if any(abs(v) > 100 for v in s['S']):
        raise Invalid('fixture_position_bound')
    if s['h'] == (0, 0) or s['base'] not in s['F'] or not s['H'] <= s['P']:
        raise Invalid('state_semantics')
    if s['D'] != s['P']-s['F']-s['H']:
        raise Invalid('deferred_semantics')
    if sign(s['E']) < 0 or sign(s['M']) < 0:
        raise Invalid('negative_resource')
    if not legal(s['F'], s['S'], s['S'], c):
        raise Invalid('unsafe_given_stop')
    return s

def check_state(saved, s):
    assert pos(saved['S']) == s['S'] and pos(saved['h']) == s['h']
    for k in ('F', 'P', 'H', 'D'):
        assert cellset(saved[k]) == s[k], k
    assert pos(saved['base'], True) == s['base']
    certified(saved['E'], s['E'])
    certified(saved['M'], s['M'])

def collect(s):
    p = s['S']
    if p in s['F'] and p in s['P'] and p not in s['H']:
        s['H'].add(p)
        return [{'kind': 'collect_here', 'cell': [int(v) for v in p]}]
    return []

def service(s, a, b, c):
    events = []
    # Test all public tasks (including H/deferred) independently, filter after hit.
    for p in s['P']:
        t = hit(a, b, p, c)
        if t is not None and t > 0 and p in s['F'] and p not in s['H']:
            events.append((t, p))
    events.sort()
    out = []
    for t, p in events:
        s['H'].add(p)
        out.append({'kind': 'arrival', 't': {'n': t.numerator, 'd': t.denominator}, 'cell': [int(v) for v in p]})
    s['D'] = s['P']-s['F']-s['H']
    return out

def suffix(s, q, response, c):
    if not isinstance(response, dict) or response.get('stub') != 'HANDWRITTEN_FIXED_RESPONSE':
        return 'stub_identity', None
    kind = response.get('kind')
    if kind not in ('native_grid', 'manual_polyline'):
        return 'suffix_kind', None
    rawpoints = response.get('points')
    if not isinstance(rawpoints, (list, tuple)) or not 1 <= len(rawpoints) <= 33:
        return 'suffix_size', None
    try:
        ps = [pos(p, True) for p in rawpoints]
    except Invalid as e:
        return str(e), None
    if ps[0] != q or ps[-1] != s['base']:
        return 'suffix_endpoints', None
    if kind == 'native_grid' and any(abs(a[0]-b[0])+abs(a[1]-b[1]) not in (0, 1) for a, b in zip(ps, ps[1:])):
        return 'native_nonunit', None
    if any(p not in s['F'] for p in ps):
        return 'suffix_vertex_blocked', None
    full = [s['S']]+ps
    f = deepcopy(s)
    events, length, squares = collect(f), {}, []
    for a, b in zip(full, full[1:]):
        if not legal(s['F'], a, b, c):
            return 'suffix_geometry', None
        l, sq = metric(a, b, c)
        length = add(length, l)
        squares.append(sq)
        events += service(f, a, b, c)
        if a != b:
            f['h'] = (b[0]-a[0], b[1]-a[1])
    if any(p not in f['H'] for p in s['P'] & s['F']):
        return 'suffix_missing_service', None
    if sign(add(s['E'], length, -1)) < 0:
        return 'suffix_overbudget', None
    f['S'], f['E'], f['M'] = s['base'], add(s['E'], length, -1), add(s['M'], length)
    return None, (full, length, events, f, squares)

def audit_session(out, c):
    c['independent_session_audits'] += 1
    try:
        s = state(out['raw_input'], c)
    except Invalid as e:
        assert out['status'] == 'invalid_input' and out['reason'] == str(e)
        assert 'response_received' not in out
        return {'checked': 'input_refusal', 'reason': str(e)}
    check_state(out['actual_before'], s)
    check_state(out['actual_after'], s)
    assert len(out['candidates']) == len(s['F'])
    accepted = []
    for row, q in zip(out['candidates'], sorted(s['F'])):
        assert pos(row['q'], True) == q
        l, sq = metric(s['S'], q, c)
        good = legal(s['F'], s['S'], q, c)
        affordable = sign(add(s['E'], l, -1)) >= 0
        dot = sum((q[i]-s['S'][i])*s['h'][i] for i in (0, 1))
        assert number(row['squared']) == sq == number(row['squared_source'])
        assert number(row['dot']) == dot
        assert row['legal'] == good and row['affordable'] == affordable
        certified(row['length'], l)
        if good and affordable:
            accepted.append((sq, -dot, q, l))
    # Check saved choice against all candidate keys; no selector or stub is invoked.
    if not accepted:
        assert out['status'] == 'no_entry' and 'response_received' not in out
        return {'checked': 'no_entry', 'candidates_checked': len(s['F'])}
    q = pos(out['q'], True)
    chosen = [(sq, dot, p) for sq, dot, p, l in accepted if p == q]
    assert len(chosen) == 1
    for sq, dot, p, l in accepted:
        c['independent_saved_choice_comparisons'] += 1
        assert chosen[0] <= (sq, dot, p), 'saved_q_not_minimal'
    l, _ = metric(s['S'], q, c)
    req = out['request']
    assert req['stub_only'] is True and pos(req['q'], True) == q
    f = deepcopy(s)
    events = collect(f)+service(f, s['S'], q, c)
    f['h'] = (q[0]-s['S'][0], q[1]-s['S'][1]) if q != s['S'] else s['h']
    f['S'], f['E'], f['M'] = q, add(s['E'], l, -1), add(s['M'], l)
    assert pos(req['h_entry']) == f['h']
    assert cellset(req['pending']) == s['P'] & s['F']-f['H']
    assert cellset(req['predicted_H']) == f['H'] and cellset(req['deferred']) == f['D']
    assert pos(req['base'], True) == s['base']
    assert req['integer_suffix_allowance'] == floor_exact(f['E'])
    certified(req['E_pred'], f['E'])
    certified(out['gamma_length'], l)
    assert [pos(p) for p in out['gamma']] == [s['S'], q]
    assert out['connector_events'] == events
    check_state(out['predicted_entry'], f)
    assert out['response_received'] == out['fixed_response']
    reason, data = suffix(s, q, out['fixed_response'], c)
    if reason:
        assert out['status'] == 'rejected_suffix' and out['reason'] == reason
        assert 'plan' not in out
        return {'checked': 'suffix_refusal_no_retry', 'q': list(map(int, q)), 'reason': reason}
    assert out['status'] == 'accepted'
    full, total, ev, final, squares = data
    saved = out['plan']
    assert saved['locked_q_index'] == 1 and [pos(p) for p in saved['points']] == full
    certified(saved['length'], total)
    assert [number(x) for x in saved['squared_sources']] == squares
    assert saved['events'] == ev and saved['kind'] == out['fixed_response']['kind']
    check_state(saved['predicted_final'], final)
    return {'checked': 'full_plan', 'edges': len(full)-1, 'q_locked': True}

def audit_actions(raw, records, c):
    c['independent_execution_audits'] += 1
    s, seen = state(raw, c), set()
    for item in records:
        c['independent_execution_commit_checks'] += 1
        act, saved = item['action'], item['result']
        if act['id'] in seen:
            assert saved == {'status': 'duplicate_rejected'}
            continue
        seen.add(act['id'])
        ev = []
        kind = act['kind']
        if kind == 'publish':
            s['P'] |= cellset(act['P'])
        elif kind == 'collect_here':
            ev = collect(s)
        elif kind == 'move':
            b = pos(act['to'])
            assert legal(s['F'], s['S'], b, c)
            l, sq = metric(s['S'], b, c)
            assert sign(add(s['E'], l, -1)) >= 0
            ev = service(s, s['S'], b, c)
            if b != s['S']:
                s['h'] = (b[0]-s['S'][0], b[1]-s['S'][1])
            s['S'], s['E'], s['M'] = b, add(s['E'], l, -1), add(s['M'], l)
            assert [number(x) for x in saved['squared_sources']] == [sq]
        else:
            raise AssertionError('unregistered_action')
        s['D'] = s['P']-s['F']-s['H']
        assert saved['status'] == 'committed' and saved['events'] == ev
        check_state(saved['actual'], s)
    return {'commits_checked': len(records), 'actual_H': [list(map(int, p)) for p in sorted(s['H'])]}

def audit_primitives(raw, records, c):
    c['independent_primitive_audits'] += 1
    s = state(raw, c)
    for saved in records:
        a, b = pos(saved['a']), pos(saved['b'])
        assert legal(s['F'], a, b, c) == saved['legal']
        l, sq = metric(a, b, c)
        certified(saved['length'], l)
        assert number(saved['squared_source']) == sq
        got = []
        for p in sorted(s['P']):
            t = hit(a, b, p, c)
            if t is not None and t > 0 and p in s['F']:
                got.append({'t': {'n': t.numerator, 'd': t.denominator}, 'cell': list(map(int, p))})
        got.sort(key=lambda e: (number(e['t']), e['cell']))
        assert got == saved['center_hits']
    return {'primitive_segments_checked': len(records)}
