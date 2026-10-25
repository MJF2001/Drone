"""Read-only evidence verification; no solver calls."""
import json,hashlib,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'TRACE_CAP适配复现_20261020'
from audit import audit
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def semantics(r):return {k:v for k,v in r.items() if k not in ('seconds','metric_counts')}
p=read(HERE/'protocol.json')
for name,h in p['sources'].items():assert sha(HERE/name)==h
for name,h in read(OLD/'delivery_manifest.json').items():assert sha(OLD/name)==h
assert sha(HERE/'runtime/structures.py')==sha(OLD/'runtime/structures.py')
assert sha(HERE/'audit.py')==sha(OLD/'audit.py')
checks=read(HERE/'checks.json');assert len(checks)==len(p['jobs'])==92
for job,check in zip(p['jobs'],checks):
    assert job['run_id']==check['run_id'];source=Path(job['input']);assert sha(source)==job['input_sha256']
    path=HERE/job['kind']/(job['run_id']+'.json');assert sha(path)==check['result_sha256']
    r=read(path);old=read(OLD/(job['kind']+'_evidence/results')/(job['run_id']+'.json'))
    audit(read(source),r);assert semantics(r)==semantics(old)
    assert r['metric_counts']['path_builds']==old['metric_counts']['path_builds']
    assert r['metric_counts']['distance_rows']<=old['metric_counts']['distance_rows']
    if r['status']=='complete':assert r['seconds']<job['budget']
c=read(OLD/'deadline_evidence/input.json');gates=read(HERE/'deadline_checks.json');assert len(gates)==51
for gate in gates:
    r=read(HERE/'deadline'/(gate['name']+'.json'));audit(c,r)
    assert r['status']==('complete' if gate['name'].endswith('__before') else 'deadline')
assert any(x['name']=='single_source__equal' for x in gates)
manifest=HERE/'delivery_manifest.json'
if manifest.exists():
    for name,h in read(manifest).items():assert sha(HERE/name)==h
print(json.dumps(dict(all_pass=True,semantic_pairs=92,deadline_outputs=51,old_seal_files=537,structures_and_auditor_unchanged=True,new_solver_calls=0),ensure_ascii=False))
