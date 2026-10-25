"""Supplementary read-only report transcription and example check, no solver calls."""
import json,pathlib,hashlib
from audit_branch import bfs
H=pathlib.Path(__file__).resolve().parent
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))
def main():
    a=read(H/'analysis.json');doc=(H/'恢复时机对照结果_20261020.md').read_text(encoding='utf-8')
    for batch,z in a['summary'].items():
        for name,v in z['pairs'].items():
            expected='|'+ '|'.join(map(str,[batch+'/'+name,v['common_states'],f"{v['shorter']}/{v['equal']}/{v['longer']}",f"{v['total_a']}/{v['total_b']}",v['difference'],f"{v['mean_relative']:.4%}"]))+'|'
            assert expected in doc,expected
    for x in a['states']:
        if x['batch']!='original20':continue
        v=x['methods'];expected='|'+ '|'.join(map(str,[x['case_id']]+[v[m]['metrics']['length'] for m in ('PPCPP','FIRST','SECOND')]+[v['SECOND']['metrics']['length']-v['FIRST']['metrics']['length'],f"{v['FIRST']['triggered']}/{v['SECOND']['triggered']}",f"{v['FIRST']['candidates']}/{v['SECOND']['candidates']}"]))+'|'
        assert expected in doc,expected
    p=read(H/'protocol.json');examples=[]
    for method in ('FIRST','SECOND'):
        j=next(j for j in p['jobs'] if j['case_id']=='gap_family0_gap1' and j['method']==method and j['seed']==20261018);c=read(j['input'])
        r=read(H/'execution/results'/(j['run_id']+'.json'))['raw'];event=r['trace'][-1];assert event['index']==17
        route=list(map(tuple,r['route']));pending=set(map(tuple,c['targets']))-set(map(tuple,c['covered']))
        completed=None
        for i,q in enumerate(route):
            pending.discard(q)
            if not pending:completed=i;break
        assert completed==17 and tuple(event['current'])==route[completed]
        tail=len(route)-1-completed;assert tail==bfs(set(map(tuple,c['free'])),route[completed])[tuple(c['base'])]==(4 if method=='FIRST' else 8)
        examples.append(dict(method=method,completion_step=completed,completion_cell=route[completed],return_steps=tail))
    states={x['case_id']:x for x in a['states'] if x['batch']=='original20'}
    diff=lambda x,k:states[x]['methods']['SECOND']['metrics'][k]-states[x]['methods']['FIRST']['metrics'][k]
    assert sum(diff(x,'turns90') for x in states)==-72 and diff('case19','turns90')==-124
    assert sum(diff(x,'turns90') for x in states if x!='case19')==52
    assert [diff(x,'length') for x in ['case01','case10','case11','case09']]==[-2,-18,-22,20]
    result=dict(report_tables_verified=True,pair_rows=6,road_state_rows=20,narrative_examples_verified=True,examples=examples,report_sha256=hashlib.sha256((H/'恢复时机对照结果_20261020.md').read_bytes()).hexdigest(),new_solver_calls=0)
    (H/'report_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
