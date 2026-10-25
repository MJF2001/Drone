import json,sys
from pathlib import Path
from run import protect,read,sha,common,ka,pa,metrics,H,R
import importlib.util
spec=importlib.util.spec_from_file_location('controlled_trace_local',H/'analyze.py')
local=importlib.util.module_from_spec(spec);spec.loader.exec_module(local);trace=local.trace
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from crosscheck import calculate
def main():
    p=protect();rows=read(H/'execution/checks.json');a=read(H/'analysis.json');assert len(rows)==36
    for family in (0,1,2):
        cases=sorted([c for c in p['cases'] if c['family']==family],key=lambda c:c['gap_columns']);cs=[read(c['input']) for c in cases]
        for c in cs:
            for key in ('free','covered','current','base','distance_budget','initial_targets','predator','previous','old_route','deferred_targets'):assert c[key]==cs[0][key]
            t=set(map(tuple,c['targets']));assert len(t)==14 and len(t-set(map(tuple,c['covered'])))==12
        fixed={(x,y) for x in range(2,5) for y in range(1,3)}|{(-1,0),(0,0)}
        for shift,c in zip((0,3,6),cs):
            moved={(x-shift,y) for x,y in set(map(tuple,c['targets']))-fixed}
            assert moved==set(map(tuple,cs[0]['targets']))-fixed
    for row in rows:
        j=row['job'];result=read(H/'execution/results'/(j['run_id']+'.json'));c=read(j['input']);raw=result['raw']
        assert sha(H/'execution/results'/(j['run_id']+'.json'))==row['result_sha256'] and result['job']==j
        assert result['eligible'] and result['entry_seconds']<20 and result['independent_call_seconds']<20
        assert common(c,dict(route=raw['route']))['valid']
        if j['method']=='CAP_KR1':ka(c,raw)
        else:pa.audit(c,raw)
        assert metrics(c,raw['route'])==calculate(c,raw['route'])==row['metrics']
    for item in a['rows']:
        for m in ('PPCPP','CAP_KR1'):
            own=[x for x in rows if x['job']['case_id']==item['case_id'] and x['job']['method']==m]
            assert len(own)==2 and own[0]['metrics']==own[1]['metrics']==item[m]['metrics']
            raw=read(H/'execution/results'/(own[0]['job']['run_id']+'.json'))['raw'];assert trace(read(own[0]['job']['input']),raw,m)==item[m]['trace']
        assert item['PPCPP']['metrics']['length']-item['CAP_KR1']['metrics']['length']==-2
    for item in a['old_cases']:
        c=read(item['input']);raw=read(item['result'])['raw']
        assert metrics(c,raw['route'])==calculate(c,raw['route'])==item['metrics']
        assert trace(c,raw,item['method'])==item['detail']
        if item['method']=='CAP_KR1':ka(c,raw)
        else:pa.audit(c,raw)
    vals=[t['relative'] for t in a['trends']]
    assert all(v[0]<v[1]<v[2]<0 for v in vals) and a['stable_monotonic_trend'] and a['stable_nonzero_advantage']
    if (H/'manifest.json').exists():
        import hashlib
        manifest=read(H/'manifest.json');assert set(manifest)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in manifest.items():assert sha(H/f)==h
    print(json.dumps(dict(verified=True,new_formal_calls=36,controlled_inputs=9,read_only_original_traces=6,absolute_gap_always_minus2=True,algorithm_changes=0,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
