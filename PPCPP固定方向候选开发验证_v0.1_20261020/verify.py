"""Only stdlib source/hash/arithmetic recheck; never imports a planner."""
from stage_a import *
def main():
 manifest=read(H/'manifest.json')
 for name,h in manifest.items():assert sha(H/name)==h,name
 actual={str(p.relative_to(H)) for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log') and '__pycache__' not in p.parts};assert actual==set(manifest)
 d=json.loads(json.dumps(compute()));assert d==read(H/'stage_a_results.json')
 assert d['new_solver_calls']==d['B2_core_calls']==d['B3_entries']==d['C_entries']==0
 assert d['admissible_by_angle']=={'0':54,'90':0,'180':54,'270':0}
 assert not any((H/name).exists() for name in ('execution','gates','candidate.py','worker.py','completion.json'))
 print(json.dumps(dict(verified=True,new_solver_calls=0,stage='A_STOP_SEMANTIC_INTERFACE',admissible_by_angle=d['admissible_by_angle'],input_count=len(d['records']),source_count=len(d['source_hashes']),status='已封存，待负责人审核'),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
