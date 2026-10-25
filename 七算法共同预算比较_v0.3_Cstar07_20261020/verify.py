"""Full read-only replay of stored audits and paired summaries; no solvers."""
import json,hashlib,sys,statistics
from pathlib import Path
from common_audit import audit
from compare import protect,extra
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=protect();rows=read(HERE/'execution/checks.json');assert len(rows)==len(p['jobs'])==280
    pre=read(HERE/'preflight/checks.json');assert len(pre)==7 and all(x['valid'] for x in pre)
    native=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012'
    for path,h in read(native/'manifest.json')['source_sha256'].items():assert sha(native/'source'/path)==h,path
    historypath=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/continuous_history_diagnostics/preparation_verification_v0.1_20261016/checks.json'
    actual={x['map_id']:x['history'] for x in read(historypath)}
    oldcontracts={x['map_id']:x for x in read(ROOT/'基线复现准备_20261019/独立版_v0.2/comparison/history_contracts.json')}
    historyhash=sha(historypath)
    for case in p['cases']:
        assert sha(Path(case['source']))==case['source_sha256']
        original=read(Path(case['source']));c=read(Path(case['input']));mid=original['map_id'];h=actual[mid];old=oldcontracts[mid]
        assert historyhash==old['history_source_sha256']
        assert c['current']==h['current'] and c['covered']==h['covered'] and c['old_route']==h['old_route']
        assert c['previous']==old['previous'] and c['predator']==old['predator']
        prefix=h['executed_route'];assert prefix[-1]==c['current']
        assert c['previous']==(prefix[-2] if len(prefix)>1 else None)
        init=Path(old['initial_input']);assert sha(init)==old['initial_input_sha256'];assert read(init)['targets']==c['initial_targets']
        initial=read(init);assert c['predator']==[min(x for x,y in initial['free'])-1,initial['base'][1]]
        for k in ('free','targets','covered','current','base','published_targets','deferred_targets','distance_budget'):assert c[k]==original[k]
    valid=timely=strict=0
    for job,row in zip(p['jobs'],rows):
        assert job['run_id']==row['run_id'];cpath=Path(job['input']);assert sha(cpath)==job['input_sha256'];c=read(cpath)
        if not row['technical_failure']:
            path=HERE/'execution/results'/(job['run_id']+'.json');assert sha(path)==row['result_sha256'];r=read(path);assert r['job']==job
            checked=audit(c,r);extra(c,r,job['method']);assert checked['valid']==row['valid'] and checked['steps']==row['steps']
            assert row['timely']==(row['valid'] and r['entry_seconds']<=20.010)
            assert row['strict_timely']==(row['valid'] and r['entry_seconds']<=20)
        valid+=row['valid'];timely+=row['timely'];strict+=row['strict_timely']
    analysis=read(HERE/'analysis.json');assert valid==analysis['completion']['valid'] and timely==analysis['completion']['timely'] and strict==analysis['completion']['strict_timely']
    index={(r['case_id'],r['seed'],r['method']):r for r in rows}
    common=[(c['case_id'],s) for c in p['cases'] for s in p['seeds'] if all(index[c['case_id'],s,m]['timely'] for m in p['methods'])]
    assert len(common)==analysis['all_method_common_timely']
    for x in analysis['common_cohort_quality']:
        values=[index[c,s,x['method']]['steps'] for c,s in common];assert sum(values)==x['sum_steps'] and len(values)==x['paired']
        assert abs(statistics.mean(values)-x['mean_steps'])<1e-12
    for pair in analysis['pairwise']:
        differences=[];relative=[]
        for case in p['cases']:
            for seed in p['seeds']:
                a=index[case['case_id'],seed,pair['a']];b=index[case['case_id'],seed,pair['b']]
                if a['timely'] and b['timely']:differences.append(a['steps']-b['steps']);relative.append(a['steps']/b['steps']-1)
        assert len(differences)==pair['paired']
        assert sum(x<0 for x in differences)==pair['a_shorter'] and sum(x==0 for x in differences)==pair['equal'] and sum(x>0 for x in differences)==pair['a_longer']
        if relative:assert abs(statistics.mean(relative)-pair['mean_a_relative_b'])<1e-12
    if (HERE/'delivery_manifest.json').exists():
        for path,h in read(HERE/'delivery_manifest.json').items():assert sha(HERE/path)==h,path
    result=dict(read_only=True,new_solver_calls=0,formal_outputs=280,preflight_outputs=7,history_inputs=20,pairs=21,valid=valid,timely=timely,strict_timely=strict,all_pass=True)
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
