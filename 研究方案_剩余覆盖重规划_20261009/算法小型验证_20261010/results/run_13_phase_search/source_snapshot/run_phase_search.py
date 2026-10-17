"""Two-repeat phase diagnostics at a common total time limit."""
from pathlib import Path
import argparse
import json
import hashlib
import statistics
import sys
from collections import Counter, defaultdict
from planners import solve
from phase_search import solve_phases
from audit import audit
from scenarios import deserialize
from run_experiments import write_json

NAMES = ('P2','SHIFT','REPEAT')


def run(source, output):
    root = Path(__file__).resolve().parent
    output.mkdir(parents=True,exist_ok=False)
    archive = output/'source_snapshot'
    archive.mkdir()
    hashes = {}
    for p in sorted(root.glob('*.py'))+[root/'config.json',root/'PHASE_PROTOCOL.md']:
        data = p.read_bytes()
        (archive/p.name).write_bytes(data)
        hashes[p.name] = hashlib.sha256(data).hexdigest()
    raw = json.loads((source/'snapshots.json').read_text(encoding='utf-8'))
    old = json.loads((source/'results.json').read_text(encoding='utf-8'))
    previous = {r['case']:r['audit']['length'] for r in old if r['algorithm']=='P2'}
    write_json(output/'snapshots.json',raw)
    write_json(output/'manifest.json',{'source':str(source.resolve()),'source_sha256':hashes,
        'input_sha256':hashlib.sha256((source/'snapshots.json').read_bytes()).hexdigest(),
        'python':sys.version,'repetitions':2,'total_time_limit_seconds':5,
        'held_out':False,'algorithms':NAMES,'stage':'exploratory phase sensitivity'})
    records, failures = [], []
    with (output/'execution_journal.jsonl').open('w',encoding='utf-8') as journal:
        for index,d in enumerate(raw):
            s = deserialize(d)
            for repeat in range(2):
                shift = (index+repeat)%3
                for name in NAMES[shift:]+NAMES[:shift]:
                    if name == 'P2':
                        result = solve(s,'P2',5)
                        r = {'algorithm':'P2','route':result.route,'status':result.status,
                             'reason':result.reason,'seconds':result.seconds,'searches':result.searches}
                    else:
                        r = solve_phases(s,name,5)
                    r.update(case=s.name,repeat=repeat,family=d['metadata']['family'],
                             domain_kind=d['metadata']['domain_kind'])
                    r['audit'] = audit(s,r['route'])
                    r['expected_case_handled'] = r['audit']['valid'] and r['status'] in ('planned','planned_at_timeout')
                    if not r['expected_case_handled']:
                        failures.append([s.name,name,repeat,r['status']])
                    if name=='P2' and r['audit']['length'] != previous[s.name]:
                        failures.append([s.name,'baseline_mismatch',repeat])
                    if name!='P2' and r['baseline_stage_length'] != previous[s.name]:
                        failures.append([s.name,name,'original_stage_mismatch',repeat])
                    records.append(r)
                    journal.write(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n')
                    journal.flush()
            print(s.name+': '+', '.join(f'{r["algorithm"]}={r["audit"]["length"]} ({r["seconds"]:.3f}s, {r["status"]})'
                for r in records[-6:] if r['repeat']==0),flush=True)
    (output/'results.json').write_text(json.dumps(records,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    pairs = defaultdict(dict)
    for r in records:
        if r['audit']['valid']:
            pairs[r['case'],r['repeat']][r['algorithm']] = r
    comparisons = {}
    for name in ('SHIFT','REPEAT'):
        for repeat in range(2):
            counts = Counter()
            for (case,rep),pair in pairs.items():
                if rep != repeat or 'P2' not in pair or name not in pair:
                    continue
                a,b = pair[name]['audit']['length'],pair['P2']['audit']['length']
                counts['shorter' if a<b else 'longer' if a>b else 'equal'] += 1
            comparisons[f'{name}_vs_P2_repeat{repeat}'] = dict(counts)
    timing = {}
    for name in NAMES:
        times = sorted(r['seconds'] for r in records if r['algorithm']==name)
        timing[name] = {'median_ms':statistics.median(times)*1000,
            'p95_ms':times[(95*len(times)+99)//100-1]*1000,'max_ms':max(times)*1000}
    changed = []
    for d in raw:
        for name in NAMES:
            a,b = pairs[d['name'],0].get(name),pairs[d['name'],1].get(name)
            if a and b and a['route'] != b['route']:
                changed.append([d['name'],name,a['audit']['length'],b['audit']['length']])
    summary = {'snapshot_count':len(raw),'execution_count':len(records),'failures':failures,
        'comparisons':comparisons,'timing':timing,
        'statuses':{name:dict(Counter(r['status'] for r in records if r['algorithm']==name)) for name in NAMES},
        'completed_pools':{name:dict(Counter(sum(log['completed'] for log in r['logs'])
            for r in records if r['algorithm']==name)) for name in ('SHIFT','REPEAT')},
        'first_repeat_total_lengths':{name:sum(r['audit']['length'] for r in records
            if r['algorithm']==name and r['repeat']==0 and r['audit']['valid']) for name in NAMES},
        'repeat_route_differences':changed,'held_out':False}
    write_json(output/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    p.add_argument('--output',required=True)
    args = p.parse_args()
    run(Path(args.source),Path(args.output))
