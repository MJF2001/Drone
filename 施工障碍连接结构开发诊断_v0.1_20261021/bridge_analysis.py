"""Read-only route/structure accounting. Never calls a planner."""
import json,sys,csv,statistics,hashlib,importlib.util
from pathlib import Path
from collections import defaultdict
from bridge_graph import cut_table
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    with Path(p).open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
MD=R/'评价指标完整补算与数据审计_v0.1_20261020'
metric=load('bridge_analysis_metric',MD/'metrics.py').metrics
cross=load('bridge_analysis_cross',MD/'crosscheck.py').calculate
scalar=load('bridge_analysis_scalar',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py')
def double(c,r):
    a=metric(c,r);b=cross(c,r);assert a==b and a['complete_legal'];return a
def percentile(xs,p):
    xs=sorted(xs);v=(len(xs)-1)*p;i=int(v)
    return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(v-i) if xs else None
def summarize(rr):
    valid=[r for r in rr if r['metrics'] is not None];tim=[r['seconds'] for r in rr]
    keys=list(valid[0]['metrics']) if valid else []
    return dict(n=len(rr),valid=len(valid),timely=sum(r['timely'] for r in rr),valid_timely=sum(r['timely'] for r in valid),seconds=dict(mean=statistics.mean(tim),median=statistics.median(tim),p95=percentile(tim,.95),max=max(tim)),metric_mean={k:statistics.mean(r['metrics'][k] for r in valid if r['metrics'][k] is not None) if any(r['metrics'][k] is not None for r in valid) else None for k in keys},excess_group_mean=statistics.mean(r['excess_group_sum_min'] for r in valid) if valid else None,statuses={s:sum(r['status']==s for r in rr) for s in sorted({r['status'] for r in rr})})
def compute(write_cuts=False):
    rows=[];pairs=defaultdict(dict);failed=[]
    for j in read(H/'formal_order.json'):
        p=H/'outputs'/f'{j["id"]}.json'
        if not p.exists():raise RuntimeError(('missing_output',j['id']))
        o=read(p);assert o['job']==j
        c=read(H/j['input']);assert o['input_sha256']==sha(H/j['input'])
        x=o['result'];raw=x['raw'];route=raw.get('route');st=read(H/'structure'/f'{c["name"]}.json')
        row=dict(id=j['id'],case=c['name'],base_id=st['base_id'],family=st['family'],size=st['size'],progress=st['progress'],level=st['level'],layout=st['layout'],seed=j['seed'],rep=j['rep'],method=j['method'],seconds=x['entry_seconds'],timely=x['entry_seconds']<20,status=raw.get('status'),source=raw.get('source'),metrics=None,excess_group_sum_min=None,excess_group_sum_max=None,positive_excess_groups=None)
        if route:
            m=double(c,route)
            if j['method']=='PPCPP':scalar.audit(c,raw['branches']['P0'])
            cuts=cut_table(c,route,False)
            row.update(metrics=m,excess_group_sum_min=sum(g['excess_min'] for g in cuts['groups']),excess_group_sum_max=sum(g['excess_max'] for g in cuts['groups']),positive_excess_groups=sum(g['excess_min']>0 for g in cuts['groups']))
            if write_cuts:save(H/'route_cuts'/f'{j["id"]}.json',cuts)
            else:assert cuts==read(H/'route_cuts'/f'{j["id"]}.json')
        else:failed.append(dict(id=j['id'],status=raw.get('status'),reason=raw.get('reason')))
        rows.append(row);pairs[(c['name'],j['rep'])][j['method']]=row
    states=[]
    for case in sorted({r['case'] for r in rows}):
        sr=[r for r in rows if r['case']==case];head=sr[0];pr=[]
        for rep in range(3):
            g=pairs[(case,rep)]
            if all(g[m]['metrics'] is not None for m in ('PPCPP','P2_MULTI')):
                a,b=g['PPCPP'],g['P2_MULTI'];pr.append(dict(rep=rep,seed=a['seed'],length_gap=a['metrics']['length']-b['metrics']['length'],excess_gap=a['excess_group_sum_min']-b['excess_group_sum_min'],timely_both=a['timely'] and b['timely']))
        states.append(dict(**{k:head[k] for k in ('case','base_id','family','size','progress','level','layout')},methods={m:summarize([r for r in sr if r['method']==m]) for m in ('PPCPP','P2_MULTI')},pairs=pr,length_gap_mean=statistics.mean(r['length_gap'] for r in pr) if len(pr)==3 else None,excess_gap_mean=statistics.mean(r['excess_gap'] for r in pr) if len(pr)==3 else None,length_gap_range=[min(r['length_gap'] for r in pr),max(r['length_gap'] for r in pr)] if pr else None,excess_gap_range=[min(r['excess_gap'] for r in pr),max(r['excess_gap'] for r in pr)] if pr else None))
    matched=[];bykey={(s['base_id'],s['progress'],s['level'],s['layout']):s for s in states}
    for s in states:
        if s['layout']=='dispersed':continue
        d=bykey[(s['base_id'],s['progress'],s['level'],'dispersed')]
        complete=s['length_gap_mean'] is not None and d['length_gap_mean'] is not None
        ld=s['length_gap_mean']-d['length_gap_mean'] if complete else None;ed=s['excess_gap_mean']-d['excess_gap_mean'] if complete else None
        ps=[]
        if complete:
            for sp,dp in zip(s['pairs'],d['pairs']):
                assert sp['rep']==dp['rep'];ps.append(dict(rep=sp['rep'],length_gap_increase=sp['length_gap']-dp['length_gap'],excess_gap_increase=sp['excess_gap']-dp['excess_gap']))
        matched.append(dict(base_id=s['base_id'],family=s['family'],size=s['size'],progress=s['progress'],level=s['level'],layout=s['layout'],case=s['case'],dispersed_case=d['case'],length_gap_increase=ld,excess_gap_increase=ed,signal=complete and ld>0 and ed>0,all_seed_differences=ps))
    signal_bases=sorted({p['base_id'] for p in matched if p['signal']});signal_families=sorted({p['family'] for p in matched if p['signal']})
    strata={}
    for field in ('family','size','progress','level','layout','base_id'):
        strata[field]={str(v):{m:summarize([r for r in rows if r[field]==v and r['method']==m]) for m in ('PPCPP','P2_MULTI')} for v in sorted({r[field] for r in rows})}
    geometric={m:{k:statistics.mean(strata['base_id'][base][m]['metric_mean'][k] for base in strata['base_id'] if strata['base_id'][base][m]['metric_mean'].get(k) is not None) for k in summarize([r for r in rows if r['method']==m])['metric_mean']} for m in ('PPCPP','P2_MULTI')}
    same_excess_different_length=[dict(case=s['case'],rep=p['rep'],length_gap=p['length_gap'],excess_gap=p['excess_gap']) for s in states for p in s['pairs'] if p['excess_gap']==0 and p['length_gap']!=0]
    selections=[]
    for fam in ('I','L','D'):
        cand=[p for p in matched if p['family']==fam and p['length_gap_increase'] is not None]
        mx=sorted(cand,key=lambda p:(-p['length_gap_increase'],p['case']))[0] if cand else None
        mn=sorted(cand,key=lambda p:(p['length_gap_increase'],p['case']))[0] if cand else None
        zero=sorted([s for s in states if s['family']==fam and all(s['methods'][m]['excess_group_mean']==0 for m in ('PPCPP','P2_MULTI'))],key=lambda s:s['case'])
        selections.append(dict(family=fam,maximum=mx,minimum=mn,first_no_excess=zero[0]['case'] if zero else None,rep=0))
    return dict(rows=rows,states=states,matched=matched,summary={m:summarize([r for r in rows if r['method']==m]) for m in ('PPCPP','P2_MULTI')},strata=strata,geometry_equal_weight_metric_mean=geometric,signal=dict(bases=signal_bases,families=signal_families,passed=len(signal_bases)>=3 and len(signal_families)>=2),same_excess_different_length=same_excess_different_length,selections=selections,failures=failed)
def csv_write(path,rows):
    if not rows:return
    with Path(path).open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def analyze():
    (H/'route_cuts').mkdir();a=compute(True);save(H/'analysis.json',a)
    csv_write(H/'全部调用指标.csv',[dict(**{k:v for k,v in r.items() if k!='metrics'},**(r['metrics'] or {})) for r in a['rows']])
    csv_write(H/'匹配布局差异.csv',a['matched'])
    save(H/'failures.json',a['failures']);save(H/'fixed_examples.json',a['selections'])
    print(json.dumps(dict(signal=a['signal'],summary=a['summary'],counterexamples=len(a['same_excess_different_length'])),ensure_ascii=False),flush=True)
if __name__=='__main__':analyze()
