"""Prepare byte-derived independent copies and exactly 24 fixed slots; no solves."""
from probe_common import *
import difflib
native=R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'
original=native.read_text(encoding='utf8');copy=original.replace('ROOT=Path(__file__).resolve().parents[2]','ROOT=Path(__file__).resolve().parents[1]')
copy=copy.replace("VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'","VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'\nfrom probe_hook import force_history_step\nPROBE_ACTION=None\nPROBE_STAGE_HOOK=None")
copy=copy.replace('reason=None;accepted=None','reason=None;accepted=None;intervention=None')
needle='            while pending:';assert copy.count(needle)==1
copy=copy.replace(needle,"            if PROBE_ACTION is not None:\n                intervention=dict(enabled=True,trigger_count=0)\n                force_history_step(s,previous,pending,route,trace,PROBE_ACTION,tick,deadline,intervention,PROBE_STAGE_HOOK)\n"+needle)
copy=copy.replace('overrun_gt_10ms=seconds>budget+.01)','overrun_gt_10ms=seconds>budget+.01,**({\'intervention\':intervention} if PROBE_ACTION is not None else {}))')
with (H/'native_probe.py').open('x',encoding='utf8') as f:f.write(copy)
rt=(P/'runtime.py').read_text(encoding='utf8');rtcopy=rt.replace("R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'","R/'PPCPP一次历史邻格干预诊断_v0.1_20261021/native_probe.py'");assert rt!=rtcopy
for name,txt in [('runtime.py',rtcopy),('candidate.py',(P/'candidate.py').read_text(encoding='utf8'))]:
    with (H/name).open('x',encoding='utf8') as f:f.write(txt)
diff=''
for src,dst in [(native,H/'native_probe.py'),(P/'runtime.py',H/'runtime.py'),(P/'candidate.py',H/'candidate.py')]:diff+=''.join(difflib.unified_diff(src.read_text(encoding='utf8').splitlines(True),dst.read_text(encoding='utf8').splitlines(True),fromfile=str(src),tofile=str(dst)))
with (H/'minimal.diff').open('x',encoding='utf8') as f:f.write(diff)
for d in ('inputs','jobs','outputs','logs'):(H/d).mkdir()
for case in CASES:
    with (H/'inputs'/f'{case}.json').open('xb') as f:f.write((S/'inputs'/f'{case}.json').read_bytes())
save(H/'actions.json',{case:dict(current=[5,2],previous=[4,2],next=[5,1],source='post_hoc_saved_P2_next_step; diagnosis only; no P2 read at runtime',max_trigger=1) for case in CASES})
jobs=[]
for phase in ('gate','formal'):
    for case in CASES:
        for i,seed in enumerate(SEEDS):
            methods=['FROZEN','OFF'] if phase=='gate' else ['FROZEN','ON'] if i in (0,2) else ['ON','FROZEN']
            for mode in methods:
                j=dict(id=f'{phase}__{case}__{seed}__{mode}',phase=phase,case=case,seed=seed,mode=mode,input=f'inputs/{case}.json',budget=20,watchdog=90,core_calls=1)
                save(H/'jobs'/f'{j["id"]}.json',j);jobs.append(j)
save(H/'fixed_order.json',jobs);save(H/'equivalence_exclusions.json',EXCLUSIONS)
print('Prepared 2 exact-byte inputs, 2 actions, minimal diff, 24 slots; planner calls=0')
