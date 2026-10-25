"""Read-only evidence check. Does not call graph, tour, or CAP solvers."""
import json,hashlib
from pathlib import Path
from checks import audit
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert digest(Path(f))==h,f
    for name in ('structures.py','primitives.py'):
        assert digest(H/'runtime'/name)==digest(H.parent/'CAP单源查询修正_v0.2_20261020/runtime'/name)
    log=(H/'unit.log').read_text(encoding='utf-8-sig')
    assert 'Ran 12 tests' in log and '\nOK' in log and 'FAILED' not in log
    records=read(H/'replay.json');jobs={j['run_id']:j for j in p['jobs']};splits=[]
    assert len(records)==60 and len({x['run_id'] for x in records})==40
    for x in records:
        j=jobs[x['run_id']];c=read(Path(j['input']));r=read(Path(j['result']))['raw']
        plan=r['plans'][x['plan_index']]
        assert x['before']==plan['structure_before']
        pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-set(map(tuple,r['diagnostic_route'][:plan['path_end']+1]))
        assert pending==set(map(tuple,x['pending']))
        assert audit(x['before'],x['after'],pending)==x['check']
        events=x['events'];batch=[e for e in events if e['type']=='known_residual_split_batch']
        if batch:
            assert len(batch)==1 and sum(e['type']=='global_replan' for e in events)==1
            splits.append(x)
            old_ids={n['id'] for n in x['before']['nodes']};new_nodes={n['id']:n for n in x['after']['nodes']}
            for rep in batch[0]['replacements']:
                assert rep['parent'] in old_ids and rep['parent'] not in new_nodes
                assert all(i not in old_ids for i in rep['children'])
                assert [new_nodes[i]['R'] for i in rep['children']]==rep['parts']
        else:
            assert not events
            active={n['id'] for n in x['after']['nodes'] if n['R']}
            assert x['after']['order']==[i for i in x['before']['order'] if i in active]
    assert len(splits)==2 and {x['case_id'] for x in splits}=={'case10'}
    for x in splits:
        assert x['plan_index']==0
        assert sorted(len(n['R']) for n in x['after']['nodes'] if n['R'])==[2,137]
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json')
        assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert digest(H/f)==h,f
    print(json.dumps(dict(verified=True,tests=12,boundaries=60,split_boundaries=2,unique_split_cases=1,full_CAP_calls=0,performance_calls=0,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
