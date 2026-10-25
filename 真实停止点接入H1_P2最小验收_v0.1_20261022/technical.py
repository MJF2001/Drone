"""Eleven fixed wrapper tests, <=12 stub attempts. Never import real core modules."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import sys, json, importlib.util, traceback, shutil
from common import HERE, read, dump, sha, now, evidence
from pipeline import run, grid, PipelineStop
from fixtures import p, expr
from audit import load_auditor, audit_one

def post_module():
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    geo = load('_technical_post_geometry', HERE/'postsrc/geometry.py')
    before = sys.modules.get('geometry')
    sys.modules['geometry'] = geo
    try:
        return load('_technical_post_engine', HERE/'postsrc/engine.py')
    finally:
        if before is None:
            sys.modules.pop('geometry', None)
        else:
            sys.modules['geometry'] = before

def fixed_path(ident):
    # Written explicitly before technical execution; no graph search here.
    return {'01': [[0, 0], [1, 0], [2, 0], [1, 0], [0, 0]],
            '02': [[0, 0], [0, 1], [1, 1], [1, 0], [1, 1], [2, 1], [2, 2], [2, 1], [1, 1], [0, 1], [0, 0]],
            '03': [[0, 0], [0, 1], [0, 0], [1, 0], [0, 0]],
            '06': [[2, 0], [1, 0], [0, 0]]}[ident]

def main():
    rnd = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    assert 1 <= rnd <= 3
    directory = HERE/'technical_rounds'/f'round_{rnd}'
    assert not directory.exists(), 'refuse technical rerun'
    frozen = read(HERE/f'technical_freeze_{rnd}.json')
    for name, value in frozen['files'].items():
        assert sha(HERE/name) == value
    directory.mkdir(parents=True)
    for f in HERE.glob('*.py'):
        shutil.copyfile(f, directory/f.name)
    reg = read(HERE/'registration.json')
    shutil.copyfile(HERE/'registration.json', directory/'registration.json')
    engine, auditor = post_module(), load_auditor()
    counts, rows = Counter(), []
    for spec in reg['stub_tests']:
        case = deepcopy(next(c for c in reg['cases'] if c['id'] == spec['case']))
        variant = spec['variant']
        result = {'id': spec['id'], 'expected': spec['expect'], 'variant': variant}
        calls = Counter()
        if variant == 'missing_heading':
            del case['input']['h']
        if variant == 'exact_radical_allowance':
            # Fixed technical-only two-target input with exact cancellation to 2.
            case['input']['P'], case['input']['H'], case['input']['D'] = [[0, 0], [1, 0]], [], []
            case['metadata']['initial_targets'] = [[0, 0], [1, 0]]
            case['input']['E'] = expr(2, {2: '1/4'})
            case['expect']['H_pred'], case['expect']['integer_allowance'] = [[0, 0]], 2
        def core(payload, method, budget, seed):
            calls['core_stub_attempts'] += 1
            request = json.loads(payload)
            assert all(type(v) is int for q in request['free'] for v in q)
            assert grid((Fraction(1), Fraction(0))) == [1, 0]
            try:
                grid((Fraction(1, 2), Fraction(0)))
            except PipelineStop:
                calls['noninteger_conversion_rejections'] += 1
            else:
                raise AssertionError('noninteger Fraction silently rounded')
            route = deepcopy(fixed_path(case['id']))
            if variant == 'exact_radical_allowance':
                route = [[0, 0], [1, 0], [0, 0]]
            if variant == 'tuple':
                route = tuple(tuple(p) for p in route)
            if variant == 'nonintegral_fraction_output':
                route[0] = [Fraction(1, 2), 0]
            raw = {'status': 'environment_infeasible' if variant == 'core_refusal' else 'finished',
                   'route': [] if variant == 'core_refusal' else route, 'source': 'HANDWRITTEN_STUB',
                   'stub': True, 'events': [], 'core_finished': True}
            calls['core_stub_returns'] += 1
            return {'raw': raw, 'budget': budget}
        def post(payload, **kwargs):
            if variant in ('post_exception', 'post_invalid_output'):
                calls['post_stub_attempts'] += 1
                if variant == 'post_exception':
                    raise RuntimeError('handwritten post rejection')
                calls['post_stub_returns'] += 1
                return json.dumps({'vertices': [[9, 9]]}), {'late': False}
            calls['technical_frozen_post_calls'] += 1
            return engine.process(payload, **kwargs)
        try:
            wire = json.dumps(case, ensure_ascii=False, allow_nan=False).encode()
            if variant == 'json_roundtrip':
                wire = json.dumps(json.loads(wire), ensure_ascii=False).encode()
            run(wire, 'P2', 20261022, core, post, result, allow_stub=True)
            result['observed'] = 'passed'
            result = evidence(result)
            result['independent'] = audit_one(result, auditor, technical=True)
            if variant == 'radical':
                assert result['core_request']['distance_budget'] == 99
                assert len(result['predicted_entry']['E']['exact']['terms']) == 2
            if variant == 'exact_radical_allowance':
                assert result['core_request']['distance_budget'] == 2 and result['full_main_audit']['predicted_final']['E']['exact']['terms'] == []
        except Exception as error:
            result['observed'] = str(error)
            result['failure'] = traceback.format_exc()
        attempts = calls['core_stub_attempts']+calls['post_stub_attempts']
        result['counts'] = dict(calls)
        result['matched_expected'] = result['observed'] == spec['expect'] and attempts <= spec['max_stub_attempts']
        dump(directory/(spec['id']+'.json'), evidence(result))
        rows.append({'id': spec['id'], 'matched_expected': result['matched_expected'], 'observed': result['observed'],
                     'counts': dict(calls), 'wrapper_counts': dict(result.get('wrapper_counts', {})),
                     'independent_counts': result.get('independent', {}).get('counts', {})})
        counts.update(calls)
        print(spec['id'], result['matched_expected'], result['observed'], flush=True)
    assert counts['core_stub_attempts']+counts['post_stub_attempts'] <= 12
    summary = {'utc': now(), 'round': rnd, 'cases': len(rows), 'passed': sum(r['matched_expected'] for r in rows),
               'failed': sum(not r['matched_expected'] for r in rows), 'counts': dict(counts),
               'native_core_calls': 0, 'BFS': 0, 'Astar': 0, 'rows': rows}
    dump(directory/'result.json', summary)
    print({k: v for k, v in summary.items() if k != 'rows'})
    if summary['failed']:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
