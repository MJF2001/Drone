"""No-solve gate: static worlds, new aggregation tests, ordinary imports, guards.
No stub callback is necessary: the executor/callback/worker are byte identical.
"""
from util import *
import sys,ast,subprocess,copy
def ordinary(method,out):
    import worker
    called=[]
    def profile(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('solve','run_payload','run_world','core_route','precheck','reach','walk_component'):
            called.append(frame.f_code.co_filename);raise AssertionError('task/solver/graph during ordinary import')
    sys.setprofile(profile);api=worker.load_api(method);native=api['runtime'].native.solve
    before={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()};reads=[]
    def hook(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            if H in p.parents and any(n in p.parts for n in ('inputs','jobs','outputs','sessions','receipts')):reads.append(str(p));raise AssertionError('task I/O at import')
    sys.addaudithook(hook)
    def refuse(h):raise AssertionError('task audit hook at import')
    sys.addaudithook=refuse;sys.argv=['ordinary_import'];import session,seal,real_audit,comparison,analysis,run,verify,deliver,render
    after={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()};assert before==after and not called and not reads and native is api['runtime'].native.solve
    # Static initial input validation, not solving or constructing geometry.
    worlds=read(H/'worlds.json');checked=[]
    from contracts import SNAPSHOT_KEYS
    for wid,w in worlds.items():
        c=dict(name='stub_snapshot',free=w['free'],targets=w['published'],covered=[],published_targets=w['published'],deferred_targets=[],initial_targets=w['published'],current=w['start'],previous=None,base=w['base'],predator=[-1,0],old_route=[w['start']],distance_budget=w['E0'],radius=0)
        assert set(c)==SNAPSHOT_KEYS;api['runtime'].validate(c);checked.append(wid)
    sys.setprofile(None);save(out,dict(passed=True,paths=worker.imported(api),ordinary_import_task_IO=False,ordinary_import_installed_task_hook=False,real_entries=0,graph_calls=0,initial_static_input_contracts=checked,worker_main_guard=True))
def geometry(out):
    from prepare import generate
    from contracts import validate_world
    from collections import deque
    worlds,meta=generate();assert worlds==read(H/'worlds.json') and meta==read(H/'world_metadata.json');rows=[];bfs=0
    for wid,w in worlds.items():
        validate_world(w);F=set(map(tuple,w['free']));P=set(map(tuple,w['published']));A=set(map(tuple,w['events'][0]['add_targets']));B=set(map(tuple,w['events'][1]['block']));m=meta[wid];L=m['L'];assert L%6==0 and P<=F and A<=F and B<=F and not A&P and tuple(w['base']) not in B and w['E0']==w['T_max']==10*len(F) and [e['tick'] for e in w['events']]==[L//2,2*L]
        stages=[]
        for t in (0,L//2,2*L):
            f=F-B if t==2*L else F;p=P|A if t else P;seen={tuple(w['base'])};q=deque(seen);bfs+=1
            while q:
                x,y=q.popleft()
                for z in ((x+1,y),(x,y+1),(x-1,y),(x,y-1)):
                    if z in f and z not in seen:seen.add(z);q.append(z)
            assert (p&f)<=seen;stages.append(dict(tick=t,reachable_cells=len(seen),active_targets=len(p&f),blocked_target_cells=len(p-f)))
        rows.append(dict(world=wid,passed=True,static_stages=stages,does_not_guarantee_actual_current_avoids_B=True))
    save(out,dict(passed=True,ordinary_static_BFS=bfs,real_entries=0,stub_responses=0,worlds=rows))
def summaries(out):
    from comparison import three_views
    def r(w,m,status,M,H0,D):return dict(world=w,method=m,summary=dict(status=status,M=M,H=H0,D=D))
    worlds=['I_S','I_M','L_S','L_M','T_S','T_M'];records=[]
    # Different credit must be excluded even when both succeed and one is short.
    specs=[('success','success',12,10,[[1,0]],[[1,0]],[],[]),('success','success',8,10,[[1,0]],[[1,0]],[],[]),('success','success',100,200,[[1,0]],[[2,0]],[[2,0]],[[1,0]]),('environment_termination','success',1,100,[],[[1,0]],[[1,0]],[]),('deadline','solver_no_solution',0,0,[],[],[],[]),('success','success',15,10,[[1,0]],[[1,0]],[],[])]
    for w,s in zip(worlds,specs):
        a,b,x,y,h,k,d,e=s;records += [r(w,'PPCPP',a,x,h,d),r(w,'P2_MULTI',b,y,k,e)]
    v=three_views(records,worlds);assert v['full_world_denominator']==6 and v['both_success']['denominator']==4 and v['same_final_H_D']['denominator']==3 and v['shapes_with_PPCPP_longer_in_comparable_pairs']==['I','T'] and v['eligible_to_suggest_cost_location_discussion']
    assert v['full_worlds'][3]['delta_M_PPCPP_minus_P2'] is None and v['statuses_per_method']['PPCPP']['environment_termination']==1
    missing=three_views([],worlds);assert missing['both_success']['denominator']==0 and missing['statuses_per_method']['PPCPP']['not_run']==6 and not missing['eligible_to_suggest_cost_location_discussion']
    # A failed short prefix never enters either successful paired description.
    save(out,dict(passed=True,handwritten_summary_records=12,missing_session_cases=12,new_stub_callbacks=0,new_real_calls=0,new_graph_searches=0,checks=['full6 denominator','both successful4','equal H and D3','different task exclusion','failure short prefix excluded','two distinct shapes threshold','not-run denominator','no invented failure cost'],handwritten_result=v))
def guards(out):
    import util
    d=out.parent/'guard_fixture';d.mkdir();(d/'receipts').mkdir();save(d/'binding_files.json',['key.txt']);put(d/'key.txt',b'bound');put(d/'critical.txt',b'critical');original=util.H;util.H=d
    try:
        try:util.require('technical');raise RuntimeError('missing PASS accepted')
        except FileNotFoundError:pass
        util.receipt('technical',[d/'key.txt']);util.require('technical');save(d/'seal.json',dict(complete=True,binding=util.binding(),critical={str(d/'critical.txt'):sha(d/'critical.txt')}));util.receipt('seal',[d/'seal.json']);util.check_seal()
        with (d/'critical.txt').open('ab') as f:f.write(b'changed')
        try:util.check_seal();raise RuntimeError('critical drift accepted')
        except AssertionError:pass
        with (d/'key.txt').open('ab') as f:f.write(b'changed')
        try:util.require('technical');raise RuntimeError('stale PASS accepted')
        except AssertionError:pass
    finally:util.H=original
    save(out,dict(passed=True,missing_PASS_blocked=True,stale_PASS_blocked=True,critical_drift_blocked=True,new_real_calls=0,new_stub_responses=0,new_graph_searches=0,other_worker_guards_reused_from_byte_identical_approved_worker=True))
def main():
    assert not (H/'actual_attempts.jsonl').exists();n=len(list((H/'technical_rounds').glob('round_*')))+1;assert n<=2;d=H/'technical_rounds'/f'round_{n:02d}';d.mkdir();rows=[]
    for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p));put(d/('source_'+p.name),p.read_bytes())
    for c in read(H/'copy_manifest.json'):
        assert sha(c['source'])==c['source_sha256'] and sha(H/c['name'])==c['target_sha256']
    cases=[('geometry',['geometry']),('summaries',['summaries']),('guards',['guards']),('ordinary_PPCPP',['ordinary','PPCPP']),('ordinary_P2',['ordinary','P2_MULTI'])]
    for name,args in cases:
        p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'technical.py'),*args,str(d/(name+'.json'))],capture_output=True,env=env(),timeout=90);put(d/(name+'.stdout.log'),p.stdout);put(d/(name+'.stderr.log'),p.stderr);rows.append(dict(case=name,passed=p.returncode==0));print('TECH',n,name,'PASS' if p.returncode==0 else 'FAIL',flush=True)
        if p.returncode:print(p.stderr.decode('utf8',errors='replace')[-4000:],flush=True)
    parsed=set()
    for p in d.glob('ordinary_*.json'):
        for name in read(p)['paths']:
            q=Path(name)
            if q.suffix=='.py':ast.parse(q.read_text(encoding='utf-8-sig'),filename=str(q));parsed.add(str(q))
    save(d/'result.json',dict(passed=all(r['passed'] for r in rows),round=n,cases=rows,parsed_actual_dependency_sources=len(parsed),stub_responses=0,real_entries=0,static_BFS=read(d/'geometry.json')['ordinary_static_BFS'] if (d/'geometry.json').exists() else 0,prior_evidence_reused=True))
    if not all(r['passed'] for r in rows):return 2
    receipt('technical',[p for p in d.rglob('*') if p.is_file()]);print('PASS new gates:0 stub callbacks,0 real solves',flush=True);return 0
if __name__=='__main__':
    a=sys.argv[1:]
    if not a:sys.exit(main())
    elif a[0]=='ordinary':ordinary(a[1],Path(a[2]))
    elif a[0]=='geometry':geometry(Path(a[1]))
    elif a[0]=='summaries':summaries(Path(a[1]))
    elif a[0]=='guards':guards(Path(a[1]))
