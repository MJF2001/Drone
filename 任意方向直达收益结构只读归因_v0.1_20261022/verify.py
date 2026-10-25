"""Independent arithmetic verification; no imports from analysis or old code.
Checks rational length brackets by integer squares, no LOS or route generation.
"""
from pathlib import Path
from fractions import Fraction
from collections import Counter,defaultdict
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parent;B=R/'任意方向合法直达有限诊断_v0.1_20261022';S=10**60
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def total(xs):
    return {'old':sum(x['l'] for x in xs),'m':sum(x['m'] for x in xs),'d':[sum(x['d_ticks'][i] for x in xs) for i in (0,1)],'gain':[sum(x['gain_ticks'][i] for x in xs) for i in (0,1)],'excess':sum(x['excess_ticks'] for x in xs),'metric_gap':[sum(x['metric_gap_ticks'][i] for x in xs) for i in (0,1)]}
def same(saved,t):
    for k,v in t.items():assert saved[k]==v,(k,saved[k],v)
    assert [saved['gain'][i]-saved['metric_gap'][i] for i in (0,1)]==[saved['excess']]*2
    for k in ('d','gain','metric_gap'):assert list(map(Fraction,saved[k+'_interval']))==[Fraction(z,S) for z in t[k]]
def main():
    for p,h in read(H/'来源hash.json').items():assert sha(Path(p))==h,p
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    jobs=read(B/'117固定清单.json');routes=read(H/'117全量区间分解.json');ed=read(H/'逐边区间分解.json');by=defaultdict(list)
    for e in ed:by[e['id']].append(e)
    assert len(jobs)==len(routes)==117 and len(ed)==8112
    rt={r['id']:r for r in routes};squared={}
    for j in jobs:
        r=rt[j['id']];o=read(B/'outputs'/(j['id']+'.json'));original=read(B/j['payload'])['raw']['route'];xs=by[j['id']];assert len(xs)==len(o['edges']);cursor=0;sq=Counter()
        for k,(e,old) in enumerate(zip(xs,o['edges'])):
            assert e['edge']==k and e['left']==old['left']==cursor and e['right']==old['right'];cursor=e['right'];assert e['a']==old['a']==original[e['left']] and e['b']==old['b']==original[e['right']]
            dx=e['b'][0]-e['a'][0];dy=e['b'][1]-e['a'][1];q=dx*dx+dy*dy;length=cursor-e['left'];m=abs(dx)+abs(dy);assert [e['dx'],e['dy'],e['l'],e['m'],e['squared_length']]==[dx,dy,length,m,q];assert length>=m
            cls='zero_displacement' if q==0 else ('axis' if dx*dy==0 else 'diagonal');assert e['class']==cls and e['kind']==old['kind'] and e['part']==old['part']
            low,high=e['d_ticks'];assert 0<=low<=high and high-low<=1;assert low*low<=q*S*S<=high*high
            assert e['excess_ticks']==(length-m)*S;assert e['metric_gap_ticks']==[m*S-high,m*S-low];assert e['gain_ticks']==[length*S-high,length*S-low];assert e['gain_ticks']==[e['excess_ticks']+z for z in e['metric_gap_ticks']]
            for key in ('d','metric_gap','gain'):assert list(map(Fraction,e[key+'_interval']))==[Fraction(z,S) for z in e[key+'_ticks']]
            sq[str(q)]+=1
        assert cursor==len(original)-1;assert dict(sq)==r['squared_length_multiset'];squared[j['id']]=sq;tt=total(xs);same(r['total'],tt);assert tt['old']==o['L4'] and Fraction(o['Lshortcut_interval'][0])<=Fraction(tt['d'][0],S)<=Fraction(tt['d'][1],S)<=Fraction(o['Lshortcut_interval'][1])
        for key,field in (('by_kind','kind'),('by_class','class')):
            for label,saved in r[key].items():same(saved,total([x for x in xs if x[field]==label]))
        assert len(r['parts'])==len(o['parts'])
        for i,(saved,part) in enumerate(zip(r['parts'],o['parts'])):
            same(saved,total([x for x in xs if x['part']==i]));assert saved['left']==part['left'] and saved['right']==part['right'] and saved['kind']==part['kind']
        assert sum(x['old'] for x in r['parts'])==tt['old'];assert [sum(x['gain'][i] for x in r['parts']) for i in (0,1)]==tt['gain']
    for group in read(H/'分层交叉汇总.json'):
        rs=[r for r in routes if r['cohort']==group['cohort'] and r['method']==group['method']];dim=group['dimension'];label=group['label']
        if dim in ('shape','scale','event','progress'):rs=[r for r in rs if r['labels'][dim]==label]
        assert group['route_denominator']==len(rs);xs=[x for r in rs for x in by[r['id']]]
        if dim in ('kind','class'):xs=[x for x in xs if x[dim]==label]
        if dim=='cross':xs=[x for x in xs if x['kind']+' x '+x['class']==label]
        same(group,total(xs));assert group['edges']==len(xs)
    pairs=read(H/'57配对成本位置与等长证据.json');assert len(pairs)==57;certificates=0
    oldpairs={(p['batch'],p['case']):p for p in read(B/'57同物理输入配对.json')}
    for p in pairs:
        a=rt[p['PPCPP_id']];b=rt[p['P2_id']];old=oldpairs[(p['batch'],p['case'])];d=[a['total']['d'][0]-b['total']['d'][1],a['total']['d'][1]-b['total']['d'][0]];assert p['new_total_difference_ticks']==d;assert [sum(x['new_difference_ticks'][i] for x in p['parts']) for i in (0,1)]==d;assert sum(x['old_difference'] for x in p['parts'])==p['old_total_difference']==old['original_PPCPP_minus_P2']
        sign='positive' if d[0]>0 else ('negative' if d[1]<0 else ('zero' if d==[0,0] else 'uncertain'));assert p['interval_sign']==sign
        for x in p['parts']:
            aa=a['by_kind'].get(x['kind'],{'d':[0,0],'old':0});bb=b['by_kind'].get(x['kind'],{'d':[0,0],'old':0});assert x['new_difference_ticks']==[aa['d'][0]-bb['d'][1],aa['d'][1]-bb['d'][0]]
        assert Fraction(old['post_difference_interval'][0])<=Fraction(d[0],S)<=Fraction(d[1],S)<=Fraction(old['post_difference_interval'][1]);assert p['prior_sign']==old['certified_sign']
        if p['additional_exact_equal_certificate'] is not None:
            assert p['prior_sign']=='uncertain' and squared[a['id']]==squared[b['id']];assert p['additional_exact_equal_certificate']['squared_length_multiset']==dict(squared[a['id']]);certificates+=1
    # Independent example selection check; compare stored fixed score with all
    # eligible routes, so no display float drives selection or tie breaking.
    def gain(r,kind):return r['by_kind'].get(kind,{'gain':[0,0]})['gain']
    def ax(r):return [sum(r['by_class'].get(k,{'gain':[0,0]})['gain'][i] for k in ('axis','zero_displacement')) for i in (0,1)]
    lag={p['PPCPP_id'] for p in pairs if p['interval_sign']=='positive'}
    for e in read(H/'解释实例固定选择.json'):
        kind=e['category'];eligible=[]
        for r in routes:
            if kind=='main_return':ok=gain(r,'last_to_base')[0]>0 and gain(r,'last_to_base')[0]>=sum(v['gain'][1] for k,v in r['by_kind'].items() if k!='last_to_base');score=gain(r,'last_to_base')
            elif kind=='between_service':ok=gain(r,'between_first_services')[0]>0;score=gain(r,'between_first_services')
            elif kind=='axis_or_zero':ok=ax(r)[0]>0;score=ax(r)
            else:ok=r['id'] in lag;score=r['total']['gain']
            if ok:eligible.append((r['id'],score))
        if e['id'] is None:assert not eligible
        else:
            best=e['selection_score_ticks'];assert (e['id'],best) in eligible and len(eligible)==e['candidate_routes']
            assert all(i==e['id'] or best[0]>s[1] or (best==s and e['id']<i) for i,s in eligible)
    ledger=read(H/'零新增调用账.json');assert all(ledger[k]==0 for k in ('planning_entries','core','graph_search','visibility_queries','shortcut_calls','candidate_generation','new_routes','counterfactual_routes','continuous_closed_loop','production_imports','old_verify_runs'))
    costfile=H/'配对成本位置分批合计.json'
    if costfile.exists():
        for row in read(costfile):
            xs=[part for p in pairs if p['batch']==row['batch'] for part in p['parts'] if part['kind']==row['kind']]
            assert row['old_difference']==sum(x['old_difference'] for x in xs);assert row['new_difference_ticks']==[sum(x['new_difference_ticks'][i] for x in xs) for i in (0,1)]
    print(json.dumps({'passed':True,'routes':117,'saved_edges':len(ed),'pairings':57,'exact_equal_supplemental_certificates':certificates,'all_edge_decompositions_recover_total_savings':True,'new_geometry_planning_routes_counterfactual':0},ensure_ascii=False))
if __name__=='__main__':main()
