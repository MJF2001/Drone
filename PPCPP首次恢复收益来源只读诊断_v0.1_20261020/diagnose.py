"""Read sealed branches only. No planner calls, new goals or new rollouts."""
import json,hashlib,sys,statistics
from pathlib import Path
from collections import deque,Counter
H=Path(__file__).resolve().parent;R=H.parent;UP=R/'PPCPP首次恢复完整试走_v0.1_20261020'
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
from crosscheck import calculate
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def distances(f,start):
    d={start:0};q=deque([start])
    while q:
        x,y=q.popleft()
        for z in ((x-1,y),(x,y+1),(x,y-1),(x+1,y)):
            if z in f and z not in d:d[z]=d[(x,y)]+1;q.append(z)
    return d
def main():
    p=read(H/'protocol.json')
    for f,h in p['files'].items():assert sha(f)==h,f
    source=read(UP/'protocol.json');states=[]
    for case in source['cases']:
        c=read(case['input']);j=next(j for j in source['jobs'] if j['batch']==case['batch'] and j['case_id']==case['case_id'] and j['method']=='THREE' and j['seed']==20261018)
        path=UP/'execution/results'/(j['run_id']+'.json');raw=read(path)['raw'];bs=raw['branches'];base=bs[0];trigger=raw['branch_state']
        initial=len(set(map(tuple,c['targets']))-set(map(tuple,c['covered']))-{tuple(c['current'])})
        record=dict(batch=case['batch'],case_id=case['case_id'],source=str(path),triggered=trigger is not None,total_initial_pending=initial,chosen=raw['selected_branch'],branches=[])
        near=far=None
        if trigger:
            pending=set(map(tuple,trigger['pending']));db=distances(set(map(tuple,c['free'])),tuple(c['base']))
            near=min(pending,key=lambda q:(db[q],q));far=min(pending,key=lambda q:(-db[q],q))
            record.update(pending_at_trigger=len(pending),remaining_fraction=len(pending)/initial,prefix_steps=len(trigger['path'])-1)
        for i,b in enumerate(bs):
            m=metrics(c,b['route']);assert m==calculate(c,b['route'])
            recoveries=[e for e in b['trace'] if e['kind']=='recovery'];ret=b['trace'][-1];assert ret['kind']=='return'
            if trigger:
                first=recoveries[0];k=b['trace'].index(first);approach_end=b['trace'][k+1]['index'];approach=approach_end-first['index'];after=ret['index']-approach_end
                cost=dict(shared_prefix=first['index'],first_approach=approach,continuation_to_last_target=after,return_steps=len(b['route'])-1-ret['index'])
                assert sum(cost.values())==m['length'] and first['index']==record['prefix_steps']
            else:cost=dict(coverage=ret['index'],return_steps=len(b['route'])-1-ret['index'])
            labels=[];goal=tuple(b['forced_goal']) if b['forced_goal'] is not None else None
            if i==0:labels.append('original_nearest' if trigger else 'no_recovery')
            if trigger and goal==near:labels.append('nearest_base')
            if trigger and goal==far:labels.append('farthest_base')
            record['branches'].append(dict(index=i,goal=goal,labels=labels,selected=i==record['chosen'],metrics=m,cost=cost,recovery_count=len(recoveries),later_recovery_count=max(0,len(recoveries)-1),difference_vs_original=m['length']-(len(base['route'])-1)))
        gain=record['branches'][record['chosen']]['difference_vs_original'];record['difference']=gain
        alts=record['branches'][1:]
        record['classification']='no_trigger' if not trigger else 'improved' if gain<0 else 'deduplicated_single' if not alts else 'tie_available' if any(b['difference_vs_original']==0 for b in alts) else 'all_alternatives_worse'
        b0=record['branches'][0]['metrics']
        record['equal_length_turn_pareto_candidates']=[b['index'] for b in alts if b['difference_vs_original']==0 and b['metrics']['turns90']<=b0['turns90'] and b['metrics']['turns180']<=b0['turns180'] and (b['metrics']['turns90']<b0['turns90'] or b['metrics']['turns180']<b0['turns180'])]
        states.append(record)
    summary={}
    for batch in ('original20','controlled27'):
        xs=[x for x in states if x['batch']==batch];classes=dict(Counter(x['classification'] for x in xs));improved=[x for x in xs if x['classification']=='improved'];unchanged=[x for x in xs if x['triggered'] and x['difference']==0]
        summary[batch]=dict(states=len(xs),classification=classes,improved_remaining_fractions=[x['remaining_fraction'] for x in improved],unchanged_triggered_remaining_fractions=[x['remaining_fraction'] for x in unchanged],improved_with_later_recoveries=sum(x['branches'][0]['later_recovery_count']>0 for x in improved),unchanged_with_later_recoveries=sum(x['branches'][0]['later_recovery_count']>0 for x in unchanged),tie_turn_pareto_states=[x['case_id'] for x in xs if x['equal_length_turn_pareto_candidates']])
    save('diagnosis.json',dict(states=states,summary=summary,new_solver_calls=0,unique_saved_THREE_results=47,branches_audited=sum(len(x['branches']) for x in states),scope='observed saved candidates only; no claim about untried entries or later triggers'))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for x in states:
        if x['batch']=='original20':print(x['case_id'],x['classification'],[(b['labels'],b['metrics']['length'],b['cost']) for b in x['branches']])
if __name__=='__main__':main()
