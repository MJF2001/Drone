from pathlib import Path
import sys,json,hashlib,copy
D=Path(__file__).resolve().parent;ROOT=D.parents[3];ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010';S=D/'source_snapshot'
sys.path.insert(0,str(ALGO/'.deps'));sys.path.insert(0,str(S))
import portable_frozen
from audit import audit
from prepare_road_range_diagnostic_20261015 import snapshot
from verify_road_range_diagnostic_20261015 import independent_plan
from verify_outer_connector_diagnostic_20261016 import assignment
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def check_unique(rows):assert len(rows)==len({x['run_id'] for x in rows})
def check_core(old,l,r,required,core,patch):
 assert patch and patch[0]==old[l] and patch[-1]==old[r]
 assert set(map(tuple,required))<=set(map(tuple,patch))
 assert core==old[:l]+patch+old[r+1:]
def check_result(j,x):
 assert x['job']==j and x['worker_status']=='returned'
 assert sha(j['case'])==j['case_sha256']
 c=read(j['case']);raw=x['raw'];route=tuple(map(tuple,raw.get('route',[])))
 assert not route or audit(snapshot(c),route)['valid']
 assert raw['budget']==j['budget'] and raw['seed']==j['seed']
 for module,e in x['loaded_modules'].items():
  path=Path(e['path']);assert sha(path)==e['sha256']
  assert str(S) in str(path) or str(ALGO/'.deps') in str(path)
 assert any(e['path'].endswith('p2_search_audit.py') for e in x['loaded_modules'].values())
 if j['method']!='P2_MULTI':
  plan=independent_plan(c);d=raw['detail']
  if d['range_plan'] is not None:assert d['range_plan']==plan
  cfg=plan['plans'][j['method'].replace('RANGE_','R_')]
  if d['responsibilities'] is not None:assert d['responsibilities']==assignment(c,cfg)
  if raw.get('core_route'):
   assert audit(snapshot(c),tuple(map(tuple,raw['core_route'])))['valid']
   check_core(c['old_route'],cfg['left'],cfg['right'],cfg['required'],raw['core_route'],raw['core_patch'])
   assert d['outside']['prefix']==c['old_route'][:cfg['left']+1] and d['outside']['suffix']==c['old_route'][cfg['right']:]
 return bool(route)
def main(mode):
 pre=mode=='preflight';pr=read(D/('preflight_protocol.json' if pre else 'protocol.json'))
 for p,h in pr['protected_hashes'].items():assert sha(p)==h,('unknown protected source/input change',p)
 folder=D/('preflight' if pre else 'formal');rows=[json.loads(x) for x in (folder/'attempts.jsonl').read_text(encoding='utf-8').splitlines()];check_unique(rows)
 jobs={j['run_id']:j for j in pr['jobs']};assert set(jobs)=={x['run_id'] for x in rows}
 valid=0
 for row in rows:
  j=jobs[row['run_id']];assert row['job']==j and not row['watchdog'] and row['returncode']==0
  valid+=check_result(j,read(row['result_path']))
 print(json.dumps({'status':'PASS','mode':mode,'tasks':len(rows),'valid_routes':valid,'read_only':True,'solver_calls':0},indent=2))
if __name__=='__main__':main(sys.argv[1])
