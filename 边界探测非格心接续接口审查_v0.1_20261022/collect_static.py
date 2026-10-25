"""Collect existing text/bytes only. No production imports or execution."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = '研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/'
PAPERS = '研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009/'
SOURCES = [
    ('S01', 'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/runtime.py'),
    ('S02', 'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/candidate.py'),
    ('S03', '基线复现准备_20261019/独立版_v0.2/ppcpp.py'),
    ('S04', 'PPCPP结构候选新开发验证_v0.1_20261020/validation.py'),
    ('S05', '基线复现准备_20261019/ppcpp_independent.py'),
    ('S06', '研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/candidate_baselines/PPCPP_CORE4/v0.1_20261014/source/candidate_ppcpp_core4_20261014.py'),
    ('S07', 'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/p2_adapter.py'),
    ('S08', '连续事件六世界开发比较_v0.1_20261022/executor.py'),
    ('S09', '连续事件六世界开发比较_v0.1_20261022/contracts.py'),
    ('S10', FROZEN + 'model.py'),
    ('S11', FROZEN + 'unified_geometry.py'),
    ('S12', FROZEN + 'bfs_metric_geometry.py'),
    ('S13', FROZEN + 'p2_search_audit.py'),
    ('S14', 'portable_frozen.py'),
    ('S15', '任意方向合法直达有限诊断_v0.1_20261022/engine.py'),
    ('S16', '任意方向合法直达有限诊断_v0.1_20261022/geometry.py'),
    ('S17', '任意方向合法直达有限诊断_v0.1_20261022/audit_geometry.py'),
    ('S18', 'PPCPP直达质量时间开发比较_v0.1_20261022/run.py'),
]
DOCUMENTS = [
    'AGENTS.md',
    PAPERS + '02_论文主题与具体研究问题.md',
    PAPERS + '42_三种基线适配审查与冻结说明_20261012.md',
    PAPERS + '00_阅读入口.md',
    '边界探测安全停止模型与接续接口审查执行稿_v1.2_给sol_20261022.md',
    '边界探测安全停止模型与接续接口审查执行稿_v1.1_给sol_20261022.md',
    '边界探测安全停止模型与接续接口审查执行稿_给sol_20261022.md',
    '任意方向合法直达有限诊断执行稿_给sol_20261022.md',
    '连续事件真实接口验收_v0.1_20261021/通俗报告.md',
    '连续事件六世界开发比较_v0.1_20261022/通俗报告与完整结果.md',
    '连续事件实际成本只读诊断_v0.1_20261022/通俗结论与裁决建议.md',
    'PPCPP直达事件信息复用可行性审查_v0.1_20261022/00_通俗结论.md',
    'PPCPP直达事件信息复用可行性审查_v0.1_20261022/01_三个对象与依赖失效成本.md',
    'PPCPP直达事件信息复用可行性审查_v0.1_20261022/02_任意方向执行接口缺口.md',
    'PPCPP直达事件信息复用可行性审查_v0.1_20261022/来源hash.json',
    'PPCPP直达质量时间开发比较_v0.1_20261022/source_seal.json',
    'PPCPP直达质量时间开发比较_v0.1_20261022/postsrc/engine.py',
    'PPCPP直达质量时间开发比较_v0.1_20261022/postsrc/geometry.py',
    'PPCPP直达质量时间开发比较_v0.1_20261022/postsrc/audit_geometry.py',
    FROZEN + 'baseline_suite.py',
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, obj):
    with (HERE / name).open('x', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def main():
    assert not (HERE / '来源hash.json').exists(), 'static collection already exists; no overwrite'
    hashes = {str((ROOT / rel).resolve()): sha(ROOT / rel) for _, rel in SOURCES}
    hashes.update({str((ROOT / rel).resolve()): sha(ROOT / rel) for rel in DOCUMENTS})
    evidence = []
    links = ['# 源码逐行证据索引', '', '仅读取源码，未导入或执行。SHA256按原始字节计算；完整文本保留一基行号。', '']
    for sid, rel in SOURCES:
        p = (ROOT / rel).resolve()
        lines = p.read_text(encoding='utf-8-sig').splitlines()
        evidence.append(dict(id=sid, path=str(p), sha256=sha(p), line_count=len(lines),
                             lines=[dict(number=i, text=t) for i, t in enumerate(lines, 1)]))
        links.append(f'- {sid} [{rel}](<{p.as_posix()}:1>)：{len(lines)}行；SHA256 `{sha(p)}`。')
    save('源码逐行证据.json', evidence)
    (HERE / '源码索引.md').write_text('\n'.join(links) + '\n', encoding='utf-8')
    save('来源hash.json', hashes)

    old_seal = json.loads((ROOT / DOCUMENTS[15]).read_text(encoding='utf-8-sig'))
    matches = []
    for sid, rel in SOURCES:
        path = str((ROOT / rel).resolve())
        if path in old_seal:
            assert hashes[path] == old_seal[path], ('historical source mismatch', sid)
            matches.append(dict(id=sid, path=path, sha256=hashes[path]))
    same_post = []
    for name in ('engine.py', 'geometry.py', 'audit_geometry.py'):
        original = ROOT / '任意方向合法直达有限诊断_v0.1_20261022' / name
        actual = ROOT / 'PPCPP直达质量时间开发比较_v0.1_20261022/postsrc' / name
        assert sha(original) == sha(actual)
        assert sha(actual) == old_seal[str(actual.resolve())]
        same_post.append(dict(original=str(original), actual_loaded_copy=str(actual), sha256=sha(actual)))
    prior = json.loads((ROOT / 'PPCPP直达事件信息复用可行性审查_v0.1_20261022/来源hash.json').read_text(encoding='utf-8-sig'))
    prior_matches = []
    for path, digest in hashes.items():
        if path in prior:
            assert digest == prior[path], ('previous review source mismatch', path)
            prior_matches.append(path)
    save('历史源一致性.json', dict(historical_pipeline_source_matches=matches,
         postprocess_byte_identical=same_post, previous_review_source_matches=prior_matches,
         scope='Selected source byte consistency only; not a runtime/model acceptance test.'))
    (HERE / '执行依据_v1.2_原字节.md').write_bytes((ROOT / DOCUMENTS[4]).read_bytes())
    (HERE / '根进度_执行前快照.md').write_bytes((ROOT / '当前进度与下一步.md').read_bytes())
    save('版本与范围.json', dict(executed_draft=DOCUMENTS[4], directory_absent_checked_before_creation=True,
         superseded_drafts_retained=DOCUMENTS[5:7], high_observation='excluded; not pending',
         source_files=len(SOURCES), hashed_sources=len(hashes), paper_gate_items=18,
         gate_execution='NOT_EXECUTED', implementation='NOT_STARTED',
         static_lookup_note='One rg lookup used an absent guessed p2_search_audit.py path; corrected via rg --files to frozen/v2 source. No executable call or experimental failure.',
         collected_utc=datetime.now(timezone.utc).isoformat()))
    counters = {name: 0 for name in (
        'planning_entries', 'planning_cores', 'graph_searches', 'geometry_LOS_queries',
        'service_intersection_queries', 'input_generation', 'candidates', 'new_routes',
        'closed_loop_sessions', 'performance_tests', 'stub_calls', 'counterfactual_replays',
        'production_module_imports', 'old_verify_runs', 'holdout_uses', 'external_messages')}
    save('零调用账.json', dict(counters=counters,
         performed=['Read existing source/document/JSON bytes', 'SHA256 and source line-number collection',
                    'Write review documents and update root progress', 'Static file-integrity verification only'],
         not_evidence_of_runtime_validation=True, paper_gate_status='all 18 not executed'))
    print(json.dumps(dict(source_files=len(evidence), hashed_sources=len(hashes),
          old_pipeline_matches=len(matches), prior_review_matches=len(prior_matches),
          postprocess_identical_copies=len(same_post), all_new_algorithm_calls=0), ensure_ascii=False))

if __name__ == '__main__':
    main()
