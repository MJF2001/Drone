"""Read-only policy-sequence/geometric-saving decomposition, no solves."""
import json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    out=HERE/'decomposition.json';assert not out.exists()
    old=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020';rows=[]
    for j in read(HERE/'protocol.json')['jobs']:
        if j['kind']!='road':continue
        z=read(HERE/'evidence/results'/(j['run_id']+'.json'))['result']
        name='c'+j['name'][-2:]+'_s'+str(j['seed'])+'_CSTAR';b=read(old/'execution/results'/(name+'.json'))['raw']
        rcg=lambda r:[(e['mode'],e['rcg_route']) for e in r['task_events']]
        choices=lambda r:[(it.get('goal'),it['why'],it.get('holes'),it.get('tsp',{}).get('order') if it.get('tsp') else None) for it in r['iterations']]
        diag=sum(abs(a[0]-v[0])==abs(a[1]-v[1])==1 for a,v in zip(z['route'],z['route'][1:]))
        saving=(len(b['route'])-1)-z['route_distance'];simple=diag*(2-math.sqrt(2))
        rows.append(dict(case=j['name'],seed=j['seed'],RCG_routes_equal=rcg(z)==rcg(b),decisions_and_TSP_orders_equal=choices(z)==choices(b),diagonals=diag,saving=saving,pure_two_cardinals_to_one_diagonal_saving=simple,simple_model_agrees=abs(saving-simple)<1e-8))
    x=dict(solver_calls=0,rows=rows,RCG_equal=sum(r['RCG_routes_equal'] for r in rows),decisions_equal=sum(r['decisions_and_TSP_orders_equal'] for r in rows),geometric_saving_model_matches=sum(r['simple_model_agrees'] for r in rows),note='Finite batch only; compares plans not every transient covered set. Return trajectories may differ. This does not prove global equivalence of changed motion models.')
    out.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8');print({k:v for k,v in x.items() if k!='rows'})
if __name__=='__main__':main()
