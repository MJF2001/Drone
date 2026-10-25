from common import *
from copy import deepcopy
import importlib.util,sys,inspect,difflib,platform,os
CONTROL=ROOT/'中心区计时插桩影响核查_v0.1_20261022'
OFF=ROOT/'中心区OFF全量质量时间开发比较_v0.1_20261022'
def main():
 assert not (H/'plan.json').exists()
 spec=importlib.util.spec_from_file_location('_accepted_control',CONTROL/'run_check.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
 for p,d in read(OFF/'active_freeze.json').items():assert sha(OFF/p)==d
 for p,d in read(H/'input_freeze.json')['files'].items():assert sha(H/p)==d
 guards=read(OFF/'source_guards.json');guards.update(read(H/'source_guards_selection.json'))
 for p in (CONTROL/'run_check.py',OFF/'run_full.py',OFF/'final_receipt.json',ROOT/'评价主次确认_改进PPCPP直达_P2仅外部参照_20261023.md',ROOT/'研究双方向与接续思路_新增任务与新障碍_20261023.md'):guards[str(p)]=sha(p)
 source=inspect.getsource(C.worker)
 oldline="native=invoke_once(lambda:runtime.run_payload(payload,'PPCPP',20,job['seed']) if job['method']=='PPCPP' else p2.run_payload(payload,20,job['seed']),ledger,obs)"
 assert oldline in source
 modified=source.replace(oldline,"native=invoke_once(lambda:repair_runtime.run_payload(payload,20,job['seed']),ledger,obs)")
 modified=modified.replace("rawname='A' if job['method']=='PPCPP' else 'C0';postname='B' if rawname=='A' else 'C'","rawname='A';postname='B'  # R raw/post aliases; job.branch identifies diagnostic R")
 modified=modified.replace("result['independent_wall_seconds']=time.perf_counter()-independent_start","result['independent']['repair_structure']=repair_runtime.audit_saved(c,result['native'])\n        result['independent_wall_seconds']=time.perf_counter()-independent_start")
 header='''from pathlib import Path
import sys,json,time,traceback
from copy import deepcopy
import repair_runtime
# Accepted OFF body below: only dispatch and R raw/post aliases / structural audit differ.
# C is bound by run.py before this function is invoked.
'''
 (H/'worker_r.py').write_text(header+modified,encoding='utf-8')
 (H/'source_snapshot/R_worker.diff').write_text(''.join(difflib.unified_diff(source.splitlines(True),modified.splitlines(True),fromfile='accepted_OFF_worker',tofile='diagnostic_R_worker')),encoding='utf-8')
 (H/'source_snapshot/accepted_OFF_worker.py.txt').write_text(source,encoding='utf-8')
 selected=read(H/'selection.json')['selected'];jobs=[];pairnum=0
 for ci,c in enumerate(selected):
  for si,seed in enumerate((20261020,20261021,20261022)):
   branches=['B','R','C'];k=(ci+si)%3;branches=branches[k:]+branches[:k]
   if (ci+si)%2:branches.reverse()
   for branch in branches:
    envs=('N','E') if pairnum%2==0 else ('E','N');pairnum+=1
    for env in envs:
     jobs.append({'id':f"formal__{c['id']}__{seed}__{branch}__{env}",'case':c['id'],'base_id':c['base_id'],'branch':branch,'env':env,'method':{'B':'PPCPP','R':'R','C':'P2_MULTI'}[branch],'config':'OFF','seed':seed,'input':c[env],'phase':'formal'})
 assert len(jobs)==18*len(selected)<=108
 dump(H/'plan.json',{'jobs':jobs,'m':len(selected),'processing_cap':108,'core_cap':72,'R_cap':36,'technical_core_cap':0,'warmup_cap':0,'seeds':[20261020,20261021,20261022],'budget':{'native_or_repair':20,'post_soft':18,'post_candidate':4096,'post_total_late_only':20,'parent':150},'thread_env':read(OFF/'plan.json')['thread_env'],'order':'case lexical distinct base then seed, cyclic/reversed branch rotation; adjacent N/E order strictly alternates by branch pair','R_neighbors':[[1,0],[0,1],[-1,0],[0,-1]],'precheck_cases':12,'preparation_repair_cap':2,'stop':'first substantive formal error; no retry or replacement; valid deadline/late output kept; legal negative effect does not stop','R_views':'A=R raw, B=R post, distinguished by job.branch=R; kept aliases to reuse unchanged independent audit grid contract','timing':'accepted OFF body unchanged for B/C; R same boundaries, charged runtime detection+BFS+assembly, source checks/cold/flush/independent outside as OFF; post-return source checks inside','source_states_are_labels_only':'old corner/obstacle labels identify cut witnesses; original expansion inputs NOT reused; N reconstructed from actual prep map/targets, E changes only free','no_closed_loop':True})
 dump(H/'source_guards.json',guards)
 dump(H/'bindings.json',{'accepted_OFF_worker_file':str(CONTROL/'run_check.py'),'accepted_OFF_worker_sha256':sha(CONTROL/'run_check.py'),'accepted_worker_function_sha256':__import__('hashlib').sha256(source.encode()).hexdigest(),'B_C_direct_reuse':True,'R_worker_diff':'source_snapshot/R_worker.diff','core_files_unmodified':True,'post_and_credit_unmodified':True,'no_core_detailed_profile':True})
 dump(H/'environment.json',{'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'CPU':os.environ.get('PROCESSOR_IDENTIFIER'),'threads':read(OFF/'plan.json')['thread_env'],'serial_fresh_process_per_entry':True,'cross_entry_cache':False})
 print({'prepared_entries':len(jobs),'core_planned':sum(j['branch']!='R' for j in jobs),'R_planned':sum(j['branch']=='R' for j in jobs),'new_core_calls':0})
if __name__=='__main__':main()
