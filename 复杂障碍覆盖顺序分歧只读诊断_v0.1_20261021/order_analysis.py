"""Observed orders/prefixes/slices only; no new candidate route or planning."""
import math,statistics,collections
from order_common import *
QS=(0,25,50,75,90,100)
def events(c,path):
    route=list(map(tuple,path));target=set(map(tuple,c['targets']));history=set(map(tuple,c['covered']));initial={route[0]}&(target-history);u=target-history-{route[0]};remain=set(u);out=[]
    for step,p in enumerate(route[1:],1):
        if p in remain:out.append(dict(target=p,rank=len(out)+1,step=step));remain.remove(p)
    assert not remain
    return initial,u,out
def slice_route(c,path,ev,u,m,dist):
    route=list(map(tuple,path));C=ev[-1]['step'] if ev else 0;L=len(route)-1;cache={};mapping=[]
    for q in QS:
        count=math.ceil(q*len(u)/100);step=ev[count-1]['step'] if count else 0
        mapping.append(dict(percent=q,count_threshold=count,step=step,snapshot=str(step)))
        if step in cache:continue
        collected={tuple(e['target']) for e in ev if e['step']<=step};remain=u-collected;ds=[dist[p] for p in sorted(remain)]
        cache[step]=dict(step=step,position=route[step],remaining=sorted(remain),remaining_count=len(remain),remaining_before_completion=C-step,return_tail=L-C,full_suffix_length=L-step,fragmentation=fragments(remain),remaining_base_distance=dict(min=min(ds),median=statistics.median(ds),max=max(ds)) if ds else dict(min=None,median=None,max=None),current_base_distance=dist[route[step]])
    return dict(empty_U=not u,proportions=mapping,snapshots={str(k):v for k,v in cache.items()})
def owner(trace,step):
    for i,event in enumerate(trace):
        end=trace[i+1]['index'] if i+1<len(trace) else float('inf')
        if event['index']<=step<end:return i
    return None
def decision_record(case,rep,t,ppath,qpath,common,c):
    out=S/'outputs'/f'{case}__{rep}__PPCPP.json';x=read(out);native=x['result']['raw'].get('branches',{}).get('P0',{});trace=native.get('trace',[]);index=owner(trace,t);p2file=S/'outputs'/f'{case}__{rep}__P2_MULTI.json';p2=read(p2file)['result']['raw']
    result=dict(PPCPP_output=str(out),PPCPP_output_sha256=sha(out),native_trace_pointer='$.result.raw.branches.P0.trace',owner_event_index=index,P2_output=str(p2file),P2_source=p2.get('source'),P2_direct_fields=list(p2),P2_stepwise_decision_record='not_recorded',evidence_scope='Only saved fields; no reward/core rerun and no missing candidate scores reconstructed.')
    if index is None:result.update(owner_kind='unknown',direct_record=None);return result
    e=trace[index];opts=e.get('options');pn=ppath[t+1] if t+1<len(ppath) else None;qn=qpath[t+1] if t+1<len(qpath) else None;at_start=e['index']==t
    result.update(owner_kind=e.get('kind'),direct_record=e,event_pointer=f'$.result.raw.branches.P0.trace[{index}]',at_event_start=at_start,nearby=[dict(index=i,pointer=f'$.result.raw.branches.P0.trace[{i}]',event=trace[i]) for i in range(max(0,index-1),min(len(trace),index+2))],missing_scores='none_for_saved_local_options' if opts is not None else 'candidate_distances_scores_not_recorded',PPCPP_next=pn,P2_next=qn)
    if e.get('kind')=='local' and at_start:
        assert tuple(e['current'])==tuple(common['current']) and e['previous']==normal(common['previous']);assert e['pending_count']==len(common['remaining'])
        assert tuple(e['goal'])==pn;chosen=min(opts,key=lambda o:(-o['score'],tuple(o['cell'])));assert tuple(chosen['cell'])==pn
        scores=[o['score'] for o in opts];maximum=max(scores);choices=[o['cell'] for o in opts if o['score']==maximum]
        result.update(chosen_record=chosen,recorded_max_tie_count=len(choices),recorded_max_tie_cells=choices,P2_next_in_recorded_options=any(tuple(o['cell'])==qn for o in opts),P2_recorded_option=next((o for o in opts if tuple(o['cell'])==qn),None),P2_next_was_initial_history=qn in set(map(tuple,c['covered'])) if qn else None,P2_next_was_pending=qn in set(map(tuple,common['remaining'])) if qn else None)
    return result
def pair_data(case,rep,c,p,q,ppath,qpath,dist):
    a=[tuple(e['target']) for e in p['acquisitions']];b=[tuple(e['target']) for e in q['acquisitions']];assert p['U']==q['U']
    k=0
    while k<min(len(ppath),len(qpath)) and ppath[k]==qpath[k]:k+=1
    t=k-1;assert t>=0
    common_acquired=set(map(tuple,c['covered']))|({x for x in ppath[:k]}&set(map(tuple,c['targets'])))
    remaining=set(map(tuple,p['U']))-set(ppath[:k]);prev=ppath[t-1] if t else (tuple(c['previous']) if c['previous'] is not None else None)
    common=dict(step=t,current=ppath[t],previous=prev,covered=sorted(common_acquired),remaining=sorted(remaining),used_steps=t,resource_remaining=c['distance_budget']-t)
    suffix={}
    for method,path in [('PPCPP',ppath),('P2_MULTI',qpath)]:
        audit_input=dict(c,current=path[t],previous=prev,covered=normal(sorted(common_acquired)),distance_budget=c['distance_budget']-t);m=both(audit_input,path[t:]);suffix[method]=dict(original_start_index=t,literal_existing_suffix=path[t:],steps=len(path)-1-t,metrics_relative_to_common_history=m)
    route_status='identical' if k==len(ppath)==len(qpath) else 'prefix_termination_difference' if k==min(len(ppath),len(qpath)) else 'common_state_fork'
    acqk=0
    while acqk<min(len(a),len(b)) and a[acqk]==b[acqk]:acqk+=1
    def arrival(data,path):
        if acqk>=len(data['acquisitions']):return None
        e=data['acquisitions'][acqk];i=e['step'];j=i-1
        return dict(next_target=e['target'],arrival_step=i,position_on_arrival=path[i],state_before_arrival=dict(step=j,position=path[j],previous=path[j-1] if j else c['previous'],resource_remaining=c['distance_budget']-j))
    order_diff=dict(common_target_count=acqk,common_targets=a[:acqk],next_PPCPP=arrival(p,ppath),next_P2_MULTI=arrival(q,qpath),warning='Acquisition-prefix equality alone is not a shared full state; route positions/headings/costs before arrivals are recorded separately.')
    if acqk:
        order_diff['last_common_acquisition']={m:dict(step=d['acquisitions'][acqk-1]['step'],position=path[d['acquisitions'][acqk-1]['step']],previous=path[d['acquisitions'][acqk-1]['step']-1]) for m,d,path in [('PPCPP',p,ppath),('P2_MULTI',q,qpath)]}
    ranks=[];ra={tuple(e['target']):e for e in p['acquisitions']};rb={tuple(e['target']):e for e in q['acquisitions']}
    for target in sorted(ra):ranks.append(dict(target=target,PPCPP_rank=ra[target]['rank'],P2_rank=rb[target]['rank'],rank_delta=ra[target]['rank']-rb[target]['rank'],PPCPP_step=ra[target]['step'],P2_step=rb[target]['step'],step_delta=ra[target]['step']-rb[target]['step'],base_distance=dist[target]))
    slices=[]
    for percent in QS:
        pa=next(x for x in p['slices']['proportions'] if x['percent']==percent);pb=next(x for x in q['slices']['proportions'] if x['percent']==percent);sa=p['slices']['snapshots'][str(pa['step'])];sb=q['slices']['snapshots'][str(pb['step'])];ua=set(map(tuple,sa['remaining']));ub=set(map(tuple,sb['remaining']));intersection=ua&ub;union=ua|ub
        slices.append(dict(percent=percent,PPCPP=sa,P2_MULTI=sb,intersection=sorted(intersection),union=sorted(union),jaccard=len(intersection)/len(union) if union else 1,PPCPP_only_remaining=sorted(ua-ub),P2_only_remaining=sorted(ub-ua),same_remaining_set=ua==ub,warning='Same capture proportion is not the same time, position, heading, history or task set; suffix deltas are not local-planner gains.'))
    delta={k:p[k]-q[k] for k in ('L','C','R')};assert delta['L']==delta['C']+delta['R'];assert suffix['PPCPP']['steps']-suffix['P2_MULTI']['steps']==delta['L']
    cls='identical_route' if ppath==qpath else 'different_path_same_complete_acquisition_order' if a==b else 'different_acquisition_order'
    tie_segments=None
    if a==b:
        aa=[0]+[e['step'] for e in p['acquisitions']]+[p['L']];bb=[0]+[e['step'] for e in q['acquisitions']]+[q['L']];tie_segments=[v-u for u,v in zip(aa,aa[1:])]==[v-u for u,v in zip(bb,bb[1:])]
    decision=decision_record(case,rep,t,ppath,qpath,common,c) if route_status=='common_state_fork' else dict(owner_kind='no_fork',evidence_scope='No fictitious next action at identical/terminated routes.')
    return dict(common_vertex_count=k,route_status=route_status,common_state=common,PPCPP_next=ppath[k] if k<len(ppath) else None,P2_next=qpath[k] if k<len(qpath) else None,existing_suffixes=suffix,acquisition_divergence=order_diff,classification=cls,same_order_all_capture_legs_equal_length=tie_segments,rank_differences=ranks,slice_pairs=slices,delta=delta,decision_evidence=decision)

def summarise(pairs):
    return dict(pairs=len(pairs),states=len({p['case'] for p in pairs}),geometries=len({p['geometry_id'] for p in pairs}),positive=sum(p['delta']['L']>0 for p in pairs),equal=sum(p['delta']['L']==0 for p in pairs),reverse=sum(p['delta']['L']<0 for p in pairs),classifications=dict(collections.Counter(p['classification'] for p in pairs)),fork_modes=dict(collections.Counter(p['decision_evidence']['owner_kind'] for p in pairs)),direct_local_forks=sum(p['decision_evidence'].get('owner_kind')=='local' and p['decision_evidence'].get('at_event_start',False) for p in pairs),local_p2_next_not_an_option=sum(p['decision_evidence'].get('owner_kind')=='local' and p['decision_evidence'].get('at_event_start',False) and p['decision_evidence'].get('P2_next_in_recorded_options') is False for p in pairs),signed_costs={k:sum(p['delta'][k] for p in pairs) for k in ('L','C','R')})
def views(pairs,ranks):
    result={}
    names=sorted({p['case'] for p in pairs})
    for view in ('timely','legal'):
        pp=[p for p in pairs if p['legal'] and (view=='legal' or p['timely'])];ss=[]
        for name in names:
            rr=sorted([p for p in pp if p['case']==name],key=lambda p:p['rep']);allp=next(p for p in pairs if p['case']==name);means={k:statistics.mean(p['delta'][k] for p in rr) for k in ('L','C','R')} if rr else None
            targetrows=[]
            if rr:
                ids={p['id'] for p in rr}
                group=collections.defaultdict(list)
                for r in ranks:
                    if r['pair_id'] in ids:group[tuple(r['target'])].append(r)
                for target,g in group.items():targetrows.append(dict(target=target,n=len(g),mean_abs_rank_delta=statistics.mean(abs(x['rank_delta']) for x in g),mean_rank_delta=statistics.mean(x['rank_delta'] for x in g),rank_delta_range=[min(x['rank_delta'] for x in g),max(x['rank_delta'] for x in g)],mean_step_delta=statistics.mean(x['step_delta'] for x in g),raw=g))
            top=sorted(targetrows,key=lambda r:(-r['mean_abs_rank_delta'],tuple(r['target'])))[:5]
            ss.append(dict(case=name,kind=allp['kind'],size=allp['size'],progress=allp['progress'],geometry_id=allp['geometry_id'],n=len(rr),reps=[p['rep'] for p in rr],seeds=[p['seed'] for p in rr],mean=means,ranges={k:[min(p['delta'][k] for p in rr),max(p['delta'][k] for p in rr)] for k in ('L','C','R')} if rr else {},raw_pair_ids=[p['id'] for p in rr],top_five_rank_delta=top))
        strata={field:{str(value):summarise([p for p in pp if p[field]==value]) for value in sorted({p[field] for p in pairs})} for field in ('kind','size','progress','geometry_id')}
        eventstrata={field:{str(value):summarise([p for p in pp if p['kind']!='control' and p[field]==value]) for value in sorted({p[field] for p in pairs if p['kind']!='control'})} for field in ('kind','size','progress','geometry_id')}
        result[view]=dict(pair_ids=[p['id'] for p in pp],states=ss,all=summarise(pp),events=summarise([p for p in pp if p['kind']!='control']),controls=summarise([p for p in pp if p['kind']=='control']),strata_all=strata,strata_events=eventstrata)
    return result
def compute():
    states={s['name']:s for s in read(S/'states.json')};old={r['id']:r for r in read(S/'analysis.json')};oldtail={r['id']:r for r in read(T/'analysis.json')['routes']};order=read(S/'formal_order.json');routes=[];paths={};byid={};ds={};counts=dict(full_base_BFS=0,independent_full_base_Dijkstra=0,independent_distance_vertices_checked=0,unique_slice_evaluations=0,proportion_mappings=0,new_planner_calls=0,coverage_exact_searches=0,candidate_route_generation=0)
    for name in sorted(states):
        c=read(S/'inputs'/f'{name}.json');free=set(map(tuple,c['free']));base=tuple(c['base']);d=distances(free,base);assert d==independent_distances(free,base);ds[name]=d;counts['full_base_BFS']+=1;counts['independent_full_base_Dijkstra']+=1;counts['independent_distance_vertices_checked']+=len(d)
    for job in order:
        c=read(S/job['input']);o=read(S/'outputs'/f'{job["id"]}.json');assert o['job']==job and o['input_sha256']==sha(S/job['input']);x=o['result'];path=list(map(tuple,x['raw'].get('route',[])));assert path
        m=both(c,path);assert m==old[job['id']]['metrics'];initial,u,ev=events(c,path);C=ev[-1]['step'] if ev else 0;L=len(path)-1;E=path[C];d=ds[job['case']];tail=oldtail[job['id']]
        assert C==m['completion_step']==tail['C'] and L==tail['L'] and L-C==m['return_tail_steps']==tail['R'] and E==tuple(tail['E']) and d[E]==tail['dF'];assert len(initial)==m['initial_credit']
        slices=slice_route(c,path,ev,u,m,d);counts['unique_slice_evaluations']+=len(slices['snapshots']);counts['proportion_mappings']+=len(slices['proportions'])
        row=dict(id=job['id'],case=job['case'],method=job['method'],rep=job['rep'],seed=job['seed'],input_sha256=sha(S/job['input']),output_sha256=sha(S/'outputs'/f'{job["id"]}.json'),L=L,C=C,R=L-C,last_capture=ev[-1]['target'] if ev else None,completion_position=E,completion_base_distance=d[E],initial_acquisition=sorted(initial),U=sorted(u),acquisitions=ev,slices=slices,metrics=m,seconds=x['entry_seconds'],legal=True,timely=x['entry_seconds']<20)
        routes.append(row);byid[job['id']]=row;paths[job['id']]=path
    pairs=[];ranks=[]
    for name,st in sorted(states.items()):
        c=read(S/'inputs'/f'{name}.json')
        for rep in range(3):
            p=byid[f'{name}__{rep}__PPCPP'];q=byid[f'{name}__{rep}__P2_MULTI'];detail=pair_data(name,rep,c,p,q,paths[p['id']],paths[q['id']],ds[name]);pid=f'{name}__r{rep}'
            paired=dict(id=pid,case=name,rep=rep,seed=p['seed'],kind=st['kind'],size=f'{st["w"]}x{st["h"]}',progress=st['progress'],geometry_id=f'{st["w"]}x{st["h"]}_{st["kind"]}',PPCPP_id=p['id'],P2_id=q['id'],legal=True,timely=p['timely'] and q['timely'],unavailable_reason=None if p['timely'] and q['timely'] else 'P2_or_PPCPP_entry_not_strictly_below20s',**detail)
            for r in detail['rank_differences']:ranks.append(dict(pair_id=pid,case=name,rep=rep,seed=p['seed'],**r))
            pairs.append(paired)
    vv=views(pairs,ranks);examples=[];missing=[]
    for kind in ('serpentine','rooms','maze','control'):
        for label,condition in [('positive',lambda p:p['delta']['L']>0),('equal',lambda p:p['delta']['L']==0)]:
            candidates=sorted([p for p in pairs if p['kind']==kind and p['timely'] and condition(p)],key=lambda p:(p['case'],p['rep']))
            if candidates:examples.append(dict(pair_id=candidates[0]['id'],kind=kind,category=label))
            else:missing.append(dict(kind=kind,category=label))
    assert len(examples)<=8
    counter=[]
    for p in pairs:
        for s in p['slice_pairs']:
            if s['percent'] in (0,100):continue
            a,b=s['PPCPP'],s['P2_MULTI'];md=a['remaining_base_distance']['median'];nd=b['remaining_base_distance']['median']
            tags=[]
            if p['delta']['L']>=0 and a['fragmentation']['components']<b['fragmentation']['components']:tags.append('PPCPP_fewer_fragments_but_not_shorter_total')
            if p['delta']['L']>=0 and md is not None and nd is not None and md<nd:tags.append('PPCPP_lower_remaining_median_distance_but_not_shorter_total')
            if tags:counter.append(dict(pair_id=p['id'],case=p['case'],geometry_id=p['geometry_id'],kind=p['kind'],timely=p['timely'],percent=s['percent'],tags=tags,deltaL=p['delta']['L'],PPCPP=a,P2_MULTI=b))
    return normal(dict(routes=routes,pairs=pairs,rank_differences=ranks,views=vv,examples=examples,missing_example_categories=missing,counterexamples=counter,distance_and_slice_execution=counts,failures=[]))
def analyze():
    a=compute();save(H/'analysis.json',a)
    for folder in ('acquisitions','slices','deep_reads'):(H/folder).mkdir()
    for r in a['routes']:
        save(H/'acquisitions'/f'{r["id"]}.json',{k:v for k,v in r.items() if k!='slices'});save(H/'slices'/f'{r["id"]}.json',r['slices'])
    for ex in a['examples']:
        p=next(p for p in a['pairs'] if p['id']==ex['pair_id']);save(H/'deep_reads'/f'{p["id"]}.json',dict(selection=ex,pair=p))
    csvsave(H/'48全配对索引与分歧.csv',a['pairs']);csvsave(H/'96路线指标.csv',[{k:v for k,v in r.items() if k not in ('slices','acquisitions','U')} for r in a['routes']]);csvsave(H/'全部目标排名与首次到达差.csv',a['rank_differences'])
    csvsave(H/'全部采集比例配对切片.csv',[dict(pair_id=p['id'],case=p['case'],rep=p['rep'],timely=p['timely'],**s) for p in a['pairs'] for s in p['slice_pairs']])
    for view,v in a['views'].items():
        csvsave(H/f'{view}_16状态均值范围与前五.csv',v['states']);csvsave(H/f'{view}_障碍分层.csv',[dict(dimension=field,value=value,**s) for field,vs in v['strata_events'].items() for value,s in vs.items()])
    save(H/'failures.json',a['failures']);print(__import__('json').dumps(dict(summary={k:{z:v[z] for z in ('all','events','controls')} for k,v in a['views'].items()},examples=a['examples'],missing=a['missing_example_categories'],distance_execution=a['distance_and_slice_execution']),ensure_ascii=False),flush=True)
if __name__=='__main__':analyze()
