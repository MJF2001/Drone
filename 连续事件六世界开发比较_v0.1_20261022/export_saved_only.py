"""Document export repair only, after all real sessions stopped.
Preserve bound deliver.py; fix only duplicate metadata keyword in its ledger.
No solver, simulation, graph call or execution-chain edits are allowed.
"""
from util import *
import inspect,sys,difflib
def main():
    assert (H/'acceptance.json').exists() and not (H/'通俗报告与完整结果.md').exists()
    before=sha(H/'actual_attempts.jsonl');source_hash=sha(H/'deliver.py');calls=[]
    def forbid(frame,event,arg):
        if event=='call' and frame.f_code.co_name in ('solve','run_payload','run_world','invoke','reach','walk_component','run_session','inspect_session'):calls.append(frame.f_code.co_name);raise AssertionError('forbidden new execution/search during document repair')
    sys.setprofile(forbid)
    import deliver
    a=inspect.getsource(deliver.ledger);b=a.replace('dict(round=p.parent.name,**read(p))','dict(round_directory=p.parent.name,**read(p))');assert a!=b
    put(H/'交付纯汇总修复.diff',''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='bound deliver.ledger',tofile='saved-only export ledger')).encode('utf8'))
    exec(compile(b,str(Path(__file__).resolve())+'::ledger_metadata_only','exec'),deliver.__dict__);deliver.main();sys.setprofile(None)
    assert not calls and before==sha(H/'actual_attempts.jsonl') and source_hash==sha(H/'deliver.py')
    save(H/'交付纯汇总修复记录.json',dict(passed=True,reason='Duplicate round keyword from existing round metadata; rename additional directory label to round_directory',original_failure_log='delivery_execution.log',bound_deliver_unchanged=source_hash,actual_attempt_journal_unchanged=before,new_real_entries=0,new_stub_responses=0,new_graph_searches=0,no_execution_chain_edits=True,new_source='export_saved_only.py',stopped=True))
if __name__=='__main__':main()
