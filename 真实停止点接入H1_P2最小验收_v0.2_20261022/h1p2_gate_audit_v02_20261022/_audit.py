"""Independent saved pipeline audit; no core/selector/postprocessor imports."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import importlib.util, json, sys, hashlib, time
from ._common import HERE
from . import _geometry as A
from . import _h1 as h1_audit

def load_auditor():
    from . import _post_saved
    return _post_saved

def audit_route(s, saved, counts):
    counts['independent_route_audits'] += 1
    path = [A.pos(p) for p in saved['points']]
    assert path[0] == s['S'] and path[-1] == s['base']
    f = deepcopy(s)
    ev, total, squares = A.collect(f), {}, []
    for a, b in zip(path, path[1:]):
        assert A.legal(s['F'], a, b, counts)
        length, sq = A.metric(a, b, counts)
        total = A.add(total, length)
        squares.append(sq)
        ev += A.service(f, a, b, counts)
        if a != b:
            f['h'] = (b[0]-a[0], b[1]-a[1])
    assert not (s['P'] & s['F']-f['H']) and A.sign(A.add(s['E'], total, -1)) >= 0
    f['S'], f['E'], f['M'] = s['base'], A.add(s['E'], total, -1), A.add(s['M'], total)
    A.certified(saved['length'], total)
    assert [A.number(x) for x in saved['squared_sources']] == squares and saved['events'] == ev
    A.check_state(saved['predicted_final'], f)
    return path, total, f

def audit_one(result, auditor, counts=None, technical=False):
    counts = Counter() if counts is None else counts
    begin = time.perf_counter()
    counts['independent_pipeline_audits'] += 1
    case = result['snapshot']
    raw, exp = case['input'], case['expect']
    s = A.state(raw, counts)
    A.check_state(result['actual_before'], s)
    A.check_state(result['actual_after'], s)
    assert result['actual_before'] == result['actual_after']
    q = A.pos(result['q'], True)
    assert list(map(int, q)) == exp['q']
    chosen_key = None
    keys = []
    assert len(result['candidates']) == len(s['F'])
    for record, p in zip(result['candidates'], sorted(s['F'])):
        assert A.pos(record['q'], True) == p
        good = A.legal(s['F'], s['S'], p, counts)
        length, sq = A.metric(s['S'], p, counts)
        can = A.sign(A.add(s['E'], length, -1)) >= 0
        dot = sum((p[i]-s['S'][i])*s['h'][i] for i in (0, 1))
        assert A.number(record['squared']) == sq == A.number(record['squared_source'])
        assert record['legal'] == good and record['affordable'] == can and A.number(record['dot']) == dot
        A.certified(record['length'], length)
        if good and can:
            key = (sq, -dot, p)
            keys.append(key)
            if p == q:
                chosen_key = key
    assert chosen_key is not None
    for key in keys:
        counts['independent_saved_choice_comparisons'] += 1
        assert chosen_key <= key
    gamma, _ = A.metric(s['S'], q, counts)
    A.certified(result['gamma_length'], gamma)
    assert [A.pos(p) for p in result['gamma']] == [s['S'], q]
    pred = deepcopy(s)
    events = A.collect(pred)+A.service(pred, s['S'], q, counts)
    pred['h'] = (q[0]-s['S'][0], q[1]-s['S'][1]) if q != s['S'] else s['h']
    pred['S'], pred['E'], pred['M'] = q, A.add(s['E'], gamma, -1), A.add(s['M'], gamma)
    A.check_state(result['predicted_entry'], pred)
    assert events == result['gamma_events'] and A.pos(result['h_entry']) == pred['h'] == A.pos(exp['h_entry'])
    assert A.cellset(exp['H_pred']) == pred['H']
    request = result['core_request']
    assert A.cellset(request['free']) == s['F'] and A.cellset(request['published_targets']) == s['P']
    assert A.cellset(request['targets']) == s['P'] & s['F'] and A.cellset(request['covered']) == pred['H']
    assert A.cellset(request['deferred_targets']) == pred['D']
    assert A.cellset(request['initial_targets']) == A.cellset(case['metadata']['initial_targets'])
    assert pred['H'] <= A.cellset(request['initial_targets'])
    assert request['old_route'] == [] and request['previous'] is None
    assert A.pos(request['current'], True) == q and A.pos(request['base'], True) == s['base']
    assert type(request['distance_budget']) is int and request['distance_budget'] == A.floor_exact(pred['E']) == exp['integer_allowance']
    assert request['predator'] == case['metadata']['predator']
    assert request['predator'][0] < min(x for x, y in s['F']) or request['predator'][0] > max(x for x, y in s['F'])
    assert tuple(Fraction(v) for v in request['incoming_heading']['vector']) == pred['h']
    assert request['incoming_heading'] == result['heading']
    assert request['incoming_heading']['source']['kind'] == 'synthetic_direction_fixture'
    assert json.loads(result['core_request_utf8']) == request
    assert hashlib.sha256(result['core_request_utf8'].encode()).hexdigest() == result['core_request_sha256']
    native = result['native_entry']['raw']
    if not technical:
        assert not native.get('stub') and result['native_counts']['core_started'] == result['native_counts']['core_returned'] == result['native_counts']['core_complete'] == 1
    if result['method'] == 'H1':
        actual = native['branches']['P0']
        assert native['selected'] == 'P0' and native['route'] == actual['route']
        assert actual['fallback_selected'] is False
        counts['independent_H1_decision_audits'] += 1
        ha = h1_audit.audit_output(request, result['heading'], actual, True)
        counts['independent_H1_unit_edge_checks'] += ha['route_edge_checks']
        if exp['H1_initial_diagonal_score']:
            assert actual['trace'][0]['index'] == 0 and actual['trace'][0]['kind'] == 'local'
            assert any('h1_certificate' in x for x in actual['trace'][0]['options']) and ha['interval_bits_used']
    else:
        actual = native
        assert actual['status'] == 'finished'
        if not technical:
            assert actual['core_finished'] and actual['source'] is not None
            assert any(e.get('stage') == 'core_finished' for e in actual['events'])
    path = [A.pos(p, True) for p in native['route']]
    assert path[0] == q and path[-1] == s['base'] and len(path)-1 <= request['distance_budget']
    assert all(p in s['F'] for p in path)
    assert all(abs(a[0]-b[0])+abs(a[1]-b[1]) == 1 for a, b in zip(path, path[1:]))
    assert not (s['P'] & s['F']-pred['H']-set(path))
    assert result['core_output_used'] is True
    assert [A.pos(p) for p in result['native_main_audit']['points']] == path
    audit_route(pred, result['native_main_audit'], counts)
    post_request = json.loads(result['post_request_utf8'])
    post_output = json.loads(result['post_response_utf8'])
    assert post_request['input'] == request and post_request['raw'] == json.loads(json.dumps(native)) and post_output == result['post']
    n = len(path)-1
    post_receipt = auditor.audit_one({'id': post_request['id'], 'limits': {'candidate_geometry': 4096,
                  'independent_geometry': n, 'independent_service_intersections': n*len(s['P'] & s['F']-pred['H'])}},
                   result['post_request_utf8'].encode(), result['post_response_utf8'].encode())
    counts['independent_frozen_post_audits'] += 1
    counts['independent_geometry'] += post_receipt['counts']['geometry']
    counts['independent_service_intersections'] += post_receipt['counts']['service_intersections']
    counts['independent_frozen_post_length_edge_checks'] += len(post_output['edges'])
    shortened = [A.pos(p, True) for p in post_output['vertices']]
    expected_full = ([s['S']] if s['S'] != q else [])+shortened
    assert [A.pos(p) for p in result['full_route']] == expected_full
    assert result['q_locked_index'] == (1 if s['S'] != q else 0)
    assert expected_full[result['q_locked_index']] == q
    assert not any(a == b for a, b in zip(expected_full, expected_full[1:]))
    assert [A.pos(p) for p in result['full_main_audit']['points']] == expected_full
    _, total, final = audit_route(s, result['full_main_audit'], counts)
    post_length = A.add(total, gamma, -1)
    assert [A.pos(p) for p in result['post_main_audit']['points']] == shortened
    A.certified(result['post_main_audit']['length'], post_length)
    A.check_state(result['post_main_audit']['predicted_final'], final)
    squares = []
    for a, b in zip(shortened, shortened[1:]):
        counts['independent_post_squared_checks'] += 1
        squares.append((b[0]-a[0])**2+(b[1]-a[1])**2)
    assert [A.number(v) for v in result['post_main_audit']['squared_sources']] == squares
    expected_events = []
    for item in post_output['first_actual']:
        t = Fraction(item['t'])
        expected_events.append({'kind': 'arrival', 'cell': item['point'], 't': {'n': t.numerator, 'd': t.denominator}})
    assert result['post_main_audit']['events'] == expected_events
    assert (A.sign(A.add(A.load(result['native_main_audit']['length']['exact']), post_length, -1))) >= 0
    assert result['timing']['pipeline_seconds'] < 30 and result['timing']['core_adapter_seconds'] < result['core_budget_passed'] <= 20
    if not technical:
        nc = result['native_counts']
        assert nc.get('post_candidate_geometry', 0) == post_output['counts']['candidate']
        assert nc.get('post_source_geometry', 0) == post_output['counts']['source_validation']
        assert nc.get('post_output_geometry', 0) == post_output['counts']['output_validation']
        assert nc.get('post_service_intersections', 0) == post_output['counts']['service_intersections']
    return {'passed': True, 'counts': dict(counts), 'frozen_post_receipt': post_receipt,
            'seconds': time.perf_counter()-begin, 'core_called_and_used': not technical,
            'full_edges': len(expected_full)-1, 'tasks_deferred': [list(map(int, p)) for p in sorted(s['D'])]}
