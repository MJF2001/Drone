"""Two explicitly diagnostic 10-iteration prefix profiles, not repeat grading."""
import sys,json,time,hashlib,cProfile,pstats
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
ROAD=ROOT/'Cstar道路正确性验收_20261019'
sys.path.insert(0,str(ROAD))
from run import verify,read,sha
from audit_outputs import audit
def write(p,z):
    with Path(p).open('xb') as f:f.write(json.dumps(z,ensure_ascii=False,indent=2).encode())
def worker(kind):
    protocol=verify();job=next(j for j in protocol['jobs'] if j['name']=='large_g1_development__'+kind and j['seed']==20261018)
    c=read(ROAD/job['input']);request={k:c[k] for k in protocol['core_input_whitelist']}
    sys.path.insert(0,str(ROOT/protocol['algorithm_source']))
    from history_adapter import solve
    profile=cProfile.Profile();profile.enable()
    result=solve(request,20,20261018,max_iterations=10)
    profile.disable();profile.dump_stats(str(HERE/(kind+'.pstats')))
    result=json.loads(json.dumps(result));reference=read(ROAD/'execution'/(job['run_id']+'.result.json'))['result']
    assert result['status']=='iteration_limit' and len(result['iterations'])==10
    assert result['diagnostic_route']==reference['diagnostic_route'][:len(result['diagnostic_route'])]
    assert result['task_filters']==reference['task_filters'][:len(result['task_filters'])]
    assert result['prune_audits']==reference['prune_audits'][:len(result['prune_audits'])]
    audit(c,result,20);write(HERE/(kind+'_result.json'),result)
    stats=pstats.Stats(profile);functions=[];selected=[]
    for (filename,line,name),(cc,nc,tt,ct,callers) in stats.stats.items():
        row=dict(file=filename,line=line,function=name,primitive_calls=cc,total_calls=nc,self_seconds=tt,cumulative_seconds=ct)
        functions.append(row)
        if name=='sync_task_protection' or (name=='refresh_retreat' and filename.endswith('history_adapter.py')) or (name=='snapshot' and filename.endswith('rcg.py')):
            selected.append(row)
    search_callers=[]
    for (filename,line,name),entry in stats.stats.items():
        if name=='path' and filename.endswith('rcg.py'):
            for (f,l,n),metrics in entry[4].items():search_callers.append(dict(caller_file=f,caller_function=n,raw_call_metrics=list(metrics)))
    write(HERE/(kind+'_profile.json'),dict(diagnostic=True,not_comparable_to_unprofiled_seconds=True,budget=20,max_iterations=10,status=result['status'],iterations=10,prefix_matches_saved_formal_run=True,prune_snapshots_match_saved_run=True,profile_total_seconds=stats.total_tt,solve_seconds=result['seconds'],selected_disjoint_cumulative_functions=selected,rcg_search_callers=search_callers,top_self_functions=sorted(functions,key=lambda x:x['self_seconds'],reverse=True)[:25]))
def main():
    if len(sys.argv)>1:worker(sys.argv[1]);return
    if (HERE/'protocol.json').exists():raise RuntimeError('Do not overwrite diagnostics')
    protocol=verify()
    write(HERE/'protocol.json',dict(scope='Two prefix diagnostics only: large_g1 control/event, seed 20261018, first 10 iterations, cProfile enabled',calls=2,budget_seconds=20,max_iterations=10,watchdog_seconds=35,source_changed=False,original_40_results_unchanged=True,not_performance_comparison=True))
    write(HERE/'pre_run_manifest.json',dict(wrapper_sha256=sha(Path(__file__)),runtime=read(ROAD/'freeze_manifest.json')['external_runtime'],formal_evidence={str(p.relative_to(ROOT)):sha(p) for p in (ROAD/'protocol.json',ROAD/'execution/completion.json',ROAD/'execution_reaudit.json')}))
    import subprocess
    for kind in ('control','event'):
        with (HERE/(kind+'.log')).open('x',encoding='utf8') as log:
            subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__)),kind],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=35,check=True)
    verify();print('Two diagnostic prefixes profiled; frozen sources and original protocol unchanged.')
if __name__=='__main__':main()
