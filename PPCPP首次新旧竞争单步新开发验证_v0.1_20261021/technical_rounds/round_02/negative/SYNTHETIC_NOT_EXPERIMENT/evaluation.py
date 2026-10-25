"""Experiment-specific saved-output association; byte-frozen independent action audit."""
from common import *
from decision_audit import saved_audit,paired_audit
import copy
def frozen_action_audit(c,out):
    # Metadata-only diagnostic view permits the exact old independent auditor
    # to check frozen choices; the stored frozen result is never altered.
    x=copy.deepcopy(out);x['job']['mode']='OFF'
    x['result']['raw']['branches']['P0']['diagnostic']=dict(mode='OFF',intervention_used=False,trigger_count=0,log=[])
    return saved_audit(c,x,0)
def job_row(j):
    p=H/'outputs'/f'{j["id"]}.json'
    if not p.exists():
        q=H/'logs'/f'{j["id"]}.receipt.json';v=read(q) if q.exists() else None
        return dict(job=j,ran=bool(v),valid=False,timely=False,metrics=None,status=v['status'] if v else 'NOT_RUN',seconds=None)
    out=read(p);assert out['job']==j and out['input_sha256']==sha(H/j['input']);c=read(H/j['input']);x=out['result']
    assert x['method']=='PPCPP' and x['budget']==20 and x['seed']==j['seed']
    if not x['raw'].get('route'):
        assert x['raw']['status'] in ('deadline','planning_failure','environment_infeasible')
        return dict(job=j,ran=True,valid=False,timely=False,metrics=None,status=x['raw']['status'],seconds=x['entry_seconds'],native_failure=True)
    if j['mode']=='FROZEN':z=frozen_action_audit(c,out)
    else:
        st=next(s for s in read(H/'states_metadata.json') if s['id']==j['state']);expected=int(j['mode']=='ON' and st['condition'] in ('MIXED_SIDE','U_SIDE'))
        z=saved_audit(c,out,expected)
    assert len(out['actual_core_calls'])==1 and set(out['runtime_reads'])=={str(H/j['input'])}
    eq=None
    if j['mode']=='OFF':
        original=read(H/'outputs'/f'gate_{j["state"]}_FROZEN.json')
        if j['phase']=='gate':eq=equivalent(out,original)
        else:
            gate_off=read(H/'outputs'/f'gate_{j["state"]}_OFF.json');gate_proof=equivalent(gate_off,original)
            assert x['raw']['route']==gate_off['result']['raw']['route'] and x['raw']['trace']==gate_off['result']['raw']['trace']
            assert x['raw']['branches']['P0']['seed_used'] is False and x['raw']['branches']['P0']['seed']==j['seed']
            eq=dict(passed=True,gate_seed=20261020,formal_seed=j['seed'],gate_equivalence=gate_proof,formal_full_route_trace_and_metrics_equal_gate=True,formal_independent_reward_audit=True,note='Fresh formal replicate; seed metadata differs as scheduled. Original gate whitelist unchanged.')
        assert z['metrics']==both(c,original['result']['raw']['route'])
    return dict(job=j,ran=True,valid=True,timely=x['eligible'] and x['entry_seconds']<20,metrics=z['metrics'],status=x['raw']['status'],seconds=x['entry_seconds'],caller_wall_seconds=out['caller_wall_seconds'],audit=z,equivalence=eq)

def check_formal_pair(j):
    if j['phase']!='formal':return None
    other='ON' if j['mode']=='OFF' else 'OFF';p=H/'outputs'/f'formal_{j["state"]}_{j["seed"]}_{other}.json'
    if not p.exists():return None
    off=read(H/'outputs'/f'formal_{j["state"]}_{j["seed"]}_OFF.json');on=read(H/'outputs'/f'formal_{j["state"]}_{j["seed"]}_ON.json')
    if off['result']['raw'].get('route') and on['result']['raw'].get('route'):return paired_audit(read(H/j['input']),off,on)
