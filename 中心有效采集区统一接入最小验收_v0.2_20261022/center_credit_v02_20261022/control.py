"""Freeze gates, then dispatch six sessions once; stop on the first exception."""
from pathlib import Path
import sys,subprocess,json,ast
from .utils import HERE,ROOT,read,dump,sha,now

def frozen_files():
    paths=list(HERE.rglob('*.py'))+[HERE/'registration.json',HERE/'source_bindings.json',HERE/'namespace_expected.json',
          HERE/'external_source_guards.json',HERE/'old_files.json',HERE/'统一信用合同与上限.md',HERE/'适配源码.diff',
          HERE/'保留机制源码段.json',HERE/'source_snapshot/执行稿.md']
    paths+=list((HERE/'source_snapshot').glob('*.md'))
    paths+=list((HERE/'worlds_public').glob('*.json'))+list((HERE/'worlds_private').glob('*.json'))
    return {str(p.relative_to(HERE)):sha(p) for p in sorted(set(paths))}

def construction_check():
    out=[]
    for w in read(HERE/'registration.json')['worlds']:
        F=set(map(tuple,w['public']['F_nominal']))
        P=set(map(tuple,w['public']['P']))
        O=set(map(tuple,w['private']['O_truth']))
        base=tuple(w['public']['base'])
        assert P<=F and len(O)==1 and O<=F and base in F-O
        # Exhaustive finite component expansion, a construction check, no route planning.
        reached={base}
        while True:
            added={v for v in F-O-reached if any(abs(v[0]-u[0])+abs(v[1]-u[1])==1 for u in reached)}
            if not added:
                break
            reached|=added
        assert P-O<=reached and P-O
        out.append({'id':w['id'],'nominal_cells':len(F),'targets':len(P),'truth_obstacles':len(O),
                    'serviceable_targets':len(P-O),'reachable_cells':len(reached),
                    'construction_component_checks':1,'planner_calls':0})
    return out

def freeze_technical():
    assert not (HERE/'technical_freeze.json').exists()
    for p in HERE.rglob('*.py'):
        ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
    dump(HERE/'technical_freeze.json',{'utc':now(),'files':frozen_files(),
         'world_construction':construction_check(),'new_core_calls':0})

def freeze_real():
    assert not (HERE/'real_freeze.json').exists() and not (HERE/'real_started.json').exists()
    passed=[p for p in (HERE/'technical_rounds').glob('round_*/receipt.json') if read(p)['passed']]
    assert len(passed)==1
    receipts=list((HERE/'technical_rounds').glob('round_*/receipt.json'))
    assert len(receipts)<=2 and sum(len(read(p)['sessions']) for p in receipts)<=48
    assert len(read(passed[0])['sessions'])==len(read(HERE/'registration.json')['technical_fixtures'])
    dump(HERE/'real_freeze.json',{'utc':now(),'files':frozen_files(),'technical_pass':str(passed[0].relative_to(HERE)),
         'technical_receipt_sha256':sha(passed[0]),'worlds_unchanged':all(
             sha(HERE/k)==v for k,v in read(HERE/'technical_freeze.json')['files'].items()
             if k.replace('\\','/').startswith(('worlds_public/','worlds_private/')) or k=='registration.json')})
    assert read(HERE/'real_freeze.json')['worlds_unchanged']

def real():
    assert (HERE/'real_freeze.json').exists() and not (HERE/'real_started.json').exists()
    reg=read(HERE/'registration.json')
    dump(HERE/'real_started.json',{'utc':now(),'jobs':reg['jobs'],'once_only':True})
    receipt={'utc':now(),'attempted':[],'not_run':[],'stopped_on_exception':False,'core_calls':0}
    for i,job in enumerate(reg['jobs']):
        try:
            done=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'run_center.py'),'worker',job['id']],cwd=ROOT,
                         capture_output=True,text=True,encoding='utf-8',timeout=105)
            (HERE/'logs'/(job['id']+'_worker_stdout.log')).write_text(done.stdout,encoding='utf-8')
            (HERE/'logs'/(job['id']+'_worker_stderr.log')).write_text(done.stderr,encoding='utf-8')
            item=read(HERE/'sessions'/(job['id']+'.json'))
            receipt['attempted'].append({'id':job['id'],'passed':item['passed'],'exit_code':done.returncode})
            receipt['core_calls']+=item['native_counts'].get('core_started',0)
            print(json.dumps(receipt['attempted'][-1],ensure_ascii=False),flush=True)
            assert receipt['core_calls']<=12
            if done.returncode or not item['passed']:
                raise RuntimeError('real_session_failed_'+job['id'])
        except BaseException as error:
            receipt.update(stopped_on_exception=True,reason=repr(error),not_run=[j['id'] for j in reg['jobs'][i+1:]])
            if not any(j['id']==job['id'] for j in receipt['attempted']):
                receipt['attempted'].append({'id':job['id'],'passed':False,'controller_exception':repr(error)})
            break
        finally:
            dump(HERE/'batch_receipt.json',receipt)
    receipt['finished_utc']=now()
    dump(HERE/'batch_receipt.json',receipt)
    if receipt['stopped_on_exception']:
        raise SystemExit(1)

if __name__=='__main__':
    {'freeze_technical':freeze_technical,'freeze_real':freeze_real,'real':real}[sys.argv[1]]()
