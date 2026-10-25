"""Saved evidence only; never calls a callback, worker or solver."""
from util import *
from real_audit import inspect_session
def main():
    cfg=config();check_seal();require('real');a=read(H/'acceptance.json');order=read(H/'session_order.json');counter={'BFS':0}
    synthetic=H.name=='SYNTHETIC_TECHNICAL_NOT_REAL'
    assert len(order)==(2 if synthetic else 6)
    sessions=[json.loads(x) for x in (H/'actual_sessions.jsonl').read_text(encoding='utf8').splitlines()];assert sessions==order
    attempts=[json.loads(x) for x in (H/'actual_attempts.jsonl').read_text(encoding='utf8').splitlines()];assert len(attempts)<=cfg['real_entry_cap']
    proofs=[inspect_session(s,counter) for s in order];assert proofs==a['proofs'] and counter['BFS']==a['independent_audit_BFS'] and a['interface_pass']==all(p['passed'] for p in proofs)
    requested=[r['id'] for p in proofs for r in p['static_dual_metrics']];assert requested==[r['id'] for r in attempts]
    assert all(v['sequence']==i+1 for i,v in enumerate(attempts))
    markers={'entries':0,'core_starts':0,'core_returns':0,'entry_returns':0}
    for row in attempts:
        q=read(H/'logs'/(row['id']+'.receipt.json'));raw=(H/'logs'/(row['id']+'.txt')).read_bytes()
        observed=dict(entries=raw.count(b'ENTRY_START '),core_starts=raw.count(b'CORE_START '),core_returns=raw.count(b'CORE_RETURN'),entry_returns=raw.count(b'ENTRY_RETURN '))
        assert q['markers']==observed
        for k,v in observed.items():markers[k]+=v
    assert markers==dict.fromkeys(markers,len(attempts))
    if not synthetic:
        for c in read(H/'copy_manifest.json'):
            assert sha(c['source'])==c['source_sha256'] and sha(H/c['target'])==c['target_sha256']
        assert len((H/'technical_stub_journal.jsonl').read_text(encoding='utf8').splitlines())<=24
        if (H/'completion_manifest.json').exists():
            for p,v in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==v,p
    print(json.dumps(dict(saved_evidence_pass=True,interface_pass=a['interface_pass'],sessions=len(order),attempts=len(attempts),markers=markers,ordinary_BFS_this_verify=counter['BFS'],new_real_entries=0,new_stub_responses=0,no_ranking=True),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
