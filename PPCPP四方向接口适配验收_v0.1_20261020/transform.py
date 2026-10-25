"""Field-specific integer isometry; preserve all input sequence ordering."""
from common_orient import *
SETS=('free','targets','covered','published_targets','deferred_targets','initial_targets','old_route')
POINTS=('current','base','previous','predator')
def rotate(p,k):
 x,y=p;return [(x,y),(-y,x),(-x,-y),(y,-x)][k%4]
def transform(c,k):
 if k==0:return c,dict(k=0,shift=[0,0])
 ff=[rotate(p,k) for p in c['free']];tx=-min(p[0] for p in ff) if ff else 0;ty=-min(p[1] for p in ff) if ff else 0
 def point(p):
  if p is None:return None
  x,y=rotate(p,k);return [x+tx,y+ty]
 out=dict(c)
 for key in SETS:out[key]=[point(p) for p in c[key]]
 for key in POINTS:out[key]=point(c[key])
 return out,dict(k=k,shift=[tx,ty])
def inverse_point(p,meta):
 if p is None:return None
 return list(rotate((p[0]-meta['shift'][0],p[1]-meta['shift'][1]),-meta['k']))
def inverse_input(c,meta):
 out=dict(c)
 for key in SETS:out[key]=[inverse_point(p,meta) for p in c[key]]
 for key in POINTS:out[key]=inverse_point(c[key],meta)
 return out
def inverse_raw(raw,meta):
 r=norm(raw);r['route']=[inverse_point(p,meta) for p in r['route']];r['predator']=inverse_point(r['predator'],meta);r['initial_previous']=inverse_point(r['initial_previous'],meta)
 for ev in r['trace']:
  for key in ('current','previous','goal'):
   if key in ev:ev[key]=inverse_point(ev[key],meta)
  for op in ev.get('options',[]):op['cell']=inverse_point(op['cell'],meta)
 return r
