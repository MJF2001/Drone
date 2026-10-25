"""Reconstruct all completed calls from raw results; no planner import."""
from decision_audit import *
import statistics

def compute(phase=None):
    order=read(H/'fixed_order.json');rows=[];audits={};outputs={}
    for j in order:
        if phase and j['phase']!=phase:continue
        file=H/'outputs'/f'{j["id"]}.json'
        if not file.exists():continue
        out=read(file);assert out['job']==j and len(out['actual_core_calls'])==1 and out['input_sha256']==sha(H/j['input']);x=out['result'];assert x['eligible'] and x['entry_seconds']<20 and x['raw']['status']=='core_complete';a=audit(read(H/j['input']),out);audits[j['id']]=a;outputs[j['id']]=out
        rows.append(dict(**j,seconds=x['entry_seconds'],eligible=x['eligible'],legal=a['metrics']['complete_legal'],**a['metrics'],completion_position=a['completion_position'],forced_count=a['forced_count'],second_step_returns_to_origin=a['second_step_returns_to_origin'],first_return_origin_index=a['first_return_origin_index'],first_new_capture=a['first_new_capture'],first_regular_decision=a['first_regular_decision']))
    equal=[];pairs=[]
    for case in CASES:
        for seed in SEEDS:
            rep=SEEDS.index(seed);old=read(S/'outputs'/f'{case}__{rep}__PPCPP.json')['result']
            def get(ph,mode):return outputs.get(f'{ph}__{case}__{seed}__{mode}')
            f=get('gate','FROZEN');off=get('gate','OFF')
            if f and off:
                assert comparable(f['result'])==comparable(off['result'])==comparable(old);equal.append(dict(case=case,seed=seed,gate_frozen=f['job']['id'],off=off['job']['id'],historical_id=f'{case}__{rep}__PPCPP',all_non_time_fields_equal=True))
            ff=get('formal','FROZEN');on=get('formal','ON')
            if ff and on:
                assert f and comparable(ff['result'])==comparable(f['result'])==comparable(old);fm=audits[ff['job']['id']]['metrics'];om=audits[on['job']['id']]['metrics'];delta={k:om[k]-fm[k] for k in ('length','completion_step','return_tail_steps','turns90','turns180','historical_target_steps','repeated_new_target_steps','non_target_steps')};assert delta['length']==delta['completion_step']+delta['return_tail_steps'];c=read(H/ff['job']['input'])
                pairs.append(dict(case=case,seed=seed,FROZEN_id=ff['job']['id'],ON_id=on['job']['id'],delta=delta,FROZEN=fm,ON=om,FROZEN_seconds=ff['result']['entry_seconds'],ON_seconds=on['result']['entry_seconds'],FROZEN_E=audits[ff['job']['id']]['completion_position'],ON_E=audits[on['job']['id']]['completion_position'],timely_legal_complete=True,intervention=on['result']['raw']['branches']['P0']['intervention'],rejoin=rejoin(c,ff,on),background_old_P2_length=len(read(S/'outputs'/f'{case}__{rep}__P2_MULTI.json')['result']['raw']['route'])-1))
    states=[]
    for case in CASES:
        pp=[p for p in pairs if p['case']==case]
        if pp:states.append(dict(case=case,n=len(pp),seeds=[p['seed'] for p in pp],raw_delta=[p['delta'] for p in pp],mean_delta={k:statistics.mean(p['delta'][k] for p in pp) for k in pp[0]['delta']},range_delta={k:[min(p['delta'][k] for p in pp),max(p['delta'][k] for p in pp)] for k in pp[0]['delta']},all_three_strictly_shorter=len(pp)==3 and all(p['delta']['length']<0 for p in pp)))
    return norm(dict(rows=rows,audits=audits,equivalence=equal,pairs=pairs,states=states,ordinary_BFS_total=sum(a['ordinary_BFS_tables'] for a in audits.values()),stop_verdict='two_specified_states_consistently_shorter' if len(states)==2 and all(s['all_three_strictly_shorter'] for s in states) else 'no_strict_benefit_stop' if len(pairs)==6 and all(p['delta']['length']>=0 for p in pairs) else 'case_signal_or_tradeoff' if len(pairs)==6 else 'incomplete'))

if __name__=='__main__':
    import sys
    phase=sys.argv[1];a=compute('gate' if phase=='gate' else None)
    if phase=='gate':assert len(a['rows'])==12 and len(a['equivalence'])==6;save(H/'gate_analysis.json',a);print('PASS 12 gate calls; all decision-related non-time fields equal to each other and old pressure outputs')
    else:
        assert len(a['rows'])==24 and len(a['pairs'])==6;save(H/'analysis.json',a);csvsave(H/'24调用完整指标.csv',a['rows']);csvsave(H/'6正式配对.csv',a['pairs']);csvsave(H/'2状态三种子原值均值范围.csv',a['states']);save(H/'all_decision_audits.json',a['audits']);print(json.dumps(dict(states=a['states'],verdict=a['stop_verdict'],ordinary_BFS=a['ordinary_BFS_total']),ensure_ascii=False))
