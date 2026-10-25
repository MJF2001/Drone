"""Standalone matplotlib rendering; never calls planners or imports experiment common."""
import json,sys,os
from pathlib import Path
if os.environ.get('SMALLGAP_PLOT_DEPS'):sys.path.insert(0,os.environ['SMALLGAP_PLOT_DEPS'])
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 a=read(H/'analysis.json');ids=list(dict.fromkeys(v for v in a['selected'].values() if v));(H/'figures').mkdir(exist_ok=True)
 for name in ids:
  c=read(H/'inputs'/f'{name}.json');raw=read(H/'execution'/f'{name}.json')['raw'];opt=read(H/'exact'/name/'global.json');mapping=read(H/'exact'/name/'mapping.json');free=set(map(tuple,c['free']));targets=set(map(tuple,c['targets']));hist=set(map(tuple,c['covered']));deferred=set(map(tuple,c['deferred_targets']));pub=set(map(tuple,c['published_targets']));row=next(r for r in a['states'] if r['id']==name)
  fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
  for ax,r,label,color in [(axes[0],raw,'PPCPP','#2060ac'),(axes[1],opt,'Shortest witness','#bd3b31')]:
   for x in range(max(p[0] for p in free)+1):
    for y in range(6):
     p=x,y;fill='#cde8cb' if p in targets else '#fafafa'
     if p in hist:fill='#a6bfd7'
     if p not in free:fill='#f0b44f' if p in deferred else '#484848'
     ax.add_patch(Rectangle((x-.5,y-.5),1,1,facecolor=fill,edgecolor='#999',lw=.6))
     if p not in free:ax.text(x,y,'X',ha='center',va='center',color='black')
   route=r['route'];xx=[p[0] for p in route];yy=[p[1] for p in route];ax.plot(xx,yy,'o-',color=color,lw=1.8,ms=3,alpha=.8)
   for i,(p,q) in enumerate(zip(route,route[1:])):
    ax.annotate('',xy=(p[0]+.65*(q[0]-p[0]),p[1]+.65*(q[1]-p[1])),xytext=(p[0]+.35*(q[0]-p[0]),p[1]+.35*(q[1]-p[1])),arrowprops=dict(arrowstyle='->',color=color,lw=1))
   ax.scatter(*c['base'],marker='*',s=180,c='#efae00',edgecolors='black',zorder=8);ax.annotate('B',c['base'],xytext=(5,-15),textcoords='offset points')
   ax.scatter(*c['current'],marker='s',s=90,facecolors='none',edgecolors='black',linewidths=2,zorder=9);ax.annotate('S',c['current'],xytext=(5,7),textcoords='offset points')
   if label=='PPCPP':
    for cp in mapping['checkpoints']:
     if cp['index'] is not None:
      point=route[cp['index']];ax.annotate(f"t={cp['index']}",point,xytext=(5,8),textcoords='offset points')
   ax.set(aspect='equal',xlim=(-.65,max(p[0] for p in free)+.65),ylim=(-.65,5.65),xlabel='x',ylabel='y',title=f'{label}: {len(route)-1} steps')
   ax.set_xticks(range(max(p[0] for p in free)+1));ax.set_yticks(range(6))
  fig.suptitle(f"{name} | G={row['G']} | checkpoints: "+(', '.join(str(q['index']) for q in mapping['checkpoints'] if q['index'] is not None) or 'absent')+'\nGreen=active target, blue=history, white=non-target, orange=deferred, dark=blocked; B=base, S=start',fontsize=10)
  fig.savefig(H/'figures'/f'{name}.png',dpi=160);fig.savefig(H/'figures'/f'{name}.svg');plt.close(fig)
 print('rendered',ids)
if __name__=='__main__':main()
