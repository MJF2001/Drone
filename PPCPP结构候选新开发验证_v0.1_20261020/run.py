import sys,copy,json
from common import H,R,read,save,sha,protect,call
from worker import snapshot
from rollout import solve,native
from checks import audit,norm
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from metrics import metrics
def gates():
    p=protect(True);stream=(H/'gates.jsonl').open('x',encoding='utf-8');count=0
    for c in p['cases']:
        inp=read(c['input']);s=snapshot(inp);initial=set(map(tuple,inp['initial_targets']));before=copy.deepcopy((inp,s,initial));args=(s,initial,20,20261021,tuple(inp['predator']),tuple(inp['previous']))
        n=native.solve(*args);stream.write(json.dumps(dict(case_id=c['case_id'],method='PPCPP',input=inp,result=n),ensure_ascii=False,separators=(',',':'))+'\n');stream.flush();audit(inp,n);count+=1
        one=solve(*args,mode='one');stream.write(json.dumps(dict(case_id=c['case_id'],method='ONE',input=inp,result=one),ensure_ascii=False,separators=(',',':'))+'\n');stream.flush();audit(inp,one);count+=1
        assert (inp,s,initial)==before and n['status']==one['status']=='core_complete'
        assert norm(n['route'])==norm(one['route']) and norm(n['trace'])==norm(one['trace'])
    stream.close();assert count==72;protect(True);save(H/'gate_PASS.json',dict(all_pass=True,calls=count,states=36));print('72 new-input equivalence calls passed')
def run():
    p=protect(True);assert read(H/'gate_PASS.json')['all_pass'] and not (H/'execution').exists();rows=[]
    for i,j in enumerate(p['jobs']):
        dest=H/'execution/results'/(j['run_id']+'.json');r=call(j,dest);inp=read(j['input']);audit(inp,r['raw'])
        rows.append(dict(job=j,eligible=r['eligible'],status=r['raw']['status'],entry_seconds=r['entry_seconds'],result_sha256=sha(dest),metrics=metrics(inp,r['raw']['route']) if r['raw']['route'] else None));save(H/'execution/checks.json',rows)
        print(i+1,'/',len(p['jobs']),j['run_id'],rows[-1]['metrics']['length'] if rows[-1]['metrics'] else rows[-1]['status'],flush=True)
    protect(True);save(H/'execution/completion.json',dict(scheduled=len(p['jobs']),executed=len(rows),eligible=sum(x['eligible'] for x in rows)))
if __name__=='__main__':
    if sys.argv[1]=='gates':gates()
    else:run()
