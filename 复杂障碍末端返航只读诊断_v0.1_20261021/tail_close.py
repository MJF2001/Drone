"""Seal the actual verification receipt after verification completes."""
from tail_analysis import H,read,sha,save
if __name__=='__main__':
    data=(H/'verify.log').read_bytes();log=data.decode('utf-16' if data.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    assert 'ALL PASS' in log and read(H/'call_ledger.json')['new_planner_calls']==0
    save(H/'verification_receipt_manifest.json',{name:sha(H/name) for name in ('manifest.json','verify.log','call_ledger.json')})
    print('Actual verification log and distance execution receipt sealed; no metric or distance recomputation.')
