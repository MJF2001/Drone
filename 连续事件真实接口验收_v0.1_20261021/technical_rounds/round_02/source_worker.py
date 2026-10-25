"""Main-guarded one-entry original PPCPP/P2 worker; current input only."""
from util import *
import sys,time
from entry import invoke
def load_api(method):
    assert method in ('PPCPP','P2_MULTI') and 'runtime' not in sys.modules
    sys.path.insert(0,str(P));import runtime
    sys.path.insert(0,str(P));import candidate,p2_adapter,p2_search_audit
    sys.path.insert(0,str(H))
    assert Path(runtime.__file__).resolve()==P/'runtime.py' and Path(candidate.__file__).resolve()==P/'candidate.py' and Path(p2_adapter.__file__).resolve()==P/'p2_adapter.py'
    assert Path(runtime.native.__file__).resolve()==R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py' and not hasattr(runtime.native,'configure')
    return dict(runtime=runtime,candidate=candidate,p2=p2_adapter,p2_module=p2_search_audit)
def imported(api):
    rt=api['runtime'];return sorted({str(Path(m.__file__).resolve()) for m in list(sys.modules.values()) if getattr(m,'__file__',None) and Path(m.__file__).is_file()}|{str(Path(rt.native.__file__).resolve()),str(Path(rt.native.core.__file__).resolve()),str(Path(rt.validate.__code__.co_filename).resolve())})
def main():
    if len(sys.argv)==3 and sys.argv[1]=='inventory':
        api=load_api(sys.argv[2]);print(json.dumps(dict(paths=imported(api),native=str(api['runtime'].native.__file__),reward=str(api['runtime'].native.core.__file__)),ensure_ascii=False));return
    cfg=config();seal=check_seal();j=read(sys.argv[1]);assert j['seed']==cfg['seed'] and j['method'] in ('PPCPP','P2_MULTI')
    assert next(s for s in read(H/'call_slots.json') if s['id']==j['id'])==j['slot'];assert j['seal_sha256']==sha(H/'seal.json')
    inp=H/j['input'];out=Path(sys.argv[2]);assert inp.parent==H/'inputs' and out.parent==H/'outputs' and not out.exists();assert sha(inp)==j['input_sha256']
    api=load_api(j['method']);imports={p:sha(p) for p in imported(api)}
    for p,v in imports.items():assert seal['files'][p]==v,('import_drift',p)
    rt=api['runtime'];p2=api['p2'];owner=rt.native if j['method']=='PPCPP' else p2;attr='solve' if j['method']=='PPCPP' else 'p2_solve';original=getattr(owner,attr);calls=[];geometries=[];attempts=[]
    def counted(*args,**kw):
        assert not calls;calls.append(dict(method=j['method'],start=time.perf_counter(),remaining_budget=args[2] if j['method']=='PPCPP' else args[1]));print('CORE_START '+j['method'],flush=True)
        try:z=original(*args,**kw)
        except BaseException:calls[-1]['raised']=True;print('CORE_RAISED',flush=True);raise
        calls[-1]['end']=time.perf_counter();print('CORE_RETURN',flush=True);return z
    setattr(owner,attr,counted)
    original_geometry=rt.native.UnifiedGeometry if j['method']=='PPCPP' else api['p2_module'].UnifiedGeometry
    def geometry(*args,**kw):attempts.append(1);g=original_geometry(*args,**kw);geometries.append(g);return g
    if j['method']=='P2_MULTI':api['p2_module'].UnifiedGeometry=geometry
    reads=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            mode=args[1]
            if not isinstance(mode,str) or 'r' in mode or '+' in mode:
                p=Path(os.fsdecode(args[0])).resolve();reads.append(str(p));assert p==inp,('unapproved_warm_read',p)
    sys.addaudithook(audit);payload=inp.read_bytes();print('ENTRY_START '+j['id'],flush=True);begin=time.perf_counter()
    x=invoke(payload,j['method'],j['seed'],api,geometry);wall=time.perf_counter()-begin
    assert len(calls)<=1 and x['response']['entry_seconds']==x['entry_seconds'] and x['entry_budget']==20
    native=x['native_return']
    if native:
        assert native['budget']==x['inner_budget'] and native['entry_seconds']<=x['entry_seconds']
        if j['method']=='PPCPP':assert native['raw']['mode']=='PPCPP' and set(native['raw']['branches'])=={'P0'} and native['raw']['branches']['P0']['version']=='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'
        else:assert native['method']=='P2_MULTI'
    save(out,dict(job=j,entry=x,worker_wall_seconds=wall,input_sha256=j['input_sha256'],imports=imports,runtime_reads=reads,core_calls=calls,native_graph=dict(geometry_construction_attempts=len(attempts),reachability_BFS_started=len(attempts),distance_row_BFS_completed=sum(g.bfs_rows_built for g in geometries),Astar_completed=sum(g.searches for g in geometries))))
    print('ENTRY_RETURN '+j['id'],flush=True)
if __name__=='__main__':main()
