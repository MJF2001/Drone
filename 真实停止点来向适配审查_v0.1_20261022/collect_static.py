"""Read and seal static source/document evidence only; never import production."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PRIOR = ROOT / '边界探测非格心接续接口审查_v0.1_20261022'
PAPERS = ROOT / '研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009'
DRAFT = ROOT / '真实停止点与来向独立适配审查执行稿_给sol_20261022.md'
FROZEN = ROOT / '研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def save(name, obj):
    with (HERE / name).open('x', encoding='utf8', newline='\n') as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def main():
    assert not (HERE / '来源hash.json').exists(), 'collection exists; do not overwrite'
    prior_sources = read(PRIOR / '源码逐行证据.json')
    selected = [(e['id'], Path(e['path'])) for e in prior_sources]
    selected.append(('S19', FROZEN / 'baseline_suite.py'))
    prior_manifest = read(PRIOR / 'completion_manifest.json')
    for name, digest in prior_manifest['files'].items():
        assert sha(PRIOR / name) == digest, ('prior sealed artifact changed', name)
    # Do not run the prior verify: its live-root check naturally predates newer progress.
    hashes = {}
    evidence = []
    lines_md = ['# 源码索引', '', 'S01—S18沿用上轮编号，S19补共同check_contract。按原始字节SHA256，逐行文本独立保存；未动态导入。', '']
    occurrence_rows = []
    for sid, p in selected:
        p = p.resolve()
        hashes[str(p)] = sha(p)
        rows = p.read_text(encoding='utf-8-sig').splitlines()
        if sid != 'S19':
            old = next(e for e in prior_sources if e['id'] == sid)
            assert hashes[str(p)] == old['sha256'], ('source changed since prior review', sid)
        numbered = [dict(number=i, text=t) for i, t in enumerate(rows, 1)]
        evidence.append(dict(id=sid, path=str(p), sha256=sha(p), line_count=len(rows), lines=numbered))
        lines_md.append(f'- {sid} [{p.relative_to(ROOT).as_posix()}](<{p.as_posix()}:1>)；{len(rows)}行；SHA256 `{sha(p)}`。')
        matches = [dict(number=q['number'], text=q['text']) for q in numbered
                   if re.search(r'\b(current|previous|prev|cur|initial_previous)\b', q['text'])]
        occurrence_rows.append(dict(id=sid, path=str(p), occurrences=matches))
    documents = [ROOT / 'AGENTS.md', DRAFT,
        ROOT / '边界探测安全停止模型与接续接口审查执行稿_v1.2_给sol_20261022.md',
        PAPERS / '02_论文主题与具体研究问题.md',
        PAPERS / '42_三种基线适配审查与冻结说明_20261012.md', PAPERS / '00_阅读入口.md',
        ROOT / 'PPCPP直达质量时间开发比较_v0.1_20261022/source_seal.json']
    documents += [p for p in PRIOR.rglob('*') if p.is_file()]
    post_pairs = []
    for name in ('engine.py', 'geometry.py', 'audit_geometry.py'):
        orig = ROOT / '任意方向合法直达有限诊断_v0.1_20261022' / name
        actual = ROOT / 'PPCPP直达质量时间开发比较_v0.1_20261022/postsrc' / name
        assert sha(orig) == sha(actual)
        documents.append(actual)
        post_pairs.append(dict(original=str(orig), actual_loaded_copy=str(actual), sha256=sha(orig)))
    for p in documents:
        hashes[str(p.resolve())] = sha(p)
    seal = read(ROOT / 'PPCPP直达质量时间开发比较_v0.1_20261022/source_seal.json')
    historical_matches = []
    for sid, p in selected:
        key = str(p.resolve())
        if key in seal:
            assert hashes[key] == seal[key], ('historical pipeline bytes changed', sid)
            historical_matches.append(dict(id=sid, path=key, sha256=seal[key]))
    for row in post_pairs:
        assert seal[str(Path(row['actual_loaded_copy']).resolve())] == row['sha256']
    save('来源hash.json', hashes)
    save('源码逐行证据.json', evidence)
    save('current_previous文本出现清单.json', dict(note='Text occurrences include inactive LAST and historical helpers. Activation classification is in 01; occurrences are not a dynamic call trace.', sources=occurrence_rows))
    save('历史源与旧包一致性.json', dict(prior_package_manifest_sha256=sha(PRIOR / 'completion_manifest.json'),
        prior_package_files_verified=len(prior_manifest['files']), prior_source_matches=18,
        historical_pipeline_source_matches=historical_matches, postprocess_copies=post_pairs,
        prior_verify_not_run=True, live_root_not_compared_to_old_progress=True,
        prior_proposal_status='Forced axial tail rejected by latest user; preserved as history, not approved.'))
    (HERE / '源码索引.md').write_text('\n'.join(lines_md) + '\n', encoding='utf8')
    (HERE / '执行依据_原字节.md').write_bytes(DRAFT.read_bytes())
    (HERE / '根进度_执行前快照.md').write_bytes((ROOT / '当前进度与下一步.md').read_bytes())
    counters = {name: 0 for name in ('planning_entries', 'planning_cores', 'graph_searches',
        'geometry_queries', 'LOS_queries', 'service_intersections', 'candidates',
        'input_generation', 'new_routes', 'closed_loop_sessions', 'performance_tests',
        'stub_calls', 'production_imports', 'historical_verify_runs', 'holdout_uses',
        'external_messages')}
    save('零调用账.json', dict(counters=counters, paper_gates=8, paper_gate_runs=0,
        work_done='Existing text/JSON/bytes read; SHA256, line collection and text occurrence inventory; paper interface design; progress and sealed review artifacts.',
        source_evidence_is_not_runtime_validation=True))
    save('范围与版本.json', dict(executed_draft=str(DRAFT), directory_absence_checked=True,
        collected_utc=datetime.now(timezone.utc).isoformat(), sources=19, hashed_files=len(hashes),
        direction_definitions=2, recommendation='H1 true normalized incoming direction; finite single straight entry decision',
        forced_axial_tail='REJECTED_NOT_USED', implementation='NOT_STARTED', experiments='NOT_STARTED',
        inherited_unknowns='v1.2 detection, unknown-map and timing policies remain unresolved; not re-audited or chosen here.',
        paper_gates=8, paper_gate_runs=0))
    print(json.dumps(dict(source_files=len(evidence), hashed_files=len(hashes),
        prior_package_files_verified=len(prior_manifest['files']), historical_pipeline_matches=len(historical_matches),
        all_new_algorithm_calls=0), ensure_ascii=False))

if __name__ == '__main__':
    main()
