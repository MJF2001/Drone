"""Preregister fixtures/selection and zero-solve audit before all new solves."""
import ast,datetime
from diag_common import *
def audit_all():
 hybrid,runtime=production();a=load('lastcheck_independent_audit',S/'audit.py');d=read(S/'analysis.json');out=[];sel=[];manifest=read(S/'manifest.json')
 for c in d['calls']:
  if c['method']!='LOCAL_P2':continue
  path=S/c['output'];assert sha(path)==manifest[c['output']];x=read(path);env=read(x['job']['input']);checked=a.check(env,x,'LOCAL_P2');cfg=x['raw']['window']
  for p,h in x['production_hashes'].items():assert sha(p)==h
  if not cfg or cfg['empty']:continue
  assert not pts(cfg['required'])&pts(cfg['local_H']) and tuple(cfg['entry']) not in pts(cfg['required']);er=x['raw']['local'];assert er['source']=='old_suffix'
  # Actual local arguments follow the sealed production dataclasses.replace at hybrid.py.
  record=dict(id=c['id'],kind=c['kind'],family=c['family'],repetition=c['repetition'],output=str(path),output_sha256=sha(path),input=x['job']['input'],input_sha256=sha(x['job']['input']),entry=cfg['entry'],exit=cfg['exit'],required=cfg['required'],local_H=cfg['local_H'],free_count=len(env['state']['free']),task_count=len(cfg['required']),initial_pending_count=len(pts(cfg['required'])-pts(cfg['local_H'])-{tuple(cfg['entry'])}),local_budget=env['state']['distance_budget']-cfg['left']-(len(x['raw']['P0']['route'])-1-cfg['right']),old_patch=cfg['original_patch'],old_steps=len(cfg['original_patch'])-1,returned_steps=len(er['route'])-1,source=er['source'],stage_names=[e['stage'] for e in er['events']],improvements=er['improvements'],snapshot_evidence='cfg/returned patch directly logged; actual replace arguments inferred from unchanged sealed hybrid source, no standalone argument-receipt log existed',unrecorded='Rejected/non-improving candidate lengths/order/reasons not recorded; improvements is accepted-only.')
  assert record['initial_pending_count']==record['task_count'];out.append(record)
  if c['kind']=='event' and c['repetition']==0:
   k=record['task_count'];cost=record['free_count']*(2**k);sel.append(dict(id=c['id'],family=c['family'],tasks=k,free=record['free_count'],states_bound=cost,eligible=k<=12 and cost<=2000000,reason='eligible' if k<=12 and cost<=2000000 else 'task_count>12 or state bound>2000000',output=str(path)))
 assert len(out)==102
 selection={}
 for fam in ('I','L','Z'):
  candidates=sorted([r for r in sel if r['family']==fam and r['eligible']],key=lambda r:(r['tasks'],r['free'],r['id']));selection[fam]=candidates[0] if candidates else None
 return out,sel,selection
def main():
 assert '"verified": true' in (D/'upstream_verify.log').read_text(encoding='utf-8')
 line=[(i,0) for i in range(5)];long=[(0,0),(1,0),(0,0),(1,0),(2,0),(3,0),(4,0)];short=line
 for name,path in [('redundant',long),('optimal',short)]:
  c=dict(name=name,free=line,targets=[(1,0),(3,0)],covered=[],published_targets=[(1,0),(3,0)],deferred_targets=[],initial_targets=[(1,0),(3,0)],current=(0,0),base=(4,0),previous=None,predator=(-1,0),old_route=path,distance_budget=6)
  save(D/'fixtures'/(name+'.json'),dict(state=c,marker=[(2,0)]))
 out,rows,selection=audit_all();save(D/'source_audit.json',out);save(D/'selection.json',dict(candidates=rows,selected=selection))
 for fam,item in selection.items():
  if not item:continue
  x=read(item['output']);env=read(x['job']['input']);cfg=x['raw']['window'];save(D/'exact_inputs'/(fam+'.json'),dict(id=item['id'],free=env['state']['free'],entry=cfg['entry'],exit=cfg['exit'],required=cfg['required'],local_H=cfg['local_H'],old_patch=cfg['original_patch'],distance_budget=env['state']['distance_budget']-cfg['left']-(len(x['raw']['P0']['route'])-1-cfg['right']),original_output=item['output'],budget=60,state_limit=2000000))
 save(D/'protocol.json',dict(created=datetime.datetime.now().astimezone().isoformat(),limits=dict(positive_entries=4,replays=3,bfs=3,dijkstra=3),seed=20261020,positive_expected=dict(redundant=dict(old_steps=6,optimum=4,source_must_change=True),optimal=dict(old_steps=4,optimum=4,source='old_suffix')),positive_boundary='Full hybrid cannot accept injected P0 in normal use; tests use existing _baseline stub solely to present hand window and obtain unmodified production accept/combine closure. No actual PPCPP generation, no claim full production hybrid tested. Direct-local and production-splice tests each call original engine once per fixture.',clock='20sec absolute warm decode/construction/callback extraction/real engine/validation/full raw encoding; tests do not rank speed. 60sec each exact solve + process watchdog60, hard state bound2000000.',selection_rule='Only event rep0 nonempty windows; required<=12 and |F|*2^required<=2000000, each family sort(tasks,F,id) first; no expansion/missing replacement.',selected=selection,stop='Fixture1 cannot shorten => stop; exact gap => at most1 observed-engine replay per selected case; no changes to enumeration/budget/seed/sorting. No new324/holdout/other maps/windows or four-direction resume.'))
 print('A audited102; selection',json.dumps(selection,ensure_ascii=False),'ZERO new planner calls')
if __name__=='__main__':main()
