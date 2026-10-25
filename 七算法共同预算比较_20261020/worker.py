import sys,json,time,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;sys.path.insert(0,str(ROOT))
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def main(job,dest):
    c=read(job['input']);m=job['method'];pre=time.perf_counter()
    if m in ('P2_MULTI','TREE_MST','OARP_CORE2'):
        import portable_frozen as pf
        from model import Snapshot
        call=pf.solve
    elif m=='PPCPP':
        sys.path.insert(0,str(ROOT/'基线复现准备_20261019/独立版_v0.2'));import ppcpp
        from model import Snapshot
        call=ppcpp.solve
    elif m=='CSTAR':
        sys.path.insert(0,str(ROOT/'Cstar状态缓存验收_20261019/runtime'));from history_adapter import solve
        call=solve
    else:
        folder='CAP单源查询修正_v0.2_20261020' if m=='CAP' else 'TRACE_CAP适配复现_20261020'
        sys.path.insert(0,str(ROOT/folder/'runtime'));from planners import solve
        call=solve
    bootstrap=time.perf_counter()-pre;begin=time.perf_counter()
    request={k:c[k] for k in ('free','targets','covered','current','base','published_targets','deferred_targets','distance_budget')}
    if m in ('P2_MULTI','TREE_MST','OARP_CORE2','PPCPP'):
        s=Snapshot(c['name'],frozenset(map(tuple,c['free'])),frozenset(map(tuple,c['targets'])),frozenset(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),(),0,c['distance_budget'])
        initial=set(map(tuple,c['initial_targets']))
        if m=='PPCPP':r=call(s,initial,job['budget'],job['seed'],tuple(c['predator']),tuple(c['previous']) if c['previous'] is not None else None)
        else:r=call(s,initial,m,job['budget'],job['seed'],pf.PROFILE)
    elif m=='CSTAR':r=call(request,job['budget'],job['seed'],max_iterations=20000)
    else:r=call(request,m,job['budget'],job['seed'])
    entry=time.perf_counter()-begin
    result=dict(job=job,bootstrap_seconds=bootstrap,entry_seconds=entry,reported_seconds=r['seconds'],status=r['status'],route=r['route'],raw=r)
    Path(dest).write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':
    try:main(read(sys.argv[1]),sys.argv[2])
    except BaseException:
        Path(sys.argv[2]+'.error.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
