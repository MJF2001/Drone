"""Freeze after pure gates, then run fixed real slots once with fail-stop."""
from pathlib import Path
import sys,json,hashlib,subprocess,os,traceback
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def freeze():
    assert not (HERE/'freeze.json').exists()
    results=[read(p) for p in sorted((HERE/'tech').glob('attempt_*_result.json'))];assert results and len(results)<=3 and results[-1]['passed']
    for rel,digest in results[-1]['source_hashes'].items():assert sha(HERE/rel)==digest
    files=[]
    for pattern in ('*.py','derived/*.py','inputs/*.json','jobs/*.json','source_snapshot/*.py'):
        files.extend(HERE.glob(pattern))
    files.extend(HERE/name for name in ('技术门槛预登记.json','计划_124槽.json','54输入来源清单.json','原来源hash.json','顶层导入静态审查.json','01_合同与数值策略_事前冻结.md','最小改动.diff'))
    dump(HERE/'freeze.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),gate_attempt=results[-1]['attempt'],gate_cases=len(results[-1]['cases']),
        package_files={p.relative_to(HERE).as_posix():sha(p) for p in files},max_real_entries=124,budget=20,source_policy='no modifications or retries after real run starts'))
    print('FROZEN AFTER PURE GATES; NO REAL ENTRIES YET')

def run():
    frozen=read(HERE/'freeze.json')
    for rel,digest in frozen['package_files'].items():assert sha(HERE/rel)==digest,rel
    assert not (HERE/'attempts.jsonl').exists(),'no rerun'
    plan=read(HERE/'计划_124槽.json');jobs=plan['jobs'];assert len(jobs)==124
    ledger=[dict(slot=j['slot'],id=j['id'],phase=j['phase'],method=j['method'],status='not_run',reason=None) for j in jobs]
    comparison=[];diagonal=[];failure=None
    dump(HERE/'124槽实际账.json',ledger)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    from independent_audit import equivalence
    for j,slot in zip(jobs,ledger):
        if j['phase']=='diagonal' and not (len(comparison)==54 and all(c['equivalent'] for c in comparison)):
            failure=dict(reason='phase1_not_all_passed');break
        slot.update(status='attempted',reason=None)
        with (HERE/'attempts.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(slot=j['slot'],id=j['id'],event='started',utc=datetime.now(timezone.utc).isoformat()))+'\n')
        dump(HERE/'124槽实际账.json',ledger)
        try:
            process=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),str(j['slot'])],env=env,capture_output=True,timeout=plan['watchdog_seconds'])
            (HERE/'logs'/(j['id']+'.log')).write_bytes(process.stdout+process.stderr)
            output=HERE/'outputs'/(j['id']+'.json')
            if process.returncode!=0:raise RuntimeError('worker exit '+str(process.returncode))
            saved=read(output);assert saved['passed'] and saved['audit']['valid']
            slot['status']='passed'
            if j['phase']=='legacy' and j['method']=='H1':
                a=read(HERE/'outputs'/f"legacy__{j['case']}__ORIGINAL.json")
                equivalent=equivalence(a['entry']['raw']['branches']['P0'],saved['entry']['raw']['branches']['P0'])
                assert a['audit']['credits']==saved['audit']['credits'] and a['audit']['decisions']==saved['audit']['decisions']
                comparison.append(dict(case=j['case'],equivalent=equivalent,original_slot=j['slot']-1,h1_slot=j['slot'],credits_equal=True,decisions_equal=True))
            if j['phase']=='diagonal':
                v=j['heading']['vector'];base=[1 if z>0 else -1 for z in v]
                key='diag__'+('_'.join(map(str,base)))+'__0'
                anchor=read(HERE/'outputs'/(key+'.json'))
                equivalent=equivalence(anchor['entry']['raw']['branches']['P0'],saved['entry']['raw']['branches']['P0'])
                assert anchor['audit']['credits']==saved['audit']['credits'] and anchor['audit']['decisions']==saved['audit']['decisions']
                diagonal.append(dict(slot=j['slot'],vector=v,repeat=j['repeat'],consistent=equivalent,reference_id=key,synthetic_not_actual_history=True))
        except BaseException as ex:
            slot.update(status='failed',reason=repr(ex));failure=dict(slot=j['slot'],id=j['id'],reason=repr(ex),traceback=traceback.format_exc())
        with (HERE/'attempts.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(slot=j['slot'],id=j['id'],event='finished',status=slot['status']))+'\n')
        dump(HERE/'124槽实际账.json',ledger);dump(HERE/'54等价证据.json',comparison);dump(HERE/'16斜向技术证据.json',diagonal)
        dump(HERE/'status.json',dict(attempted=sum(x['status']!='not_run' for x in ledger),passed=sum(x['status']=='passed' for x in ledger),failure=failure,legacy_pairs=len(comparison),diagonal_entries=len(diagonal)))
        if failure:print('STOP FAILURE '+json.dumps(failure,ensure_ascii=False),flush=True);break
        if j['slot']%12==0 or j['slot']==124:print(f"PASS {j['slot']}/124; legacy pairs {len(comparison)}; diagonal {len(diagonal)}",flush=True)
    if not failure:print('COMPLETE STOP; DO NOT RUN FURTHER ENTRIES',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='freeze':freeze()
    elif sys.argv[1]=='run':run()
    else:raise SystemExit('freeze or run only')
