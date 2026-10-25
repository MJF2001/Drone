import json,hashlib
def transform(p,k):
 x,y=p
 if k>=4:x=-x
 for _ in range(k%4):x,y=-y,x
 return x,y
def signature(c,kind='shape',symmetry=True):
 variants=[]
 for k in range(8) if symmetry else (0,):
  fields=['published_targets'] if kind=='shape' else ['free','targets','covered','published_targets','deferred_targets','initial_targets']
  data={f:[transform(q,k) for q in c[f]] for f in fields}
  if kind=='shape':data['blocked']=[transform(q,k) for q in set(map(tuple,c['published_targets']))-set(map(tuple,c['free']))]
  anchor=data['published_targets'] if kind=='shape' else data['free'];dx=min(q[0] for q in anchor);dy=min(q[1] for q in anchor)
  shift=lambda q:[q[0]-dx,q[1]-dy]
  data={f:sorted(shift(q) for q in qs) for f,qs in data.items()}
  if kind!='shape':
   for f in ('current','base','previous','predator'):data[f]=shift(transform(c[f],k)) if c[f] is not None else None
   data['old_route']=[shift(transform(q,k)) for q in c['old_route']];data['distance_budget']=c['distance_budget']
  variants.append(json.dumps(data,sort_keys=True,separators=(',',':')))
 return hashlib.sha256(min(variants).encode()).hexdigest()
def exact_equal(a,b):return {k:v for k,v in a.items() if k!='name'}=={k:v for k,v in b.items() if k!='name'}
