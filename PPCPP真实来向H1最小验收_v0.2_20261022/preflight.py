"""Hand-written auditor stubs, JSON round trips, then old-result re-audit."""
from pathlib import Path
import json,copy,hashlib,traceback,sys,difflib,ast

HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'PPCPP真实来向H1最小验收_v0.1_20261022'
CASES=[
 ('tuple_tuple',True),('tuple_list',True),('list_tuple',True),('list_list',True),
 ('none_none',True),('none_coordinate',False),('coordinate_none',False),('different_coordinate',False),
 ('wrong_real_previous',False),('missing_previous_or_heading',False),('wrong_dimension_1',False),('wrong_dimension_3',False),
 ('string_container',False),('string_element',False),('bool_element',False),('float_element',False),
 ('nan_element',False),('infinite_element',False),('route_bool',False),('current_bool',False),('goal_bool',False),
 ('option_cell_bool',False),('return_previous_explicit_correct',True),('return_previous_explicit_wrong',False),
 ('return_schema_without_previous',True),('missing_goal',False),('missing_current',False),('missing_recovery_field',False),
 ('new_source_missing_or_legacy_previous_missing',False),('new_source_wrong_or_legacy_previous_wrong',False),
]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def fixture(newer, expected_type=list, actual_type=tuple, no_motion=False):
    route=[(0,0),(1,0),(2,0),(2,1),(1,1),(0,1),(0,0)]
    previous=None if no_motion else expected_type((-1,0))
    source=dict(kind='handwritten_auditor_stub') if no_motion else dict(kind='handwritten_auditor_stub',start=previous,end=expected_type((0,0)))
    heading=dict(status='NO_PRIOR_MOTION' if no_motion else 'KNOWN',vector=None if no_motion else [1,0],source=source)
    c=dict(current=expected_type((0,0)),base=expected_type((0,0)),previous=previous,
        free=[expected_type(p) for p in route[:-1]],targets=[expected_type((1,0)),expected_type((2,1))],covered=[expected_type((0,0))],predator=[-1,0],distance_budget=6)
    trace=[]
    for kind,i,goal,pending in (('local',0,(1,0),2),('recovery',1,(2,1),1),('return',3,(0,0),0)):
        row=dict(kind=kind,index=i,current=actual_type(route[i]),goal=actual_type(goal),pending_count=pending)
        if newer:
            primitive=None if i==0 and no_motion else [1,0] if i<=1 else [0,1]
            incoming_source=copy.deepcopy(source) if i==0 else dict(kind='predicted_route_edge',start=actual_type(route[i-1]),end=actual_type(route[i]),end_index=i)
            if i==0 and not no_motion:incoming_source['start']=actual_type((-1,0));incoming_source['end']=actual_type((0,0))
            row['incoming_heading']=dict(primitive=primitive,source=incoming_source)
        elif kind!='return':row['previous']=None if i==0 and no_motion else actual_type((-1,0) if i==0 else route[i-1])
        if kind=='local':row['options']=[dict(cell=actual_type((1,0)),distance_reward=0.0,straight_reward=0.0 if no_motion else 1.0,boundary_reward=1.0,score=.5 if no_motion else 2.5)]
        trace.append(row)
    raw=dict(status='core_complete',route=[actual_type(p) for p in route],trace=trace,reason=None,seed=1,weights=[2.,.5],predator=[-1,0])
    return c,heading,raw

def payload(name,newer):
    pairs={'tuple_tuple':(tuple,tuple),'tuple_list':(tuple,list),'list_tuple':(list,tuple),'list_list':(list,list)}
    expected_type,actual_type=pairs.get(name,(list,tuple));no_motion=name in ('none_none','none_coordinate')
    c,h,r=fixture(newer,expected_type,actual_type,no_motion)
    first=r['trace'][0];second=r['trace'][1];last=r['trace'][-1]
    def put(value,event=first):
        if newer:event['incoming_heading']['primitive']=value
        else:event['previous']=value
    if name=='none_coordinate':put([1,0])
    elif name=='coordinate_none':put(None)
    elif name=='different_coordinate':put([-1,0] if newer else [99,99])
    elif name=='wrong_real_previous':
        if newer:first['incoming_heading']['source']['start']=[0,-1]
        else:first['previous']=[0,-1]
    elif name=='missing_previous_or_heading':del first['incoming_heading' if newer else 'previous']
    elif name=='wrong_dimension_1':put([1])
    elif name=='wrong_dimension_3':put([1,0,0])
    elif name=='string_container':put('1,0')
    elif name=='string_element':put(['1',0] if newer else ['-1',0])
    elif name=='bool_element':put([True,0] if newer else [False,0],second)
    elif name=='float_element':put([1.0,0] if newer else [0.0,0],second)
    elif name=='nan_element':put([float('nan'),0])
    elif name=='infinite_element':put([float('inf'),0])
    elif name=='route_bool':r['route'][0]=[False,0]
    elif name=='current_bool':last['current']=[2,True]
    elif name=='goal_bool':last['goal']=[False,0]
    elif name=='option_cell_bool':first['options'][0]['cell']=[True,0]
    elif name=='return_previous_explicit_correct':
        if not newer:last['previous']=actual_type((2,0))
    elif name=='return_previous_explicit_wrong':
        if newer:last['incoming_heading']['source']['start']=[1,0]
        else:last['previous']=[1,0]
    elif name=='missing_goal':del second['goal']
    elif name=='missing_current':del last['current']
    elif name=='missing_recovery_field':
        if newer:del second['incoming_heading']['primitive']
        else:del second['previous']
    elif name=='new_source_missing_or_legacy_previous_missing':
        if newer:del second['incoming_heading']['source']['start']
        else:del second['previous']
    elif name=='new_source_wrong_or_legacy_previous_wrong':
        if newer:second['incoming_heading']['source']['end']=[9,9]
        else:second['previous']=[9,9]
    return c,h,r

def register():
    assert not (HERE/'修复预检事前登记.json').exists()
    dump(HERE/'修复预检事前登记.json',dict(cases=[dict(id=n,should_accept=b) for n,b in CASES],branches=['legacy_previous','H1_heading_source'],
        representations=['runtime','JSON_roundtrip'],expected_audit_calls=len(CASES)*4,expected_equivalence_checks=4,
        handcrafted_route_fixture='fixed 6 edges, local/recovery/return; no solver',max_technical_rounds=3,
        saved_result_audits_after_pure_pass=2,production_calls=0))

def test():
    prereg=read(HERE/'修复预检事前登记.json');assert len(prereg['cases'])==len(CASES)
    round_no=len(list((HERE/'repair_rounds').glob('round_*_result.json')))+1;assert round_no<=3
    snapshot={name:sha(HERE/name) for name in ('independent_audit.py','preflight.py','worker.py')}
    for name in snapshot:(HERE/'repair_rounds'/f'round_{round_no}_{name}').write_bytes((HERE/name).read_bytes())
    old=(OLD/'independent_audit.py').read_text(encoding='utf8');new=(HERE/'independent_audit.py').read_text(encoding='utf8')
    (HERE/'repair_rounds'/f'round_{round_no}_auditor.diff').write_text(''.join(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='v0.1/independent_audit.py',tofile='v0.2/independent_audit.py')),encoding='utf8')
    rows=[];failures=[];equivalence_rows=[]
    from independent_audit import audit_output,equivalence
    for name,accept in CASES:
        for newer in (False,True):
            values=payload(name,newer);outputs=[]
            for representation in ('runtime','JSON_roundtrip'):
                # NaN/Infinity are explicit negative-parser controls only.
                data=copy.deepcopy(values) if representation=='runtime' else json.loads(json.dumps(values,allow_nan=True))
                try:
                    out=audit_output(*data,newer);observed=True;reason=None
                except (AssertionError,KeyError,TypeError,ValueError) as ex:out=None;observed=False;reason=repr(ex)
                passed=observed==accept;row=dict(case=name,newer=newer,representation=representation,expected_accept=accept,accepted=observed,passed=passed,reason=reason)
                rows.append(row);outputs.append(out)
                if not passed:failures.append(row)
            if accept and outputs[0]!=outputs[1]:failures.append(dict(case=name,reason='runtime_JSON_audit_result_differs'))
    c,h,a=fixture(False);_,_,b=fixture(True)
    scenarios=[('coordinate_runtime_JSON',True),('missing_current_both',False),('missing_raw_route',False),('bad_option_cell',False)]
    for name,accept in scenarios:
        left=copy.deepcopy(a);right=json.loads(json.dumps(b))
        if name=='missing_current_both':del left['trace'][0]['current'];del right['trace'][0]['current']
        elif name=='missing_raw_route':del right['route']
        elif name=='bad_option_cell':right['trace'][0]['options'][0]['cell']=[True,0]
        try:equivalence(left,right);observed=True;reason=None
        except (AssertionError,KeyError,TypeError,ValueError) as ex:observed=False;reason=repr(ex)
        row=dict(case=name,expected_accept=accept,accepted=observed,passed=accept==observed,reason=reason);equivalence_rows.append(row)
        if not row['passed']:failures.append(row)
    result=dict(round=round_no,passed=not failures,source_hashes=snapshot,rows=rows,equivalence_rows=equivalence_rows,failures=failures,
        auditor_calls=len(rows),accepted=sum(x['accepted'] for x in rows),expected_rejections=sum(not x['accepted'] for x in rows),
        real_entries=0,core_calls=0,graph_searches=0,LOS_queries=0,handwritten_stub_routes=1,algorithm_generated_routes=0)
    dump(HERE/'repair_rounds'/f'round_{round_no}_result.json',result)
    print(json.dumps(dict(round=round_no,passed=result['passed'],auditor_calls=len(rows),accepted=result['accepted'],rejected=result['expected_rejections'],failures=failures),ensure_ascii=False))
    if failures:raise SystemExit(1)

def recheck_saved():
    rounds=[read(p) for p in sorted((HERE/'repair_rounds').glob('round_*_result.json'))];assert rounds and rounds[-1]['passed']
    assert not (HERE/'reuse/slot_001_reaudit.json').exists(),'no repeated stage-B saved audits'
    from independent_audit import audit_output
    source=OLD/'outputs/legacy__large_I_corner_p30__ORIGINAL.json';old=read(source)
    assert old['passed'] is False and old['entry']['eligible'] and old['entry']['raw']['branches']['P0']['status']=='core_complete'
    audits=[]
    for label in ('saved_JSON_arrays','equal_coordinate_tuple_payload'):
        c=copy.deepcopy(old['input']);h=copy.deepcopy(old['job']['heading']);raw=copy.deepcopy(old['entry']['raw']['branches']['P0'])
        if label=='equal_coordinate_tuple_payload':
            for field in ('current','base','previous'):c[field]=tuple(c[field]) if c[field] is not None else None
            for field in ('free','targets','covered'):c[field]=[tuple(p) for p in c[field]]
            raw['route']=[tuple(p) for p in raw['route']]
            for event in raw['trace']:
                for field in ('current','goal','previous'):
                    if field in event and event[field] is not None:event[field]=tuple(event[field])
                for row in event.get('options',[]):row['cell']=tuple(row['cell'])
        audit=audit_output(c,h,raw,False);audits.append(dict(representation=label,audit=audit))
    assert audits[0]['audit']==audits[1]['audit']
    dump(HERE/'reuse/slot_001_reaudit.json',dict(source_path=str(source),source_sha256=sha(source),old_slot=1,old_status='failed',old_failure=old['failure'],
        new_status='reused_existing_original_return_reaudited',audits=audits,reused_entry_seconds=old['entry']['entry_seconds'],
        old_graph_accounts=old['accounts'],new_entries=0,new_core_calls=0,new_graph_searches=0,new_saved_route_audits=2,
        not_full_runtime_type_reconstruction=True))
    print(json.dumps(dict(reused_slot1=True,old_status='failed',saved_route_audits=2,new_entries=0),ensure_ascii=False))

if __name__=='__main__':
    if sys.argv[1]=='register':register()
    elif sys.argv[1]=='test':test()
    elif sys.argv[1]=='recheck':recheck_saved()
