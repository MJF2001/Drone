"""Render only saved evidence; no planner or exact solver imports."""
import os,sys,json
from pathlib import Path
if os.environ.get('SMALLGAP_PLOT_DEPS'):sys.path.insert(0,os.environ['SMALLGAP_PLOT_DEPS'])
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 a=read(H/'analysis.json');(H/'figures').mkdir(exist_ok=True)
 for name in dict.fromkeys(v for v in a['selected'].values() if v):
  c=read(H/'inputs'/f'{name}.json');r=next(r for r in a['states'] if r['id']==name);raw=read(H/'execution'/f'{name}.json')['raw'];glob=read(H/'exact'/name/'A.json');qnear=read(H/'exact'/name/(r['mapping']['C']+'.json')) if r['mapping']['C'] else None
  panels=[('PPCPP',raw,'#2060ac'),('Global shortest witness',glob,'#bd3b31'),('Nearest-last constrained',qnear,'#7a4594')]
  fig,axes=plt.subplots(1,3,figsize=(16,5.5),layout='constrained');f=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));hist=set(map(tuple,c['covered']));defer=set(map(tuple,c['deferred_targets']));W=max(x for x,y in f)+1
  for ax,(label,res,color) in zip(axes,panels):
   for x in range(W):
    for y in range(6):
     p=x,y;fill='#d9edcd' if p in t else '#fafafa'
     if p in hist:fill='#abc6df'
     if p not in f:fill='#efb65b' if p in defer else '#555555'
     ax.add_patch(Rectangle((x-.5,y-.5),1,1,facecolor=fill,edgecolor='#999',lw=.6))
     if p not in f:ax.text(x,y,'H/X' if p in hist else 'X',ha='center',va='center',fontsize=8)
   route=res['route'] if res else []
   if route:
    ax.plot([p[0] for p in route],[p[1] for p in route],'-o',lw=1.6,ms=3,color=color,alpha=.75)
    for p,q in zip(route,route[1:]):ax.annotate('',xy=(p[0]+.7*(q[0]-p[0]),p[1]+.7*(q[1]-p[1])),xytext=(p[0]+.35*(q[0]-p[0]),p[1]+.35*(q[1]-p[1])),arrowprops=dict(arrowstyle='->',color=color,lw=.8))
   ax.scatter(*c['base'],marker='*',s=170,c='#efae00',edgecolors='black',zorder=9);ax.annotate('B',c['base'],xytext=(5,-14),textcoords='offset points')
   ax.scatter(*c['current'],marker='s',s=100,facecolors='none',edgecolors='black',linewidths=1.6,zorder=10);ax.annotate('S',c['current'],xytext=(5,7),textcoords='offset points')
   for field,lab,marker,col,off in [('e0','e0','D','#e06b00',(5,7)),('emin','emin','o','#007f59',(5,-13))]:
    if r[field] is not None:ax.scatter(*r[field],s=100,marker=marker,facecolors='none',edgecolors=col,lw=2,zorder=10);ax.annotate(lab,r[field],xytext=off,textcoords='offset points',color=col,fontsize=8)
   length=len(route)-1 if route else (res['status'] if res else 'not applicable')
   ax.set(aspect='equal',xlim=(-.7,W-.3),ylim=(-.7,5.7),xlabel='x',ylabel='y',title=f'{label}: {length} steps');ax.set_xticks(range(W));ax.set_yticks(range(6))
  fig.suptitle(f"{name} | G={r.get('G')}, E={r.get('E')}, R={r.get('R')} | group={r['shape_group']}\nGreen=target, blue=history, orange=deferred, dark=blocked, white=non-target; B=base, S=start",fontsize=10)
  fig.savefig(H/'figures'/f'{name}.png',dpi=150);fig.savefig(H/'figures'/f'{name}.svg');plt.close(fig)
 (H/'plot_environment.json').write_text(json.dumps(dict(matplotlib=matplotlib.__version__,python=sys.version,dependency_path=os.environ.get('SMALLGAP_PLOT_DEPS')),indent=2),encoding='utf-8')
 print('saved figures',list(dict.fromkeys(v for v in a['selected'].values() if v)))
if __name__=='__main__':main()
