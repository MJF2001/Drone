"""Report-only own-progress obstruction experiments; immutable algorithm imports."""
from pathlib import Path
import sys,os,json,subprocess,math,traceback
from run_front_block import read,write,sha,pts
from run_scaled_mixed_v03 import reachable,valid
H=Path(__file__).resolve().parent;R=H.parent;O=H/'各自进度前方障碍展示_v0.1_20261024';OLD=R/'七算法共同预算比较_v0.3_Cstar07_20261020'
METHODS=['PPCPP','LOCAL_P2','ORIENT4']
def main():
 assert not O.exists();O.mkdir();[(O/d).mkdir() for d in ['inputs','jobs','results','logs']]
 sources=read(H/'前方未飞覆盖路段受阻展示_v0.1_20261024/protocol.json')['sources'];sources[str(Path(__file__).resolve())]=sha(__file__)
 schedule=[('obstacle',.20),('obstacle',.50),('obstacle',.75)];mixed=[('straight',.10),('obstacle',.20),('corner',.35),('obstacle',.50),('obstacle',.75)]
 configs=[('small',10,6,5,5),('medium',20,8,6,7),('large',30,10,8,9)]
 write(O/'protocol.json',dict(seed=20261020,methods=METHODS,max_entries=90,configs=configs,schedule=schedule,mixed_schedule=mixed,sources=sources,coverage='actual unique inspected / currently published inspectable targets (exclude already blocked targets); latch each threshold only once in sequence; expansions may lower percentage',obstacle='after threshold, first actual vertex with immediate next planned cell a never-flown pending task; removing it must leave all remaining targets/base reachable and another task after it. Do not skip ahead in route to plant farther obstacle. If current next-cell fails, execute next old-route move and inspect at next vertex. Record actual ratio and steps waited. If no opportunity before completion, stop session, no replacement.',comparison='same trigger policy; each method has own history, trigger time and obstruction coordinate. Not same-map strict paired comparison. All start with empty history at common external base under original grid-center model. Original six-method component unchanged. Fixed20s entries serial; no retries or selection by gains.'))
 worlds=[];ledger=[];env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
 def call(s,m,ident,marker):
  assert len(ledger)<90
  for f,h in sources.items():assert sha(f)==h,f
  ip=O/'inputs'/(ident+'.json');write(ip,s);job=dict(id=ident,run_id=ident,case_id=s['name'],method=m,input=str(ip),input_sha256=sha(ip),marker=marker,budget=20,seed=20261020);jp=O/'jobs'/(ident+'.json');out=O/'results'/(ident+'.json');write(jp,job);ledger.append(dict(id=ident,status='started'));write(O/'ledger.json',ledger)
  cmd=[sys.executable,'-B','-X','utf8',str(H/'run_front_block.py'),'worker',str(jp),str(out)] if m!='PPCPP' else [sys.executable,'-B','-X','utf8',str(OLD/'worker.py'),str(jp),str(out)]
  with (O/'logs'/(ident+'.log')).open('wb') as log:p=subprocess.run(cmd,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
  ledger[-1]['returncode']=p.returncode;write(O/'ledger.json',ledger);assert p.returncode==0,ident
  d=read(out);r=d.get('result',d);valid(s,r['raw']['route']);ledger[-1].update(status='valid',seconds=r['entry_seconds']);write(O/'ledger.json',ledger);print(ident,'valid',flush=True)
  return dict(plan=r['raw']['route'],seconds=r['entry_seconds'],raw=r['raw'],source=str(out),sha256=sha(out))
 try:
  for size,n,h,width,leg in configs:
   for kind in ['single','mixed']:
    P0={(x,y) for x in range(n) for y in range(h)};F0={(x,y) for x in range(-1,n) for y in range(h)};base=[-1,0];cid=size+'_'+kind
    ini=dict(name=cid,free=sorted(F0),targets=sorted(P0),published_targets=sorted(P0),initial_targets=sorted(P0),covered=[],deferred_targets=[],current=base,base=base,previous=None,predator=[-2,0],old_route=[base],distance_budget=1000000)
    w=dict(id=cid,kind=kind,size=size,initial=ini,sessions=[],events=[dict(name=(('障碍 '+str(int(t*100))+'%') if k=='obstacle' else ('直线扩展' if k=='straight' else '拐角扩展')),threshold=t) for k,t in (mixed if kind=='mixed' else schedule)])
    for m in METHODS:
     P=set(P0);F=set(F0);route=[base];Hc=set();events=[];first=call(ini,m,cid+'_'+m+'_start',[]);plan=first['plan'];phases=[dict(start_step=0,free=sorted(F),published=sorted(P),**first)];stop=None
     for j,(etype,threshold) in enumerate(mixed if kind=='mixed' else schedule):
      reached=None;cut=None;block=None
      for i,q in enumerate(plan):
       if i:route.append(q)
       if tuple(q) in P:Hc.add(tuple(q))
       ratio=len(Hc & F)/len(P & F)
       if ratio+1e-12<threshold:continue
       if reached is None:reached=len(route)-1
       if etype!='obstacle':cut=i;break
       if i+1>=len(plan):break
       b=tuple(plan[i+1]);pending=(P&F)-Hc
       if b not in pending or b in pts(route) or not (pts(plan[i+2:])&pending-{b}):continue
       if not ((P&F)-{b}|{tuple(base)})<=reachable(F-{b},q):continue
       cut=i;block=b;break
      if cut is None:stop='no qualified immediate-next-cell opportunity';break
      old=plan[cut:];priorP=set(P);e=dict(name=w['events'][j]['name'],step=len(route)-1,threshold=threshold,ratio=ratio,threshold_first_step=reached,wait_steps=len(route)-1-reached,current=route[-1],old_route=old,actual_history=sorted(Hc),remove=[],add_targets=[],add_free=[])
      if etype=='obstacle':F.remove(block);marker=[block];e['remove']=marker;assert old[1]==list(block) or tuple(old[1])==block
      else:
       add={(x,y) for x in range(n,n+width) for y in (range(h) if etype=='straight' else range(h,h+leg))};F|=add;P|=add;marker=sorted(add-priorP);e.update(add_targets=marker,add_free=sorted(add))
      events.append(e);write(O/(cid+'_'+m+'_event'+str(j)+'_precall.json'),e)
      s=dict(ini,name=cid+'_'+m+'_'+str(j),free=sorted(F),targets=sorted(P&F),published_targets=sorted(P),covered=sorted(Hc),initial_targets=sorted(priorP),current=route[-1],previous=route[-2] if len(route)>1 else None,old_route=old,deferred_targets=sorted(P-F-Hc),distance_budget=1000000-len(route)+1)
      r=call(s,m,cid+'_'+m+'_'+str(j),marker);plan=r['plan'];phases.append(dict(start_step=len(route)-1,free=sorted(F),published=sorted(P),**r))
     if not stop:
      route+=plan[1:];Hc|=pts(plan)&P
     session=dict(method=m,route=route,covered=sorted(Hc),deferred=sorted(P-F-Hc),steps=len(route)-1,events=events,phases=phases,status='not_applicable' if stop else 'complete',reason=stop)
     w['sessions'].append(session);write(O/'partial.json',dict(worlds=worlds,current=w))
    w['status']='complete' if all(s['status']=='complete' for s in w['sessions']) else 'partial';worlds.append(w);write(O/'results.json',dict(worlds=worlds,entries=len(ledger)))
  write(O/'status.json',dict(complete=True,entries=len(ledger)))
 except BaseException as e:
  write(O/'failure.json',dict(error=repr(e),traceback=traceback.format_exc()));raise
if __name__=='__main__':main()
