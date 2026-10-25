"""One locked-anchor shortcut pass. Production planners are never imported."""
import json,time,math
from decimal import Decimal
from collections import Counter
from . import geometry as G
from .. import service as C

def ps(x):return set(map(tuple,x))

def first_original(path,U):
    seen=set();out=[]
    for i,p in enumerate(path):
        if p in U and p not in seen:out.append({'point':list(p),'index':i});seen.add(p)
    assert seen==U
    return out

def split(path,first):
    n=len(path)-1
    if not first:return [(0,n,'empty_task_to_base')]
    f=[v['index'] for v in first]
    return [(0,f[0],'start_to_first')]+[(a,b,'between_first_services') for a,b in zip(f,f[1:])]+[(f[-1],n,'last_to_base')]

def credits(path,U,counters):
    seen=set();out=[]
    for p in sorted(U):
        if C.inside(path[0],p,counters,'post'):
            seen.add(p)
            out.append({'point':list(p),'edge':-1,'collect_here':True,
                        'witness':{'t':C.rat(0),'point':C.pt(path[0])}})
    for k,(a,b) in enumerate(zip(path,path[1:])):
        found=[]
        for p in sorted(U):
            counters['service_intersections']+=1
            evidence=C.intersection(a,b,p,counters,'post')
            if evidence is not None and p not in seen:
                t=evidence['witness']['t'];found.append((None,p,evidence))
        # Exact order is diagnostic witness order, not a claimed first internal time.
        from fractions import Fraction
        found.sort(key=lambda z:(Fraction(z[2]['witness']['t']['n'],z[2]['witness']['t']['d']),z[1]))
        for _,p,evidence in found:
            if p not in seen:
                out.append({'point':list(p),'edge':k,'evidence':evidence});seen.add(p)
    assert seen==U,('missing_credit',U-seen)
    return out

def turns(path):
    ds=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(path,path[1:]) if a!=b];count=0;angle=0.
    for u,v in zip(ds,ds[1:]):
        cross=u[0]*v[1]-u[1]*v[0];dot=u[0]*v[0]+u[1]*v[1]
        if cross or dot<0:count+=1;angle+=math.atan2(abs(cross),dot)
    return {'nonzero_direction_changes':count,'total_turn_radians':angle}

def process(payload,limit=4096,soft=18.,total=20.):
    start=time.perf_counter();o=json.loads(payload);c=o['input'];raw=o['raw'];path=list(map(tuple,raw['route']));F=ps(c['free']);U=ps(c['targets'])-ps(c['covered']);n=len(path)-1
    counts=Counter(candidate=0,source_validation=0,output_validation=0,service_intersections=0);times={};phase=time.perf_counter()
    assert path[0]==tuple(c['current']) and path[-1]==tuple(c['base']);assert n<=Decimal(str(c['distance_budget']))
    assert ps(c['targets'])==ps(c['published_targets'])&F and ps(c['deferred_targets'])==ps(c['published_targets'])-F-ps(c['covered'])
    for a,b in zip(path,path[1:]):
        assert abs(a[0]-b[0])+abs(a[1]-b[1])==1
        counts['source_validation']+=1;assert G.legal(F,a,b)
    first=first_original(path,U);parts=split(path,first);times['parse_preprocess_source_validation']=time.perf_counter()-start
    phase=time.perf_counter();edges=[];querylog=[];fallback=None;partdata=[]
    for part,(left,right,kind) in enumerate(parts):
        idx=left;loedge=len(edges)
        while idx<right:
            if fallback is None and (counts['candidate']>=limit or time.perf_counter()-start>=soft):fallback='candidate_cap' if counts['candidate']>=limit else 'soft_deadline'
            if fallback is not None:j=idx+1
            else:
                j=right
                while j>idx:
                    if counts['candidate']>=limit or time.perf_counter()-start>=soft:
                        fallback='candidate_cap' if counts['candidate']>=limit else 'soft_deadline';j=idx+1;break
                    counts['candidate']+=1;ok=G.legal(F,path[idx],path[j]);querylog.append({'i':idx,'j':j,'legal':ok,'part':part})
                    if ok:break
                    j-=1
                assert j>idx
            edges.append({'left':idx,'right':j,'a':list(path[idx]),'b':list(path[j]),'part':part,'kind':kind});idx=j
        partdata.append({'left':left,'right':right,'kind':kind,'edge_start':loedge,'edge_end':len(edges)})
    times['candidate']=time.perf_counter()-phase;phase=time.perf_counter()
    output=[path[0]]+[tuple(e['b']) for e in edges]
    for a,b in zip(output,output[1:]):counts['output_validation']+=1;assert G.legal(F,a,b)
    credited=credits(output,U,counts);bounds=G.interval(output);lo,hi=map(Decimal,bounds);E=Decimal(str(c['distance_budget']))
    assert hi<=Decimal(n) and hi<=E,('length_or_resource_interval',bounds,n,str(E))
    assert len(edges)<=n and counts['candidate']<=limit and counts['service_intersections']<=n*len(U)
    for p in partdata:p['L4']=p['right']-p['left'];p['new_interval']=G.interval([path[p['left']]]+[tuple(e['b']) for e in edges[p['edge_start']:p['edge_end']]])
    trace=raw.get('trace',[]);cross=Counter()
    for p in partdata:
        for k in range(p['left'],p['right']):
            ts=[t for t in trace if t['index']<=k];tr=ts[-1]['kind'] if ts else 'unavailable';cross[p['kind']+' x '+tr]+=1
    r={'id':o['id'],'L4':n,'Lshortcut_interval':bounds,'Lshortcut_display':float((lo+hi)/2),'saving_display':float(Decimal(n)-(lo+hi)/2),'saving_ratio_display':float((Decimal(n)-(lo+hi)/2)/n) if n else 0.,'distance_budget':c['distance_budget'],'resource_proof':'source L4 <= E; subsequence edges replace disjoint original intervals; triangle inequality; independently bounded output <= E','vertices':output,'edges':edges,'parts':partdata,'locked_nominal_anchors':first,'credit_witnesses':credited,'witness_order_differs_from_locked_anchors':[v['point'] for v in first]!=[v['point'] for v in credited],'trace_cross_original_moves':dict(cross),'counts':dict(counts),'query_log':querylog,'fallback':fallback,'turns_original':turns(path),'turns_new':turns(output),'timing':times}
    times['main_validation_metrics']=time.perf_counter()-phase;phase=time.perf_counter();encoded=json.dumps(r,ensure_ascii=False,separators=(',',':'));times['encoding']=time.perf_counter()-phase
    # Return a fully encoded artifact plus an external timing envelope; encoding is inside the budget.
    elapsed=time.perf_counter()-start
    return encoded,{'entry_seconds':elapsed,'late':elapsed>total,'counts':dict(counts),'fallback':fallback}
