import json,sys,time,traceback
from pathlib import Path
from validation import validate
from rollout import solve,native
from first_rollout import solve as first
from model import Snapshot

def snapshot(c):return Snapshot(c['name'],frozenset(map(tuple,c['free'])),frozenset(map(tuple,c['targets'])),frozenset(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])

def main(j,dest):
    payload=Path(j['input']).read_bytes();begin=time.perf_counter();c=json.loads(payload);validate(c);s=snapshot(c);initial=set(map(tuple,c['initial_targets']));pred=tuple(c['predator']);prev=tuple(c['previous']) if c['previous'] else None
    left=j['budget']-(time.perf_counter()-begin)
    if j['method']=='PPCPP':r=native.solve(s,initial,left,j['seed'],pred,prev)
    elif j['method']=='FIRST':r=first(s,initial,left,j['seed'],pred,prev,mode='three')
    else:
        assert j['method']=='SECOND';r=solve(s,initial,left,j['seed'],pred,prev,mode='three')
    wire=json.dumps(r,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8');elapsed=time.perf_counter()-begin
    x=dict(job=j,raw=r,entry_seconds=elapsed,eligible=r['status']=='core_complete' and elapsed<j['budget'],payload_bytes=len(wire));x['independent_seconds']=time.perf_counter()-begin
    if x['independent_seconds']>=j['budget']:x['eligible']=False
    Path(dest).write_text(json.dumps(x,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':
    try:main(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')),sys.argv[2])
    except BaseException:
        Path(sys.argv[2]+'.error.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
