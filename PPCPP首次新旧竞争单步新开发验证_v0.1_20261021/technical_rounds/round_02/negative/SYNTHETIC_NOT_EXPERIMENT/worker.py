"""One guarded task, one original or byte-frozen diagnostic core."""
from common import *
import sys,os,time
def dependencies(mode):
    if H.name=='SYNTHETIC_NOT_EXPERIMENT':
        rt=sys.modules['runtime'];ca=sys.modules['candidate'];rt.synthetic_requested_mode=mode;return rt,ca
    assert 'runtime' not in sys.modules and 'candidate' not in sys.modules
    folder=P if mode=='FROZEN' else H;sys.path.insert(0,str(folder));import runtime
    sys.path.insert(0,str(folder));import candidate
    assert Path(runtime.__file__).resolve()==folder/'runtime.py' and Path(candidate.__file__).resolve()==folder/'candidate.py'
    expected=R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py' if mode=='FROZEN' else H/'native_diag.py'
    assert Path(runtime.native.__file__).resolve()==expected
    sys.path.insert(0,str(H))
    return runtime,candidate
def imported(rt):return sorted({str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}|{str(Path(rt.native.__file__).resolve()),str(Path(rt.native.core.__file__).resolve()),str(Path(rt.validate.__code__.co_filename).resolve())})
def main():
    if len(sys.argv)==3 and sys.argv[1]=='inventory':
        rt,ca=dependencies(sys.argv[2]);print(json.dumps(dict(paths=imported(rt),runtime=str(rt.__file__),candidate=str(ca.__file__),native=str(rt.native.__file__),reward_tools=str(rt.native.core.__file__)),ensure_ascii=False));return
    require('technical');require('action_stubs');j=read(sys.argv[1]);assert j['mode'] in ('FROZEN','OFF','ON');cfg=plan()
    seal=check_seal(j['seal'][:-5]);require('prep') if j['phase']=='gate' else None;require('gate') if j['phase']=='formal' else None
    jobfile=Path(sys.argv[1]).resolve();inp=H/j['input'];out=Path(sys.argv[2]);assert not out.exists()
    assert sha(jobfile)==seal['files'][str(jobfile)] and sha(inp)==seal['files'][str(inp)]
    rt,ca=dependencies(j['mode']);imports={p:sha(p) for p in imported(rt)}
    for p,h in imports.items():assert seal['files'][p]==h,('import_drift',p)
    original=rt.native.solve;calls=[];geometries=[];attempts=[]
    def counted(*args,**kwargs):
        calls.append(dict(kind=j['mode'],start=time.perf_counter(),source=str(rt.native.__file__),remaining_budget=args[2]));print('CORE_START '+j['mode'],flush=True);assert len(calls)==1
        x=original(*args,**kwargs);calls[-1]['end']=time.perf_counter();return x
    original_geometry=rt.native.UnifiedGeometry
    def geometry(*args,**kwargs):attempts.append(1);g=original_geometry(*args,**kwargs);geometries.append(g);return g
    rt.native.solve=counted;reads=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            mode=args[1]
            if not isinstance(mode,str) or 'r' in mode or '+' in mode:
                p=Path(os.fsdecode(args[0])).resolve();reads.append(str(p));assert p==inp,('unapproved_planning_read',p)
    sys.addaudithook(audit);payload=inp.read_bytes();print('ENTRY_START '+j['id'],flush=True);begin=time.perf_counter()
    kw={} if j['mode']=='FROZEN' else dict(diagnostic_mode=j['mode'])
    x=rt.run_payload(payload,'PPCPP',20,j['seed'],geometry=geometry,**kw);wall=time.perf_counter()-begin
    assert set(x['raw'].get('branches',{}))<={'P0'} and len(calls)<=1
    if j['mode']!='FROZEN':assert x['diagnostic_entry']==LABEL and x['diagnostic_mode']==j['mode']
    save(out,dict(job=j,result=x,caller_wall_seconds=wall,imports=imports,input_sha256=seal['files'][str(inp)],runtime_reads=reads,actual_core_calls=calls,native_geometry_account=dict(construction_attempts=len(attempts),completed_instances=len(geometries),reachability_BFS_started=len(attempts),distance_row_BFS_completed=sum(g.bfs_rows_built for g in geometries),Astar_path_searches_completed=sum(g.searches for g in geometries))))
    print(j['id'],x['raw']['status'],x['entry_seconds'],len(calls),flush=True)
if __name__=='__main__':main()
