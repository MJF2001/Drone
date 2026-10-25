"""Read-only foundation audit, no solver calls or archived data writes."""
import json,hashlib,statistics
from pathlib import Path
from metrics import metrics,percentile
from crosscheck import calculate
from process import summarize,tests
H=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    tests_count=tests();assert tests_count==10288
    rs=read(H/'per_run.json');summary=read(H/'summary.json');pairs=read(H/'paired_states.json');wins=read(H/'paired_wins.json')
    assert len(rs)==360 and len({(x['batch'],x['run_id']) for x in rs})==360
    for x in rs:
        b=next(b for b in p['batches'] if b['id']==x['batch']);root=Path(b['root']);pr=read(root/'protocol.json')
        job=next(j for j in pr['jobs'] if j['run_id']==x['run_id']);c=read(job['input']);raw=read(x['source_path'])
        assert raw['job']==job
        first=metrics(c,raw['raw']['route']);second=calculate(c,raw['raw']['route'])
        assert first==second==x['m'] and x['entry_seconds']==raw['entry_seconds']
        assert first['missing_active']==0 and first['returned'] and first['complete_legal']
        assert first['uncompleted_published']==first['missing_active']+first['deferred']
        timely=raw['eligible'] if x['batch']=='KR1_PAIR' else raw['entry_seconds']<=20
        assert x['timely']==timely
    for batch,methods in summary.items():
        for method,s in methods.items():assert summarize([x for x in rs if x['batch']==batch and x['method']==method])==s
    # Independently reconstruct every aggregate count using the second metric
    # implementation instead of trusting summarize() for numerical totals.
    for batch,methods in summary.items():
        for method,s in methods.items():
            xs=[x for x in rs if x['batch']==batch and x['method']==method]
            for subset,ys in [('all_valid',xs),('timely_only',[x for x in xs if x['timely']])]:
                for key,value in s[subset].items():
                    if key in xs[0]['m'] and isinstance(xs[0]['m'][key],(int,float)) and key not in ('overlap_ratio',):assert sum(y['m'][key] for y in ys)==value
                a=s[subset];assert a['length']==a['fresh_target_steps']+a['historical_target_steps']+a['repeated_new_target_steps']+a['non_target_steps']
                assert a['overlap_pooled']==a['duplicate_target_arrivals']/a['target_arrivals']
            ts=sorted(x['entry_seconds'] for x in xs);pos=.95*(len(ts)-1);i=int(pos)
            assert s['time']['p95']==ts[i]+(ts[min(i+1,len(ts)-1)]-ts[i])*(pos-i)
    assert len(pairs)==20 and len({x['map_id'] for x in pairs})==10
    for pair in pairs:
        for method in ('PPCPP','CAP_KR1'):
            xs=[x for x in rs if x['batch']=='KR1_PAIR' and x['case_id']==pair['case_id'] and x['method']==method]
            assert len(xs)==2 and all(x['timely'] for x in xs) and xs[0]['m']==xs[1]['m']==pair[method]
    for group,measures in wins.items():
        xs=[x for x in pairs if group=='all' or group in (x['state'],x['scale'])]
        for key,value in measures.items():
            ds=[x['PPCPP'][key]-x['CAP_KR1'][key] for x in xs if x['PPCPP'][key] is not None and x['CAP_KR1'][key] is not None]
            assert value==dict(n=len(ds),PPCPP_better=sum(d<0 for d in ds),equal=sum(d==0 for d in ds),PPCPP_worse=sum(d>0 for d in ds))
    upstream=read(H/'upstream_checks.json');assert len(upstream)==2 and all(x['exit_code']==0 for x in upstream)
    for b in p['batches']:
        root=Path(b['root']);m=read(b['original_manifest'])
        # Older delivery manifests may carry structured entries; upstream
        # verifier checks those formats. New pair manifest is flat.
        if b['id']=='KR1_PAIR':
            for f,h in m.items():assert sha(root/f)==h
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,formal_routes=360,independent_metric_agreements=360,exhaustive_and_boundary_cases=tests_count,unique_primary_states=20,base_maps=10,upstream_verifiers=2,new_solver_calls=0,source_files_unchanged=True,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
