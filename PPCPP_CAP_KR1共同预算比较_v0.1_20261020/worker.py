"""Isolated warm-process worker with one COMMON serialized-entry clock."""
import json,sys,time,traceback
from pathlib import Path
from validation import validate
H=Path(__file__).resolve().parent;ROOT=H.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(H/'runtime'))
import candidate
sys.path.insert(0,str(ROOT/'基线复现准备_20261019/独立版_v0.2'))
import ppcpp
from model import Snapshot

def invoke(payload,method,budget,seed,*,clock=time.perf_counter,phase_hook=None):
    start=clock();raw=None;wire=None;called=False
    def phase(s):
        if phase_hook:phase_hook(s)
    phase('begin');c=json.loads(payload);validate(c);phase('decoded')
    if method=='PPCPP':
        s=Snapshot(c['name'],frozenset(map(tuple,c['free'])),frozenset(map(tuple,c['targets'])),frozenset(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),tuple(map(tuple,c['old_route'])),0,c['distance_budget'])
        initial=set(map(tuple,c['initial_targets']));predator=tuple(c['predator']);previous=tuple(c['previous']) if c['previous'] is not None else None
    elif method!='CAP_KR1':raise ValueError(method)
    left=budget-(clock()-start)
    if left>0:
        called=True
        if method=='PPCPP':raw=ppcpp.solve(s,initial,left,seed,predator,previous)
        else:raw=candidate.solve(c,budget=left)
        phase('solved');wire=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8');phase('serialized')
    elapsed=clock()-start
    complete=raw is not None and raw['status']==('core_complete' if method=='PPCPP' else 'complete')
    eligible=complete and elapsed<budget
    return dict(method=method,raw=raw,entry_seconds=elapsed,eligible=eligible,
        accepted_route=raw['route'] if eligible else [],payload_bytes=len(wire) if wire is not None else 0,
        solver_called=called,complete=complete,status='timely_complete' if eligible else 'late_complete' if complete else 'entry_deadline' if raw is None else raw['status'])

def main(job,dest):
    # File loading/bootstrapping are separately excluded on BOTH methods.
    payload=Path(job['input']).read_bytes();begin=time.perf_counter()
    r=invoke(payload,job['method'],job['budget'],job['seed'])
    r['independent_call_seconds']=time.perf_counter()-begin;r['job']=job
    if r['independent_call_seconds']>=job['budget']:
        r['eligible']=False;r['accepted_route']=[]
        if r['complete']:r['status']='late_complete'
    Path(dest).write_text(json.dumps(r,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
if __name__=='__main__':
    try:main(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')),sys.argv[2])
    except BaseException:
        Path(sys.argv[2]+'.error.txt').write_text(traceback.format_exc(),encoding='utf-8');raise
