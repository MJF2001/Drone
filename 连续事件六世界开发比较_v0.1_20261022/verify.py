"""Read saved evidence and independent BFS only; never execute methods again."""
from util import *
from real_audit import inspect_session
from analysis import collect
def main():
    cfg=config();check_seal();require('real');a=read(H/'acceptance.json');order=read(H/'session_order.json');assert len(order)==12 and len(read(H/'worlds.json'))==6 and len(read(H/'call_slots.json'))==36
    actual=[json.loads(x) for x in (H/'actual_sessions.jsonl').read_text(encoding='utf8').splitlines()];assert actual==order
    attempts=[json.loads(x) for x in (H/'actual_attempts.jsonl').read_text(encoding='utf8').splitlines()];assert len(attempts)<=36 and all(r['sequence']==i+1 for i,r in enumerate(attempts))
    counter={'BFS':0};proofs=[inspect_session(s,counter) for s in order];assert proofs==a['proofs'] and counter['BFS']==a['independent_audit_BFS']
    requested=[v['id'] for p in proofs for v in p['static_dual_metrics']];assert requested==[v['id'] for v in attempts]
    markers=dict(entries=0,core_starts=0,core_returns=0,entry_returns=0)
    for row in attempts:
        rid=row['id'];q=read(H/'logs'/(rid+'.receipt.json'));b=(H/'logs'/(rid+'.txt')).read_bytes();observed=dict(entries=b.count(b'ENTRY_START '),core_starts=b.count(b'CORE_START '),core_returns=b.count(b'CORE_RETURN'),entry_returns=b.count(b'ENTRY_RETURN '));assert observed==q['markers']
        for k,v in observed.items():markers[k]+=v
    assert markers==dict.fromkeys(markers,len(attempts))
    for c in read(H/'copy_manifest.json'):assert sha(c['source'])==c['source_sha256'] and sha(H/c['name'])==c['target_sha256']
    z=collect();assert z==read(H/'完整开发分析.json');assert sum(z['views']['statuses_per_method']['PPCPP'].values())==sum(z['views']['statuses_per_method']['P2_MULTI'].values())==6
    assert len(z['slots'])==36 and all(s['attempt'] or s['unused_reason'] for s in z['slots'])
    for wid in read(H/'worlds.json'):assert (H/'figures'/(wid+'.png')).is_file() and (H/'figures'/(wid+'.svg')).is_file()
    if (H/'completion_manifest.json').exists():
        for p,v in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==v,p
    print(json.dumps(dict(saved_evidence_pass=True,development_batch_complete=True,sessions=len(order),real_entries=len(attempts),markers=markers,ordinary_BFS_this_verify=counter['BFS'],both_success_pairs=z['views']['both_success']['denominator'],same_H_D_pairs=z['views']['same_final_H_D']['denominator'],new_real_entries=0,new_stub_responses=0),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
