"""Small independent maps, using the exact saved pressure-layout function."""
import ast,random,math,collections,json
from joint_common import H,R,S,read,save,sha,normal,query
def layouts(w,h):
    text=(S/'stress.py').read_text(encoding='utf8');tree=ast.parse(text);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='layouts');code=ast.get_source_segment(text,node);scope={'random':random};exec(compile(code,str(S/'stress.py')+':layouts','exec'),scope)
    return scope['layouts'](w,h)
def snapshot(name,free,targets,covered=(),start=(0,0),base=(0,0),resource=1000):
    return dict(name=name,free=sorted(free),targets=sorted(targets),covered=sorted(covered),published_targets=sorted(set(targets)|set(covered)),deferred_targets=[],initial_targets=sorted(set(targets)|set(covered)),current=start,base=base,previous=None,predator=(-1,0),old_route=[],distance_budget=resource)
def graph(f,base):
    d={base:0};parent={base:None};queue=collections.deque([base])
    while queue:
        x,y=queue.popleft()
        for q in ((x-1,y),(x,y-1),(x+1,y),(x,y+1)):
            if q in f and q not in d:d[q]=d[x,y]+1;parent[q]=(x,y);queue.append(q)
    assert set(d)==f
    tin={};low={};bridges=[]
    def visit(p,previous=None):
        tin[p]=low[p]=len(tin)
        for q in sorted(f):
            if q==previous or abs(p[0]-q[0])+abs(p[1]-q[1])!=1:continue
            if q in tin:low[p]=min(low[p],tin[q])
            else:
                visit(q,p);low[p]=min(low[p],low[q])
                if low[q]>tin[p]:bridges.append(sorted((p,q)))
    visit(base)
    stats=dict(free=len(f),connected=True,bridges=sorted(bridges),bridge_count=len(bridges),degree_counts=dict(sorted(collections.Counter(sum(abs(p[0]-q[0])+abs(p[1]-q[1])==1 for q in f) for p in f).items())),base_distance_distribution=dict(sorted(collections.Counter(d.values()).items())),max_base_distance=max(d.values()))
    return stats,d,parent
def signature(f,pub,base):
    forms=[]
    for reflect in (1,-1):
        for rotation in range(4):
            def transform(p):
                x=(p[0]-base[0])*reflect;y=p[1]-base[1]
                for _ in range(rotation):x,y=-y,x
                return x,y
            forms.append(json.dumps([sorted(map(transform,f)),sorted(map(transform,pub))],separators=(',',':')))
    return min(forms)
def gate_fixtures():
    line=lambda n:{(i,0) for i in range(n)};fixtures=[]
    def add(id,f,s,b,t,expected,last=None,h=()):
        c=snapshot(id,f,set(t)|set(h),h,s,b);fixtures.append(dict(id=id,input=c,request=query(c,last),expected=expected))
    add('g0_empty',line(3),(2,0),(0,0),set(),2)
    add('g1_single',line(3),(0,0),(0,0),{(2,0)},4)
    add('g2_start_credit',line(2),(0,0),(0,0),{(0,0),(1,0)},2)
    add('g3_return_collect',line(4),(3,0),(0,0),{(1,0),(2,0)},3)
    add('g4_fixed_detour',{(0,0),(1,0),(0,1),(1,1)},(0,0),(0,0),{(1,0),(1,1)},4,(1,0))
    add('g5_historical_transit',line(4),(0,0),(0,0),{(3,0)},6,h={(1,0),(2,0)})
    add('g6_obstacle_detour',{(x,y) for x in range(3) for y in range(3)}-{(1,0),(1,1)},(0,0),(0,0),{(2,0)},12)
    add('g7_fixed_impossible',line(3),(0,0),(0,0),{(1,0),(2,0)},None,(1,0))
    return fixtures
def setup():
    for d in ('inputs','prep','prep_outputs','outputs','jobs','logs','exact','certificates','requests','figures'):(H/d).mkdir()
    order=[]
    for w,h in ((7,7),(9,7)):
        f={(x,y) for x in range(w) for y in range(h)};name=f'base_{w}_{h}';c=snapshot(name,f,f,resource=10*w*h);save(H/'prep'/f'{name}.json',c)
        order.append(dict(id=name,phase='prep',input=f'prep/{name}.json',seed=20261021,seal='prep_seal.json'))
    save(H/'prep_order.json',order);save(H/'gate_fixtures.json',gate_fixtures())
    save(H/'config.json',dict(sizes=[[7,7],[9,7]],progress=[80,90],layouts=['control','serpentine','rooms','maze'],seed=20261021,budget=20,watchdog=90,exact_seconds=60,exact_states=1000000,max_pending=14,max_calls=dict(PPCPP=18,exact=80),ordinary_graph_counts=dict(setup_bfs=0)))
    import sys,platform,os
    save(H/'environment.json',dict(python=sys.version,executable=sys.executable,executable_sha256=sha(sys.executable),platform=platform.platform(),thread_environment=dict(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1'),warm_entry='same pressure runtime.run_payload(PPCPP)',exact_limits='60s whole solve/proof encoding; 1000000 discovered; 90s outer watchdog'))
    source=(S/'stress.py').read_text(encoding='utf8');node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='layouts');segment=ast.get_source_segment(source,node)
    save(H/'layout_source.json',dict(path=str(S/'stress.py'),sha256=sha(S/'stress.py'),exact_function=segment))
def construct():
    out=[];inputs={};history={};seen={}
    for j in read(H/'prep_order.json'):
        c=read(H/j['input']);raw=read(H/'prep_outputs'/f'{j["id"]}.json')['result'];assert raw['eligible'] and raw['entry_seconds']<20
        route=list(map(tuple,raw['raw']['route']));full=set(map(tuple,c['free']));w=max(p[0] for p in full)+1;h=max(p[1] for p in full)+1
        for progress in (80,90):
            collected=set();threshold=math.ceil(w*h*progress/100)
            for i,p in enumerate(route):
                collected.add(p)
                if len(collected)>=threshold:break
            current=route[i];history[f'{w}x{h}_p{progress}']=dict(prep=j['id'],index=i,threshold=threshold,prefix=route[:i+1],covered=sorted(collected),current=current,previous=route[i-1] if i else None,old_route=route[i:])
            for kind,template in layouts(w,h).items():
                f=set(template);opened=[]
                if current not in f:
                    dest=min(f,key=lambda p:(abs(p[0]-current[0])+abs(p[1]-current[1]),p));p=current;opened.append(p);f.add(p)
                    for axis in (0,1):
                        while p[axis]!=dest[axis]:
                            point=list(p);point[axis]+=1 if dest[axis]>p[axis] else -1;p=tuple(point);f.add(p);opened.append(p)
                stats,_,_=graph(f,(0,0));name=f'{w}x{h}_{kind}_p{progress}';cc=dict(c,name=name,free=sorted(f),targets=sorted(f),covered=sorted(collected),deferred_targets=sorted(full-f-collected),current=current,previous=route[i-1] if i else None,old_route=route[i:])
                pending=f-collected-{current};key=json.dumps([cc[k] for k in ('free','targets','covered','current','base','previous','published_targets','deferred_targets','old_route')],sort_keys=True)
                alias=seen.get(key);seen.setdefault(key,name);inputs[name]=cc
                out.append(dict(id=name,w=w,h=h,kind=kind,progress=progress,base_geometry=f'{w}x{h}_{kind}',template_signature=signature(template,full,(0,0)),actual_signature=signature(f,full,(0,0)),history_key=f'{w}x{h}_p{progress}',pending=len(pending),deferred=len(full-f-collected),obstacles=len(full-f),obstacle_ratio=len(full-f)/len(full),opened=opened,structure=stats,alias_of=alias,valid=len(pending)<=14,empty=not pending))
    assert len(out)==16
    return normal(dict(states=out,inputs=inputs,histories=history,ordinary_graph_counts=dict(full_base_bfs=16)))
def build():
    data=construct()
    for name,c in data['inputs'].items():save(H/'inputs'/f'{name}.json',c)
    save(H/'states.json',data['states']);save(H/'histories.json',data['histories']);save(H/'generation_counts.json',data['ordinary_graph_counts'])
    formal=[];templates=[]
    for s in sorted(data['states'],key=lambda s:s['id']):
        if s['valid'] and not s['alias_of']:
            formal.append(dict(id=s['id'],phase='formal',input=f'inputs/{s["id"]}.json',seed=20261021,seal='event_seal.json'))
            if not s['empty']:
                for problem in ('FREE','FIXED'):
                    for engine in ('BFS','DIJKSTRA'):templates.append(dict(id=f'{s["id"]}__{problem}__{engine}',phase='exact',case=s['id'],problem=problem,engine=engine,seal='event_seal.json'))
    save(H/'formal_order.json',formal);save(H/'exact_templates.json',templates)
    save(H/'gate_order.json',[dict(id=f'{g["id"]}__{engine}',phase='gate',fixture=g['id'],engine=engine,seal='event_seal.json') for g in read(H/'gate_fixtures.json') for engine in ('BFS','DIJKSTRA')])
    print('GENERATED',len(data['states']),'states,',len(formal),'unique valid PPCPP entries,',len(templates),'formal exact engines;',[(s['id'],s['pending']) for s in data['states']],flush=True)
if __name__=='__main__':
    import sys
    {'setup':setup,'build':build}[sys.argv[1]]()
