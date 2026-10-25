from common import *
from copy import deepcopy
from collections import Counter
from fractions import Fraction as Q
import traceback,json,importlib.util,sys
import repair_runtime as RR
from select_inputs import interior
def fixture(block=()):
 F={(x,y) for x in range(7) for y in range(4)}-set(block)
 path=[[x,1] for x in range(7)]+[[6,2]]+[[x,2] for x in range(5,-1,-1)]+[[0,1]]
 return {'name':'fixed_stub','free':[list(p) for p in sorted(F)],'targets':[[0,1],[6,1]],'covered':[[0,1]],'published_targets':[[0,1],[6,1]],'deferred_targets':[],'current':[0,1],'previous':[0,0],'base':[0,1],'predator':[-1,0],'initial_targets':[[0,1],[6,1]],'old_route':path,'distance_budget':200}
NAMES=['common_snapshot_alignment','old_route_true_interior_certificate','no_block_idempotence','single_and_multiple_interval_repair','responsibility_complete','unreachable_rejected','insufficient_resource_rejected','closed_boundary_and_strict_center_credit','source_identity_and_serialization','zero_and_unobservable_counts','deadline_and_entry_exception_paths','tampering_negative_controls']
def main():
 assert not (H/'prechecks.json').exists()
 control=ROOT/'中心区计时插桩影响核查_v0.1_20261022/run_check.py'
 spec=importlib.util.spec_from_file_location('_check_control',control);C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
 import selection_geometry as G
 from center_bench_v01_20261022 import service as S
 from center_bench_v01_20261022.audit import region as Z
 counts=Counter();records=[];pure_repairs=[]
 def repair(c):
  r=RR.solve(c);pure_repairs.append(r['repair_counts']);RR.audit_saved(c,r);return r
 def rejected(c,expected,limit=20):
  try:RR.solve(c,limit);raise AssertionError('expected rejection')
  except RR.RepairFailure as e:
   assert e.reason==expected;pure_repairs.append(e.counts)
 for name in NAMES:
  try:
   if name=='common_snapshot_alignment':
    for c in read(H/'selection.json')['selected']:
     n,e=read(H/c['N']),read(H/c['E']);assert all(n[k]==e[k] for k in n if k!='free');assert ps(n['free'])-ps(e['free'])==ps(c['obstacles'])
     assert not (ps(n['targets'])-ps(n['covered']))&ps(c['obstacles'])
   elif name=='old_route_true_interior_certificate':
    assert interior((0,0),(0,1),(0,1),counts)
    assert interior((0,1),(1,0),(1,1),counts) is None
    for c in read(H/'selection.json')['selected']:
     h=read(H/c['history']);assert h['old_suffix_N_legal'] and h['old_suffix_E_invalid_interiors']
   elif name=='no_block_idempotence':
    c=fixture();r=repair(c);assert r['raw']['route']==c['old_route'] and not r['repair_intervals'];assert r['repair_counts']['BFS_started']==0
   elif name=='single_and_multiple_interval_repair':
    for block,n in [({(2,1)},1),({(2,1),(4,1)},2)]:
     c=fixture(block);r=repair(c);assert len(r['repair_intervals'])==n and r['repair_counts']['BFS_started']==n
   elif name=='responsibility_complete':
    c=fixture({(2,1)});r=repair(c);assert (6,1) in ps(r['raw']['route'])
    c=fixture();c['targets'].append([5,0]);c['published_targets'].append([5,0]);rejected(c,'missing_required_tasks')
   elif name=='unreachable_rejected':rejected(fixture({(2,y) for y in range(4)}),'unreachable_repair_endpoint')
   elif name=='insufficient_resource_rejected':
    c=fixture();c['distance_budget']=1;rejected(c,'resource_insufficient')
   elif name=='closed_boundary_and_strict_center_credit':
    F=ps(fixture()['free'])-{(1,1)}
    counts['independent_legality_calls']+=2;assert not G.legal(F,(0,1),(1,0)) and G.legal(F,(0,0),(1,0))
    for q,inside in [((1,1),True),((Q(6,5),1),False),((Q(119,100),1),True)]:
     assert S.inside(q,(1,1),counts,'pure') is inside and Z.internal(q,(1,1),counts) is inside
   elif name=='source_identity_and_serialization':
    ids=C.B.identity();assert ids['primary']['file']!=ids['independent']['file'];x=fixture();assert json.loads(json.dumps(x))==x
    for p,d in read(H/'input_freeze.json')['files'].items():assert sha(H/p)==d
   elif name=='zero_and_unobservable_counts':
    z=RR.zero();assert set(z)==set(RR.KEYS) and all(type(v) is int and v==0 for v in z.values());assert C.detail(None)['counts'] is None
   elif name=='deadline_and_entry_exception_paths':
    rejected(fixture(),'repair_20_second_deadline',-1)
    token={'started':0,'returned':0,'exceptions':0}
    try:C.invoke_once(lambda:(_ for _ in ()).throw(ValueError('fixed')),token,None);raise AssertionError('swallowed')
    except ValueError:assert token=={'started':1,'returned':0,'exceptions':1} and sys.getprofile() is None
    try:C.invoke_once(lambda:None,token,None);raise AssertionError('duplicate allowed')
    except AssertionError as e:assert 'entry' in str(e)
   elif name=='tampering_negative_controls':
    c=fixture({(2,1)});r=repair(c);bad=deepcopy(r);bad['raw']['route'][1]=[99,99]
    try:RR.audit_saved(c,bad);raise RuntimeError('tamper accepted')
    except AssertionError:pass
   records.append({'id':name,'passed':True})
  except BaseException as e:records.append({'id':name,'passed':False,'error':repr(e),'traceback':traceback.format_exc()});break
 out={'passed':len(records)==12 and all(r['passed'] for r in records),'cases':records,'pure_query_counts':dict(counts),'pure_fixed_fixture_repair_calls':len(pure_repairs),'pure_repair_counts':pure_repairs,'real_processing_entries':0,'real_core_calls':0,'real_R_calls':0,'post_search_calls':0,'preparation_repairs':1}
 dump(H/'prechecks.json',out);print(json.dumps({'passed':out['passed'],'cases':len(records),'last':records[-1],'real_core_calls':0},ensure_ascii=False));assert out['passed']
if __name__=='__main__':main()
