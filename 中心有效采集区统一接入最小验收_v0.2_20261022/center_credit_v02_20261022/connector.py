"""Finite straight-entry wrapper, fixed handwritten suffix only. No native imports."""
from collections import Counter
from copy import deepcopy
from functools import cmp_to_key
from fractions import Fraction as Q
from .exact import Expr, Refusal, Uncertain, point, pt, rat, squared, distance, certificate
from . import geometry as geo

def cellset(x):
    if not isinstance(x, (list, tuple)):
        raise Refusal('cellset_schema')
    ps = [point(p, grid=True) for p in x]
    if len(set(ps)) != len(ps):
        raise Refusal('duplicate_cell')
    return set(ps)

def cells(x):
    return [[int(a), int(b)] for a, b in sorted(x)]

def state_save(s):
    return {'S': pt(s['S']), 'h': pt(s['h']), 'F': cells(s['F']), 'P': cells(s['P']),
            'H': cells(s['H']), 'D': cells(s['D']), 'base': [int(v) for v in s['base']],
            'E': certificate(s['E']), 'M': certificate(s['M'])}

def parse(raw, c):
    c['parse'] += 1
    required = {'S', 'h', 'F', 'P', 'H', 'D', 'base', 'E', 'M'}
    if not isinstance(raw, dict) or not required <= set(raw):
        raise Refusal('missing_field')
    s = {k: cellset(raw[k]) for k in ('F', 'P', 'H', 'D')}
    s.update(S=point(raw['S']), h=point(raw['h']), base=point(raw['base'], True),
             E=Expr.load(raw['E']), M=Expr.load(raw['M']))
    if not s['F'] or len(s['F']) > 25:
        raise Refusal('free_cell_bound')
    # The test interface additionally bounds public target cells, protecting all loops.
    if len(s['P']) > 25 or any(abs(v) > 100 for p in s['F'] | s['P'] for v in p):
        raise Refusal('fixture_domain_bound')
    if any(abs(v) > 100 for v in s['S']):
        raise Refusal('fixture_position_bound')
    if s['h'] == (0, 0) or s['base'] not in s['F'] or not s['H'] <= s['P']:
        raise Refusal('state_semantics')
    if s['D'] != s['P']-s['F']-s['H']:
        raise Refusal('deferred_semantics')
    if s['E'].sign() < 0 or s['M'].sign() < 0:
        raise Refusal('negative_resource')
    if not geo.legal(s['F'], s['S'], s['S'], c, 'input'):
        raise Refusal('unsafe_given_stop')
    return s

from .service import collect,credit_move

def select(s, c):
    c['selector'] += 1
    rows, eligible = [], []
    for q in sorted(s['F']):
        c['candidate_checks'] += 1
        sq = squared(s['S'], q)
        length, provenance = distance(s['S'], q, c, 'candidate')
        good = geo.legal(s['F'], s['S'], q, c, 'candidate')
        c['candidate_resource_checks'] += 1
        affordable = (s['E']-length).sign() >= 0
        dot = sum(h*(v-w) for h, v, w in zip(s['h'], q, s['S']))
        row = {'q': list(map(int, q)), 'squared': rat(sq), 'dot': rat(dot),
               'legal': good, 'affordable': affordable, 'length': certificate(length),
               'squared_source': provenance}
        rows.append(row)
        if good and affordable:
            eligible.append((q, sq, dot, length))
        else:
            c['candidate_rejected'] += 1
    def compare(a, b):
        c['candidate_comparisons'] += 1
        if a[1] != b[1]:
            return -1 if a[1] < b[1] else 1
        # Equal norm and fixed h: larger exact dot means smaller angle.
        c['angle_tie_comparisons'] += 1
        if a[2] != b[2]:
            return -1 if a[2] > b[2] else 1
        c['lex_tie_comparisons'] += 1
        return (a[0] > b[0])-(a[0] < b[0])
    eligible.sort(key=cmp_to_key(compare))
    return (eligible[0] if eligible else None), rows

def audit_plan(s, q, response, c):
    c['main_plan_audits'] += 1
    if not isinstance(response, dict) or response.get('stub') != 'HANDWRITTEN_FIXED_RESPONSE':
        raise Refusal('stub_identity')
    if response.get('kind') not in ('native_grid', 'manual_polyline'):
        raise Refusal('suffix_kind')
    rawpoints = response.get('points')
    if not isinstance(rawpoints, (tuple, list)) or not 1 <= len(rawpoints) <= 33:
        raise Refusal('suffix_size')
    points = [point(p, True) for p in rawpoints]
    if points[0] != q or points[-1] != s['base']:
        raise Refusal('suffix_endpoints')
    if response['kind'] == 'native_grid' and any(sum(abs(x-y) for x, y in zip(a, b)) not in (0, 1)
             for a, b in zip(points, points[1:])):
        raise Refusal('native_nonunit')
    if any(p not in s['F'] for p in points):
        raise Refusal('suffix_vertex_blocked')
    forecast = deepcopy(s)
    events = collect(forecast, c, 'main')
    full = [s['S']] + points   # q is explicitly retained, including zero entry.
    sources, total = [], Expr()
    for a, b in zip(full, full[1:]):
        if not geo.legal(s['F'], a, b, c, 'main'):
            raise Refusal('suffix_geometry')
        l, src = distance(a, b, c, 'main')
        total = total+l
        sources.append(src)
        events += credit_move(forecast, a, b, c, 'main')
    if s['P'] & s['F'] - forecast['H']:
        raise Refusal('suffix_missing_service')
    c['main_resource_checks'] += 1
    if (s['E']-total).sign() < 0:
        raise Refusal('suffix_overbudget')
    forecast['S'] = s['base']
    for a, b in zip(full, full[1:]):
        if a != b:
            forecast['h'] = tuple(v-w for v, w in zip(b, a))
    forecast['E'], forecast['M'] = s['E']-total, s['M']+total
    return {'points': [pt(p) for p in full], 'locked_q_index': 1,
            'length': certificate(total), 'squared_sources': sources, 'events': events,
            'predicted_final': state_save(forecast), 'kind': response['kind']}

def session(raw, response, c):
    c['sessions'] += 1
    out = {'status': 'started', 'raw_input': deepcopy(raw), 'fixed_response': deepcopy(response)}
    try:
        s = parse(raw, c)
        out['actual_before'] = state_save(s)
        chosen, rows = select(s, c)
        out['candidates'] = rows
        if chosen is None:
            out.update(status='no_entry', reason='no_legal_affordable_straight_entry', actual_after=state_save(s))
            return out
        q, sq, dot, length = chosen
        prediction = deepcopy(s)
        predicted_events = collect(prediction, c, 'predict')
        predicted_events += credit_move(prediction, s['S'], q, c, 'predict')
        prediction['S'] = q
        prediction['h'] = tuple(v-w for v, w in zip(q, s['S'])) if q != s['S'] else s['h']
        prediction['E'], prediction['M'] = s['E']-length, s['M']+length
        c['integer_allowance_certifications'] += 1
        request = {'stub_only': True, 'q': list(map(int, q)), 'h_entry': pt(prediction['h']),
                   'pending': cells(s['P'] & s['F']-prediction['H']), 'deferred': cells(prediction['D']),
                   'predicted_H': cells(prediction['H']), 'E_pred': certificate(prediction['E']),
                   'integer_suffix_allowance': prediction['E'].floor(), 'base': list(map(int, s['base']))}
        out.update(q=list(map(int, q)), request=request, predicted_entry=state_save(prediction),
                   connector_events=predicted_events, gamma=[pt(s['S']), pt(q)],
                   gamma_length=certificate(length))
        c['stub_responses'] += 1
        # Return exactly the pre-registered response, no computation or fallback.
        out['response_received'] = deepcopy(response)
        out['plan'] = audit_plan(s, q, response, c)
        out['status'] = 'accepted'
    except Uncertain as e:
        out.update(status='uncertain', reason=str(e))
    except Refusal as e:
        out.update(status='rejected_suffix' if 'response_received' in out else 'invalid_input', reason=str(e))
    if 'actual_before' in out:
        out['actual_after'] = state_save(s)
    return out

def commit(s, action, seen, c):
    """Manually supplied prefix action; atomic validation then actual commit."""
    c['execution_commit_calls'] += 1
    if action['id'] in seen:
        c['execution_duplicate_rejected'] += 1
        return {'status': 'duplicate_rejected'}
    t = deepcopy(s)
    events, sources = [], []
    kind = action['kind']
    if kind == 'collect_here':
        events = collect(t, c, 'execution')
    elif kind == 'publish':
        t['P'] |= cellset(action['P'])
        if len(t['P']) > 25:
            raise Refusal('fixture_target_bound')
        t['D'] = t['P']-t['F']-t['H']
    elif kind == 'move':
        b = point(action['to'])
        if any(abs(v) > 100 for v in b):
            raise Refusal('fixture_position_bound')
        if not geo.legal(t['F'], t['S'], b, c, 'execution'):
            raise Refusal('execution_illegal_segment')
        length, src = distance(t['S'], b, c, 'execution')
        c['execution_resource_checks'] += 1
        if (t['E']-length).sign() < 0:
            raise Refusal('execution_overbudget')
        sources = [src]
        events = credit_move(t, t['S'], b, c, 'execution')
        if b != t['S']:
            t['h'] = tuple(v-w for v, w in zip(b, t['S']))
        t['S'], t['E'], t['M'] = b, t['E']-length, t['M']+length
    else:
        raise Refusal('execution_kind')
    seen.add(action['id'])
    s.clear()
    s.update(t)
    c['execution_commits_accepted'] += 1
    return {'status': 'committed', 'events': events, 'squared_sources': sources, 'actual': state_save(s)}
