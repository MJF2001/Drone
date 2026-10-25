"""Predeclared topology regressions, no result-driven search or ranking."""
import json,hashlib
from pathlib import Path
import micro_suite
from history_adapter import solve
ROOT=Path(__file__).resolve().parent
def cases():
    rows=[]
    def add(name,f,t,h=(),s=(0,0),b=(0,0),**kw):
        c=dict(name=name,free=sorted(f),targets=sorted(t),covered=sorted(h),published_targets=sorted(set(t)|set(h)),current=s,base=b,distance_budget=1000)
        c.update(kw);rows.append(c)
    line={(x,0) for x in range(7)}
    add('covered_bridge',line,line,line-{(0,0),(3,0)},(6,0))
    cross={(x,0) for x in range(-2,3)}|{(0,y) for y in range(-2,3)}
    add('multi_exit_cross',cross,{(-2,0),(2,0),(0,-2),(0,2)},{(0,0)})
    ring={(x,y) for x in range(3) for y in range(3) if x in (0,2) or y in (0,2)}
    add('cycle_sparse',ring,{(2,2),(0,2)},{(0,0),(1,0)},(1,0))
    add('cycle_single_remaining',ring,ring,ring-{(2,2)})
    square={(x,y) for x in range(5) for y in range(5)}
    add('interior_target_no_frontier_node',square,{(2,2)},s=(2,0),b=(2,0))
    add('link_from_top_into_left_lap',square,{(2,2),(3,1)},{(3,4)},(3,4),(3,4))
    add('two_interior_columns',square,{(1,2),(3,2)},{(0,0),(1,0),(3,0)})
    maze={(0,y) for y in range(4)}|{(x,3) for x in range(5)}|{(4,y) for y in range(4)}
    add('covered_non_target_long_connector',maze,{(4,0)},{(0,0),(0,1)},(0,1))
    add('all_covered_cycle_return',ring,ring,ring,(2,2))
    active={(4,0),(5,0),(6,0)}
    add('deferred_not_completed',active,active,s=(4,0),b=(6,0),published_targets=sorted(active|{(3,0)}),known_blocked=[(3,0)])
    return rows
def main():
    out=ROOT/'regression_evidence';out.mkdir(exist_ok=True)
    if (out/'results.json').exists():raise RuntimeError('Do not overwrite evidence')
    cs=cases();raw=json.dumps(cs,ensure_ascii=False,indent=2);(out/'inputs.json').write_text(raw,encoding='utf8')
    files={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'runtime').rglob('*.py')}
    files['regression_suite.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();files['regression_evidence/inputs.json']=hashlib.sha256(raw.encode()).hexdigest()
    (out/'pre_run_manifest.json').write_text(json.dumps(dict(files=files,budget_seconds=2,seeds=[7,19],max_iterations=400,scope='10 fixed topology fixtures, two seeds; no performance ranking'),indent=2),encoding='utf8')
    rs=[]
    for c in cs:
        for seed in (7,19):
            try:r=solve(c,2,seed)
            except Exception as e:r=dict(status='exception',exception=repr(e),route=[])
            rs.append(dict(name=c['name'],seed=seed,result=r));print(c['name'],seed,r['status'],len(r['route'])-1,flush=True)
    (out/'results.json').write_text(json.dumps(rs,ensure_ascii=False,indent=2),encoding='utf8')
if __name__=='__main__':main()
