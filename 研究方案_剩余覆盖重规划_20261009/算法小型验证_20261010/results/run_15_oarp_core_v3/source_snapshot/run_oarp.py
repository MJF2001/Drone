"""Two OARP core adaptations on frozen v3 snapshots; all limitations in manifest."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time
import oarp_replan
import pyscipopt
import glns
from oarp_replan.adapter import solve_core
from scenarios import deserialize
from audit import audit
from run_experiments import write_json


def run(out):
    root = Path(__file__).resolve().parent
    input_path = root/'results/run_14_single_cell_v3/snapshots.json'
    baseline_path = root/'results/run_14_single_cell_v3/results.json'
    profile_path = root/'oarp_replan/runtime_profile.json'
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    raw = json.loads(input_path.read_text(encoding='utf-8'))
    baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
    out.mkdir(parents=True,exist_ok=False)
    archive = out/'source_snapshot'
    archive.mkdir()
    sources = list((root/'oarp_replan').glob('*.py'))+[
        root/n for n in ('model.py','audit.py','scenarios.py','run_oarp.py','test_oarp_core.py')]
    sources.append(profile_path)
    hashes = {}
    for p in sources:
        rel = p.relative_to(root)
        dest = archive/rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(p.read_bytes())
        hashes[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'snapshots.json').write_bytes(input_path.read_bytes())
    (out/'baseline_results.json').write_bytes(baseline_path.read_bytes())
    write_json(out/'manifest.json',{'kind':'OARP-Replan unit-step core adaptation',
        'original_end_to_end_reproduction':False,'original_robot_dynamics':False,
        'original_encounter_loop':False,'scene_expansion':'new adaptation',
        'python':sys.version,'pyscipopt':pyscipopt.__version__,'glns':glns.__version__,
        'glns_source_commit':'7804f7c65c66ddd13a12107163884ca334f8f93f',
        'solver_port':'author-maintained C++, Julia reference not used',
        'input_sha256':hashlib.sha256(input_path.read_bytes()).hexdigest(),
        'baseline_sha256':hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        'source_sha256':hashes,'time_limit_seconds':5,'repetitions':1,'held_out':False,
        'baseline_execution':'reused saved P1/P2 routes; no timing ranking across runs',
        'LP_integer_policy':'detect all variables, MIP fallback if fractional; recorded',
        'fallback':'old-order A* detour then new-target H snake; explicit GD adapter'})
    records = []
    for index,d in enumerate(raw):
        s = deserialize(d)
        old = frozenset(map(tuple,d['metadata']['initial_targets']))
        for variant in ((1,2) if index%2 == 0 else (2,1)):
            result = solve_core(s,old,variant,5,profile,seed=1000+index)
            result.update({'case':s.name,'algorithm':f'OARP_CORE_{variant}',
                'family':d['metadata']['family'],
                'audit':audit(s,result['route']) if result['route'] else None})
            records.append(result)
        write_json(out/'results.json',records)
        print(s.name+': '+', '.join(f'{r["algorithm"]}={r["audit"]["length"] if r["audit"] else r["status"]} ({r.get("source")})' for r in records[-2:]),flush=True)
    all_rows = baseline+records
    by_case = defaultdict(dict)
    for r in all_rows:
        if r['audit'] and r['audit']['valid']:
            by_case[r['case']][r['algorithm']] = r['audit']['length']
    comparisons = {}
    for name in ('OARP_CORE_1','OARP_CORE_2'):
        for base in ('P1','P2'):
            c = Counter()
            a_total = b_total = 0
            for pair in by_case.values():
                if name in pair and base in pair:
                    a,b = pair[name],pair[base]
                    c['core_shorter' if a<b else 'baseline_shorter' if a>b else 'equal'] += 1
                    a_total += a
                    b_total += b
            comparisons[name+'_vs_'+base] = {'wins':dict(c),'core_total':a_total,'baseline_total':b_total}
    summary = {'snapshots':len(raw),'executions':len(records),'comparisons':comparisons,
        'by_algorithm':{name:{
            'statuses':dict(Counter(r['status'] for r in records if r['algorithm']==name)),
            'sources':dict(Counter(r.get('source') for r in records if r['algorithm']==name)),
            'invalid_routes':sum(bool(r['audit'] and not r['audit']['valid']) for r in records if r['algorithm']==name),
            'core_tours_returned':sum('tour' in r['detail'] for r in records if r['algorithm']==name),
            'fractional_LPs':sum(r['detail'].get('rank',{}).get('fractional_lp',False) for r in records if r['algorithm']==name),
            'integer_fallbacks':sum(r['detail'].get('rank',{}).get('used_integer_fallback',False) for r in records if r['algorithm']==name),
            'overruns_gt_10ms':sum(r.get('deadline_overrun',False) for r in records if r['algorithm']==name)
        } for name in ('OARP_CORE_1','OARP_CORE_2')},'held_out':False}
    write_json(out/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output',required=True)
    run(Path(p.parse_args().output))
