"""Saved actual source/response and dual metrics plus independent full log audit."""
from util import *
from auditor import audit
import importlib.util
def load(fn,p):
    s=importlib.util.spec_from_file_location(fn,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=R/'评价指标完整补算与数据审计_v0.1_20261020'
metric=load('real_interface_metrics',M/'metrics.py').metrics;cross=load('real_interface_cross',M/'crosscheck.py').calculate
def inspect_session(sj,counter):
    result=read(H/'sessions'/(sj['id']+'.json'));spec=dict(id=sj['id'],category='REAL_INTERFACE',world=read(H/'worlds.json')[sj['world']],methods={sj['method']:None})
    proof=audit(result,spec,counter);s=result['sessions'][sj['method']];static=[];sources=[]
    for req in s['requests']:
        slot=next(z for z in read(H/'call_slots.json') if z['session']==sj['id'] and z['tick']==req['tick']);rid=slot['id'];out=read(H/'outputs'/(rid+'.json'));j=read(H/'jobs'/(rid+'.json'));receipt0=read(H/'logs'/(rid+'.receipt.json'))
        assert out['job']==j and j['slot']==slot and req['payload_sha256']==sha(H/j['input'])==out['input_sha256']
        assert (H/j['input']).read_bytes()==req['payload_utf8'].encode('utf8') and req['response']==out['entry']['response']
        assert set(out['runtime_reads'])=={str(H/j['input'])} and len(out['core_calls'])==1 and 'end' in out['core_calls'][0]
        assert receipt0['output_sha256']==sha(H/'outputs'/(rid+'.json')) and receipt0['exit_code']==0
        seal=read(H/'seal.json')
        for p,v in out['imports'].items():assert seal['files'][p]==v==sha(p)
        entry=out['entry'];native=entry['native_return'];assert entry['entry_budget']==20 and native['budget']==entry['inner_budget']==20-entry['preprocess_seconds'] and native['entry_seconds']<=entry['entry_seconds']<=out['worker_wall_seconds']<=receipt0['callback_total_wall_seconds']
        assert entry['native_payload_utf8']==req['payload_utf8'] and native['raw'].get('route',[])==req['response']['route']
        if sj['method']=='PPCPP':assert set(native['raw']['branches'])=={'P0'} and native['raw']['mode']=='PPCPP' and native['raw']['branches']['P0']['version']=='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'
        else:assert native['method']=='P2_MULTI'
        met=None
        if req['response']['route']:
            met=metric(req['input'],req['response']['route']);assert met==cross(req['input'],req['response']['route']) and met['complete_legal']
        static.append(dict(id=rid,tick=req['tick'],admission=req['admission'],native_status=req['response']['native_status'],entry_seconds=entry['entry_seconds'],inner_native_seconds=native['entry_seconds'],inner_budget=entry['inner_budget'],preprocess_seconds=entry['preprocess_seconds'],callback_total_wall_seconds=receipt0['callback_total_wall_seconds'],metrics=met,strict_timely=entry['entry_seconds']<20))
        sources.append(dict(id=rid,input_sha256=out['input_sha256'],output_sha256=sha(H/'outputs'/(rid+'.json')),plan_before=req['plan_before'],cursor_before=req['cursor_before'],actual_prefix=req['actual_prefix']))
    # Evidence that event2 is from response1 execution, even if two routes coincide.
    chain=None
    if len(s['requests'])==3:
        r1,r2=s['requests'][1:];moves=[a for a in s['actions'] if a['kind']=='move' and r1['tick']<=a['tick']<r2['tick']];adopt=r1['plan_adopted'];assert moves and r2['plan_before']==adopt
        assert [a['end'] for a in moves]==adopt[1:len(moves)+1] and r2['cursor_before']==len(moves)
        chain=dict(passed=True,event1_tick=r1['tick'],event2_tick=r2['tick'],event1_actual_moves=moves,event2_input_current=r2['input']['current'],event2_previous=r2['input']['previous'],event2_H=r2['input']['covered'],event2_remaining_resource=r2['input']['distance_budget'],source='actual response1 adopted plan prefix, not initial plan checkpoint')
    zero_base=[e for e in s['credits'] if e['source']=='publication' and e['tick']==4 and e['point']==[0,0]] if sj['world']=='W3' else None
    passed=s['summary']['status']=='success' and s['summary']['returned'] and len(s['requests'])==3 and chain is not None and all(r['admission']=='accepted' and r['strict_timely'] and r['metrics'] for r in static)
    return dict(session=sj,passed=bool(passed),independent_log_audit=proof,static_dual_metrics=static,input_sources=sources,two_event_chain=chain,summary=s['summary'],W3_base_zero_credit_triggered=bool(zero_base) if sj['world']=='W3' else None)
