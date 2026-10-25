"""Reuse accepted diagnostic modules; bind N input and reverse goal configuration."""
from common import *
import sys,subprocess,difflib,platform
from eventdep_labels import label,validate
OLD=ROOT/'覆盖受阻恢复目标单变量诊断_v0.1_20261023'
BASE=ROOT/'覆盖阶段真实受阻两例成对诊断_v0.1_20261023'
MODULES=('native','hook','runtime','candidate','decision_audit','compare','worker')
def main():
 assert not (H/'plan.json').exists()
 for d in ('inputs','specs','reused_E','outputs','logs','source_snapshot'):(H/d).mkdir(exist_ok=True)
 assert (H/'root_before.md').read_bytes()==(ROOT/'当前进度与下一步.md').read_bytes()
 p=subprocess.run([sys.executable,'-B','-X','utf8',str(OLD/'verify.py')],capture_output=True,encoding='utf-8');assert p.returncode==0,p.stdout+p.stderr
 dump(H/'previous_verify_at_start.json',dict(json.loads(p.stdout),root_sha256_at_start=sha(ROOT/'当前进度与下一步.md'),old_final_sha256=sha(OLD/'final_receipt.json')))
 guards=read(OLD/'source_guards.json')
 for f,d in read(OLD/'final_receipt.json')['files'].items():assert sha(OLD/f)==d;guards[str(OLD/f)]=d
 guards[str(OLD/'final_receipt.json')]=sha(OLD/'final_receipt.json')
 (H/'source_snapshot/执行稿.md').write_bytes((ROOT/'恢复目标收益事件依赖性补齐执行稿_给sol_20261023.md').read_bytes())
 bindings=[]
 for tail in MODULES:
  src=OLD/('recovery_diag_'+tail+'.py');name='eventdep_diag_'+tail+'.py';a=src.read_text(encoding='utf-8');b=a.replace('recovery_diag_','eventdep_diag_')
  if tail=='compare':b=b.replace('old_B_E','old_B_N')
  if tail=='worker':
   b=b.replace("result={'job':job,", "result={'environment':job['environment'],'target_label':job['target_label'],'target_intervention_enabled':job['target_intervention_enabled'],'job':job,")
   b=b.replace("coreend=time.perf_counter();result['native']=native;", "coreend=time.perf_counter();native.update(environment=job['environment'],target_label=job['target_label'],target_intervention_enabled=job['target_intervention_enabled']);result['native']=native;")
  out=H/name
  if a==b:out.write_bytes(src.read_bytes())
  else:out.write_text(b,encoding='utf-8')
  (H/'source_snapshot'/(name+'.diff')).write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=str(src),tofile=name)),encoding='utf-8')
  bindings.append({'source':str(src),'source_sha256':sha(src),'destination':name,'destination_sha256':sha(out),'byte_identical':src.read_bytes()==out.read_bytes(),'namespace_only_equal':b.replace('eventdep_diag_','recovery_diag_')==a,'changes':'namespace only; compare baseline config key E->N; worker stable output tags only'})
 # Accepted serial controller only changes unique import prefix and log labels.
 a=(OLD/'run.py').read_text(encoding='utf-8');b=a.replace('recovery_diag_','eventdep_diag_').replace("'arm':j['arm'],'core':1", "'arm':j['arm'],'environment':j['environment'],'target_label':j['target_label'],'target_intervention_enabled':j['target_intervention_enabled'],'core':1")
 (H/'run.py').write_text(b,encoding='utf-8');(H/'source_snapshot/run.py.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='accepted serial runner',tofile='new N runner')),encoding='utf-8')
 selected=[];reused=[]
 for ci,c in enumerate(read(BASE/'selection.json')['selected']):
  inp=H/'inputs'/(c['id']+'__N.json');inp.write_bytes((BASE/c['N']).read_bytes());n=read(inp);e=read(BASE/c['E']);assert sha(inp)==c['sources']['N']['sha256']
  assert all(n[k]==e[k] for k in n if k not in ('free','targets')) and ps(n['targets'])-ps(n['covered'])==ps(e['targets'])-ps(e['covered'])
  first=read(BASE/'outputs'/f"formal__{c['id']}__20261020__B__N.json");trace=first['native']['raw']['trace'];k=[60,29][ci];event=trace[k];cursor=event['index'];route=first['native']['raw']['route'];pending=ps(n['targets'])-ps(n['covered'])-ps(route[:cursor+1]);prior_spec=read(OLD/'specs'/(c['id']+'.json'))
  assert event['kind']=='recovery' and event['goal']==prior_spec['alternative_goal'] and trace[:k]==prior_spec['original_trace'][:k] and pending==ps(prior_spec['pending'])
  spec={'case':c['id'],'environment':'N','trace_record':k,'route_index_from_saved_trace':cursor,'current':event['current'],'previous':event['previous'],'pending':[list(p) for p in sorted(pending)],'default_goal':event['goal'],'alternative_goal':prior_spec['default_goal'],'T0':event['goal'],'T1':prior_spec['default_goal'],'original_trace':trace,'original_route_prefix':route[:cursor+1],'initial_U':len(ps(n['targets'])-ps(n['covered'])),'source_N':c['sources']['N'],'source_E':c['sources']['E'],'old_E_spec':str(OLD/'specs'/(c['id']+'.json')),'offline_pair_selected_from_seen_divergence':True}
  sp=H/'specs'/(c['id']+'.json');dump(sp,spec);selected.append({'id':c['id'],'base_id':c['base_id'],'shape':'Z','input':str(inp.relative_to(H)),'spec':str(sp.relative_to(H)),'N_source':str(BASE/c['N']),'N_sha256':sha(BASE/c['N']),'E_source':str(BASE/c['E']),'E_sha256':sha(BASE/c['E'])})
  for seed in (20261020,20261021,20261022):
   bn=read(BASE/'outputs'/f"formal__{c['id']}__{seed}__B__N.json");assert bn['native']['raw']['trace']==trace and bn['native']['raw']['route']==route
   for arm in ('OFF','ON'):
    src=OLD/'outputs'/f"formal__{c['id']}__{seed}__{arm}.json";x=read(src);enabled=arm=='ON';tl=label('E',enabled)
    assert x['passed'] and x['independent']['passed'] and x['decision_audit']['passed'] and x['native']['diagnostic']['trigger']['pending']==spec['pending']
    assert x['native']['raw']['trace'][:k]==trace[:k] and x['native']['raw']['route'][:cursor+1]==spec['original_route_prefix']
    assert x['native']['diagnostic']['trigger']['chosen_goal']==spec[tl]
    ref={'id':src.stem,'case':c['id'],'seed':seed,'environment':'E','target_label':tl,'target_intervention_enabled':enabled,'original_arm':arm,'origin':'reused_E_not_new_call','source':str(src),'source_sha256':sha(src),'wrapper':'reused_E/'+src.stem+'.json'};validate(ref)
    dump(H/ref['wrapper'],dict(ref,saved_output=x));reused.append(ref)
 dump(H/'selection.json',{'selected':selected,'previous_E_package':str(OLD),'baseline_input_package':str(BASE),'new_E_R_P2_history_warmup_technical_calls':0})
 dump(H/'reused_E/index.json',{'references':reused,'reused_processing_outputs':12,'reused_views':24,'new_core_or_post_calls':0})
 jobs=[]
 for j in read(OLD/'plan.json')['jobs']:
  c=next(c for c in selected if c['id']==j['case']);new=dict(j);enabled=j['target_intervention_enabled'];oldbn=BASE/'outputs'/f"formal__{j['case']}__{j['seed']}__B__N.json"
  new.update(id=j['id'].replace('formal__','formal_N__'),environment='N',env='N',target_label=label('N',enabled),input=c['input'],spec=c['spec'],old_B_N=str(oldbn),old_B_N_sha256=sha(oldbn));new.pop('old_B_E');new.pop('old_B_E_sha256');validate(new);jobs.append(new)
 plan=dict(read(OLD/'plan.json'),jobs=jobs,pure_precheck_identities=6,new_E_R_P2_history_warmup_technical=0,reused_E_processing=12,reused_E_views=24,combined_processing_routes=24,combined_views=48)
 plan['time']='new N only same-batch OFF/ON cost; historical E clocks kept as provenance only, no cross-batch time difference-in-differences or speed ranking'
 plan['labels']='N_OFF=T0, N_ON=T1, reused E_ON=T0, reused E_OFF=T1; environment+target_label+enabled stored together'
 plan['formula']='D_N=L(N,T0)-L(N,T1); D_E=L(E,T0)-L(E,T1); I=D_E-D_N; separate raw/post, exact certified signs'
 dump(H/'plan.json',plan);dump(H/'source_guards.json',guards);dump(H/'bindings.json',{'module_copies':bindings,'accepted_runner':str(OLD/'run.py'),'accepted_runner_sha256':sha(OLD/'run.py'),'unchanged_algorithm_hook_audit_post':True,'configuration_changes_only':'unique namespace, N input/spec/default/alternative/reference binding, stable labels','no_original_monkeypatch':True})
 dump(H/'input_freeze.json',{'files':{str(p.relative_to(H)):sha(p) for folder in ('inputs','specs','reused_E') for p in (H/folder).rglob('*') if p.is_file()}})
 dump(H/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'threads':plan['thread_env'],'serial_fresh_process':True})
 dump(H/'preparation_repairs.json',{'used':0,'cap':2,'records':[]});print({'planned_new_N_core':12,'planned_new_N_post':12,'reused_E_outputs':12,'new_calls_so_far':0})
if __name__=='__main__':main()
