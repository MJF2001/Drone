from pathlib import Path
import sys,json,hashlib,subprocess,os
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';S=D/'source_snapshot'
sys.path.insert(0,str(ALGO/'.deps'));sys.path.insert(0,str(S))
import portable_frozen
from verify_road_range_diagnostic_20261015 import independent_plan
from verify_outer_connector_diagnostic_20261016 import assignment
from prepare_road_range_diagnostic_20261015 import snapshot
import fixed_scope_candidate as candidate
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=read(D.parent/'acceptance_and_range_rules_v0.2_20261017/range_details_final.json');rows=[]
for state in old['states']:
 c=read(state['case_path']);ps=lambda x:set(map(tuple,x));published=ps(c['metadata']['published_targets']);covered=ps(c['covered']);free=ps(c['free'])
 assert ps(c['targets'])==published&free and ps(c['metadata']['deferred_targets'])==(published-covered)-free
 plan=independent_plan(c);actual=json.loads(json.dumps(candidate.range_plan(snapshot(c),ps(c['metadata']['initial_targets']))));assert actual==plan
 for rr in state['ranges']:
  cfg=plan['plans'][rr['name']];assert cfg==rr['cfg']
  assert assignment(c,cfg)==json.loads(json.dumps(candidate.responsibilities(snapshot(c),cfg)))
 rows.append({'map_id':state['map_id'],'plan':plan,'aliases':state['range_aliases']})
(D/'input_scope_gates.json').write_text(json.dumps({'status':'PASS','states':rows},ensure_ascii=False,indent=2),encoding='utf-8')
# Run only the relevant 10 continuous-history and 15 outer-connector regressions.
cmd=[sys.executable,'-B','-X','utf8','-m','unittest','test_continuous_history_20261016','test_outer_connector_20261016','-v']
r=subprocess.run(cmd,cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,encoding='utf-8');(D/'related_regressions.log').write_text(r.stdout+r.stderr,encoding='utf-8');assert r.returncode==0
print('PASS input/scope gates; relevant regressions saved')
