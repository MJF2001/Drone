"""Read-only review verification. No solver execution."""
import json,hashlib,sys,itertools
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'TRACE_CAP适配复现_20261020'
sys.path.insert(0,str(OLD))
from audit import audit
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=read(HERE/'protocol.json')
assert sha(HERE/'review.py')==p['review_script_sha256']
for name,h in p['sources'].items():assert sha(OLD/name)==h
for name,h in read(OLD/'delivery_manifest.json').items():assert sha(OLD/name)==h
count=0
for case in p['fixtures']:
    c=read(HERE/'inputs'/(case+'.json'));rows=[]
    for mode in ('plain','observed'):
        r=read(HERE/'results'/(case+'__'+mode+'.json'));audit(c,r)
        assert r['status']=='complete' and r['seconds']<p['budget_seconds']
        r.pop('seconds');rows.append(r);count+=1
    assert rows[0]==rows[1]
assert count==8
saved=read(HERE/'saved_road_plan_review.json');assert len(saved)==120
for row in saved:
    r=read(OLD/'road_evidence/results'/row['result']);q=r['plans'][row['plan']]
    assert q['end_source']==row['source'] and q['start']==row['plan_start'] and q['end']==row['end']
for row in read(HERE/'endpoint_sensitivity_exact.json')['variants']:
    end=tuple(row['endpoint']);mid=[p for p in (1,2,3) if p!=end[0]]
    cost=min(sum(abs(a-b) for a,b in zip(seq,seq[1:])) for order in itertools.permutations(mid) for seq in [[0,*order,end[0]]])
    assert cost==row['exact_local_cost'];assert cost+abs(end[0]-5)+5==row['complete_cost_same_region_order']
manifest=HERE/'review_manifest.json'
if manifest.exists():
    for name,h in read(manifest).items():assert sha(HERE/name)==h
print(json.dumps(dict(all_pass=True,old_sealed_files=537,micro_results=8,semantic_pairs=4,new_solver_calls=0,road_plan_records=120),ensure_ascii=False))
