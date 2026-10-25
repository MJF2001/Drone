"""Independent integration wrapper. No native planner import at module top level."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import json, time
from common import HERE, sha
from exact import Expr, Refusal, point, pt, distance, certificate
from connector import parse, select, collect, credit_move, state_save, cells
import geometry

class PipelineStop(RuntimeError):
    pass

class GuardedCounter(Counter):
    def __init__(self, begin, clock=time.perf_counter):
        super().__init__()
        self.begin, self.clock = begin, clock

    def __setitem__(self, key, value):
        if key == 'candidate_checks':
            if self.clock()-self.begin >= 2:
                raise PipelineStop('connector_deadline')
            if value > 25:
                raise PipelineStop('connector_candidate_cap')
        super().__setitem__(key, value)
        if key.endswith('_geometry') and sum(v for k, v in self.items() if k.endswith('_geometry')) > 327:
            raise PipelineStop('wrapper_geometry_cap')
        if key.endswith('_service_intersections') and sum(v for k, v in self.items() if k.endswith('_service_intersections')) > 3624:
            raise PipelineStop('wrapper_service_cap')

def grid(p):
    # This conversion is only for known exact denominator-1 grid centers.
    if len(p) != 2 or any(not isinstance(v, Fraction) or v.denominator != 1 for v in p):
        raise PipelineStop('noninteger_grid_conversion')
    return [v.numerator for v in p]

def native_points(raw):
    if not isinstance(raw, (tuple, list)) or not raw or len(raw) > 101:
        raise PipelineStop('core_grid_schema')
    if any(not isinstance(p, (tuple, list)) or len(p) != 2 or any(type(v) is not int for v in p) for p in raw):
        raise PipelineStop('core_grid_schema')
    return [tuple(Fraction(v) for v in p) for p in raw]

def main_audit(s, points, c, phase):
    c[phase+'_route_audits'] += 1
    if not points or points[0] != s['S'] or points[-1] != s['base']:
        raise PipelineStop(phase+'_endpoints')
    predicted = deepcopy(s)
    events = collect(predicted, c, phase)
    total, sources = Expr(), []
    for a, b in zip(points, points[1:]):
        if not geometry.legal(s['F'], a, b, c, phase):
            raise PipelineStop(phase+'_illegal_geometry')
        l, square = distance(a, b, c, phase)
        total, sources = total+l, sources+[square]
        events += credit_move(predicted, a, b, c, phase)
        if a != b:
            predicted['h'] = tuple(v-w for v, w in zip(b, a))
    if s['P'] & s['F']-predicted['H']:
        raise PipelineStop(phase+'_missing_credit')
    c[phase+'_resource_checks'] += 1
    if (s['E']-total).sign() < 0:
        raise PipelineStop(phase+'_overbudget')
    predicted['S'], predicted['E'], predicted['M'] = s['base'], s['E']-total, s['M']+total
    return {'points': [pt(p) for p in points], 'length': certificate(total), 'squared_sources': sources,
            'events': events, 'predicted_final': state_save(predicted), 'valid': True}

def run(input_bytes, method, seed, core, post, result, recorder=None, allow_stub=False):
    begin = time.perf_counter()
    if recorder:
        recorder.begin = begin
    c = GuardedCounter(begin)
    result.update(method=method, seed=seed, wrapper_counts=c, stage='parse', timing={})
    case = json.loads(input_bytes)
    raw = case['input']
    original_bytes = json.dumps(raw, sort_keys=True, ensure_ascii=False, allow_nan=False)
    s = parse(raw, c)
    result.update(snapshot=case, actual_before=state_save(s), actual_after=state_save(s))
    result['stage'] = 'connector'
    selected, rows = select(s, c)
    result['candidates'] = rows
    if not selected:
        raise PipelineStop('no_entry')
    if time.perf_counter()-begin >= 2:
        raise PipelineStop('connector_deadline')
    q, square, dot, gamma_length = selected
    pred = deepcopy(s)
    gamma_events = collect(pred, c, 'prediction')+credit_move(pred, s['S'], q, c, 'prediction')
    pred['S'] = q
    pred['h'] = tuple(v-w for v, w in zip(q, s['S'])) if q != s['S'] else s['h']
    pred['E'], pred['M'] = s['E']-gamma_length, s['M']+gamma_length
    cap = pred['E'].floor()
    h = [v.numerator if v.denominator == 1 else str(v) for v in pred['h']]
    heading = {'status': 'KNOWN', 'vector': h,
               'source': {'kind': 'synthetic_direction_fixture', 'snapshot_id': case['id'],
                          'snapshot_sha256': __import__('hashlib').sha256(input_bytes).hexdigest(),
                          'meaning': 'paid_predicted_gamma_direction' if q != s['S'] else 'given_synthetic_incoming_direction'}}
    expected = case['expect']
    if grid(q) != expected['q'] or pt(pred['h']) != expected['h_entry'] or cells(pred['H']) != expected['H_pred']:
        raise PipelineStop('entry_expectation_mismatch')
    if cap != expected['integer_allowance']:
        raise PipelineStop('allowance_expectation_mismatch')
    initial = case['metadata']['initial_targets']
    if not pred['H'] <= set(map(tuple, initial)):
        raise PipelineStop('initial_target_history_conflict')
    request = {'name': 'synthetic_stop_'+case['id'], 'free': cells(s['F']), 'published_targets': cells(s['P']),
               'targets': cells(s['P'] & s['F']), 'covered': cells(pred['H']), 'deferred_targets': cells(pred['D']),
               'current': grid(q), 'base': grid(s['base']), 'old_route': [], 'initial_targets': initial,
               'distance_budget': cap, 'predator': case['metadata']['predator'], 'previous': None,
               'incoming_heading': heading}
    request_bytes = json.dumps(request, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    result.update(q=grid(q), gamma=[pt(s['S']), pt(q)], gamma_length=certificate(gamma_length),
                  gamma_events=gamma_events, h_entry=pt(pred['h']), heading=heading, predicted_entry=state_save(pred),
                  core_request=request, core_request_utf8=request_bytes.decode('utf-8'),
                  core_request_sha256=__import__('hashlib').sha256(request_bytes).hexdigest())
    result['timing']['connector_and_contract_seconds'] = time.perf_counter()-begin
    result['stage'] = 'core'
    core_start = time.perf_counter()
    core_budget = min(20., 30.-(core_start-begin))
    if core_budget <= 0:
        raise PipelineStop('no_core_time_remaining')
    result['core_budget_passed'] = core_budget
    c['native_adapter_calls'] += 1
    entry = core(request_bytes, method, core_budget, seed)
    result['native_entry'] = entry       # Kept even if all later audits fail.
    result['timing']['core_adapter_seconds'] = time.perf_counter()-core_start
    raw_core = entry['raw']
    if raw_core.get('stub', False) and not allow_stub:
        raise PipelineStop('stub_in_real_stage')
    if raw_core.get('status') not in ('core_complete', 'finished') or not raw_core.get('route'):
        raise PipelineStop('core_refused')
    if result['timing']['core_adapter_seconds'] >= core_budget:
        raise PipelineStop('core_late')
    points = native_points(raw_core['route'])
    n = len(points)-1
    if n > cap or points[0] != q or points[-1] != s['base'] or any(p not in s['F'] for p in points):
        raise PipelineStop('core_grid_contract')
    if any(sum(abs(x-y) for x, y in zip(a, b)) != 1 for a, b in zip(points, points[1:])):
        raise PipelineStop('core_grid_steps')
    result['stage'] = 'native_main_audit'
    result['native_main_audit'] = main_audit(pred, points, c, 'native')
    result['core_output_used'] = True
    result['native_source'] = raw_core.get('source', raw_core.get('version'))
    result['native_fallback_selected'] = raw_core.get('fallback_selected', False)
    result['native_raw_edges'] = n
    result['stage'] = 'post'
    post_start = time.perf_counter()
    remaining_total = 30.-(post_start-begin)
    remaining_candidates = max(0., 28.-(post_start-begin))
    if remaining_total <= 0:
        raise PipelineStop('no_post_time_remaining')
    post_request = {'id': case['id']+'_'+method, 'input': request, 'raw': raw_core}
    post_wire = json.dumps(post_request, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    result.update(post_request_utf8=post_wire.decode('utf-8'), post_candidate_time_remaining=remaining_candidates,
                  post_total_time_remaining=remaining_total)
    try:
        post_text, envelope = post(post_wire, limit=4096, soft=remaining_candidates, total=remaining_total)
    except Exception as error:
        result['post_failure_original'] = repr(error)
        raise PipelineStop('post_refused') from error
    result['post_response_utf8'] = post_text
    result['post_envelope'] = envelope
    output = json.loads(post_text)
    result['post'] = output
    result['timing']['post_adapter_seconds'] = time.perf_counter()-post_start
    if envelope.get('late') or time.perf_counter()-begin >= 30:
        raise PipelineStop('post_late')
    try:
        shortened = native_points(output['vertices'])
        if shortened[0] != q or shortened[-1] != s['base'] or len(shortened)-1 > n:
            raise ValueError('post endpoints/edge count')
    except Exception as error:
        raise PipelineStop('post_schema_or_endpoints') from error
    result['stage'] = 'post_and_full_main_audit'
    result['post_main_audit'] = main_audit(pred, shortened, c, 'post')
    # Join once at q. Zero entry retained as gamma metadata, no duplicate route vertex.
    gamma_vertices = [s['S']] if s['S'] == q else [s['S'], q]
    full = gamma_vertices[:-1]+shortened
    if len(full)-1 > 101 or any(a == b for a, b in zip(full, full[1:])):
        raise PipelineStop('duplicate_splice_or_full_size')
    result['full_route'] = [pt(p) for p in full]
    result['q_locked_index'] = 0 if s['S'] == q else 1
    result['full_main_audit'] = main_audit(s, full, c, 'full')
    if (result['full_main_audit']['length']['exact'] !=
        (gamma_length+Expr.load(result['post_main_audit']['length']['exact'])).save()):
        raise PipelineStop('distance_splice_identity')
    result['actual_after'] = state_save(s)
    if result['actual_before'] != result['actual_after'] or original_bytes != json.dumps(raw, sort_keys=True, ensure_ascii=False, allow_nan=False):
        raise PipelineStop('actual_state_mutated')
    result['stage'] = 'encoding'
    encode_start = time.perf_counter()
    json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    result['timing']['main_encoding_seconds'] = time.perf_counter()-encode_start
    result['timing']['pipeline_seconds'] = time.perf_counter()-begin
    result['timing']['pipeline_late'] = result['timing']['pipeline_seconds'] >= 30
    if result['timing']['pipeline_late']:
        raise PipelineStop('pipeline_late')
    result['stage'] = 'main_complete'
    result['main_passed'] = True
    return result
