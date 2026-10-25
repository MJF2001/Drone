"""Bounded independent-process checks; no native algorithm entry anywhere."""
from pathlib import Path
import sys,os,subprocess,json,traceback,shutil
from v02_utils import HERE,read,dump,sha,now

def main(rnd):
    assert 1<=rnd<=3
    reg=read(HERE/'registration.json')
    directory=HERE/'prechecks'/f'round_{rnd}'
    assert not directory.exists(),'no repeated technical round'
    directory.mkdir()
    freeze=read(HERE/f'technical_freeze_{rnd}.json')
    for name,digest in freeze['files'].items():
        assert sha(HERE/name)==digest
    for path in HERE.glob('*.py'):
        shutil.copyfile(path,directory/path.name)
    package=reg['v02'].get('audit_package','h1p2_gate_audit_v02_20261022')
    shutil.copytree(HERE/package,directory/package)
    shutil.copyfile(HERE/'registration.json',directory/'registration.json')
    prior=[]
    for n in range(1,rnd):
        prior+=read(HERE/'prechecks'/f'round_{n}'/'result.json')['rows']
    passed={r['id'] for r in prior if r['passed']}
    todo=[x for x in reg['v02']['planned_checks'] if x['id'] not in passed]
    assert len(prior)+len(todo)<=12,'global precheck process cap'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
    rows=[]
    for check in todo:
        proc=subprocess.run([sys.executable,'-B','-X','utf8',str(HERE/'precheck.py'),str(rnd),check['id']],
                            env=env,capture_output=True,timeout=45)
        (directory/(check['id']+'.log')).write_bytes(proc.stdout+proc.stderr)
        target=directory/(check['id']+'.json')
        data=read(target) if target.exists() else {'passed':False,'saved_audit_calls':0,'failure':'process failed before receipt'}
        rows.append({'id':check['id'],'passed':proc.returncode==0 and data['passed'],
                     'saved_audit_calls':data['saved_audit_calls'],'source':str(target.relative_to(HERE)),
                     'sha256':sha(target) if target.exists() else None,'failure':data.get('failure')})
        print(check['id'],rows[-1]['passed'],rows[-1].get('failure'),flush=True)
    audit_total=sum(r['saved_audit_calls'] for r in prior+rows)
    assert audit_total<=12 and all(r['saved_audit_calls']<=1 for r in prior+rows)
    passed|={r['id'] for r in rows if r['passed']}
    result={'utc':now(),'round':rnd,'processes_this_round':len(rows),'processes_total':len(prior)+len(rows),
        'saved_audits_total':audit_total,'rows':rows,'passed_unique_checks':sorted(passed),
        'all_six_passed':len(passed)==6,'new_core':0,'new_selector':0,'new_postprocess':0,'new_stub':0,'new_graph_search':0}
    dump(directory/'result.json',result)
    if not result['all_six_passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main(int(sys.argv[1]) if len(sys.argv)>1 else 1)
