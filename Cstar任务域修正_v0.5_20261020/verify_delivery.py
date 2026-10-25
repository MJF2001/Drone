"""Read-only verification. No solver import/call, no rewriting evidence."""
import hashlib,json
from collections import Counter
from pathlib import Path
from audit_v05 import audit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def native_chain(r):
    # A completed tour must be reached by the core's own hole branch; an
    # interrupted tour may exist without a completed iteration record.
    events=[e for e in r['events'] if e['type']=='tsp']
    traced=[it['tsp'] for it in r['iterations'] if it.get('tsp')]
    assert traced==[e for e in events if 'moved_steps' in e]
    for it in r['iterations']:
        if it.get('tsp'):assert it['holes']==it['tsp']['hole_nodes'] and it['holes']
    assert r['completion_tsp'] is False
def main():
    p=read(HERE/'protocol.json')
    for f,h in p['sources'].items():assert sha(HERE/f)==h,f
    unchanged=['common_geometry.py','history_core/__init__.py','history_core/planner.py','history_core/public_map.py','history_core/rcg.py']
    for f in unchanged:assert sha(HERE/'runtime'/f)==sha(ROOT/'Cstar状态缓存验收_20261019/runtime'/f)
    rows=read(HERE/'gate_checks.json')+read(HERE/'road_checks.json');assert len(rows)==len(p['jobs'])==106
    byid={r['run_id']:r for r in rows};assert len(byid)==106
    previous=read(ROOT/'七算法共同预算比较_v0.2_20261020/protocol.json')
    old={(j['case_id'],j['seed']):j for j in previous['jobs'] if j['method']=='CSTAR'}
    for j in p['jobs']:
        assert sha(Path(j['input']))==j['input_sha256']
        rp=HERE/'evidence/results'/(j['run_id']+'.json');z=read(rp);row=byid[j['run_id']]
        assert z['job']==j and row['result_sha256']==sha(rp)
        check=audit(read(Path(j['input'])),z['result'],j['budget']);native_chain(z['result'])
        for k,v in check.items():assert row[k]==v,(j['run_id'],k)
        assert row['timely']==(check['accepted'] and z['entry_seconds']<=j['budget']+.010)
        if j['kind']=='road':assert j['input_sha256']==old[j['name'],j['seed']]['input_sha256']
    c=read(HERE/'inputs/boundary_known.json');deadline=read(HERE/'deadline/checks.json')
    assert len(deadline)==63
    for item in deadline:
        r=read(HERE/'deadline'/(item['name']+'.json'));audit(c,r,2);native_chain(r)
        assert r['status']==item['status']
        if item['name'].endswith('__before'):assert r['status']=='task_complete'
        else:assert not r['route'] and r['status'] in ('deadline','wall_clock_cap')
    audit(c,read(HERE/'deadline/discovery.json'),2)
    road=[r for r in rows if r['kind']=='road'];summary=read(HERE/'road_summary.json')
    assert summary['calls']==len(road)==40
    assert summary['accepted']==sum(r['accepted'] for r in road)
    assert summary['timely']==sum(r['timely'] for r in road)
    assert summary['counts']==dict(Counter(r['status'] for r in road))
    assert summary['gate']==('PASS' if all(r['timely'] for r in road) else 'NOT_PASSED')
    if (HERE/'profile/protocol.json').exists():
        q=read(HERE/'profile/protocol.json');assert q['calls']==1 and q['budget']==5
        assert sha(Path(q['input']))==q['input_sha256'] and q['source_hashes']==p['sources']
        audit(read(Path(q['input'])),read(HERE/'profile/result.json'),5)
    if (HERE/'manifest.json').exists():
        manifest=read(HERE/'manifest.json')
        actual={str(f.relative_to(HERE)) for f in HERE.rglob('*') if f.is_file() and f.name!='manifest.json'}
        assert actual==set(manifest)
        for f,h in manifest.items():assert sha(HERE/f)==h,f
    print(json.dumps(dict(verified=True,gate_outputs=66,road_outputs=40,synthetic_deadlines=63,discovery=1,unchanged_core_files=5,road=summary,manifest=(HERE/'manifest.json').exists()),ensure_ascii=False))
if __name__=='__main__':main()
