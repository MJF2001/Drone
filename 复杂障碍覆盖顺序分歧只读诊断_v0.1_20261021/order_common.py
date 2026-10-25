"""Pure I/O/metrics and ordinary distance tables. No planner imports."""
import json,csv,hashlib,importlib.util,collections,heapq,statistics
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;S=R/'复杂障碍压力开发测试_v0.1_20261021';T=R/'复杂障碍末端返航只读诊断_v0.1_20261021'
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def normal(x):return json.loads(json.dumps(x,ensure_ascii=False))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def csvsave(p,rows):
    if not rows:return
    with Path(p).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows([{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict,tuple)) else v for k,v in r.items()} for r in rows])
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
MD=R/'评价指标完整补算与数据审计_v0.1_20261020';metric=load('order_metric_a',MD/'metrics.py').metrics;cross=load('order_metric_b',MD/'crosscheck.py').calculate
def both(c,path):
    a=metric(c,path);assert a==cross(c,path) and a['complete_legal'];return a
def distances(f,base):
    d={base:0};queue=collections.deque([base])
    while queue:
        x,y=queue.popleft()
        for q in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
            if q in f and q not in d:d[q]=d[x,y]+1;queue.append(q)
    assert set(d)==f
    return d
def independent_distances(f,base):
    best={base:0};todo=[(0,base)];done={}
    while todo:
        cost,p=heapq.heappop(todo)
        if p in done:continue
        done[p]=cost
        for axis,step in ((1,-1),(0,-1),(1,1),(0,1)):
            q=list(p);q[axis]+=step;q=tuple(q)
            if q in f and cost+1<best.get(q,float('inf')):best[q]=cost+1;heapq.heappush(todo,(cost+1,q))
    assert set(done)==f;return done
def fragments(u):
    rest=set(u);sizes=[]
    while rest:
        start=min(rest);rest.remove(start);todo=[start]
        for x,y in todo:
            for q in ((x-1,y),(x,y-1),(x+1,y),(x,y+1)):
                if q in rest:rest.remove(q);todo.append(q)
        sizes.append(len(todo))
    return dict(components=len(sizes),largest_component=max(sizes,default=0))
