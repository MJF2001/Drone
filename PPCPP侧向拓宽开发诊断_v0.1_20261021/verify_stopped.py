"""Verify stopped package only, without importing malformed analysis or planners."""
from common import *
import ast,sys
def verify():
    require('stat_stubs');require('seal1');seal=check_seal('seal1.json');assert sha(sys.executable)==seal['python_sha256']
    for p,h in seal['files'].items():assert sha(p)==h,p
    for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    assert not (H/'seal2.json').exists() and not (H/'actual_order.jsonl').exists() and not list((H/'outputs').glob('*')) and not list((H/'logs').glob('*'))
    assert not (H/'states.json').exists() and not (H/'groups.json').exists()
    for m in read(H/'maps.json'):
        L,w=m['L'],m['w'];c=read(H/m['input']);assert set(map(tuple,c['free']))==rect(0,0,L+8,w+8) and set(map(tuple,c['targets']))==rect(4,4,L,w) and not c['covered'] and c['current']==c['base']==[1,1] and c['predator']==[-1,0] and c['distance_budget']==1000000
    assert len(read(H/'maps.json'))==len(read(H/'prep_order.json'))==6;assert len(read(H/'stat_stub_results.json')['tests'])==8 and read(H/'stat_stub_results.json')['passed']
    for name in ('runtime.py','candidate.py','p2_adapter.py'):assert (H/'frozen_source_bytes'/name).read_bytes()==(P/name).read_bytes()
    for finding in read(H/'syntax_findings.json'):
        p=H/finding['file'];assert sha(p)==finding['sha256']
        try:ast.parse(p.read_text(encoding='utf8'))
        except SyntaxError as ex:assert ex.lineno==finding['line'] and ex.msg==finding['message']
        else:raise AssertionError('malformed original was changed')
    slots=read(H/'unrun_slots.json');assert len(slots)==306 and all(x['execution']=='NOT_RUN' for x in slots);assert collections.Counter(x['phase'] for x in slots)==dict(prep=6,gate=12,formal=288)
    with (H/'306未运行槽位.csv').open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==306
    ledger=read(H/'call_ledger.json');assert ledger['actual_true_entries']==ledger['actual_core_calls']==ledger['ordinary_graph_searches']==ledger['event_inputs']==0 and ledger['pure_statistic_stub_cases']==8;assert read(H/'STOP.json')['hypothesis_result']=='NOT_TESTED'
    assert 'SyntaxError' in (H/'prep_execution.log').read_text(encoding='utf8')
    print('PASS10242 first-seal source/environment hashes, frozen binary references, six fixed initial inputs and8 saved pure statistic stubs',flush=True)
    print('PASS original two syntax findings retained, no actual order/worker outputs/second seal/history/event states;306 unrun slots and zero real entry/core ledgers',flush=True)
    print('ALL PASS STOPPED PACKAGE ONLY; hypothesis NOT_TESTED; new planner/core/graph calls=0.',flush=True)
if __name__=='__main__':verify()
