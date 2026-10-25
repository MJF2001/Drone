"""Stage A only: source text, recorded provenance, integer bounds. NO solver import."""
import json,hashlib,ast,datetime
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent
S=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
F=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source'
CORE=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/candidate_baselines/PPCPP_CORE4/v0.1_20261014/source/candidate_ppcpp_core4_20261014.py'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 with Path(p).open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def rot(p,k):
 x,y=p
 return [(x,y),(-y,x),(-x,-y),(y,-x)][k]
def compute():
 protocol=read(S/'protocol.json');manifest=read(S/'manifest.json');records=[]
 for item in protocol['inputs']:
  p=Path(item['path']);assert sha(p)==item['sha256']==sha(Path(item['source']));c=read(p);free=list(map(tuple,c['free']));pred=tuple(c['predator']);angles=[]
  for k in range(4):
   ff=[rot(q,k) for q in free];a=rot(pred,k);lo=min(q[0] for q in ff);hi=max(q[0] for q in ff);ylo=min(q[1] for q in ff);yhi=max(q[1] for q in ff)
   shift=(0,0) if k==0 else (-lo,-ylo)
   angles.append(dict(degrees=90*k,rotated_predator=a,rotated_bounds=[lo,hi,ylo,yhi],translation=shift,normalized_predator=[a[0]+shift[0],a[1]+shift[1]],normalized_bounds=[lo+shift[0],hi+shift[0],ylo+shift[1],yhi+shift[1]],passes_actual_x_predicate=a[0]<lo or a[0]>hi,predator_outside_flight_graph=a not in set(ff)))
  records.append(dict(id=item['id'],input=str(p.relative_to(R)),sha256=sha(p),fields=list(c),predator=pred,angles=angles))
 sample=sorted((S/'execution').glob('*__b20__r0__PPCPP.json'))[0];assert sha(sample)==manifest[str(sample.relative_to(S))];x=read(sample)
 source_paths=[S/'runtime.py',S/'candidate.py',S/'worker.py',S/'p2_adapter.py',S/'gates.py',S/'audit.py',S/'audit_adapter.py',R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py',R/'基线复现准备_20261019/ppcpp_independent.py',CORE,R/'portable_frozen.py',R/'PPCPP_LAST新开发地图验证_v0.1_20261020/spec.py',R/'PPCPP结构候选新开发验证_v0.1_20261020/validation.py',F/'model.py',F/'unified_geometry.py',F/'bfs_metric_geometry.py',F/'baseline_suite.py',F/'p2_search_audit.py',R/'评价指标完整补算与数据审计_v0.1_20261020/metrics.py',R/'评价指标完整补算与数据审计_v0.1_20261020/crosscheck.py']
 sources={str(p.relative_to(R)):sha(p) for p in source_paths}
 # Historical worker source paths/hash prove actual import identity, not folder-name inference.
 actual={p:h for p,h in x['production_hashes'].items() if Path(p).name in ('ppcpp.py','ppcpp_independent.py','candidate_ppcpp_core4_20261014.py','model.py','unified_geometry.py','bfs_metric_geometry.py','runtime.py','candidate.py')}
 for p,h in actual.items():assert sha(p)==h
 native=(R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py').read_text(encoding='utf-8');tree=ast.parse(native);solve=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='solve')
 calls=[ast.unparse(n.func) for n in ast.walk(solve) if isinstance(n,ast.Call)]
 assert 'core.reward_options' in calls and not any('predator_for' in name for name in calls)
 assert "predator outside fixed flight-domain x bounds required" in native
 assert all(len(r['fields'])==13 and r['predator']==(-1,0) for r in records)
 assert [sum(r['angles'][k]['passes_actual_x_predicate'] for r in records) for k in range(4)]==[54,0,54,0]
 return dict(stage='A_STOP_SEMANTIC_INTERFACE',new_solver_calls=0,B1_calls=0,B2_core_calls=0,B3_entries=0,B3_core_calls=0,C_entries=0,C_core_calls=0,observed_runtime_exceptions=0,note='Predicate is evaluated by integer arithmetic from frozen source; no planner called, no runtime rejection claimed.',actual_import_evidence=dict(output=str(sample.relative_to(R)),sha256=sha(sample),recorded_sources=actual),source_hashes=sources,records=records,admissible_by_angle={str(k*90):sum(r['angles'][k]['passes_actual_x_predicate'] for r in records) for k in range(4)},native_call_names=calls)
def main():
 assert not (H/'stage_a_results.json').exists();save(H/'stage_a_prereg.json',dict(created=datetime.datetime.now().astimezone().isoformat(),stage='A only before any planner invocation',method='read actual source and previous-worker hashes; evaluate the unmodified x-exterior contract on all54 public inputs at rotations0/90/180/270, optional common translation only; do not call check_contract/solve/BFS/native modules',stop='If consistent predator rotation conflicts with actual native admission rule, stop for reviewer decision; do not regenerate predator, bypass check, use inactive legacy generator, reduce to two directions, or change frozen code',planned_solver_calls=0))
 d=compute();save(H/'stage_a_results.json',d);print(json.dumps(dict(stage=d['stage'],admissible=d['admissible_by_angle'],new_solver_calls=0,observed_runtime_exceptions=0),ensure_ascii=False))
if __name__=='__main__':main()
