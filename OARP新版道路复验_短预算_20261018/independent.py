"""Independent graph, exact route, and structural verification; stdlib only."""
import collections,functools,itertools

def targets(req):return (set(map(tuple,req['P']))-set(map(tuple,req['C'])))&set(map(tuple,req['F']))
def audit(req,route):
    P,F,C=(set(map(tuple,req[k])) for k in ('P','F','C'));Q=(P-C)&F
    route=list(map(tuple,route));errors=[]
    if not C<=P:errors.append('ledger')
    if not route:return ['empty']+errors
    if route[0]!=tuple(req['current']):errors.append('start')
    if route[-1]!=tuple(req['base']):errors.append('base')
    if not set(route)<=F:errors.append('collision')
    if any(abs(a[0]-b[0])+abs(a[1]-b[1])!=1 for a,b in zip(route,route[1:])):errors.append('step')
    if not Q<=set(route):errors.append('coverage')
    if len(route)-1>req['resource']:errors.append('resource')
    return errors

def check_strips(plan,Q):
    path=list(map(tuple,plan['route']));cells=[];identities=[]
    for s in plan['strips']:
        pts=list(map(tuple,s['cells']));axis=s['axis'];assert pts and axis in ('H','V')
        dx,dy=(1,0) if axis=='H' else (0,1)
        assert all((b[0]-a[0],b[1]-a[1])==(dx,dy) for a,b in zip(pts,pts[1:]))
        assert path[s['service_start']:s['service_end']+1]==(pts[::-1] if s['reversed_direction'] else pts)
        cells.extend(pts);identities.append(s['rank_id'])
    assert len(cells)==len(set(cells)) and set(cells)==Q and len(identities)==len(set(identities))
    for b in plan.get('packets',[]):assert path[b['start']:b['end']+1]==list(map(tuple,b['path']))

class Geometry:
    def __init__(self,req):self.free=set(map(tuple,req['F']));self.req=req;self.rows={}
    def path(self,a,b):
        a,b=tuple(a),tuple(b)
        if a not in self.rows:
            q=collections.deque([a]);prev={a:None}
            while q:
                x,y=q.popleft()
                for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if p in self.free and p not in prev:prev[p]=(x,y);q.append(p)
            self.rows[a]=prev
        prev=self.rows[a];assert b in prev;out=[];p=b
        while p is not None:out.append(p);p=prev[p]
        return out[::-1]

def exact(req,paths):
    if len(paths)>12:return {'status':'not_computed_group_limit','groups':len(paths)}
    g=Geometry(req);states=[]
    for p in paths:
        p=list(map(tuple,p));assert p and set(p)<=g.free
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(p,p[1:]))
        states.extend((p,p[::-1]))
    n=len(paths);s=tuple(req['current']);base=tuple(req['base'])
    def lastpoint(last):return s if last==2*n else states[last][-1]
    @functools.lru_cache(None)
    def dp(mask,last):
        origin=lastpoint(last)
        if mask==(1<<n)-1:return len(g.path(origin,base))-1,()
        options=[]
        for k in range(n):
            if mask>>k&1:continue
            for v in (2*k,2*k+1):
                cost,tail=dp(mask|1<<k,v)
                options.append((len(g.path(origin,states[v][0]))-1+len(states[v])-1+cost,(v,)+tail))
        return min(options)
    cost,order=dp(0,2*n);route=[s]
    for v in order:
        route.extend(g.path(route[-1],states[v][0])[1:]);route.extend(states[v][1:])
    route.extend(g.path(route[-1],base)[1:]);assert cost==len(route)-1 and not audit(req,route)
    return {'status':'optimal','groups':n,'cost':cost,'order':order,'route':route,'dp_states':dp.cache_info().currsize}

def global_cover(req):
    Q=sorted(targets(req));assert len(Q)<=12
    bit={p:1<<i for i,p in enumerate(Q)};allmask=(1<<len(Q))-1
    s=tuple(req['current']);base=tuple(req['base']);F=set(map(tuple,req['F']))
    start=(s,bit.get(s,0));q=collections.deque([start]);prev={start:None};finish=None
    while q:
        state=q.popleft();(x,y),mask=state
        if (x,y)==base and mask==allmask:finish=state;break
        for p in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            z=p,mask|bit.get(p,0)
            if p in F and z not in prev:prev[z]=state;q.append(z)
    assert finish is not None;route=[];z=finish
    while z is not None:route.append(z[0]);z=prev[z]
    route.reverse();assert not audit(req,route)
    return {'cost':len(route)-1,'route':route,'states_discovered':len(prev),'target_count':len(Q)}

def minimum_rank_ties(req):
    Q=targets(req);best=len(Q)+1;covers=[];count=0
    def walk(left,segments):
        nonlocal best,covers,count
        if not left:
            count+=1
            if len(segments)<best:best=len(segments);covers=[segments]
            elif len(segments)==best:covers.append(segments)
            return
        p=min(left)
        for a,(dx,dy) in (('H',(1,0)),('V',(0,1))):
            cells=[];z=p
            while z in left:
                cells.append(z);walk(left-set(cells),segments+[{'axis':a,'cells':cells[:]}]);z=z[0]+dx,z[1]+dy
    walk(set(Q),[]);winner=None;worst=None
    for cover in covers:
        answer=exact(req,[s['cells'] for s in cover]);cost=answer['cost']
        if winner is None or cost<winner['cost']:winner={'cost':cost,'ranks':cover,'route':answer['route']}
        worst=cost if worst is None else max(worst,cost)
    return {'enumerated_covers':count,'minimum_rank_count':best,'minimum_rank_ties':len(covers),
            'best_minimum_rank_cover':winner,'worst_minimum_rank_cover_cost':worst}

def signature(ranks):return sorted((r['axis'],tuple(map(tuple,r['cells']))) for r in ranks)

def selftest():
    req={'F':[(0,0),(1,0),(2,0)],'P':[(1,0),(2,0)],'C':[],'current':(0,0),'base':(0,0),'resource':10}
    assert exact(req,[[(1,0),(2,0)]])['cost']==global_cover(req)['cost']==4
    assert audit(dict(req,resource=3),[(0,0),(1,0),(2,0),(1,0),(0,0)])==['resource']
    assert 'step' in audit(req,[(0,0),(2,0),(0,0)])
    assert 'coverage' in audit(req,[(0,0)])
    assert 'base' in audit(req,[(0,0),(1,0),(2,0)])
    assert minimum_rank_ties(req)['minimum_rank_count']==1
    # Exhaustive permutations is a second exact algorithm for a four-point graph.
    req={'F':[(x,y) for x in range(3) for y in range(3)],'P':[(0,1),(2,1)],'C':[],
         'current':(1,0),'base':(1,0),'resource':100}
    paths=[[(0,1)],[(2,1)]];g=Geometry(req)
    brute=min(sum(len(g.path(a,b))-1 for a,b in zip([tuple(req['current'])]+list(order),list(order)+[tuple(req['base'])]))
              for order in itertools.permutations([p[0] for p in paths]))
    assert exact(req,paths)['cost']==brute==6
    return {'passed':True,'planner_calls':0,'negative_resource_step_coverage_base_checks':4,'exact_DP_vs_full_permutation':True}
