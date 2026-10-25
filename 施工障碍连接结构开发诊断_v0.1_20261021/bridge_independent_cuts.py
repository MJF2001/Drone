"""Independent union-find cuts and first-visit-time accounting, offline only."""
from bridge_analysis import H,read
def verify():
    routes=edges=0
    for inp in sorted((H/'inputs').glob('*.json')):
        c=read(inp);f=set(map(tuple,c['free']));s=tuple(c['current']);b=tuple(c['base']);u=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{s}
        splits={}
        for row in read(H/'structure'/inp.name)['structure']['cuts']['edges']:
            edge=tuple(map(tuple,row['edge']));blocked=frozenset(edge);parent={p:p for p in f}
            def find(p):
                while parent[p]!=p:parent[p]=parent[parent[p]];p=parent[p]
                return p
            for x,y in f:
                for q in ((x+1,y),(x,y+1)):
                    p=(x,y)
                    if q in f and frozenset((p,q))!=blocked:parent[find(p)]=find(q)
            startroot=find(s);side={p for p in f if find(p)!=startroot};assert side and side!=f
            tasks=u&side;lb=1 if b in side else 2 if tasks else 0
            assert len(side)==row['other_size'] and sorted(tasks)==list(map(tuple,row['other_pending'])) and lb==row['lower_bound']
            splits[edge]=(side,tasks,lb);edges+=1
        for method in ('PPCPP','P2_MULTI'):
            for rep in range(3):
                jid=f'{inp.stem}__r{rep}__{method}';raw=read(H/'outputs'/f'{jid}.json')['result']['raw'];route=list(map(tuple,raw.get('route',[])))
                if not route:continue
                cuts=read(H/'route_cuts'/f'{jid}.json')
                for row in cuts['edges']:
                    side,tasks,lb=splits[tuple(map(tuple,row['edge']))]
                    inside=[p in side for p in route];changes=[i for i in range(1,len(route)) if inside[i]!=inside[i-1]]
                    enter=[i for i in changes if inside[i]];leave=[i for i in changes if not inside[i]]
                    first={p:route.index(p) for p in tasks};exits=[dict(step=i,remaining=sum(step>i for step in first.values())) for i in leave]
                    assert row['crossings']==len(changes) and row['excess']==len(changes)-lb
                    assert row['first_enter']==(enter[0] if enter else None)
                    assert row['final_exit']==(leave[-1] if leave else None)
                    assert row['last_completion']==(max(first.values()) if first else None)
                    assert row['exits']==exits
                    assert row['unfinished_exit_reentry']==sum(x['remaining']>0 and any(j>x['step'] for j in enter) for x in exits)
                routes+=1
    return dict(passed=True,state_bridge_edges=edges,complete_routes=routes,real_solver_calls=0,exact_search_calls=0)
if __name__=='__main__':
    import json
    print(json.dumps(verify(),ensure_ascii=False))
