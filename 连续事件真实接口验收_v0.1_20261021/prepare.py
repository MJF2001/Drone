"""Exclusive fixed-world/source construction, no algorithm imports or calls."""
from pathlib import Path
import json,hashlib,difflib
H=Path(__file__).resolve().parent;R=H.parent;S=R/'连续事件执行器纯桩验收_v0.1_20261021';P=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020';D=R/'PPCPP首次新旧竞争单步干预诊断_v0.1_20261021'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def main():
    for n in ('inputs','jobs','outputs','logs','sessions','receipts','technical_rounds','frozen_source_bytes'):(H/n).mkdir()
    old=json.loads((S/'completion_manifest.json').read_text(encoding='utf8'))['files'];rows=[]
    for name in ('executor.py','contracts.py'):
        assert sha(S/name)==old[name]
        with (H/name).open('xb') as f:f.write((S/name).read_bytes())
        rows.append(dict(source=str(S/name),target=name,source_sha256=sha(S/name),target_sha256=sha(H/name),byte_identical=True))
    a=(S/'auditor.py').read_text(encoding='utf8');b=a
    b=b.replace("assert req['response']==serialized_stub(spec['methods'][name][ri]);admission,why=response_rule(snap,req['response']);", "assert isinstance(req['response'],dict);admission,why=response_rule(snap,req['response']);")
    b=b.replace("ri==len(requests)==len(spec['methods'][name])", "ri==len(requests) and ri<=3")
    b=b.replace("manual_subset(summary,spec['expected'][name],spec['id']+'/'+name)", "assert_real_source = True")
    b=b.replace('hand_expectations_passed=True','hand_expectations_passed=False,real_saved_response_audit=True').replace('manual_expectations_original=True','manual_expectations_original=False,real_response_mode=True')
    with (H/'auditor.py').open('x',encoding='utf8') as f:f.write(b)
    with (H/'auditor_binding.diff').open('x',encoding='utf8') as f:f.write(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=str(S/'auditor.py'),tofile=str(H/'auditor.py'))))
    rows.append(dict(source=str(S/'auditor.py'),target='auditor.py',source_sha256=sha(S/'auditor.py'),target_sha256=sha(H/'auditor.py'),byte_identical=False,reason='Only remove handwritten-return/manual-result association; all independent state/credit/move/input/BFS reconstruction unchanged'))
    with (H/'reference_contract.py').open('xb') as f:f.write((D/'reference_contract.py').read_bytes())
    save(H/'copy_manifest.json',rows)
    f15=[[x,y] for x in range(5) for y in range(3)];p0=[[1,0],[2,0],[3,0]]
    def e(t,id,a=[],b=[]):return dict(tick=t,id=id,add_targets=a,block=b)
    def w(f,p,events):return dict(free=f,published=p,start=[0,0],base=[0,0],E0=100,T_max=60,events=events)
    worlds=dict(W1=w(f15,p0,[e(1,'e1',[[2,1],[3,1]]),e(3,'e2',[[1,2],[2,2]])]),W2=w(f15,p0,[e(1,'e1',[[2,1],[3,1]]),e(3,'e2',b=[[4,2]])]),W3=w([[0,0],[1,0],[2,0],[3,0]],[[1,0]],[e(4,'e1',[[0,0],[2,0]]),e(10,'e2',[[3,0]])]))
    save(H/'worlds.json',worlds);order=[];slots=[]
    for wid,methods in (('W1',['PPCPP','P2_MULTI']),('W2',['P2_MULTI','PPCPP']),('W3',['PPCPP','P2_MULTI'])):
        for method in methods:
            sid=wid+'_'+method;j=dict(id=sid,world=wid,method=method,seed=20261021);order.append(j)
            for tick in [0]+[v['tick'] for v in worlds[wid]['events']]:slots.append(dict(id=sid+f'_t{tick:03d}',session=sid,method=method,tick=tick,seed=20261021))
    assert len(slots)==18;save(H/'session_order.json',order);save(H/'call_slots.json',slots)
    save(H/'config.json',dict(real_entry_cap=18,entry_budget=20,watchdog=90,seed=20261021,threads=1,stub_cap_all_rounds=24,technical_round_cap=3))
    save(H/'source_lock.json',json.loads((D/'preseal.json').read_text(encoding='utf8'))['files'])
    with (H/'执行稿.md').open('xb') as f:f.write((R/'连续事件真实算法接口验收执行稿_给sol_20261021.md').read_bytes())
    print('Fixed3 technical worlds,6 isolated sessions,18 real slots; byte-copy executor/contracts; real calls0')
if __name__=='__main__':main()
