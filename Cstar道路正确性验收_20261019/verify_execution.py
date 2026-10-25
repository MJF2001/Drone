"""Read-only re-audit of the sealed batch; zero additional solver calls."""
import json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from run import verify,read,HERE,ROOT,sha
from audit_outputs import audit
def main():
    protocol=verify();out=HERE/'execution';completion=read(out/'completion.json')
    rows=[json.loads(line) for line in (out/'ledger.jsonl').read_text(encoding='utf8').splitlines() if line.strip()]
    assert len(rows)==completion['started'] and completion['unstarted']==40-len(rows)
    rechecks=[];by_scale=defaultdict(Counter);by_state=defaultdict(Counter);statuses=Counter();consecutive=0
    full_prunes=partial_prunes=total_pending=0
    for i,row in enumerate(rows):
        job=protocol['jobs'][i];name=job['run_id'];assert row['run_id']==name
        assert read(out/(name+'.job.json'))==job
        c=read(HERE/job['input']);assert sha(HERE/job['input'])==job['input_sha256']
        technical=row['watchdog'] or row['returncode']!=0
        consecutive=consecutive+1 if technical else 0
        if i<len(rows)-1:assert consecutive<2,'batch continued past stop rule'
        if not technical:
            saved=read(out/(name+'.result.json'));assert saved['job']==job and saved['input_sha256']==job['input_sha256']
            r=saved['result']
            try:
                checked=audit(c,r,job['budget_seconds']);assert row.get('independent_audit')=='passed'
                for k,v in checked.items():assert row[k]==v,(name,k)
                full_prunes+=checked['completed_prunes'];partial_prunes+=checked['interrupted_prunes']
                total_pending+=len(r['pending'])
                detail=dict(run_id=name,**checked,pending=len(r['pending']),graph_status=r['graph_status'],graph_error=r['graph_error'],iterations=len(r['iterations']),task_transit=sum(it['why']['group']=='task_transit' for it in r['iterations']))
            except Exception:
                if row.get('independent_audit')!='failed':raise
                assert not row['accepted'];detail=dict(run_id=name,accepted=False,status='independent_audit_failed',traceback=row.get('audit_error'))
        else:
            assert not row['accepted'];detail=dict(run_id=name,accepted=False,status='watchdog' if row['watchdog'] else 'worker_exception')
        rechecks.append(detail);category='accepted' if detail['accepted'] else 'not_accepted'
        by_scale[job['scale']][category]+=1;by_state[job['state']][category]+=1;statuses[detail['status']]+=1
    assert sum(r['accepted'] for r in rechecks)==completion['accepted']
    expected_gate='PASS' if len(rows)==40 and all(r['accepted'] for r in rechecks) else 'NOT_PASSED'
    assert completion['gate']==expected_gate and not completion['ranking'] and not completion['holdout_used']
    if completion['aborted']:assert consecutive>=2 and len(rows)<40
    else:assert len(rows)==40
    artifacts={str(p.relative_to(HERE)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    print(json.dumps(dict(read_only=True,new_solver_calls=0,completion=completion,status_counts=statuses,by_scale=dict(by_scale),by_state=dict(by_state),full_prunes_checked=full_prunes,partial_prunes_retained=partial_prunes,all_sealed_hashes_unchanged=True,records=rechecks,artifact_sha256=artifacts),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
