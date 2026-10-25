"""Read-only verification. No planner imports or calls; no artifact writes."""
import hashlib,json,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in read(H/'manifest.json').items():assert sha(R/p)==h,p
a=read(H/'analysis.json');S=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
for p,h in a['source_hashes'].items():assert sha(R/p)==h,p
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=R/'评价指标完整补算与数据审计_v0.1_20261020'
metrics=mod('verify_metrics',M/'metrics.py').metrics
cross=mod('verify_cross',M/'crosscheck.py').calculate
sums={k:{f:0 for f in v} for k,v in a['totals'].items()};n=0
for c in read(S/'analysis.json')['calls']:
 if c['budget']!=20:continue
 x=read(S/c['output']);p=Path(x['job']['input']);assert sha(p)==x['job']['input_sha256']
 m=metrics(read(p),x['raw']['route']);assert m==cross(read(p),x['raw']['route'])==c['metrics']
 assert c['timely_valid'] and m['complete_legal'];n+=1
 for f in sums[c['method']]:sums[c['method']][f]+=m[f]
assert n==486 and len(a['states'])==54 and len(a['queries'])==162 and a['new_solver_calls']==0
for k,fs in sums.items():
 for f,v in fs.items():assert abs(v/3-a['totals'][k][f])<1e-8
for q in a['queries']:
 d=q['delta'];assert d['length']==q['LAST']-q['P2']==d['completion_step']+d['return_tail_steps']
 assert d['length']==sum(d[f] for f in ('fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps'))
assert sum(q['core_best'] for q in a['queries'])==13236
assert sum(q['core_best']-q['P2'] for q in a['queries'])==56
print('PASS: hashes; 486 original routes dual metrics; 54 states / 162 pairs; partitions; core logs. New solver calls: 0.')
