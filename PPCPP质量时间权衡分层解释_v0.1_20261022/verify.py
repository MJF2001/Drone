"""Independent reconstruction from saved raw pipelines; no analysis import/LOS."""
from pathlib import Path
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
from fractions import Fraction as F
from collections import Counter
import json,hashlib,statistics
H=Path(__file__).resolve().parent;R=H.parent;B=R/'PPCPP直达质量时间开发比较_v0.1_20261022';OLD=R/'任意方向合法直达有限诊断_v0.1_20261022'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):assert abs(a-b)<=1e-9*max(1,abs(a),abs(b)),(a,b)
def bound(v):
    with localcontext() as cx:
        cx.prec=80;lo=hi=Decimal(0)
        for a,b in zip(v,v[1:]):
            q=(b[0]-a[0])**2+(b[1]-a[1])**2;r=Decimal(q).sqrt()
            if r==r.to_integral_value() and r*r==q:l=u=r
            else:l=r.next_minus();u=r.next_plus()
            cx.rounding=ROUND_FLOOR;lo+=l
            cx.rounding=ROUND_CEILING;hi+=u
        return F(lo),F(hi)
def equal(a,b):
    def bag(v):return Counter((b[0]-a[0])**2+(b[1]-a[1])**2 for a,b in zip(v,v[1:]))
    return bag(a)==bag(b)
def quad(sign,t):return 'distance_uncertain' if sign=='uncertain' else ('time_equal' if t==0 else ('faster' if t>0 else 'slower')+('_longer' if sign=='longer' else '_not_longer'))
def main():
    for p,h in read(H/'来源hash.json').items():assert sha(Path(p))==h,p
    for p,h in read(OLD/'来源hash.json').items():assert sha(Path(p))==h,p
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    pairs=read(H/'162重建配对.json');states=read(H/'54重建状态均值.json');assert len(pairs)==162 and len(states)==54;actual={}
    for p in pairs:
        b=read(B/'outputs'/(p['B_id']+'.json'));c=read(B/'outputs'/(p['C_id']+'.json'));assert b['audit_payload']['input']==c['audit_payload']['input'];assert b['job']['seed']==c['job']['seed']==p['seed'];assert c['native']['raw']['status']==p['P2_status']=='finished';lb,lc=bound(b['post']['vertices']),bound(c['post']['vertices'])
        for label,v in [('B_length_interval',lb),('C_length_interval',lc)]:saved=list(map(F,p[label]));assert saved[0]<=v[0]<=v[1]<=saved[1]
        dif=[lb[0]-lc[1],lb[1]-lc[0]];rat=[lb[0]/lc[1]-1,lb[1]/lc[0]-1];assert F(p['extra_distance_interval'][0])<=dif[0]<=dif[1]<=F(p['extra_distance_interval'][1]);assert F(p['extra_ratio_interval'][0])<=rat[0]<=rat[1]<=F(p['extra_ratio_interval'][1]);eq=equal(b['post']['vertices'],c['post']['vertices']);sign='longer' if dif[0]>0 else ('shorter' if dif[1]<0 else ('equal' if eq else 'uncertain'));assert sign==p['distance_sign']
        close(p['extra_ratio'],float((rat[0]+rat[1])/2));close(p['extra_distance'],float((dif[0]+dif[1])/2));close(p['B_length'],float((lb[0]+lb[1])/2));close(p['C_length'],float((lc[0]+lc[1])/2));assert p['A_length']==b['post']['L4'] and p['C0_length']==c['post']['L4'];close(p['B_post_ms'],1000*b['timing']['post_increment_seconds'])
        tb,tc=b['timing']['pipeline_seconds'],c['timing']['pipeline_seconds'];close(p['saved_seconds'],tc-tb);close(p['speed_ratio'],tc/tb);close(p['saved_time_ratio'],1-tb/tc);assert p['quadrant']==quad(sign,tc-tb)
        for x in (b,c):t=x['timing'];close(t['pipeline_seconds'],t['original_seconds']+t['post_increment_seconds']);assert t['original_seconds']>=x['native']['entry_seconds'] and t['pipeline_seconds']>=t['original_seconds'];assert x['native']['raw']['route'][0]==x['post']['vertices'][0] and x['audit']['passed']
        actual[(p['case'],p['seed'])]=(dif,rat,eq)
    for s in states:
        ps=[p for p in pairs if p['case']==s['case']];assert len(ps)==3 and s['case'].split('_')[:3]==[s['scale'],s['shape'],s['event']];lo=sum(actual[(p['case'],p['seed'])][0][0] for p in ps)/3;hi=sum(actual[(p['case'],p['seed'])][0][1] for p in ps)/3;sg='longer' if lo>0 else ('shorter' if hi<0 else ('equal' if all(actual[(p['case'],p['seed'])][2] for p in ps) else 'uncertain'));assert sg==s['distance_sign']
        for k in ('extra_distance','extra_ratio','saved_seconds','B_post_ms','B_seconds','C_seconds'):close(s[k],sum(p[k] for p in ps)/3)
        assert s['quadrant']==quad(sg,s['saved_seconds'])
    for row in read(H/'原标签完整分层.json'):
        sr=states if row['dimension']=='all' else [s for s in states if s[row['dimension']]==row['label']];pp=[p for p in pairs if p['case'] in {s['case'] for s in sr}];assert len(sr)==row['states'] and len(pp)==row['seed_pairs'];close(row['state_equal_extra_ratio'],statistics.mean(s['extra_ratio'] for s in sr));close(row['total_length_weighted_extra_ratio'],sum(p['B_length'] for p in pp)/sum(p['C_length'] for p in pp)-1);close(row['saved_seconds_mean_state'],statistics.mean(s['saved_seconds'] for s in sr));close(row['saved_seconds_median_state'],statistics.median(s['saved_seconds'] for s in sr));assert row['time_negative_states']==sum(s['saved_seconds']<0 for s in sr) and row['time_positive_pairs']==sum(p['saved_seconds']>0 for p in pp);assert row['distance_sign_states']==dict(Counter(s['distance_sign'] for s in sr));close(row['worst_pair_extra_ratio'],max(p['extra_ratio'] for p in pp))
    oldjobs=read(OLD/'117固定清单.json')
    for r in read(H/'54新旧来源核对.json'):
        for m in ('PPCPP','P2_MULTI'):
            j=next(j for j in oldjobs if j['case']==r['case'] and j['method']==m and j['batch']=='54_states');oldraw=read(Path(j['source_output']))['result']['raw'];new=read(B/'outputs'/('formal__'+r['case']+'__0__'+m+'.json'));assert sha(Path(j['source_input']))==sha(B/'inputs'/(r['case']+'.json'));assert r[m+'_original_route_same_rep0']==(oldraw['route']==new['native']['raw']['route'])
    ex=read(H/'极值与全部seed证据.json')
    specs={'max_state_extra_ratio':('extra_ratio',True),'max_state_extra_distance':('extra_distance',True),'max_state_time_saved':('saved_seconds',True),'min_state_time_saved':('saved_seconds',False)}
    for e in ex:
        if e['criterion'] not in specs:continue
        k,rev=specs[e['criterion']];best=sorted(states,key=lambda s:((-s[k] if rev else s[k]),s['case']))[0];assert best['case']==e['case'] and len(e['all_three_seeds'])==3;close(e['value'],best[k])
    q=read(H/'四象限.json');assert q['state_counts']==dict(Counter(s['quadrant'] for s in states)) and q['pair_counts']==dict(Counter(p['quadrant'] for p in pairs));assert all(v==0 for v in read(H/'零新增求解账.json').values());print(json.dumps({'passed':True,'raw_pairs':162,'states':54,'strata':10,'new_planning_postprocessing_geometry':0,'state_quadrants':q['state_counts']},ensure_ascii=False))
    concentration=read(H/'时间节省集中度.json');ordered=sorted(states,key=lambda s:(-s['saved_seconds'],s['case']));den=sum(s['saved_seconds'] for s in states)
    for n in (1,3,5):assert concentration['top'+str(n)]['cases']==[s['case'] for s in ordered[:n]];close(concentration['top'+str(n)]['share_of_signed_total_time_saved'],sum(s['saved_seconds'] for s in ordered[:n])/den)
    for size,value in concentration['size_shares'].items():close(value,sum(s['saved_seconds'] for s in states if s['scale']==size)/den)
    case='medium_L_straight_p70';raws=[read(B/'outputs'/('formal__'+case+'__'+str(rep)+'__PPCPP.json'))['native']['raw']['route'] for rep in range(3)];assert raws[0]==raws[1]==raws[2]
if __name__=='__main__':main()
