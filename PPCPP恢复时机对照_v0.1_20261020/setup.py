"""Seal input/code/protocol BEFORE gates and formal calls."""
import json,hashlib,datetime
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;UP=R/'PPCPP首次恢复完整试走_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (H/'protocol.json').exists()
    old=read(UP/'protocol.json');cases=old['cases'];jobs=[]
    for i,c in enumerate(cases):
        for z,seed in enumerate((20261018,20261019)):
            order=['PPCPP','FIRST','SECOND'];offset=(i+z)%3;order=order[offset:]+order[:offset]
            for m in order:jobs.append(dict(run_id=f"{c['batch']}_{c['case_id']}_{seed}_{m}",batch=c['batch'],case_id=c['case_id'],input=c['input'],seed=seed,method=m,budget=20))
    files={str(f):sha(f) for f in UP.rglob('*') if f.is_file()}
    files.update(old['files'])
    for c in cases:files[c['input']]=sha(c['input'])
    for f in H.iterdir():
        if f.suffix in ('.py','.md'):files[str(f)]=sha(f)
    for f,h in files.items():assert sha(f)==h,f
    assert sha(H/'first_rollout.py')==sha(UP/'rollout.py')
    p=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage='pre_registered_before_calls',cases=cases,jobs=jobs,files=files,methods=['PPCPP','FIRST','SECOND'],formal_calls=282,holdout=False,only_variable='branch once at first vs second recovery',budget=20)
    (H/'protocol.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(registered=True,inputs=len(cases),formal_calls=len(jobs),pinned_files=len(files))))
if __name__=='__main__':main()
