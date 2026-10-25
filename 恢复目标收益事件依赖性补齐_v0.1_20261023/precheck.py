"""Six fixed pure checks; no planning core or real post entry."""
from common import *
from eventdep_labels import label,validate
from eventdep_arithmetic import calculate,Expr,certificate
from eventdep_arithmetic_audit import audit as arithmetic_audit
from collections import Counter
from copy import deepcopy
import sys,ast,importlib,importlib.util,traceback
def main():
 assert not (H/'prechecks.json').exists()
 names=['source_hashes_contracts','stable_four_cell_labels','full_trigger_identity','accepted_module_diff_imports','saved_interface_zero_schema_normalization_exclusive','fixed_arithmetic_direction_zero_missing']
 counts=Counter(label_checks=0,label_expected_rejections=0,exclusive_claim_attempts=0,numeric_fixture_attempts=0,numeric_missing_rejections=0,arithmetic_primary_calls=0,arithmetic_independent_calls=0);records=[];arith=[]
 try:
  for name in names:
   if name=='source_hashes_contracts':
    for p,d in read(H/'source_guards.json').items():assert sha(p)==d
    for p,d in read(H/'input_freeze.json')['files'].items():assert sha(H/p)==d
    for c in read(H/'selection.json')['selected']:
     n,e=read(H/c['input']),read(c['E_source']);assert n==read(c['N_source']) and sha(H/c['input'])==c['N_sha256']
     assert all(n[k]==e[k] for k in n if k not in ('free','targets')) and ps(n['targets'])-ps(n['covered'])==ps(e['targets'])-ps(e['covered'])
     for x in (n,e):assert ps(x['targets'])==ps(x['published_targets'])&ps(x['free']) and not ps(x['published_targets'])-ps(x['free'])-ps(x['covered'])
   elif name=='stable_four_cell_labels':
    table={('N',False):'T0',('N',True):'T1',('E',False):'T1',('E',True):'T0'}
    for (env,en),expected in table.items():
     counts['label_checks']+=1;row={'environment':env,'target_intervention_enabled':en,'target_label':expected};assert label(env,en)==expected and validate(row)
     bad=dict(row,target_label='T1' if expected=='T0' else 'T0');counts['label_checks']+=1
     try:validate(bad);raise RuntimeError('inverted label accepted')
     except AssertionError:counts['label_expected_rejections']+=1
   elif name=='full_trigger_identity':
    refs=read(H/'reused_E/index.json')['references']
    for c in read(H/'selection.json')['selected']:
     sp=read(H/c['spec']);k=sp['trace_record'];n=read(H/c['input']);assert sp['T0']!=sp['T1'] and {tuple(sp['T0']),tuple(sp['T1'])}<=ps(sp['pending'])<=ps(n['free'])
     assert ps(sp['pending'])==ps(n['targets'])-ps(n['covered'])-ps(sp['original_route_prefix'])
     assert sp['original_trace'][k]['goal']==sp['T0'] and sp['original_trace'][k]['current']==sp['current'] and sp['original_trace'][k]['previous']==sp['previous']
     for ref in [r for r in refs if r['case']==c['id']]:
      wrapper=read(H/ref['wrapper']);x=wrapper['saved_output'];tr=x['native']['diagnostic']['trigger'];assert x==read(ref['source']) and sha(ref['source'])==ref['source_sha256'];validate(ref)
      assert x['native']['raw']['trace'][:k]==sp['original_trace'][:k] and tr['current']==sp['current'] and tr['previous']==sp['previous'] and tr['pending']==sp['pending']
      assert x['native']['raw']['route'][:tr['route_index']+1]==sp['original_route_prefix'] and tr['chosen_goal']==sp[ref['target_label']]
   elif name=='accepted_module_diff_imports':
    for binding in read(H/'bindings.json')['module_copies']:
     a=Path(binding['source']).read_text(encoding='utf-8');b=(H/binding['destination']).read_text(encoding='utf-8');compile(b,binding['destination'],'exec')
     if binding['destination'] in ('eventdep_diag_native.py','eventdep_diag_hook.py','eventdep_diag_decision_audit.py'):assert binding['byte_identical'] and a==b
     if binding['destination'] in ('eventdep_diag_runtime.py','eventdep_diag_candidate.py'):assert b.replace('eventdep_diag_','recovery_diag_')==a
    control=ROOT/'中心区计时插桩影响核查_v0.1_20261022/run_check.py';spec=importlib.util.spec_from_file_location('_eventdep_pure_control',control);C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C);C.B.load_native()
    for tail in ('native','hook','runtime','candidate','decision_audit','compare','worker'):
     m=importlib.import_module('eventdep_diag_'+tail);assert Path(m.__file__).resolve()==(H/('eventdep_diag_'+tail+'.py')).resolve()
    for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
   elif name=='saved_interface_zero_schema_normalization_exclusive':
    from eventdep_diag_hook import Diagnostic,KEYS
    from eventdep_diag_compare import semantic,claim_destination
    sp=read(H/read(H/'selection.json')['selected'][0]['spec']);zero=Diagnostic(sp,False).export();assert set(zero['counts'])==set(KEYS) and all(type(v) is int and v==0 for v in zero['counts'].values())
    a={'goal':(1,2),'options':[{'cell':(2,3),'score':1}],'index':3,'pending_count':2,'seconds':1};b=json.loads(json.dumps(a));b['seconds']=5;assert semantic(a)==semantic(b);b['goal']=[2,1];assert semantic(a)!=semantic(b)
    p=H/'pure_stub/not_formal.json';p.parent.mkdir(exist_ok=True);counts['exclusive_claim_attempts']+=1;claim_destination(p);x={'environment':'N','target_label':'T0','target_intervention_enabled':False,'counts':zero['counts'],'profile_detail':None,'kind':'pure serialization stub, no core/post'};dump(p,x);assert read(p)==x and validate(read(p))
    counts['exclusive_claim_attempts']+=1
    try:claim_destination(p);raise RuntimeError('exclusive file overwritten')
    except FileExistsError:pass
   else:
    fixtures=[([10,10,10,10],(0,0,0)),([10,12,8,10],(-2,-2,0)),([12,10,8,10],(2,-2,-4)),([10,12,9,12],(-2,-3,-1)),([8,11,10,11],(-3,-1,2))]
    for values,expected in fixtures:
     counts['numeric_fixture_attempts']+=1;certs={k:certificate(Expr.number(v)) for k,v in zip(('N_T0','N_T1','E_T0','E_T1'),values)}
     counts['arithmetic_primary_calls']+=1;p=calculate(certs);counts['arithmetic_independent_calls']+=1;a=arithmetic_audit(certs,p);assert a['passed'] and tuple(p['values'][k]['display'] for k in ('D_N','D_E','I'))==expected
     arith.append({'fixture':values,'expected':expected,'primary':p,'independent':a})
    counts['numeric_fixture_attempts']+=1;missing={k:certificate(Expr.number(1)) for k in ('N_T0','N_T1','E_T0')}
    counts['arithmetic_primary_calls']+=1
    try:calculate(missing);raise RuntimeError('missing cell accepted')
    except AssertionError:counts['numeric_missing_rejections']+=1
    counts['arithmetic_independent_calls']+=1
    try:arithmetic_audit(missing,{});raise RuntimeError('independent missing cell accepted')
    except AssertionError:counts['numeric_missing_rejections']+=1
   records.append({'id':name,'passed':True,'new_core_post':0})
 except BaseException as ex:records.append({'id':name,'passed':False,'reason':repr(ex),'traceback':traceback.format_exc()})
 out={'passed':len(records)==6 and all(r['passed'] for r in records),'cases':records,'pure_counts':dict(counts),'arithmetic_fixtures':arith,'new_core_post_geometry_BFS':0,'preparation_repairs':read(H/'preparation_repairs.json')['used']}
 dump(H/'prechecks.json',out);print(json.dumps({'passed':out['passed'],'cases':records,'counts':dict(counts),'new_core_post_geometry_BFS':0},ensure_ascii=False));assert out['passed']
if __name__=='__main__':main()
