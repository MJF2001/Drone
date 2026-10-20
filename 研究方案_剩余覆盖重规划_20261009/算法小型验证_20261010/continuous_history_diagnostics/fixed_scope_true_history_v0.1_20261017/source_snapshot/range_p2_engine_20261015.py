# Experimental range adapter: only adds an optional complete-route acceptance callback.
"""Instrumented P2: unchanged search order for base; explicit enhanced variants."""
import time,random
from unified_geometry import UnifiedGeometry,single_cell_audit
from model import DeadlineExceeded
from planners import candidates,nearest

def solve(s,budget,variant,seed,accept=None):
    begin=time.perf_counter();g=None;best=None;source=None;events=[];improvements=[];current='geometry'
    def elapsed():return time.perf_counter()-begin
    def offer(route,label):
        nonlocal best,source
        g.check_time();valid=route and (accept(route,label) if accept is not None else single_cell_audit(s,route)['valid']);g.check_time()
        if valid and (best is None or len(route)<len(best)):
            best=tuple(route);source=label;improvements.append(dict(seconds=elapsed(),steps=len(route)-1,source=label))
    def stage(label,fn):
        nonlocal current
        current=label;t=elapsed()
        try:
            value=fn();events.append(dict(stage=label,start=t,end=elapsed(),status='completed'));return value
        except DeadlineExceeded:
            events.append(dict(stage=label,start=t,end=elapsed(),status='deadline'));raise
    def opt(points,limit,label):
        visits=list(points);swaps=0;passes=0;reason='pass_limit';t=elapsed()
        try:
            for _ in range(limit):
                passes+=1;delta_best=0;pair=None
                for i in range(len(visits)-1):
                    a=s.current if i==0 else visits[i-1];b=visits[i]
                    for j in range(i+1,len(visits)):
                        c=visits[j];d=s.base if j+1==len(visits) else visits[j+1]
                        delta=g.distance(a,c)+g.distance(b,d)-g.distance(a,b)-g.distance(c,d)
                        if delta<delta_best:delta_best=delta;pair=(i,j)
                if pair is None:reason='no_improving_2opt_move';break
                i,j=pair;visits[i:j+1]=reversed(visits[i:j+1]);swaps+=1
            return visits
        except DeadlineExceeded:reason='deadline';raise
        finally:events.append(dict(stage=label+'_passes',start=t,end=elapsed(),passes=passes,swaps=swaps,termination=reason))
    try:
        g=UnifiedGeometry(s,time.perf_counter()+budget)
        if g.precheck():raise ValueError('infeasible input')
        def fallback():
            offer(s.old_route,'old_suffix');left=set(s.targets-s.covered);visits=[]
            for p in s.old_route:
                if p in left and p in s.free:visits.append(p);left.remove(p)
            visits.extend(sorted(left,key=lambda p:(p[1],p[0] if p[1]%2==0 else -p[0])))
            offer(g.expand(visits),'common_fallback')
        stage('fallback',fallback)
        demand=s.targets-s.covered-g.views[s.current];scans={};optimized=[]
        for axis in ('H','V'):
            points=stage(axis+'_generate',lambda:candidates(g,demand,axis));scans[axis]=points
            stage(axis+'_raw',lambda:offer(g.expand(points),axis+'_raw'))
            nn=stage(axis+'_nearest',lambda:nearest(g,points))
            stage(axis+'_NN_raw',lambda:offer(g.expand(nn),axis+'_NN_raw'))
            for label,initial in ((axis+'_scan',points),(axis+'_NN',nn)):
                order=stage(label+'_opt',lambda:opt(initial,8,label))
                stage(label+'_expand',lambda:offer(g.expand(order),label+'_opt'))
                optimized.append((label,order))
        events.append(dict(stage='core_finished',end=elapsed(),status='completed'))
        if variant!='base8':
            for label,p in optimized:
                order=stage(label+'_deep',lambda:opt(p,120,label+'_deep'))
                stage(label+'_deep_expand',lambda:offer(g.expand(order),label+'_deep'))
            events.append(dict(stage='deep_finished',end=elapsed(),status='completed'))
        if variant=='multi':
            rng=random.Random(seed)
            extra=[('reverse_H',list(reversed(scans['H']))),('reverse_V',list(reversed(scans['V'])))]
            for axis in ('H','V'):
                p=list(scans[axis])
                for _ in range(4):
                    if len(p)>1:
                        a,b=sorted(rng.sample(range(len(p)),2));p[a:b+1]=reversed(p[a:b+1])
                extra.append(('perturb_'+axis,p))
            for k in range(2):
                p=sorted(demand);rng.shuffle(p);extra.append(('shuffle_'+str(k),p))
            for label,p in extra:
                stage(label+'_raw',lambda:offer(g.expand(p),label+'_raw'))
                order=stage(label+'_opt',lambda:opt(p,32,label))
                stage(label+'_expand',lambda:offer(g.expand(order),label+'_opt'))
        status='finished'
    except DeadlineExceeded:status='deadline'
    return dict(route=best or (),source=source,status=status,seconds=elapsed(),active_stage=current,
        events=events,improvements=improvements,core_finished=any(e['stage']=='core_finished' for e in events))
