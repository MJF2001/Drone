"""Read-only verification for PRE-ENTRY STOP only. No planner imports or solves."""
from probe_common import *
import sys,ast
def verify():
    seal=read(H/'preseal.json');assert seal['complete'] and sha(sys.executable)==seal['python_executable_sha256']
    for p,h in seal['files'].items():assert sha(p)==h,p
    for p,h in read(H/'manifest.json').items():assert sha(H/p)==h,p
    a=(P/'candidate.py').read_bytes();b=(H/'candidate.py').read_bytes();f=read(H/'preentry_static_failure.json');assert sha(P/'candidate.py')==f['original_sha256'] and sha(H/'candidate.py')==f['copy_sha256'];assert a!=b and a.replace(b'\r\n',b'\n')==b.replace(b'\r\n',b'\n') and ast.dump(ast.parse(a.decode('utf8')))==ast.dump(ast.parse(b.decode('utf8')))
    assert not (H/'actual_order.jsonl').exists() and not (H/'stub_results.json').exists() and not list((H/'outputs').glob('*')) and not list((H/'logs').glob('*'))
    order=read(H/'fixed_order.json');pending=read(H/'unrun_slots.json');assert len(order)==len(pending)==24 and [j['id'] for j in order]==[j['id'] for j in pending] and all(j['status']=='NOT_RUN' for j in pending)
    for case in CASES:assert sha(H/'inputs'/f'{case}.json')==sha(S/'inputs'/f'{case}.json')
    actions=read(H/'actions.json');assert set(actions)==set(CASES)
    for action in actions.values():assert action['current']==[5,2] and action['previous']==[4,2] and action['next']==[5,1]
    counts=read(H/'call_ledger.json');assert counts['real_entries']==counts['real_core_calls']==counts['stub_checks']==counts['retries']==0 and counts['unrun_entries']==24
    assert read(H/'STOP.json')['algorithm_hypothesis_verdict']=='NOT_TESTED';assert 'ALL PASS;' in (H/'upstream_verify.log').read_text(encoding='utf8')
    print('PASS all10511 pre-run source/environment hashes and stopped-package manifest; original frozen files unchanged',flush=True)
    print('PASS observed LF/CRLF mismatch, identical normalized text/AST, two exact input copies and fixed actions',flush=True)
    print('PASS 24 unrun slots, no actual order/output/logs/stubs, real entries/cores/retries=0, hypothesis NOT_TESTED',flush=True)
    print('ALL PASS FOR PRE-ENTRY STOP PACKAGE ONLY; no experiment gate or efficacy claim; planner=0, graph-distance searches=0.',flush=True)
if __name__=='__main__':verify()
