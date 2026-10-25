"""Read-only diagnostics verification; never solves or changes frozen code."""
import json,hashlib,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent;BATCH=ROOT/'七算法共同预算比较_v0.2_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(BATCH));from common_audit import audit
p=read(HERE/'protocol_v02.json')
assert sha(HERE/'diagnose_v02.py')==p['diagnostic_script_sha256']
for path,h in p['sources'].items():assert sha(ROOT/path)==h,path
rows=read(BATCH/'execution/checks.json');index={x['run_id']:x for x in rows}
for x in read(HERE/'Cstar_saved_diagnostics.json'):
    path=BATCH/'execution/results'/(x['run_id']+'.json');assert sha(path)==index[x['run_id']]['result_sha256'];raw=read(path)['raw']
    assert sum(x['visit_classes'].values())==len(raw['diagnostic_route'])-1==x['diagnostic_steps']
    assert not any(i.get('holes',[]) for i in raw['iterations']) and not any(e['type']=='tsp' for e in raw['events'])
for x in read(HERE/'TRACE_CAP_saved_diagnostics.json'):
    assert sha(BATCH/'execution/results'/(x['run_id']+'.json'))==index[x['run_id']]['result_sha256']
checks=read(HERE/'micro/checks.json');assert len(checks)==6
for job,x in zip(p['jobs'],checks):
    assert sha(Path(job['input']))==job['input_sha256'];path=HERE/'micro/results'/(job['run_id']+'.json');assert sha(path)==x['sha256'];r=read(path)
    assert r['job']==job;check=audit(read(Path(job['input'])),r);assert check['valid'] and check['steps']==x['steps'] and r['entry_seconds']<5
assert [x['steps'] for x in checks if 'CSTAR' in x['run_id']]==[40,88,136]
assert [x['steps'] for x in checks if 'PPCPP' in x['run_id']]==[12,12,12]
probe=read(HERE/'knowledge_predicate_probe.json');assert sha(HERE/'knowledge_probe.py')==probe['script_sha256']
assert len(probe['normal_holes'])==0 and len(probe['domain_closed_probe_holes'])==23 and probe['graph_unchanged']
if (HERE/'manifest.json').exists():
    for name,h in read(HERE/'manifest.json').items():assert sha(HERE/name)==h
print(json.dumps(dict(all_pass=True,new_solver_calls=0,saved_outputs_hash_checked=120,micro_outputs_checked=6,frozen_sources_unchanged=True,predicate_probe='0 to 23 on same graph'),ensure_ascii=False))
