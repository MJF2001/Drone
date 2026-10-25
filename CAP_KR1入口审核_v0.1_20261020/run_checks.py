import json,hashlib,time
from pathlib import Path
from entry import invoke
from audit import audit
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    protocol=read(H/'protocol.json')
    for f,h in protocol['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
    records=[]
    def call(name,payload,**kw):
        r=invoke(payload,**kw);x=dict(name=name,entry=r);records.append(x)
        if r['result'] is not None:
            x['input']=json.loads(payload);x['check']=audit(x['input'],r['result'])
        (H/'gates.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8');return r
    for item in protocol['invalid']:
        r=call(item['name'],item['payload']);assert r['entry_status']=='invalid_input' and not r['eligible'] and not r['accepted_route']
    c=protocol['small_input'];payload=json.dumps(c)
    for budget in (0,-1):
        r=call('bad_budget_'+str(budget),payload,budget=budget);assert r['entry_status']=='invalid_input' and not r['solver_called']
    for stage in ('entry_begin','after_parse','after_solve','after_serialize'):
        class Clock:
            value=0
            def __call__(self):return self.value
        clock=Clock()
        def hook(s):
            if s==stage:clock.value=2
        r=call('outer_deadline_'+stage,payload,budget=1,clock=clock,phase_hook=hook)
        assert not r['eligible'] and not r['accepted_route']
        assert r['entry_status']==('entry_deadline_before_solve' if stage in ('entry_begin','after_parse') else 'entry_late')
        if stage in ('after_solve','after_serialize'):assert r['result']['status']=='complete'
    # A real solver-stage deadline after one actual move: preserve honest prefix.
    class Clock:
        value=0
        def __call__(self):return self.value
    clock=Clock()
    def hook(s):
        if s=='move_after':clock.value=2
    r=call('solver_interrupt_after_actual_move',payload,budget=1,clock=clock,solver_hook=hook)
    assert r['result']['status']=='deadline' and r['result']['distance']==1 and not r['eligible']
    r=call('distance_limit_zero',json.dumps(dict(c,distance_budget=0)))
    assert r['result']['status']=='resource_exceeded' and not r['eligible']
    r=call('normal_entry',payload);assert r['eligible']
    roads=[]
    for job in protocol['roads']:
        payload=Path(job['input']).read_bytes();begin=time.perf_counter();entry=invoke(payload,budget=20);wall=time.perf_counter()-begin
        c=json.loads(payload);check=audit(c,entry['result'])
        old=read(Path(job['old_result']))[job['old_index']]['result'];new=entry['result']
        same={k:v for k,v in old.items() if k!='seconds'}=={k:v for k,v in new.items() if k!='seconds'}
        x=dict(case_id=job['case_id'],input=c,entry=entry,independent_call_seconds=wall,check=check,same_except_seconds=same)
        roads.append(x);(H/'roads.json').write_text(json.dumps(roads,ensure_ascii=False,indent=2),encoding='utf-8')
        assert entry['eligible'] and wall<20 and same,(job['case_id'],entry['entry_status'],entry['result']['status'],same)
    print(json.dumps(dict(gate_calls=len(records),road_calls=len(roads),all_roads_eligible=True,max_entry_seconds=max(x['entry']['entry_seconds'] for x in roads),max_independent_call_seconds=max(x['independent_call_seconds'] for x in roads),performance_ranking_calls=0)))
if __name__=='__main__':main()
