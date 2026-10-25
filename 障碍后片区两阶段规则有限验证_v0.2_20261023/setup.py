"""Bind existing evidence and fixed remaining calls; no task execution."""
from region_common import *
import difflib,ast
def setup():
 assert not (H/'plan.json').exists()
 for d in ('jobs','claims','outputs/worker','outputs/parent','audits/old','audits/new','regression','control','figures'):(H/d).mkdir(parents=True,exist_ok=True)
 f=read(OLD/'final_receipt.json');vr=read(OLD/'verify_receipt.json');assert vr['passed'] and vr['final_receipt_sha256']==sha(OLD/'final_receipt.json')
 assert (H/'root_before.md').read_bytes()==(OLD/'root_after.md').read_bytes() and sha(H/'root_before.md')==f['root_sha256']
 oldguards=dict(f['files']);oldguards.update({'final_receipt.json':sha(OLD/'final_receipt.json'),'verify_receipt.json':sha(OLD/'verify_receipt.json')})
 for p,v in oldguards.items():assert sha(OLD/p)==v,p
 dump(H/'old_package_guards.json',oldguards)
 registered=read(OLD/'plan.json');rows=read(OLD/'state_registry.json');qualified=[r['id'] for r in rows if r['status']=='qualified'];assert len(qualified)==9
 miss={r['id'] for r in read(OLD/'missing_jobs.json')};executed=[json.loads(z) for z in (OLD/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()];starts=[z for z in executed if z['event']=='started'];assert len(starts)==44
 selected=[j for j in registered['jobs'] if j['phase']=='formal' and j['slot'] in qualified and j['slot']!='G1-A'];assert len(selected)==16 and all(j['id'] in miss for j in selected)
 assert {j['slot'] for j in selected}=={'G1-B','G2-A','G3-A','G3-B','G4-A','G4-B','G5-A','G6-A'}
 assert not any(r['job']==j['id'] for r in starts for j in selected)
 jobs=[dict(j,id='v02__'+j['id'],old_job_id=j['id']) for j in selected]
 for j in jobs:dump(H/'jobs'/(j['id']+'.json'),j)
 plan={'jobs':jobs,'old_plan_sha256':sha(OLD/'plan.json'),'old_missing_sha256':sha(OLD/'missing_jobs.json'),'qualified_slots':qualified,'permanent_ineligible':['G2-B','G5-B','G6-B'],'old_saved_pair':'G1-A','new_core_cap':16,'new_post_cap':16,'old_actual_core':22,'old_actual_post':22,'cumulative_core_cap':38,'cumulative_post_cap':38,'original_cap':44,'budgets':registered['budgets'],'seed':registered['seed'],'source_slots':registered['slots'],'old_history_calls_to_repeat':0,'old_gate_calls_to_repeat':0,'old_G1_A_calls_to_repeat':0,'precheck_cases_cap':16,'pre_real_engineering_repair_cap':1,'stop_on_technical_error':True}
 dump(H/'plan.json',plan)
 bindings=[]
 for name in ('region_rule.py','region_native.py','frozen_reference.py'):
  assert sha(H/name)==sha(OLD/name);bindings.append(dict(copy=name,old=name,sha256=sha(H/name),byte_equal=True))
 for p in (H/'region_center_v01_20261023').rglob('*.py'):
  rel=str(p.relative_to(H));assert sha(p)==sha(OLD/rel);bindings.append(dict(copy=rel,old=rel,sha256=sha(p),byte_equal=True))
 for p in (H/'inputs').glob('*.json'):assert sha(p)==sha(OLD/'inputs'/p.name)
 dump(H/'immutable_bindings.json',bindings)
 diff=''.join(difflib.unified_diff((OLD/'region_audit.py').read_text(encoding='utf-8').splitlines(True),(H/'region_audit.py').read_text(encoding='utf-8').splitlines(True),fromfile='v0.1/region_audit.py',tofile='v0.2/region_audit.py'))
 (H/'审核器类型修复.diff').write_text(diff,encoding='utf-8')
 before=ast.parse((OLD/'region_audit.py').read_text(encoding='utf-8'));after=ast.parse((H/'region_audit.py').read_text(encoding='utf-8'));a=next(x for x in before.body if isinstance(x,ast.FunctionDef) and x.name=='audit');z=next(x for x in after.body if isinstance(x,ast.FunctionDef) and x.name=='audit');assert ast.dump(ast.Module(body=a.body[:-2],type_ignores=[]),include_attributes=False)==ast.dump(ast.Module(body=z.body[1:-2],type_ignores=[]),include_attributes=False),'semantic reconstruction changed'
 dump(H/'setup_receipt.json',dict(passed=True,old_bound_files=len(oldguards),immutable_algorithm_files=len(bindings),saved_inputs_byte_equal=True,remaining_jobs=len(jobs),scientific_semantics_prefix_unchanged=True,core_calls=0,post_calls=0,old_failed_status_preserved=True,dependency_binding_copied=True))
 for p in H.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
 freeze={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='active_freeze.json'};dump(H/'active_freeze.json',freeze)
 print('SETUP: 16 remaining entries fixed; old 22+22 bound; immutable algorithm bytes unchanged')
if __name__=='__main__':setup()
