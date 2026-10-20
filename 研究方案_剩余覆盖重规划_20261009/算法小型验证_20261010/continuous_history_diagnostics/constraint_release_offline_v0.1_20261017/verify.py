"""Independent arithmetic/route checks; imports no planner or producer."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=read(D/'evidence.json');p=read(D/'provenance.json')
for k in ('source_hashes','input_hashes'):
 for f,h in p[k].items():assert sha(f)==h,('source mismatch',f)
assert len(a['structures'])==40 and len(a['compatibility'])==640 and len(a['runs'])==160
ss={(s['map_id'],s['scope']):s for s in a['structures']};rr={r['run_id']:r for r in a['runs']};cases={}
for j in read(D.parent/'fixed_scope_true_history_v0.1_20261017/protocol.json')['jobs']:cases[j['map_id']]=read(j['case'])
for s in ss.values():
 c=cases[s['map_id']];old=c['old_route'];start=old[s['left']];end=old[s['right']];md=lambda u,v:sum(abs(x-y) for x,y in zip(u,v));n=max([md(start,end)]+[md(start,q)+md(q,end) for q in s['required']]);assert s['lower_bound']==s['prefix_steps']+s['suffix_steps']+n
for run in rr.values():
 c=cases[run['map_id']];r=run['route'];raw=read(run['path']);assert raw['raw']['route']==r and sha(run['path'])==run['sha256']
 assert r[0]==c['current'] and r[-1]==c['base'];assert set(map(tuple,r))<=set(map(tuple,c['free']));assert set(map(tuple,c['targets']))-set(map(tuple,c['covered']))<=set(map(tuple,r));assert all(sum(abs(x-y) for x,y in zip(u,v))==1 for u,v in zip(r,r[1:]));assert len(r)-1==run['steps']<=c['distance_budget']
for e in a['compatibility']:
 run=rr[e['run_id']];s=ss[run['map_id'],e['target_scope']];c=cases[run['map_id']];old=c['old_route'];r=run['route'];l,h=s['left'],s['right'];end=len(r)-s['suffix_steps'];patch=r[l:end]
 valid=bool(patch) and patch[0]==old[l] and patch[-1]==old[h] and old[:l]+patch+old[h+1:]==r and set(map(tuple,s['required']))<=set(map(tuple,patch));assert valid==e['compatible']
for cert in a['certificates']:
 s=ss[cert['map_id'],cert['scope']];w=rr[cert['best_witness_run_id']];assert cert['constraint_cost_certificate']==(w['steps']<s['lower_bound']);assert w['steps']==min(r['steps'] for r in rr.values() if r['map_id']==cert['map_id'])
assert len({(e['run_id'],e['target_scope']) for e in a['compatibility']})==640
for st in a['structures']:
 run=next(r for r in rr.values() if r['map_id']==st['map_id']);cfg=read(run['path'])['raw']['detail']['range_plan']['plans'][st['scope']];c=cases[st['map_id']]
 assert st['left']==cfg['left'] and st['right']==cfg['right'] and st['required']==cfg['required'] and st['free']==c['free'] and st['distance_budget']==c['distance_budget']
 assert st['start']==c['old_route'][cfg['left']] and st['join']==c['old_route'][cfg['right']]
for rc in a['run_certificates']:
 compatible_ids={e['run_id'] for e in a['compatibility'] if e['map_id']==rc['map_id'] and e['target_scope']==rc['scope'] and e['compatible']}
 better=[rr[k] for k in compatible_ids if rr[k]['steps']<rc['steps']]
 assert rc['search_omission_certificate']==bool(better)
 assert set(rc['same_budget_repeat_shorter_witnesses'])=={r['run_id'] for r in better if r['budget']==rc['budget'] and r['repeat']==rc['repeat']}
for cert in a['certificates']:
 ids={e['run_id'] for e in a['compatibility'] if e['map_id']==cert['map_id'] and e['target_scope']==cert['scope'] and e['compatible']};assert cert['shortest_compatible_steps']==min(rr[k]['steps'] for k in ids)
for batch in ('fixed_scope_true_history_v0.1_20261017','initial_repair_retention_v0.1_20261017'):
 for e in read(D.parent/batch/'delivery_sha256.json')['files']:assert sha(e['absolute_path'])==e['sha256']
for e in read(D/'delivery_sha256.json')['files']:assert sha(e['path'])==e['sha256']
print(json.dumps(dict(status='PASS',structures=40,saved_routes=160,compatibility_comparisons=640,constraint_certificates=5,planner_calls=0,performance_experiments=0,holdout_used=False,read_only=True)))
