import json,hashlib,datetime
from pathlib import Path
from spec import cases,SEEDS,METHODS
H=Path(__file__).resolve().parent;R=H.parent;UP=R/'PPCPP两窗口结构候选_v0.1_20261020'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (H/'protocol.json').exists();cs=[dict(**c,input=str(H/'inputs'/(c['case_id']+'.json'))) for c in cases()];jobs=[]
    for i,c in enumerate(cs):
        for z,seed in enumerate(SEEDS):
            order=list(METHODS);offset=(i+z)%3;order=order[offset:]+order[:offset]
            for m in order:jobs.append(dict(run_id=f"{c['case_id']}_{seed}_{m}",batch='newdev36',case_id=c['case_id'],input=c['input'],seed=seed,method=m,budget=20))
    old=read(UP/'protocol.json');files=dict(old['files'])
    for f in UP.rglob('*'):
        if f.is_file():files[str(f)]=sha(f)
    for f in H.iterdir():
        if f.suffix in ('.py','.md'):files[str(f)]=sha(f)
    modules=('rollout.py','first_rollout.py','checks.py','audit_branch.py','validation.py','worker.py')
    for name in modules:assert sha(H/name)==sha(UP/name)
    for f,h in files.items():assert sha(f)==h,f
    p=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),stage='before_preparation_and_generation',files=files,cases=cs,jobs=jobs,prep_calls=6,gate_calls=72,formal_calls=540,budget=20,seeds=SEEDS,methods=METHODS,frozen_modules=modules,holdout=False,statistical_independence=False)
    (H/'protocol.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(registered=True,snapshots=len(cs),base_plans=6,formal_calls=len(jobs),frozen_modules=list(modules),pinned_files=len(files))))
if __name__=='__main__':main()
