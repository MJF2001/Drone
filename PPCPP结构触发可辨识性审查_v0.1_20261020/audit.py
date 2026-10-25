"""Read saved first/second rollouts, no solver imports or calls."""
import json,hashlib,sys,statistics,datetime
from pathlib import Path
from rule import measure,select
H=Path(__file__).resolve().parent;R=H.parent;UP=R/'PPCPP恢复时机对照_v0.1_20261020'
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
from crosscheck import calculate
TOTAL_KEYS=('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','direction_changes','completion_step','return_tail_steps','target_arrivals','duplicate_target_arrivals','remaining_before','newly_completed','active_targets','active_covered','missing_active','published_targets','published_covered','deferred','uncompleted_published')
POLICIES=('FIRST_FILTER','TWO_WINDOW_REPLAY')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def prepare():
    assert not (H/'protocol.json').exists()
    p=read(UP/'protocol.json');files={str(f):sha(f) for f in UP.rglob('*') if f.is_file()}
    for c in p['cases']:files[c['input']]=sha(c['input'])
    for f in (R/'评价指标完整补算与数据审计_v0.1_20261020').glob('*.py'):files[str(f)]=sha(f)
    for f in H.iterdir():
        if f.suffix in ('.py','.md'):files[str(f)]=sha(f)
    save('protocol.json',dict(stage='before_structural_feature_extraction',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,cases=p['cases'],seed=20261018,predicate='at least two U-components represented among the three deduplicated candidate rules',new_solver_calls=0,holdout=False,policies=POLICIES))
    print('registered',len(files),'files')
def protect():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    return p
def summarize(states):
    summary={}
    for batch in ('original20','controlled27'):
        xs=[x for x in states if x['batch']==batch];s=dict(n=len(xs),features={},replay={})
        for m in ('FIRST','SECOND'):
            trigger=[x for x in xs if x['features'][m]['triggered']];gain=[x for x in trigger if x['metrics'][m]['length']<x['metrics']['PPCPP']['length']]
            missed=[x['case_id'] for x in gain if not x['features'][m]['eligible']]
            skipped=[x['case_id'] for x in trigger if not x['features'][m]['eligible'] and x['metrics'][m]['length']==x['metrics']['PPCPP']['length']]
            s['features'][m]=dict(triggered=len(trigger),eligible=sum(x['features'][m]['eligible'] for x in trigger),known_improved=len(gain),retained_improved=len(gain)-len(missed),missed_improved=missed,skipped_no_improvement=skipped,conservative_gate_pass=not missed and bool(skipped))
        for policy in POLICIES:
            chosen=[x['selections'][policy] for x in xs];ms=[x['metrics'][m] for x,m in zip(xs,chosen)];totals={k:sum(v[k] for v in ms) for k in TOTAL_KEYS}
            totals.update(overlap_pooled=totals['duplicate_target_arrivals']/totals['target_arrivals'],active_coverage_pooled=totals['active_covered']/totals['active_targets'],published_coverage_pooled=totals['published_covered']/totals['published_targets'])
            pairs={}
            for ref in ('PPCPP','FIRST','SECOND'):
                ds=[v['length']-x['metrics'][ref]['length'] for x,v in zip(xs,ms)]
                pairs[ref]=dict(shorter=sum(d<0 for d in ds),equal=sum(d==0 for d in ds),longer=sum(d>0 for d in ds),difference=sum(ds),mean_relative=statistics.mean(d/x['metrics'][ref]['length'] for d,x in zip(ds,xs)))
            s['replay'][policy]=dict(totals=totals,source_counts={m:chosen.count(m) for m in ('PPCPP','FIRST','SECOND')},pairs=pairs,timing_measured=False,new_solver_calls=0)
        summary[batch]=s
    return summary
def main():
    p=protect();up=read(UP/'protocol.json');states=[];branches=0
    for c in p['cases']:
        inp=read(c['input']);row=dict(**c,features={},metrics={},sources={},selections={})
        for m in ('PPCPP','FIRST','SECOND'):
            j=next(j for j in up['jobs'] if j['batch']==c['batch'] and j['case_id']==c['case_id'] and j['seed']==p['seed'] and j['method']==m)
            path=UP/'execution/results'/(j['run_id']+'.json');x=read(path);raw=x['raw'];assert x['eligible']
            v=metrics(inp,raw['route']);assert v==calculate(inp,raw['route']);row['metrics'][m]=v;row['sources'][m]=str(path)
            if m!='PPCPP':
                row['features'][m]=measure(inp,raw,1 if m=='FIRST' else 2)
                for b in raw['branches']:assert metrics(inp,b['route'])==calculate(inp,b['route']);branches+=1
        for policy in POLICIES:row['selections'][policy]=select(policy,row['features']['FIRST'],row['features']['SECOND'])
        states.append(row)
    out=dict(states=states,summary=summarize(states),saved_cases=47,saved_results_read=141,feature_windows=94,actual_trigger_windows=sum(v['triggered'] for x in states for v in x['features'].values()),complete_candidate_branches_checked=branches,new_solver_calls=0,planner_changes=0,holdout=False)
    save('analysis.json',out);protect();print(json.dumps(out['summary'],ensure_ascii=False,indent=2))
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    else:main()
