"""Predeclared H/V partition witnesses; not an equal-budget planner benchmark."""
from pathlib import Path
import hashlib
import json
import time
from collections import Counter
import oarp_replan
from oarp_replan.ranks import partition
from oarp_replan.tour import tour_replan
from model import Geometry
from scenarios import deserialize
from audit import audit
from run_experiments import write_json
from run_oarp_service_skip import replay
from run_oarp_ablation import exact_independent

ROOT = Path(__file__).resolve().parent
OUT = ROOT/'results/run_19_partition_objective_diagnostic'


def main():
    OUT.mkdir(exist_ok=False)
    inputs = {'snapshots':ROOT/'results/run_16_oarp_default_v3/snapshots.json',
        'core':ROOT/'results/run_16_oarp_default_v3/results.json',
        'split':ROOT/'results/run_17_frozen_partition_ablation/results.json',
        'skip':ROOT/'results/run_18_frozen_service_skip/results.json'}
    data = {}
    for name,p in inputs.items():
        (OUT/('input_'+name+'.json')).write_bytes(p.read_bytes())
        data[name] = json.loads(p.read_text(encoding='utf-8'))
    files = [Path(__file__),ROOT/'model.py',ROOT/'audit.py',ROOT/'scenarios.py',
        ROOT/'run_oarp_service_skip.py',ROOT/'run_oarp_ablation.py',ROOT/'oarp_replan/ranks.py',ROOT/'oarp_replan/tour.py']
    hashes = {}
    for f in files:
        rel = f.relative_to(ROOT)
        dest = OUT/'source_snapshot'/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(f.read_bytes())
        hashes[str(rel)] = hashlib.sha256(f.read_bytes()).hexdigest()
    write_json(OUT/'manifest.json',{'protocol':'original CORE2 partition versus maximal all-H/all-V partitions of identical pending cells',
        'source_sha256':hashes,'input_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in inputs.items()},
        'primary_reference':'CORE2 chosen before execution; CORE1 not searched',
        'GLNS':'author default, seed 1000+case_index, up to 5 seconds per orientation',
        'candidate_order':'alternate H/V by case index','held_out':False,'repetitions':1,
        'time_fairness':'NOT equal-total-budget; two new TOUR solves versus saved original; diagnostic only',
        'scope':'partition witnesses, not proof all minimum-rank partitions inferior; no original change-budget enforcement on H/V'})
    orig = {r['case']:r for r in data['core'] if r['algorithm']=='OARP_CORE_2'}
    split = {r['case']:r for r in data['split'] if r['algorithm']=='OARP_CORE_2'}
    skip = {r['case']:r for r in data['skip'] if r['algorithm']=='OARP_CORE_2'}
    rows = []
    for index,d in enumerate(data['snapshots']):
        s = deserialize(d)
        pending = s.targets-s.covered
        ref = {'rank_count':len(orig[s.name]['detail']['ranks']),
            'full_length':split[s.name]['split']['length'],'full_exact':split[s.name]['split']['exact'],
            'skip_length':skip[s.name]['skip']['length'],'final_length':skip[s.name]['final_after']}
        row = {'case':s.name,'family':d['metadata']['family'],'reference':ref,
            'p2_length':skip[s.name]['p2_length'],'common_fallback_length':skip[s.name]['common_fallback_length'],'candidates':{}}
        for axis in (('H','V') if index%2==0 else ('V','H')):
            ranks = partition(pending,{p:axis for p in pending})
            blocks = [{'kind':'rank','path':r.cells} for r in ranks]
            cells = [p for r in ranks for p in r.cells]
            assert len(cells)==len(set(cells)) and set(cells)==pending
            begin = time.perf_counter()
            try:
                full = tour_replan(Geometry(s,begin+5),blocks,seconds=5,seed=1000+index)
                elapsed = time.perf_counter()-begin
                processed = replay(s,blocks,full['order'],True)
                exact = exact_independent(s,blocks)
                check1,check2 = audit(s,full['route']),audit(s,processed['route'])
                assert check1['valid'] and check2['valid']
                assert processed['length']<=full['length']
                assert exact is None or exact<=full['length']
                row['candidates'][axis] = {'status':'planned','ranks':[{'axis':r.axis,'cells':r.cells} for r in ranks],
                    'rank_count':len(ranks),'order':full['order'],'full_length':full['length'],'full_exact':exact,
                    'full_route':full['route'],'full_audit':check1,'skip_length':processed['length'],
                    'skip_route':processed['route'],'skip_audit':check2,'tour_seconds':elapsed,
                    'overrun_gt_10ms':elapsed>5.01,'solver':full['solver']}
            except (TimeoutError,):
                row['candidates'][axis] = {'status':'timeout','rank_count':len(ranks)}
        feasible = [(k,v) for k,v in row['candidates'].items() if v['status']=='planned']
        key,best = min(feasible,key=lambda kv:(kv[1]['skip_length'],kv[0]))
        row['best_axis'] = key
        row['best_skip_length'] = best['skip_length']
        row['combined_final_length'] = min(ref['skip_length'],best['skip_length'],row['common_fallback_length'])
        rows.append(row)
        write_json(OUT/'results.json',rows)
        print(s.name+': original='+str(ref['skip_length'])+' H/V='+str([(k,v.get('skip_length')) for k,v in feasible]),flush=True)
    witnesses = []
    for r in rows:
        for axis,v in r['candidates'].items():
            ref = r['reference']
            if v['status']=='planned' and v['full_exact'] is not None and ref['full_exact'] is not None and v['full_exact']<ref['full_exact']:
                witnesses.append({'case':r['case'],'axis':axis,'original_ranks':ref['rank_count'],
                    'alternative_ranks':v['rank_count'],'original_fixed_partition_optimum':ref['full_exact'],
                    'alternative_fixed_partition_optimum':v['full_exact']})
    summary = {'cases':len(rows),'candidate_statuses':dict(Counter(v['status'] for r in rows for v in r['candidates'].values())),
        'best_HV_vs_original_skip':dict(Counter('HV_shorter' if r['best_skip_length']<r['reference']['skip_length'] else 'equal' if r['best_skip_length']==r['reference']['skip_length'] else 'original_shorter' for r in rows)),
        'combined_improved_cases':sum(r['combined_final_length']<r['reference']['final_length'] for r in rows),
        'original_final_total':sum(r['reference']['final_length'] for r in rows),
        'combined_final_total':sum(r['combined_final_length'] for r in rows),'p2_total':sum(r['p2_length'] for r in rows),
        'combined_vs_p2':dict(Counter('combined_shorter' if r['combined_final_length']<r['p2_length'] else 'equal' if r['combined_final_length']==r['p2_length'] else 'p2_shorter' for r in rows)),
        'exact_partition_witnesses':witnesses,
        'exact_checks_new':sum(v.get('full_exact') is not None for r in rows for v in r['candidates'].values()),
        'exact_positive_heuristic_gaps':sum(v.get('full_exact') is not None and v['full_length']>v['full_exact'] for r in rows for v in r['candidates'].values()),
        'overruns_gt_10ms':sum(v.get('overrun_gt_10ms',False) for r in rows for v in r['candidates'].values())}
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
