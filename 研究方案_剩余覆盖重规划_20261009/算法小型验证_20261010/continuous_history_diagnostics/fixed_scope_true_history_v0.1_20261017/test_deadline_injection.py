from pathlib import Path
import sys,json
D=Path(__file__).resolve().parent;R=D.parents[3];A=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
sys.path.insert(0,str(A/'.deps'));sys.path.insert(0,str(D/'source_snapshot'))
import portable_frozen
import fixed_scope_candidate as c
from model import Snapshot,DeadlineExceeded
from audit import audit
s=Snapshot('deadline_after_accepted_fallback',frozenset((x,y) for x in range(3) for y in range(2)),frozenset({(1,0),(2,0)}),frozenset(),(0,0),(0,0),((0,0),(1,0),(2,0),(1,0),(0,0)),0,100)
original=c.engine_solve;rows=[]
def interrupted_engine(*args,**kwargs):raise DeadlineExceeded()
c.engine_solve=interrupted_engine
try:
 for scope in ['R_SEED','R_PLUS1','R_PLUS2','R_ALL']:
  x=c.solve(s,set(s.targets),'LITERAL',3,0,scope_name=scope)
  assert audit(s,x['route'])['valid']
  assert x['detail']['acceptances'] and c.digest(x['route'])==x['detail']['acceptances'][-1]['route_sha256']
  assert not x['core_route'] or x['detail']['core_acceptances']
  rows.append({'scope':scope,'status':x['status'],'source':x['source'],'accepted_route_preserved':True})
finally:c.engine_solve=original
(D/'deadline_injection_results.json').write_text(json.dumps({'status':'PASS','fixture_calls':len(rows),'rows':rows},indent=2),encoding='utf-8')
print('PASS synthetic engine cutoff, 4 fixture calls')
