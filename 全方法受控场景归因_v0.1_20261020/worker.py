import sys,json,time,traceback
from pathlib import Path
from validation import validate
H=Path(__file__).resolve().parent;R=H.parent
def main(j,dest):
    m=j['method'];sys.path.insert(0,str(R))
    if m=='PPCPP':
        sys.path.insert(0,str(R/'基线复现准备_20261019/独立版_v0.2'));import ppcpp
        from model import Snapshot
        call=ppcpp.solve;success='core_complete'
    elif m=='CSTAR':
        sys.path.insert(0,str(R/'Cstar连接器等价提速_v0.7_20261020/runtime'));from history_adapter import solve
        call=solve;success='task_complete'
    elif m=='CAP_KR1':
        sys.path.insert(0,str(R/'PPCPP_CAP_KR1共同预算比较_v0.1_20261020/runtime'));from candidate import solve
        call=solve;success='complete'
    else:
        folder='TRACE_CAP适配复现_20261020' if m=='TRACE' else 'CAP单源查询修正_v0.2_20261020'
        sys.path.insert(0,str(R/folder/'runtime'));from planners import solve
        call=solve;success='complete'
    payload=Path(j['input']).read_bytes();begin=time.perf_counter();c=json.loads(payload);validate(c)
    if m=='PPCPP':
        s=Snapshot(c['name'],frozenset(map(tuple,c['free'])),frozenset(map(tuple,c['targets'])),frozenset(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
        initial=set(map(tuple,c['initial_targets']));pred=tuple(c['predator']);prev=tuple(c['previous'])
    left=j['budget']-(time.perf_counter()-begin);raw=None
    if left>0:
        if m=='PPCPP':raw=call(s,initial,left,j['seed'],pred,prev)
        elif m=='CSTAR':raw=call(c,left,j['seed'],max_iterations=20000)
        elif m=='CAP_KR1':raw=call(c,left)
        else:raw=call(c,'TRACE' if m=='TRACE' else 'CAP',left,j['seed'])
        wire=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
    entry=time.perf_counter()-begin
    if j.get('inject_late'):entry=j['budget']+1
    complete=raw is not None and raw['status']==success;eligible=complete and entry<j['budget']
    output=dict(job=j,raw=raw,entry_seconds=entry,complete=complete,eligible=eligible,accepted_route=raw['route'] if eligible else [],solver_budget=left,payload_bytes=len(wire) if raw else 0)
    output['independent_call_seconds']=time.perf_counter()-begin
    if output['independent_call_seconds']>=j['budget']:output.update(eligible=False,accepted_route=[])
    Path(dest).write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':
    try:main(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')),sys.argv[2])
    except BaseException:
        Path(sys.argv[2]+'.error.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
