"""Exact rational heading evidence. Pure functions: no planner imports."""
from fractions import Fraction
from math import gcd, lcm
from copy import deepcopy

class HeadingError(ValueError):
    pass

def scalar(x):
    if type(x) is int:
        return Fraction(x)
    if type(x) is str:
        try:
            return Fraction(x)
        except (ValueError, ZeroDivisionError):
            pass
    raise HeadingError('integer_or_rational_scalar_required')

def primitive(raw):
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise HeadingError('two_component_vector_required')
    a, b = map(scalar, raw)
    if not (a or b):
        raise HeadingError('zero_vector')
    den = lcm(a.denominator, b.denominator)
    x, y = int(a * den), int(b * den)
    g = gcd(abs(x), abs(y))
    return [x // g, y // g]

def parse_heading(request, current=None):
    if not isinstance(request, dict):
        raise HeadingError('heading_object_required')
    status = request.get('status')
    source = request.get('source')
    if not isinstance(source, dict) or not isinstance(source.get('kind'), str) or not source['kind']:
        raise HeadingError('heading_source_required')
    if status == 'UNKNOWN':
        raise HeadingError('unknown_is_not_no_prior_motion')
    if status == 'NO_PRIOR_MOTION':
        if request.get('vector') is not None or source['kind'] != 'initialization_no_motion':
            raise HeadingError('no_motion_evidence_required')
        return dict(status=status, raw=None, primitive=None, source=deepcopy(source))
    if status != 'KNOWN':
        raise HeadingError('unknown_heading_status')
    raw = request.get('vector')
    p = primitive(raw)
    if source['kind'] == 'saved_previous':
        a, b = source.get('start'), source.get('end')
        if not all(isinstance(q, (list, tuple)) and len(q) == 2 and all(type(v) is int for v in q) for q in (a, b)):
            raise HeadingError('saved_previous_grid_evidence_required')
        if current is not None and tuple(b) != tuple(current):
            raise HeadingError('heading_evidence_endpoint_mismatch')
        delta = [b[0] - a[0], b[1] - a[1]]
        if primitive(delta) != p or sum(abs(v) for v in delta) != 1:
            raise HeadingError('saved_previous_direction_mismatch')
        if not source.get('input_sha256'):
            raise HeadingError('saved_source_hash_required')
    elif source['kind'] not in ('handwritten_technical', 'synthetic_direction_fixture'):
        raise HeadingError('unsupported_heading_evidence_kind')
    return dict(status='KNOWN', raw=list(raw), primitive=p, source=deepcopy(source))

def after_edge(state, a, b, end_index):
    if tuple(a) == tuple(b):
        return state
    delta = [b[0] - a[0], b[1] - a[1]]
    if any(type(v) is not int for v in delta) or sum(abs(v) for v in delta) != 1:
        raise HeadingError('predicted_edge_must_be_unit_grid_edge')
    return dict(status='KNOWN', raw=delta, primitive=delta,
                source=dict(kind='predicted_route_edge', start=list(a), end=list(b), end_index=end_index))
