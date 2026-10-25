"""Bounded source/runtime checks. No repairs or ranking batch reruns."""
import json,sys,hashlib,subprocess,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;BATCH=ROOT/'七算法共同预算比较_v0.2_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    if p.exists():
        assert read(p)==json.loads(json.dumps(x));return
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
assert not (HERE/'protocol_v02.json').exists()
jobs=[]
for padding in (2,6,10):
    t=[[x,y] for x in range(6) for y in (0,1)]
    c=dict(name='padding_'+str(padding),free=[[x,y] for x in range(-1,7) for y in range(-padding,padding+2)],targets=t,covered=[[x,0] for x in range(6)],current=[0,0],base=[0,0],published_targets=t,deferred_targets=[],distance_budget=10000,initial_targets=t,predator=[-2,0],previous=[-1,0],old_route=[])
    path=HERE/'micro/inputs'/(c['name']+'.json');save(path,c)
    for method in ('CSTAR','PPCPP'):
        jobs.append(dict(run_id=f'padding{padding}_{method}',case_id=c['name'],input=str(path),input_sha256=sha(path),method=method,budget=5,seed=20261018))
sources={str(p.relative_to(ROOT)):sha(p) for folder in (ROOT/'Cstar状态缓存验收_20261019/runtime',ROOT/'CAP单源查询修正_v0.2_20261020/runtime',ROOT/'TRACE_CAP适配复现_20261020/runtime') for p in folder.rglob('*.py')}
sources.update({str(p.relative_to(ROOT)):sha(p) for p in (BATCH/'worker.py',BATCH/'common_audit.py',BATCH/'protocol.json',BATCH/'execution/checks.json',ROOT/'基线复现准备_20261019/独立版_v0.2/ppcpp.py',ROOT/'基线复现准备_20261019/ppcpp_independent.py')})
save(HERE/'protocol_v02.json',dict(scope='identity verification plus saved branch/route analysis and one-variable flight-domain padding test',planned_new_solver_calls=6,budget_seconds=5,watchdog_seconds=30,no_road_reruns=True,no_repairs=True,stop='first exception/illegal output; no retries',jobs=jobs,sources=sources,diagnostic_script_sha256=sha(Path(__file__))))
sys.path.insert(0,str(BATCH));from common_audit import audit
sys.path.insert(0,str(ROOT/'Cstar状态缓存验收_20261019/runtime'));from history_core.public_map import PublicMap
protocol=read(BATCH/'protocol.json');case_info={x['case_id']:x for x in protocol['cases']}
saved=[]
for row in read(BATCH/'execution/checks.json'):
    if row['method']!='CSTAR':continue
    r=read(BATCH/'execution/results'/(row['run_id']+'.json'))['raw'];c=read(Path(next(j['input'] for j in protocol['jobs'] if j['run_id']==row['run_id'])))
    f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']));pending=t-h-{tuple(c['current'])}
    known=PublicMap();known.update({p:True for p in f});known.update({p:False for p in set(map(tuple,c['published_targets']))-f})
    groups=collections.Counter(x['why']['group'] for x in r['iterations']);modes=collections.Counter();credits=collections.Counter()
    for e in r['task_events']:modes[e['mode']]+=e['end_index']-e['start_index'];credits[e['mode']]+=len(e['credited'])
    # Prefix ledger: repeated and non-task visits are not new acquisition.
    acquired=set(h);counts=collections.Counter()
    for p in map(tuple,r['diagnostic_route'][1:]):
        kind='new_task' if p in t and p not in acquired else 'already_done_target' if p in t else 'non_target'
        counts[kind]+=1
        if p in t:acquired.add(p)
    unknown_flags=sum(known.unknown_adjacent(p) for p in f)
    graph_unknown=sum(known.unknown_adjacent(tuple(n[:2])) for n in r['prune_audits'][0]['before']['nodes']) if r['prune_audits'] else None
    saved.append(dict(run_id=row['run_id'],name=case_info[row['case_id']]['original_name'],status=r['status'],free_count=len(f),targets=len(t),initial_pending=len(pending),remaining=len(r['pending']),diagnostic_steps=len(r['diagnostic_route'])-1,groups=dict(groups),mode_steps=dict(modes),mode_credits=dict(credits),visit_classes=dict(counts),hole_iterations=sum(bool(i.get('holes',[])) for i in r['iterations']),tsp_events=sum(e['type']=='tsp' for e in r['events']),unknown_adjacent_free=unknown_flags,first_graph_unknown_nodes=graph_unknown))
save(HERE/'Cstar_saved_diagnostics.json',saved)
# TRACE/CAP: count stored nonzero revisits to already acquired destinations.
tour_checks=[]
for row in read(BATCH/'execution/checks.json'):
    if row['method'] not in ('TRACE','CAP'):continue
    r=read(BATCH/'execution/results'/(row['run_id']+'.json'))['raw'];job=next(j for j in protocol['jobs'] if j['run_id']==row['run_id']);c=read(Path(job['input']))
    path=list(map(tuple,r['diagnostic_route']));t=set(map(tuple,c['targets']));h=set(map(tuple,c['covered']));repeat=[]
    for e in r['moves']:
        d=tuple(e['destination']);a=e['start_index'];b=e['end_index']
        if e['mode']=='region' and b>a and d in t and d in (h|set(path[:a+1])):repeat.append(dict(destination=d,steps=b-a,start_index=a,end_index=b))
    tour_checks.append(dict(run_id=row['run_id'],method=row['method'],plans=len(r['plans']),unknown_exploring_plans=sum(n['state']=='exploring' for p in r['plans'] for n in p['structure_before']['nodes']),fixed_endpoint_plans=sum(p['end'] is not None for p in r['plans']),revisit_moves=repeat))
save(HERE/'TRACE_CAP_saved_diagnostics.json',tour_checks)
micro=[]
for j in jobs:
    for name,h in sources.items():assert sha(ROOT/name)==h
    jp=HERE/'micro/jobs'/(j['run_id']+'.json');rp=HERE/'micro/results'/(j['run_id']+'.json');save(jp,j);rp.parent.mkdir(parents=True,exist_ok=True)
    proc=subprocess.run([sys.executable,'-B','-X','utf8',str(BATCH/'worker.py'),str(jp),str(rp)],capture_output=True,text=True,timeout=30)
    (HERE/'micro'/(j['run_id']+'.log')).write_text(proc.stdout+proc.stderr,encoding='utf-8');assert proc.returncode==0,proc.stderr
    c=read(Path(j['input']));r=read(rp);check=audit(c,r);assert check['valid'] and r['entry_seconds']<5
    raw=r['raw'];micro.append(dict(run_id=j['run_id'],free_count=len(c['free']),pending=6,steps=check['steps'],entry_seconds=r['entry_seconds'],status=r['status'],tsp_events=sum(e['type']=='tsp' for e in raw.get('events',[])),groups=dict(collections.Counter(i['why']['group'] for i in raw.get('iterations',[]))),sha256=sha(rp)))
save(HERE/'micro/checks.json',micro)
summary=dict(new_solver_calls=6,new_road_calls=0,saved_Cstar_outputs=40,Cstar_hole_iterations=sum(x['hole_iterations'] for x in saved),Cstar_tsp_events=sum(x['tsp_events'] for x in saved),Cstar_outputs_with_unknown_adjacency=sum(x['unknown_adjacent_free']>0 for x in saved),saved_TRACE_CAP_outputs=len(tour_checks),TRACE_CAP_exploring_plan_nodes=sum(x['unknown_exploring_plans'] for x in tour_checks),micro=micro)
save(HERE/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
