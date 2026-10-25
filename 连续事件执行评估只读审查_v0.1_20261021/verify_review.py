"""Read-only hashes, saved-evidence and document checks; stdlib only."""
from pathlib import Path
import json,hashlib,re,ast,sys
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    sources=read(H/'source_hashes.json')
    for p,v in sources.items():assert sha(Path(p))==v,p
    x=read(H/'saved_evidence_checks.json');z=read(H/'zero_call_ledger.json')
    assert x['passed'] and len(sources)==z['source_files_read']==381
    assert len(x['old_continuous']['histories'])==10 and len(x['old_continuous']['responses'])==80 and x['old_continuous']['response_inputs_unique']==10
    assert x['old_continuous']['classification']==2 and x['widening']['classification']==3 and x['widening']['groups']==12 and x['widening']['states']==48
    assert x['stress']['states']==16 and x['stress']['position_dependent_opening_states']==4 and x['stress']['resource_not_debited_states']==16
    assert all(r['equal'] for r in x['source_snapshot_identity']) and len(x['source_snapshot_identity'])==7
    assert z['old_algorithm_modules_imported']==[] and z['read_source_unchanged_at_end']
    for key in ('planner_entries','native_cores','candidate_trials','BFS','Dijkstra','Astar','coverage_exact','new_routes','new_worlds','real_closed_loops','simulated_closed_loops','old_verify_or_tests_executed'):assert z[key]==0,key
    # Refuse non-stdlib/new-old-module imports in the only saved-data audit tool.
    tree=ast.parse((H/'audit_saved.py').read_text(encoding='utf8'));allowed={'pathlib','json','hashlib','ast','sys','traceback'}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):assert all(n.name in allowed for n in node.names)
        if isinstance(node,ast.ImportFrom):assert node.module in allowed
    links=0
    for name in ('01_能力与来源审查.md','02_最小连续执行协议草案.md','03_通俗结论与待裁决.md'):
        s=(H/name).read_text(encoding='utf8')
        for target in re.findall(r'\]\(([^)]+)\)',s):
            p,line=(target.rsplit(':',1) if re.search(r':\d+$',target) else (target,None));path=Path(p) if re.match(r'^[A-Za-z]:/',p) else H/p
            assert path.is_file(),(name,target)
            if line:assert 1<=int(line)<=len(path.read_text(encoding='utf-8-sig').splitlines()),target
            links+=1
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    assert not any(name in sys.modules for name in ('runtime','candidate','portable_frozen','model','baseline_suite','ppcpp_independent','p2_search_audit','continuous_history_inputs_20261016'))
    print(json.dumps(dict(status='ALL PASS',source_hashes=len(sources),document_links=links,old_modules_imported=0,planner_calls=0,cores=0,graph_searches=0,new_routes=0,new_worlds=0,closed_loop_runs=0,claim='Review and draft only; not continuous-event experiment execution'),ensure_ascii=False))
if __name__=='__main__':main()
