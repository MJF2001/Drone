"""One isolated method session; one fresh worker per actual response."""
from util import *
from executor import run_world
from contracts import TechnicalError
import sys,subprocess,time
def run_session(sj):
    cfg=config();check_seal();world=read(H/'worlds.json')[sj['world']];slots=[s for s in read(H/'call_slots.json') if s['session']==sj['id']];index=0;callback_rows=[]
    def callback(payload):
        nonlocal index
        begin=time.perf_counter();check_seal();assert index<len(slots);slot=slots[index];index+=1
        journal=H/'actual_attempts.jsonl';past=[json.loads(x) for x in journal.read_text(encoding='utf8').splitlines()] if journal.exists() else [];assert len(past)<cfg['real_entry_cap']
        rid=slot['id'];inp=H/'inputs'/(rid+'.json');jobpath=H/'jobs'/(rid+'.json');out=H/'outputs'/(rid+'.json');log=H/'logs'/(rid+'.txt');assert not any(p.exists() for p in (inp,jobpath,out,log))
        put(inp,payload);j=dict(id=rid,session=sj['id'],method=sj['method'],seed=sj['seed'],slot=slot,input=str(inp.relative_to(H)),input_sha256=sha(inp),seal_sha256=sha(H/'seal.json'));save(jobpath,j)
        attempt=dict(id=rid,session=sj['id'],method=sj['method'],sequence=len(past)+1,process_start=time.time(),synthetic=H.name=='SYNTHETIC_TECHNICAL_NOT_REAL')
        with journal.open('a',encoding='utf8') as f:f.write(json.dumps(attempt)+'\n')
        try:p=subprocess.run([sys.executable,'-B','-X','utf8',str(H/'worker.py'),str(jobpath),str(out)],env=env(),capture_output=True,timeout=90);code=p.returncode;data=p.stdout+p.stderr
        except subprocess.TimeoutExpired as ex:code='watchdog';data=(ex.stdout or b'')+(ex.stderr or b'')
        put(log,data);markers=dict(entries=data.count(b'ENTRY_START '),core_starts=data.count(b'CORE_START '),core_returns=data.count(b'CORE_RETURN'),entry_returns=data.count(b'ENTRY_RETURN '));assert max(markers.values())<=1
        q=dict(job=j,exit_code=code,markers=markers,callback_total_wall_seconds=time.perf_counter()-begin,no_retry=True)
        if code!=0:
            q['status']='WATCHDOG' if code=='watchdog' else 'PROCESS_ABNORMAL';save(H/'logs'/(rid+'.receipt.json'),q);raise RuntimeError(('worker_process_stop',rid,code))
        x=read(out);assert x['job']==j and x['input_sha256']==sha(inp) and markers==dict(entries=1,core_starts=1,core_returns=1,entry_returns=1)
        q.update(status='RETURNED',output_sha256=sha(out),entry_seconds=x['entry']['entry_seconds'],native_graph=x['native_graph']);save(H/'logs'/(rid+'.receipt.json'),q);callback_rows.append(q)
        return x['entry']['response']
    try:result=run_world(world,{sj['method']:callback})
    except TechnicalError as ex:
        if ex.result:save(H/'sessions'/(sj['id']+'.json'),ex.result)
        raise
    save(H/'sessions'/(sj['id']+'.json'),result);save(H/'sessions'/(sj['id']+'.callbacks.json'),callback_rows)
    print('SESSION_COMPLETE',sj['id'],result['sessions'][sj['method']]['summary']['status'],'responses',index,flush=True)
    return result
def main():
    j=read(sys.argv[1]);assert j in read(H/'session_order.json');run_session(j)
if __name__=='__main__':main()
