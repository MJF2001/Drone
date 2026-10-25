"""Run only frozen session slots; all primary/independent geometry separately counted."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import traceback
import shutil
from exact import point, pt, rat, distance, certificate
import geometry as geo
from connector import session, parse, commit, state_save
import independent as ind
from io_utils import HERE, write_json, read_json, sha, now, tuple_coords, plain

def expect_case(case, out):
    exp = case['expect']
    assert out['status'] == exp['status'], (case['id'], out['status'], exp['status'])
    for key in ('q', 'reason'):
        if key in exp:
            assert out.get(key) == exp[key], (key, out.get(key), exp[key])
    if 'h_entry' in exp:
        assert out['request']['h_entry'] == exp['h_entry']
    if 'allowance' in exp:
        assert out['request']['integer_suffix_allowance'] == exp['allowance']
    if 'gamma_H' in exp:
        assert out['predicted_entry']['H'] == exp['gamma_H']
    if 'actual_H' in exp:
        assert out['actual_after']['H'] == exp['actual_H']
    if 'deferred' in exp:
        assert out['request']['deferred'] == exp['deferred']
    if 'candidate_reject' in exp:
        row = next(r for r in out['candidates'] if r['q'] == exp['candidate_reject'])
        assert row['legal'] is False
    if 'final_plan_E' in exp:
        assert ind.load(out['plan']['predicted_final']['E']['exact']) == ind.load(exp['final_plan_E'])
    if 'actual_before' in out:
        assert out['actual_before'] == out['actual_after'], 'actual_changed_during_planning'
    if 'q' in out:
        assert 'response_received' in out

def check_ledger_expectations(case, records, final):
    exp = case['expect']
    for key in ('H', 'S', 'h'):
        if 'final_'+key in exp:
            assert final[key] == exp['final_'+key], (case['id'], key, final[key], exp['final_'+key])
    for key in ('E', 'M'):
        if 'final_'+key in exp:
            assert ind.load(final[key]['exact']) == ind.load(exp['final_'+key])
    if 'action_H' in exp:
        assert [x['result']['actual']['H'] for x in records] == exp['action_H']

def main():
    import sys
    rnd = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    reg = read_json(HERE/'门槛事前登记.json')
    assert 1 <= rnd <= reg['round_limit']
    target = HERE/'repair_rounds'/f'round_{rnd}'
    if target.exists():
        raise SystemExit('Round exists, refusing rerun/overwrite')
    freeze_path = HERE/f'round_{rnd}_freeze.json'
    frozen = read_json(freeze_path)
    for name, digest in frozen['files'].items():
        assert sha(HERE/name) == digest, ('freeze_changed', name)
    target.mkdir(parents=True)
    for source in HERE.glob('*.py'):
        shutil.copyfile(source, target/source.name)
    shutil.copyfile(HERE/'门槛事前登记.json', target/'expectations.json')
    shutil.copyfile(freeze_path, target/'freeze.json')
    c, ic, rows = Counter(), Counter(), []
    prior_rows = {}
    if rnd > 1:
        prior = read_json(HERE/'repair_rounds'/f'round_{rnd-1}'/'result.json')
        prior_rows = {r['id']: r for r in prior['rows']}
    for case in reg['cases']:
        old = prior_rows.get(case['id'])
        if old and old['gate_status'] == 'passed':
            oldpath = old.get('evidence_path', str(Path('repair_rounds')/f'round_{rnd-1}'/'outputs'/f'{case["id"]}.json'))
            rows.append({'id': case['id'], 'group': case['group'], 'gate_status': 'passed',
                         'status': old['status'], 'reason': old.get('reason'), 'reused': True,
                         'evidence_path': oldpath, 'evidence_sha256': sha(HERE/oldpath),
                         'primary_counts': {}, 'independent_counts': {}})
            print(case['id'], 'reused_prior_pass_no_execution', flush=True)
            continue
        before, before_i = c.copy(), ic.copy()
        result = {'case_id': case['id'], 'group': case['group'], 'started_utc': now()}
        try:
            raw = deepcopy(case['input'])
            fixed = deepcopy(case['suffix'])
            if case.get('runtime_tuple'):
                raw, fixed = tuple_coords(raw), tuple_coords(fixed)
                assert type(raw['S']) is tuple and type(raw['F'][0]) is tuple
                assert type(fixed['points'][0]) is tuple
            result['runtime_container_evidence'] = {'S': type(raw.get('S')).__name__,
                                                   'F_first': type(raw['F'][0]).__name__,
                                                   'suffix_first': type(fixed['points'][0]).__name__}
            out = session(raw, fixed, c)
            result['session'] = out
            expect_case(case, out)
            result['independent_session'] = ind.audit_session(out, ic)
            primitives, records = [], []
            if case.get('primitives') or case.get('actions'):
                s = parse(raw, c)
                for item in case.get('primitives', []):
                    a, b = point(item['a']), point(item['b'])
                    good = geo.legal(s['F'], a, b, c, 'primitive')
                    l, src = distance(a, b, c, 'primitive')
                    hits = []
                    for p in sorted(s['P']):
                        t = geo.hit(a, b, p, c, 'primitive')
                        if t is not None and t > 0 and p in s['F']:
                            hits.append({'t': rat(t), 'cell': list(map(int, p))})
                    hits.sort(key=lambda x: (ind.number(x['t']), x['cell']))
                    saved = dict(a=item['a'], b=item['b'], legal=good, length=certificate(l),
                                 squared_source=src, center_hits=hits, role=item['role'])
                    primitives.append(saved)
                    assert good == item['expect_legal']
                    assert [v['cell'] for v in hits] == item['expect_hits']
                result['primitives'] = primitives
                if primitives:
                    result['independent_primitives'] = ind.audit_primitives(raw, primitives, ic)
                seen = set()
                for action in case.get('actions', []):
                    records.append({'action': action, 'result': commit(s, action, seen, c)})
                result['actions'] = records
                if records:
                    result['actions_role'] = case.get('actions_role', 'handwritten_ledger_actions')
                    result['actual_final'] = state_save(s)
                    check_ledger_expectations(case, records, result['actual_final'])
                    result['independent_actions'] = ind.audit_actions(raw, records, ic)
            result['gate_status'] = 'passed'
        except Exception:
            result.update(gate_status='failed', failure=traceback.format_exc())
        result['primary_counts'] = dict(c-before)
        result['independent_counts'] = dict(ic-before_i)
        result['finished_utc'] = now()
        result = plain(result)
        write_json(target/'outputs'/f'{case["id"]}.json', result)
        rows.append({'id': case['id'], 'group': case['group'], 'gate_status': result['gate_status'],
                     'status': result.get('session', {}).get('status', 'implementation_error'),
                     'reason': result.get('session', {}).get('reason'), 'primary_counts': result['primary_counts'],
                     'independent_counts': result['independent_counts'], 'reused': False,
                     'evidence_path': str((target/'outputs'/f'{case["id"]}.json').relative_to(HERE)),
                     'evidence_sha256': sha(target/'outputs'/f'{case["id"]}.json')})
        print(case['id'], result['gate_status'], rows[-1]['status'], flush=True)
    total = c+ic
    first = read_json(target/'outputs'/'01_1.json')
    tuple_case = read_json(target/'outputs'/'18_1.json')
    representation_pair = all(first['session'].get(k) == tuple_case['session'].get(k)
                              for k in ('status', 'q', 'request', 'plan', 'actual_before', 'actual_after'))
    upper = reg['per_round_counter_upper_bounds']
    violations = {k: v for k, v in total.items() if k not in upper or v > upper[k]}
    zero = {k: 0 for k in reg['zero_required']}
    summary = {'round': rnd, 'utc': now(), 'slots': len(reg['cases']),
               'new_sessions': c['sessions'], 'reused_prior_pass': sum(r.get('reused', False) for r in rows),
               'passed': sum(r['gate_status'] == 'passed' for r in rows),
               'failed': sum(r['gate_status'] == 'failed' for r in rows), 'not_run': 0,
               'primary_counts': dict(c), 'independent_counts': dict(ic),
               'required_zeros': zero, 'upper_bound_violations': violations,
               'saved_list_tuple_pair_equal': representation_pair,
               'response_statuses': dict(Counter(r['status'] for r in rows)), 'rows': rows}
    write_json(target/'result.json', summary)
    print({k: summary[k] for k in ('round', 'slots', 'passed', 'failed', 'not_run', 'response_statuses', 'upper_bound_violations')})
    if summary['failed'] or violations or not representation_pair:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
