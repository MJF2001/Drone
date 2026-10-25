"""Final immutable-input seal; the append-only live call ledger is excluded."""
import time
from bridge_run import H,read,sha,save
def seal():
    assert read(H/'stage_A.json')['passed']
    prior=read(H/'prep_seal.json')['files']
    for p,h in prior.items():assert sha(p)==h,p
    order=[]
    for i,inp in enumerate(sorted((H/'inputs').glob('*.json'))):
        for rep,seed in enumerate((20261020,20261021,20261022)):
            methods=['PPCPP','P2_MULTI'] if (i+rep)%2==0 else ['P2_MULTI','PPCPP']
            for method in methods:
                j=dict(id=f'{inp.stem}__r{rep}__{method}',phase='formal',method=method,seed=seed,rep=rep,budget=20,input='inputs/'+inp.name,seal='event_seal.json');save(H/'jobs'/f'{j["id"]}.json',j);order.append(j)
    assert len(order)==432;save(H/'formal_order.json',order)
    files=dict(prior)
    for p in H.rglob('*'):
        if p.is_file() and p.name!='actual_order.jsonl':files[str(p.resolve())]=sha(p)
    save(H/'event_seal.json',dict(stage='after_histories_before_gates_and_event_solves',created_utc=time.time(),files=files,excluded_mutable=['actual_order.jsonl'],reason='Append-only actual call ledger is covered by final manifest instead of a preregistered byte hash.'))
    print('EVENT SEALED',len(files),flush=True)
if __name__=='__main__':seal()
