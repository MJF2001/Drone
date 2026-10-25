"""Closed required observer schema. No arbitrary missing-key defaults."""
SCOPES=tuple('scope_'+p+'_region_queries' for p in ('engine','wrapper_prediction','wrapper_native','wrapper_post','wrapper_full'))
REQUIRED=('shared_region_queries_total',*SCOPES,'post_service_intersections','post_service_queries_total_protected',
          'observer_started','observer_finished','observer_aborted')

def validate(counts):
    assert set(REQUIRED)<=set(counts),'missing required observer fields'
    assert all(type(counts[k]) is int and counts[k]>=0 for k in REQUIRED),'invalid counter type/value'
    assert all(k in SCOPES for k in counts if k.startswith('scope_')),'unknown scope'
    assert counts['observer_started']==1 and counts['observer_finished']==1 and counts['observer_aborted']==0,'not a completed observation'
    assert counts['shared_region_queries_total']==sum(counts[k] for k in SCOPES),'scope conservation'
    assert counts['post_service_intersections']==counts['scope_engine_region_queries'],'engine equality'
    assert counts['post_service_queries_total_protected']==counts['scope_engine_region_queries']+counts['scope_wrapper_post_region_queries'],'old overall scope equality'
    assert counts['post_service_queries_total_protected']<=1200 and counts['post_service_intersections']<=1200,'unchanged cap'
    return True

def compatible(plan,source_hash):
    """Derive only demonstrated legacy omissions, retain original values and origin."""
    from copy import deepcopy
    out=deepcopy(plan);nc=out['native_counts'];original=deepcopy(nc)
    assert plan['main_passed'] and plan['stage']=='main_complete'
    assert nc['core_started']==nc['core_returned']==nc['core_complete']==1 and nc['post_entry_calls']==1
    assert plan['actual_before']==plan['actual_after']
    raw=plan['snapshot']['input'];pred=plan['predicted_entry']
    pending_before=set(map(tuple,raw['P']))&set(map(tuple,raw['F']))-set(map(tuple,raw['H']))
    pending_pred=set(map(tuple,pred['P']))&set(map(tuple,pred['F']))-set(map(tuple,pred['H']))
    additions={}
    expected_engine=plan['post']['counts']['service_intersections']
    scopes={SCOPES[0]:expected_engine}
    for phase in ('prediction','native','post','full'):
        key=phase+'_service_intersections'
        if key in plan['wrapper_counts']:v=plan['wrapper_counts'][key]
        else:
            assert not pending_before and not pending_pred,'unproven wrapper zero'
            v=0
        scopes['scope_wrapper_'+phase+'_region_queries']=v
    expected={**scopes,'shared_region_queries_total':sum(scopes.values()),'post_service_intersections':expected_engine,
              'post_service_queries_total_protected':expected_engine+scopes['scope_wrapper_post_region_queries']}
    for k,v in expected.items():
        if k in nc:assert nc[k]==v,('saved scope mismatch',k)
        else:
            assert v==0 and not pending_before and not pending_pred,'missing nonzero or unproven omission'
            nc[k]=0;additions[k]={'value':0,'evidence':'empty active responsibility before and after entry; engine service counter=0; complete wrapper audits and original normal returns'}
    for k,v in (('observer_started',1),('observer_finished',1),('observer_aborted',0)):
        if k in nc:assert nc[k]==v
        else:
            nc[k]=v;additions[k]={'value':v,'evidence':'derived legacy lifecycle: main_complete/main_passed, unchanged actual input, core started/returned/complete=1, post_entry=1; not original lifecycle trace'}
    validate(nc)
    out['counter_schema_compatibility']={'source_sha256':source_hash,'original_native_counts':original,'derived_fields':additions,
        'status':'derived_legacy_schema_not_original_trace'}
    return out
