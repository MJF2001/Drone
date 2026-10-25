"""Independent replay; no hybrid/window/engine helper imports."""
from support import *
pa=load('local_original_scalar',R/'基线复现准备_20261019/独立版_v0.2/audit_ppcpp.py')
metric=load('local_metrics',R/'评价指标完整补算与数据审计_v0.1_20261020/metrics.py').metrics
cross=load('local_cross',R/'评价指标完整补算与数据审计_v0.1_20261020/crosscheck.py').calculate
def rebuild(c,p,B):
 f=pts(c['targets']);h=pts(c['covered']);u=f-h-{tuple(c['current'])};ids={};seen=set(h)
 for i,v in enumerate(map(tuple,p)):
  if v in f and v not in seen:ids[v]=i;seen.add(v)
 seeds=sorted(q for q in u if any(abs(q[0]-b[0])+abs(q[1]-b[1])<=2 for b in map(tuple,B)))
 if not seeds:return dict(empty=True,seeds=[],first_indices=[dict(cell=list(q),index=i) for q,i in sorted(ids.items())])
 l=max(0,min(ids[q] for q in seeds)-1);r=min(len(p)-1,max(ids[q] for q in seeds)+1);done=h|(pts(p[:l+1])&f);req=sorted(q for q,i in ids.items() if l<i<=r)
 return dict(empty=False,left=l,right=r,entry=p[l],exit=p[r],seeds=list(map(list,seeds)),required=list(map(list,req)),local_H=list(map(list,sorted(done))),prefix=p[:l+1],suffix=p[r:],original_patch=p[l:r+1],pending=len(u),task_fraction=len(req)/len(u) if u else 0,step_fraction=(r-l)/(len(p)-1) if len(p)>1 else 0,first_indices=[dict(cell=list(q),index=i) for q,i in sorted(ids.items())])
def path(f,p,start,end):
 p=list(map(tuple,p));assert p and p[0]==tuple(start) and p[-1]==tuple(end) and set(p)<=f
 assert all(abs(a[0]-b[0])+abs(a[1]-b[1])==1 for a,b in zip(p,p[1:]))
def checked_metric(c,p):
 a=metric(c,p);assert a==cross(c,p) and a['complete_legal'];return a
def check(env,x,method):
 c=env['state'];r=x['raw'];f=pts(c['free']);out={}
 if method=='PPCPP' and r.get('route'):pa.audit(c,r)
 if method=='LOCAL_P2':
  p0=r.get('P0')
  if p0 and p0['route']:pa.audit(c,p0);out['P0_metrics']=checked_metric(c,p0['route'])
  cfg=r.get('window')
  if cfg is not None:
   assert cfg==rebuild(c,p0['route'],env['marker'])
   if not cfg['empty'] and r.get('local'):
    er=r['local'];patch=er['route'];assert er['improvements'] and er['source']==er['improvements'][-1]['source'] and len(patch)-1==er['improvements'][-1]['steps']
    path(f,patch,cfg['entry'],cfg['exit']);assert pts(cfg['required'])<=pts(cfg['local_H'])|pts(patch)
    full=cfg['prefix'][:-1]+patch+cfg['suffix'][1:];assert full==r['assembled_route'];out['assembled_metrics']=checked_metric(c,full)
    assert len(full)-len(p0['route'])==len(patch)-len(cfg['original_patch'])
    out['incidental_external']=sorted(pts(patch)&(pts(c['targets'])-pts(c['covered']))-pts(cfg['required'])-pts(cfg['local_H']))
   if r['status']=='core_complete':
    if cfg['empty']:assert r['selected']=='P0' and r['route']==p0['route']
    else:
     expected='LOCAL_P2' if len(r['assembled_route'])<len(p0['route']) else 'P0';assert r['selected']==expected;assert r['route']==(r['assembled_route'] if expected=='LOCAL_P2' else p0['route'])
 if r['route']:out['metrics']=checked_metric(c,r['route'])
 if method!='P2_MULTI' and x['entry_seconds']>=x['budget']:assert not r['route']
 return norm(out)
