"""Exactly 16 predetermined synthetic cases, no real planning/post entries."""
from region_common import *
import ast,traceback
from unittest.mock import patch
from region_rule import Priority
def run():
 assert not (H/'prechecks.json').exists() and not (H/'entry_log.jsonl').exists()
 spec=read(H/'pure_cases.json');assert len(spec)==16
 b=None;records=[]
 free={(x,y) for x in range(0,111) for y in range(0,6)}
 def make(labels=None,F=None,B=(0,0),tick=lambda:None):return Priority(labels or {'S':[(2,0)],'R':[(6,0),(7,0)]},F or free,B,tick)
 def checked(labels=None,X=(4,0),q0=(2,0),F=None,B=(0,0)):
  r=make(labels,F,B);Q=set().union(*r.labels.values());r.inspect(Q,X,q0,0);return r,Q
 for item in spec:
  row=dict(item,passed=False);start=time.perf_counter()
  try:
   n=item['id']
   if n==1:
    guard();p=read(H/'plan.json');assert len(p['jobs'])==44 and len(p['slots'])==12
    for f in H.rglob('*.py'):ast.parse(f.read_text(encoding='utf-8-sig'))
    for f in ('register.py','precheck.py','worker.py','qualify.py','run.py','archive.py','verify.py'):assert "__name__=='__main__'" in (H/f).read_text(encoding='utf-8')
   elif n==2:
    calls=[]
    def profile(frame,event,arg):
     if event=='call' and frame.f_code.co_name in ('solve','core_route','process','run_payload'):calls.append(frame.f_code.co_filename)
    sys.setprofile(profile)
    try:b=bindings()
    finally:sys.setprofile(None)
    assert not calls and b['B'].identity()['primary']['file']!=b['B'].identity()['independent']['file'];row['task_calls_on_import']=calls
    runtime=read(H/'runtime_guards.json');active=read(H/'active_freeze.json')
    for path,value in loaded_sources().items():
     pp=Path(path)
     if pp.is_relative_to(ROOT/'运行环境'):continue
     assert runtime.get(path)==value or (pp.is_relative_to(H) and active.get(str(pp.relative_to(H)))==value),('preflight unbound source',path)
    from region_audit import audit
    assert 'region_rule' not in audit.__globals__ and 'Priority' not in audit.__globals__
   elif n==3:
    r=make({'S':[(2,0)],'R':[(2,0),(6,0)]});r.inspect({(2,0),(6,0)},(4,0),(2,0),0);assert r.check['reason']=='missing_or_overlapping_label'
    r=make();r.inspect({(2,0),(6,0),(90,0)},(4,0),(2,0),0);assert r.check['reason']=='missing_or_overlapping_label'
   elif n==4:
    r,Q=checked({'S':[(2,0)],'R':[(3,0),(4,0)]});assert r.check['reason']=='touching_original_labels'
    r=make({'S':[(2,0)],'R':[(6,0),(7,0),(8,0)]});Q={(2,0),(6,0),(8,0)};r.inspect(Q,(4,0),(2,0),0);assert r.check['counts']=={'S':1,'R':2} and len(r.labels)==2
   elif n==5:
    labels={'S':[(x,0) for x in range(2,10)],'R':[(x,0) for x in range(20,28)]};r,Q=checked(labels);assert r.check['reason']=='minimum_tie'
    r,Q=checked({'S':[(2,0),(3,0)]});assert r.check['reason']=='single_region'
   elif n==6:
    r,Q=checked({'S':[(x,0) for x in range(3,52)],'R':[(x,2) for x in range(60,110)]},X=(55,3),q0=(51,0),B=(0,3));assert r.check['counts']=={'S':49,'R':50} and r.check['S']=='S' and r.check['reason']=='geometry_conditions_failed'
   elif n==7:
    r,Q=checked({'S':[(1,2),(2,1)],'R':[(6,3),(7,3),(8,3)]},X=(4,3),q0=(2,1));assert r.check['representatives']['S']==(1,2)
    r,Q=checked(X=(0,0));assert r.check['conditions'][0]['on_return'] and not r.check['conditions'][0]['detour_strict']
   elif n==8:
    r,Q=checked(q0=(6,0));first=norm(r.check);r.inspect(Q,(4,0),(2,0),1);assert r.check['reason']=='default_already_other' and norm(r.check)==first
   elif n==9:
    r,Q=checked();assert r.phase=='OTHER' and r.check['activated'] and r.counts['rule_distance_rows']<=3
    r,Q=checked({'S':[(2,0)],'R':[(6,0),(7,0)],'T':[(0,4),(0,5),(1,5)]});assert r.check['reason']=='geometry_conditions_failed' and len(r.check['conditions'])==2
   elif n==10:
    r,Q=checked();opts=[{'cell':(2,0),'score':123.}];assert r.filter(opts,Q)==[] and r.allowed(Q)=={(6,0),(7,0)}
    opts=[{'cell':(2,0),'score':9.},{'cell':(6,0),'score':3.}];assert r.filter(opts,Q)==[opts[1]] and r.filter(opts,Q)[0] is opts[1]
    text=(H/'region_native.py').read_text();assert 'reward_options(cur,prev,Q,s.free' in text and text.index('reward_options(cur,prev,Q,s.free')<text.index('allowed=rule.filter(opts,Q)')
   elif n==11:
    r,Q=checked();before=(set(r.free),{k:set(v) for k,v in r.labels.items()});Q.discard((2,0));r.moved(Q,1);assert r.phase=='CANCELLED' and r.allowed(Q)==Q and (r.free,r.labels)==before
    assert 'post' not in (H/'region_rule.py').read_text().split('class Priority:')[1]
   elif n==12:
    r,Q=checked();Q-={(6,0),(7,0)};r.moved(Q,2);assert r.phase=='TAIL' and r.release_pending==[(2,0)] and r.allowed(Q)==Q
    r,Q=checked();Q.clear();r.moved(Q,3);assert r.phase=='DONE' and not r.allowed(Q)
    text=(H/'region_native.py').read_text();block=text[text.index('def move('):text.index(' try:')];assert 'g.path' not in block and 'choose' not in block
   elif n==13:
    import region_native
    marker={'sentinel':'unchanged original'}
    with patch.object(region_native.original,'solve',return_value=marker) as solve,patch.object(region_native,'Priority',side_effect=AssertionError('OFF entered rule')):
     result=region_native.solve(None,None,20,20261023,None,None,labels={},enabled=False);assert result is marker and solve.call_count==1
   elif n==14:
    class Expired(Exception):pass
    def expire():raise Expired()
    r=make(tick=expire)
    try:r.inspect({(2,0),(6,0),(7,0)},(4,0),(2,0),0)
    except Expired:pass
    else:raise AssertionError('deadline swallowed')
    text=(H/'region_native.py').read_text();assert "deadline=begin+budget" in text and 'single_cell_audit(s,tuple(route))' in text and 'read(' not in text and "else ()" in text
   elif n==15:
    p=H/('preparation/exclusive_fixture_retest.claim' if (H/'engineering_repair.json').exists() else 'preparation/exclusive_fixture.claim')
    with p.open('x',encoding='utf-8') as f:f.write('first owner')
    try:
     with p.open('x'):pass
    except FileExistsError:pass
    else:raise AssertionError('exclusive failed')
    r=make();assert norm([(1,2),None,{'BFS':0,'unobserved':None}])==[[1,2],None,{'BFS':0,'unobserved':None}];assert all(x==0 for x in r.counts.values())
    t=(H/'worker.py').read_text();assert t.index('begin=time.perf_counter()')<t.index("entry(job,'core')")<t.index('native_end=time.perf_counter()')<t.index("entry(job,'post')")<t.index('mainend=time.perf_counter()')
   elif n==16:
    from region_audit import audit
    r,Q=checked(F={(x,y) for x in range(9) for y in range(2)});qq=set(Q);r.moved(qq-{(6,0)},2);qq-={(6,0),(7,0)};r.moved(qq,3)
    path=[(4,0),(5,0),(6,0),(7,0),(6,0),(5,0),(4,0),(3,0),(2,0),(1,0),(0,0)]
    opt={'cell':(7,0),'distance_reward':0.,'straight_reward':1.,'boundary_reward':1.,'score':2.5}
    tr=[dict(index=0,current=(4,0),previous=(4,1),pending_count=3,phase='OTHER',Q=sorted(Q),allowed=[(6,0),(7,0)],original_options=[],kind='recovery',goal=(6,0)),dict(index=2,current=(6,0),previous=(5,0),pending_count=2,phase='OTHER',Q=[(2,0),(7,0)],allowed=[(7,0)],original_options=[opt],options=[opt],kind='local',goal=(7,0)),dict(index=3,current=(7,0),previous=(6,0),pending_count=1,phase='TAIL',Q=[(2,0)],allowed=[(2,0)],original_options=[],kind='recovery',goal=(2,0)),dict(kind='return',index=8,current=(2,0),goal=(0,0),pending_count=0)]
    raw=dict(status='core_complete',route=path,trace=tr,rule=r.export());c=dict(free=sorted(r.free),targets=sorted(Q),covered=[],current=(4,0),base=(0,0),previous=(4,1),predator=(-10,0),distance_budget=1000000,labels={k:sorted(v) for k,v in r.labels.items()})
    result=audit(norm(c),norm(raw),True);assert result['passed']
    bad=norm(raw);bad['trace'][0]['allowed'].append([2,0])
    try:audit(norm(c),bad,True)
    except AssertionError:pass
    else:raise AssertionError('tamper undetected')
    row['synthetic_audit']=result
   row['passed']=True
  except BaseException as e:row.update(failure=repr(e),traceback=traceback.format_exc())
  row['seconds']=time.perf_counter()-start;records.append(row)
  dump(H/'prechecks.json',dict(cases=records,passed=all(z['passed'] for z in records) and len(records)==16,real_core=0,real_post=0,synthetic_only=True,repair_rounds=int((H/'engineering_repair.json').exists())))
  print('PURE',item['id'],row['passed'],row.get('failure',''),flush=True)
  if not row['passed']:break
 return all(z['passed'] for z in records) and len(records)==16
if __name__=='__main__':raise SystemExit(0 if run() else 1)
