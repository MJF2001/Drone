"""Only continue the original unused slots 2..124; slot1 is immutable reuse."""
from pathlib import Path
import sys,json,hashlib,subprocess,os,traceback,difflib,ast
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'PPCPP真实来向H1最小验收_v0.1_20261022'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def check_bindings():
    bindings=read(HERE/'准备与旧包绑定.json')
    for rel,row in bindings['algorithm_bindings'].items():assert sha(HERE/rel)==sha(Path(row['source']))==row['sha256'],rel
    assert read(OLD/'124槽实际账.json')[0]['status']=='failed'
    manifest=read(OLD/'completion_manifest.json')
    for rel,digest in manifest['files'].items():assert sha(OLD/rel)==digest
    assert sha(OLD/'completion_manifest.json')==bindings['old_manifest_sha256']

def freeze():
    assert not (HERE/'freeze.json').exists()
    check_bindings()
    rounds=[read(p) for p in sorted((HERE/'repair_rounds').glob('round_*_result.json'))]
    assert 1<=len(rounds)<=3 and rounds[-1]['passed']
    for rel,digest in rounds[-1]['source_hashes'].items():assert sha(HERE/rel)==digest
    reuse=read(HERE/'reuse/slot_001_reaudit.json');assert reuse['old_status']=='failed' and len(reuse['audits'])==2 and all(x['audit']['valid'] for x in reuse['audits'])
    assert sha(Path(reuse['source_path']))==reuse['source_sha256']
    old=(OLD/'independent_audit.py').read_text(encoding='utf8');new=(HERE/'independent_audit.py').read_text(encoding='utf8')
    def segments(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
    a,b=segments(old),segments(new)
    unchanged={name:hashlib.sha256(a[name].encode('utf8')).hexdigest() for name in ('direction','scalar_interval','certified_winner','expected_options')}
    assert all(a[name]==b[name] for name in unchanged)
    dump(HERE/'数值与评分审核函数未变.json',unchanged)
    diffs=[];reasons={
      'independent_audit.py':'Validated coordinate value equality; explicit required fields; stable coordinate reports. Scoring/math helper bodies unchanged.',
      'worker.py':'Only reject real execution of slot1; all original entry and counting behavior retained.',
      'run.py':'Continue unused original slots, reference old returned data, retain separate reuse provenance and cross-version cap.',
      'verify.py':'Audit saved new/reused data only and historical progress snapshots, never launch core.'}
    for name in reasons:
        if (HERE/name).exists():
            diffs.extend(difflib.unified_diff((OLD/name).read_text(encoding='utf8').splitlines(keepends=True),(HERE/name).read_text(encoding='utf8').splitlines(keepends=True),fromfile='v0.1/'+name,tofile='v0.2/'+name))
    (HERE/'v0.2表示修复与包装.diff').write_text(''.join(diffs),encoding='utf8');dump(HERE/'修改项与理由.json',reasons)
    files=[]
    for pattern in ('*.py','derived/*.py','inputs/*.json','jobs/*.json','source_snapshot/*.py','reuse/*.json','repair_rounds/*'):
        files.extend(p for p in HERE.glob(pattern) if p.is_file())
    files.extend(HERE/name for name in ('计划_124槽.json','54输入来源清单.json','原来源hash.json','准备与旧包绑定.json',
      '顶层导入静态审查.json','02_v0.2修复合同_事前登记.md','01_合同与数值策略_事前冻结.md','修复预检事前登记.json',
      '技术门槛预登记.json','数值与评分审核函数未变.json','v0.2表示修复与包装.diff','修改项与理由.json'))
    dump(HERE/'freeze.json',dict(frozen_utc=datetime.now(timezone.utc).isoformat(),package_files={p.relative_to(HERE).as_posix():sha(p) for p in files},
      repair_round=rounds[-1]['round'],preflight_audit_calls=rounds[-1]['auditor_calls'],reused_slot1='v0.1 failed; returned data reaudited only',
      new_entry_slots=[2,124],max_new_real_entries=123,max_cross_version_real_entries=124,budget=20,source_policy='no repairs/retries after continuation starts'))
    print('FROZEN v0.2; original slot1 reused, no new real entries yet')

def reference(case):
    first=read(HERE/'计划_124槽.json')['jobs'][0]
    if case==first['case']:
        reuse=read(HERE/'reuse/slot_001_reaudit.json');old=read(Path(reuse['source_path']))
        assert sha(Path(reuse['source_path']))==reuse['source_sha256']
        return dict(entry=old['entry'],audit=reuse['audits'][0]['audit'],origin='v0.1_return_reaudited_v0.2',source_path=reuse['source_path'],source_sha256=reuse['source_sha256'])
    p=HERE/'outputs'/f'legacy__{case}__ORIGINAL.json';x=read(p)
    return dict(entry=x['entry'],audit=x['audit'],origin='v0.2_new_entry',source_path=str(p),source_sha256=sha(p))

def run():
    frozen=read(HERE/'freeze.json')
    for rel,digest in frozen['package_files'].items():assert sha(HERE/rel)==digest,rel
    check_bindings();assert not (HERE/'attempts.jsonl').exists(),'no retry or second continuation run'
    plan=read(HERE/'计划_124槽.json');jobs=plan['jobs'];assert [j['slot'] for j in jobs]==list(range(1,125))
    reuse=read(HERE/'reuse/slot_001_reaudit.json')
    ledger=[dict(slot=j['slot'],id=j['id'],phase=j['phase'],method=j['method'],status='not_run',reason=None,new_execution=j['slot']!=1) for j in jobs]
    ledger[0].update(status='reused_saved_reaudited',old_status='failed',source_path=reuse['source_path'],source_sha256=reuse['source_sha256'])
    comparisons=[];diagonals=[];failure=None
    dump(HERE/'124槽接续实际账.json',ledger);dump(HERE/'54等价证据.json',comparisons);dump(HERE/'16斜向技术证据.json',diagonals)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    from independent_audit import equivalence
    for j,slot in zip(jobs[1:],ledger[1:]):
        if j['phase']=='diagonal':assert len(comparisons)==54 and all(x['equivalent'] for x in comparisons),'phase1 gate not passed'
        slot['status']='attempted'
        with (HERE/'attempts.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(slot=j['slot'],id=j['id'],event='started',utc=datetime.now(timezone.utc).isoformat()))+'\n')
        dump(HERE/'124槽接续实际账.json',ledger)
        try:
            process=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'worker.py'),str(j['slot'])],env=env,capture_output=True,timeout=plan['watchdog_seconds'])
            (HERE/'logs'/(j['id']+'.log')).write_bytes(process.stdout+process.stderr)
            if process.returncode:raise RuntimeError('worker exit '+str(process.returncode))
            p=HERE/'outputs'/(j['id']+'.json');saved=read(p);assert saved['passed'] and saved['audit']['valid']
            slot['status']='passed'
            if j['phase']=='legacy' and j['method']=='H1':
                a=reference(j['case']);ok=equivalence(a['entry']['raw']['branches']['P0'],saved['entry']['raw']['branches']['P0'])
                assert a['audit']['credits']==saved['audit']['credits'] and a['audit']['decisions']==saved['audit']['decisions']
                comparisons.append(dict(case=j['case'],equivalent=ok,original_slot=j['slot']-1,h1_slot=j['slot'],credits_equal=True,decisions_equal=True,
                    original_origin=a['origin'],original_source_path=a['source_path'],original_source_sha256=a['source_sha256'],same_run_timing_pair=a['origin']=='v0.2_new_entry'))
            if j['phase']=='diagonal':
                vector=j['heading']['vector'];base=[1 if z>0 else -1 for z in vector];key='diag__'+'_'.join(map(str,base))+'__0'
                anchor=read(HERE/'outputs'/(key+'.json'));ok=equivalence(anchor['entry']['raw']['branches']['P0'],saved['entry']['raw']['branches']['P0'])
                assert anchor['audit']['credits']==saved['audit']['credits'] and anchor['audit']['decisions']==saved['audit']['decisions']
                diagonals.append(dict(slot=j['slot'],vector=vector,repeat=j['repeat'],consistent=ok,reference_id=key,synthetic_not_actual_history=True))
        except BaseException as ex:
            slot.update(status='failed',reason=repr(ex));failure=dict(slot=j['slot'],id=j['id'],reason=repr(ex),traceback=traceback.format_exc(),native_output_exists=(HERE/'outputs'/(j['id']+'.json')).exists())
        with (HERE/'attempts.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(dict(slot=j['slot'],id=j['id'],event='finished',status=slot['status']))+'\n')
        dump(HERE/'124槽接续实际账.json',ledger);dump(HERE/'54等价证据.json',comparisons);dump(HERE/'16斜向技术证据.json',diagonals)
        attempted=sum(x['status'] not in ('not_run','reused_saved_reaudited') for x in ledger)
        dump(HERE/'status.json',dict(new_attempted=attempted,new_passed=sum(x['status']=='passed' for x in ledger),cross_version_attempts=attempted+1,reused_original_returns=1,
            failure=failure,legacy_pairs=len(comparisons),diagonal_entries=len(diagonals)))
        if failure:print('STOP FAILURE '+json.dumps(failure,ensure_ascii=False),flush=True);break
        if j['slot']%12==0 or j['slot']==124:print(f"PASS new {attempted}/123; original slot {j['slot']}; legacy pairs {len(comparisons)}; diagonal {len(diagonals)}",flush=True)
    if not failure:print('COMPLETE STOP; 123 NEW + 1 HISTORICAL; NO MORE ENTRIES',flush=True)

if __name__=='__main__':
    if sys.argv[1]=='freeze':freeze()
    elif sys.argv[1]=='run':run()
