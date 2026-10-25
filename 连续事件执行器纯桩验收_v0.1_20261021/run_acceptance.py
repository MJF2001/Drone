"""Finite handwritten stub acceptance. All attempts append, cap48 globally."""
from pathlib import Path
import json,sys,hashlib,ast,copy,subprocess,os,importlib,traceback
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2,allow_nan=False)
def binding():return {n:sha(H/n) for n in read(H/'fixed_files.json')}
def check_lock():
    z=read(H/'initial_seal.json');assert z['binding']==binding()
    for p,v in read(H/'source_hashes.json').items():assert sha(p)==v,p
    return z
def ordinary_import(out):
    from safety import install,clear
    install();before={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()}
    seen=[]
    def observe(event,args):
        if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):
            p=Path(os.fsdecode(args[0])).resolve()
            if H in p.parents and (p.suffix=='.json' or p.suffix=='.jsonl'):
                seen.append(str(p));raise AssertionError('task read/write during ordinary import')
    sys.addaudithook(observe);sys.argv=['ordinary_import_no_task'];import contracts,executor,auditor,fixture_source,verify,deliver
    clear();after={str(p):[p.stat().st_size,p.stat().st_mtime_ns] for p in H.rglob('*') if p.is_file()};assert before==after and not seen
    # JSON proof is written only after the no-task import observer is disabled
    # by process termination; this check reports via stdout only.
    print(json.dumps(dict(passed=True,no_task_access=True,no_file_mutation=True,no_real_algorithm_imports=True,stub_calls=0)))
def preflight(d):
    from safety import install,clear
    install();parsed=[]
    for p in H.glob('*.py'):ast.parse(p.read_text(encoding='utf8'),filename=str(p));parsed.append(dict(path=p.name,sha256=sha(p)))
    p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'run_acceptance.py'),'--import-only'],capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),timeout=30)
    with (d/'ordinary_import.stdout.log').open('xb') as f:f.write(p.stdout)
    with (d/'ordinary_import.stderr.log').open('xb') as f:f.write(p.stderr)
    assert p.returncode==0,p.stderr.decode('utf8',errors='replace');assert read(H/'fixture_spec.json')['planned_stub_responses']==43
    import contracts,executor
    blocked=False
    try:importlib.import_module('portable_frozen')
    except ImportError as ex:blocked='REAL_ALGORITHM_IMPORT_FORBIDDEN' in str(ex)
    assert blocked;clear()
    spec=read(H/'fixture_spec.json');assert len(spec['ordered_cases'])==23 and sum(len(v) for c in spec['ordered_cases'] for v in c['methods'].values())==43
    for c in spec['ordered_cases']:contracts.validate_world(c['world'])
    good=copy.deepcopy(spec['ordered_cases'][0]['world']);bad=copy.deepcopy(good);bad['events'][0]['tick']=bad['T_max']
    try:contracts.validate_world(bad);raise RuntimeError('event at T_max accepted')
    except AssertionError:pass
    bad=copy.deepcopy(good);bad['events'][1]['id']=bad['events'][0]['id']
    try:contracts.validate_world(bad);raise RuntimeError('duplicate event ID accepted')
    except AssertionError:pass
    bad=copy.deepcopy(good);bad['future_table_leak']=[]
    try:contracts.validate_world(bad);raise RuntimeError('unrecognized world field accepted')
    except AssertionError:pass
    large=dict(text='中文引号",\n'+'长'*160000,zero=0,none=None,nested=[['a',1]])
    serialized=contracts.wire(large);assert json.loads(serialized)==large
    with (d/'long_field.json').open('x',encoding='utf8') as f:f.write(serialized)
    assert read(d/'long_field.json')==large
    save(d/'preflight.json',dict(passed=True,parsed=parsed,real_ordinary_import=True,real_import_blocked_before_load=True,invalid_event_tick_blocked=True,duplicate_event_blocked=True,unknown_world_field_blocked=True,long_JSON_roundtrip=True,stub_calls=0,BFS=0,binding=binding()))
def run_round():
    check_lock();n=len(list((H/'technical_rounds').glob('round_*')))+1;assert n<=3;d=H/'technical_rounds'/f'round_{n:02d}';d.mkdir();(d/'results').mkdir()
    for p in H.glob('*.py'):
        with (d/('source_'+p.name)).open('xb') as f:f.write(p.read_bytes())
    try:
        preflight(d);from executor import run_world
        from contracts import TechnicalError,wire
        from auditor import audit
        spec=read(H/'fixture_spec.json');journal=H/'actual_stub_responses.jsonl';past=[json.loads(x) for x in journal.read_text(encoding='utf8').splitlines()] if journal.exists() else []
        assert not past,'No silent repeat of a stub batch; retain and audit completed evidence instead.'
        proofs=[];counter={'BFS':0};main_bfs=0;sim_sessions=0;expected_technical_seen=False
        for ci,c in enumerate(spec['ordered_cases']):
            check_lock();assert not expected_technical_seen;indices={m:0 for m in c['methods']};callbacks={}
            for name,table in c['methods'].items():
                def callback(payload,name=name,table=table):
                    assert type(payload) is bytes and len(past)<spec['cumulative_stub_cap_all_rounds'];i=indices[name]
                    item=dict(global_sequence=len(past)+1,round=n,subcase=c['id'],method=name,response_sequence=i,payload_sha256=hashlib.sha256(payload).hexdigest(),input_fields_read=sorted(json.loads(payload)),kind='HANDWRITTEN_STUB_CALLBACK')
                    with journal.open('a',encoding='utf8') as f:f.write(json.dumps(item,ensure_ascii=False)+'\n')
                    past.append(item);assert i<len(table),'extra callback not scheduled';indices[name]+=1;response=copy.deepcopy(table[i])
                    if isinstance(response,dict) and response.get('entry_seconds')=='NaN_STUB_FIELD':response['entry_seconds']=float('nan')
                    return response
                callbacks[name]=callback
            print('RUN',ci+1,'/',len(spec['ordered_cases']),c['id'],flush=True)
            try:result=run_world(c['world'],callbacks)
            except TechnicalError as ex:
                assert ex.result is not None
                save(d/'results'/(c['id']+'.json'),ex.result)
                if not c.get('expected_technical_stop') or ci!=len(spec['ordered_cases'])-1:raise
                result=ex.result;expected_technical_seen=True
            else:
                assert not c.get('expected_technical_stop');save(d/'results'/(c['id']+'.json'),result)
            main_bfs+=len(result['environment_BFS']);sim_sessions+=len(result['sessions']);proof=audit(result,c,counter);save(d/'results'/(c['id']+'.audit.json'),proof);proofs.append(proof)
            assert all(indices[m]==len(c['methods'][m]) for m in indices)
            print('PASS',c['id'],'stub_calls_cumulative',len(past),flush=True)
        ra=read(d/'results/12a_merged_future_A.json');rb=read(d/'results/12b_merged_future_B.json')
        assert ra['world_hash']!=rb['world_hash'] and ra['sessions']['A']['requests'][0]['payload_utf8']==rb['sessions']['A']['requests'][0]['payload_utf8']
        for r in (ra,rb):assert len(r['sessions']['A']['requests'])==2 and r['publications'][1]['ids']==['a','b']
        assert len(past)==43 and sim_sessions==25 and len(proofs)==23 and expected_technical_seen
        save(d/'acceptance.json',dict(status='PASS',categories=12,subcases=23,sessions=25,stub_responses=43,all_round_cap=48,main_environment_BFS=main_bfs,independent_audit_BFS=counter['BFS'],future_snapshot_byte_identity=True,same_tick_one_response=True,expected_NaN_technical_stop_is_last=True,real_planner_calls=0,real_cores=0,candidate_trials=0,automatic_routes=0,handwritten_route_responses=43,simulated_sessions=25,technical_round=n,binding=binding(),proofs=proofs))
        save(H/'acceptance_pointer.json',dict(round=n,path=str((d/'acceptance.json').relative_to(H)),sha256=sha(d/'acceptance.json')))
        print('ALL PASS:12 categories23 subcases25 simulated sessions43 handwritten responses; real algorithms0',flush=True);return 0
    except BaseException:
        save(d/'FAILED.json',dict(status='STOPPED',reason=traceback.format_exc(),real_algorithm_calls=0,no_automatic_retry=True))
        print(traceback.format_exc(),flush=True);return 2
if __name__=='__main__':
    if sys.argv[1:]==['--import-only']:ordinary_import(None)
    else:sys.exit(run_round())
