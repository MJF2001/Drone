"""One warm entry/core only; hash-bound stages; runtime reads input/actions only."""
import os,sys,json,time
from pathlib import Path
from stage_control import *
def imported():return sorted({str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()})
inventory=sys.argv[1]=='inventory';mode=sys.argv[2] if inventory else read(sys.argv[1])['mode']
sys.path.insert(0,str(P if mode=='FROZEN' else H))
import runtime,candidate
assert Path(runtime.__file__).resolve()==(P if mode=='FROZEN' else H)/'runtime.py';assert Path(candidate.__file__).resolve()==(P if mode=='FROZEN' else H)/'candidate.py'
assert Path(runtime.native.__file__).resolve()==(R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py' if mode=='FROZEN' else H/'native_probe.py')
if inventory:
    print(json.dumps(dict(paths=imported(),runtime=str(runtime.__file__),candidate=str(candidate.__file__),native=str(runtime.native.__file__),core=str(runtime.native.core.__file__)),ensure_ascii=False));sys.exit(0)
j=read(sys.argv[1]);seal=require_preseal();require('stubs');require('gate') if j['phase']=='formal' else None
sources={}
for path in imported():assert path in seal['files'] and sha(path)==seal['files'][path],path;sources[path]=sha(path)
inp=H/j['input'];actions=H/'actions.json';assert sha(inp)==seal['files'][str(inp)] and sha(actions)==seal['files'][str(actions)]
core_calls=[];original_native=runtime.native.solve
def counted(*args,**kwargs):
    core_calls.append(dict(index=len(core_calls)+1,begin=time.perf_counter(),native=str(runtime.native.__file__),native_budget=args[2]))
    if len(core_calls)!=1:raise RuntimeError('one_core_limit')
    result=original_native(*args,**kwargs);core_calls[-1]['end']=time.perf_counter();return result
runtime.native.solve=counted;reads=[]
def audit(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        access=args[1]
        if not isinstance(access,str) or 'r' in access or '+' in access:
            path=Path(os.fsdecode(args[0])).resolve();reads.append(str(path));assert path in (inp,actions),('unapproved_runtime_read',path)
sys.addaudithook(audit);payload=inp.read_bytes()
def hook(stage):
    if stage=='entry':
        config=read(actions);assert set(config)==set(CASES);runtime.native.PROBE_ACTION=config[j['case']]
x=runtime.run_payload(payload,'PPCPP',20,j['seed'],hook=hook if mode=='ON' else None)
assert len(core_calls)==1 and set(x['raw']['branches'])=={'P0'}
save(Path(sys.argv[2]),dict(job=j,result=x,imports=sources,input_sha256=seal['files'][str(inp)],runtime_reads=reads,actual_core_calls=core_calls,diagnostic_label='PPCPP_HISTORY_STEP_PROBE_v0.2' if mode=='ON' else 'OFF_equivalence_only' if mode=='OFF' else 'PPCPP_FROZEN'))
print(j['id'],x['raw']['status'],x['entry_seconds'],flush=True)
