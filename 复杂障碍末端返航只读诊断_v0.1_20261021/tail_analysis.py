"""Read-only original-route accounting. Imports no planner modules."""
import json,csv,hashlib,statistics,collections,heapq,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;S=R/'复杂障碍压力开发测试_v0.1_20261021'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def normal(x):return json.loads(json.dumps(x,ensure_ascii=False))
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def csvsave(p,rr):
    if not rr:return
    keys=list(dict.fromkeys(k for r in rr for k in r))
    with Path(p).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v for k,v in r.items()} for r in rr])
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
MD=R/'评价指标完整补算与数据审计_v0.1_20261020'
metric=module('tail_metric_a',MD/'metrics.py').metrics
cross=module('tail_metric_b',MD/'crosscheck.py').calculate
def bfs(f,base):
    d={base:0};parents={base:None};q=collections.deque([base])
    while q:
        x,y=q.popleft()
        for p in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
            if p in f and p not in d:d[p]=d[x,y]+1;parents[p]=(x,y);q.append(p)
    assert set(d)==f
    return d,parents
def independent_distance(f,start,goal):
    # Heap-based Dijkstra, different frontier and adjacency implementation.
    todo=[(0,start)];best={start:0};settled=set()
    while todo:
        cost,p=heapq.heappop(todo)
        if p in settled:continue
        settled.add(p)
        if p==goal:return cost
        for axis,inc in ((1,1),(0,-1),(1,-1),(0,1)):
            q=list(p);q[axis]+=inc;q=tuple(q)
            if q in f and cost+1<best.get(q,float('inf')):best[q]=cost+1;heapq.heappush(todo,(cost+1,q))
    raise AssertionError('unreachable endpoint')
KEYS=('dL','dC','dR','ddF','dX','dFresh','dHistorical','dRepeated','dNonTarget')
def signs(x):return '+' if x>0 else '-' if x<0 else '0'
def flags(v):
    a,c,r=v['dL'],v['dC'],v['dR']
    return dict(return_major=a>0 and r>0 and 2*r>=a,return_over_total=a>0 and r>a,pre_major=a>0 and c>0 and 2*c>=a,phase_sign=signs(c)+signs(r),return_share=r/a if a>0 else None)
def identities(v):
    assert abs(v['dL']-v['dC']-v['dR'])<1e-9
    assert abs(v['dR']-v['ddF']-v['dX'])<1e-9
    assert abs(v['dL']-sum(v[k] for k in ('dFresh','dHistorical','dRepeated','dNonTarget')))<1e-9
def summarize(pp,states):
    ss=[s for s in states if s['n']];positive=[p for p in pp if p['dL']>0]
    return dict(pairs=len(pp),states=len(ss),full_three_seed_states=sum(s['n']==3 for s in ss),geometries=len({s['geometry_id'] for s in ss}),positive_pairs=len(positive),equal_pairs=sum(p['dL']==0 for p in pp),reverse_pairs=sum(p['dL']<0 for p in pp),return_major=sum(p['return_major'] for p in pp),return_over_total=sum(p['return_over_total'] for p in pp),pre_major=sum(p['pre_major'] for p in pp),phase_sign_counts={a+b:sum(p['phase_sign']==a+b for p in pp) for a in ('+','-','0') for b in ('+','-','0')},signed_pair_sums={k:sum(p[k] for p in pp) for k in KEYS},state_distribution={k:dict(median=statistics.median(s['mean'][k] for s in ss),min=min(s['mean'][k] for s in ss),max=max(s['mean'][k] for s in ss),equal_state_mean=statistics.mean(s['mean'][k] for s in ss)) for k in KEYS} if ss else {},geometry_equal_mean={k:statistics.mean(statistics.mean(s['mean'][k] for s in ss if s['geometry_id']==g) for g in sorted({s['geometry_id'] for s in ss})) for k in KEYS} if ss else {})
def make_view(pairs,metadata,mode):
    pp=[p for p in pairs if p['legal'] and (mode=='legal' or p['timely'])];ss=[]
    for name,m in sorted(metadata.items()):
        group=sorted([p for p in pp if p['case']==name],key=lambda p:p['rep']);means={k:statistics.mean(p[k] for p in group) for k in KEYS} if group else None
        if means:identities(means)
        ss.append(dict(case=name,kind=m['kind'],size=f'{m["w"]}x{m["h"]}',progress=m['progress'],geometry_id=f'{m["w"]}x{m["h"]}_{m["kind"]}',n=len(group),seeds=[p['seed'] for p in group],reps=[p['rep'] for p in group],mean=means,ranges={k:[min(p[k] for p in group),max(p[k] for p in group)] for k in KEYS} if group else {},labels=flags(means) if means else None,raw=group))
    strata={}
    for field in ('kind','size','progress','geometry_id'):
        strata[field]={str(value):summarize([p for p in pp if p[field]==value],[s for s in ss if s[field]==value]) for value in sorted({s[field] for s in ss})}
    strata['kind_size_progress']={f'{s["kind"]}|{s["size"]}|p{s["progress"]}':summarize([p for p in pp if p['case']==s['case']],[s]) for s in ss}
    signals=[s for s in ss if s['kind']!='control' and s['n']==3 and s['mean']['dL']>0 and s['labels']['return_major']]
    fam=sorted({s['kind'] for s in signals});geoms=sorted({s['geometry_id'] for s in signals})
    counter={
        'same_tail_different_total':[p['id'] for p in pp if p['dR']==0 and p['dL']!=0],
        'shorter_tail_longer_total':[p['id'] for p in pp if p['dR']<0 and p['dL']>0],
        'same_endpoint_different_pre':[p['id'] for p in pp if p['same_endpoint'] and p['dC']!=0],
        'equal_total':[p['id'] for p in pp if p['dL']==0],
        'reverse_total':[p['id'] for p in pp if p['dL']<0]}
    return dict(pairs=pp,states=ss,full_three_seed_states=[s['case'] for s in ss if s['n']==3],summary={kind:summarize([p for p in pp if (p['kind']!='control' if kind=='events' else p['kind']=='control' if kind=='control' else True)],[s for s in ss if (s['kind']!='control' if kind=='events' else s['kind']=='control' if kind=='control' else True)]) for kind in ('all','events','control')},strata=strata,signal=dict(passed=len(fam)>=2 and len(geoms)>=3,families=fam,geometries=geoms,states=[s['case'] for s in signals],seed_consistency={s['case']:dict(all_dL_positive=all(p['dL']>0 for p in s['raw']),all_return_major=all(p['return_major'] for p in s['raw']),signs=[dict(seed=p['seed'],**{k:signs(p[k]) for k in ('dL','dC','dR','ddF','dX')}) for p in s['raw']]) for s in signals}),counterexamples=counter)
def compute():
    order=read(S/'formal_order.json');old={r['id']:r for r in read(S/'analysis.json')};meta={s['name']:s for s in read(S/'states.json')};assert len(order)==96 and len(meta)==16
    rows=[];group={};queries=[];counts=dict(planner_calls=0,coverage_exact_searches=0,full_graph_bfs=0,primary_endpoint_lookups=0,independent_unique_pair_searches=0,independent_cached_lookups=0);cache={};dist={}
    for name,m in sorted(meta.items()):
        c=read(S/'inputs'/f'{name}.json');f=set(map(tuple,c['free']));base=tuple(c['base']);dist[name]=bfs(f,base);counts['full_graph_bfs']+=1
    for j in order:
        o=read(S/'outputs'/f'{j["id"]}.json');assert o['job']==j
        c=read(S/j['input']);assert o['input_sha256']==sha(S/j['input']);x=o['result'];route=list(map(tuple,x['raw']['route']));assert route
        a=metric(c,route);b=cross(c,route);assert a==b==old[j['id']]['metrics'] and a['complete_legal']
        assert old[j['id']]['seconds']==x['entry_seconds']
        t=set(map(tuple,c['targets']));pending=t-set(map(tuple,c['covered']));pending.discard(route[0]);empty=not pending;completion=0 if empty else None
        for i,p in enumerate(route[1:],1):
            pending.discard(p)
            if completion is None and not pending:completion=i
        assert completion is not None and completion==a['completion_step'];endpoint=route[completion];d,parents=dist[j['case']];short=d[endpoint];counts['primary_endpoint_lookups']+=1
        key=(j['case'],endpoint)
        if key not in cache:cache[key]=independent_distance(set(map(tuple,c['free'])),endpoint,tuple(c['base']));counts['independent_unique_pair_searches']+=1;cache_hit=False
        else:counts['independent_cached_lookups']+=1;cache_hit=True
        assert short==cache[key]
        shortest=[endpoint]
        while shortest[-1]!=tuple(c['base']):shortest.append(parents[shortest[-1]])
        length=len(route)-1;tail=length-completion;excess=tail-short;assert excess>=0 and tail==a['return_tail_steps']
        r=dict(id=j['id'],case=j['case'],kind=meta[j['case']]['kind'],size=f'{meta[j["case"]]["w"]}x{meta[j["case"]]["h"]}',progress=meta[j['case']]['progress'],method=j['method'],seed=j['seed'],rep=j['rep'],seconds=x['entry_seconds'],legal=True,timely=x['entry_seconds']<20,L=length,C=completion,E=endpoint,R=tail,dF=short,X=excess,empty_initial_pending=empty,endpoint_label='completion_position' if empty else 'last_capture',base=c['base'],tail=route[completion:],shortest_return=shortest,metrics=a)
        rows.append(r);group.setdefault((j['case'],j['rep']),{})[j['method']]=r;queries.append(dict(route_id=j['id'],case=j['case'],endpoint=endpoint,base=c['base'],bfs_distance=short,independent_distance=cache[key],cache_hit=cache_hit))
    pairs=[]
    for (case,rep),g in sorted(group.items()):
        assert set(g)=={'PPCPP','P2_MULTI'};p,q=g['PPCPP'],g['P2_MULTI'];m=meta[case]
        dif=dict(dL=p['L']-q['L'],dC=p['C']-q['C'],dR=p['R']-q['R'],ddF=p['dF']-q['dF'],dX=p['X']-q['X'],dFresh=p['metrics']['fresh_target_steps']-q['metrics']['fresh_target_steps'],dHistorical=p['metrics']['historical_target_steps']-q['metrics']['historical_target_steps'],dRepeated=p['metrics']['repeated_new_target_steps']-q['metrics']['repeated_new_target_steps'],dNonTarget=p['metrics']['non_target_steps']-q['metrics']['non_target_steps']);identities(dif)
        pairs.append(dict(id=f'{case}__r{rep}',case=case,kind=m['kind'],size=p['size'],progress=m['progress'],geometry_id=p['size']+'_'+m['kind'],rep=rep,seed=p['seed'],legal=p['legal'] and q['legal'],timely=p['timely'] and q['timely'],same_endpoint=p['E']==q['E'],PPCPP={k:p[k] for k in ('id','L','C','E','R','dF','X','seconds','timely')},P2_MULTI={k:q[k] for k in ('id','L','C','E','R','dF','X','seconds','timely')},**dif,**flags(dif)))
    views={v:make_view(pairs,meta,v) for v in ('timely','legal')};examples={};missing=[]
    for kind in ('serpentine','rooms','maze'):
        ss=[s for s in views['timely']['states'] if s['kind']==kind and s['n']]
        choices={'maximum_gap':sorted(ss,key=lambda s:(-s['mean']['dL'],s['case'])),'minimum_positive_gap':sorted([s for s in ss if s['mean']['dL']>0],key=lambda s:(s['mean']['dL'],s['case'])),'first_equal':sorted([s for s in ss if s['mean']['dL']==0],key=lambda s:s['case'])}
        for label,candidates in choices.items():
            if not candidates:missing.append(dict(kind=kind,category=label));continue
            s=candidates[0];examples.setdefault(s['case'],dict(case=s['case'],view='timely',rep=min(s['reps']),reasons=[]))['reasons'].append(kind+':'+label)
    known='21x15_maze_p30'
    if known not in examples:
        for view in ('timely','legal'):
            s=next(s for s in views[view]['states'] if s['case']==known)
            if s['n']:examples[known]=dict(case=known,view=view,rep=min(s['reps']),reasons=[]);break
    examples[known]['reasons'].append('previously_discussed_posthoc_case')
    late=[dict(id=r['id'],milliseconds_over=(r['seconds']-20)*1000) for r in rows if not r['timely']]
    return normal(dict(routes=rows,pairs=pairs,views=views,distance_queries=queries,distance_execution=counts,examples=sorted(examples.values(),key=lambda x:x['case']),missing_example_categories=missing,late_returns=late,failures=[]))
def analyze():
    a=compute();save(H/'analysis.json',a);save(H/'distance_ledger.json',dict(queries=a['distance_queries'],execution=a['distance_execution']));save(H/'failures.json',a['failures'])
    csvsave(H/'96路线指标与末端.csv',a['routes']);csvsave(H/'48全部配对.csv',a['pairs'])
    for view,v in a['views'].items():
        csvsave(H/f'{view}_状态.csv',v['states']);csvsave(H/f'{view}_配对.csv',v['pairs']);save(H/f'{view}_分层.json',v['strata']);csvsave(H/f'{view}_分层.csv',[dict(dimension=field,value=value,**data) for field,groups in v['strata'].items() for value,data in groups.items()])
    print(json.dumps(dict(views={k:dict(events=v['summary']['events'],signal=v['signal']) for k,v in a['views'].items()},distance_execution=a['distance_execution'],examples=a['examples'],missing=a['missing_example_categories']),ensure_ascii=False),flush=True)
if __name__=='__main__':analyze()
