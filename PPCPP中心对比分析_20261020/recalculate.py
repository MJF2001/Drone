"""Reframe saved benchmark around PPCPP; no new solver calls."""
import json,csv,statistics,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;SOURCE=HERE.parent/'七算法共同预算比较_v0.2_20261020'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=read(SOURCE/'protocol.json');rows=read(SOURCE/'execution/checks.json');assert len(rows)==280
cases={c['case_id']:c for c in p['cases']};index={(r['case_id'],r['seed'],r['method']):r for r in rows}
methods=[m for m in p['methods'] if m!='PPCPP'];details=[];all_valid=[];summaries=[]
def summarize(xs):
    return dict(n=len(xs),shorter=sum(x['difference']<0 for x in xs),equal=sum(x['difference']==0 for x in xs),longer=sum(x['difference']>0 for x in xs),mean_relative=statistics.mean(x['relative'] for x in xs) if xs else None,median_relative=statistics.median(x['relative'] for x in xs) if xs else None,sum_PPCPP_steps=sum(x['PPCPP_steps'] for x in xs),sum_other_steps=sum(x['other_steps'] for x in xs))
for method in methods:
    paired=[];valid=[];missing=[]
    for case in p['cases']:
        for seed in p['seeds']:
            a=index[case['case_id'],seed,'PPCPP'];b=index[case['case_id'],seed,method]
            if a['valid'] and b['valid']:
                item=dict(case_id=case['case_id'],name=case['original_name'],scale=case['scale'],state=case['state'],event=case['event'],seed=seed,other=method,PPCPP_steps=a['steps'],other_steps=b['steps'],difference=a['steps']-b['steps'],relative=a['steps']/b['steps']-1,PPCPP_timely=a['timely'],other_timely=b['timely'])
                valid.append(item);all_valid.append(item)
                if a['timely'] and b['timely']:paired.append(item);details.append(item)
            if not (a['timely'] and b['timely']):missing.append(dict(case_id=case['case_id'],name=case['original_name'],seed=seed,PPCPP_timely=a['timely'],other_timely=b['timely'],other_status=b.get('status')))
    summaries.append(dict(other=method,**summarize(paired),unpaired=len(missing),missing=missing,by_scale={s:summarize([x for x in paired if x['scale']==s]) for s in ('small','medium','large')},by_state={s:summarize([x for x in paired if x['state']==s]) for s in ('control','event')},valid_ignoring_deadline_diagnostic_only=summarize(valid),best_relative_example=min(paired,key=lambda x:x['relative']) if paired else None,worst_relative_example=max(paired,key=lambda x:x['relative']) if paired else None))
time_summary=[]
for method in ['PPCPP']+methods:
    rr=[r for r in rows if r['method']==method]
    time_summary.append(dict(method=method,calls=len(rr),valid=sum(r['valid'] for r in rr),timely=sum(r['timely'] for r in rr),late=sum(r['valid'] and not r['timely'] for r in rr),incomplete=sum(not r['valid'] for r in rr),mean_entry=statistics.mean(r['entry_seconds'] for r in rr),median_entry=statistics.median(r['entry_seconds'] for r in rr),max_entry=max(r['entry_seconds'] for r in rr),mean_reported=statistics.mean(r['reported_seconds'] for r in rr)))
provenance={str(path.relative_to(SOURCE)):sha(path) for path in (SOURCE/'protocol.json',SOURCE/'analysis.json',SOURCE/'execution/checks.json',SOURCE/'delivery_manifest.json')}
out=dict(focus='PPCPP',formula='mean over paired observations of (L_PPCPP/L_other - 1); negative means PPCPP shorter; NOT negation or reciprocal of previous mean',new_solver_calls=0,source=str(SOURCE),source_sha256=provenance,comparisons=summaries,timing=time_summary)
(HERE/'PPCPP中心统计.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for name,data in [('PPCPP及时配对明细.csv',details),('PPCPP合法输出附录_忽略截止仅诊断.csv',all_valid)]:
    with (HERE/name).open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
print(json.dumps(dict(comparisons=[{k:x[k] for k in ('other','n','unpaired','shorter','equal','longer','mean_relative')} for x in summaries],timing=time_summary),ensure_ascii=False,indent=2))
