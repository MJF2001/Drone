"""Read saved walks only: no optimization, graph search or new route."""
from pathlib import Path
import json,hashlib,sys,collections
H=Path(__file__).resolve().parent;R=H.parent;A=R/'PPCPP四方向共同预算正式比较_v0.1_20261020';B=R/'连续事件六世界开发比较_v0.1_20261022'
sources={}
def read(p):
    p=Path(p);sources[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest();return json.loads(p.read_text(encoding='utf8'))
def save(n,x):
    with (H/n).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def ps(x):return set(map(tuple,x))
def guard():
    class Block:
        def find_spec(self,n,path=None,target=None):
            if n.split('.')[0] in {'model','runtime','candidate','planners','executor','worker','p2_search_audit','heapq','_heapq','ppcpp'}:raise AssertionError('forbidden planner import')
    sys.meta_path.insert(0,Block())
    def profile(f,e,a):
        if e=='call' and f.f_code.co_name in {'solve','run_payload','run_world','reach','walk_component','precheck'}:raise AssertionError('forbidden solve/search')
    sys.setprofile(profile)
def inventory(c,raw,source,inputfile,batch,case,refs,seedproof):
    path=raw['route'];T=ps(c['targets']);old=ps(c['covered']);required=T-old;seen=set(old);first=[];kinds=[];occ={};edge={}
    for i,p in enumerate(path):
        q=tuple(p);occ.setdefault(q,[]).append(i)
        if i:kinds.append('non_target' if q not in T else 'historical' if q in old else 'repeat_target' if q in seen else 'fresh')
        if q in T and q not in seen:first.append(dict(point=p,index=i));seen.add(q)
        if i:
            a,b=tuple(path[i-1]),q;assert abs(a[0]-b[0])+abs(a[1]-b[1])==1;key=tuple(sorted((a,b)));edge.setdefault(key,[]).append(i-1)
    assert required<=set(map(tuple,path)) and path[0]==c['current'] and path[-1]==c['base'] and ps(path)<=ps(c['free']) and len(path)-1<=c['distance_budget']
    loops=[]
    for q,positions in occ.items():
        for l,r in zip(positions,positions[1:]):
            responsible=[list(p) for p,ix in occ.items() if p in required and all(l<j<r for j in ix)]
            loops.append(dict(left=l,right=r,endpoint=list(q),steps=r-l,exclusive_interior_required=sorted(responsible),first_service_interior=[e for e in first if l<e['index']<r],gain_unknown=True))
    trace=raw.get('trace',[]);segments=[]
    for i,e in enumerate(trace):
        l=e['index'];r=trace[i+1]['index'] if i+1<len(trace) else len(path)-1;assert 0<=l<=r<len(path);segments.append(dict(trace_index=i,kind=e['kind'],left=l,right=r,steps=r-l,entry=path[l],exit=path[r]))
    counts=dict(collections.Counter(kinds));refsteps=[dict(source=x['source'],steps=x['steps'],legal=x['legal']) for x in refs];valid=[x['steps'] for x in refs if x['legal']];delta=(len(path)-1-valid[0]) if valid else None
    return dict(batch=batch,case=case,input=inputfile,output=source,steps=len(path)-1,counts=counts,first_services=first,segments=segments,closed_intervals=loops,repeated_edges=[dict(endpoints=list(k),depart_indices=v) for k,v in edge.items() if len(v)>1],repeated_vertices=[dict(point=list(k),indices=v) for k,v in occ.items() if len(v)>1],P2_reference=refsteps,delta_to_primary_P2=delta,relation='unknown' if delta is None else 'PPCPP_longer' if delta>0 else 'equal' if delta==0 else 'PPCPP_shorter',seed_equivalence=seedproof)
def main():
    guard();rows=[];order=read(A/'order.json');cases=sorted({j['case'] for j in order});assert len(cases)==54;seal=read(A/'seal.json');bm=read(B/'completion_manifest.json')['files']
    def check(p,expected):assert hashlib.sha256(p.read_bytes()).hexdigest()==expected,('source conflict',p)
    for case in cases:
        js=[j for j in order if j['case']==case and j['method']=='PPCPP'];outs=[read(A/'outputs'/(j['id']+'.json')) for j in js];c=read(A/js[0]['input']);check(A/js[0]['input'],js[0]['input_sha256']);routes=[o['result']['raw']['route'] for o in outs];traces=[o['result']['raw']['trace'] for o in outs];assert len(js)==3 and routes[0]==routes[1]==routes[2] and traces[0]==traces[1]==traces[2]
        for o in outs:
            for p,v in o['imports'].items():assert seal[p]==v
        refs=[]
        for j in order:
            if j['case']==case and j['method']=='P2_MULTI':
                f=A/'outputs'/(j['id']+'.json');o=read(f);p=o['result']['raw']['route'];legal=bool(p) and p[0]==c['current'] and p[-1]==c['base'] and ps(p)<=ps(c['free']) and ps(c['targets'])-ps(c['covered'])<=ps(p) and len(p)-1<=c['distance_budget'] and all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(p,p[1:]));refs.append(dict(source=str(f),steps=len(p)-1,legal=legal))
        rows.append(inventory(c,outs[0]['result']['raw'],str(A/'outputs'/(js[0]['id']+'.json')),str(A/js[0]['input']),'54_states',case,refs,dict(seeds=[j['seed'] for j in js],routes_equal=True,traces_equal=True,outputs=[str(A/'outputs'/(j['id']+'.json')) for j in js])))
    for wid in read(B/'worlds.json'):
        s=read(B/'sessions'/(wid+'_PPCPP.json'))['sessions']['PPCPP'];req=s['requests'][-1];slot=next(x for x in read(B/'call_slots.json') if x['session']==wid+'_PPCPP' and x['tick']==req['tick']);f=B/'outputs'/(slot['id']+'.json');check(f,bm[str(f.relative_to(B))]);o=read(f);assert req['response']['route']==o['entry']['native_return']['raw']['route'];rows.append(inventory(req['input'],o['entry']['native_return']['raw'],str(f),str(B/o['job']['input']),'6_last_responses',wid,[],dict(seed=o['job']['seed'],note='one last-response input, not whole session')))
    save('60份保存结构全表.json',rows)
    summaries=[]
    for batch in ('54_states','6_last_responses'):
        for rel in sorted({r['relation'] for r in rows if r['batch']==batch}):
            group=[r for r in rows if r['batch']==batch and r['relation']==rel];summaries.append(dict(batch=batch,relation=rel,records=len(group),with_closed_intervals=sum(bool(r['closed_intervals']) for r in group),with_zero_exclusive_interval=sum(any(not a['exclusive_interior_required'] for a in r['closed_intervals']) for r in group),with_non_target=sum(r['counts'].get('non_target',0)>0 for r in group),all_case_names=[r['case'] for r in group]))
    save('分批正反结构汇总.json',summaries)
    paths=['range_p2_engine_20261015.py','range_interface_probe_20261015.py','PPCPP局部P2混合开发诊断_v0.1_20261020/hybrid.py','PPCPP首次恢复完整试走_v0.1_20261020/rollout.py','PPCPP恢复时机对照_v0.1_20261020/rollout.py','PPCPP两窗口结构候选_v0.1_20261020/rollout.py','PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/candidate.py','PPCPP四方向接口适配验收_v0.1_20261020/entry.py','基线复现准备_20261019/独立版_v0.2/ppcpp.py'];frozen=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source';files=[R/p for p in paths]+[frozen/n for n in ('p2_search_audit.py','model.py','planners.py')];anchors=[]
    for p in files:
        text=p.read_text(encoding='utf8');sources[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();anchors.append(dict(path=str(p),sha256=sources[str(p)],numbered_source=[f'{i}: {t}' for i,t in enumerate(text.splitlines(),1)]))
    save('旧机制源码逐行证据.json',anchors);save('来源hash.json',sources);save('零调用账.json',dict(planning=0,core=0,candidate_solves=0,path_search=0,coverage_exact=0,new_routes=0,route_edits=0,new_worlds=0,simulated_closed_loops=0,old_verify_runs=0,algorithm_modules_imported=0));print(json.dumps(summaries,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
