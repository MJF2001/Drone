"""Saved-route figures only; no planner or exact imports."""
import os,sys,json
from pathlib import Path
if os.environ.get('SMALLGAP_PLOT_DEPS'):sys.path.insert(0,os.environ['SMALLGAP_PLOT_DEPS'])
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 a=read(H/'analysis.json');(H/'figures').mkdir(exist_ok=True)
 for name in dict.fromkeys(v for v in a['selected'].values() if v):
  c=read(H/'inputs'/f'{name}.json');r=next(x for x in a['states'] if x['id']==name);raw=read(H/'execution'/f'{name}__r0__LAST.json')['raw'];free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));hist=set(map(tuple,c['covered']));defer=set(map(tuple,c['deferred_targets']));W=max(x for x,y in free)+1;Y=max(y for x,y in free)+1
  canvas=np.zeros((Y,W),dtype=int)
  for x in range(W):
   for y in range(Y):
    p=x,y;canvas[y,x]=3 if p not in free else 2 if p in hist else 1 if p in targets else 0
    if p in defer:canvas[y,x]=4
  fig,axes=plt.subplots(1,2,figsize=(15,7.5),layout='constrained')
  for ax,b,title,color in [(axes[0],raw['branches']['P0'],'P0 '+('selected' if raw['selected']=='P0' else 'original'),'#2060ac'),(axes[1],raw['branches'].get('P1'),'P1 '+('selected' if raw['selected']=='P1' else 'rejected/tied'),'#91418e')]:
   ax.imshow(canvas,origin='lower',interpolation='nearest',cmap=ListedColormap(['#fafafa','#d5ebcb','#acc7df','#555555','#efb35c']),vmin=0,vmax=4,extent=(-.5,W-.5,-.5,Y-.5))
   path=b['route'] if b and b['route'] else b.get('diagnostic_route',[]) if b else []
   if path:
    ax.plot([p[0] for p in path],[p[1] for p in path],'-',color=color,lw=1,alpha=.8)
    for p,q in zip(path,path[1:]):ax.annotate('',xy=(p[0]+.7*(q[0]-p[0]),p[1]+.7*(q[1]-p[1])),xytext=(p[0]+.35*(q[0]-p[0]),p[1]+.35*(q[1]-p[1])),arrowprops=dict(arrowstyle='->',color=color,lw=.65,mutation_scale=5))
   ax.scatter(*c['base'],marker='*',s=110,c='#efae00',edgecolors='black',zorder=8);ax.annotate('B',c['base'],xytext=(3,5),textcoords='offset points',fontsize=8)
   ax.scatter(*c['current'],marker='s',s=75,facecolors='none',edgecolors='black',lw=1.5,zorder=9);ax.annotate('S',c['current'],xytext=(4,5),textcoords='offset points',fontsize=8)
   if r.get('e'):ax.scatter(*r['e'],marker='D',s=75,facecolors='none',edgecolors='#ce6400',lw=1.8,zorder=10);ax.annotate('e',r['e'],xytext=(4,-12),textcoords='offset points',fontsize=8,color='#ad5000')
   for x,y in hist-free:ax.text(x,y,'H/X',fontsize=5,ha='center',va='center',color='white')
   length=len(b['route'])-1 if b and b['route'] else b['status'] if b else 'absent';ax.set(title=f'{title}: {length} steps',xlabel='x',ylabel='y',aspect='equal',xlim=(-.6,W-.4),ylim=(-.6,Y-.4));ax.set_xticks(np.arange(-.5,W,1),minor=True);ax.set_yticks(np.arange(-.5,Y,1),minor=True);ax.grid(which='minor',lw=.25,color='#aaa');ax.tick_params(which='minor',bottom=False,left=False)
  fig.suptitle(f"{name} | final={raw['selected']}, saved={r.get('saved')} ({r.get('relative_saved',0)*100:.4f}%)\nFull public flight domain; green=target, blue=history, orange=deferred, dark=blocked; B=base, S=current, e=strategically reserved target",fontsize=10)
  fig.savefig(H/'figures'/f'{name}.png',dpi=150);fig.savefig(H/'figures'/f'{name}.svg');plt.close(fig)
 (H/'plot_environment.json').write_text(json.dumps(dict(matplotlib=matplotlib.__version__,python=sys.version,dependencies=os.environ.get('SMALLGAP_PLOT_DEPS')),indent=2),encoding='utf-8');print('saved fixed figures')
if __name__=='__main__':main()
