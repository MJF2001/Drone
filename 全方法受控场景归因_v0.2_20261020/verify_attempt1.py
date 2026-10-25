import sys,json,importlib.util
from pathlib import Path
from run import H,R,protect,read,sha,audit,common,metrics
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from crosscheck import calculate
s=importlib.util.spec_from_file_location('explicit_local_attribution',H/'analyze.py');local=importlib.util.module_from_spec(s);s.loader.exec_module(local)
def main():
    p=protect();rows=read(H/'execution/checks.json');a=read(H/'analysis.json');assert len(rows)==270 and all(x['eligible'] and x['valid'] and not x['technical_failure'] for x in rows)
    first=R/'全方法受控场景归因_v0.1_20261020'
    for f in ('worker.py','run.py','validation.py','analyze.py'):assert sha(H/f)==sha(first/f)
    for case in p['cases']:
        c=read(case['input']);t=set(map(tuple,c['targets']));f=set(map(tuple,c['free']));h=set(map(tuple,c['covered']))
        for folder in ('history_witnesses','witnesses'):
            path=list(map(tuple,read(H/folder/(case['case_id']+'.json'))['route']))
            assert set(path)<=f and all(abs(x[0]-y[0])+abs(x[1]-y[1])==1 for x,y in zip(path,path[1:]))
            if folder=='history_witnesses':assert path[0]==tuple(c['base']) and path[-1]==tuple(c['current']) and set(path)&t==h
            else:assert path[0]==tuple(c['current']) and path[-1]==tuple(c['base']) and t<=h|set(path) and len(path)-1<=c['distance_budget']
    for factor in ('gap','history','barrier'):
        for template in (0,1,2):
            cases=sorted([x for x in p['cases'] if x['factor']==factor and x['template']==template],key=lambda x:x['level']);cs=[read(x['input']) for x in cases];assert len(cs)==3
            allowed={'name','targets','published_targets'} if factor=='gap' else {'name','covered'} if factor=='history' else {'name','free'}
            for c in cs:
                for k in c:
                    if k not in allowed:assert c[k]==cs[0][k],(factor,k)
                assert len(c['targets'])==len(cs[0]['targets']) and len(c['covered'])==len(cs[0]['covered'])
    for row in rows+read(H/'preflight/checks.json'):
        j=row['job'];root=H/('preflight' if j['run_id'].startswith('gate_') else 'execution');rp=root/'results'/(j['run_id']+'.json');r=read(rp);c=read(j['input']);raw=r['raw']
        assert sha(rp)==row['result_sha256'] and r['job']==j and common(c,dict(route=raw['route']))['valid']
        audit(c,raw,j['method'],r['solver_budget']);assert metrics(c,raw['route'])==calculate(c,raw['route'])==row['metrics']
        expected=r['complete'] and r['entry_seconds']<j['budget'] and r['independent_call_seconds']<j['budget']
        assert row['eligible']==r['eligible']==expected
    for row in a['rows']:
        for m,d in row['methods'].items():
            own=[x for x in rows if x['job']['case_id']==row['case_id'] and x['job']['method']==m];assert len(own)==2 and own[0]['metrics']==own[1]['metrics']==d['metrics']
            raw=read(H/'execution/results'/(own[0]['job']['run_id']+'.json'))['raw'];assert local.trace(read(own[0]['job']['input']),raw,m)==d['trace']
    for factor,ms in a['factors'].items():
        for m,d in ms.items():
            assert d['paired_states']==9 and d['ppcpp_shorter']+d['equal']+d['ppcpp_longer']==9
            for pat in d['patterns']:
                own=sorted([x for x in a['rows'] if x['factor']==factor and x['template']==pat['template']],key=lambda x:x['level'])
                values=[x['methods']['PPCPP']['metrics']['length']-x['methods'][m]['metrics']['length'] for x in own];assert pat['deltas']==values
                assert pat['increasing']==(values[0]<=values[1]<=values[2] and values[0]<values[2])
                assert pat['decreasing']==(values[0]>=values[1]>=values[2] and values[0]>values[2])
            if factor!='history':assert d['stable_absolute_monotonic']==(all(x['increasing'] for x in d['patterns']) or all(x['decreasing'] for x in d['patterns']))
    for old in a['old_cases']:
        sel=old['selection'];c=read(sel['input'])
        for m,d in old['methods'].items():
            raw=read(sel['ppcpp_source'] if m=='PPCPP' else sel['opponent_source'])['raw'];assert metrics(c,raw['route'])==calculate(c,raw['route'])==d['metrics']
            assert local.trace(c,raw,m)==d['trace'];audit(c,raw,m,20)
    if (H/'manifest.json').exists():
        manifest=read(H/'manifest.json');assert set(manifest)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in manifest.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,methods=5,controlled_inputs=27,new_formal_calls=270,preflight_calls=10,history_and_future_witnesses=54,old_pair_dossiers=len(a['old_cases']),algorithm_changes=0,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
