"""Supplementary transcription and negative-result check; no planner imports."""
import json,pathlib,hashlib
H=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def row(xs):return '|'+ '|'.join(map(str,xs))+'|'
def main():
    a=read(H/'analysis.json');s=a['summary']['newdev36'];st=read(H/'strata.json');ia=read(H/'input_audit.json');doc=(H/'新开发验证结果与候选保留判断_20261020.md').read_text(encoding='utf-8')
    for name,v in s['pairs'].items():assert row([name,v['common_states'],f"{v['shorter']}/{v['equal']}/{v['longer']}",f"{v['total_a']}/{v['total_b']}",v['difference'],f"{v['mean_relative']:.4%}"]) in doc
    for m,v in s['methods'].items():assert row([m]+[f"{v[k]:.6f}" for k in ('time_mean','time_median','time_p95','time_max')]) in doc
    for x in a['states']:
        ms=x['methods'];assert ms['PPCPP']['metrics']==ms['FIRST']['metrics']==ms['STRUCT']['metrics']
        assert row([x['case_id']]+[ms[m]['metrics']['length'] for m in ('PPCPP','FIRST','STRUCT')]+[0,ms['STRUCT']['trigger_recovery']]) in doc
        if ms['STRUCT']['triggered']:
            assert row([x['case_id'],'／'.join(map(str,ms['STRUCT']['candidate_steps'])),'替代更长' if len(ms['STRUCT']['candidate_steps'])==2 else '有等长替代，无更短']) in doc
    assert sum(x['deferred'] for x in ia['rows'])==82 and sum(x['blocked_previously_completed'] for x in ia['rows'])==86
    assert sum(x['methods'][m]['candidates'] for x in a['states'] for m in ('FIRST','STRUCT'))*5==600
    result=dict(report_verified=True,pair_rows=3,time_rows=3,state_rows=36,actual_trial_rows=7,all_metrics_equal_verified=True,narrative_totals_verified=True,new_solver_calls=0,report_sha256=hashlib.sha256((H/'新开发验证结果与候选保留判断_20261020.md').read_bytes()).hexdigest())
    (H/'report_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
