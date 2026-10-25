from common import *
from spec import nearest
from exact import solve
from independent import oracle,certificate_audit
def test_case(f,t,cur=(0,0),h=set()):return dict(free=sorted(f),targets=sorted(t),covered=sorted(h),base=(0,0),current=cur)
def main():
 protect();assert read(H/'tests/results.json')['passed'];rows=[]
 line={(i,0) for i in range(4)};square={(x,y) for x in range(4) for y in range(3)}
 cases=[('tie',test_case(square,{(1,0),(0,1)}),(0,1)),('empty',test_case(square,{(0,0)},h={(0,0)}),None),('current_credit',test_case(square,{(0,0),(2,0)}),(2,0)),('graph_distance',test_case(square-{(1,0),(1,1)},{(2,0),(0,2)}),(0,2))]
 for name,c,e in cases:
  r=nearest(c);assert r['emin']==e;rows.append(dict(name=name,input=c,result=r))
 # Mandatory collection in a one-cell bridge makes this requested last impossible.
 r=solve(line,(0,0),(0,0),{(1,0),(3,0)},last=(1,0),certificate=H/'tests/mandatory_last.gz');assert r['status']=='infeasible' and oracle(line,(0,0),(0,0),{(1,0),(3,0)},(1,0)) is None
 certificate_audit(line,r,H/'tests/mandatory_last.gz');rows.append(dict(name='mandatory_last_infeasible',result=r))
 # Current target is already collected; cannot enter the candidate pending set.
 assert nearest(test_case(line,{(1,0),(3,0)},cur=(1,0)))['emin']==(3,0);rows.append(dict(name='current_not_last_candidate',passed=True))
 # The reuse mapping uses equality of input-only near candidate and saved e0.
 from run import query_map
 assert query_map((1,0),(1,0),True)==dict(A='A',B='B',C='B');assert query_map(None,None,False)==dict(A='A',B=None,C=None)
 rows.append(dict(name='reuse_and_empty_mapping',passed=True))
 # Test cap label remains unresolved; original reviewed tests also inject caps.
 t=solve(square,(0,0),(0,0),{(3,2)},max_states=1);assert t['status']=='unresolved';rows.append(dict(name='cap_not_infeasible',result=t))
 save(H/'tests/new_gates.json',dict(passed=True,count=len(rows),rows=rows))
 golden=R/'PPCPP小图最优差距诊断_v0.2_20261020';gates=[]
 for name in ('s1_I_corner_p25','s2_L_corner_p60'):
  inp=golden/'inputs'/f'{name}.json';c=read(inp);out=solve_payload(json.dumps(c));pa.audit(c,out['raw']);g=read(golden/'execution'/f'{name}.json')
  for field in ('route','trace'):assert json.loads(json.dumps(out['raw'][field]))==g['raw'][field]
  gates.append(dict(name=name,input=str(inp.relative_to(R)),input_sha256=sha(inp),golden=str((golden/'execution'/f'{name}.json').relative_to(R)),golden_sha256=sha(golden/'execution'/f'{name}.json'),result=out))
 save(H/'gates.json',gates);print('new fixed gates',len(rows),'wrapper equivalence',len(gates),flush=True)
if __name__=='__main__':main()
