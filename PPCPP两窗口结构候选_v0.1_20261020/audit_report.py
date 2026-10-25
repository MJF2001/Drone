"""Check report transcription and post-run timing description; no solver imports."""
import json,pathlib,hashlib,statistics
H=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def row(v):return '|'+ '|'.join(map(str,v))+'|'
def main():
    a=read(H/'analysis.json');doc=(H/'两窗口结构候选开发结果与判断_20261020.md').read_text(encoding='utf-8');rows=read(H/'execution/checks.json');tr=read(H/'time_review.json')
    for batch,s in a['summary'].items():
        for name,v in s['pairs'].items():
            assert row([batch+'/'+name,v['common_states'],f"{v['shorter']}/{v['equal']}/{v['longer']}",f"{v['total_a']}/{v['total_b']}",v['difference'],f"{v['mean_relative']:.4%}"]) in doc
        for m,v in s['methods'].items():assert row([batch+'/'+m]+[f"{v[k]:.6f}" for k in ('time_mean','time_median','time_p95','time_max')]) in doc
        pairs=[]
        cases=[x for x in a['states'] if x['batch']==batch]
        for x in cases:
            for seed in (20261018,20261019):
                pairs.append({m:next(r for r in rows if r['job']['batch']==batch and r['job']['case_id']==x['case_id'] and r['job']['seed']==seed and r['job']['method']==m)['entry_seconds'] for m in ('FIRST','STRUCT')})
        z=tr[batch];assert z['paired_calls']==len(pairs) and z['struct_faster']==sum(x['STRUCT']<x['FIRST'] for x in pairs) and z['struct_slower']==sum(x['STRUCT']>x['FIRST'] for x in pairs)
        assert z['mean_time_relative_change']==statistics.mean(x['STRUCT'] for x in pairs)/statistics.mean(x['FIRST'] for x in pairs)-1
        assert z['complete_branches_per_state_once']=={m:sum(x['methods'][m]['candidates'] for x in cases) for m in ('FIRST','STRUCT')}
    roads=[x for x in a['states'] if x['batch']=='original20']
    for x in roads:
        m=x['methods'];assert row([x['case_id']]+[m[k]['metrics']['length'] for k in ('PPCPP','FIRST','STRUCT')]+[m['STRUCT']['metrics']['length']-m['FIRST']['metrics']['length'],m['STRUCT']['trigger_recovery'],str(len(m['STRUCT']['windows']))+'/'+str(m['STRUCT']['candidates'])]) in doc
    assert [x['case_id'] for x in roads if x['methods']['FIRST']['metrics']['length']!=x['methods']['STRUCT']['metrics']['length']]==['case10']
    assert all(x['methods']['FIRST']['metrics']==x['methods']['STRUCT']['metrics'] for x in a['states'] if x['batch']=='controlled27')
    result=dict(report_verified=True,pair_rows=6,time_rows=6,road_rows=20,timing_review_verified=True,narrative_examples_verified=True,new_solver_calls=0,report_sha256=hashlib.sha256((H/'两窗口结构候选开发结果与判断_20261020.md').read_bytes()).hexdigest())
    (H/'report_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
