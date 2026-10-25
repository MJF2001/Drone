"""Read-only weighted motion re-audit; no solver calls."""
import json,hashlib,statistics,csv,math
from pathlib import Path
from audit_diagonal import audit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=read(HERE/'protocol.json');rows=read(HERE/'gate_checks.json')+read(HERE/'road_checks.json');assert len(rows)==len(p['jobs'])==102
    parent=read(ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020/protocol.json')
    for name in ('audit_special.py','audit_micro.py'):
        dependency=ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3'/name
        assert sha(dependency)==parent['sources'][str(dependency.relative_to(ROOT))]
    for f,h in p['sources'].items():assert sha(HERE/f)==h
    for f in (HERE/'runtime').rglob('*.py'):
        rel=f.relative_to(HERE/'runtime');assert sha(f)==sha(ROOT/'Cstar斜向运动敏感性_v0.1_20261020/runtime'/rel)
        if rel.name not in ('history_adapter.py','diagonal_geometry.py'):assert sha(f)==sha(ROOT/'Cstar连接器等价提速_v0.7_20261020/runtime'/rel)
    by={r['run_id']:r for r in rows}
    for j in p['jobs']:
        assert sha(Path(j['input']))==j['input_sha256'];rp=HERE/'evidence/results'/(j['run_id']+'.json');z=read(rp);r=by[j['run_id']]
        assert z['job']==j and sha(rp)==r['result_sha256'];check=audit(read(Path(j['input'])),z['result'],j['budget'])
        for k,v in check.items():assert r[k]==v
        assert r['timely']==(r['accepted'] and z['entry_seconds']<=j['budget']+.010)
    c=read(ROOT/'Cstar任务域修正_v0.5_20261020/inputs/boundary_known.json');dead=read(HERE/'deadline/checks.json');assert len(dead)==78
    for d in dead:
        r=read(HERE/'deadline'/(d['name']+'.json'));audit(c,r,2);assert r['status']==d['status']
        assert r['status']=='task_complete' if d['name'].endswith('__before') else not r['route'] and r['status'] in ('deadline','wall_clock_cap')
    audit(c,read(HERE/'deadline/discovery.json'),2)
    summary=read(HERE/'road_summary.json');rr=read(HERE/'road_checks.json');assert len(rr)==40 and summary['timely']==sum(r['timely'] for r in rr)
    analysis=read(HERE/'analysis.json');assert analysis['timely']==summary['timely']
    pairs=list(csv.DictReader((HERE/'motion_pairs.csv').open(encoding='utf-8-sig')));assert len(pairs)==40
    ri={(r['name'],r['seed']):r for r in rr}
    for row in pairs:
        r=ri[row['case'],int(row['seed'])];assert float(row['distance8'])==r['distance'] and int(row['diagonal_moves'])==r['diagonal_moves']
    assert abs(sum(float(x['distance8']) for x in pairs)-analysis['sum_distance8'])<1e-8
    assert abs(statistics.mean(float(x['distance8'])/int(x['distance4'])-1 for x in pairs)-analysis['mean_relative_8_to_4'])<1e-12
    assert abs(statistics.mean(int(x['PPCPP_distance4'])/float(x['distance8'])-1 for x in pairs)-analysis['cross_model_PPCPP_mean_relative'])<1e-12
    dec=read(HERE/'decomposition.json');assert dec['solver_calls']==0 and len(dec['rows'])==40
    assert dec['RCG_equal']==dec['decisions_equal']==dec['geometric_saving_model_matches']==40
    assert abs((analysis['sum_distance4_on_same_subset']-analysis['sum_distance8'])-analysis['diagonal_moves']*(2-math.sqrt(2)))<1e-8
    if (HERE/'manifest.json').exists():
        m=read(HERE/'manifest.json');assert set(m)=={str(f.relative_to(HERE)) for f in HERE.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(HERE/f)==h
    print(json.dumps(dict(pass_all=True,new_solves=0,micro_outputs=62,road_outputs=40,deadline_outputs=78,motion_sensitivity_only=True,road=summary,sealed=(HERE/'manifest.json').exists()),ensure_ascii=False))
if __name__=='__main__':main()
