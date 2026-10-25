import json,hashlib,sys,subprocess,os,copy,time
from pathlib import Path
from worker import snapshot
from rollout import solve,native
from first_rollout import solve as first
from checks import audit,norm
H=Path(__file__).resolve().parent;R=H.parent
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def protect():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    return p
def gate_records():return [json.loads(line) for line in (H/'gates.jsonl').read_text(encoding='utf-8').splitlines()]
def gates():
    p=protect();records=[];witness={};stream=(H/'gates.jsonl').open('x',encoding='utf-8')
    def call(c,method,hook=None,clock=time.perf_counter,injection=None):
        s=snapshot(c);initial=set(map(tuple,c['initial_targets']));before=copy.deepcopy((s,initial,c));args=(s,initial,5,20261018,tuple(c['predator']),tuple(c['previous']) if c['previous'] else None)
        if method=='PPCPP':r=native.solve(*args)
        elif method=='FIRST':r=first(*args,mode='three')
        else:r=solve(*args,mode='one' if method=='ONE' else 'three',_hook=hook,_clock=clock)
        item=dict(input=c,method=method,result=r,injection=injection);records.append(item);stream.write(json.dumps(item,ensure_ascii=False,separators=(',',':'))+'\n');stream.flush()
        assert (s,initial,c)==before;audit(c,r);return r
    def group(c):
        rs={m:call(c,m) for m in ('PPCPP','FIRST','ONE','STRUCT')};n=rs['PPCPP']
        if n['status']=='core_complete':
            for m in ('FIRST','ONE','STRUCT'):
                r=rs[m];assert r['status']=='core_complete';b=r['branches'][0]
                assert norm(b['route'])==norm(n['route']) and norm(b['trace'])==norm(n['trace'])
                if m=='ONE':assert norm(r['route'])==norm(n['route']) and norm(r['trace'])==norm(n['trace'])
                if m=='STRUCT' and r['override_recovery'] is None:assert norm(r['route'])==norm(n['route']) and norm(r['trace'])==norm(n['trace'])
        else:
            for r in rs.values():assert not r['route'] and r['status']!='core_complete'
        return rs
    for mask in range(64):
        h={(-1,0),(0,0)};cells=[(x,y) for x in range(3) for y in range(2)];t=h|{q for k,q in enumerate(cells) if mask>>k&1}
        c=dict(name='micro_'+str(mask),free=sorted(set(cells)|h),targets=sorted(t),covered=sorted(h),published_targets=sorted(t),deferred_targets=[],current=(0,0),base=(-1,0),distance_budget=100,initial_targets=sorted(h),predator=(-2,0),previous=(-1,0),old_route=[(0,0),(-1,0)])
        group(c)
    for case in p['cases']:
        c=read(case['input']);r=group(c)['STRUCT'];k=r['override_recovery']
        if k is not None and len(r['branches'])>1 and k not in witness:witness[k]=c
    assert set(witness)=={1,2}
    empty=dict(name='empty',free=[(-1,0),(0,0)],targets=[(-1,0),(0,0)],covered=[(-1,0),(0,0)],published_targets=[(-1,0),(0,0)],deferred_targets=[],current=(0,0),base=(-1,0),distance_budget=100,initial_targets=[(-1,0),(0,0)],predator=(-2,0),previous=(-1,0),old_route=[(0,0),(-1,0)])
    unreachable=dict(name='unreachable',free=[(-1,0),(1,0)],targets=[],covered=[],published_targets=[],deferred_targets=[],current=(1,0),base=(-1,0),distance_budget=100,initial_targets=[],predator=(-2,0),previous=(0,0),old_route=[(1,0)])
    limited=copy.deepcopy(witness[1]);limited.update(name='resource_insufficient',distance_budget=0)
    for c in (empty,unreachable,limited):group(c)
    assert len(records)==456
    stage_counts={}
    for k,c in sorted(witness.items()):
        seen=[];call(c,'STRUCT',lambda stage:seen.append(stage));stage_counts[str(k)]=len(set(seen))
        for target in sorted(set(seen)):
            def hook(stage):
                if stage==target:raise native.DeadlineExceeded()
            r=call(c,'STRUCT',hook,injection=dict(kind='raise',witness=k,stage=target));assert r['status']=='deadline' and not r['route']
            if target=='alternative_start':assert r['branches'][0]['status']=='core_complete'
    for k,target in ((1,'baseline_ready'),(1,'result_ready'),(2,'w2_component_visit')):
        expired=[False];origin=time.perf_counter()
        def clock():return origin+6 if expired[0] else time.perf_counter()
        def hook(stage):
            if stage==target:expired[0]=True
        r=call(witness[k],'STRUCT',hook,clock,injection=dict(kind='advance_clock',witness=k,stage=target));assert expired[0] and r['status']=='deadline' and not r['route']
    stream.close();protect();save(H/'gate_PASS.json',dict(calls=len(records),fixed_group_calls=456,fixed_groups=114,micro_calls=256,development_gate_calls=188,boundary_calls=12,discovery_calls=2,deadline_stage_calls=stage_counts,clock_advance_calls=3,all_pass=True))
def run():
    p=protect();assert read(H/'gate_PASS.json')['all_pass'] and not (H/'execution').exists();rows=[]
    for i,j in enumerate(p['jobs']):
        jp=H/'execution/jobs'/(j['run_id']+'.json');dest=H/'execution/results'/(j['run_id']+'.json');save(jp,j);dest.parent.mkdir(parents=True,exist_ok=True)
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
        with (H/'execution'/(j['run_id']+'.log')).open('x',encoding='utf-8') as log:
            code=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jp),str(dest)],cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90).returncode
        assert code==0,j;r=read(dest);c=read(j['input']);audit(c,r['raw'])
        row=dict(job=j,eligible=r['eligible'],status=r['raw']['status'],entry_seconds=r['entry_seconds'],result_sha256=sha(dest),metrics=metrics(c,r['raw']['route']) if r['raw']['route'] else None);rows.append(row);save(H/'execution/checks.json',rows)
        print(i+1,'/',len(p['jobs']),j['run_id'],row['metrics']['length'] if row['metrics'] else row['status'],flush=True)
    protect();save(H/'execution/completion.json',dict(scheduled=len(p['jobs']),executed=len(rows),eligible=sum(x['eligible'] for x in rows)))
if __name__=='__main__':
    if sys.argv[1]=='gates':gates()
    else:run()
