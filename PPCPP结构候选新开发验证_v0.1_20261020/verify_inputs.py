"""Independently reconstruct footprints and always-on history from saved execution."""
import sys
from pathlib import Path
from common import H,R,read,save,sha,protect,signature
from validation import validate
sys.path.insert(0,str(R/'评价指标完整补算与数据审计_v0.1_20261020'));from crosscheck import calculate
from metrics import metrics
from checks import audit
def points(xs):return set(map(tuple,xs))
def check():
    p=protect();old=read(R/'PPCPP两窗口结构候选_v0.1_20261020/protocol.json');old_sigs={signature(read(c['input'])) for c in old['cases']};seen=set();rows=[]
    for c in p['cases']:
        inp=read(c['input']);wtn=read(H/'witnesses'/(c['case_id']+'.json'));initial=read(wtn['initial_input']);result=read(wtn['initial_result']);assert result['eligible'] and result['job']['method']=='PPCPP'
        validate(initial);validate(inp);audit(initial,result['raw']);L,w=c['length'],c['width'];W=2*L+2*w+12;Y=L+2*w+12
        f0={(x,y) for x in range(W) for y in range(Y)}
        t0={(x,y) for x,y in f0 if (4<=x<4+L and 4<=y<4+w) or (c['layout']=='B' and 4+L-w<=x<4+L and 4+w<=y<4+w+L//2)}
        assert points(initial['free'])==f0 and points(initial['targets'])==t0==points(initial['published_targets'])==points(initial['initial_targets']) and not initial['covered']
        assert initial['current']==initial['base']==[1,1] and initial['previous'] is None and initial['predator']==[-1,0]
        route=list(map(tuple,result['raw']['route']));assert route[0]==route[-1]==(1,1) and set(route)<=f0 and t0<=set(route)
        assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(route,route[1:]))
        cutoff=wtn['cut_index'];prefix=route[:cutoff+1];h=set(prefix)&t0;cur=prefix[-1];goal=(len(t0)*c['progress']+99)//100
        assert points(inp['covered'])==h and len(h)==goal==wtn['goal_covered'] and len(set(prefix[:-1])&t0)<goal
        assert wtn['history']==[list(q) for q in prefix] and inp['current']==list(cur) and inp['previous']==list(prefix[-2]) and inp['old_route']==[list(q) for q in route[cutoff:]]
        extra=set();b=set()
        if c['event']=='straight':
            extra={(x,y) for x,y in f0 if (4+L<=x<4+L+L//2 and 4<=y<4+w)} if c['layout']=='A' else {(x,y) for x,y in f0 if 4+L-w<=x<4+L and 4+w+L//2<=y<4+w+L}
        elif c['event']=='corner':
            extra={(x,y) for x,y in f0 if 4+L-w<=x<4+L and 4+w<=y<4+w+L//2} if c['layout']=='A' else {(x,y) for x,y in f0 if 4+L-w-L//2<=x<4+L-w and 4+L//2<=y<4+w+L//2}
        else:
            x0=4+2*L//3;x1=x0+max(2,L//10);lower={(x,y) for x,y in f0 if x0<=x<x1 and 4<=y<4+w//2}
            switched=cur in lower;bottom=4+w-w//2 if switched else 4;b={(x,y) for x,y in f0 if x0<=x<x1 and bottom<=y<bottom+w//2}
            assert wtn['switched']==switched
        pub=t0|extra;f=f0-b
        assert not extra&t0 and (len(extra)==L//2*w if c['event']!='obstacle' else not extra)
        assert points(inp['free'])==f and points(inp['published_targets'])==pub and points(inp['targets'])==pub&f and points(inp['deferred_targets'])==pub-f-h
        assert points(wtn['blocked'])==b and cur in f and (1,1) in f and points(inp['initial_targets'])==t0 and inp['distance_budget']==1000000
        assert inp['base']==[1,1] and inp['predator']==[-1,0]
        v=metrics(inp,wtn['feasible_route']);assert v==calculate(inp,wtn['feasible_route']) and v['complete_legal'] and v['missing_active']==0
        sig=signature(inp);assert sig not in seen and sig not in old_sigs;seen.add(sig)
        rows.append(dict(case_id=c['case_id'],signature=sig,history_steps=len(prefix)-1,history_targets=len(h),active_targets=len(pub&f),deferred=len(pub-f-h),blocked_previously_completed=len(b&h),feasible_steps=v['length']))
    assert len(rows)==36;return rows
def main():
    rows=check();assert not (H/'input_seal.json').exists();save(H/'input_audit.json',dict(verified=True,snapshots=36,base_plans=6,event_families=18,history_witnesses=36,future_witnesses=36,no_old_translated_duplicates=True,rows=rows))
    files={str(f):sha(f) for root in (H/'inputs',H/'witnesses',H/'prep') for f in root.rglob('*') if f.is_file()};files[str(H/'input_audit.json')]=sha(H/'input_audit.json')
    save(H/'input_seal.json',dict(protocol_sha256=sha(H/'protocol.json'),files=files,snapshots=36));print('input audit and seal passed: 36 histories + 36 feasible routes, 6 preparation calls')
if __name__=='__main__':main()
