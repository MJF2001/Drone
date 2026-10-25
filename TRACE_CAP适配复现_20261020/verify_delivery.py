"""Read-only replay of all saved evidence; no new solver calls."""
import json,hashlib
from pathlib import Path
from collections import Counter
from audit import audit,distance
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def detailed(c,r):
    checked=audit(c,r);cursor=0;f=set(map(tuple,c['free']))
    for plan in r['plans']:
        expected=list(map(tuple,plan['executed_order']))[1:];n=len(expected)
        available=r['moves'][cursor:cursor+n]
        for move,dest in zip(available,expected):
            assert move['mode']=='region';assert tuple(move['destination'])==dest
        cursor+=len(available)
        if plan['completed']:
            assert len(available)==n and not any(m['interrupted'] for m in available)
            cost=sum(m['end_index']-m['start_index'] for m in available)
            if r['method']=='TRACE' and plan['end'] is not None:
                cost+=distance(f,tuple(plan['executed_order'][-1]),tuple(plan['end']))
            assert cost==plan['tsp']['final_cost'],('TSP realized objective',cost,plan['tsp']['final_cost'])
        else:assert cursor==len(r['moves'])
    assert all(m['mode']=='return' for m in r['moves'][cursor:])
    return checked
allchecks=[]
for kind in ('micro','road'):
    folder=HERE/(kind+'_evidence');protocol=read(folder/'protocol.json');old=read(folder/'checks.json')
    assert len(old)==len(protocol['jobs'])
    for path,h in protocol['sources'].items():assert sha(HERE/path)==h
    for job,prior in zip(protocol['jobs'],old):
        assert job['run_id']==prior['run_id'];p=Path(job['input']);assert sha(p)==job['input_sha256']
        rp=folder/'results'/(job['run_id']+'.json');assert sha(rp)==prior['result_sha256']
        r=read(rp);c=read(p);check=detailed(c,r)
        if kind=='micro':
            name=c['name'];expected='resource_exceeded' if name=='resource_too_short' else 'unreachable' if name in ('disconnected_target','disconnected_return') else 'complete'
            assert r['status']==expected,(name,r['status'],expected)
        else:assert r['status']=='complete'
        if r['status']=='complete':assert r['seconds']<job['budget']
        allchecks.append(dict(kind=kind,method=job['method'],run_id=job['run_id'],**check))
    # Deterministic seed repeats must have identical semantic results.
    for a,b in zip(protocol['jobs'][::2],protocol['jobs'][1::2]):
        x=read(folder/'results'/(a['run_id']+'.json'));y=read(folder/'results'/(b['run_id']+'.json'))
        for z in (x,y):z.pop('seconds');z.pop('seed')
        assert x==y
folder=HERE/'deadline_evidence'
for path,h in read(folder/'manifest.json').items():assert sha(HERE/path)==h
c=read(folder/'input.json')
for check in read(folder/'checks.json'):
    r=read(folder/(check['name']+'.json'));detailed(c,r)
    assert r['status']==('complete' if check['relation']=='before' else 'deadline')
sources=read(HERE/'sources'/'manifest.json')
for entry in sources:assert sha(HERE/'sources'/entry['path'])==entry['sha256']
summary=dict(saved_calls=len(allchecks),deadline_calls=len(read(folder/'checks.json')),all_pass=True,by_kind={k:dict(Counter(x['status'] for x in allchecks if x['kind']==k)) for k in ('micro','road')},road_by_method={m:dict(calls=sum(x['kind']=='road' and x['method']==m for x in allchecks),max_core_seconds=max(x['seconds'] for x in allchecks if x['kind']=='road' and x['method']==m),max_steps=max(x['steps'] for x in allchecks if x['kind']=='road' and x['method']==m)) for m in ('TRACE','CAP')})
(HERE/'verification.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
