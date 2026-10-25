"""Independent 80-digit directed Decimal arithmetic and vector proof checks.
Never imports analysis or old geometry/planning code, and never generates paths.
"""
from pathlib import Path
from fractions import Fraction
from decimal import Decimal,localcontext,ROUND_FLOOR,ROUND_CEILING
from collections import Counter,defaultdict
import json,hashlib
H=Path(__file__).resolve().parent;B=H.parent/'任意方向合法直达有限诊断_v0.1_20261022';S=10**60
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sq(a,b):return (a[0]-b[0])**2+(a[1]-b[1])**2
def bounds(qs):
    with localcontext() as c:
        c.prec=80;lo=hi=Decimal(0)
        for q in qs:
            root=Decimal(q).sqrt()
            if root==root.to_integral_value() and root*root==q:a=b=root
            else:a=root.next_minus();b=root.next_plus()
            c.rounding=ROUND_FLOOR;lo+=a
            c.rounding=ROUND_CEILING;hi+=b
        return Fraction(lo),Fraction(hi)
def contains(t,v):assert Fraction(t[0],S)<=v[0]<=v[1]<=Fraction(t[1],S),(t,v)
def direct_vectors(points):
    vx,vy=points[-1][0]-points[0][0],points[-1][1]-points[0][1]
    vecs=[(q[0]-p[0],q[1]-p[1]) for p,q in zip(points,points[1:])]
    if vx==vy==0:return all(x==y==0 for x,y in vecs)
    return all(x*vy-y*vx==0 and x*vx+y*vy>=0 for x,y in vecs)
def phys(c):
    return [frozenset(map(tuple,c[k])) for k in ('free','published_targets','covered','targets','deferred_targets')]+[c[k] for k in ('current','previous','base','distance_budget')]
def main():
    for p,h in read(H/'来源hash.json').items():assert sha(Path(p))==h,p
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    jobs=read(B/'117固定清单.json');rows=read(H/'117路线固定顺序下界.json');parts=read(H/'全部锚点区间下界.json');rm={r['id']:r for r in rows};pm=defaultdict(list)
    for p in parts:pm[p['id']].append(p)
    assert len(jobs)==len(rows)==117;independent={};inputs={};derived_multis=[]
    for job in jobs:
        jid=job['id'];r=rm[jid];payload=read(B/job['payload']);c=payload['input'];o=read(B/'outputs'/(jid+'.json'));orig=payload['raw']['route'];U=set(map(tuple,c['targets']))-set(map(tuple,c['covered']));first=sorted(((min(i for i,p in enumerate(orig) if tuple(p)==q),q) for q in U),key=lambda x:x[0]);seq=[list(q) for i,q in first];assert seq==[x['point'] for x in o['first_original']]==[x['point'] for x in o['first_actual']]==r['actual_first_service_sequence'];assert not o['actual_order_changed'] and len(seq)==r['tasks_remaining'];assert r['actual_sequence_equals_original']
        anchors=[c['current']]+seq+[c['base']] if seq else [c['current'],c['base']];assert anchors==r['anchor_sequence_definition_only'];assert len(pm[jid])==r['parts']==len(anchors)-1;allq=[];chordq=[];certs=[];bs=[];ls=[];caps=[]
        for k,(p,old) in enumerate(zip(pm[jid],o['parts'])):
            assert p['part']==k and p['kind']==old['kind'];assert p['original_left']==old['left'] and p['original_right']==old['right'];assert p['anchor_a']==anchors[k] and p['anchor_b']==anchors[k+1];points=o['vertices'][old['edge_start']:old['edge_end']+1];assert p['saved_output_vertices']==points and points[0]==anchors[k] and points[-1]==anchors[k+1];qs=[sq(a,b) for a,b in zip(points,points[1:])];q=sq(*anchors[k:k+2]);assert p['saved_edge_squared_lengths']==qs and p['endpoint_squared_distance']==q;assert len(qs)==p['output_edges'];assert sum(x>0 for x in qs)==p['nonzero_output_edges']
            lower=bounds([q]);length=bounds(qs);contains(p['B_ticks'],lower);contains(p['L_ticks'],length);assert list(map(Fraction,p['B_interval']))==[Fraction(v,S) for v in p['B_ticks']];assert list(map(Fraction,p['L_interval']))==[Fraction(v,S) for v in p['L_ticks']]
            coll=direct_vectors(points);assert p['exact_equal_by_collinear_forward']==coll;certs.append(coll)
            gap=(length[0]-lower[1],length[1]-lower[0]);cap=(Fraction(0),Fraction(0)) if coll else (max(Fraction(0),gap[0]),max(Fraction(0),gap[1]));contains(p['improvement_cap_ticks'],cap);assert p['raw_L_minus_B_ticks']==[p['L_ticks'][0]-p['B_ticks'][1],p['L_ticks'][1]-p['B_ticks'][0]]
            bs.append(lower);ls.append(length);caps.append(cap);allq+=qs;chordq.append(q)
            if len(qs)>1:derived_multis.append(p)
        bb=bounds(chordq);ll=bounds(allq);contains(r['B_ticks'],bb);contains(r['L_ticks'],ll);contains(r['improvement_cap_ticks'],(sum(x[0] for x in caps),sum(x[1] for x in caps)));assert r['improvement_cap_ticks']==[sum(p['improvement_cap_ticks'][i] for p in pm[jid]) for i in (0,1)];assert r['fixed_actual_order_optimal_certificate']==all(certs);assert r['single_edge_parts']==sum(p['output_edges']==1 for p in pm[jid]) and r['multi_edge_parts']==sum(p['output_edges']>1 for p in pm[jid]);assert r['zero_edge_parts']==sum(p['output_edges']==0 for p in pm[jid]);assert r['distance_budget']==c['distance_budget'];assert ll[1]<=Fraction(str(c['distance_budget']));assert Counter(map(str,allq))==r['output_squared_length_multiset'] and Counter(map(str,chordq))==r['anchor_squared_length_multiset']
        for v in o['first_actual']:
            if v['edge']==-1:assert v['point']==c['current']
            else:
                a,b=o['vertices'][v['edge']:v['edge']+2];t=Fraction(v['t']);assert 0<=t<=1 and [Fraction(a[k])+t*(b[k]-a[k]) for k in (0,1)]==list(map(Fraction,v['point']))
        independent[jid]={'B':bb,'L':ll,'cap':(sum(x[0] for x in caps),sum(x[1] for x in caps)),'seq':seq,'anchor_q':Counter(chordq),'edge_q':Counter(allq)};inputs[jid]=c
    assert derived_multis==read(H/'多段区间全量表.json')
    pairs=read(H/'57配对顺序限制证书.json');assert len(pairs)==57;signs=defaultdict(Counter)
    for p in pairs:
        a,b=independent[p['PPCPP_id']],independent[p['P2_id']];assert phys(inputs[p['PPCPP_id']])==phys(inputs[p['P2_id']]) and p['same_physical_input'];d=(a['B'][0]-b['L'][1],a['B'][1]-b['L'][0]);contains(p['B_PPCPP_minus_saved_L_P2_ticks'],d);different=a['seq']!=b['seq'];assert p['actual_sequences_different']==different;equal=a['anchor_q']==b['edge_q'];assert p['exact_equal_by_squared_multiset']==equal
        sign='positive' if d[0]>0 else ('nonpositive' if d[1]<=0 or equal else 'uncertain');assert p['sign']==sign;assert p['strict_order_restriction_certificate']==(sign=='positive' and different)
        if sign=='positive':assert different,'CONTRADICTION: identical service order but lower bound exceeds feasible P2'
        signs[p['batch']][sign]+=1
    for s in read(H/'分批核验汇总.json'):
        rs=[r for r in rows if r['cohort']==s['cohort'] and r['method']==s['method']];assert len(rs)==s['routes'];assert sum(r['parts'] for r in rs)==s['parts'];assert sum(r['multi_edge_parts'] for r in rs)==s['multi_edge_parts'];assert sum(r['single_edge_parts'] for r in rs)==s['single_edge_parts'];assert sum(r['fixed_actual_order_optimal_certificate'] for r in rs)==s['fixed_order_optimal_routes']
        for k in ('L','B'):assert s[k+'_ticks']==[sum(r[k+'_ticks'][i] for r in rs) for i in (0,1)]
        assert s['improvement_cap_ticks']==[sum(r['improvement_cap_ticks'][i] for r in rs) for i in (0,1)]
    ledger=read(H/'零求解调用账.json');assert all(ledger[k]==0 for k in ('new_planning','core','graph_search','visibility_queries','postprocessing','candidate_generation','new_routes','counterfactual_routes','production_geometry_imports','old_verify_runs'))
    print(json.dumps({'passed':True,'independent_method':'80-digit directed Decimal root sums + segment-vector collinearity; primary uses integer-square bounds + point projections','routes':117,'anchor_parts':len(parts),'multi_parts':len(derived_multis),'fixed_order_optimal_certificates':sum(r['fixed_actual_order_optimal_certificate'] for r in rows),'pair_signs':{k:dict(v) for k,v in signs.items()},'same_order_contradictions':0,'new_planning_geometry_routes':0},ensure_ascii=False))
if __name__=='__main__':main()
