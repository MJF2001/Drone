"""Endpoint-distance lower bounds only. No route or geometry engine imported."""
from pathlib import Path
from fractions import Fraction
from math import isqrt
from collections import Counter,defaultdict
import hashlib,json,csv,sys
H=Path(__file__).resolve().parent;R=H.parent;A=R/'任意方向直达收益结构只读归因_v0.1_20261022';B=R/'任意方向合法直达有限诊断_v0.1_20261022';S=10**60
sources={}
def guard():
    class Block:
        def find_spec(self,name,path=None,target=None):
            if name.split('.')[0] in {'geometry','audit_geometry','engine','runtime','planners','ppcpp','heapq','_heapq'}:raise RuntimeError('forbidden module '+name)
    sys.meta_path.insert(0,Block())
    def profile(f,event,arg):
        if event=='call' and f.f_code.co_name in {'legal','hit','process','solve','audit_one','line_of_sight','run_world','run_payload'}:raise RuntimeError('forbidden planning/geometry call')
    sys.setprofile(profile)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    p=Path(p).resolve();sources[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(n,v):
    with (H/n).open('x',encoding='utf8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def fmt(t):return ('-' if t<0 else '')+str(abs(t)//S)+'.'+str(abs(t)%S).zfill(60)
def interval(v):return [fmt(v[0]),fmt(v[1])]
def dist2(a,b):return sum((x-y)**2 for x,y in zip(a,b))
def bracket(q):
    b=isqrt(q*S*S);return [b,b if b*b==q*S*S else b+1]
def add(xs):return [sum(x[i] for x in xs) for i in (0,1)]
def forward_collinear(points):
    a,b=points[0],points[-1];dx,dy=b[0]-a[0],b[1]-a[1];q=dx*dx+dy*dy
    if q==0:return all(p==a for p in points)
    prev=-1
    for p in points:
        x,y=p[0]-a[0],p[1]-a[1];t=x*dx+y*dy
        if x*dy-y*dx!=0 or not prev<=t<=q:return False
        prev=t
    return True
def physical(c):
    return {**{k:sorted(map(tuple,c[f])) for k,f in [('F','free'),('P','published_targets'),('H','covered'),('T','targets'),('D','deferred_targets')]},**{k:c[k] for k in ('current','previous','base','distance_budget')}}
def main():
    guard();mf=read(A/'completion_manifest.json')['files']
    for p,v in mf.items():f=A/p;assert sha(f)==v,('attribution_package_conflict',p);sources[str(f)]=v
    for p,v in read(A/'来源hash.json').items():assert sha(Path(p))==v,('source_conflict',p);sources[p]=v
    draft=R/'任意方向固定采集顺序连接下界核验执行稿_给sol_20261022.md';sources[str(draft)]=sha(draft)
    jobs=read(B/'117固定清单.json');pairs_in=read(B/'57同物理输入配对.json');routes=[];parts_all=[];multi=[];outputs={};inputs={};jobmap={j['id']:j for j in jobs}
    for job in jobs:
        jid=job['id'];payload=read(B/job['payload']);c=payload['input'];o=read(B/'outputs'/(jid+'.json'));audit=read(B/'audits'/(jid+'.json'));assert audit['passed'] and audit['output_sha256']==sha(B/'outputs'/(jid+'.json'));orig=payload['raw']['route'];new=o['vertices'];assert new[0]==c['current'] and new[-1]==c['base'];U=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));assert set(map(tuple,c['targets']))==set(map(tuple,c['published_targets']))&set(map(tuple,c['free']));assert set(map(tuple,c['deferred_targets']))==set(map(tuple,c['published_targets']))-set(map(tuple,c['free']))-set(map(tuple,c['covered']))
        seen=set();first=[]
        for i,p in enumerate(orig):
            t=tuple(p)
            if t in U and t not in seen:first.append({'point':p,'index':i});seen.add(t)
        assert seen==U and first==o['first_original'];actual=o['first_actual'];assert [x['point'] for x in actual]==[x['point'] for x in first] and not o['actual_order_changed'];assert len(actual)==len(U) and set(map(tuple,[x['point'] for x in actual]))==U
        # Arithmetic check of the saved credit witnesses, no fresh center scan.
        for rec in actual:
            if rec['edge']==-1:assert rec['point']==new[0]
            else:
                e=rec['edge'];t=Fraction(rec['t']);assert 0<=t<=1;assert all(Fraction(new[e][k])+t*(new[e+1][k]-new[e][k])==rec['point'][k] for k in (0,1))
        cuts=[0]+[x['index'] for x in first]+[len(orig)-1] if first else [0,len(orig)-1];anchors=[c['current']]+[x['point'] for x in first]+[c['base']] if first else [c['current'],c['base']];assert len(o['parts'])==len(anchors)-1;pr=[];lq=Counter();bq=Counter();edge_cursor=0
        for k,p in enumerate(o['parts']):
            assert [p['left'],p['right']]==cuts[k:k+2];assert p['edge_start']==edge_cursor;edge_cursor=p['edge_end'];es=o['edges'][p['edge_start']:p['edge_end']];points=[anchors[k]]+[e['b'] for e in es];assert points[-1]==anchors[k+1] and (not es or es[0]['a']==anchors[k]);assert points==new[p['edge_start']:p['edge_end']+1]
            q=dist2(anchors[k],anchors[k+1]);qs=[dist2(e['a'],e['b']) for e in es];Lb=add([bracket(z) for z in qs]);Bb=bracket(q);raw_gap=[Lb[0]-Bb[1],Lb[1]-Bb[0]];collinear=forward_collinear(points);gap=[0,0] if collinear else [max(0,raw_gap[0]),max(0,raw_gap[1])]
            assert Fraction(p['new_interval'][0])<=Fraction(Lb[0],S)<=Fraction(Lb[1],S)<=Fraction(p['new_interval'][1]);bq[q]+=1;lq.update(qs)
            row={'id':jid,'part':k,'kind':p['kind'],'original_left':p['left'],'original_right':p['right'],'anchor_a':anchors[k],'anchor_b':anchors[k+1],'endpoint_squared_distance':q,'output_edge_start':p['edge_start'],'output_edge_end':p['edge_end'],'saved_output_vertices':points,'saved_edge_squared_lengths':qs,'output_edges':len(es),'nonzero_output_edges':sum(z>0 for z in qs),'B_ticks':Bb,'B_interval':interval(Bb),'L_ticks':Lb,'L_interval':interval(Lb),'raw_L_minus_B_ticks':raw_gap,'improvement_cap_ticks':gap,'improvement_cap_interval':interval(gap),'exact_equal_by_collinear_forward':collinear,'exact_equal_evidence':'Saved points on chord, ordered monotonically along its nonnegative dot coordinate (or all identical for zero chord). No geometry query.' if collinear else None}
            pr.append(row);parts_all.append(row)
            if len(es)>1:multi.append(row)
        assert edge_cursor==len(o['edges']);LB=add([p['L_ticks'] for p in pr]);BB=add([p['B_ticks'] for p in pr]);cap=add([p['improvement_cap_ticks'] for p in pr]);exact=all(p['exact_equal_by_collinear_forward'] for p in pr);E=c['distance_budget'];assert Fraction(LB[1],S)<=Fraction(str(E)) and Fraction(o['Lshortcut_interval'][0])<=Fraction(LB[0],S)<=Fraction(LB[1],S)<=Fraction(o['Lshortcut_interval'][1])
        cohort='54_states' if job['batch']=='54_states' else ('six_paired3' if job['case'] in ('L_S','L_M','T_M') else 'six_unpaired3')
        row={'id':jid,'case':job['case'],'batch':job['batch'],'cohort':cohort,'method':job['method'],'anchor_sequence_definition_only':anchors,'actual_first_service_sequence':[x['point'] for x in actual],'actual_sequence_equals_original':True,'tasks_remaining':len(U),'distance_budget':E,'resource_proof':'Saved L <= original remaining E; B is only a lower bound on routes with exactly these endpoints and actual service order. No budget reset.','parts':len(pr),'zero_edge_parts':sum(p['output_edges']==0 for p in pr),'single_edge_parts':sum(p['output_edges']==1 for p in pr),'multi_edge_parts':sum(p['output_edges']>1 for p in pr),'nonzero_chord_parts':sum(p['endpoint_squared_distance']>0 for p in pr),'single_nonzero_edge_parts':sum(p['nonzero_output_edges']==1 for p in pr),'B_ticks':BB,'B_interval':interval(BB),'L_ticks':LB,'L_interval':interval(LB),'improvement_cap_ticks':cap,'improvement_cap_interval':interval(cap),'fixed_actual_order_optimal_certificate':exact,'certificate_basis':'Existing legal and credit-valid route attains the anchor chord-sum lower bound in every part, by exact forward collinearity.' if exact else 'Not certified: B may be unattainable; cap is only an upper bound on further improvement.','anchor_squared_length_multiset':{str(q):v for q,v in sorted(bq.items())},'output_squared_length_multiset':{str(q):v for q,v in sorted(lq.items())}}
        routes.append(row);outputs[jid]=row;inputs[jid]=c
    pairs=[]
    for old in pairs_in:
        prefix=old['batch']+'__'+old['case']+'__';a=outputs[prefix+'PPCPP'];b=outputs[prefix+'P2_MULTI'];same_physical=physical(inputs[a['id']])==physical(inputs[b['id']]);assert same_physical;different=a['actual_first_service_sequence']!=b['actual_first_service_sequence'];gap=[a['B_ticks'][0]-b['L_ticks'][1],a['B_ticks'][1]-b['L_ticks'][0]];exact_equal=a['anchor_squared_length_multiset']==b['output_squared_length_multiset'];sign='positive' if gap[0]>0 else ('nonpositive' if gap[1]<=0 or exact_equal else 'uncertain')
        if sign=='positive':assert different,('contradiction_same_order_but_B_exceeds_legal_P2',old['case'])
        pairs.append({'batch':old['batch'],'case':old['case'],'PPCPP_id':a['id'],'P2_id':b['id'],'same_physical_input':same_physical,'actual_sequences_different':different,'B_PPCPP_minus_saved_L_P2_ticks':gap,'B_PPCPP_minus_saved_L_P2_interval':interval(gap),'sign':sign,'exact_equal_by_squared_multiset':exact_equal,'strict_order_restriction_certificate':sign=='positive' and different,'meaning':'Every route retaining this PPCPP actual first-service order is strictly longer than the existing saved P2 route.' if sign=='positive' else 'This lower-bound comparison alone does not exclude reaching the P2 reference under this PPCPP order.','PPCPP_further_improvement_cap_ticks':a['improvement_cap_ticks'],'PPCPP_fixed_order_optimal':a['fixed_actual_order_optimal_certificate']})
    summary=[]
    for cohort in ('54_states','six_paired3','six_unpaired3'):
        for method in ('PPCPP','P2_MULTI'):
            rs=[r for r in routes if r['cohort']==cohort and r['method']==method]
            if not rs:continue
            cap=add([r['improvement_cap_ticks'] for r in rs]);summary.append({'cohort':cohort,'method':method,'routes':len(rs),'parts':sum(r['parts'] for r in rs),'single_edge_parts':sum(r['single_edge_parts'] for r in rs),'multi_edge_parts':sum(r['multi_edge_parts'] for r in rs),'fixed_order_optimal_routes':sum(r['fixed_actual_order_optimal_certificate'] for r in rs),'B_ticks':add([r['B_ticks'] for r in rs]),'L_ticks':add([r['L_ticks'] for r in rs]),'improvement_cap_ticks':cap,'improvement_cap_interval':interval(cap)})
    dump('117路线固定顺序下界.json',routes);dump('全部锚点区间下界.json',parts_all);dump('多段区间全量表.json',multi);dump('57配对顺序限制证书.json',pairs);dump('分批核验汇总.json',summary);dump('来源hash.json',sources)
    dump('零求解调用账.json',{'new_planning':0,'core':0,'graph_search':0,'visibility_queries':0,'postprocessing':0,'candidate_generation':0,'new_routes':0,'counterfactual_routes':0,'production_geometry_imports':0,'old_verify_runs':0,'saved_routes':117,'saved_pairings':57,'anchor_distance_lower_bound_arithmetic':len(parts_all),'note':'Only exact integer/rational distance bounds on existing anchor pairs and saved edges; anchors are definition data, not new path outputs.'})
    with (H/'117路线固定顺序下界.csv').open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['id','cohort','B_lower','B_upper','L_lower','L_upper','further_improvement_upper','parts','single_edge_parts','multi_edge_parts','fixed_order_optimal'])
        for r in routes:w.writerow([r['id'],r['cohort'],*r['B_interval'],*r['L_interval'],r['improvement_cap_interval'][1],r['parts'],r['single_edge_parts'],r['multi_edge_parts'],r['fixed_actual_order_optimal_certificate']])
    print(json.dumps({'routes':len(routes),'anchor_parts':len(parts_all),'multi_parts':len(multi),'pairs':len(pairs),'strict_certificates':{b:dict(Counter(p['sign'] for p in pairs if p['batch']==b)) for b in ('54_states','6_last_responses')},'new_queries':0},ensure_ascii=False))
if __name__=='__main__':main()
