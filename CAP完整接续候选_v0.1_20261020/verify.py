"""Read-only independent trajectory and pre-registered policy verification."""
import json,hashlib
from pathlib import Path
from audit import audit
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(Path(f))==h,f
    for name in ('structures.py','primitives.py','known_sync.py'):
        assert sha(H/'runtime'/name)==sha(H.parent/'CAP已知分区同步候选_v0.1_20261020/runtime'/name)
    ip=read(H/'integration_protocol.json')
    for f,h in ip['files'].items():assert sha(Path(f))==h,f
    micro=read(H/'micro.json');roads=read(H/'roads.json');extra=read(H/'integration.json')
    names={x['name'] for x in micro};assert len(names)==len(micro)
    assert all('grid_subset_'+str(i) in names for i in range(64))
    specials={'external_resume','resource_prefix','deferred','history','unreachable','deadline_discovery'}
    assert specials<=names
    for x in micro:
        assert audit(x['input'],x['result'])==x['check']
        expected='deadline' if x['name'].startswith('deadline_') and x['name']!='deadline_discovery' else 'resource_exceeded' if x['name']=='resource_prefix' else 'unreachable' if x['name']=='unreachable' else 'complete'
        assert x['result']['status']==expected
    assert len(roads)==20 and {x['case_id'] for x in roads}=={j['case_id'] for j in p['roads']}
    inputs={j['case_id']:read(Path(j['input'])) for j in p['roads']}
    for x in roads:
        assert x['input']==inputs[x['case_id']]
        assert audit(x['input'],x['result'])==x['check'] and x['result']['status']=='complete'
    assert len(extra)==2
    for x,definition in zip(extra,ip['cases']):
        assert x['name']==definition['name'] and x['input']==definition['input']
        assert audit(x['input'],x['result'])==x['check'] and x['result']['status']=='complete'
    split=extra[0]['result'];batch=[e for e in split['structure_events'] if e['type']=='known_residual_split_batch']
    assert len(batch)==1 and sorted(map(len,batch[0]['replacements'][0]['parts']))==[1,1]
    assert len(split['plans'])>=2 and not extra[1]['result']['plans'] and extra[1]['result']['distance']==2
    for x in micro+roads+extra:
        r=x['result'];bound={e['state']['generation']:e['state'] for e in r['events'] if e['type']=='bind'}
        for plan in r['plans']:assert plan['target_state']==bound[plan['target_state']['generation']]
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,micro_calls=len(micro),deadline_cases=len(micro)-70,road_complete=len(roads),additional_integration_calls=len(extra),full_candidate_calls=len(micro)+len(roads)+len(extra),performance_ranking_calls=0,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
