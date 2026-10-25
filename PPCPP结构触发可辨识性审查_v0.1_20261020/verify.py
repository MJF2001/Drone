"""Independent DSU check of U-components; explicit non-outcome selection replay."""
import json,statistics
from pathlib import Path
from audit import H,UP,read,sha,protect,TOTAL_KEYS,POLICIES
from crosscheck import calculate

def dsu(cells):
    cells=set(cells);p={q:q for q in cells}
    def root(q):
        while p[q]!=q:p[q]=p[p[q]];q=p[q]
        return q
    for x,y in cells:
        for z in ((x+1,y),(x,y+1)):
            if z in cells:p[root(z)]=root((x,y))
    groups={}
    for q in cells:groups.setdefault(root(q),set()).add(q)
    return sorted(groups.values(),key=min)
def main():
    p=protect();a=read(H/'analysis.json');assert len(a['states'])==47 and a['feature_windows']==94 and a['actual_trigger_windows']==69
    assert a['new_solver_calls']==a['planner_changes']==0
    fixtures=[(set(),0),({(0,0)},1),({(0,0),(1,1)},2),({(0,0),(1,0),(1,1)},1),({(0,0),(2,0),(4,0)},3)]
    from rule import components
    for cells,n in fixtures:
        label,sizes,anchors=components(cells);groups=dsu(cells);assert len(groups)==len(sizes)==n and sizes==list(map(len,groups)) and anchors==list(map(min,groups))
    branch_count=0
    for x in a['states']:
        c=read(x['input']);raws={m:read(path)['raw'] for m,path in x['sources'].items()}
        for m,r in raws.items():
            assert calculate(c,r['route'])==x['metrics'][m]
            for b in r.get('branches',[]):calculate(c,b['route']);branch_count+=1
        for m,k in (('FIRST',1),('SECOND',2)):
            r=raws[m];f=x['features'][m];s=r['branch_state'];assert f['recovery_index']==k and f['triggered']==(s is not None)
            if s is None:assert not f['eligible'];continue
            pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-set(map(tuple,s['path']))
            assert pending==set(map(tuple,s['pending']));groups=dsu(pending);lookup={q:i for i,g in enumerate(groups) for q in g}
            ids=[lookup[tuple(b['forced_goal'])] for b in r['branches']]
            assert f['component_count']==len(groups) and f['component_sizes']==list(map(len,groups)) and f['component_anchors']==[list(min(g)) for g in groups]
            assert f['candidate_goals']==[b['forced_goal'] for b in r['branches']] and f['candidate_component_ids']==ids
            assert f['candidate_component_count']==len(set(ids)) and f['eligible']==(len(set(ids))>=2)
            assert f['pending_count']==len(pending) and f['prefix_steps']==len(s['path'])-1
        e1=x['features']['FIRST']['eligible'];e2=x['features']['SECOND']['eligible']
        assert x['selections']['FIRST_FILTER']==('FIRST' if e1 else 'PPCPP')
        assert x['selections']['TWO_WINDOW_REPLAY']==('FIRST' if e1 else 'SECOND' if e2 else 'PPCPP')
        # Both candidate baseline prefixes originate in the same native route, so a
        # rejected first window can reach the stored second window without clairvoyance.
        for m in ('FIRST','SECOND'):
            assert raws[m]['branches'][0]['route']==raws['PPCPP']['route'] and raws[m]['branches'][0]['trace']==raws['PPCPP']['trace']
    assert branch_count==a['complete_candidate_branches_checked']==193
    for batch,s in a['summary'].items():
        xs=[x for x in a['states'] if x['batch']==batch];assert s['n']==len(xs)
        for m,f in s['features'].items():
            trigger=[x for x in xs if x['features'][m]['triggered']];gain=[x for x in trigger if x['metrics'][m]['length']<x['metrics']['PPCPP']['length']]
            assert f['triggered']==len(trigger) and f['eligible']==sum(x['features'][m]['eligible'] for x in trigger)
            assert f['known_improved']==len(gain) and f['missed_improved']==[x['case_id'] for x in gain if not x['features'][m]['eligible']]
            assert f['skipped_no_improvement']==[x['case_id'] for x in trigger if not x['features'][m]['eligible'] and x['metrics'][m]['length']==x['metrics']['PPCPP']['length']]
            assert f['retained_improved']==f['known_improved']-len(f['missed_improved']) and f['conservative_gate_pass']==(not f['missed_improved'] and bool(f['skipped_no_improvement']))
        for policy,v in s['replay'].items():
            chosen=[x['selections'][policy] for x in xs];ms=[x['metrics'][m] for x,m in zip(xs,chosen)]
            for key in TOTAL_KEYS:assert v['totals'][key]==sum(m[key] for m in ms)
            for ref,q in v['pairs'].items():
                ds=[m['length']-x['metrics'][ref]['length'] for x,m in zip(xs,ms)]
                assert q['shorter']==sum(d<0 for d in ds) and q['equal']==sum(d==0 for d in ds) and q['longer']==sum(d>0 for d in ds) and q['difference']==sum(ds)
                assert q['mean_relative']==statistics.mean(d/x['metrics'][ref]['length'] for d,x in zip(ds,xs))
            assert v['source_counts']=={m:chosen.count(m) for m in ('PPCPP','FIRST','SECOND')} and not v['timing_measured']
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,states=47,feature_windows=94,actual_triggers=69,branches_checked=193,component_fixtures=5,new_solver_calls=0,planner_changes=0,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
