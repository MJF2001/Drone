"""One bounded round, 12 fixed sessions; identical pre-core context to worker."""
from collections import Counter
from fractions import Fraction as Q
from copy import deepcopy
import json,sys,traceback
from loop_utils import HERE,read,dump,sha,now,evidence
from pipeline import grid,native_points,PipelineStop
from executor import Executor
from context import prepare_context,stable_context

def guard(frame,event,arg):
    if event=='call' and frame.f_code.co_name in ('run_payload','solve','process','core_route'):
        raise RuntimeError('algorithm_entry_forbidden_in_pure_gate')
    return guard

def probe_contract(ex):
    from public_contract import parse,select,heading
    from h1_direction import parse_heading
    from exact import pt
    c=Counter()
    initial=Executor({'F_nominal':[[x,y] for x in range(5) for y in range(3)],'P':[],
                     'start':[0,0],'base':[0,0],'E':100},{'O_truth':[[2,1]]})
    receipts=[]
    for obj in (initial,ex):
        case=obj.public_case('pure_contract')
        s=parse(case['input'],c)
        winner,rows=select(s,c)
        q,_,_,_=winner
        pred=deepcopy(s)
        pred['S']=q
        pred['h']=tuple(q[k]-s['S'][k] for k in (0,1)) if q!=s['S'] else s['h']
        hh=heading(pred,s,case,'fixed_pure_gate')
        parsed=parse_heading(hh,grid(q))
        assert parsed['status']==('NO_PRIOR_MOTION' if obj is initial else 'KNOWN')
        assert grid(q)==([0,0] if obj is initial else [1,1])
        receipts.append({'q':grid(q),'heading':hh,'rows':rows})
    assert grid((Q(1),Q(2)))==[1,2]
    assert grid([Q(1),Q(2)])==[1,2]
    assert native_points(((0,0),[1,0]))==[(Q(0),Q(0)),(Q(1),Q(0))]
    refused=0
    for func,arg in ((grid,(Q(1,2),Q(0))),(native_points,[(Q(0),0)]),(native_points,[(True,0)])):
        try:
            func(arg)
        except PipelineStop:
            refused+=1
    assert refused==3
    return {'counts':dict(c),'receipts':receipts,'type_boundary_guards_passed':True}

def main(round_id):
    reg=read(HERE/'registration.json')
    assert round_id in (1,2)
    dest=HERE/'technical_rounds'/('round_'+str(round_id))
    assert not dest.exists(),'never overwrite a technical round'
    if round_id==2:
        assert (HERE/'technical_rounds/round_1/receipt.json').exists()
        assert not read(HERE/'technical_rounds/round_1/receipt.json')['passed']
    assert not (HERE/'real_started.json').exists()
    dest.mkdir()
    dump(dest/'source_hashes.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*.py')})
    result={'started_utc':now(),'round':round_id,'passed':False,'sessions':[],
            'true_core_calls':0,'post_calls':0,'graph_search_calls':0}
    total=Counter()
    try:
        h1,p2,engine,binding,cold,loaded,identity=prepare_context()
        result.update(cold=cold,identity=identity,loaded_sources=loaded)
        sys.settrace(guard)
        A=binding.package._audit.A
        for case in reg['technical_fixtures']:
            item={'id':case['id'],'passed':False,'case':case}
            ex=Executor(case['public'],case['private'],initial=case['initial'])
            item['initial']=ex.initial
            try:
                statuses=[]
                for action in case['actions']:
                    if action['kind']=='plan_wait':
                        ex.wait_plan('fixed_'+case['id'],action['route'],'fixed_handwritten_response',True)
                        statuses.append('plan_wait')
                    else:
                        statuses.append(ex.action(action['kind'],action.get('to'))['status'])
                expected=case['expect']
                assert statuses==expected['statuses'],(statuses,expected['statuses'])
                saved=ex.snapshot()
                for k in ('S','H','known','h','event_count'):
                    if k in expected:
                        assert saved[k]==expected[k],(k,saved[k],expected[k])
                for k in ('E','M'):
                    if k in expected:
                        assert A.load(saved[k]['exact'])==A.load(expected[k]),k
                if 'detected_t' in expected:
                    assert next(r for r in ex.records if r.get('status')=='detected')['sensor']['t']==expected['detected_t']
                if 'completed' in expected:
                    assert ex.completed()==expected['completed']
                item['independent']=binding.package.audit_execution(case['public'],case['private'],ex.initial,
                                             ex.records,saved,technical=True)
                if case.get('contract_probe'):
                    item['contract_probe']=probe_contract(ex)
                    cc=item['contract_probe']['counts']
                    assert cc['candidate_checks']<=25
                    assert sum(v for k,v in cc.items() if k.endswith('_geometry'))<=26
                item['passed']=True
            except BaseException as error:
                item['failure']={'reason':repr(error),'traceback':traceback.format_exc()}
            item.update(records=ex.records,final=ex.snapshot(),main_counts=dict(ex.counts))
            dump(dest/(case['id']+'.json'),evidence(item))
            result['sessions'].append({'id':case['id'],'passed':item['passed']})
            total.update(ex.counts)
            total.update(item.get('independent',{}).get('counts',{}))
            if not item['passed']:
                raise RuntimeError('fixed_gate_failed_'+case['id'])
        sys.settrace(None)
        result['identity_after']=stable_context(binding,identity)
        assert len(result['sessions'])==12
        limits=reg['per_technical_round_caps']
        assert total['detector_box_queries']+total['safety_box_queries']<=limits['main_boxes']
        assert total['independent_detector_box_queries']+total['independent_safety_box_queries']<=limits['independent_boxes']
        assert total['execution_truth_geometry']<=limits['main_truth_geometry']
        assert total['independent_geometry']<=limits['independent_truth_geometry']
        assert total['execution_service_intersections']<=limits['main_service']
        assert total['independent_service_intersections']<=limits['independent_service']
        result['passed']=True
    except BaseException as error:
        sys.settrace(None)
        result['failure']={'reason':repr(error),'traceback':traceback.format_exc()}
    result.update(finished_utc=now(),counts=dict(total))
    dump(dest/'receipt.json',evidence(result))
    print(json.dumps({'round':round_id,'passed':result['passed'],'sessions':result['sessions'],'failure':result.get('failure'),'counts':dict(total)},ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)

if __name__=='__main__':
    main(int(sys.argv[1]))
