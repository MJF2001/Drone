"""Extra read-only certificate/set/arithmetic checks on saved results.
No core, post, BFS, service intersection or visibility calls.
"""
from common import *
from collections import Counter
from fractions import Fraction as Q
import verify as baseverify
def verify_saved():
 result=baseverify.verify();reg=read(H/'state_registry.json');pairs=read(H/'pairs.json');derived=read(H/'derived_pairs.json');assert len(reg)==12
 lookup={p['id']:p for p in pairs};extra=Counter();short=flat=long=0;gb=set();gf=set()
 for row in reg:
  if row['status']!='qualified':continue
  c=read(H/row['input']);F=ps(c['free']);P=ps(c['published_targets']);HH=ps(c['covered']);U=P-HH
  assert ps(c['targets'])==P&F and ps(c['targets'])-HH==U and not P-F-HH and tuple(c['current']) in HH
  selected=[x for x in row['attempts'] if x['status']=='selected'];assert len(selected)==1 and selected[0] is row['attempts'][-1]
  assert len(row['attempts'])<=20 and selected[0]['cell']==row['selected_obstacle'];extra['qualified_set_certificates']+=1
  witness=row['blocked_old_post']['interval'];t=Q(witness['midpoint']['n'],witness['midpoint']['d']);lo=Q(witness['lower']['n'],witness['lower']['d']);hi=Q(witness['upper']['n'],witness['upper']['d']);assert 0<=lo<t<hi<=1
  for z,b in zip(witness['point'],row['selected_obstacle']):assert abs(Q(z['n'],z['d'])-b)<Q(1,2)
  assert row['blocked_old_post']['pending_at_edge_end']>=2 and row['independent_qualification']['passed'];extra['saved_collision_certificates']+=1
  refs={arm:read(H/'outputs'/(row['id']+'__'+arm+'.json')) for arm in ('REF','OFF','ALT1')}
  for o in refs.values():assert o['eligible'] and o['passed'] and o['decision_audit']['passed'] and o['independent']['passed']
  assert all(refs['OFF']['off_equivalence'].values());extra['OFF_equivalence']+=1
  trace=refs['REF']['native']['raw']['trace'];path=refs['REF']['native']['raw']['route'];pending=set(U);cursor=0;first=None
  for i,e in enumerate(trace):
   pending-=ps(path[cursor:e['index']+1]);cursor=e['index'];assert len(pending)==e['pending_count']
   if e['kind']=='recovery' and len(pending)>=2:
    first=(i,e['index'],set(pending),tuple(e['goal']));break
  assert first is not None;tr=refs['OFF']['diagnostic']['trigger'];assert first[0]==tr['trace_record'] and first[1]==tr['route_index'] and first[2]==ps(tr['pending']) and first[3]==tuple(tr['default_goal'])
  ordered=[]
  for q in map(tuple,row['old_order']):
   if q not in ordered:ordered.append(q)
  q0=first[3];q1=next(q for q in ordered if q in first[2] and q!=q0);assert q1==tuple(tr['alternative_goal']);extra['first_trigger_and_candidate']+=1
  a=list(map(tuple,refs['OFF']['native']['raw']['route']));b=list(map(tuple,refs['ALT1']['native']['raw']['route']));pair=lookup[row['id']]
  if a==b:assert pair['raw_same'] and pair['post_same'] and pair['delta_post_sign']==0;extra['same_physical_route']+=1
  else:
   k=0
   while k<min(len(a),len(b)) and a[k]==b[k]:k+=1
   k-=1;h=pair['H2'];p=a[k];QQ=U-set(a[:k+1]);assert h['p']==list(p) and h['common_index']==k and ps(h['Qstar'])==QQ
   adj={(p[0]-1,p[1]),(p[0]+1,p[1]),(p[0],p[1]-1),(p[0],p[1]+1)};L=adj&QQ-{a[k+1]};assert ps(h['L'])==L
   for arm,route in [('OFF',a),('ALT1',b)]:
    s=max(next(j for j,q in enumerate(route) if q==u) for u in QQ);cc=h['C_'+arm]
    assert cc['C']==s-k and cc['last_common_pending_service_index']==s and k+cc['C']+len(route)-1-s==len(route)-1
    extra['shared_C_identities']+=1
   assert not L and h['witnesses']['OFF']['W']==h['witnesses']['ALT1']['W']==0;extra['empty_L_not_support']+=1
  sg=pair['delta_post_sign'];short+=sg<0;flat+=sg==0;long+=sg>0
  assert pair['independent_sign']['independent_from_physical_vertices']
  if pair['strict_H1']:assert pair['delta_recovery']>0 and sg<0 and all(refs[x]['post_envelope']['fallback'] is None for x in ('OFF','ALT1'));gb.add(row['base_geometry']);gf.add(row['family'])
 assert (short,flat,long)==(4,7,1) and len(gb)==3 and len(gf)==2
 summary=read(H/'summary.json');assert summary['protocol_gate_H1'] and summary['valid_pairs']==12 and summary['H2']['nonidentical_with_empty_L']==8
 assert read(H/'图版索引.json')['figures'] and len(read(H/'84视图完整指标.json'))==84
 for d in derived:assert d['decision_available_indicators']['provenance'].startswith('reconstructed')
 result['extra_saved_checks']=dict(extra);result['outcomes_independently_recounted']=dict(shorter=short,equal=flat,longer=long,strict_geometries=len(gb),strict_families=len(gf))
 print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':verify_saved()
