from pathlib import Path
import json,hashlib,time,traceback
import engine,verify
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
def main():
    assert not (H/'batch_status.json').exists(),'one batch only'
    for p,h in read(H/'frozen_manifest.json')['files'].items():assert sha(H/p)==h,p
    for p,h in read(H/'来源hash.json').items():assert sha(Path(p))==h,p
    jobs=read(H/'117固定清单.json');status={'started':[],'completed':[],'unrun':[j['id'] for j in jobs],'failure':None};dump(H/'batch_status.json',status)
    ledger=H/'actual_entries.jsonl'
    for job in jobs:
        jid=job['id'];status['started'].append(jid);status['unrun'].remove(jid);dump(H/'batch_status.json',status)
        try:
            payload=(H/job['payload']).read_bytes();assert hashlib.sha256(payload).hexdigest()==job['payload_sha256']
            encoded,envelope=engine.process(payload);outbytes=encoded.encode('utf8');op=H/'outputs'/(jid+'.json');op.write_bytes(outbytes)
            with ledger.open('a',encoding='utf8') as f:f.write(json.dumps({'id':jid,'entry':envelope},ensure_ascii=False)+'\n')
            audit=verify.audit_one(job,payload,outbytes);dump(H/'audits'/(jid+'.json'),audit)
            status['completed'].append(jid);dump(H/'batch_status.json',status)
            if len(status['completed'])%10==0:print('completed',len(status['completed']),flush=True)
        except Exception as ex:
            status['failure']={'id':jid,'exception':repr(ex),'traceback':traceback.format_exc()};dump(H/'batch_status.json',status);print(json.dumps(status['failure'],ensure_ascii=False),flush=True);return
    print('completed',len(status['completed']),'STOP',flush=True)
if __name__=='__main__':main()
