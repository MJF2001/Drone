"""Independent PPCPP-centered recheck from sealed execution rows; no solves."""
import json,csv,hashlib,statistics
from pathlib import Path
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'七算法共同预算比较_v0.2_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
a=read(HERE/'PPCPP中心统计.json');p=read(SOURCE/'protocol.json');rows=read(SOURCE/'execution/checks.json')
for name,h in a['source_sha256'].items():assert sha(SOURCE/name)==h
idx={(r['case_id'],r['seed'],r['method']):r for r in rows};assert len(idx)==280
for item in a['comparisons']:
    values=[];diff=[]
    for case in p['cases']:
        for seed in p['seeds']:
            x=idx[case['case_id'],seed,'PPCPP'];y=idx[case['case_id'],seed,item['other']]
            if x['timely'] and y['timely']:
                values.append((x['steps']-y['steps'])/y['steps']);diff.append(x['steps']-y['steps'])
    assert len(values)==item['n'] and 40-len(values)==item['unpaired']
    assert abs(statistics.mean(values)-item['mean_relative'])<1e-12
    assert sum(d<0 for d in diff)==item['shorter'] and sum(d==0 for d in diff)==item['equal'] and sum(d>0 for d in diff)==item['longer']
with (HERE/'PPCPP及时配对明细.csv').open(encoding='utf-8-sig',newline='') as f:
    detail=list(csv.DictReader(f))
assert len(detail)==sum(x['n'] for x in a['comparisons'])==217
for row in detail:
    x=idx[row['case_id'],int(row['seed']),'PPCPP'];y=idx[row['case_id'],int(row['seed']),row['other']]
    assert x['timely'] and y['timely'];assert x['steps']==int(row['PPCPP_steps']) and y['steps']==int(row['other_steps'])
    assert abs(float(row['relative'])-(x['steps']/y['steps']-1))<1e-12
if (HERE/'manifest.json').exists():
    for name,h in read(HERE/'manifest.json').items():assert sha(HERE/name)==h
print(json.dumps(dict(all_pass=True,focus='PPCPP',comparators=6,timely_pair_records=217,new_solver_calls=0,percentages_recomputed_not_sign_reversed=True),ensure_ascii=False))
