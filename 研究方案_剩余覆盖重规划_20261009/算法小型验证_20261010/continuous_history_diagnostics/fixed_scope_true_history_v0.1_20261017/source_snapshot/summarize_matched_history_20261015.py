"""Directional PPCPP comparisons recomputed from verified step counts, no solve."""
from pathlib import Path
import hashlib,json,statistics

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/development_preflights/matched_history_v2_20261015_verification'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)
def main():
    assert read(OUT/'summary.json')['selected_route_audits']==384
    rows=read(OUT/'enriched_ledger.json');lookup={(r['case'],r['budget'],r['method']):r for r in rows}
    figure=read(OUT/'figure_metadata.json')['values'];results=[]
    for subset,variants in {'all':{'H25','H50','H75','V50'},'new_states':{'H25','H75','V50'},
                           **{v:{v} for v in ('H25','H50','H75','V50')}}.items():
        for budget in (1,20):
            for comparator in ('P2_MULTI','OARP_CORE2','TREE_MST'):
                states=[];by_map={};pp_only=other_only=both_fail=0
                for r in rows:
                    if r['budget']!=budget or r['method']!='PPCPP_CORE4' or r['variant'] not in variants:continue
                    other=lookup[r['case'],budget,comparator]
                    if r['valid'] and other['valid']:
                        x=r['metrics']['steps'];y=other['metrics']['steps'];relative=x/y-1 if y else None
                        states.append(dict(case=r['case'],map_id=r['map_id'],variant=r['variant'],
                            ppcpp_steps=x,comparator_steps=y,step_difference=x-y,relative_difference=relative))
                        if relative is not None:by_map.setdefault(r['map_id'],[]).append(relative)
                    elif r['valid']:pp_only+=1
                    elif other['valid']:other_only+=1
                    else:both_fail+=1
                mean=statistics.mean([statistics.mean(v) for v in by_map.values()]) if by_map else None
                for f in figure:
                    if (f['subset'],f['budget'],f['comparator'])==(subset,budget,comparator):
                        assert abs(100*mean-f['percent'])<1e-10
                results.append(dict(subset=subset,budget=budget,comparator=comparator,paired_states=len(states),
                    ppcpp_shorter=sum(s['step_difference']<0 for s in states),equal=sum(s['step_difference']==0 for s in states),
                    ppcpp_longer=sum(s['step_difference']>0 for s in states),
                    ppcpp_only_success=pp_only,comparator_only_success=other_only,both_fail=both_fail,
                    step_difference_sum=sum(s['step_difference'] for s in states),
                    relative_difference_map_equal=mean,per_state=states,
                    per_map_mean_relative={k:statistics.mean(v) for k,v in by_map.items()}))
    budgets=[]
    for method in ('P2_MULTI','OARP_CORE2','TREE_MST','PPCPP_CORE4'):
        for subset,variants in (('all',{'H25','H50','H75','V50'}),('new_states',{'H25','H75','V50'})):
            differences=[];identical=0
            for r in rows:
                if r['budget']!=1 or r['method']!=method or r['variant'] not in variants:continue
                other=lookup[r['case'],20,method]
                if r['valid'] and other['valid']:
                    differences.append(other['metrics']['steps']-r['metrics']['steps'])
                    if method=='PPCPP_CORE4':
                        source=OUT.with_name('matched_history_v2_20261015')/'runs'
                        identical+=read(source/(r['run_id']+'.json'))['raw']['route']==read(source/(other['run_id']+'.json'))['raw']['route']
            budgets.append(dict(method=method,subset=subset,paired_states=len(differences),
                twenty_shorter=sum(d<0 for d in differences),equal=sum(d==0 for d in differences),
                twenty_longer=sum(d>0 for d in differences),step_difference_sum=sum(differences),
                ppcpp_identical_routes=identical if method=='PPCPP_CORE4' else None))
    write(OUT/'ppcpp_directional_summary.json',results);write(OUT/'budget_endpoint_comparison.json',budgets)
    paths=[Path(__file__),ROOT/'render_matched_history_20261015.py',OUT/'ppcpp_directional_summary.json',
        OUT/'budget_endpoint_comparison.json',OUT/'figure_metadata.json',OUT/'ppcpp_relative_quality.png']
    write(OUT/'supplement_sha256.json',{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    print(json.dumps([r for r in results if r['subset']=='new_states'],ensure_ascii=False))
    print(json.dumps(budgets,ensure_ascii=False))

if __name__=='__main__':main()
