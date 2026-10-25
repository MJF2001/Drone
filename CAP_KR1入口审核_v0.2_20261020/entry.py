"""Warm-process public entry budget: JSON decode/validate -> solve -> encode.
Eligibility is authoritative here, not the preserved raw solver status.
Soft admission deadline, NOT preemptive cancellation of Python/native calls.
Imports, independent audits, disk I/O and observer envelope are outside scope.
"""
import json,math,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'runtime'))
from candidate import solve

def validate(c):
    if not isinstance(c,dict):raise ValueError('object required')
    def point(p):
        if not isinstance(p,(list,tuple)) or len(p)!=2 or any(type(x) is not int for x in p):raise ValueError('integer grid point required')
    for field in ('free','targets','covered'):
        if not isinstance(c[field],list):raise ValueError(field)
        for p in c[field]:point(p)
    for field in ('published_targets','deferred_targets'):
        if field in c:
            if not isinstance(c[field],list):raise ValueError(field)
            for p in c[field]:point(p)
    point(c['current']);point(c['base'])
    if 'distance_budget' in c:
        v=c['distance_budget']
        if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('finite nonnegative distance budget')
    if 'cap_resume_target' in c and c['cap_resume_target'] is not None:
        r=c['cap_resume_target']
        if not isinstance(r,dict):raise ValueError('resume object')
        point(r['point'])
        if not isinstance(r['reference'],str) or not r['reference']:raise ValueError('resume reference')
    f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']))
    published=set(map(tuple,c.get('published_targets',list(t|h))))
    if tuple(c['current']) not in f or tuple(c['base']) not in f or not t<=f or not (t|h)<=published or (published&f)-h-t:raise ValueError('snapshot ledger')
    if 'deferred_targets' in c and set(map(tuple,c['deferred_targets']))!=published-f-h:raise ValueError('deferred ledger')
    if c.get('cap_resume_target') is not None and tuple(c['cap_resume_target']['point']) not in f:raise ValueError('resume not free')

def invoke(payload,budget=20,*,clock=time.perf_counter,phase_hook=None,solver_hook=None):
    start=clock();result=None;wire=None;solver_called=False;error=None
    def phase(s):
        if phase_hook:phase_hook(s)
    try:
        if type(budget) not in (int,float) or not math.isfinite(budget) or budget<=0:raise ValueError('positive finite time budget')
        phase('entry_begin')
        if not isinstance(payload,(str,bytes)):raise ValueError('JSON string/bytes required')
        c=json.loads(payload,parse_constant=lambda value:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
        validate(c);phase('after_parse')
        left=budget-(clock()-start)
        if left<=0:status='entry_deadline_before_solve'
        else:
            solver_called=True;result=solve(c,budget=left,clock=clock,hook=solver_hook)
            phase('after_solve')
            wire=json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode('utf-8')
            phase('after_serialize');status='returned'
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        status='solver_error' if solver_called else 'invalid_input';error=type(exc).__name__+': '+str(exc)
    elapsed=clock()-start
    timely=type(budget) in (int,float) and math.isfinite(budget) and budget>0 and elapsed<budget
    if status=='returned' and not timely:status='entry_late'
    eligible=status=='returned' and timely and result['status']=='complete'
    return dict(entry_status=status,entry_seconds=elapsed,budget=budget,eligible=eligible,
        accepted_route=result['route'] if eligible else [],solver_called=solver_called,
        result=result,payload_bytes=len(wire) if wire is not None else 0,error=error)
