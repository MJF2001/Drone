"""Fixed six bases and, only after real history, fixed48 event inputs."""
from common import *
def make_input(name,F,T,H0,current,previous,old,budget,initial):
    return dict(name=name,free=sorted(F),targets=sorted(T),covered=sorted(H0),published_targets=sorted(T),deferred_targets=[],initial_targets=sorted(initial),current=current,previous=previous,base=[1,1],predator=[-1,0],old_route=old,distance_budget=budget)
def setup():
    for folder in ('inputs','jobs','outputs','logs','receipts','history','witnesses','figures'):(H/folder).mkdir()
    maps=[];prep=[]
    for i,(L,w) in enumerate((L,w) for L in (18,30,42) for w in (3,5)):
        gid=f'g{i:02d}';T0=rect(4,4,L,w);F=rect(0,0,L+8,w+8);c=make_input('dev_initial_'+gid,F,T0,set(),[1,1],None,[],1000000,T0);inp=f'inputs/prep_{gid}.json';save(H/inp,c)
        meta=dict(id=gid,L=L,w=w,development=True,input=inp);maps.append(meta);j=dict(id='prep_'+gid,phase='prep',case=gid,input=inp,method='PPCPP',seed=20261021,budget=20,seal='seal1.json');save(H/'jobs'/f'{j["id"]}.json',j);prep.append(j)
    save(H/'maps.json',maps);save(H/'prep_order.json',prep)
def witness(F,current,base):
    # External feasibility walk only: full-domain DFS plus legal return, never a solver input.
    seen={current};route=[current];stack=[(current,iter(sorted(adj(current))))]
    while stack:
        p,it=stack[-1]
        try:q=next(it)
        except StopIteration:
            stack.pop()
            if stack:route.append(stack[-1][0])
            continue
        if q in F and q not in seen:seen.add(q);route.append(q);stack.append((q,iter(sorted(adj(q)))))
    assert seen==F
    p=current
    for axis in (0,1):
        while p[axis]!=base[axis]:q=list(p);q[axis]+=1 if base[axis]>p[axis] else -1;p=tuple(q);route.append(p)
    return route
def build():
    require('prep');groups=[];states=[];missing=[];BFS=0
    for m in read(H/'maps.json'):
        L,w=m['L'],m['w'];T0=rect(4,4,L,w);F=rect(0,0,L+8,w+8);original=read(H/'outputs'/f'prep_{m["id"]}.json');path=list(map(tuple,original['result']['raw']['route']));c0=read(H/m['input']);dual(c0,path);B={(x,4) for x in range(4,4+L)}
        for count in (L//2,2*L//3):
            seen=set();cut=None
            for i,p in enumerate(path):
                if p in B:seen.add(p)
                if len(seen)>=count:cut=i;break
            assert cut is not None and cut>0;hist=history(path,T0,cut);cur=path[cut];prev=path[cut-1];gid=f'{m["id"]}_b{count:03d}';ell=L//3;candidates=[]
            for aa in range(4,4+L-ell+1):
                C={(x,4) for x in range(aa,aa+ell)};k=len(C&hist);candidates.append(dict(a=aa,k=k,ell=ell))
            eligible={z:[x for x in candidates if (x['k']==ell if z=='H_SIDE' else 0<x['k']<ell if z=='MIXED_SIDE' else x['k']==0)] for z in CONDS[1:]};selection={}
            for cond,choices in eligible.items():
                if not choices:missing.append(dict(group=gid,condition=cond));continue
                selection[cond]=min(choices,key=lambda x:(abs(2*x['k']-ell),x['a']) if cond=='MIXED_SIDE' else (x['a'],))
            gp=dict(id=gid,geometry=m['id'],L=L,w=w,boundary_count=count,ell=ell,prep_id='prep_'+m['id'],history_cut=cut,current=cur,previous=prev,H=sorted(hist),boundary_covered=len(hist&B),actual_history_fraction=len(hist)/len(T0),executed_steps=cut,old_remaining=len(T0-hist),budget_after_prefix=1000000-cut,candidates=candidates,selection=selection)
            save(H/'history'/f'{gid}.json',dict(**gp,prefix=path[:cut+1],old_suffix=path[cut:]));groups.append(gp)
            if any(cond not in selection for cond in CONDS[1:]):continue
            dc=bfs(F,cur);db=bfs(F,(1,1));BFS+=2;walk=witness(F,cur,(1,1));assert len(walk)-1<=1000000-cut;save(H/'witnesses'/f'{gid}.json',dict(group=gid,route=walk,only_for_external_feasibility=True,planner_input=False,steps=len(walk)-1))
            for cond in CONDS:
                record=selection.get(cond);A=set() if record is None else rect(record['a'],2,ell,2);assert not A&T0 and A<=F
                sid=f'{gid}_{cond}';inp=f'inputs/{sid}.json';c=make_input(f'dev_e{len(states):03d}',F,T0|A,hist,cur,prev,path[cut:],1000000-cut,T0);save(H/inp,c);dual(c,walk)
                distance=None if not A else dict(A_to_current_min=min(dc[p] for p in A),A_to_base_min=min(db[p] for p in A),A_current_distance_range=[min(dc[p] for p in A),max(dc[p] for p in A)],A_base_distance_range=[min(db[p] for p in A),max(db[p] for p in A)])
                for p in A:assert dc[p]==abs(p[0]-cur[0])+abs(p[1]-cur[1]) and db[p]==abs(p[0]-1)+abs(p[1]-1)
                states.append(dict(id=sid,index=len(states),group=gid,geometry=m['id'],L=L,w=w,boundary_count=count,condition=cond,input=inp,A=sorted(A),A_count=len(A),T0_count=len(T0),H_count=len(hist),old_remaining=len(T0-hist),history_fraction=len(hist)/len(T0),history_cut=cut,current=cur,previous=prev,k=record['k'] if record else None,a=record['a'] if record else None,distance=distance,development=True,retroactive_A_credit=0))
    save(H/'groups.json',groups);save(H/'states.json',states);save(H/'generation_ledger.json',dict(ordinary_BFS=BFS,external_feasibility_walks=len(list((H/'witnesses').glob('*.json'))),missing=missing));csvsave(H/'全部候选位置与已检接触数.csv',[dict(group=g['id'],**x) for g in groups for x in g['candidates']]);csvsave(H/'48输入位置距离与历史账.csv',states)
    if missing:
        save(H/'STOP.json',dict(stage='generation',reason='missing_fixed_label_candidate',missing=missing,real_entries_so_far=6,no_rule_changes=True));raise RuntimeError('missing H/M/U candidate: fixed design stopped')
    assert len(groups)==12 and len(states)==48
    gates=[s for s in states if (s['L']==18 and s['w']==3 and s['boundary_count']==9) or (s['L']==42 and s['w']==5 and s['boundary_count']==28 and s['condition'] in ('H_SIDE','U_SIDE'))];gate=[];formal=[]
    for s in gates:
        for method in METHODS:gate.append(dict(id=f'gate_{s["id"]}_{method}',phase='gate',case=s['id'],input=s['input'],method=method,seed=20261021,budget=20,seal='seal2.json'))
    for s in states:
        for rep,seed in enumerate(SEEDS):
            mm=METHODS if (s['index']+rep)%2==0 else METHODS[::-1]
            for method in mm:formal.append(dict(id=f'formal_{s["id"]}_{seed}_{method}',phase='formal',case=s['id'],input=s['input'],method=method,seed=seed,budget=20,seal='seal2.json'))
    assert len(gate)==12 and len(formal)==288
    for j in gate+formal:save(H/'jobs'/f'{j["id"]}.json',j)
    save(H/'gate_order.json',gate);save(H/'order.json',formal);receipt('generated',[H/'states.json',H/'groups.json',H/'generation_ledger.json',H/'gate_order.json',H/'order.json',*sorted((H/'history').glob('*.json')),*sorted((H/'inputs').glob('*.json'))]);print('PASS fixed48 states generated from12 true prefixes; all H/M/U candidates exist; no event calls yet',flush=True)
if __name__=='__main__':
    import sys
    setup() if sys.argv[1]=='setup' else build()
