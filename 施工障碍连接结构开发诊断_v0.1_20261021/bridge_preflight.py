"""Pure hand-route bridge tests and matching/history ledger review."""
import json
from pathlib import Path
from bridge_graph import cut_table,reach
from bridge_generate import base,history,layouts,case
from bridge_analysis import double,scalar
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def hand():
    f={(x,1) for x in range(3)};cases=[]
    # Each bridge has LB2,4 crossings and excess2, with unfinished exit/reentry.
    c=case('manual_reenter',f,{(2,1)},(0,1));route=[(0,1),(1,1),(0,1),(1,1),(2,1),(1,1),(0,1)]
    x=cut_table(c,route);assert [r['lower_bound'] for r in x['edges']]==[2,2]
    assert [r['excess'] for r in x['edges']]==[2,0] and x['edges'][0]['unfinished_exit_reentry']==1
    cases.append(dict(name=c['name'],input=c,route=route,stats=x))
    c=case('manual_cross',f,{(1,1)},(2,1));x=cut_table(c,[(2,1),(1,1),(0,1)])
    assert all(r['lower_bound']==1 and r['crossings']==1 for r in x['edges']);cases.append(dict(name=c['name'],stats=x))
    c=case('manual_empty',f,set(),(0,1));x=cut_table(c,[(0,1)])
    assert all(r['lower_bound']==0 and r['crossings']==0 for r in x['edges']);cases.append(dict(name=c['name'],stats=x))
    save(H/'manual_cut_tests.json',dict(passed=True,real_solver_calls=0,exact_search_calls=0,cases=cases))
def matching():
    assert read(H/'stage_A.json')['passed'];checks=[]
    for id in read(H/'base_order.json'):
        m=read(H/'bases'/f'{id}.json');assert m==json.loads(json.dumps(base(m['family'],m['size'])))
        out=read(H/'prep_outputs'/f'{id}.json');double(m['input'],out['result']['raw']['route']);scalar.audit(m['input'],out['result']['raw']['branches']['P0'])
        for progress in (30,70):
            h=history(m,out,progress);stored=read(H/'histories'/f'{id}_p{progress}.json');assert stored==json.loads(json.dumps(h))
            for level,count in m['obstacle_counts'].items():
                ls,info=layouts(m,h,count);group=[]
                for label,l in ls.items():
                    name=f'{id}_p{progress}_{level}_{label}';c=read(H/'inputs'/f'{name}.json');st=read(H/'structure'/f'{name}.json')
                    f=set(map(tuple,c['free']));before=set(map(tuple,m['input']['free']));b=set(map(tuple,l['obstacles']));prefix=set(map(tuple,h['prefix']))
                    assert before-f==b and len(b)==count and not b&prefix and not b&set(map(tuple,c['targets']))
                    assert l['selected_rooms']==st['selected_rooms'] and l['obstacles']==list(map(tuple,st['obstacles']))
                    assert f==reach(f,tuple(c['current'])) and c['deferred_targets']==[]
                    assert c['covered']==stored['covered'] and c['current']==stored['current'] and c['previous']==stored['previous'] and c['old_route']==stored['old_route']
                    w=read(H/'witnesses'/f'{name}.json');assert set(map(tuple,w))==f
                    assert w[0]==c['current'] and w[-1]==c['base'] and all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(w,w[1:]));assert len(w)-1<c['distance_budget']
                    group.append(c)
                for field in ('targets','covered','published_targets','initial_targets','deferred_targets','current','previous','base','old_route','predator','distance_budget'):
                    assert all(c[field]==group[0][field] for c in group)
                assert group[0]['distance_budget']==10*max(len(read(H/'witnesses'/f'{c["name"]}.json'))-1 for c in group)
                checks.append(dict(id=f'{id}_p{progress}_{level}',passed=True))
    return dict(passed=True,groups=checks,states=72,history_routes=6,history_prefixes=12,real_solver_calls=0)
if __name__=='__main__':
    hand();save(H/'matching_review.json',matching());print('PASS hand cut tests, six native histories, twelve prefixes, 24 matched triples /72 inputs; zero solver calls.')
