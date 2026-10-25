"""Read-only full re-audit; never re-runs solvers."""
import sys,json,hashlib
from pathlib import Path
from collections import Counter,defaultdict
from validate_and_run import HERE,ROOT,OLD,read,verify,equivalence,auditors
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
def main():
    verify();protocol=read(HERE/'protocol.json');gate=read(HERE/'gates/verification.json');assert gate['gate']=='PASS' and gate['calls']==88
    audit,ledger,prunes=auditors();gate_rows=read(HERE/'gates/results.json')
    prior=read(ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3/evidence/results.json')
    from validate_and_run import semantic
    for index,row in enumerate(gate_rows):
        if row['kind']=='functional':
            assert semantic(row['result'])==semantic(prior[index]['result'])
            audit(prior[index]['input'],row['result'],2)
        elif row['kind']=='boundary':
            c=prior[index]['input'];ledger(c,row['result']);prunes(row['result'],row['result']['status']=='task_complete')
            assert bool(row['result']['route'])==row['label'].endswith('_before')
        else:
            j=next(j for j in protocol['jobs'] if j['name']=='large_g1_development__'+row['label'] and j['seed']==20261018)
            ref=read(ROOT/'Cstar超时归因诊断_20261019'/(row['label']+'_result.json'))
            assert semantic(row['result'])==semantic(ref);audit(read(OLD/j['input']),row['result'],20)
    out=HERE/'execution';completion=read(out/'completion.json');rows=[json.loads(x) for x in (out/'ledger.jsonl').read_text(encoding='utf8').splitlines()]
    assert len(rows)==completion['started'] and completion['unstarted']==40-len(rows)
    records=[];counts=Counter();scales=defaultdict(Counter);full_prunes=partial_prunes=0
    for j,row in zip(protocol['jobs'],rows):
        assert row['run_id']==j['run_id'];assert read(out/(j['run_id']+'.job.json'))==j
        detail=dict(run_id=j['run_id'],accepted=row['accepted'])
        if row['returncode']==0 and not row['watchdog']:
            saved=read(out/(j['run_id']+'.result.json'));assert saved['job']==j
            assert saved['input_sha256']==j['input_sha256']==digest(OLD/j['input'])
            r=saved['result'];checked=audit(read(OLD/j['input']),r,20)
            same=equivalence(j,r)
            for k,v in checked.items():assert row[k]==v,(j['run_id'],k)
            assert row['equivalence']==same and row['independent_audit']=='passed'
            assert r['protection_cache']==row['cache']
            stats=r['protection_cache'];assert stats['requests']>=stats['hits']+stats['rebuilds']
            full_prunes+=checked['completed_prunes'];partial_prunes+=checked['interrupted_prunes']
            detail.update(checked,equivalence=same,cache=stats,pending=len(r['pending']),graph_error=r['graph_error'])
        else:detail['status']='watchdog' if row['watchdog'] else 'worker_exception'
        records.append(detail);counts[detail['status']]+=1;scales[j['scale']]['accepted' if detail['accepted'] else 'not_accepted']+=1
    accepted=sum(r['accepted'] for r in records);assert completion['accepted']==accepted
    assert completion['gate']==('PASS' if len(rows)==40 and accepted==40 else 'NOT_PASSED')
    # The earlier deliveries are immutable references, not rewritten manifests.
    old_deliveries=[ROOT/'Cstar超时归因诊断_20261019',ROOT/'Cstar历史适配验收_20261019/专项验收_v0.3']
    for directory in old_deliveries:
        for name,sha in read(directory/'delivery_manifest.json')['files'].items():assert digest(directory/name)==sha
    artifacts={str(p.relative_to(HERE)):digest(p) for p in sorted(out.rglob('*')) if p.is_file()}
    print(json.dumps(dict(read_only=True,new_solver_calls=0,gates_verified=88,completion=completion,status_counts=counts,by_scale=dict(scales),completed_prunes=full_prunes,interrupted_prunes=partial_prunes,old_reference_deliveries_unchanged=True,sealed_hashes_unchanged=True,records=records,execution_sha256=artifacts),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
