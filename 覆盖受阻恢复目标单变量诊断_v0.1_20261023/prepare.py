"""Copy frozen inputs and generate minimally changed, uniquely named modules."""
from common import *
import sys,subprocess,inspect,importlib.util,difflib,platform,os
OLD=ROOT/'覆盖阶段真实受阻两例成对诊断_v0.1_20261023'
CONTROL=ROOT/'中心区计时插桩影响核查_v0.1_20261022/run_check.py'
def changed(source,replacements,name):
 modified=source
 for a,b in replacements:
  assert modified.count(a)==1,(name,a);modified=modified.replace(a,b)
 (H/name).write_text(modified,encoding='utf-8')
 (H/'source_snapshot'/(name+'.diff')).write_text(''.join(difflib.unified_diff(source.splitlines(True),modified.splitlines(True),fromfile='frozen_original',tofile=name)),encoding='utf-8')
 return modified
def main():
 assert not (H/'plan.json').exists()
 for d in ('inputs','specs','outputs','logs','source_snapshot'):(H/d).mkdir(exist_ok=True)
 assert (H/'root_before.md').read_bytes()==(ROOT/'当前进度与下一步.md').read_bytes()
 v=subprocess.run([sys.executable,'-B','-X','utf8',str(OLD/'verify.py')],capture_output=True,encoding='utf-8');assert v.returncode==0,v.stdout+v.stderr
 dump(H/'previous_verify_at_start.json',dict(json.loads(v.stdout),root_sha256_at_start=sha(ROOT/'当前进度与下一步.md'),previous_final_sha256=sha(OLD/'final_receipt.json')))
 guards=read(OLD/'source_guards.json')
 for p,d in read(OLD/'final_receipt.json')['files'].items():assert sha(OLD/p)==d;guards[str(OLD/p)]=d
 guards[str(OLD/'final_receipt.json')]=sha(OLD/'final_receipt.json')
 for p in ('研究双方向与接续思路_新增任务与新障碍_20261023.md','评价主次确认_改进PPCPP直达_P2仅外部参照_20261023.md','PPCPP首次恢复完整试走_v0.1_20261020/首次恢复试走实现与开发结果_20261020.md','PPCPP首次恢复收益来源只读诊断_v0.1_20261020/首次恢复为何改善及为何未改善_20261020.md'):
  guards[str(ROOT/p)]=sha(ROOT/p)
 (H/'source_snapshot/执行稿.md').write_bytes((ROOT/'覆盖受阻恢复目标单变量诊断执行稿_给sol_20261023.md').read_bytes())
 selected=[]
 for ci,c in enumerate(read(OLD/'selection.json')['selected']):
  inp=H/'inputs'/(c['id']+'__E.json');inp.write_bytes((OLD/c['E']).read_bytes());e=read(inp)
  assert sha(inp)==c['sources']['E']['sha256'] and c['sources']['E']['path'].endswith('E_contract_v02.json')
  original=read(OLD/'outputs'/f"formal__{c['id']}__20261020__B__E.json");n=read(OLD/'outputs'/f"formal__{c['id']}__20261020__B__N.json")
  trace=original['native']['raw']['trace'];k=[60,29][ci];record=trace[k];cursor=record['index'];route=original['native']['raw']['route'];pending=ps(e['targets'])-ps(e['covered'])-ps(route[:cursor+1])
  assert len(pending)==[141,46][ci] and record['kind']=='recovery' and n['native']['raw']['trace'][:k]==trace[:k]
  assert cursor==record['index'] # read actual path index, never substitute trace number
  spec={'case':c['id'],'trace_record':k,'route_index_from_saved_trace':cursor,'current':record['current'],'previous':record['previous'],'pending':[list(p) for p in sorted(pending)],'default_goal':record['goal'],'alternative_goal':n['native']['raw']['trace'][k]['goal'],'original_trace':trace,'original_route_prefix':route[:cursor+1],'initial_U':len(ps(e['targets'])-ps(e['covered'])),'source_E':c['sources']['E'],'saved_E_source':str(OLD/c['E']),'saved_E_sha256':sha(OLD/c['E']),'saved_B_E_first_seed':str(OLD/'outputs'/f"formal__{c['id']}__20261020__B__E.json"),'saved_B_E_first_seed_sha256':sha(OLD/'outputs'/f"formal__{c['id']}__20261020__B__E.json"),'old_N_target_source':str(OLD/'outputs'/f"formal__{c['id']}__20261020__B__N.json"),'offline_target_not_online_capability':True}
  for seed in (20261020,20261021,20261022):
   other=read(OLD/'outputs'/f"formal__{c['id']}__{seed}__B__E.json");assert other['native']['raw']['trace']==trace and other['native']['raw']['route']==route
  sp=H/'specs'/(c['id']+'.json');dump(sp,spec);selected.append({'id':c['id'],'base_id':c['base_id'],'shape':'Z','input':str(inp.relative_to(H)),'spec':str(sp.relative_to(H)),'old_selection':c})
 dump(H/'selection.json',{'selected':selected,'old_package':str(OLD),'new_N_R_P2_calls':0,'new_maps':0})
 # Exact original source remains untouched. Generated modules have independent names.
 native=ROOT/'基线复现准备_20261019/独立版_v0.2/ppcpp.py';source=native.read_text(encoding='utf-8');(H/'source_snapshot/native_original.py.txt').write_text(source,encoding='utf-8')
 changed(source,[('ROOT=Path(__file__).resolve().parents[2]','ROOT=Path(__file__).resolve().parent.parent'),('_audit=single_cell_audit):','_audit=single_cell_audit,_diag=None):'),("goal=min(pending,key=lambda q:(g.distance(cur,q),q));tick();segment=g.path(cur,goal)","goal=min(pending,key=lambda q:(g.distance(cur,q),q));tick()\n                    if _diag is not None:goal=_diag.choose(trace,route,cur,prev,pending,goal,g);tick()\n                    segment=g.path(cur,goal)"),('trace.append(event);move(segment,pending)','if _diag is not None:_diag.record(trace,event,pending,route,segment);tick()\n                trace.append(event);move(segment,pending)')],'recovery_diag_native.py')
 cand=ROOT/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/candidate.py';source=cand.read_text(encoding='utf-8')
 changed(source,[('from runtime import native,DeadlineExceeded,NoPath','from recovery_diag_runtime import native,DeadlineExceeded,NoPath'),('mark,clock,geometry):','mark,clock,geometry,diagnostic=None):'),('_geometry=geometry);phases','_geometry=geometry,_diag=diagnostic);phases')],'recovery_diag_candidate.py')
 rt=ROOT/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/runtime.py';source=rt.read_text(encoding='utf-8')
 changed(source,[("native=module('last_native',R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py')","import recovery_diag_native as native\nfrom recovery_diag_hook import Diagnostic"),('geometry=native.UnifiedGeometry):','geometry=native.UnifiedGeometry,diagnostic_spec=None,target_intervention_enabled=False):'),('from candidate import solve','from recovery_diag_candidate import solve'),('c=json.loads(payload);validate(c);s=snapshot(c);mark(\'entry\')',"c=json.loads(payload);validate(c);s=snapshot(c);mark('entry');diagnostic=Diagnostic(diagnostic_spec,target_intervention_enabled,clock)"),('begin,deadline,phases,mark,clock,geometry)','begin,deadline,phases,mark,clock,geometry,diagnostic)\n  if raw[\'status\']==\'core_complete\':diagnostic.finish(raw)'),("wire=json.dumps(raw,ensure_ascii=False,allow_nan=False,separators=(',',':'));phases", "wire=json.dumps({'raw':raw,'diagnostic':diagnostic.export()},ensure_ascii=False,allow_nan=False,separators=(',',':'));phases"),('injection_events=events)','injection_events=events,diagnostic=diagnostic.export())')],'recovery_diag_runtime.py')
 spec=importlib.util.spec_from_file_location('_recovery_diag_accepted_control',CONTROL);C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
 src=inspect.getsource(C.worker);(H/'source_snapshot/accepted_worker.py.txt').write_text(src,encoding='utf-8')
 body=changed(src,[("dest=H/'outputs'/(job['id']+'.json');assert not dest.exists()","dest=H/'outputs'/(job['id']+'.json');assert not dest.exists();claim_destination(dest)"),("cold=time.perf_counter();runtime,p2=B.load_native();result['cold_import_seconds']=time.perf_counter()-cold","cold=time.perf_counter();runtime,p2=B.load_native();import recovery_diag_runtime as DRun;result['cold_import_seconds']=time.perf_counter()-cold"),("payload=(H/job['input']).read_bytes();c=json.loads(payload);original=deepcopy(c);result['input']=c","payload=(H/job['input']).read_bytes();c=json.loads(payload);original=deepcopy(c);result['input']=c;diagnostic_spec=read(H/job['spec'])"),("native=invoke_once(lambda:runtime.run_payload(payload,'PPCPP',20,job['seed']) if job['method']=='PPCPP' else p2.run_payload(payload,20,job['seed']),ledger,obs)","native=invoke_once(lambda:DRun.run_payload(payload,'PPCPP',20,job['seed'],diagnostic_spec=diagnostic_spec,target_intervention_enabled=job['target_intervention_enabled']),ledger,obs)"),("flush=time.perf_counter();dump(H/'outputs'/(job['id']+'_native_raw.json'),native);native_flush=time.perf_counter()-flush","result['loaded_diagnostic_sources']={}\n        for key in ('recovery_diag_runtime','recovery_diag_native','recovery_diag_candidate','recovery_diag_hook','recovery_diag_decision_audit','recovery_diag_compare'):\n            module=sys.modules[key];path=Path(module.__file__).resolve();rel=str(path.relative_to(H));assert sha(path)==read(H/'active_freeze.json')[rel];result['loaded_diagnostic_sources'][str(path)]=sha(path)\n        flush=time.perf_counter();dump(H/'outputs'/(job['id']+'_native_raw.json'),native);native_flush=time.perf_counter()-flush"),("result['independent_wall_seconds']=time.perf_counter()-independent_start","result['decision_audit']=decision_audit.audit(c,native,diagnostic_spec,job['target_intervention_enabled'])\n        result['off_equivalence']=compare_old_off(result) if not job['target_intervention_enabled'] else None\n        result['independent_wall_seconds']=time.perf_counter()-independent_start")],'recovery_diag_worker.py')
 # The generated worker function needs the same bindings, plus unique auditor/helper.
 header='from pathlib import Path\nfrom copy import deepcopy\nimport sys,json,time,traceback\nimport recovery_diag_decision_audit as decision_audit\nfrom recovery_diag_compare import compare_old_off,claim_destination\n'
 (H/'recovery_diag_worker.py').write_text(header+body,encoding='utf-8')
 jobs=[]
 def add(ci,seed,enabled,phase):
  c=selected[ci];arm='ON' if enabled else 'OFF';oldp=OLD/'outputs'/f"formal__{c['id']}__{seed}__B__E.json"
  jobs.append({'id':f"formal__{c['id']}__{seed}__{arm}",'case':c['id'],'base_id':c['base_id'],'seed':seed,'arm':arm,'target_intervention_enabled':enabled,'config':'OFF','core_detail_profile_enabled':False,'method':'PPCPP','branch':'B','env':'E','input':c['input'],'spec':c['spec'],'old_B_E':str(oldp),'old_B_E_sha256':sha(oldp),'phase':phase})
 add(0,20261020,False,'first_two_OFF_gate');add(1,20261020,False,'first_two_OFF_gate');add(0,20261020,True,'paired_first_seed_ON');add(1,20261020,True,'paired_first_seed_ON')
 pair=0
 for seed in (20261021,20261022):
  for ci in (0,1):
   for enabled in ((True,False) if pair%2==0 else (False,True)):add(ci,seed,enabled,'remaining_alternating_pairs')
   pair+=1
 dump(H/'plan.json',{'jobs':jobs,'processing_cap':12,'core_cap':12,'post_cap':12,'views_cap':24,'technical_core':0,'warmup':0,'new_N_R_P2':0,'seeds':[20261020,20261021,20261022],'pure_precheck_identities':8,'preparation_repair_cap':2,'budget':read(OLD/'plan.json')['budget'],'thread_env':read(OLD/'plan.json')['thread_env'],'stop':'first substantive equality/audit/implementation error; no code repair or retries after formal start; preserve missing slots; valid longer/equal continue','order':'two first-seed OFF gates first, only then two corresponding ON; remaining four seed-case pairs alternate ON/OFF first','OFF_meaning':'target intervention disabled; core detailed profiler OFF in BOTH arms','one_exogenous_change':'one recovery goal only; default nearest computed before replacement; same geometry/cache/path ties, no reset/rollout','time':'accepted OFF timing boundaries; diagnostic logging and two explanatory repeat distance calls inside main/core, encoding included; independent decision BFS/credit audits outside main'})
 for p in (native,cand,rt,CONTROL):guards[str(p)]=sha(p)
 dump(H/'source_guards.json',guards)
 dump(H/'bindings.json',{'original_native':str(native),'original_native_sha256':sha(native),'accepted_worker':str(CONTROL),'accepted_worker_sha256':sha(CONTROL),'original_independent_auditor':str(ROOT/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py'),'original_independent_auditor_sha256':sha(ROOT/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py'),'new_module_prefix':'recovery_diag_','core_copy_diff':'source_snapshot/recovery_diag_native.py.diff','unchanged_frozen_files':True,'unchanged_post_and_credit':True,'no_original_module_monkeypatching':True})
 dump(H/'input_freeze.json',{'files':{str(p.relative_to(H)):sha(p) for folder in ('inputs','specs') for p in (H/folder).rglob('*') if p.is_file()}})
 dump(H/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'threads':read(OLD/'plan.json')['thread_env'],'serial_fresh_process':True})
 dump(H/'preparation_repairs.json',{'used':0,'cap':2,'records':[]})
 print({'planned_core':len(jobs),'new_core_calls':0,'unique_states':2})
if __name__=='__main__':main()
