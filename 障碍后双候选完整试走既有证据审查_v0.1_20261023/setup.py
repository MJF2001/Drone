from common import *
import importlib.util,sys,io,contextlib
def main():
 start=time.perf_counter();assert not (H/'manifest.json').exists();(H/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes());(H/'protocol').mkdir(exist_ok=True);(H/'source_snapshot').mkdir(exist_ok=True)
 (H/'protocol/执行稿.md').write_bytes((ROOT/'障碍后双候选完整试走既有证据与成本审查执行稿_给sol_20261023.md').read_bytes())
 # The only old code executed is the latest stdlib-only read-only verifier.
 # FIRST, algorithm modules, post and geometry are NEVER imported.
 spec=importlib.util.spec_from_file_location('_double_saved_shadow_verify',SHADOW/'verify.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 with contextlib.redirect_stdout(io.StringIO()):receipt=m.verify()
 receipt.update(source=str(SHADOW/'verify.py'),source_sha256=sha(SHADOW/'verify.py'),final_sha256=sha(SHADOW/'final_receipt.json'),root_scope='actual current root; no historical projection in this review');dump(H/'protocol/开工影子包只读核验.json',receipt)
 assert receipt['passed'] and read(SHADOW/'final_receipt.json')['root_sha256']==sha(H/'root_before.md')
 guards=read(SHADOW/'source_guards.json');sealed=Counter()
 for package in (BASE,VAR,STRUCT,SHADOW):
  ff=read(package/'final_receipt.json')
  for rel,v in ff['files'].items():assert sha(package/rel)==v,(package.name,rel);guards[str(package/rel)]=v;sealed[package.name]+=1
  for rel in ('final_receipt.json','verify_receipt.json'):guards[str(package/rel)]=sha(package/rel)
 # The former roots are frozen byte images, linked without changing manifests.
 assert read(STRUCT/'final_receipt.json')['root_sha256']==sha(SHADOW/'root_before.md')
 assert read(VAR/'final_receipt.json')['root_sha256']==sha(STRUCT/'root_before.md')
 assert read(BASE/'final_receipt.json')['root_sha256']==sha(VAR/'root_before.md')
 for later,earlier in ((SHADOW,STRUCT),(STRUCT,VAR),(VAR,BASE)):
  assert (later/'root_before.md').read_bytes()==(earlier/'root_after.md').read_bytes()
 for rel,v in read(FIRST/'manifest.json').items():assert sha(FIRST/rel)==v,('FIRST manifest',rel);guards[str(FIRST/rel)]=v
 first_protocol=read(FIRST/'protocol.json')
 for file,v in first_protocol['files'].items():assert sha(file)==v,('FIRST protocol source',file);guards[file]=v
 guards[str(FIRST/'manifest.json')]=sha(FIRST/'manifest.json')
 sources=[BASE/'worker.py',BASE/'run.py',BASE/'common.py',BASE/'expand_native.py',BASE/'expand_hook.py',BASE/'decision_audit.py',BASE/'export_results.py',FIRST/'rollout.py',FIRST/'worker.py',FIRST/'checks.py',FIRST/'audit_branch.py',FIRST/'run.py',FIRST/'预登记.md',FIRST/'首次恢复试走实现与开发结果_20261020.md',ROOT/'基线复现准备_20261019/独立版_v0.2/ppcpp.py']
 center=ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022'
 sources.extend(center/n for n in ('post/engine.py','metrics.py','bench.py','service.py','audit/_post_saved.py'))
 snapshots=[]
 for i,src in enumerate(sources):
  dest=H/'source_snapshot'/(f'{i:02d}_'+src.name);dest.write_bytes(src.read_bytes());guards[str(src)]=sha(src);snapshots.append(dict(source=str(src),copy=str(dest.relative_to(H)),sha256=sha(src),line_count=len(textread(src).splitlines())))
 dump(H/'source_snapshot/index.json',snapshots)
 dump(H/'source_guards.json',guards)
 rows=read(BASE/'state_registry.json');assert len(rows)==12 and all(r['status']=='qualified' for r in rows)
 dump(H/'manifest.json',dict(scope='read-only saved two-candidate reference/cost/static FIRST review',states=[r['id'] for r in rows],state_count=12,base_geometries=6,seed=20261020,response_timing_observations=dict(REF=12,OFF=12,ALT1=12),history_only_source_boundary=6,variants_only_repetition_context=True,choice_rule='certified complete shortcut distance; tie OFF; no winner rerun',first_imported=False,prohibited_new_calls=dict(core=0,history=0,post=0,path_distance_search=0,geometry_visibility=0,candidate_route=0,counterfactual=0,training=0,profile_experiment=0),created_utc=time.time(),root_chain=True))
 dump(H/'setup_receipt.json',dict(passed=True,wall_seconds=time.perf_counter()-start,counts=dict(C),old_sealed_files=dict(sealed),FIRST_manifest_bindings=len(read(FIRST/'manifest.json')),FIRST_protocol_bindings=len(first_protocol['files']),source_guards=len(guards),actual_current_root_verified=True,no_projection_used=True,source_algorithm_imports=0,new_experiment_calls=0))
 print(dict(prepared=True,states=12,source_guards=len(guards),seconds=time.perf_counter()-start))
if __name__=='__main__':
 try:main()
 except BaseException as e:fail_record('setup',e);raise
