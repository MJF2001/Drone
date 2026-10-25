from pathlib import Path
from fractions import Fraction as F
from math import isqrt
from collections import Counter,defaultdict
import json,hashlib,statistics,csv,sys
H=Path(__file__).resolve().parent;R=H.parent;B=R/'PPCPP直达质量时间开发比较_v0.1_20261022';OLD=R/'任意方向合法直达有限诊断_v0.1_20261022';S=10**60;sources={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    p=Path(p).resolve();sources[str(p)]=sha(p);return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def guard():
    class Block:
        def find_spec(self,name,path=None,target=None):
            if name.split('.')[0] in {'runtime','engine','geometry','audit_geometry','planners','candidate','heapq'}:raise RuntimeError('forbidden import')
    sys.meta_path.insert(0,Block())
def qs(points):return Counter((a[0]-b[0])**2+(a[1]-b[1])**2 for a,b in zip(points,points[1:]))
def length(points):
    low=high=0
    for q,n in qs(points).items():
        x=isqrt(q*S*S);low+=n*x;high+=n*(x if x*x==q*S*S else x+1)
    return F(low,S),F(high,S)
def sign(a,b,equal=False):return 'longer' if a[0]>b[1] else ('shorter' if a[1]<b[0] else ('equal' if equal else 'uncertain'))
def physical(c):return [sorted(map(tuple,c[k])) for k in ('free','targets','published_targets','covered','deferred_targets')]+[c[k] for k in ('current','previous','base','distance_budget')]
def quad(d,t):
    if d=='uncertain':return 'distance_uncertain'
    if t==0:return 'time_equal'
    return ('faster' if t>0 else 'slower')+('_longer' if d=='longer' else '_not_longer')
def mean(v):return sum(v)/len(v)
def main():
    guard()
    for root in (B,OLD):
        for n,h in read(root/'completion_manifest.json')['files'].items():assert sha(root/n)==h,n;sources[str((root/n).resolve())]=h
    for p,h in read(B/'source_seal.json').items():assert sha(Path(p))==h,p;sources[p]=h
    draft=R/'PPCPP质量时间权衡负责人审核与分层解释执行稿_给sol_20261022.md';sources[str(draft)]=sha(draft)
    jobs=read(B/'plan.json')['formal'];pairs=[];pipelines={};numerics={}
    for j in jobs:
        x=read(B/'outputs'/(j['id']+'.json'));c=read(B/j['input']);assert x['job']==j and physical(c)==physical(x['audit_payload']['input']);t=x['timing'];assert abs(t['original_seconds']+t['post_increment_seconds']-t['pipeline_seconds'])<1e-10;assert x['native']['raw']['status'] in ('finished','core_complete');assert x['audit']['passed'];d=length(x['post']['vertices']);assert F(x['post']['Lshortcut_interval'][0])<=d[0]<=d[1]<=F(x['post']['Lshortcut_interval'][1]);assert x['post']['L4']==len(x['native']['raw']['route'])-1<=c['distance_budget'];pipelines[(j['case'],j['seed'],j['method'])]=x;numerics[j['id']]=d
    for case,seed in sorted({(j['case'],j['seed']) for j in jobs}):
        b=pipelines[(case,seed,'PPCPP')];c=pipelines[(case,seed,'P2_MULTI')];assert physical(b['audit_payload']['input'])==physical(c['audit_payload']['input']);lb=numerics[b['job']['id']];lc=numerics[c['job']['id']];dif=(lb[0]-lc[1],lb[1]-lc[0]);rat=(lb[0]/lc[1]-1,lb[1]/lc[0]-1);equal=qs(b['post']['vertices'])==qs(c['post']['vertices']);sg=sign(lb,lc,equal);tb=b['timing']['pipeline_seconds'];tc=c['timing']['pipeline_seconds'];saved=tc-tb
        row={'case':case,'seed':seed,'B_id':b['job']['id'],'C_id':c['job']['id'],'A_length':b['post']['L4'],'C0_length':c['post']['L4'],'B_length_interval':list(map(str,lb)),'C_length_interval':list(map(str,lc)),'B_length':float(mean(lb)),'C_length':float(mean(lc)),'extra_distance_interval':list(map(str,dif)),'extra_ratio_interval':list(map(str,rat)),'extra_distance':float(mean(dif)),'extra_ratio':float(mean(rat)),'exact_equal_by_square_multiset':equal,'distance_sign':sg,'A_seconds':b['timing']['original_seconds'],'B_seconds':tb,'C0_seconds':c['timing']['original_seconds'],'C_seconds':tc,'B_post_ms':1000*b['timing']['post_increment_seconds'],'C_post_ms':1000*c['timing']['post_increment_seconds'],'saved_seconds':saved,'speed_ratio':tc/tb,'saved_time_ratio':1-tb/tc,'quadrant':quad(sg,saved),'P2_status':c['native']['raw']['status']};pairs.append(row)
    states=[]
    for case in sorted({p['case'] for p in pairs}):
        pp=[p for p in pairs if p['case']==case];assert len(pp)==3;dif=[mean([F(p['extra_distance_interval'][i]) for p in pp]) for i in (0,1)];ratio=[mean([F(p['extra_ratio_interval'][i]) for p in pp]) for i in (0,1)];sg='longer' if dif[0]>0 else ('shorter' if dif[1]<0 else ('equal' if all(p['exact_equal_by_square_multiset'] for p in pp) else 'uncertain'));scale,shape,event,progress=case.split('_');row={'case':case,'scale':scale,'shape':shape,'event':event,'progress':progress,'seed_count':3,'extra_distance_interval':list(map(str,dif)),'extra_ratio_interval':list(map(str,ratio)),'distance_sign':sg}
        for k in ('A_length','C0_length','B_length','C_length','extra_distance','extra_ratio','A_seconds','B_seconds','C0_seconds','C_seconds','B_post_ms','C_post_ms','saved_seconds','speed_ratio','saved_time_ratio'):row[k]=mean([p[k] for p in pp])
        row['quadrant']=quad(sg,row['saved_seconds']);states.append(row)
    def stats(sr,dimension,label):
        pp=[p for p in pairs if p['case'] in {s['case'] for s in sr}];return {'dimension':dimension,'label':label,'states':len(sr),'seed_pairs':len(pp),'state_equal_extra_ratio':mean([s['extra_ratio'] for s in sr]),'total_length_weighted_extra_ratio':sum(p['B_length'] for p in pp)/sum(p['C_length'] for p in pp)-1,'saved_seconds_mean_state':mean([s['saved_seconds'] for s in sr]),'saved_seconds_median_state':statistics.median(s['saved_seconds'] for s in sr),'saved_seconds_median_pair':statistics.median(p['saved_seconds'] for p in pp),'B_post_ms_mean_state':mean([s['B_post_ms'] for s in sr]),'B_post_ms_median_pair':statistics.median(p['B_post_ms'] for p in pp),'time_positive_states':sum(s['saved_seconds']>0 for s in sr),'time_negative_states':sum(s['saved_seconds']<0 for s in sr),'time_zero_states':sum(s['saved_seconds']==0 for s in sr),'time_positive_pairs':sum(p['saved_seconds']>0 for p in pp),'time_negative_pairs':sum(p['saved_seconds']<0 for p in pp),'distance_sign_states':dict(Counter(s['distance_sign'] for s in sr)),'worst_state_extra_ratio':max(s['extra_ratio'] for s in sr),'worst_pair_extra_ratio':max(p['extra_ratio'] for p in pp),'saved_seconds_sum_state':sum(s['saved_seconds'] for s in sr)}
    strata=[stats(states,'all','all')]
    for dim in ('scale','shape','event'):
        for label in sorted({s[dim] for s in states}):strata.append(stats([s for s in states if s[dim]==label],dim,label))
    extreme=[]
    for kind,key,reverse in [('max_state_extra_ratio','extra_ratio',True),('max_state_extra_distance','extra_distance',True),('max_state_time_saved','saved_seconds',True),('min_state_time_saved','saved_seconds',False)]:
        r=sorted(states,key=lambda s:((-s[key] if reverse else s[key]),s['case']))[0];extreme.append({'criterion':kind,'case':r['case'],'value':r[key],'state':r,'all_three_seeds':[p for p in pairs if p['case']==r['case']],'selection':'Predefined extreme, ID tie break. Not representative sampling.'})
    p=sorted(pairs,key=lambda p:(-p['extra_ratio'],p['case'],p['seed']))[0];extreme.append({'criterion':'max_single_seed_extra_ratio','case':p['case'],'seed':p['seed'],'value':p['extra_ratio'],'all_three_seeds':[x for x in pairs if x['case']==p['case']]})
    oldjobs=read(OLD/'117固定清单.json');changes=[];oldsigns=[];rep0signs=[]
    for s in states:
        case=s['case'];oj={j['method']:j for j in oldjobs if j['case']==case and j['batch']=='54_states'};old={m:read(OLD/'outputs'/(j['id']+'.json')) for m,j in oj.items()};a=old['PPCPP'];b=old['P2_MULTI'];oldsg=sign(length(a['vertices']),length(b['vertices']),qs(a['vertices'])==qs(b['vertices']));new0=next(p for p in pairs if p['case']==case and p['seed']==20261020);oldsigns.append(oldsg);rep0signs.append(new0['distance_sign']);row={'case':case,'old_rep0_sign':oldsg,'new_rep0_sign':new0['distance_sign'],'new_three_seed_state_sign':s['distance_sign'],'seed_evidence':[p for p in pairs if p['case']==case]}
        for m in ('PPCPP','P2_MULTI'):
            j=oj[m];oldsource=read(Path(j['source_output']));raw=oldsource['result']['raw'];now=pipelines[(case,20261020,m)];row[m+'_original_route_same_rep0']=raw['route']==now['native']['raw']['route'];row[m+'_post_vertices_same_rep0']=old[m]['vertices']==now['post']['vertices'];row[m+'_old_rep0_original_length']=len(raw['route'])-1;row[m+'_new_rep0_original_length']=len(now['native']['raw']['route'])-1
        changes.append(row)
    concentration={};order=sorted(states,key=lambda s:(-s['saved_seconds'],s['case']));den=sum(s['saved_seconds'] for s in states)
    for n in (1,3,5):concentration['top'+str(n)]={'cases':[s['case'] for s in order[:n]],'share_of_signed_total_time_saved':sum(s['saved_seconds'] for s in order[:n])/den}
    concentration['size_shares']={r['label']:r['saved_seconds_sum_state']/den for r in strata if r['dimension']=='scale'}
    for name,x in [('162重建配对.json',pairs),('54重建状态均值.json',states),('原标签完整分层.json',strata),('极值与全部seed证据.json',extreme),('54新旧来源核对.json',changes),('时间节省集中度.json',concentration)]:dump(name,x)
    dump('四象限.json',{'state_counts':dict(Counter(s['quadrant'] for s in states)),'pair_counts':dict(Counter(p['quadrant'] for p in pairs)),'states':{k:[s['case'] for s in states if s['quadrant']==k] for k in sorted({s['quadrant'] for s in states})},'pairs':{k:[{'case':p['case'],'seed':p['seed'],'saved_seconds':p['saved_seconds'],'extra_ratio':p['extra_ratio']} for p in pairs if p['quadrant']==k] for k in sorted({p['quadrant'] for p in pairs})}})
    dump('统计核对摘要.json',{'old_rep0':dict(Counter(oldsigns)),'new_rep0':dict(Counter(rep0signs)),'new_state3':dict(Counter(s['distance_sign'] for s in states)),'rep0_original_changes':{m:sum(not r[m+'_original_route_same_rep0'] for r in changes) for m in ('PPCPP','P2_MULTI')},'P2_statuses':dict(Counter(p['P2_status'] for p in pairs))})
    for name,rows in [('162重建配对.csv',pairs),('54重建状态均值.csv',states),('原标签完整分层.csv',strata)]:
        with (H/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    dump('来源hash.json',sources);dump('零新增求解账.json',{k:0 for k in ('planning','postprocessing','geometry','candidate_generation','new_routes','input_transformations','old_verify_runs')});print(json.dumps({'pairs':len(pairs),'states':len(states),'strata':len(strata),'quadrants':dict(Counter(s['quadrant'] for s in states)),'new_queries':0},ensure_ascii=False))
if __name__=='__main__':main()
