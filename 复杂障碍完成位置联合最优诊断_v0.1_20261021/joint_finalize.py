"""Final execution ledger and immutable delivery manifest, refuses overwrite."""
from joint_common import H,R,read,save,sha
if __name__=='__main__':
    records=[__import__('json').loads(x) for x in (H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()]
    save(H/'call_ledger.json',dict(PPCPP_entries=sum(r['phase'] in ('prep','formal') for r in records),PPCPP_preparation=2,PPCPP_formal=16,coverage_exact_searches=sum(r['phase'] in ('gate','exact') for r in records),gate_problem_instances=8,gate_exact_searches=16,formal_problem_instances=32,formal_primary_BFS_searches=32,formal_independent_Dijkstra_searches=32,coverage_BFS_total=40,coverage_Dijkstra_total=40,verification_coverage_searches=0,verification_planner_calls=0,P2_LAST_ORIENT_new_candidates=0,retries=0,holdout=0,ordinary_graph_offline=dict(build_base_BFS=16,analysis_base_BFS=16,verification_expected_base_BFS=32,latest_upstream_verify=dict(base_BFS=16,ordinary_point_Dijkstra=29,provenance='Derived from upstream saved pure compute implementation; this round ran its read-only verifier once, never reran96 planning routes.')),expected_total_offline_base_BFS_after_one_verify=80,note='Ordinary graph distances and checking saved state-closure proofs are distinct from coverage search. Actual final verification operations are recorded in verify.log; verifier never reruns exact engines.'))
    context={}
    for directory in ('PPCPP小图最优差距诊断_v0.2_20261020','PPCPP结束位置跨几何验证_v0.1_20261020','PPCPP保留末采集格候选_v0.1_20261020'):
        for p in (R/directory).glob('*'):
            if p.is_file() and (p.suffix=='.md' or p.name in ('exact.py','independent.py','manifest.json')):context[str(p)]=sha(p)
    save(H/'context_reading_hashes.json',dict(note='Contextual prior-study documents/models, recorded at delivery; actual runtime code/inputs were sealed before execution in the two stage seals.',files=context))
    save(H/'manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name not in ('manifest.json','verify.log')})
    print('Final ledger and manifest saved; verification log is excluded from self-reference.')
