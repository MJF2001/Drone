"""Six pure acceptance probes, ZERO real engine/PPCPP calls."""
from diag_common import *
hybrid,runtime=production()
def main():
 validations=[];replays=[]
 for record in read(D/'exact_index.json')['records']:
  fam=record['family'];problem=read(D/'exact_inputs'/(fam+'.json'));old=read(problem['original_output']);env=read(old['job']['input']);cfg=old['raw']['window']
  for algorithm,r in record['results'].items():
   if r['status']!='optimal':continue
   patch=r['route'];F=pts(problem['free']);assert patch[0]==problem['entry'] and patch[-1]==problem['exit'] and pts(patch)<=F
   assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(patch,patch[1:]));assert pts(problem['required'])<=pts(problem['local_H'])|pts(patch)
   assert len(patch)-1==r['length'];assert r['length']==len(problem['old_patch'])-1,'Unexpected exact gap: requires separate observer replay within protocol cap; stop for trace setup, never silent success.'
   def fake_base(*a,**k):return {**old['raw']['P0'],'route':tuple(map(tuple,old['raw']['P0']['route']))}
   def acceptance_probe(s,b,v,seed,accept):
    assert s.free==frozenset(F) and s.targets==frozenset(pts(problem['required'])) and s.covered==frozenset(pts(problem['local_H'])) and s.current==tuple(problem['entry']) and s.base==tuple(problem['exit']) and s.old_route==tuple(map(tuple,problem['old_patch'])) and s.distance_budget==problem['distance_budget']
    assert accept(tuple(map(tuple,patch)),algorithm)
    return dict(route=patch,status='pure_acceptance_probe_not_engine_solve',source=algorithm,improvements=[dict(steps=r['length'],source=algorithm)],events=[])
   result=hybrid.run(json.dumps(env),20,20261020,baseline=fake_base,engine=acceptance_probe);assert result['raw']['status']=='core_complete' and result['raw']['selected']=='P0'
   # Full validation from independent original auditor also checks prefix/suffix and metrics.
   auditor=load('lastcheck_full_audit',S/'audit.py');checked=auditor.check(env,norm(result),'LOCAL_P2')
   validations.append(dict(family=fam,algorithm=algorithm,optimal_steps=r['length'],old_steps=len(problem['old_patch'])-1,original_engine_steps=len(old['raw']['local']['route'])-1,production_accepted=True,result=norm(result),audit=checked,real_solver_calls=0))
 save(D/'exact_acceptance.json',dict(probes=validations,real_solver_calls=0,engine_replays=0,reason_no_replay='All3 exact optima equal original windows; replay condition not triggered.'));print('6 production acceptance probes passed; ZERO solves/replays')
if __name__=='__main__':main()
