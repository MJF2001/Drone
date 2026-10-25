"""Guarded one-entry/one-diagnostic-core worker with current-input read whitelist."""
from common import *
import sys,os,time
import runtime,candidate
def imported():return sorted({str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}|{str(Path(runtime.native.__file__).resolve()),str(Path(runtime.native.core.__file__).resolve()),str(Path(runtime.validate.__code__.co_filename).resolve())})
def main():
    assert Path(runtime.__file__).resolve()==H/'runtime.py' and Path(candidate.__file__).resolve()==H/'candidate.py' and Path(runtime.native.__file__).resolve()==H/'native_diag.py'
    if sys.argv[1:] == ['inventory']:
        print(json.dumps(dict(paths=imported(),runtime=str(runtime.__file__),candidate=str(candidate.__file__),native=str(runtime.native.__file__),reward_tools=str(runtime.native.core.__file__)),ensure_ascii=False));return
    require('technical');require('action_stubs');s=preseal();j=read(sys.argv[1]);assert j['mode'] in ('OFF','ON');require('OFF') if j['mode']=='ON' else None;config=plan()
    assert sha(sys.argv[1])==s['files'][str(Path(sys.argv[1]).resolve())];inp=H/j['input'];assert sha(inp)==s['files'][str(inp)];out=Path(sys.argv[2]);assert not out.exists()
    imports={p:sha(p) for p in imported()}
    for p,h in imports.items():assert s['files'][p]==h,('import_drift',p)
    original=runtime.native.solve;calls=[];geometries=[];geometry_attempts=[]
    def counted(*args,**kwargs):
        calls.append(dict(kind='diagnostic_native',start=time.perf_counter(),source=str(runtime.native.__file__),remaining_budget=args[2]));print('CORE_START diagnostic_native',flush=True);assert len(calls)==1
        z=original(*args,**kwargs);calls[-1]['end']=time.perf_counter();return z
    original_geometry=runtime.native.UnifiedGeometry
    def geometry(*args,**kwargs):
        geometry_attempts.append(1);g=original_geometry(*args,**kwargs);geometries.append(g);return g
    runtime.native.solve=counted;reads=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            mode=args[1]
            if not isinstance(mode,str) or 'r' in mode or '+' in mode:
                p=Path(os.fsdecode(args[0])).resolve();reads.append(str(p));assert p==inp,('unapproved_planning_read',p)
    sys.addaudithook(audit);payload=inp.read_bytes();print('ENTRY_START '+j['id'],flush=True);begin=time.perf_counter()
    x=runtime.run_payload(payload,'PPCPP',20,j['seed'],diagnostic_mode=j['mode'],geometry=geometry);wall=time.perf_counter()-begin
    assert x['diagnostic_entry']==LABEL and x['diagnostic_mode']==j['mode'] and set(x['raw'].get('branches',{}))<={'P0'} and len(calls)<=1
    save(out,dict(job=j,result=x,caller_wall_seconds=wall,imports=imports,input_sha256=s['files'][str(inp)],runtime_reads=reads,actual_core_calls=calls,native_geometry_account=dict(construction_attempts=len(geometry_attempts),completed_instances=len(geometries),reachability_BFS_started=len(geometry_attempts),distance_row_BFS_completed=sum(g.bfs_rows_built for g in geometries),Astar_path_searches_completed=sum(g.searches for g in geometries)),diagnostic_label=LABEL))
    print(j['id'],x['raw']['status'],x['entry_seconds'],len(calls),flush=True)
if __name__=='__main__':main()
