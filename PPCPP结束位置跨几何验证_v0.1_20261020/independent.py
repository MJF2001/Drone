"""Independent set-valued Dijkstra and search-certificate verifier. No exact imports."""
import heapq,gzip,json
def oracle(free,start,base,targets,last=None):
 todo=frozenset(targets-{start})
 if last==start and todo:return None
 heap=[(0,start,todo)];dist={(start,todo):0}
 while heap:
  d,p,u=heapq.heappop(heap)
  if dist[p,u]!=d:continue
  if not u and p==base:return d
  for z in free:
   if abs(z[0]-p[0])+abs(z[1]-p[1])!=1:continue
   if z==last and z in u and len(u)>1:continue
   v=u-{z};key=z,v
   if d+1<dist.get(key,10**9):dist[key]=d+1;heapq.heappush(heap,(d+1,z,v))
 return None
def audit_route(free,start,base,targets,path,last=None):
 path=list(map(tuple,path));assert path and path[0]==start and path[-1]==base and set(path)<=free
 assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(path,path[1:]))
 remain=set(targets);acq=[]
 for i,p in enumerate(path):
  if p in remain:remain.remove(p);acq.append((i,p))
 assert not remain
 if last is not None:assert acq and acq[-1][1]==last
 return len(path)-1
def certificate_audit(free,r,path):
 with gzip.open(path,'rt',encoding='utf-8') as f:c=json.load(f)
 cells=list(map(tuple,c['cells']));assert set(cells)==free and cells==sorted(free)
 n=len(cells);ts=list(map(tuple,r['targets']));index={p:i for i,p in enumerate(cells)}
 def bit(p):return (1<<ts.index(p)) if p in ts else 0
 full=(1<<len(ts))-1;last=tuple(r['last']) if r['last'] else None
 def legal(s,t):
  m,a=divmod(s,n);v,b=divmod(t,n);p,q=cells[a],cells[b]
  return abs(p[0]-q[0])+abs(p[1]-q[1])==1 and v==m|bit(q) and not (last==q and not m&bit(q) and (m|bit(q))!=full)
 records=c['records'];seen={s:(i,d) for i,(s,p,d) in enumerate(records)};assert len(seen)==len(records)==r['discovered']
 start=tuple(r['start']);base=tuple(r['base']);assert records[0]==[bit(start)*n+index[start],-1,0]
 prev=-1
 for i,(s,p,d) in enumerate(records):
  assert d>=prev;prev=d
  if i:assert 0<=p<i and records[p][2]+1==d and legal(records[p][0],s)
 if r['status']=='optimal':
  goal=c['goal'];assert goal==c['expanded'] and records[goal][0]==full*n+index[base] and records[goal][2]==r['length']
  audit_route(free,start,base,set(ts),r['route'],last)
 elif r['status']=='infeasible':assert c['expanded']==len(records) or c['invalid_start']
 else:assert r['status']=='unresolved' and r['length'] is None and not r['route'];return
 if c['invalid_start']:
  assert last==start and set(ts)-{start};return
 # Every popped nonterminal state before termination has all legal successors
 # discovered at distance <= d+1. Together with parent witnesses this proves
 # no shorter terminal can have been omitted; exhaustion proves infeasibility.
 for s,p,d in records[:c['expanded']]:
  m,a=divmod(s,n);assert not(m==full and cells[a]==base)
  for q in free:
   if abs(q[0]-cells[a][0])+abs(q[1]-cells[a][1])!=1:continue
   nxt=(m|bit(q))*n+index[q]
   if legal(s,nxt):assert nxt in seen and seen[nxt][1]<=d+1
