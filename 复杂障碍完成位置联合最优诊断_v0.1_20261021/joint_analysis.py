"""Saved-proof analysis only: no planner or coverage search invocation."""
import statistics,collections
from joint_common import H,R,read,save,sha,normal,account,csvsave
from joint_generate import graph
from joint_proof import audit
CATEGORIES=('G0','O_only','E_only','O_and_E','unresolved_or_unavailable','empty_not_applicable')
def geometric_groups(states):
    names=sorted({s['base_geometry'] for s in states});parent={n:n for n in names}
    def find(n):
        while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
        return n
    for i,a in enumerate(names):
        aa=[s for s in states if s['base_geometry']==a]
        for b in names[i+1:]:
            bb=[s for s in states if s['base_geometry']==b]
            if any(x['template_signature']==y['template_signature'] or x['actual_signature']==y['actual_signature'] for x in aa for y in bb):parent[find(b)]=find(a)
    return {n:find(n) for n in names}
def summarize(rows):
    solved=[r for r in rows if r['category'] in ('G0','O_only','E_only','O_and_E')]
    return dict(n=len(rows),solved=len(solved),categories={k:sum(r['category']==k for r in rows) for k in CATEGORIES},sums={k:sum(r[k] for r in solved) for k in ('Lp','Lstar','Lfixed','G','O','E')},positive_E=sum(r['E'] is not None and r['E']>0 for r in rows),E_at_least_half_G=sum(r['G'] is not None and r['G']>0 and 2*r['E']>=r['G'] for r in rows))
def compute(check_proofs=True):
    states=read(H/'states.json');groups=geometric_groups(states);rows=[];proofs=[];all_solutions=[];failed=[];queries=0
    for state in sorted(states,key=lambda s:s['id']):
        name=state['id'];c=read(H/'inputs'/f'{name}.json');f=set(map(tuple,c['free']));stats,d,_=graph(f,tuple(c['base']));assert normal(stats)==state['structure']
        row=dict(id=name,kind=state['kind'],size=f'{state["w"]}x{state["h"]}',progress=state['progress'],geometry_group=groups[state['base_geometry']],pending=state['pending'],deferred=state['deferred'],alias_of=state['alias_of'],Lp=None,Lstar=None,Lfixed=None,G=None,O=None,E=None,category='unresolved_or_unavailable',reference=None,FREE=None,FIXED=None,reason=None)
        source=state['alias_of'] or name;refpath=H/'outputs'/f'{source}.json'
        if not state['valid'] or not refpath.exists():row['reason']='input_invalid_or_reference_missing';rows.append(row);continue
        ref=read(refpath)['result'];path=ref['raw'].get('route',[])
        if not path:row['reason']='reference_no_route';rows.append(row);continue
        acc=account(c,path);acc['d_base']=d[tuple(path[acc['C']])];acc['seconds']=ref['entry_seconds'];row.update(Lp=acc['metrics']['length'],reference=acc)
        if ref['entry_seconds']>=20:row['reason']='late_reference';rows.append(row);continue
        if state['empty']:
            assert row['Lp']>=d[tuple(c['current'])];row.update(category='empty_not_applicable',shortest_return=d[tuple(c['current'])]);rows.append(row);continue
        solved={};certs={};complete=True
        for problem in ('FREE','FIXED'):
            for engine in ('BFS','DIJKSTRA'):
                id=f'{source}__{problem}__{engine}';p=H/'exact'/f'{id}.json'
                if not p.exists():complete=False;failed.append(dict(id=id,reason='not_run'));continue
                x=read(p);r=x['result'];request=x['request'];assert x.get('request_sha256')==sha(H/x['job']['request'])
                expectedlast=normal(acc['ep']) if problem=='FIXED' else None;assert request['last']==expectedlast
                assert set(map(tuple,request['free']))==f and set(map(tuple,request['tasks']))==set(map(tuple,c['targets']))-set(map(tuple,c['covered']))
                if check_proofs and x['certificate']:proofs.append(dict(id=id,**audit(request,r,H/x['certificate'])))
                if r['status']!='optimal':complete=False;failed.append(dict(id=id,reason=r['reason']));continue
                assert x['query_seconds']<60 and r['discovered']<=1000000
                a=account(c,r['route'],expectedlast);a.update(d_base=d[tuple(r['route'][a['C']])],seconds=x['query_seconds'],engine=engine,problem=problem,query=id)
                all_solutions.append(dict(case=name,**a));solved[problem,engine]=r['length'];certs[problem,engine]=a
            if (problem,'BFS') in solved and (problem,'DIJKSTRA') in solved:assert solved[problem,'BFS']==solved[problem,'DIJKSTRA']
        if complete:
            best=solved['FREE','BFS'];fixed=solved['FIXED','BFS'];G=row['Lp']-best;O=row['Lp']-fixed;E=fixed-best
            assert min(G,O,E)>=0 and G==O+E
            cat='G0' if G==0 else 'O_only' if E==0 else 'E_only' if O==0 else 'O_and_E'
            row.update(Lstar=best,Lfixed=fixed,G=G,O=O,E=E,category=cat,FREE=certs['FREE','BFS'],FIXED=certs['FIXED','BFS'])
        else:row['reason']='one_or_more_exact_queries_unresolved'
        rows.append(row)
    event=[r for r in rows if r['kind']!='control'];positive=[r for r in event if r['E'] is not None and r['E']>0];families=sorted({r['kind'] for r in positive});geoms=sorted({r['geometry_group'] for r in positive})
    strata={field:{str(v):summarize([r for r in rows if r[field]==v]) for v in sorted({r[field] for r in rows})} for field in ('kind','size','progress')}
    selected=[];missing=[]
    for category in CATEGORIES:
        eligible=[r for r in rows if r['category']==category]
        if eligible:selected.append(dict(category=category,id=min(r['id'] for r in eligible)))
        else:missing.append(category)
    return normal(dict(rows=rows,summary=dict(all=summarize(rows),events=summarize(event),controls=summarize([r for r in rows if r['kind']=='control'])),strata=strata,signal=dict(passed=len(families)>=2 and len(geoms)>=3,families=families,non_equivalent_geometry_groups=geoms,positive_states=[r['id'] for r in positive]),geometry_audit=dict(base_groups=groups,template_signature_groups={sig:sorted({s['base_geometry'] for s in states if s['template_signature']==sig}) for sig in sorted({s['template_signature'] for s in states})},actual_signature_groups={sig:[s['id'] for s in states if s['actual_signature']==sig] for sig in sorted({s['actual_signature'] for s in states})}),selected=selected,missing_categories=missing,all_exact_solution_metrics=all_solutions,certificate_checks=proofs,failures=failed,ordinary_graph_counts=dict(analysis_base_bfs=len(states)),exact_execution_summary=dict(n=len(list((H/'exact').glob('*.json'))),max_query_seconds=max(read(p)['query_seconds'] for p in (H/'exact').glob('*.json')),max_discovered=max(read(p)['result']['discovered'] or 0 for p in (H/'exact').glob('*.json')))))
def analyze():
    a=compute();save(H/'analysis.json',a);save(H/'failures.json',a['failures']);csvsave(H/'16状态最优分解.csv',a['rows']);csvsave(H/'全部精确路线双指标.csv',a['all_exact_solution_metrics']);csvsave(H/'分层.csv',[dict(dimension=field,value=value,**x) for field,vals in a['strata'].items() for value,x in vals.items()]);print(__import__('json').dumps({k:a[k] for k in ('summary','signal','selected','missing_categories','exact_execution_summary')},ensure_ascii=False),flush=True)
if __name__=='__main__':analyze()
