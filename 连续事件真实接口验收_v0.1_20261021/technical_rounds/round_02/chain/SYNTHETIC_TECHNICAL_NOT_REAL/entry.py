"""Additional mandatory serialization/normalization stays inside total20s.
The existing frozen warm entry receives only the unspent shared budget.
"""
import json,time
def invoke(payload,method,seed,api,geometry=None,clock=time.perf_counter):
    begin=clock();snapshot=json.loads(payload);native_payload=json.dumps(snapshot,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf8')
    preprocess=clock()-begin;remaining=20-preprocess
    if remaining<=0:
        native=None;response=dict(route=[],native_status='deadline',source='original_native',entry_seconds=clock()-begin)
        return dict(native_return=native,response=response,entry_seconds=response['entry_seconds'],preprocess_seconds=preprocess,inner_budget=0,entry_budget=20,native_payload_utf8=native_payload.decode())
    if method=='PPCPP':native=api['runtime'].run_payload(native_payload,'PPCPP',remaining,seed,geometry=geometry)
    else:
        assert method=='P2_MULTI';native=api['p2'].run_payload(native_payload,remaining,seed)
    # Normalize exact returned values, including route tuples, by full JSON
    # encoding/decoding inside the common entry. Native raw/trace is preserved.
    wire=json.dumps(native,ensure_ascii=False,separators=(',',':'),allow_nan=False);native=json.loads(wire)
    response=dict(route=native['raw'].get('route',[]),native_status=native['raw']['status'],source='original_native',entry_seconds=0.)
    json.dumps(dict(native_return=native,response=response),ensure_ascii=False,separators=(',',':'),allow_nan=False)
    elapsed=clock()-begin;response['entry_seconds']=elapsed
    return dict(native_return=native,response=response,entry_seconds=elapsed,preprocess_seconds=preprocess,inner_budget=remaining,entry_budget=20,native_payload_utf8=native_payload.decode('utf8'))
