"""Fixed pure gates, no real solve/post/search. Preserve every attempted case."""
from collections import Counter
from fractions import Fraction as Q
from copy import deepcopy
from pathlib import Path
import ast,json,sys,traceback
from .utils import HERE,read,dump,sha,now,evidence
from .pipeline import grid,native_points,PipelineStop
from .executor import Executor
from .context import prepare_context,stable_context
from .public_contract import parse,select,state_save
from .service import collect,credit_move
from .exact import pt
from .audit.pure import audit_entry,audit_forecast

def guard(frame,event,arg):
    if event=='call' and frame.f_code.co_name in ('run_payload','solve','process','core_route'):
        raise RuntimeError('pure_gate_forbids_algorithm_entry')
    return guard

def entry_prediction(ex):
    c=Counter();raw=ex.public_case('pure_entry')
    s=parse(raw['input'],c);before=state_save(s)
    selected,rows=select(s,c);q=selected[0];length=selected[3]
    f=deepcopy(s)
    events=collect(f,c,'pure_prediction')+credit_move(f,s['S'],q,c,'pure_prediction')
    f['h']=tuple(q[k]-s['S'][k] for k in (0,1)) if q!=s['S'] else s['h']
    f['S'],f['E'],f['M']=q,s['E']-length,s['M']+length
    return {'input':raw,'q':grid(q),'candidates':rows,'events':events,'prediction':state_save(f),
            'actual_before':before,'actual_after':state_save(s),'counts':dict(c)}

def preparation(binding):
    for p in HERE.rglob('*.py'):
        tree=ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
        # Any task main is guarded or invoked explicitly by the root dispatcher.
        for node in tree.body:
            if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call):
                assert not(isinstance(node.value.func,ast.Name) and node.value.func.id=='main'),str(p)
    assert grid((Q(1),Q(2)))==grid([Q(1),Q(2)])==[1,2]
    assert native_points(((0,0),[1,0]))==native_points([[0,0],[1,0]])
    refusals=0
    for func,arg in ((grid,(Q(1,2),Q(0))),(native_points,[(Q(0),0)]),(native_points,[(True,0)])):
        try:
            func(arg)
        except PipelineStop:
            refusals+=1
    assert refusals==3
    return {'syntax_and_guards':True,'tuple_list_and_fraction_boundary':True,'identity':binding.assert_stable(),
            'single_seal_writer':'seal command only','core_calls':0,'post_calls':0,'graph_search_calls':0}

def main(round_id):
    reg=read(HERE/'registration.json')
    assert round_id in (1,2) and not (HERE/'real_started.json').exists()
    dest=HERE/'technical_rounds'/('round_'+str(round_id))
    assert not dest.exists();dest.mkdir()
    requested=list(reg['technical_fixtures'])
    used=0
    if round_id==2:
        previous=read(HERE/'technical_rounds/round_1/receipt.json')
        assert not previous['passed']
        used=len(previous['sessions'])
        accepted={s['id'] for s in previous['sessions'] if s['passed']}
        requested=[case for case in requested if case['id'] not in accepted]
        assert used+len(requested)<=48,'pure cap: stop rather than repeat whole batch'
    result={'round':round_id,'utc':now(),'passed':False,'sessions':[],
            'core_calls':0,'post_calls':0,'graph_search_calls':0}
    total=Counter()
    dump(dest/'source_hashes.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*.py')})
    try:
        files_before={str(p) for p in HERE.rglob('*') if p.is_file()}
        h1,p2,engine,binding,cold,loaded,identity=prepare_context()
        assert files_before=={str(p) for p in HERE.rglob('*') if p.is_file()},'import wrote results'
        result.update(cold=cold,loaded_sources=loaded,identity=identity)
        dump(dest/'preparation.json',preparation(binding))
        sys.settrace(guard)
        pairs={}
        for case in requested:
            assert len(case['actions'])<=8
            item={'id':case['id'],'case':case,'passed':False}
            ex=Executor(case['public'],case['private'],initial=case['initial'],technical=True)
            item['initial']=ex.initial
            independent=Counter()
            try:
                statuses=[];history=[]
                for action in case['actions']:
                    kind=action['kind']
                    if kind=='entry_prediction':
                        predicted=entry_prediction(ex)
                        assert predicted['q']==case['expected_q']
                        assert predicted['prediction']['H']==[[1,1]] and ex.snapshot()['H']==[]
                        item['entry_prediction']=predicted
                        item['independent_entry']=audit_entry(predicted,independent)
                        total.update(predicted['counts'])
                        statuses.append('prediction_only')
                    elif kind=='publish':
                        statuses.append(ex.publish(action['P'],action['blocked'])['status'])
                    elif kind=='plan_wait':
                        # Fixed prediction has its own region witnesses; waiting cannot commit them.
                        f=deepcopy(ex.s)
                        forecast=collect(f,ex.counts,'pure_forecast')
                        for a,b in zip(action['route'],action['route'][1:]):
                            from .exact import point
                            forecast+=credit_move(f,point(a),point(b),ex.counts,'pure_forecast')
                        item['fixed_forecast']={'route':action['route'],'events':forecast,'H':sorted([list(map(int,p)) for p in f['H']])}
                        assert item['fixed_forecast']['H']==[[1,1]]
                        item['independent_forecast']=audit_forecast(ex.initial,item['fixed_forecast'],independent)
                        ex.wait_plan('fixed_'+case['id'],action['route'],'handwritten_fixed_prediction',True)
                        statuses.append('plan_wait')
                    else:
                        statuses.append(ex.action(kind,action.get('to'),action.get('before_event',False))['status'])
                    history.append(ex.snapshot()['H'])
                saved=ex.snapshot()
                assert saved['H']==case['expect']['H'],(saved['H'],case['expect']['H'])
                for field,target in (('expected_D','D'),('expected_h','h')):
                    if field in case:
                        assert saved[target]==case[field]
                if 'expected_history' in case:
                    assert history==case['expected_history']
                if 'expected_statuses' in case:
                    assert statuses==case['expected_statuses']
                credits=[credit for row in ex.records for credit in row.get('credits',[])]
                if 'expected_credits' in case:
                    assert len(credits)==case['expected_credits']
                if 'expect_interval' in case:
                    assert credits[0]['evidence']['interval']==case['expect_interval']
                if 'expected_M' in case:
                    A=binding.package._audit.A
                    assert A.load(saved['M']['exact'])==A.load(case['expected_M'])
                if case.get('expected_return'):
                    assert ex.completed()
                if case.get('old_center_difference'):
                    assert credits and all(c['kind']=='region_traverse' for c in credits)
                    a,b=ex.s['S'],ex.s['S']
                    from .exact import point
                    a,b=map(point,next(row for row in ex.records if row['kind']=='move')['actual'])
                    for c in credits:
                        target=tuple(c['cell']);dx,dy=b[0]-a[0],b[1]-a[1]
                        assert dx*(target[1]-a[1])!=dy*(target[0]-a[0]),'old-center positive control must miss center'
                item['independent']=binding.package.audit_execution(case['public'],case['private'],ex.initial,
                                     ex.records,saved,technical=True,counts=independent)
                if 'segmentation_pair' in case:
                    pairs[case['segmentation_pair']]={'H':saved['H'],'M':saved['M']['exact']}
                if 'negative_controls' in case:
                    item['negative_controls']=[]
                    for kind in case['negative_controls']:
                        mutated=deepcopy(ex.records);wrong_final=deepcopy(saved)
                        if kind=='witness_point':
                            mutated[0]['credits'][0]['evidence']['witness']['point'][0]={'n':999,'d':1}
                            # Rechain to ensure the analytic witness check, not just hash integrity, rejects it.
                            from .executor import digest
                            previous='0'*64
                            for record in mutated:
                                record['previous_hash']=previous
                                raw={k:v for k,v in record.items() if k!='record_hash'}
                                record['record_hash']=digest(raw);previous=record['record_hash']
                        else:
                            wrong_final['H'].append([3,1])
                        rejected=False;nc=Counter()
                        try:
                            binding.package.audit_execution(case['public'],case['private'],ex.initial,mutated,wrong_final,technical=True,counts=nc)
                        except AssertionError:
                            rejected=True
                        assert rejected,'negative audit control accepted'
                        item['negative_controls'].append({'kind':kind,'records':mutated,'final':wrong_final,'rejected':True,'counts':dict(nc)})
                        total.update(nc)
                item['passed']=True
            except BaseException as error:
                item['failure']={'reason':repr(error),'traceback':traceback.format_exc()}
            item.update(records=ex.records,final=ex.snapshot(),main_counts=dict(ex.counts),independent_counts=dict(independent))
            # Preserve a round-trip load exactly as future saved-only verify will see it.
            dump(dest/(case['id']+'.json'),evidence(item))
            assert read(dest/(case['id']+'.json'))==evidence(item)
            total.update(ex.counts);total.update(independent)
            result['sessions'].append({'id':case['id'],'passed':item['passed']})
            if not item['passed']:
                raise RuntimeError('fixed_pure_gate_failed_'+case['id'])
        sys.settrace(None)
        if pairs:
            assert pairs['whole']==pairs['split'],'segmentation changes H or exact distance'
        result['identity_after']=stable_context(binding,identity)
        limits=reg['all_pure_caps']
        assert used+len(result['sessions'])<=48
        assert total['candidate_checks']<=limits['main_candidates']
        assert total['safety_box_queries']+total['detector_box_queries']<=limits['main_boxes']
        assert total['independent_safety_box_queries']+total['independent_detector_box_queries']<=limits['independent_boxes']
        assert total['execution_truth_geometry']+total['candidate_geometry']+total['input_geometry']<=limits['main_geometry']
        assert total['independent_geometry']<=limits['independent_geometry']
        assert sum(v for k,v in total.items() if k.endswith('_service_intersections') and not k.startswith('independent'))<=limits['main_service']
        assert total['independent_service_intersections']<=limits['independent_service']
        result['passed']=True
    except BaseException as error:
        sys.settrace(None)
        result['failure']={'reason':repr(error),'traceback':traceback.format_exc()}
    result.update(finished_utc=now(),counts=dict(total))
    dump(dest/'receipt.json',evidence(result))
    print(json.dumps({'round':round_id,'passed':result['passed'],'cases':result['sessions'],'counts':dict(total),'failure':result.get('failure')},ensure_ascii=False))
    if not result['passed']:
        raise SystemExit(1)
