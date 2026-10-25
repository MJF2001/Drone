"""Read-only evidence re-audit; no planner calls or output writes."""
import hashlib,json
from pathlib import Path
from collections import Counter
from audit_v05 import audit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def view(r):return {k:v for k,v in r.items() if k not in ('seconds','version','adaptation','protection_cache','efficiency_stats')}
def chain(r):
    events=[e for e in r['events'] if e['type']=='tsp']
    assert [it['tsp'] for it in r['iterations'] if it.get('tsp')]==[e for e in events if 'moved_steps' in e]
    for it in r['iterations']:
        if it.get('tsp'):assert it['holes'] and it['holes']==it['tsp']['hole_nodes']
    assert r['completion_tsp'] is False
    for s in r['efficiency_stats']:
        assert s['rows']==s['points'] and s['exact_queries']<=s['points']*(s['points']+1)//2
def main():
    p=read(HERE/'protocol.json');v7=p['version'].endswith('v0.7')
    for f,h in p['sources'].items():assert sha(HERE/f)==h,f
    for f in ('__init__.py','planner.py','public_map.py','rcg.py'):
        assert sha(HERE/'runtime/history_core'/f)==sha(ROOT/'Cstar任务域修正_v0.5_20261020/runtime/history_core'/f)
    if v7:
        assert sha(HERE/'runtime/equivalent_tsp.py')==sha(ROOT/'Cstar等价效率修正_v0.6_20261020/runtime/equivalent_tsp.py')
    else:assert sha(HERE/'runtime/common_geometry.py')==sha(ROOT/'Cstar任务域修正_v0.5_20261020/runtime/common_geometry.py')
    gates=read(HERE/'gate_checks.json');roads=read(HERE/'road_checks.json');rows=gates+roads
    assert len(rows)==len(p['jobs']) and len(roads)==40 and len({r['run_id'] for r in rows})==len(rows)
    byid={r['run_id']:r for r in rows};goldens=0
    common=read(ROOT/'七算法共同预算比较_v0.2_20261020/protocol.json')
    original={(j['case_id'],j['seed']):j for j in common['jobs'] if j['method']=='CSTAR'}
    for j in p['jobs']:
        assert sha(Path(j['input']))==j['input_sha256']
        rp=HERE/'evidence/results'/(j['run_id']+'.json');z=read(rp);assert z['job']==j
        row=byid[j['run_id']];assert row['result_sha256']==sha(rp)
        checks=audit(read(Path(j['input'])),z['result'],j['budget']);chain(z['result'])
        for k,v in checks.items():assert row[k]==v,(j['run_id'],k)
        assert row['timely']==(row['accepted'] and z['entry_seconds']<=j['budget']+.010)
        if j['kind']=='road':assert j['input_sha256']==original[j['name'],j['seed']]['input_sha256']
        if 'golden' in j:
            assert sha(Path(j['golden']))==j['golden_sha256']
            assert view(read(Path(j['golden']))['result'])==view(z['result']) and row['golden_equal'];goldens+=1
    g=read(HERE/'gates_PASS.json');assert g['calls']==len(gates) and g['golden_calls']==goldens and g['unit_tests']==p['unit_tests']
    fixture=read(ROOT/'Cstar任务域修正_v0.5_20261020/inputs/boundary_known.json');deadline=read(HERE/'deadline/checks.json')
    assert len(deadline)==3*len(g['stages'])==g['deadline_calls']
    for d in deadline:
        r=read(HERE/'deadline'/(d['name']+'.json'));audit(fixture,r,2);chain(r);assert r['status']==d['status']
        assert r['status']=='task_complete' if d['name'].endswith('__before') else r['status'] in ('deadline','wall_clock_cap') and not r['route']
    audit(fixture,read(HERE/'deadline/discovery.json'),2)
    summary=read(HERE/'road_summary.json')
    assert summary['calls']==40 and summary['accepted']==sum(r['accepted'] for r in roads) and summary['timely']==sum(r['timely'] for r in roads)
    assert summary['counts']==dict(Counter(r['status'] for r in roads))
    assert summary['gate']==('PASS' if all(r['timely'] for r in roads) else 'NOT_PASSED')
    if v7:
        analysis=read(HERE/'correction_analysis.json');assert analysis['versions']['v07']['timely']==summary['timely']
        previous={r['run_id']:r for r in read(ROOT/'Cstar等价效率修正_v0.6_20261020/road_checks.json')}
        prefix=0
        for row in roads:
            oldrow=previous[row['run_id']]
            if oldrow['accepted'] or not row['accepted']:continue
            old=read(ROOT/'Cstar等价效率修正_v0.6_20261020/evidence/results'/(row['run_id']+'.json'))['result']
            new=read(HERE/'evidence/results'/(row['run_id']+'.json'))['result']
            assert old['diagnostic_route']==new['route'][:len(old['diagnostic_route'])]
            completed=[it for it in old['iterations'] if it['why']['group']!='failure']
            assert completed==new['iterations'][:len(completed)]
            assert sum(it['why']['group']=='failure' for it in old['iterations'])==1
            strip=lambda e:{k:v for k,v in e.items() if k!='moved_steps'}
            assert list(map(strip,old['events']))==list(map(strip,new['events'][:len(old['events'])]));prefix+=1
        assert prefix==len(analysis['v06_failed_prefix_checks'])==4
        if (HERE/'freeze.json').exists():
            f=read(HERE/'freeze.json');assert summary['gate']=='PASS' and f['status']=='ACCEPTED_FOR_NEXT_COMMON_BENCHMARK'
            for name,h in f['runtime_sha256'].items():assert sha(HERE/name)==h
            for name,h in f['parent_evidence_sha256'].items():assert sha(ROOT/name)==h
    if not v7:
        q=read(HERE/'cost_oracle/protocol.json');c=read(HERE/'cost_oracle/checks.json')
        assert q['sources']==p['sources'] and c['pass_all'] and c['solver_calls']==0
        for f,h in q['outputs'].items():assert sha(Path(f))==h
        assert len(c['rows'])==20 and sum(x.get('pairs',0) for x in c['rows'])==960
        assert len(c['utility_deadlines'])==3
    if (HERE/'manifest.json').exists():
        m=read(HERE/'manifest.json');actual={str(f.relative_to(HERE)) for f in HERE.rglob('*') if f.is_file() and f.name!='manifest.json'}
        assert actual==set(m)
        for f,h in m.items():assert sha(HERE/f)==h,f
    print(json.dumps(dict(verified=True,version=p['version'],gates=len(gates),golden_equal=goldens,unit_tests=p['unit_tests'],deadline_calls=len(deadline),road=summary,sealed=(HERE/'manifest.json').exists()),ensure_ascii=False))
if __name__=='__main__':main()
