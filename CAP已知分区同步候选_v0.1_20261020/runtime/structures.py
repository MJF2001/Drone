"""Paper-mechanism cores. Public-map restart uses explored branches only."""
from primitives import components,center,cap_center,tour,neighbours
class TraceTree:
    def __init__(self,domain,states,metric,current):
        self.metric=metric;self.states=dict(states);self.nodes={};self.index={};self.order=[];self.events=[];self.next_id=0
        root=self.create(set(domain),None);self.order=[root];self.current=current
        self.update(set(domain))
        if not domain:self.nodes[root]['state']='C';self.order=[]
    def create(self,area,parent):
        i=self.next_id;self.next_id+=1
        self.nodes[i]=dict(A=set(area),R=set(area),parent=parent,children=[],center=None,state='exploring')
        for p in area:self.index[p]=i
        return i
    def update(self,changed,current=None):
        if current is not None:self.current=current
        affected=sorted({self.index[p] for p in changed if p in self.index});expanded={};completed=set()
        old_order=list(self.order)
        for i in affected:
            self.metric.check('tree_update');n=self.nodes[i]
            r={p for p in n['A'] if self.states.get(p) in ('U','Fu')}
            n['R']=r;n['center']=center(r);n['state']='C' if not r else 'exploring' if any(self.states[p]=='U' for p in r) else 'E'
            if not r:completed.add(i);continue
            parts=components(r,self.metric.check)
            if len(parts)>1:
                for p in n['A']:self.index.pop(p,None)
                ids=[self.create(a,i) for a in parts];n['children']=ids;expanded[i]=ids
                for v in ids:
                    a=self.nodes[v];a['center']=center(a['R']);a['state']='exploring' if any(self.states[p]=='U' for p in a['R']) else 'E'
                self.events.append(dict(type='split',parent=i,children=ids,parts=[sorted(a) for a in parts]))
        # Only replace expanded slots. Unaffected region order is never reoptimized.
        active_old=[i for i in old_order if i not in completed]
        new=[]
        for k,i in enumerate(active_old):
            if i not in expanded:new.append(i);continue
            ids=expanded[i];pred=new[-1] if new else None
            successor=active_old[k+1] if k+1<len(active_old) else None
            anchor=('start',i);end=('end',i) if successor is not None else None
            def position(v):
                if v==anchor:return self.nodes[pred]['center'] if pred is not None else self.current
                if v==end:return self.nodes[successor]['center']
                return self.nodes[v]['center']
            seq,info=tour(ids,anchor,position,self.metric,end)
            ordered=[v for v in seq if v in ids];new.extend(ordered)
            self.events.append(dict(type='slot_refine',parent=i,old_order=old_order,children_order=ordered,predecessor=pred,successor=successor,tsp=info))
        self.order=new
        self.events.append(dict(type='update',affected=affected,old_order=old_order,new_order=list(new)))
    def snapshot(self):
        return dict(order=list(self.order),index=[[list(p),i] for p,i in sorted(self.index.items())],nodes=[dict(id=i,A=sorted(n['A']),R=sorted(n['R']),parent=n['parent'],children=n['children'],center=n['center'],state=n['state']) for i,n in self.nodes.items()])
class CapGraph:
    def __init__(self,pending,metric,current,unknown=()):
        self.metric=metric;self.current=current;self.unknown=set(unknown);self.nodes={};self.order=[];self.events=[];self.next_id=0
        # Full-public restart seeding: do NOT invent past unknown-map history.
        for area in components(pending,metric.check):self.add(area)
        self.replan()
    def add(self,area):
        i=self.next_id;self.next_id+=1
        state='exploring' if any(v in self.unknown for p in area for v in neighbours(p)) else 'E'
        self.nodes[i]=dict(A=set(area),R=set(area),center=cap_center(area,self.metric.free),state=state)
        return i
    def replan(self):
        ids=[i for i,n in self.nodes.items() if n['state']!='C'];anchor=('robot',self.next_id)
        pos=lambda i:self.current if i==anchor else self.nodes[i]['center']
        exploring=[i for i in ids if self.nodes[i]['state']=='exploring'];end=None
        if exploring:
            dist=self.metric.matrix([self.current]+[pos(i) for i in exploring])[0]
            end=max(enumerate(exploring,1),key=lambda pair:(dist[pair[0]],-pair[1]))[1]
        seq,info=tour(ids,anchor,pos,self.metric,end);self.order=[i for i in seq if i!=anchor]
        self.events.append(dict(type='global_replan',nodes=ids,exploring=exploring,end=end,order=list(self.order),complete_graph_edges=(len(ids)+1)*len(ids)//2,tsp=info))
    def replace(self,i,parts):
        del self.nodes[i];ids=[self.add(set(a)) for a in parts];self.events.append(dict(type='replace',removed=i,added=ids));self.replan()
        return ids
    def sync(self,pending,current):
        self.current=current
        for n in self.nodes.values():
            n['R']=n['A']&pending
            if not n['R']:n['state']='C'
            else:n['center']=cap_center(n['R'],self.metric.free)
        self.order=[i for i in self.order if self.nodes[i]['state']!='C']
    def snapshot(self):
        return dict(order=list(self.order),nodes=[dict(id=i,A=sorted(n['A']),R=sorted(n['R']),center=n['center'],state=n['state']) for i,n in self.nodes.items()])
def cap_greedy(current,pending):return next((p for p in neighbours(current) if p in pending),None)
def trace_greedy(current,residual,states,free):
    x,y=current;candidates=[]
    for a in range(x-1,x+2):
        for b in range(y-1,y+2):
            p=(a,b)
            if p==current or p not in residual or states.get(p)!='Fu':continue
            if all((u,v) in free for u in range(min(x,a),max(x,a)+1) for v in range(min(y,b),max(y,b)+1)):candidates.append(p)
    return min(candidates,key=lambda p:(0 if p[0]<x else 1 if p[0]==x else 2,(p[0]-x)**2+(p[1]-y)**2,p)) if candidates else None
def trace_mark_departure(p,states):
    x,y=p;deferred=states.get((x,y+1))=='Fu' and states.get((x,y-1))=='Fu'
    states[p]='Fu' if deferred else 'Fc';return deferred
def trace_dead_end(current,residual,states,metric):
    candidates=sorted(p for p in residual if states.get(p)=='Fu' and any(states.get(q)=='Fc' for q in neighbours(p)))
    if not candidates:return None
    row=metric.matrix([current]+candidates)[0];return candidates[min(range(len(candidates)),key=lambda i:(row[i+1],candidates[i]))]
