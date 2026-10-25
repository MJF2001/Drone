from common import *
import importlib.util,sys,io,contextlib,ast,difflib
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def main():
 start=time.perf_counter();assert not (H/'manifest.json').exists()
 (H/'root_before.md').write_bytes((ROOT/'当前进度与下一步.md').read_bytes())
 for d in ('protocol','crops','crop_audits','outputs','audits','logs','technical','figures'):(H/d).mkdir(exist_ok=True)
 (H/'protocol/执行稿.md').write_bytes((ROOT/'障碍后接续估计器影子评估执行稿_给sol_20261023.md').read_bytes())
 # Previous verifiers demand their historical root byte image. Project that one
 # path only; separately verify every suffix/hash link to the actual current root.
 class HistoricalRoot:
  def __init__(self,package):self.package=package
  def __truediv__(self,key):return self.package/'root_after.md' if key=='当前进度与下一步.md' else ROOT/key
 receipts=[]
 for i,package in enumerate((BASE,VAR,STRUCT)):
  m=load('_shadow_source_verify_'+str(i),package/'verify.py')
  original=m.ROOT
  if package!=STRUCT:m.ROOT=HistoricalRoot(package)
  capture=io.StringIO();begin=time.perf_counter()
  with contextlib.redirect_stdout(capture):r=m.verify()
  r.update(wall_seconds=time.perf_counter()-begin,source=str(package),verify_source_sha256=sha(package/'verify.py'),final_receipt_sha256=sha(package/'final_receipt.json'),root_scope='actual current root' if package==STRUCT else 'unchanged historical root_after projection; actual current suffix chain separately checked')
  dump(H/'protocol'/('source_verify_'+str(i)+'.json'),r);receipts.append(r);m.ROOT=original
 assert read(STRUCT/'final_receipt.json')['root_sha256']==sha(H/'root_before.md')
 assert (H/'root_before.md').read_bytes().endswith((STRUCT/'root_before.md').read_bytes())
 assert read(VAR/'final_receipt.json')['root_sha256']==sha(STRUCT/'root_before.md')
 assert read(BASE/'final_receipt.json')['root_sha256']==sha(VAR/'root_before.md')
 guards=read(STRUCT/'source_guards.json')
 for package in (BASE,VAR,STRUCT):
  ff=read(package/'final_receipt.json')
  for p,v in ff['files'].items():assert sha(package/p)==v;guards[str(package/p)]=v
  for n in ('verify.py','final_receipt.json','verify_receipt.json'):guards[str(package/n)]=sha(package/n)
 origin=ROOT/'中心区PPCPP直达质量时间开发比较_v0.1_20261022/center_bench_v01_20261022'
 copies=[]
 for src in sorted(origin.rglob('*.py')):
  dest=H/'frozen_shadow_center_20261023'/src.relative_to(origin);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes());guards[str(src)]=sha(src);copies.append(dict(source=str(src),copy=str(dest.relative_to(H)),source_sha256=sha(src),copy_sha256=sha(dest),change='byte identical'))
 connector=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source'
 (H/'frozen_shadow_connector_20261023').mkdir();(H/'frozen_shadow_connector_20261023/__init__.py').write_text('',encoding='utf-8')
 differences=[]
 for name in ('model.py','bfs_metric_geometry.py','unified_geometry.py'):
  src=connector/name;s=src.read_text(encoding='utf-8-sig');t=s.replace('from model import','from .model import').replace('from bfs_metric_geometry import','from .bfs_metric_geometry import');dest=H/'frozen_shadow_connector_20261023'/name;dest.write_text(t,encoding='utf-8');guards[str(src)]=sha(src)
  differences+=list(difflib.unified_diff(s.splitlines(True),t.splitlines(True),fromfile=str(src),tofile=str(dest)))
  copies.append(dict(source=str(src),copy=str(dest.relative_to(H)),source_sha256=sha(src),copy_sha256=sha(dest),change='relative import names only; path algorithm/ties unchanged'))
 (H/'protocol/connector_import_only.diff').write_text(''.join(differences),encoding='utf-8')
 dump(H/'protocol/source_copies.json',copies)
 index=read(STRUCT/'pair_index.json');assert len(index)==19
 slots=[]
 for ix in index:
  for arm in ('OFF','ALT1'):slots.append(dict(id=ix['key']+'__'+arm,key=ix['key'],arm=arm,dataset=ix['dataset'],base_geometry=ix['base_geometry'],crop='crops/'+ix['key']+'__'+arm+'.json'))
 policy=dict(local_edge_cap=16,total_edge_cap=64,stop_priority=['all_pending_collected','total_64','next_recovery_after_q','local_16'],tail_order='frozen pre-event old_order; first remaining occurrence; incidental collection; no fallback',connector='fresh UnifiedGeometry per arm, original lexicographically oriented Astar tie, no cross-arm cache',tail_new_edge_cap=4096,tail_soft_seconds=20,post_soft_seconds=18,post_candidate_cap=4096,post_late_seconds=20,outer_seconds=150,numeric_epsilon_m='0.00000001',prediction='q1 iff both eligible and delta_hat < -1e-8 certified; else q0 with reason',core_calls=0,tail_cap=38,post_cap=38,technical_case_cap=20,technical_repair_cap=1,stage='A only: saved finite-prefix diagnostic, not online timing')
 dump(H/'manifest.json',dict(created_utc=time.time(),policy=policy,policy_sha256=digest(policy),slots=slots,input_whitelist=['schema','id','key','arm','event','seed','old_order','common_prefix','choice_state','selected_q','finite_prefix','stop_state'],datasets=dict(base=12,variants=7,missing_ineligible=5),truth_release='only after predictions_seal.json',old_root_history_verified=True))
 dump(H/'source_guards.json',guards)
 dump(H/'setup_receipt.json',dict(passed=True,source_verify_receipts=3,source_bindings=len(guards),slots=len(slots),wall_seconds=time.perf_counter()-start,new_core=0,new_post=0,new_connector=0))
 print(dict(prepared=True,slots=len(slots),source_bindings=len(guards),seconds=time.perf_counter()-start))
if __name__=='__main__':main()
