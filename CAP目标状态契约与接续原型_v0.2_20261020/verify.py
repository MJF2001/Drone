"""Re-audit saved local states and original cut; no CAP/region solver calls."""
import json,hashlib
from pathlib import Path
from audit_contract import audit
from replay_saved import components,points
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=read(HERE/'protocol.json');assert p['unit_tests']==20 and p['full_CAP_solver_calls']==p['formal_performance_calls']==0
    for f,h in p['files'].items():assert sha(Path(f))==h,f
    for f in ('target_contract.py','primitives.py'):assert sha(HERE/'runtime'/f)==sha(ROOT/'CAP目标状态契约与接续原型_v0.1_20261020/runtime'/f)
    assert sha(HERE/'runtime/primitives.py')==sha(ROOT/'CAP单源查询修正_v0.2_20261020/runtime/primitives.py')
    log=(HERE/'unit.log').read_text(encoding='utf-16' if (HERE/'unit.log').read_bytes().startswith(b'\xff\xfe') else 'utf-8')
    assert 'Ran 20 tests' in log and '\nOK' in log and 'FAILED' not in log
    records=read(HERE/'mechanism_cases.json')
    for x in records:assert audit(x['input'],x['result'])==x['check']
    d=read(HERE/'saved_replay.json');assert d['full_CAP_solver_calls']==0 and d['saved_input_jobs']==40 and d['unique_inputs']==20
    assert d['missing_explicit_resume_target_jobs']==40 and not any(x['has_resume_target'] for x in d['missing_records'])
    batch=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020'
    for item in d['split_replays']:
        r=read(batch/'execution/results'/(item['run_id']+'.json'))['raw'];first=r['plans'][0];second=r['plans'][1]
        node=next(n for n in first['structure_before']['nodes'] if n['id']==second['region_id']);remaining=points(node['R']);assert len(remaining)==142
        path=list(map(tuple,r['diagnostic_route']))
        for entry in item['critical_cells']:
            cur=points(node['R'])-set(path[first['path_start']+1:entry['path_index']]);assert len(components(cur))==entry['components_before']
            assert path[entry['path_index']]==tuple(entry['actual_cell']);cur.discard(path[entry['path_index']]);assert sorted(map(len,components(cur)))==entry['component_sizes']==[2,137]
        remaining-=set(path[first['path_start']+1:first['path_end']+1]);assert remaining==points(second['required']) and len(components(remaining))==2
    if (HERE/'manifest.json').exists():
        m=read(HERE/'manifest.json');assert set(m)=={str(f.relative_to(HERE)) for f in HERE.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(HERE/f)==h,f
    print(json.dumps(dict(verified=True,unit_tests=20,saved_local_snapshots=len(records),saved_CAP_input_jobs=40,exact_cut_replays=2,full_CAP_solver_calls=0,formal_performance_calls=0,complete_CAP_implementation=False,sealed=(HERE/'manifest.json').exists()),ensure_ascii=False))
if __name__=='__main__':main()
