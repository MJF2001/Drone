"""Copy immutable code, record static import review, preregister only. No execution."""
from pathlib import Path
from collections import Counter
import shutil, ast, platform, sys
from common import HERE, ROOT, dump, read, sha, now
from fixtures import build, tech_plan

def main():
    assert not (HERE/'registration.json').exists(), 'refuse registration overwrite'
    pure = ROOT/'真实停止点首连接纯桩验收_v0.1_20261022'
    h1 = ROOT/'PPCPP真实来向H1最小验收_v0.2_20261022'
    post = ROOT/'任意方向合法直达有限诊断_v0.1_20261022'
    pairs = [(pure/'exact.py', HERE/'exact.py'), (pure/'geometry.py', HERE/'geometry.py'),
             (pure/'connector.py', HERE/'connector.py'), (pure/'independent.py', HERE/'geometry_audit.py'),
             (h1/'h1_direction.py', HERE/'h1_direction.py'), (h1/'h1_rewards.py', HERE/'h1_rewards.py'),
             (h1/'independent_audit.py', HERE/'h1_audit.py'),
             (h1/'derived/runtime_h1.py', HERE/'derived/runtime_h1.py'),
             (h1/'derived/candidate_h1.py', HERE/'derived/candidate_h1.py'),
             (h1/'derived/ppcpp.py', HERE/'source_snapshot/h1_ppcpp.py'),
             (post/'engine.py', HERE/'postsrc/engine.py'), (post/'geometry.py', HERE/'postsrc/geometry.py'),
             (post/'verify.py', HERE/'postsrc/audit_saved.py'), (post/'audit_geometry.py', HERE/'postsrc/audit_geometry.py'),
             (ROOT/'真实停止点首连接接入H1与P2最小验收执行稿_给sol_20261022.md', HERE/'source_snapshot/执行稿.md')]
    bindings = []
    for source, copy in pairs:
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, copy)
        bindings.append({'source': str(source.relative_to(ROOT)), 'copy': str(copy.relative_to(HERE)), 'sha256': sha(source)})
    dump(HERE/'bindings.json', bindings)
    cases, stubs = build(), tech_plan()
    for c in cases:
        assert len(c['input']['F']) <= 25 and len(c['input']['P']) <= 12
    assert len(cases) == 6 and sum(x['max_stub_attempts'] for x in stubs) == 12
    jobs = []
    for index, case in enumerate(cases):
        dump(HERE/'inputs'/f'{case["id"]}.json', case)
        for method in (('H1', 'P2') if index % 2 == 0 else ('P2', 'H1')):
            jobs.append({'id': f'{case["id"]}_{method}', 'case': case['id'], 'method': method,
                         'seed': 20261022, 'input': f'inputs/{case["id"]}.json'})
    limits = {'connector_candidates': 25, 'native_return_edges': 100, 'post_return_edges': 100, 'full_return_edges': 101,
              'post_candidate_geometry': 4096, 'post_source_geometry': 100, 'post_output_geometry': 100,
              'post_service_intersections': 1200, 'wrapper_geometry': 327, 'wrapper_distance': 326,
              'wrapper_service_intersections': 3624, 'independent_geometry': 327,
              'independent_service_intersections': 3624, 'independent_distance': 227,
              'native_context_BFS': 1, 'native_distance_row_BFS': 25, 'native_Astar': 625,
              'native_geometry_distance': 1000000, 'native_geometry_path': 10000, 'native_internal_main_audits': 64}
    dump(HERE/'registration.json', {'utc': now(), 'cases': cases, 'jobs': jobs, 'stub_tests': stubs,
         'limits_per_real_slot': limits, 'real_core_entry_cap': 12, 'stub_attempts_per_round_cap': 12,
         'stub_round_cap': 3, 'all_stub_attempts_cap': 36, 'pipeline_seconds': 30, 'connector_seconds': 2,
         'core_seconds_max': 20, 'post_candidate_absolute_seconds': 28, 'max_F': 25, 'max_P': 12,
         'read_only_verify': 'No selector/core/postprocessor; separately count geometry of saved outputs',
         'time_semantics': 'imports excluded; parse, contract, conversion, native, shortcut, main audits and encoding included; independent audit outside'})
    # Bind old sources/results including prior failure history. Exclude no old files.
    old = []
    for directory in (pure, h1, ROOT/'PPCPP真实来向H1最小验收_v0.1_20261022'):
        for f in sorted(directory.rglob('*')):
            if f.is_file():
                old.append({'path': str(f.relative_to(ROOT)), 'sha256': sha(f)})
    frozen = ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source'
    for f in sorted(frozen.rglob('*.py')):
        old.append({'path': str(f.relative_to(ROOT)), 'sha256': sha(f)})
    for directory in (ROOT/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020', ROOT/'基线复现准备_20261019'):
        for name in ('runtime.py', 'p2_adapter.py', 'ppcpp_independent.py', '独立版_v0.2/ppcpp.py'):
            f = directory/name
            if f.exists():
                old.append({'path': str(f.relative_to(ROOT)), 'sha256': sha(f)})
    dump(HERE/'old_files.json', old)
    guards = {str(ROOT/item['path']): item['sha256'] for item in old}
    for path in (ROOT/'PPCPP直达质量时间开发比较_v0.1_20261022/source_seal.json',
                 h1/'原来源hash.json'):
        for name, digest in read(path).items():
            assert sha(name) == digest, ('preexisting_source_conflict', name)
            guards[name] = digest
    dump(HERE/'external_source_guards.json', guards)
    (HERE/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
    rows = []
    for f in sorted(HERE.rglob('*.py')):
        tree = ast.parse(f.read_text(encoding='utf-8-sig'))
        calls = []
        for node in tree.body:
            # Only unguarded top-level statements, excluding definitions and main guard.
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.If)):
                continue
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    name = ast.unparse(n.func)
                    assert name.split('.')[-1] not in ('solve', 'run_payload', 'process', 'pipeline', 'run')
                    calls.append(name)
        rows.append({'file': str(f.relative_to(HERE)), 'unguarded_top_level_calls': calls,
                     'no_unguarded_task_entry': True})
    dump(HERE/'static_import_review.json', {'utc': now(), 'files': rows,
         'note': 'Original runtime loads function modules at import; dynamic cold-load profile also required before native calls.',
         'source_alias': 'runtime_h1 unchanged loads old v0.1 derived/ppcpp.py; same byte hash as v0.2 source snapshot'})
    dump(HERE/'environment.json', {'python': sys.version, 'executable': sys.executable, 'platform': platform.platform(),
        'threads': {'OMP_NUM_THREADS': 1, 'OPENBLAS_NUM_THREADS': 1, 'MKL_NUM_THREADS': 1},
        'strategy': 'serial process per slot, new geometry/cache for every entry, no warmup planner call'})
    print({'registered_real_slots': len(jobs), 'stub_tests': len(stubs), 'max_stub_attempts': 12,
           'old_files_bound': len(old), 'sources_copied': len(bindings), 'no_geometry_or_core_executed': True})

if __name__ == '__main__':
    main()
