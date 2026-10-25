"""Byte-preserving preparation and explicit minimal diagnostic source patch."""
from pathlib import Path
import json,hashlib,difflib,ast
H=Path(__file__).resolve().parent;R=H.parent;B=R/'PPCPP侧向拓宽开发诊断_v0.4_20261021';P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(b)
def main():
    assert not (H/'plan.json').exists()
    old=json.loads((B/'completion_manifest.json').read_text(encoding='utf8'))['files']
    for n,h in old.items():assert sha(B/n)==h,('source_drift',n)
    rows=[];diff=''
    for n in ('runtime.py','candidate.py','p2_adapter.py'):put(H/'frozen_source_bytes'/n,(P/n).read_bytes())
    for folder in ('inputs','jobs','outputs','logs','receipts','technical_rounds','figures'):(H/folder).mkdir()
    src_native=R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'
    for src,name in [(P/'runtime.py','runtime.py'),(P/'candidate.py','candidate.py'),(src_native,'native_diag.py'),(B/'reference_contract.py','reference_contract.py')]:
        raw=src.read_bytes();s=raw.decode('utf8').replace('\r\n','\n');n=s
        if name=='runtime.py':
            n=n.replace("R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'","Path(__file__).resolve().parent/'native_diag.py'")
            n=n.replace('*,hook=None,clock=',"*,diagnostic_mode='OFF',hook=None,clock=")
            n=n.replace("c=json.loads(payload);validate(c);s=snapshot(c);mark('entry')","c=json.loads(payload);validate(c);s=snapshot(c);native.configure(diagnostic_mode,set(map(tuple,c['published_targets']))-set(map(tuple,c['initial_targets'])));mark('entry')")
            n=n.replace("return dict(raw=raw,entry_seconds=elapsed,","return dict(diagnostic_entry='PPCPP_FIRST_NEW_STEP_DIAG_v0.1',diagnostic_mode=diagnostic_mode,raw=raw,entry_seconds=elapsed,")
        elif name=='native_diag.py':
            n=n.replace('ROOT=Path(__file__).resolve().parents[2]','ROOT=Path(__file__).resolve().parents[1]')
            n=n.replace("VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'","VERSION='PPCPP_FIRST_NEW_STEP_DIAG_v0.1'\nfrom intervention import first_new_step\nDIAG_MODE='OFF'\nNEW_TARGETS=frozenset()\ndef configure(mode,new_targets):\n    global DIAG_MODE,NEW_TARGETS\n    assert mode in ('OFF','ON')\n    DIAG_MODE=mode;NEW_TARGETS=frozenset(new_targets)")
            n=n.replace("reason=None;accepted=None","reason=None;accepted=None;intervention_used=False;intervention_log=[]")
            original="                    goal=core.choose_neighbor(options);event.update(kind='local',options=options,goal=goal);segment=(cur,goal)"
            replacement="""                    goal=core.choose_neighbor(options)
                    forced=first_new_step(DIAG_MODE=='ON',intervention_used,options,set(initial),NEW_TARGETS,goal)
                    if forced is not None:
                        before_pending=sorted(pending);original_selected=goal;goal=forced['forced_selected'];intervention_used=True
                        intervention_log.append(dict(index=len(route)-1,current=cur,previous=prev,pending_count=len(pending),old_pending_count=len(set(initial)&pending),new_pending_count=len(NEW_TARGETS&pending),original_selected=original_selected,forced_selected=goal,options=options,old_options=forced['old_options'],new_options=forced['new_options'],before_pending=before_pending,after_pending=sorted(pending-{goal}),after_current=goal,after_previous=cur,resource_before=s.distance_budget-(len(route)-1),resource_after=s.distance_budget-len(route),reason='first_local_both_classes_unique_new_one_step'))
                    event.update(kind='local',options=options,goal=goal);segment=(cur,goal)"""
            assert n.count(original)==1;n=n.replace(original,replacement)
            n=n.replace("method='PPCPP_INDEPENDENT'","method='PPCPP_FIRST_NEW_STEP_DIAG'")
            n=n.replace("overrun_gt_10ms=seconds>budget+.01)","overrun_gt_10ms=seconds>budget+.01,diagnostic=dict(mode=DIAG_MODE,intervention_used=intervention_used,trigger_count=len(intervention_log),log=intervention_log))")
        result=raw if n==s else n.encode('utf8');put(H/name,result)
        ast.parse(n);rows.append(dict(source=str(src),source_sha256=sha(src),target=name,target_sha256=sha(H/name),reason='unchanged binary' if result==raw else 'explicit diagnostic native hook / input-derived timed configuration only'))
        if n!=s:diff+=''.join(difflib.unified_diff(s.splitlines(True),n.splitlines(True),fromfile=str(src),tofile=name))
    states=json.loads((B/'states.json').read_text(encoding='utf8'));jobs=[]
    for s in states:
        path=H/'inputs'/f'input_{s["index"]:03d}.json';put(path,(B/s['input']).read_bytes());assert sha(path)==sha(B/s['input'])
    for mode in ('OFF','ON'):
        for s in states:
            for seed in (20261020,20261021,20261022):
                j=dict(id=f'{mode}_{s["index"]:03d}_{seed}',mode=mode,state=s['id'],input=f'inputs/input_{s["index"]:03d}.json',seed=seed,budget=20);jobs.append(j);save(H/'jobs'/f'{j["id"]}.json',j)
    save(H/'states_metadata.json',states);save(H/'order.json',jobs);save(H/'plan.json',dict(counts=dict(OFF=144,ON=144),entry_cap=288,entry_budget=20,watchdog=90,threads=1,expected_triggered_states=24,expected_protection_states=24))
    save(H/'copy_manifest.json',rows);put(H/'minimal.diff',diff.encode('utf8'));save(H/'old_v04_hashes.json',{str(B/n):h for n,h in old.items()})
    save(H/'stage_dependencies.json',dict(technical=[],preseal=['technical','action_stubs'],OFF=['technical','action_stubs','preseal'],ON=['technical','action_stubs','preseal','OFF']))
    print('Prepared48 exact byte inputs,288 fixed OFF/ON slots, copied candidate unchanged, minimal diagnostic source diff; real calls0')
if __name__=='__main__':main()
