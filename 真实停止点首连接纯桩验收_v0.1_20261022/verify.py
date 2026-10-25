"""Saved evidence only. Never import/call selector, stub, execution committer or planners."""
from collections import Counter
from pathlib import Path
import ast
import independent as ind
from io_utils import HERE, ROOT, read_json, write_json, sha, now

def expect(case, result):
    out, ex = result['session'], case['expect']
    assert result['gate_status'] == 'passed'
    assert out['raw_input'] == case['input']
    assert out['fixed_response'] == case['suffix']
    for key in ('status', 'q', 'reason'):
        if key in ex:
            assert out.get(key) == ex[key]
    if 'h_entry' in ex:
        assert out['request']['h_entry'] == ex['h_entry']
    if 'allowance' in ex:
        assert out['request']['integer_suffix_allowance'] == ex['allowance']
    if 'gamma_H' in ex:
        assert out['predicted_entry']['H'] == ex['gamma_H']
    if 'actual_H' in ex:
        assert out['actual_after']['H'] == ex['actual_H']
    if 'candidate_reject' in ex:
        assert next(x for x in out['candidates'] if x['q'] == ex['candidate_reject'])['legal'] is False
    if 'deferred' in ex:
        assert out['request']['deferred'] == ex['deferred']
    if 'final_plan_E' in ex:
        assert ind.load(out['plan']['predicted_final']['E']['exact']) == ind.load(ex['final_plan_E'])
    assert [v['action'] for v in result.get('actions', [])] == case.get('actions', [])
    if result.get('actions'):
        final = result['actual_final']
        for key in ('H', 'S', 'h'):
            if 'final_'+key in ex:
                assert final[key] == ex['final_'+key]
        for key in ('E', 'M'):
            if 'final_'+key in ex:
                assert ind.load(final[key]['exact']) == ind.load(ex['final_'+key])
        if 'action_H' in ex:
            assert [r['result']['actual']['H'] for r in result['actions']] == ex['action_H']
    assert len(result.get('primitives', [])) == len(case.get('primitives', []))
    for saved, original in zip(result.get('primitives', []), case.get('primitives', [])):
        assert saved['a'] == original['a'] and saved['b'] == original['b']
        assert saved['legal'] == original['expect_legal']
        assert [v['cell'] for v in saved['center_hits']] == original['expect_hits']

def main():
    manifest = read_json(HERE/'completion_manifest.json')
    for name, digest in manifest['files'].items():
        assert sha(HERE/name) == digest, ('package_hash', name)
    for old in read_json(HERE/'旧H1两版只读哈希.json'):
        assert sha(ROOT/old['path']) == old['sha256'], ('old_changed', old['path'])
    for source in read_json(HERE/'source_bindings.json'):
        assert sha(ROOT/source['source']) == sha(HERE/source['copy']) == source['sha256']
    # Snapshot hashes, intentionally no requirement that live root progress remains equal.
    assert sha(HERE/'根进度_执行前快照.md') == manifest['root_before']
    assert sha(HERE/'根进度_执行后快照.md') == manifest['root_after']
    # Dependency safety is inspectable: main components only stdlib and new pure modules.
    allowed = {'collections', 'copy', 'functools', 'fractions', 'math', 'exact', 'geometry'}
    for name in ('exact.py', 'geometry.py', 'connector.py', 'independent.py'):
        tree = ast.parse((HERE/name).read_text(encoding='utf-8'))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                assert all(a.name in allowed for a in n.names)
            if isinstance(n, ast.ImportFrom):
                assert n.module in allowed
    reg = read_json(HERE/'门槛事前登记.json')
    rnd = manifest['accepted_round']
    result = read_json(HERE/'repair_rounds'/f'round_{rnd}'/'result.json')
    assert result['failed'] == result['not_run'] == 0 and not result['upper_bound_violations']
    assert result['saved_list_tuple_pair_equal'] is True
    c, rows, primary_sum, independent_sum = Counter(), [], Counter(), Counter()
    mapping = {r['id']: r for r in result['rows']}
    for case in reg['cases']:
        source = mapping[case['id']]
        path = HERE/source.get('evidence_path', str(Path('repair_rounds')/f'round_{rnd}'/'outputs'/f'{case["id"]}.json'))
        if 'evidence_sha256' in source:
            assert sha(path) == source['evidence_sha256']
        data = read_json(path)
        expect(case, data)
        if case.get('runtime_tuple'):
            assert set(data['runtime_container_evidence'].values()) == {'tuple'}
        if not source.get('reused'):
            primary_sum.update(data['primary_counts'])
            independent_sum.update(data['independent_counts'])
        checked = ind.audit_session(data['session'], c)
        if data.get('actions'):
            ind.audit_actions(data['session']['raw_input'], data['actions'], c)
        if data.get('primitives'):
            ind.audit_primitives(data['session']['raw_input'], data['primitives'], c)
        rows.append({'id': case['id'], 'status': 'verified_saved_only', 'checked': checked})
    assert primary_sum == Counter(result['primary_counts'])
    assert independent_sum == Counter(result['independent_counts'])
    upper = reg['read_only_verify_upper_bounds']
    assert all(k in upper and v <= upper[k] for k, v in c.items())
    report = {'utc': now(), 'status': 'VERIFIED_SAVED_ONLY', 'accepted_round': rnd,
              'saved_sessions_checked': len(rows), 'new_selector': 0, 'new_stub_responses': 0,
              'new_execution_committer': 0, 'native_planner': 0, 'PPCPP': 0, 'P2': 0,
              'BFS': 0, 'A_star': 0, 'visibility_graph': 0, 'saved_geometry_rechecks': dict(c),
              'old_H1_files_unchanged': len(read_json(HERE/'旧H1两版只读哈希.json')),
              'manifest_files_checked': len(manifest['files']), 'rows': rows}
    # New, separate receipt for each read-only invocation; never overwrite prior evidence.
    directory = HERE/'verify_receipts'
    directory.mkdir(exist_ok=True)
    index = len(list(directory.glob('verify_*.json')))+1
    target = directory/f'verify_{index:03d}.json'
    assert not target.exists()
    write_json(target, report)
    print({k: v for k, v in report.items() if k != 'rows'})

if __name__ == '__main__':
    main()
