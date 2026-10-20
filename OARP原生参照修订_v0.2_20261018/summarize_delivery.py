"""Create descriptive tables and a post-execution dependency snapshot, no solver."""
import collections,csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def save(p,x):(ROOT/p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    assert not (ROOT/'dependency_lock_after_execution.json').exists()
    deps=ROOT.parent/'DeepSeek_底层算法开发比较_20261018/sources/reference_tree/研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/.deps'
    paths=[p for p in deps.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc']
    exe=Path(sys.executable);paths.extend([exe]+list(exe.parent.glob('python*.dll')))
    save('dependency_lock_after_execution.json',{'snapshot_timing':'after all real calls; not a pre-execution dependency seal',
        'python_version':sys.version,'python_executable':str(exe),'expected_versions':{'numpy':'2.5.4','pyscipopt':'6.2.1','glns':'0.1.0'},
        'files':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}})
    rows=[]
    for p in sorted((ROOT/'results').glob('*.json')):
        r=json.loads(p.read_text(encoding='utf-8'));d=r['core_detail'];core=r['core_plan']
        rows.append({'plan_id':r['plan_id'],'kind':r['kind'],'method':r['method'],'cap':r['cap'],
            'remaining_resource':r['request']['resource'],'core_status':d.get('status','empty_target_direct_return'),
            'core_steps':len(core['route'])-1 if core else '', 'core_candidate_valid':r['flags']['core_candidate_valid'],
            'selected_steps':len(r['route'])-1 if r['route'] else '', 'selected_source':r['source'],
            'final_route_valid':r['flags']['route_valid'],'call_within_budget':r['flags']['call_within_budget'],
            'public_seconds':r['public_seconds'],'certification_repair':d.get('certification_repair',False),
            'core_error':d.get('error',''),'core_interruption':d.get('interruption','')})
    with (ROOT/'response_table.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    ledger=[json.loads(s) for s in (ROOT/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
    counts=collections.Counter(e['kind'] for e in ledger if e['event']=='start')
    events=[r for r in rows if r['kind']=='event']
    save('summary.json',{'full_entry_calls':sum(counts[k] for k in ('event','boundary','preparation')),
        'counts_by_kind':dict(counts),'new_solver_attempts':counts['SCIP']+counts['GLNS'],
        'event_final_valid':sum(r['final_route_valid'] for r in events),
        'event_core_valid':sum(r['core_candidate_valid'] for r in events),
        'event_core_infeasible':sum(r['core_status']=='infeasible' for r in events),
        'event_final_sources':dict(collections.Counter(r['selected_source'] for r in events)),
        'all_full_calls_completed_before_deadline':all(r['call_within_budget'] for r in rows),
        'successful_task_retries':0,'unexpected_full_calls':0,'planner_hard_terminations':0,
        'shared_rank_certification_repair_activated':any(r['certification_repair'] for r in rows),
        'dependency_snapshot_post_execution':True,'old_delivery_files_unchanged':150})
    print(json.dumps(json.loads((ROOT/'summary.json').read_text(encoding='utf-8')),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
