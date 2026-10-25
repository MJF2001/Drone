import json,hashlib,sys,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parent;UP=R/'PPCPP首次恢复完整试走_v0.1_20261020'
sys.path.insert(0,str(UP));from checks import audit,norm
from audit_branch import bfs
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from crosscheck import calculate
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    source=read(UP/'protocol.json');d=read(H/'diagnosis.json');assert len(d['states'])==47
    for x in d['states']:
        c=next(c for c in source['cases'] if c['batch']==x['batch'] and c['case_id']==x['case_id']);c=read(c['input']);r=read(x['source'])['raw'];audit(c,r)
        assert len(x['branches'])==len(r['branches'])
        trigger=r['branch_state'];assert x['triggered']==(trigger is not None)
        if trigger is not None:
            pending=set(map(tuple,trigger['pending']));db=bfs(set(map(tuple,c['free'])),tuple(c['base']))
            near=min(pending,key=lambda q:(db[q],q));far=min(pending,key=lambda q:(-db[q],q))
            initial=len(set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])})
            assert x['total_initial_pending']==initial and x['pending_at_trigger']==len(pending)
            assert x['remaining_fraction']==len(pending)/initial
        for b,raw in zip(x['branches'],r['branches']):
            labels=[];goal=tuple(raw['forced_goal']) if raw['forced_goal'] is not None else None
            if b['index']==0:labels.append('original_nearest' if trigger is not None else 'no_recovery')
            if trigger is not None and goal==near:labels.append('nearest_base')
            if trigger is not None and goal==far:labels.append('farthest_base')
            assert b['labels']==labels and b['goal']==(list(goal) if goal is not None else None)
            assert calculate(c,raw['route'])==b['metrics']
            assert sum(b['cost'].values())==len(raw['route'])-1
            if x['triggered']:
                e=next(e for e in raw['trace'] if e['kind']=='recovery');i=raw['trace'].index(e);ret=raw['trace'][-1];k=raw['trace'][i+1]['index']
                assert b['cost']==dict(shared_prefix=e['index'],first_approach=k-e['index'],continuation_to_last_target=ret['index']-k,return_steps=len(raw['route'])-1-ret['index'])
            assert b['difference_vs_original']==len(raw['route'])-len(r['branches'][0]['route'])
        assert x['difference']==x['branches'][x['chosen']]['difference_vs_original']
        alts=x['branches'][1:]
        cls='no_trigger' if trigger is None else 'improved' if x['difference']<0 else 'deduplicated_single' if not alts else 'tie_available' if any(b['difference_vs_original']==0 for b in alts) else 'all_alternatives_worse'
        assert x['classification']==cls
        b0=x['branches'][0]['metrics']
        assert x['equal_length_turn_pareto_candidates']==[b['index'] for b in alts if b['difference_vs_original']==0 and b['metrics']['turns90']<=b0['turns90'] and b['metrics']['turns180']<=b0['turns180'] and (b['metrics']['turns90']<b0['turns90'] or b['metrics']['turns180']<b0['turns180'])]
    for batch,s in d['summary'].items():
        own=[x for x in d['states'] if x['batch']==batch]
        for key,n in s['classification'].items():assert sum(x['classification']==key for x in own)==n
    accounting=read(H/'saved_branch_policy_accounting.json')
    for batch,ps in accounting.items():
        own=[x for x in d['states'] if x['batch']==batch]
        for policy,label in [('near','nearest_base'),('far','farthest_base')]:
            bs=[next((b for b in x['branches'] if label in b['labels']),x['branches'][0]) for x in own]
            assert ps[policy]==dict(total_steps=sum(b['metrics']['length'] for b in bs),shorter=sum(b['difference_vs_original']<0 for b in bs),equal=sum(b['difference_vs_original']==0 for b in bs),longer=sum(b['difference_vs_original']>0 for b in bs))
    report=(H/'首次恢复为何改善及为何未改善_20261020.md').read_text(encoding='utf-8')
    table=report.split('## 6.')[1].split('## 7.')[0]
    rows=[line.split('|')[1:-1] for line in table.splitlines() if line.startswith('| case')]
    assert len(rows)==20
    for cells in rows:
        key,*values=[s.strip() for s in cells];x=next(x for x in d['states'] if x['batch']=='original20' and x['case_id']==key)
        lengths=[str(x['branches'][0]['metrics']['length'])]
        lengths+=[str(next(b['metrics']['length'] for b in x['branches'] if label in b['labels'])) if x['triggered'] else '—' for label in ['nearest_base','farthest_base']]
        lengths.append(str(x['branches'][x['chosen']]['metrics']['length']));assert values==lengths,key
    if (H/'manifest.json').exists():
        m=read(H/'manifest.json');assert set(m)=={str(f.relative_to(H)) for f in H.rglob('*') if f.is_file() and f.name!='manifest.json'}
        for f,h in m.items():assert sha(H/f)==h,f
    print(json.dumps(dict(verified=True,saved_states=47,branches=d['branches_audited'],new_solver_calls=0,algorithm_changes=0,sealed=(H/'manifest.json').exists())))
if __name__=='__main__':main()
