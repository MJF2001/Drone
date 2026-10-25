"""Standalone read-only stop audit; no project module or worker import."""
from pathlib import Path
import json,hashlib,ast
H=Path(__file__).resolve().parent;R=H.parent;OLD=R/'PPCPP侧向拓宽开发诊断_v0.1_20261021'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    for p,h in read(H/'old_evidence_hashes.json').items():assert sha(Path(p))==h,p
    for x in read(H/'source_manifest.json'):
        source=Path(x['source']);target=Path(x['target']);assert sha(source)==x['source_sha256'] and sha(target)==x['target_sha256']
        expected=source.read_bytes()
        if target.name in ('analysis.py','verify.py'):
            for key in ('visits_A','pp_first_A_event'):expected=expected.replace((key+"=r['"+key+"']").encode(),("'"+key+"':r['"+key+"']").encode())
        assert target.read_bytes()==expected,str(target)
    for x in read(H/'preflight/active_syntax.json')['active_files']:assert sha(Path(x['path']))==x['sha256'];ast.parse(Path(x['path']).read_text(encoding='utf8'));assert x['passed']
    blocked=read(H/'preflight/B_STATIC_BLOCK.json');assert blocked['worker_import_not_attempted'];worker=read(H/'preflight/import_static.json')['modules'][-1];assert worker['file']=='worker.py' and not worker['safe_for_dynamic_import'];targets={x['target'] for x in worker['unsafe_top_level_calls']};assert {'runtime.run_payload','p2_adapter.run_payload','sys.addaudithook'}<=targets
    assert (H/'worker.py').read_bytes()==(OLD/'worker.py').read_bytes();assert not read(H/'worker_guard_proposal.json')['applied'] and sha(H/'worker.py')==read(H/'worker_guard_proposal.json')['source_sha256']
    assert not list((H/'outputs').glob('*')) and not list((H/'logs').glob('*')) and not list((H/'receipts').glob('*'))
    for name in ('actual_order.jsonl','seal1.json','seal2.json','states.json','stat_stub_results.json'):assert not (H/name).exists(),name
    slots=read(H/'unrun_slots.json');assert len(slots)==306 and all(x['execution']=='NOT_RUN' for x in slots);assert read(H/'STOP.json')['hypothesis_result']=='NOT_TESTED';assert read(H/'call_ledger.json')['v02_actual_entries']==read(H/'call_ledger.json')['v02_actual_cores']==0
    for name,h in read(H/'manifest.json').items():assert sha(H/name)==h,name
    print('PASS old evidence hashes, exact initial/frozen binary copies, two authorized dictionary-only repairs and12 syntax records',flush=True)
    print('PASS actual worker top-level unsafe calls, dynamic import not attempted, proposal unapplied, all downstream stages/unrun306 and zero entry/core ledger',flush=True)
    print('ALL PASS V02 STATIC-IMPORT STOP PACKAGE ONLY; hypothesis NOT_TESTED; planner/core/graph calls=0.',flush=True)
if __name__=='__main__':main()
