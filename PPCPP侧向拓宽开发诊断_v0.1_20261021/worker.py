"""Frozen warm entry with external call accounting; no new policy."""
import os,sys,time
from common import *
sys.path.insert(0,str(P));import runtime,candidate,p2_adapter
def imports():return sorted({str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()})
assert Path(runtime.__file__).resolve()==P/'runtime.py' and Path(candidate.__file__).resolve()==P/'candidate.py' and Path(p2_adapter.__file__).resolve()==P/'p2_adapter.py'
assert Path(runtime.native.__file__).resolve()==R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py'
if sys.argv[1]=='inventory':
    print(json.dumps(dict(paths=imports(),runtime=str(runtime.__file__),candidate=str(candidate.__file__),p2_adapter=str(p2_adapter.__file__),native=str(runtime.native.__file__),reward_tools=str(runtime.native.core.__file__),P2_core=str(Path(p2_adapter.p2_solve.__code__.co_filename).resolve())),ensure_ascii=False));sys.exit(0)
j=read(sys.argv[1]);seal=check_seal(j['seal']);require(j['seal'].replace('.json',''));require('stat_stubs');require('prep') if j['phase']!='prep' else None;require('gate') if j['phase']=='formal' else None
assert sha(sys.argv[1])==seal['files'][str(Path(sys.argv[1]).resolve())]
hs={}
for p in imports():assert p in seal['files'] and sha(p)==seal['files'][p],('unsealed_or_changed_import',p);hs[p]=sha(p)
inp=H/j['input'];assert sha(inp)==seal['files'][str(inp)];counts=[]
original_pp=runtime.native.solve;original_p2=p2_adapter.p2_solve
def pp(*args,**kwargs):
    counts.append(dict(kind='PPCPP_native',start=time.perf_counter()));print('CORE_START PPCPP_native',flush=True);assert len(counts)==1;z=original_pp(*args,**kwargs);counts[-1]['end']=time.perf_counter();return z
def p2(*args,**kwargs):
    counts.append(dict(kind='P2_multi_core',start=time.perf_counter()));print('CORE_START P2_multi_core',flush=True);assert len(counts)==1;z=original_p2(*args,**kwargs);counts[-1]['end']=time.perf_counter();return z
runtime.native.solve=pp;p2_adapter.p2_solve=p2;reads=[]
def audit(event,args):
    if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
        mode=args[1]
        if not isinstance(mode,str) or 'r' in mode or '+' in mode:
            p=Path(os.fsdecode(args[0])).resolve();reads.append(str(p));assert p==inp,('unapproved_planning_read',p)
sys.addaudithook(audit);payload=inp.read_bytes();print('ENTRY_START '+j['id'],flush=True);begin=time.perf_counter()
x=runtime.run_payload(payload,'PPCPP',20,j['seed']) if j['method']=='PPCPP' else p2_adapter.run_payload(payload,20,j['seed']);wall=time.perf_counter()-begin
if j['method']=='PPCPP':assert x['raw'].get('mode','PPCPP')=='PPCPP' and set(x['raw'].get('branches',{}))<={'P0'}
assert len(counts)<=1
with Path(sys.argv[2]).open('x',encoding='utf8') as f:json.dump(dict(job=j,result=x,caller_wall_seconds=wall,entry_overrun_seconds=max(0,x['entry_seconds']-20),imports=hs,input_sha256=seal['files'][str(inp)],runtime_reads=reads,actual_core_calls=counts),f,ensure_ascii=False,allow_nan=False,separators=(',',':'))
print(j['id'],x['raw'].get('status'),x['entry_seconds'],len(counts),flush=True)
