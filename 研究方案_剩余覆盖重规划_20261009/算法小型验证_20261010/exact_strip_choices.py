"""Exact fixed-strip diagnostic. Mandatory full service; not a final planner."""
from pathlib import Path
from collections import defaultdict
from itertools import permutations, product
import json, hashlib, time
from scenarios import deserialize
from unified_geometry import UnifiedGeometry
from audit import audit
from supplement_route_metrics import metrics

D=Path(__file__).parent;O=D/'results/run_31_exact_strip_choices_20261012'
B=D.parent/'论文资料汇总_三篇文献与论文主题_20261009'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def partition(s,axis):
    pending=set(s.targets-s.covered)-{s.current};groups=defaultdict(list)
    for p in pending:groups[p[1-axis]].append(p)
    blocks=[]
    for row,ps in sorted(groups.items()):
        part=[]
        for p in sorted(ps,key=lambda p:p[axis]):
            if part and p[axis]!=part[-1][axis]+1:blocks.append(tuple(part));part=[]
            part.append(p)
        if part:blocks.append(tuple(part))
    assert set().union(*(set(b) for b in blocks))==pending
    return blocks

VARIANTS=[('fixed',False,False,True),('direction',False,True,True),
          ('order',True,False,True),('joint',True,True,True),('prefix_only',True,True,False)]

def solve(s,blocks,g,order_free,dir_free,return_aware):
    n=len(blocks);full=(1<<n)-1
    opts={i:[blocks[i],tuple(reversed(blocks[i]))] for i in range(n)}
    # Fixed reference alternates by sorted block index, including split rows.
    fixed=[i%2 for i in range(n)]
    orientations=lambda j:range(2) if dir_free and len(blocks[j])>1 else [fixed[j] if len(blocks[j])>1 else 0]
    dp={};parent={}
    for j in (range(n) if order_free else [0]):
        for d in orientations(j):
            key=(1<<j,j,d);dp[key]=g.distance(s.current,opts[j][d][0])+len(blocks[j])-1;parent[key]=None
    for mask in range(1,full+1):
        for j in range(n):
            if not mask>>j&1:continue
            for d in orientations(j):
                key=(mask,j,d)
                if key not in dp:continue
                for k in (range(n) if order_free else [j+1]):
                    if k>=n or mask>>k&1:continue
                    for e in orientations(k):
                        nxt=(mask|1<<k,k,e)
                        value=dp[key]+g.distance(opts[j][d][-1],opts[k][e][0])+len(blocks[k])-1
                        if value<dp.get(nxt,float('inf')):dp[nxt]=value;parent[nxt]=key
    def score(key):
        prefix=dp[key];tail=g.distance(opts[key[1]][key[2]][-1],s.base)
        return (prefix+tail,prefix,key) if return_aware else (prefix,tail,key)
    end=min((k for k in dp if k[0]==full),key=score);value=dp[end];chain=[];cur=end
    while cur is not None:chain.append((cur[1],cur[2]));cur=parent[cur]
    chain.reverse();route=[s.current]
    for j,d in chain:
        service=opts[j][d];route.extend(g.path(route[-1],service[0])[1:]);route.extend(service[1:])
    tail=g.distance(route[-1],s.base);route.extend(g.path(route[-1],s.base)[1:])
    assert len(route)-1==value+tail
    return dict(route=route,sequence=chain,prefix_objective=value,tail_objective=tail,length=value+tail,states=len(dp))

def brute(s,blocks,g,order_free,dir_free,return_aware):
    n=len(blocks);best=None
    for seq in permutations(range(n)) if order_free else [tuple(range(n))]:
        choices=[range(2) if dir_free and len(blocks[j])>1 else [j%2 if len(blocks[j])>1 else 0] for j in seq]
        for dirs in product(*choices):
            p=s.current;cost=0
            for j,d in zip(seq,dirs):
                b=blocks[j] if not d else tuple(reversed(blocks[j]));cost+=g.distance(p,b[0])+len(b)-1;p=b[-1]
            tail=g.distance(p,s.base);score=(cost+tail,cost) if return_aware else (cost,tail)
            if best is None or score<best:best=score
    return best

def main():
    O.mkdir(parents=True,exist_ok=False)
    paths=[D/'results/run_21_micro_global_optimum/snapshots.json',D/'results/run_21_micro_global_optimum/results.json',D/'results/run_26_unified_new_maps/snapshots.json']
    hashes={str(p):sha(p) for p in paths}
    protocol=dict(input_sha256=hashes,script_sha256=sha(Path(__file__)),
      model='fixed maximal contiguous pending strips; full service once even if incidentally covered; start and return included',
      reference='blocks sorted by row then coordinate; alternating direction by block index',
      variants=VARIANTS,max_blocks=12,micro='all 48 states, horizontal and vertical partitions',
      medium='all 24 run26 states, horizontal partition; exclude over12 blocks before solving',
      tie_rule='prefix_only minimizes prefix then return among prefix-optimal solutions',
      independent_check='exhaustive permutations and directions for all partitions with <=5 blocks',
      note='not a fair-time benchmark; no global optimality claim except within frozen strip model')
    (O/'protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    exact={r['case']:r for r in read(paths[1]) if r['algorithm']=='EXACT_GRID'}
    jobs=[];excluded=[]
    for batch,rs in [('micro',read(paths[0])),('medium',read(paths[2]))]:
        for r in rs:
            raw=r.get('snapshot',r);s=deserialize(raw)
            for axis in ((0,1) if batch=='micro' else (0,)):
                blocks=partition(s,axis)
                item=dict(batch=batch,case=s.name,axis=axis,n_blocks=len(blocks))
                if not blocks or len(blocks)>12:excluded.append(item);continue
                jobs.append((s,blocks,item))
    results=[];checks=0;start=time.perf_counter()
    for index,(s,blocks,item) in enumerate(jobs):
        g=UnifiedGeometry(s);outputs={}
        for name,order_free,dir_free,return_aware in VARIANTS:
            t=time.perf_counter();v=solve(s,blocks,g,order_free,dir_free,return_aware);v['seconds']=time.perf_counter()-t
            a=audit(s,tuple(map(tuple,v['route'])));assert a['valid'],(item,name,a)
            v['audit']=a;v['metrics']=metrics(v['route'],s.targets,s.covered)
            if len(blocks)<=5:
                z=brute(s,blocks,g,order_free,dir_free,return_aware)
                score=(v['length'],v['prefix_objective']) if return_aware else (v['prefix_objective'],v['tail_objective'])
                assert z==score,(item,name,z,score);checks+=1
            if item['batch']=='micro':
                e=exact[s.name];assert audit(s,tuple(map(tuple,e['route'])))['valid'];assert v['length']>=e['length'];v['grid_optimum']=e['length']
            outputs[name]=v
        L=lambda k:outputs[k]['length']
        assert L('joint')<=min(L('order'),L('direction'))<=L('fixed')
        assert L('joint')<=L('prefix_only')
        results.append(dict(**item,blocks=blocks,outputs=outputs))
        if index%10==0:print(f'{index+1}/{len(jobs)} partitions checked',flush=True)
    assert hashes=={str(p):sha(p) for p in paths}
    summaries=[]
    for batch in ('micro','medium'):
        rs=[r for r in results if r['batch']==batch];pairs=[]
        for a,b in [('direction','fixed'),('order','fixed'),('joint','fixed'),('joint','order'),('joint','direction'),('joint','prefix_only')]:
            ds=[r['outputs'][a]['length']-r['outputs'][b]['length'] for r in rs]
            pairs.append(dict(candidate=a,reference=b,win_tie_loss=[sum(d<0 for d in ds),sum(d==0 for d in ds),sum(d>0 for d in ds)],delta=sum(ds)))
        summaries.append(dict(batch=batch,n=len(rs),totals={name:sum(r['outputs'][name]['length'] for r in rs) for name,*_ in VARIANTS},pairs=pairs,
          grid_gap=sum(r['outputs']['joint']['length']-r['outputs']['joint'].get('grid_optimum',r['outputs']['joint']['length']) for r in rs)))
    for name,data in [('results.json',results),('summary.json',summaries),('excluded.json',excluded),('completion.json',dict(partitions=len(results),routes=len(results)*5,valid=len(results)*5,brute_checks=checks,seconds=time.perf_counter()-start,hashes_unchanged=True))]:
        (O/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summaries,ensure_ascii=False));print('finished',checks,flush=True)

if __name__=='__main__':main()
