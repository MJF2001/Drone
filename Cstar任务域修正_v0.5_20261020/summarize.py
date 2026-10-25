"""Development correction diagnostics only; zero new solves."""
import csv,json
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    old={(r['case_id'],int(r['seed'])):r for r in csv.DictReader((HERE.parent/'七算法共同预算比较_v0.2_20261020/all_runs.csv').open(encoding='utf-8-sig')) if r['method']=='CSTAR'}
    rows=[]
    for r in read(HERE/'road_checks.json'):
        b=old[r['name'],r['seed']]
        z=read(HERE/'evidence/results'/(r['run_id']+'.json'))['result']
        rows.append(dict(case=r['name'],seed=r['seed'],name=b['name'],scale=b['scale'],state=b['state'],old_status=b['status'],old_timely=b['timely']=='True',old_steps=int(b['steps']) if b['steps'] else None,new_status=r['status'],new_timely=r['timely'],new_steps=r['steps'],entry_seconds=r['entry_seconds'],prefix_steps=len(z['diagnostic_route'])-1,pending=len(z['pending']),error=z['graph_error'],hole_tours=r['hole_tours']))
    with (HERE/'road_before_after.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    paired=[r for r in rows if r['old_timely'] and r['new_timely']]
    summary=dict(calls=40,scales={s:dict(count=sum(r['scale']==s for r in rows),complete=sum(r['new_timely'] for r in rows if r['scale']==s)) for s in sorted(set(r['scale'] for r in rows))},complete_pairs=len(paired),shorter=sum(r['new_steps']<r['old_steps'] for r in paired),equal=sum(r['new_steps']==r['old_steps'] for r in paired),longer=sum(r['new_steps']>r['old_steps'] for r in paired),old_sum=sum(r['old_steps'] for r in paired),new_sum=sum(r['new_steps'] for r in paired),mean_relative=sum(r['new_steps']/r['old_steps']-1 for r in paired)/len(paired),fail_errors=dict(Counter(r['error'] for r in rows if not r['new_timely'])),note='paired subset only; not a full-batch improvement or algorithm ranking')
    (HERE/'correction_analysis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
