"""Fixed developer comparison, no algorithm changes or retries."""
import json,sys,hashlib,subprocess,time,os,importlib.util
from pathlib import Path
from common_audit import audit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;ROAD=ROOT/'Cstar道路正确性验收_20261019'
METHODS=['P2_MULTI','OARP_CORE2','TREE_MST','PPCPP','CSTAR','TRACE','CAP']
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def extra(c,r,m):
    raw=r['raw']
    if m in ('TRACE','CAP'):
        module('_trace_auditor',ROOT/'TRACE_CAP适配复现_20261020/audit.py').audit(c,raw)
    elif m=='CSTAR':
        sys.path.insert(0,str(ROAD));module('_cstar_auditor',ROAD/'audit_outputs.py').audit(c,raw,r['job']['budget'])
    elif m=='PPCPP' and raw['route']:
        module('_ppcpp_auditor',ROOT/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py').audit(c,raw)
def protect():
    p=read(HERE/'protocol.json')
    for name,h in p['sources'].items():assert sha(ROOT/name)==h,name
    return p
def prepare():
    assert not (HERE/'protocol.json').exists()
    history={c['map_id']:c for c in read(ROOT/'基线复现准备_20261019/独立版_v0.2/comparison/history_contracts.json')}
    actual={c['map_id']:c['history'] for c in read(ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/continuous_history_diagnostics/preparation_verification_v0.1_20261016/checks.json')}
    old=read(ROAD/'protocol.json');jobs=[];cases=[]
    sys.path.insert(0,str(ROAD));from audit_inputs import check_case
    for i,item in enumerate(old['cases']):
        original=ROAD/item['input'];assert sha(original)==item['input_sha256'];c=read(original)
        check_case(c,read(ROAD/'witnesses'/(item['name']+'.json'))['route'])
        e=history[c['map_id']];initial=read(Path(e['initial_input']));assert sha(Path(e['initial_input']))==e['initial_input_sha256']
        clean={k:c[k] for k in ('free','targets','covered','current','base','published_targets','deferred_targets','distance_budget')}
        clean.update(name=f'case{i:02d}',initial_targets=initial['targets'],predator=e['predator'],previous=e['previous'])
        h=actual[c['map_id']];assert h['current']==c['current'] and h['covered']==c['covered']
        clean['old_route']=h['old_route']
        path=HERE/'inputs'/(f'case{i:02d}'+'.json');save(path,clean)
        cases.append(dict(case_id=clean['name'],original_name=item['name'],scale=item['scale'],state=item['state'],event=item['event'],input=str(path),input_sha256=sha(path),source=str(original),source_sha256=sha(original)))
        for si,seed in enumerate((20261018,20261019)):
            rotation=(i+si)%len(METHODS);order=METHODS[rotation:]+METHODS[:rotation]
            if si:order=order[::-1]
            for method in order:jobs.append(dict(run_id=f'c{i:02d}_s{seed}_{method}',case_id=clean['name'],input=str(path),input_sha256=sha(path),method=method,budget=20,seed=seed))
    # Dependency source and binaries are pinned without copying or editing them.
    algo=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
    paths=[ROOT/'portable_frozen.py',ROOT/'基线复现准备_20261019/ppcpp_independent.py',ROOT/'基线复现准备_20261019/独立版_v0.2/ppcpp.py',ROOT/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py',algo/'frozen_baselines/v2_20261012/runtime_profile.json']
    for folder in (algo/'frozen_baselines/v2_20261012/source',algo/'candidate_baselines/PPCPP_CORE4/v0.1_20261014/source',ROOT/'Cstar状态缓存验收_20261019/runtime',ROOT/'TRACE_CAP适配复现_20261020/runtime',ROOT/'CAP单源查询修正_v0.2_20261020/runtime',HERE):paths.extend(folder.rglob('*.py'))
    for folder in ('glns','pyscipopt'):
        paths.extend(p for p in (algo/'.deps'/folder).rglob('*') if p.suffix in ('.py','.pyd','.dll'))
    paths.extend([ROOT/'TRACE_CAP适配复现_20261020/audit.py',ROAD/'audit_outputs.py',ROAD/'audit_inputs.py',ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3/audit_special.py',ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3/audit_micro.py'])
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths if p.is_file() and '__pycache__' not in p.parts}
    save(HERE/'protocol.json',dict(version='developer_comparison_v0.2_20261020',methods=METHODS,cases=cases,jobs=jobs,sources=sources,clock='primary complete entry after imports through return, before serialization and independent outside audit; retains native audits inside entry; native reported seconds also saved',primary_timely='valid complete route and entry_seconds <= budget + 0.010; strict <= budget also reported',budgets=[20],watchdog_seconds=90,seeds=[20261018,20261019],scope='20 published developer states; same genuine historical old tail available to ALL; frozen engineering methods use it, independent methods ignore it through their fixed APIs; OARP is frozen variant2, NOT independent RANK0 FULL',fallback='frozen engineering methods retain original fallback; report source/fallback separately; no new fallback for any method',constraints='common input F/T/C/P/current/base/resource; no future events or witness; actual old suffix and initial targets are pre-event historical inputs; fixed historical heading/predator',stop='two consecutive worker exceptions/watchdogs or any independent audit failure; logical deadline/resource failures retained without retries',gates='7 fixed five-cell calls at budget5 plus independent audit checks, before formal batch',holdout=False,ranking='bounded developer results only, paired timely cases and failed/unpaired counts; no universal winner',preflight_calls=7,formal_calls=280))
def execute(job,folder):
    protect();p=Path(job['input']);assert sha(p)==job['input_sha256']
    jp=folder/'jobs'/(job['run_id']+'.json');rp=folder/'results'/(job['run_id']+'.json');assert not rp.exists();save(jp,job);rp.parent.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
    start=time.perf_counter();watchdog=False
    with (folder/(job['run_id']+'.log')).open('x',encoding='utf-8') as log:
        try:code=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),str(jp),str(rp)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90).returncode
        except subprocess.TimeoutExpired:code=None;watchdog=True
    wall=time.perf_counter()-start;row=dict(run_id=job['run_id'],method=job['method'],case_id=job['case_id'],seed=job['seed'],returncode=code,watchdog=watchdog,process_wall_seconds=wall,valid=False,timely=False,strict_timely=False,steps=None,technical_failure=watchdog or code!=0)
    if not row['technical_failure']:
        r=read(rp);assert r['job']==job;c=read(p);checked=audit(c,r);extra(c,r,job['method']);raw=r['raw'];row.update(checked,status=r['status'],entry_seconds=r['entry_seconds'],reported_seconds=r['reported_seconds'],bootstrap_seconds=r['bootstrap_seconds'],source=raw.get('source'),fallback_selected=raw.get('fallback_selected',False),result_sha256=sha(rp),audit='PASS')
        row.update(timely=checked['valid'] and r['entry_seconds']<=job['budget']+.010,strict_timely=checked['valid'] and r['entry_seconds']<=job['budget'])
        if r['route'] and not checked['valid']:raise AssertionError(('invalid claimed route',row))
    return row
def gates():
    c=dict(name='gate_five_cells',free=[[x,0] for x in range(5)],targets=[[x,0] for x in range(5)],covered=[[0,0]],current=[1,0],base=[0,0],published_targets=[[x,0] for x in range(5)],deferred_targets=[],distance_budget=100,initial_targets=[[x,0] for x in range(5)],predator=[-1,0],previous=[0,0],old_route=[[1,0],[2,0],[3,0],[4,0],[3,0],[2,0],[1,0],[0,0]])
    path=HERE/'preflight/input.json';save(path,c);rows=[]
    # Deliberate illegal route probes exercise the common independent auditor.
    good=dict(route=[[1,0],[2,0],[3,0],[4,0],[3,0],[2,0],[1,0],[0,0]])
    assert audit(c,good)['valid']
    for route in ([],[[1,0],[0,0]],[[1,0],[4,0],[0,0]],[[1,0],[99,0],[0,0]],[[1,0],[2,0],[3,0],[4,0]]):assert not audit(c,dict(route=route))['valid']
    for m in METHODS:
        j=dict(run_id='pre_'+m,case_id='gate',input=str(path),input_sha256=sha(path),method=m,budget=5,seed=20261018)
        row=execute(j,HERE/'preflight');rows.append(row);save(HERE/'preflight/checks.json',rows)
        assert row['valid'] and not row['technical_failure'],row
    save(HERE/'preflight/PASS.json',dict(all_pass=True,calls=7,audit_contract_checks=6))
def run():
    p=protect();assert (HERE/'preflight/PASS.json').exists();assert not (HERE/'execution').exists();folder=HERE/'execution';folder.mkdir();rows=[];consecutive=0
    for i,j in enumerate(p['jobs']):
        try:row=execute(j,folder)
        except Exception as exc:
            save(folder/'ABORTED.json',dict(index=i,error=repr(exc),rule='audit/input/source failure'));raise
        rows.append(row);save(folder/'checks.json',rows);consecutive=consecutive+1 if row['technical_failure'] else 0
        print(i+1,'/',len(p['jobs']),j['run_id'],row.get('status','technical_failure'),'valid',row['valid'],'timely',row['timely'],'steps',row['steps'],flush=True)
        if consecutive>=2:break
    protect();save(folder/'completion.json',dict(scheduled=len(p['jobs']),executed=len(rows),not_run=len(p['jobs'])-len(rows),technical_failures=sum(r['technical_failure'] for r in rows),valid=sum(r['valid'] for r in rows),timely=sum(r['timely'] for r in rows),strict_timely=sum(r['strict_timely'] for r in rows),holdout=False))
if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare()
    elif sys.argv[1]=='gates':gates()
    elif sys.argv[1]=='run':run()
