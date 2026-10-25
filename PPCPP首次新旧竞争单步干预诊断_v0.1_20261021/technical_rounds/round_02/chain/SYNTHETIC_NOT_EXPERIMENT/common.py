"""I/O, hash stages and unchanged dual metrics; no planner imports."""
from pathlib import Path
import json,hashlib,csv,importlib.util,collections,statistics
H=Path(__file__).resolve().parent;R=H.parent;B=R/'PPCPP侧向拓宽开发诊断_v0.4_20261021';P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020';M=R/'评价指标完整补算与数据审计_v0.1_20261020'
LABEL='PPCPP_FIRST_NEW_STEP_DIAG_v0.1'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def norm(x):return json.loads(json.dumps(x,ensure_ascii=False))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def csvsave(p,rows):
    if not rows:return
    with Path(p).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,tuple)) else v for k,v in r.items()} for r in rows])
def load(n,p):
    s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
metric=load('first_new_metric',M/'metrics.py').metrics;cross=load('first_new_cross',M/'crosscheck.py').calculate
def both(c,r):
    a=metric(c,r);assert a==cross(c,r) and a['complete_legal'];return a
def binding():return {n:sha(H/n) for n in read(H/'binding_files.json')}
def receipt(stage,paths):save(H/'receipts'/f'{stage}.json',dict(stage=stage,status='PASS',binding=binding(),files={str(Path(p).relative_to(H)):sha(p) for p in paths}))
def require(stage):
    x=read(H/'receipts'/f'{stage}.json');assert x['stage']==stage and x['status']=='PASS' and x['binding']==binding(),stage
    for p,h in x['files'].items():assert sha(H/p)==h,p
    return x
def preseal():
    require('preseal');s=read(H/'preseal.json');assert s['complete'] and s['binding']==binding()
    for p,h in s['critical'].items():assert sha(p)==h,p
    return s
def plan():
    p=read(H/'plan.json')
    if H.name!='SYNTHETIC_NOT_EXPERIMENT':assert p==dict(counts=dict(OFF=144,ON=144),entry_cap=288,entry_budget=20,watchdog=90,threads=1,expected_triggered_states=24,expected_protection_states=24)
    else:assert read(H/'SYNTHETIC_NOT_EXPERIMENT.json')['synthetic_only']
    return p
EQUIVALENCE_EXCLUSIONS={
 'result.entry_seconds':'independent execution time',
 'result.phase_seconds':'independent phase times',
 'result.raw.branches.P0.seconds':'native execution time',
 'result.raw.branches.P0.budget':'remaining shared entry deadline depends on elapsed overhead',
 'result.raw.branches.P0.accepted_seconds':'native acceptance time',
 'result.raw.branches.P0.overrun_gt_10ms':'time classification separately required timely',
 'result.raw.branches.P0.version':'explicit diagnostic version',
 'result.raw.branches.P0.method':'explicit diagnostic method',
 'result.raw.branches.P0.diagnostic':'new independent diagnostic metadata; OFF must be empty',
 'result.diagnostic_entry':'explicit new entry identifier',
 'result.diagnostic_mode':'explicit OFF/ON identifier'}
def equivalent(off,old):
    x=norm(off['result']);y=norm(old['result']);p=x['raw']['branches']['P0'];assert x['diagnostic_entry']==LABEL and x['diagnostic_mode'] in ('OFF','ON') and p['version']==LABEL and p['method']=='PPCPP_FIRST_NEW_STEP_DIAG'
    assert p['diagnostic']['trigger_count']==0 and not p['diagnostic']['intervention_used'] and not p['diagnostic']['log']
    assert y['raw']['branches']['P0']['version']=='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019' and y['raw']['branches']['P0']['method']=='PPCPP_INDEPENDENT'
    def trim(v,prefix):
        if isinstance(v,dict):return {k:trim(q,prefix+'.'+k) for k,q in v.items() if prefix+'.'+k not in EQUIVALENCE_EXCLUSIONS}
        if isinstance(v,list):return [trim(q,prefix+'[]') for q in v]
        return v
    assert trim(x,'result')==trim(y,'result'),'explicit-path-only OFF/untouched equivalence failed'
    return dict(passed=True,route_equal=True,full_non_time_P0_trace_equal=True,all_other_result_fields_equal_after_explicit_exclusions=True,exclusions=EQUIVALENCE_EXCLUSIONS)
