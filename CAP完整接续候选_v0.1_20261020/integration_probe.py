"""Additional branch gate: roads did not exercise runtime graph split.
Pre-register exact geometry before execution; no policy changes or ranking.
"""
import json,sys,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H/'runtime'))
from candidate import solve
from audit import audit
def main():
    p=json.loads((H/'integration_protocol.json').read_text(encoding='utf-8'))
    for f,h in p['files'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
    out=[]
    for item in p['cases']:
        c=item['input'];r=solve(c);entry=dict(name=item['name'],input=c,result=r)
        out.append(entry);(H/'integration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        entry['check']=audit(c,r);assert r['status']=='complete'
        if item['name']=='incidental_bridge_split_then_continue':
            events=[e for e in r['structure_events'] if e['type']=='known_residual_split_batch']
            assert len(events)==1 and len(events[0]['replacements'])==1
            assert sorted(map(len,events[0]['replacements'][0]['parts']))==[1,1]
            assert len(r['plans'])>=2 and r['plans'][0]['end']==(1,-1)
        else:assert not r['plans'] and r['distance']==2
    (H/'integration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(additional_full_calls=2,bridge_split_continue_pass=True,empty_return_pass=True,policy_changes=0)))
if __name__=='__main__':main()
