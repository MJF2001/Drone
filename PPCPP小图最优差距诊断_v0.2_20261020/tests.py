from common import H,save
from exact import solve
from independent import oracle,certificate_audit
def fixtures():
 line={(i,0) for i in range(4)};square={(x,y) for x in range(3) for y in range(2)}
 return [
 ('empty_return',line,(3,0),(0,0),set(),None),
 ('current_target',line,(1,0),(0,0),{(1,0)},None),
 ('line',line,(0,0),(0,0),{(2,0),(3,0)},None),
 ('wide',square,(0,0),(0,0),square,None),
 ('obstacle',square-{(1,0)},(0,0),(0,0),{(2,0)},None),
 ('required_repeat',{(0,0),(1,0),(2,0),(1,1)},(1,0),(1,0),{(0,0),(2,0),(1,1)},None),
 ('unreachable_target',{(0,0),(2,0)},(0,0),(0,0),{(2,0)},None),
 ('unreachable_base',{(0,0),(2,0)},(0,0),(2,0),set(),None),
 ('history_blocked',{(0,0),(1,0),(1,1)},(0,0),(0,0),{(1,1)},None),
 ('equal_paths',square,(0,0),(0,0),{(2,1)},None),
 ('incidental_collection',line,(0,0),(0,0),{(1,0),(3,0)},None),
 ('last_constraint',square,(0,0),(0,0),{(1,0),(2,1)},(1,0)),
 ('last_current_impossible',square,(1,0),(0,0),{(1,0),(2,1)},(1,0))]
def main():
 out=[]
 for name,f,s,b,t,e in fixtures():
  cert=H/'tests'/f'{name}.gz';cert.parent.mkdir(exist_ok=True)
  r=solve(f,s,b,t,e,certificate=cert);v=oracle(f,s,b,t,e);assert r['length']==v and (r['status']=='optimal')==(v is not None)
  certificate_audit(f,r,cert);out.append(dict(name=name,expected=v,result=r))
 f={(x,y) for x in range(3) for y in range(2)};cells=sorted(f)
 for mask in range(64):
  t={p for i,p in enumerate(cells) if mask>>i&1}
  for e in [None]+sorted(t):
   r=solve(f,(0,0),(0,0),t,e);assert r['length']==oracle(f,(0,0),(0,0),t,e)
   out.append(dict(name=f'subset_{mask}_last_{e}',result=r))
 r=solve(f,(0,0),(0,0),f,max_states=1);assert r['status']=='unresolved' and r['reason']=='state_limit' and r['length'] is None;out.append(dict(name='state_cap',result=r))
 class Clock:
  def __init__(self):self.x=0
  def __call__(self):self.x+=1;return self.x
 r=solve(f,(0,0),(0,0),f,clock=Clock(),seconds=.5);assert r['status']=='unresolved' and r['reason']=='time_limit' and r['length'] is None;out.append(dict(name='time_cap',result=r))
 save(H/'tests/results.json',dict(passed=True,count=len(out),tests=out));print('exact gates passed',len(out),flush=True)
if __name__=='__main__':main()
