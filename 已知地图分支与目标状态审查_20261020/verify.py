"""Read-only archive and check-count verification. No planner calls."""
import json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=read(HERE/'protocol.json');assert p['solver_calls']==0
    parent=read(ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020/protocol.json')
    dependency=ROOT/'TRACE_CAP适配复现_20261020/audit.py'
    assert sha(dependency)==parent['sources'][str(dependency.relative_to(ROOT))]
    for f,h in p['files'].items():assert sha(Path(f))==h,f
    d=read(HERE/'checks.json');assert d['calls']==0 and d['saved_outputs']==80 and d['plans']==120 and d['all_checks_pass']
    rows=d['records'];trace=[r for r in rows if r['method']=='TRACE'];cap=[r for r in rows if r['method']=='CAP'];assert len(trace)==len(cap)==60
    assert sum(r['nonadjacent'] for r in trace)==sum(r['nonadjacent'] for r in cap)==26
    assert sum(r['end_source']=='next_region_virtual_center' for r in trace)==20
    assert sum(r['end_source']=='free_end' for r in trace)==40
    assert sum(r['end_source']=='restart_direction_target' for r in cap)==34
    assert sum(r['end_source']=='restart_nearest_entry_target' for r in cap)==26
    assert sum(r['plan']>0 for r in cap)==20
    assert sum(r['tau_differs_from_fresh_global_greedy'] for r in cap)==6
    bad=[r for r in cap if r['required_components']>1];assert len(bad)==2 and all(r['run_id'].startswith('c10_') and r['plan']==1 for r in bad)
    for f,h in read(HERE/'figure_check.json')['files'].items():assert sha(ROOT/f)==h
    if (HERE/'manifest.json').exists():
        m=read(HERE/'manifest.json');assert set(m)=={str(f.relative_to(HERE)) for f in HERE.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(HERE/f)==h,f
    print(json.dumps(dict(verified=True,new_solves=0,saved_outputs=80,plans=120,additional_CAP_state_risks_preserved=True,sealed=(HERE/'manifest.json').exists()),ensure_ascii=False))
if __name__=='__main__':main()
