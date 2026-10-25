"""Preregistered deterministic development geometry; no solver imports."""
import json,hashlib,math
from pathlib import Path
from bridge_graph import reach,bridges,witness,structure
H=Path(__file__).resolve().parent
SEED=20261021
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def rect(x,y,w,h):return {(i,j) for i in range(x,x+w) for j in range(y,y+h)}
def case(name,f,t,current=(0,1),covered=(),previous=None,old=(),budget=100000):
    return dict(name=name,free=sorted(f),targets=sorted(t),covered=sorted(covered),published_targets=sorted(t),deferred_targets=[],current=current,base=(0,1),previous=previous,predator=(-1,0),initial_targets=sorted(t),old_route=list(old),distance_budget=budget)
def base(family,size):
    w=4 if size=='small' else 6;stride=w+3;n=12;rooms=[];gates=[]
    if family in ('I','D'):
        length=n*stride+2;f=rect(0,0,length,3)
        for i in range(n):
            x=2+i*stride;rooms.append(rect(x,4,w,w));gates.append(rect(x,3,w,1))
        if family=='D':f|=rect(0,-5,length,3)|rect(0,-5,3,8)|rect(length-3,-5,3,8)
    else:
        length=6*stride+2;f=rect(0,0,length+3,3)|rect(length,0,3,6*stride+12)
        for i in range(6):
            x=2+i*stride;rooms.append(rect(x,4,w,w));gates.append(rect(x,3,w,1))
        for i in range(6):
            y=w+7+i*stride;rooms.append(rect(length+4,y,w,w));gates.append(rect(length+3,y,1,w))
    for r,g in zip(rooms,gates):f|=r|g
    t=set().union(*rooms);assert reach(f,(0,1))==f and not bridges(f)
    return dict(id=f'{family}_{size}',family=family,size=size,width=w,obstacle_counts=dict(low=2*(w-1),high=3*(w-1)),rooms=[sorted(r) for r in rooms],gates=[sorted(g) for g in gates],input=case(f'{family}_{size}__prep',f,t))
def setup():
    for d in ('bases','prep_jobs','prep_outputs','prep_logs','histories','inputs','structure','witnesses','generation_failures','gates','jobs','outputs','logs'):(H/d).mkdir()
    bases=[]
    for fam in ('I','L','D'):
        for size in ('small','medium'):
            m=base(fam,size);save(H/'bases'/f'{m["id"]}.json',m);bases.append(m['id'])
    save(H/'base_order.json',bases)
    for i,id in enumerate(bases):save(H/'prep_jobs'/f'{id}.json',dict(id=id,method='PPCPP',seed=SEED,budget=20,input=f'bases/{id}.json',base_record=True,phase='prep',seal='prep_seal.json'))
    save(H/'config.json',dict(seed=SEED,base_ids=bases,progress=[30,70],counts='low/high = 2(w-1)/3(w-1)',layouts=['dispersed','single','multi'],formal_seeds=[20261020,20261021,20261022],max_calls=dict(prep=6,gates=12,formal=432),budget=20,watchdog=90))
def history(m,output,progress):
    route=list(map(tuple,output['result']['raw']['route']));t=set(map(tuple,m['input']['targets']));seen=set();threshold=math.ceil(len(t)*progress/100)
    for i,p in enumerate(route):
        seen|={p}&t
        if len(seen)>=threshold:break
    assert len(seen)>=threshold
    return dict(base_id=m['id'],progress=progress,threshold=threshold,index=i,prefix=route[:i+1],covered=sorted(seen),current=route[i],previous=route[i-1] if i else None,old_route=route[i:])
def layouts(m,h,count):
    f=set(map(tuple,m['input']['free']));t=set(map(tuple,m['input']['targets']));prefix=set(h['prefix']);pending=t-set(h['covered'])-{h['current']}
    gates=[set(map(tuple,g)) for g in m['gates']];rooms=[set(map(tuple,r)) for r in m['rooms']]
    eligible=[i for i,(g,r) in enumerate(zip(gates,rooms)) if len(g&prefix)<=1 and r&pending]
    info=dict(eligible_rooms=eligible,rooms=[dict(id=i,pending=len(r&pending),executed_gates=sorted(g&prefix)) for i,(g,r) in enumerate(zip(gates,rooms))])
    if len(eligible)<2:raise ValueError(('fewer_than_two_eligible_pending_rooms',info))
    allg=set().union(*gates);pool=f-t-prefix-allg-{(0,1),h['current']}
    pool=sorted(pool,key=lambda p:(hashlib.sha256(f'{SEED}:{m["id"]}:{h["progress"]}:{p}'.encode()).hexdigest(),p))
    result={}
    for label,nrooms in [('dispersed',0),('single',1),('multi',2)]:
        b=set();chosen=eligible[:nrooms]
        for i in chosen:
            g=gates[i];retained=min(g&prefix) if g&prefix else sorted(g)[len(g)//2];b|=g-{retained}
        baseline=bridges(f-b)
        for p in pool:
            if len(b)>=count:break
            # Padding is spatially dispersed, leaves graph connected and preserves bridges.
            if any(abs(p[0]-q[0])+abs(p[1]-q[1])<2 for q in b):continue
            trial=f-b-{p}
            if reach(trial,(0,1))==trial and bridges(trial)==baseline:b.add(p)
        if len(b)!=count:raise ValueError(('insufficient_padding',label,count,len(b),info))
        assert b<=f-t-prefix and reach(f-b,(0,1))==f-b
        result[label]=dict(obstacles=sorted(b),selected_rooms=chosen)
    return result,info
def instantiate():
    records=[];failed=[]
    for id in read(H/'base_order.json'):
        m=read(H/'bases'/f'{id}.json');out=read(H/'prep_outputs'/f'{id}.json')
        for progress in (30,70):
            h=history(m,out,progress);save(H/'histories'/f'{id}_p{progress}.json',h)
            # Normalize historical tuples for graph operations.
            h['prefix']=list(map(tuple,h['prefix']));h['covered']=list(map(tuple,h['covered']))
            for level,count in m['obstacle_counts'].items():
                key=f'{id}_p{progress}_{level}'
                try:
                    ls,info=layouts(m,h,count);cs=[];ws=[]
                    for label,l in ls.items():
                        b=set(map(tuple,l['obstacles']));f=set(map(tuple,m['input']['free']))-b
                        c=case(f'{key}_{label}',f,set(map(tuple,m['input']['targets'])),h['current'],h['covered'],h['previous'],h['old_route'])
                        w=witness(f,h['current'],(0,1));cs.append((label,c,l));ws.append(w)
                    common_budget=10*max(len(w)-1 for w in ws)
                    for (label,c,l),w in zip(cs,ws):
                        c['distance_budget']=common_budget;stats=structure(c)
                        if label=='single':assert stats['task_bridge_groups']>=1
                        if label=='multi':assert stats['task_bridge_groups']>=2
                        save(H/'inputs'/f'{c["name"]}.json',c);save(H/'witnesses'/f'{c["name"]}.json',w)
                        r=dict(id=c['name'],base_id=id,family=m['family'],size=m['size'],progress=progress,level=level,layout=label,obstacle_count=count,obstacle_ratio=count/len(m['input']['free']),generation_info=info,**l,structure=stats)
                        save(H/'structure'/f'{c["name"]}.json',r);records.append(r)
                    print('STRUCTURE',key,'PASS',flush=True)
                except Exception as e:
                    fail=dict(id=key,type=type(e).__name__,reason=str(e));failed.append(fail);save(H/'generation_failures'/f'{key}.json',fail);print('STRUCTURE',key,'FAIL',str(e),flush=True)
    save(H/'stage_A.json',dict(records=len(records),failed=failed,passed=not failed and len(records)==72))
if __name__=='__main__':
    import sys
    {'setup':setup,'instantiate':instantiate}[sys.argv[1]]()
