"""Saved-edge arithmetic only. No LOS, counterfactual route, or planner call."""
from pathlib import Path
from math import isqrt
from fractions import Fraction
from collections import Counter,defaultdict
import json,hashlib,csv,sys
H=Path(__file__).resolve().parent;R=H.parent;B=R/'任意方向合法直达有限诊断_v0.1_20261022';S=10**60
sources={}
def guard():
    class Block:
        def find_spec(self,name,path=None,target=None):
            if name.split('.')[0] in {'geometry','audit_geometry','engine','runtime','planners','ppcpp','heapq','_heapq'}:raise RuntimeError('forbidden production/geometry import: '+name)
    sys.meta_path.insert(0,Block())
    def profile(frame,event,arg):
        if event=='call' and frame.f_code.co_name in {'legal','hit','process','audit_one','solve','line_of_sight','lineofsight','run_world','run_payload'}:raise RuntimeError('forbidden query/route call')
    sys.setprofile(profile)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    p=Path(p).resolve();sources[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(n,v):
    with (H/n).open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def fmt(t):return ('-' if t<0 else '')+str(abs(t)//S)+'.'+str(abs(t)%S).zfill(60)
def decint(t):return [fmt(t[0]),fmt(t[1])]
def blank():return {'edges':0,'old':0,'m':0,'d':[0,0],'excess':0,'metric_gap':[0,0],'gain':[0,0],'zero_gain_edges':0,'positive_gain_edges':0,'uncertain_gain_edges':0}
def accumulate(out,e):
    out['edges']+=1;out['old']+=e['l'];out['m']+=e['m'];out['excess']+=e['excess_ticks']
    for key,field in (('d','d_ticks'),('metric_gap','metric_gap_ticks'),('gain','gain_ticks')):
        for i in (0,1):out[key][i]+=e[field][i]
    out['zero_gain_edges']+=e['gain_ticks']==[0,0];out['positive_gain_edges']+=e['gain_ticks'][0]>0;out['uncertain_gain_edges']+=e['gain_ticks'][0]<=0<e['gain_ticks'][1]
def packed(a):return {**a,'d_interval':decint(a['d']),'gain_interval':decint(a['gain']),'excess_interval':decint([a['excess']]*2),'metric_gap_interval':decint(a['metric_gap'])}
def main():
    guard()
    mf=read(B/'completion_manifest.json')['files']
    for p,h in mf.items():
        f=B/p;assert sha(f)==h,('old_package_hash_conflict',p);sources[str(f)]=h
    for p,h in read(B/'来源hash.json').items():assert sha(Path(p))==h,('old_source_hash_conflict',p);sources[p]=h
    draft=R/'任意方向直达结果负责人审核与收益归因执行稿_给sol_20261022.md';sources[str(draft)]=sha(draft)
    meta_path=R/'连续事件六世界开发比较_v0.1_20261022/world_metadata.json';meta=read(meta_path);mm=read(meta_path.parent/'completion_manifest.json')['files'];assert mm['world_metadata.json']==sha(meta_path)
    jobs=read(B/'117固定清单.json');oldpairs=read(B/'57同物理输入配对.json');assert len(jobs)==117 and len(oldpairs)==57
    route_rows=[];edge_rows=[];grouped=defaultdict(blank);routes={};rawout={};multisets={}
    for job in jobs:
        payload=read(B/job['payload']);r=read(B/'outputs'/(job['id']+'.json'));audit=read(B/'audits'/(job['id']+'.json'));assert audit['passed'] and audit['output_sha256']==sources[str((B/'outputs'/(job['id']+'.json')).resolve())]
        orig=payload['raw']['route'];edges=r['edges'];n=len(orig)-1;assert n==r['L4']<=payload['input']['distance_budget'];assert len(r['vertices'])==len(edges)+1
        if job['batch']=='54_states':
            scale,shape,event,progress=job['case'].split('_');cohort='54_states';labels={'scale':scale,'shape':shape,'event':event,'progress':progress,'source':'pre-existing case ID'}
        else:
            z=meta[job['case']];cohort='six_paired3' if job['case'] in ('L_S','L_M','T_M') else 'six_unpaired3';labels={'scale':z['scale'],'shape':z['shape'],'event':None,'progress':None,'source':str(meta_path),'event_note':'Saved last response in the fixed six-world event sequence; no single-event class in original metadata, not relabelled as obstacle/extension only.'}
        total=blank();parts=[blank() for _ in r['parts']];kinds=defaultdict(blank);classes=defaultdict(blank);squares=Counter();cursor=0
        for k,e in enumerate(edges):
            left,right=e['left'],e['right'];assert left==cursor and left<right<=n;cursor=right;a,b=e['a'],e['b'];assert a==orig[left]==r['vertices'][k] and b==orig[right]==r['vertices'][k+1]
            dx,dy=b[0]-a[0],b[1]-a[1];m=abs(dx)+abs(dy);q=dx*dx+dy*dy;l=right-left;assert l>=m
            # A rational envelope of the length of THIS saved output edge only.
            # Endpoints/LOS and candidate construction are never recomputed.
            root=isqrt(q*S*S);upper=root if root*root==q*S*S else root+1
            kind=e['kind'];cls='zero_displacement' if m==0 else ('axis' if dx==0 or dy==0 else 'diagonal');x={'id':job['id'],'edge':k,'part':e['part'],'kind':kind,'class':cls,'left':left,'right':right,'a':a,'b':b,'dx':dx,'dy':dy,'l':l,'m':m,'squared_length':q,'d_ticks':[root,upper],'d_interval':decint([root,upper]),'excess_ticks':(l-m)*S,'excess_interval':decint([(l-m)*S]*2),'metric_gap_ticks':[m*S-upper,m*S-root],'metric_gap_interval':decint([m*S-upper,m*S-root]),'gain_ticks':[l*S-upper,l*S-root],'gain_interval':decint([l*S-upper,l*S-root])}
            assert x['gain_ticks']==[x['excess_ticks']+z for z in x['metric_gap_ticks']];assert min(x['metric_gap_ticks'])>=0
            for a0 in (total,parts[e['part']],kinds[kind],classes[cls],grouped[(cohort,job['method'],'all','all')],grouped[(cohort,job['method'],'kind',kind)],grouped[(cohort,job['method'],'class',cls)],grouped[(cohort,job['method'],'cross',kind+' x '+cls)]):accumulate(a0,x)
            for axis in ('scale','shape','event','progress'):
                if labels[axis] is not None:accumulate(grouped[(cohort,job['method'],axis,labels[axis])],x)
            edge_rows.append(x);squares[q]+=1
        assert cursor==n and total['old']==n
        assert Fraction(r['Lshortcut_interval'][0])<=Fraction(total['d'][0],S)<=Fraction(total['d'][1],S)<=Fraction(r['Lshortcut_interval'][1])
        for p,a0 in zip(r['parts'],parts):
            assert a0['old']==p['L4'];assert Fraction(p['new_interval'][0])<=Fraction(a0['d'][0],S)<=Fraction(a0['d'][1],S)<=Fraction(p['new_interval'][1])
        row={'id':job['id'],'case':job['case'],'batch':job['batch'],'cohort':cohort,'method':job['method'],'labels':labels,'total':packed(total),'parts':[{'kind':p['kind'],'left':p['left'],'right':p['right'],**packed(a0)} for p,a0 in zip(r['parts'],parts)],'by_kind':{k:packed(v) for k,v in kinds.items()},'by_class':{k:packed(v) for k,v in classes.items()},'first_actual_order_changed_saved':r['actual_order_changed'],'squared_length_multiset':{str(k):v for k,v in sorted(squares.items())}}
        route_rows.append(row);routes[job['id']]=row;rawout[job['id']]=r;multisets[job['id']]=squares
    groups=[]
    for (cohort,method,dimension,label),v in sorted(grouped.items()):
        n=sum(r['cohort']==cohort and r['method']==method and (dimension not in ('scale','shape','event','progress') or r['labels'][dimension]==label) for r in route_rows)
        groups.append({'cohort':cohort,'method':method,'dimension':dimension,'label':label,'route_denominator':n,**packed(v)})
    pairs=[]
    for p in oldpairs:
        prefix=p['batch']+'__'+p['case']+'__';a=routes[prefix+'PPCPP'];b=routes[prefix+'P2_MULTI'];same=multisets[a['id']]==multisets[b['id']];parts=[]
        def diff(aa,bb):return [aa['d'][0]-bb['d'][1],aa['d'][1]-bb['d'][0]]
        for kind in ('start_to_first','between_first_services','last_to_base','empty_task_to_base'):
            aa=a['by_kind'].get(kind,packed(blank()));bb=b['by_kind'].get(kind,packed(blank()));d=diff(aa,bb);parts.append({'kind':kind,'PPCPP_old':aa['old'],'P2_old':bb['old'],'old_difference':aa['old']-bb['old'],'new_difference_ticks':d,'new_difference_interval':decint(d),'PPCPP_new_ticks':aa['d'],'P2_new_ticks':bb['d']})
        d=diff(a['total'],b['total']);assert [sum(x['new_difference_ticks'][i] for x in parts) for i in (0,1)]==d
        sign='positive' if d[0]>0 else ('negative' if d[1]<0 else ('zero' if d==[0,0] else 'uncertain'))
        certificate=None
        if p['case']=='large_I_obstacle_p70' and p['batch']=='54_states' and same:certificate={'claim':'exact equal total length','basis':'Identical multiset of saved output squared edge lengths, including multiplicities and zero-length edges. Pair corresponding square-root terms; no generic radical simplification or new geometry.','squared_length_multiset':a['squared_length_multiset']}
        assert p['certified_sign']=='uncertain' or p['certified_sign']==sign
        pairs.append({'batch':p['batch'],'case':p['case'],'PPCPP_id':a['id'],'P2_id':b['id'],'parts':parts,'old_total_difference':a['total']['old']-b['total']['old'],'new_total_difference_ticks':d,'new_total_difference_interval':decint(d),'prior_sign':p['certified_sign'],'interval_sign':sign,'same_squared_length_multiset':same,'additional_exact_equal_certificate':certificate,'old_original_difference':p['original_PPCPP_minus_P2'],'saved_prior_difference_interval':p['post_difference_interval']})
    # Explanatory selection: maximize registered category saving, exact/rational
    # interval ordering; ties only by ID. No change to experimental membership.
    def choose(candidates,score):
        assert candidates
        best=sorted(candidates,key=lambda r:(-score(r)[0],r['id']))[0];best_score=score(best)
        for r in candidates:
            other=score(r)
            assert r['id']==best['id'] or best_score[0]>other[1] or (best_score==other and best['id']<=r['id']),('example_selection_unresolved',best['id'],r['id'])
        return best,best_score
    def gain(r,kind):return r['by_kind'].get(kind,blank())['gain']
    def nond(r):return [sum(r['by_class'].get(k,blank())['gain'][i] for k in ('axis','zero_displacement')) for i in (0,1)]
    lag_ids={p['PPCPP_id'] for p in pairs if p['interval_sign']=='positive'}
    categories=[('main_return',[r for r in route_rows if gain(r,'last_to_base')[0]>0 and gain(r,'last_to_base')[0]>=sum(v['gain'][1] for k,v in r['by_kind'].items() if k!='last_to_base')],lambda r:gain(r,'last_to_base')),
      ('between_service',[r for r in route_rows if gain(r,'between_first_services')[0]>0],lambda r:gain(r,'between_first_services')),
      ('axis_or_zero',[r for r in route_rows if nond(r)[0]>0],nond),
      ('still_behind',[r for r in route_rows if r['id'] in lag_ids],lambda r:r['total']['gain'])]
    examples=[]
    for label,candidates,fn in categories:
        if candidates:
            best,sc=choose(candidates,fn);examples.append({'category':label,'id':best['id'],'selection':'Maximum saving within stated category; exact interval-separated ranking, ties by ID. Explanatory selection, not representative sampling.','candidate_routes':len(candidates),'selection_score_ticks':sc,'selection_score_interval':decint(sc)})
        else:examples.append({'category':label,'id':None,'reason':'No saved route in this category; no replacement or synthetic path.'})
    dump('逐边区间分解.json',edge_rows);dump('117全量区间分解.json',route_rows);dump('分层交叉汇总.json',groups);dump('57配对成本位置与等长证据.json',pairs);dump('解释实例固定选择.json',examples)
    with (H/'117全量区间分解.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['id','cohort','old','new_lower','new_upper','gain_lower','gain_upper','l_minus_m_exact','m_minus_d_lower','m_minus_d_upper'])
        for r in route_rows:a=r['total'];w.writerow([r['id'],r['cohort'],a['old'],*a['d_interval'],*a['gain_interval'],fmt(a['excess']),*a['metric_gap_interval']])
    dump('来源hash.json',sources);dump('零新增调用账.json',{'planning_entries':0,'core':0,'graph_search':0,'visibility_queries':0,'shortcut_calls':0,'candidate_generation':0,'new_routes':0,'counterfactual_routes':0,'continuous_closed_loop':0,'production_imports':0,'old_verify_runs':0,'existing_routes_read':117,'existing_output_edges_arithmetically_decomposed':len(edge_rows),'integer_length_enclosures':'Only saved actual edges; integer square bounds on scale10^60, not a geometry/LOS call.','prior_independent_geometry_calls_8112':'historical saved evidence only, not repeated this round'})
    print(json.dumps({'routes':len(route_rows),'saved_edges':len(edge_rows),'pairings':len(pairs),'new_queries':0,'uncertain_pair_equal_certificate':next(p['additional_exact_equal_certificate'] is not None for p in pairs if p['case']=='large_I_obstacle_p70')},ensure_ascii=False))
if __name__=='__main__':main()
