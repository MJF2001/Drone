"""Preregister and freeze; no selector/geometry/planner import or evaluation."""
from pathlib import Path
from collections import Counter
import shutil
from fixtures import build
from io_utils import HERE, ROOT, write_json, sha, now

def main():
    registration = HERE/'门槛事前登记.json'
    if registration.exists():
        raise SystemExit('Already registered; refusing overwrite')
    cases = build()
    groups = Counter(x['group'] for x in cases)
    assert len(groups) == 18 and len(cases) <= 54 and max(groups.values()) <= 3
    for case in cases:
        assert len(case['input']['F']) <= 25 and len(case['suffix']['points']) <= 33
        assert len(case.get('actions', [])) <= 8 and len(case.get('primitives', [])) <= 2
    n = len(cases)
    bounds = {'sessions': n, 'stub_responses': n, 'selector': n, 'parse': 2*n,
              'candidate_checks': 25*n, 'candidate_geometry': 25*n, 'candidate_distance': 25*n,
              'candidate_resource_checks': 25*n, 'candidate_rejected': 25*n,
              'candidate_comparisons': 25*24*n, 'angle_tie_comparisons': 25*24*n, 'lex_tie_comparisons': 25*24*n,
              'input_geometry': 2*n, 'main_plan_audits': n, 'main_geometry': 33*n, 'main_distance': 33*n,
              'main_resource_checks': n, 'integer_allowance_certifications': n, 'execution_resource_checks': 8*n,
              'primitive_geometry': 2*n, 'primitive_distance': 2*n,
              'execution_commit_calls': 8*n, 'execution_commits_accepted': 8*n, 'execution_duplicate_rejected': 8*n,
              'execution_geometry': 8*n, 'execution_distance': 8*n,
              'predict_service_intersections': 25*n, 'main_service_intersections': 33*25*n,
              'primitive_service_intersections': 2*25*n, 'execution_service_intersections': 8*25*n,
              'predict_collect_here': n, 'main_collect_here': n, 'execution_collect_here': 8*n,
              'independent_session_audits': n, 'independent_execution_audits': n, 'independent_primitive_audits': n,
              'independent_execution_commit_checks': 8*n,
              'independent_saved_choice_comparisons': 25*n,
              'independent_geometry': (3+25+33+8+2)*n,
              'independent_distance': (25+1+33+8+2)*n,
              'independent_service_intersections': (1+33+8+2)*25*n,
              'independent_forbidden_box_checks': (3+25+33+8+2)*n*201*201,
              'primary_domain_points': (2+25+33+2+8)*n*2000}
    data = {'registered_utc': now(), 'round_limit': 3, 'all_round_session_cap': 162,
            'all_round_stub_cap': 162, 'this_round_slots': n, 'groups': dict(groups),
            'max_F': 25, 'max_P': 25, 'max_suffix_edges': 32, 'cases': cases,
            'per_round_counter_upper_bounds': bounds,
            'read_only_verify_upper_bounds': {k: v for k, v in bounds.items() if k.startswith('independent_')},
            'zero_required': ['native_planner', 'PPCPP', 'P2', 'BFS', 'A_star', 'visibility_graph', 'detector', 'closed_loop'],
            'clarification': '40 sessions are not all computations. Direct geometry and technical polylines counted separately.'}
    write_json(registration, data)
    (HERE/'根进度_执行前快照.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
    source_dir = HERE/'source_snapshot'
    source_dir.mkdir()
    names = ['真实停止点首连接与距离账本纯桩验收执行稿_给sol_20261022.md', 'AGENTS.md',
             '任意方向合法直达有限诊断_v0.1_20261022/geometry.py',
             '任意方向合法直达有限诊断_v0.1_20261022/audit_geometry.py',
             'PPCPP真实来向H1最小验收_v0.2_20261022/00_通俗报告与三栏结果.md',
             '真实停止点来向适配审查_v0.1_20261022/02_推荐合同与方向首连接.md']
    bindings = []
    for index, name in enumerate(names):
        src = ROOT/name
        target = source_dir/f'{index:02d}_{src.name}'
        shutil.copyfile(src, target)
        bindings.append({'source': name, 'copy': str(target.relative_to(HERE)), 'sha256': sha(src)})
    write_json(HERE/'source_bindings.json', bindings)
    old = []
    for dirname in ('PPCPP真实来向H1最小验收_v0.1_20261022', 'PPCPP真实来向H1最小验收_v0.2_20261022'):
        for f in sorted((ROOT/dirname).rglob('*')):
            if f.is_file():
                old.append({'path': str(f.relative_to(ROOT)), 'sha256': sha(f)})
    write_json(HERE/'旧H1两版只读哈希.json', old)
    table = ['# 18类事前预期（运行前冻结）', '', '|槽|类|手工夹具|预期|q|', '|---|---|---|---|---|']
    for case in cases:
        table.append(f'|{case["id"]}|{case["group_name"]}|{case["label"]}|{case["expect"]}|{case["expect"].get("q", "—")}|')
    (HERE/'18类事前预期.md').write_text('\n'.join(table)+'\n', encoding='utf-8')
    files = [p for p in HERE.iterdir() if p.is_file() and p.suffix == '.py']+[registration, HERE/'01_接口与数值合同.md']
    write_json(HERE/'round_1_freeze.json', {'utc': now(), 'files': {p.name: sha(p) for p in files},
               'expectations_cannot_change': True, 'geometry_or_selector_calls_so_far': 0})
    print({'registered_slots': n, 'groups': dict(groups), 'old_files_bound': len(old), 'no_test_executed': True,
           'candidate_geometry_cap': bounds['candidate_geometry'], 'main_geometry_cap': bounds['main_geometry'],
           'independent_geometry_cap': bounds['independent_geometry'],
           'primary_service_cap': sum(v for k, v in bounds.items() if k.endswith('_service_intersections') and not k.startswith('independent')),
           'execution_commits_cap': bounds['execution_commit_calls']})

if __name__ == '__main__':
    main()
