from pathlib import Path
from collections import deque
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parent
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    assert not (H/'protocol.json').exists();cases=[];methods=['PPCPP','CSTAR','TRACE','CAP_OLD','CAP_KR1']
    def offer(name,f,t,h,current,base,initial,factor,template,level):
        c=dict(name=name,free=sorted(f),targets=sorted(t),covered=sorted(h),published_targets=sorted(t),deferred_targets=[],current=current,base=base,distance_budget=1000,initial_targets=sorted(initial),previous=base,predator=(-3,current[1]),old_route=[current,base])
        assert current in h and base in h and sum(abs(a-b) for a,b in zip(current,base))==1 and h<=t<=f
        # Independent BFS witness saved but never passed to any method.
        route=[current]
        for goal in sorted(t-h)+[base]:
            parents={route[-1]:None};queue=deque(parents)
            while goal not in parents:
                x,y=queue.popleft()
                for q in ((x-1,y),(x,y+1),(x,y-1),(x+1,y)):
                    if q in f and q not in parents:parents[q]=(x,y);queue.append(q)
            seg=[goal]
            while seg[-1]!=route[-1]:seg.append(parents[seg[-1]])
            route+=seg[::-1][1:]
        assert len(route)-1<1000 and t<=h|set(route)
        ip=H/'inputs'/(name+'.json');save(ip,c);save(H/'witnesses'/(name+'.json'),dict(route=route))
        cases.append(dict(case_id=name,factor=factor,template=template,level=level,input=str(ip),input_sha256=sha(ip)))
    previous=read(R/'固定实现_区域间距受控诊断_v0.1_20261020/protocol.json')
    for item in previous['cases']:
        c=read(item['input']);offer('gap_'+item['case_id'],set(map(tuple,c['free'])),set(map(tuple,c['targets'])),set(map(tuple,c['covered'])),tuple(c['current']),tuple(c['base']),set(map(tuple,c['initial_targets'])),'gap',item['family'],item['gap_columns'])
    for k,w in enumerate((8,10,12)):
        t={(x,y) for x in range(1,w+1) for y in range(1,7)}|{(0,1)};fixed={(0,1),(1,1)};f={(x,y) for x in range(-2,w+3) for y in range(-1,9)}
        forms=[{(x,6) for x in range(w-5,w+1)},{(w//2,y) for y in range(1,7)},{(i+2,i+1) for i in range(6)}]
        for level,extra in enumerate(forms):offer(f'history_t{k}_l{level}',f,t,fixed|extra,(1,1),(0,1),t,'history',k,level)
    for k,by in enumerate((2,5,8)):
        t={(x,y) for x in range(2,5) for y in range(2,4)}|{(x,y) for x in range(10,13) for y in range(by,by+2)}|{(-1,1),(0,1)};history={(-1,1),(0,1)}
        full={(x,y) for x in range(-2,16) for y in range(-2,12)}
        for height in (0,6,10):offer(f'barrier_t{k}_h{height}',full-{(7,y) for y in range(-2,-2+height)},t,history,(0,1),(-1,1),history,'barrier',k,height)
    jobs=[]
    for i,c in enumerate(cases):
        for si,seed in enumerate((20261018,20261019)):
            rot=(i+si)%5;order=methods[rot:]+methods[:rot]
            if si:order=order[::-1]
            for m in order:jobs.append(dict(run_id=f'{c["case_id"]}_{seed}_{m}',case_id=c['case_id'],method=m,input=c['input'],input_sha256=c['input_sha256'],budget=20,seed=seed))
    gate=H/'gate_input.json';save(gate,read(R/'七算法共同预算比较_v0.3_Cstar07_20261020/preflight/input.json'))
    oldrows=read(R/'评价指标完整补算与数据审计_v0.1_20261020/per_run.json');selected=[]
    for m,batch,original_m in [('CSTAR','SEVEN_V03','CSTAR'),('TRACE','SEVEN_V03','TRACE'),('CAP_OLD','SEVEN_V03','CAP'),('CAP_KR1','KR1_PAIR','CAP_KR1')]:
        own=[x for x in oldrows if x['batch']==batch and x['method']==original_m and x['seed']==20261018];paired=[]
        for x in own:
            ref=next(y for y in oldrows if y['batch']==batch and y['method']=='PPCPP' and y['case_id']==x['case_id'] and y['seed']==x['seed']);paired.append((ref['m']['length']/x['m']['length']-1,x,ref))
        for role,key in [('ppcpp_positive',lambda z:z[0]),('opponent_positive',lambda z:-z[0]),('closest_tie',lambda z:abs(z[0]))]:
            delta,x,ref=min(paired,key=key);selected.append(dict(opponent=m,role=role,relative=delta,case_id=x['case_id'],opponent_source=x['source_path'],ppcpp_source=ref['source_path'],input=read(Path(x['source_path']))['job']['input']))
    prior=read(R/'PPCPP_CAP_KR1共同预算比较_v0.1_20261020/protocol.json');files=dict(prior['files'])
    for f in list(H.rglob('*'))+[R/'评价指标完整补算与数据审计_v0.1_20261020/per_run.json',R/'固定实现_区域间距受控诊断_v0.1_20261020/protocol.json']:
        if f.is_file():files[str(f)]=sha(f)
    for item in selected:
        for k in ('opponent_source','ppcpp_source','input'):files[item[k]]=sha(Path(item[k]))
    save(H/'protocol.json',dict(version='ALL_PAPER_ADAPTATIONS_CAUSAL_DIAG_v0.1',methods=methods,cases=cases,jobs=jobs,gate_input=str(gate),selected_cases=selected,files=files,formal_calls=270,preflight_calls=10,holdout=False))
    print('presealed',len(cases),'inputs',len(jobs),'jobs')
if __name__=='__main__':main()
