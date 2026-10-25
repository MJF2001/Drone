"""Bounded acceptance fixtures; deliberately NOT a performance comparison."""
import sys,json,hashlib,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'runtime'))
from history_adapter import solve

def build_cases():
    cases=[]
    def add(name,free,targets=None,covered=(),current=(0,0),base=(0,0),**extra):
        targets=set(free) if targets is None else set(targets);covered=set(covered)
        c=dict(name=name,free=sorted(free),targets=sorted(targets),covered=sorted(covered),
               published_targets=sorted(targets|covered),current=current,base=base,distance_budget=1000)
        c.update(extra);cases.append(c)
    line={(x,0) for x in range(5)}
    add('line_no_history',line)
    add('line_history',line,covered={(0,0),(1,0),(2,0)},current=(2,0))
    add('all_covered_return',line,covered=line,current=(4,0))
    add('covered_lap_endpoints',{(0,y) for y in range(5)},covered={(0,0),(0,1),(0,3),(0,4)})
    add('sparse_targets_transit',line,{(4,0)},current=(1,0))
    add('current_auto_capture',line,{(2,0)},current=(2,0))
    corner=line|{(4,y) for y in range(1,4)}
    add('corner_expansion',corner,covered=line,current=(4,0))
    blocked={(2,0)};detour=line|{(x,1) for x in range(1,4)}
    add('new_obstacle_deferred',detour-blocked,targets=line-blocked,covered={(0,0),(1,0)},current=(1,0),published_targets=sorted(line))
    square={(x,y) for x in range(3) for y in range(3)}
    add('square_open_boundary',square)
    add('square_history_interior',square,covered={(0,0),(1,1),(2,2)})
    ring={(x,y) for x in range(-1,4) for y in range(-1,4)}-square
    add('square_explicit_known_boundary',square,known_blocked=sorted(ring))
    u={(0,y) for y in range(4)}|{(3,y) for y in range(4)}|{(x,0) for x in range(4)}
    add('u_shape',u)
    add('non_target_base_pending',line,{(4,0)},covered={(1,0)},current=(3,0))
    add('resource_too_short',line,distance_budget=1)
    add('disconnected_target',{(0,0),(2,0)})
    add('disconnected_return',{(0,0),(2,0)},targets={(0,0)},base=(2,0))
    return cases

def main():
    out=ROOT/'micro_evidence';out.mkdir(exist_ok=True)
    if (out/'results.json').exists():raise RuntimeError('Do not overwrite evidence')
    cases=build_cases();(out/'inputs.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf8')
    frozen={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'runtime').rglob('*.py'))}
    frozen['micro_suite.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'pre_run_manifest.json').write_text(json.dumps(dict(budget_seconds=2,seed=7,max_iterations=400,replicates=2,scope='16 tiny acceptance fixtures, no holdout or developer ranking',files=frozen),indent=2),encoding='utf8')
    results=[]
    for c in cases:
        for replay in range(2):
            try:r=solve(c,2,7)
            except Exception as exc:r=dict(status='exception',exception=repr(exc),route=[])
            results.append(dict(name=c['name'],replay=replay,result=r))
            print(c['name'],replay,r['status'],len(r['route'])-1,flush=True)
    (out/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
