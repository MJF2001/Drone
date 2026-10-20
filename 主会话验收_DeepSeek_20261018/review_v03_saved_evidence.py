"""Independent read-only cross-join; writes only this review's result JSON."""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
V03 = HERE.parent / 'DeepSeek_基线复现隔离工作_20261018' / 'revision_v0.3'
manifest = json.loads((V03/'artifacts_v03/runs/run_manifest_v03.json').read_text(encoding='utf-8'))
summary = json.loads((V03/'artifacts_v03/runs/micro_runs_v03.json').read_text(encoding='utf-8'))
with open(V03/'logs_v03/call_ledger_v03.csv', encoding='utf-8-sig', newline='') as f:
    ledger = list(csv.DictReader(f))
formal = [r for r in ledger if r['kind']=='formal' and r['batch']==manifest['batch']]
ends = [r for r in formal if r['phase']=='end']
starts = [r for r in formal if r['phase']=='start']
saved = [json.loads(p.read_text(encoding='utf-8')) for p in (V03/'artifacts_v03/routes').glob('*/*.json')]
failures=[]
def require(value, message):
    if not value: failures.append(message)
require(len(starts)==len(ends)==len(saved)==len(summary['rows'])==102, 'expected 102 of each record')
indexes=[]
for name, rows in [('start',starts),('end',ends),('route',saved),('summary',summary['rows'])]:
    counts=Counter(r.get('run_id') for r in rows)
    require(None not in counts and all(n==1 for n in counts.values()),name+' duplicate/missing ids')
    indexes.append({r.get('run_id'):r for r in rows})
require(all(set(i)==set(indexes[0]) for i in indexes),'run id sets differ')
planned={(r['case_id'],r['method_id']) for r in manifest['planned']}
require(planned=={(r['case_id'],r['method_id']) for r in ends},'planned identity mismatch')
def norm(v):
    return '' if v is None else str(v)
for rid,end in indexes[1].items():
    start=indexes[0].get(rid,{})
    route=indexes[2].get(rid,{})
    row=indexes[3].get(rid,{})
    for field in ('case_id','method_id','seed','plan_id','time_limit_seconds','batch','kind','task_set_sha256'):
        require(norm(start.get(field))==norm(end.get(field)),rid+' start/end '+field)
    for field in ('case_id','method_id','status','route_steps','seed','method_version'):
        summary_value = row.get('request', {}).get('seed') if field == 'seed' else row.get(field)
        require(norm(end.get(field))==norm(route.get(field))==norm(summary_value),rid+' join '+field)
    require(route.get('route')==row.get('route'),rid+' summary route differs')
    require(route.get('audit')==row.get('audit'),rid+' summary audit differs')

result={'planner_calls':0,'formal_calls':len(ends),'cross_join_failures':failures,
        'nonempty_routes':sum(bool(r.get('route')) for r in saved),
        'coverage_complete':sum(r.get('audit',{}).get('coverage_complete',False) for r in saved),
        'valid':sum(r.get('audit',{}).get('valid',False) for r in saved),
        'status_counts':dict(Counter(r['status'] for r in saved))}
(HERE/'review_v03_saved_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
raise SystemExit(bool(failures))
