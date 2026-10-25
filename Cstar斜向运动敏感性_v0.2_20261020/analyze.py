"""Motion sensitivity, NOT a replacement seven-algorithm ranking."""
import csv,json,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    assert not (HERE/'analysis.json').exists();protocol=read(HERE/'protocol.json');checks=read(HERE/'road_checks.json')
    batch=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020';oldp=read(batch/'protocol.json');old={(j['case_id'],j['seed'],j['method']):j for j in oldp['jobs']}
    cases={c['case_id']:c for c in oldp['cases']};rows=[]
    for r in checks:
        key=r['name'],r['seed'];cj=old[*key,'CSTAR'];pj=old[*key,'PPCPP']
        c=read(batch/'execution/results'/(cj['run_id']+'.json'));p=read(batch/'execution/results'/(pj['run_id']+'.json'));z=read(HERE/'evidence/results'/(r['run_id']+'.json'))['result']
        assert cj['input_sha256']==next(j['input_sha256'] for j in protocol['jobs'] if j['run_id']==r['run_id'])
        rows.append(dict(case=key[0],seed=key[1],scale=cases[key[0]]['scale'],state=cases[key[0]]['state'],status=r['status'],timely=r['timely'],distance8=r['distance'],moves8=r['moves'],diagonal_moves=r['diagonal_moves'],entry_seconds=r['entry_seconds'],distance4=len(c['route'])-1,PPCPP_distance4=len(p['route'])-1,pending=len(z['pending'])))
    paired=[r for r in rows if r['timely']];diff=[r['distance8']-r['distance4'] for r in paired]
    summary=dict(scheduled=40,completed=len(rows),timely=len(paired),shorter_than_4=sum(d<-1e-8 for d in diff),same_as_4=sum(abs(d)<=1e-8 for d in diff),longer_than_4=sum(d>1e-8 for d in diff),sum_distance8=sum(r['distance8'] for r in paired),sum_distance4_on_same_subset=sum(r['distance4'] for r in paired),mean_relative_8_to_4=statistics.mean(r['distance8']/r['distance4']-1 for r in paired),diagonal_moves=sum(r['diagonal_moves'] for r in rows),runs_with_diagonals=sum(r['diagonal_moves']>0 for r in rows),max_entry=max(r['entry_seconds'] for r in rows),mean_entry=statistics.mean(r['entry_seconds'] for r in rows),cross_model_PPCPP_mean_relative=statistics.mean(r['PPCPP_distance4']/r['distance8']-1 for r in paired),ranking=False,warning='mixed motion freedoms; sensitivity only, do not replace frozen seven-method results')
    (HERE/'analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (HERE/'motion_pairs.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
