import platform,sys
from common import H,R,save,sha
from geometry import geometry
def main():
 assert not (H/'protocol.json').exists()
 cases=[]
 for scale in ('s1','s2'):
  for shape in ('I','L'):
   for event in ('straight','corner','obstacle'):
    for progress in (25,60):
     cases.append(dict(id=f'{scale}_{shape}_{event}_p{progress}',scale=scale,shape=shape,event=event,progress=progress,base_id=f'{scale}_{shape}'))
 # Pure geometry upper bound before history or any solver outcome.
 checks=[]
 for c in cases:
  f0,t0,_=geometry(c['scale'],c['shape']);f,t,b=geometry(c['scale'],c['shape'],c['event'],(-99,-99));k=(len(t0)*c['progress']+99)//100
  assert len(f)<=48 and len(t)-k<=14 and t<=f0
  checks.append(dict(id=c['id'],free=len(f),old_targets=len(t0),published=len(t),pending_upper_bound=len(t)-k))
 roots=[R/'基线复现准备_20261019/独立版_v0.2',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source',R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/candidate_baselines/PPCPP_CORE4/v0.1_20261014/source']
 files=[p for root in roots for p in root.rglob('*.py')]
 files+=list(H.glob('*.py'))+[R/'portable_frozen.py',R/'基线复现准备_20261019/ppcpp_independent.py',R/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py',R/'评价指标完整补算与数据审计_v0.1_20261020/metrics.py',R/'评价指标完整补算与数据审计_v0.1_20261020/crosscheck.py',H/'预登记.md',R/'实验结论与PPCPP改进讨论_20261020/交给6.1sol_小图最优差距诊断执行稿_v1_20261020.md']
 save(H/'protocol.json',dict(version='v0.2_20261020',cases=cases,geometric_preflight=checks,files={str(p.relative_to(R)):sha(p) for p in sorted(set(files))},environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform()),exact_limits=dict(seconds=60,states=800000),ppcpp_budget=20,distance_budget=1000000,checkpoint_rule=['first_recovery_before','first_recovery_after','second_recovery_before'],max_official_queries=120))
 print('protocol fixed',sha(H/'protocol.json'),flush=True)
if __name__=='__main__':main()
