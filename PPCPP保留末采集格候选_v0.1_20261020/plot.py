import os,sys,json
from pathlib import Path
if os.environ.get('SMALLGAP_PLOT_DEPS'):sys.path.insert(0,os.environ['SMALLGAP_PLOT_DEPS'])
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 a=read(H/'analysis.json');(H/'figures').mkdir(exist_ok=True)
 for ident in dict.fromkeys(v for v in a['selected'].values() if v):
  row=next(r for r in a['states'] if r['id']==ident);c=read(R/row['input']);raw=read(H/'execution'/f'{ident}__r0__LAST.json')['raw'];p0=raw['branches']['P0'];p1=raw['branches'].get('P1');folder=R/('PPCPP结束位置跨几何验证_v0.1_20261020' if row['batch']=='main36' else 'PPCPP小图最优差距诊断_v0.2_20261020');label='A' if row['batch']=='main36' else 'global';opt=read(folder/'exact'/row['name']/f'{label}.json')
  panels=[('P0 original',p0,'#2060ac'),('P1 '+('selected' if raw['selected']=='P1' else 'rejected'),p1,'#7c4594'),('Global shortest reference',opt,'#b23b31')];fig,axes=plt.subplots(1,3,figsize=(16,5.7),layout='constrained');free=set(map(tuple,c['free']));t=set(map(tuple,c['targets']));hist=set(map(tuple,c['covered']));defer=set(map(tuple,c['deferred_targets']));W=max(x for x,y in free)+1
  for ax,(name,result,color) in zip(axes,panels):
   for x in range(W):
    for y in range(6):
     p=x,y;fill='#d5ebcb' if p in t else '#fafafa'
     if p in hist:fill='#a9c4dd'
     if p not in free:fill='#efb65b' if p in defer else '#555555'
     ax.add_patch(Rectangle((x-.5,y-.5),1,1,facecolor=fill,edgecolor='#999',lw=.6))
     if p not in free:ax.text(x,y,'X',ha='center',va='center')
   route=result['route'] if result else []
   if route:
    ax.plot([p[0] for p in route],[p[1] for p in route],'-o',color=color,ms=3,lw=1.6,alpha=.8)
    for p,q in zip(route,route[1:]):ax.annotate('',xy=(p[0]+.7*(q[0]-p[0]),p[1]+.7*(q[1]-p[1])),xytext=(p[0]+.35*(q[0]-p[0]),p[1]+.35*(q[1]-p[1])),arrowprops=dict(arrowstyle='->',color=color,lw=.9))
   ax.scatter(*c['base'],marker='*',s=160,c='#efae00',edgecolors='black',zorder=9);ax.annotate('B',c['base'],xytext=(5,-14),textcoords='offset points')
   ax.scatter(*c['current'],marker='s',s=100,facecolors='none',edgecolors='black',lw=1.8,zorder=10);ax.annotate('S',c['current'],xytext=(5,7),textcoords='offset points')
   if row['e']:
    ax.scatter(*row['e'],marker='D',s=100,facecolors='none',edgecolors='#007f59',lw=2,zorder=10);ax.annotate('reserved e',row['e'],xytext=(5,8),textcoords='offset points',color='#007f59',fontsize=8)
   ax.set(aspect='equal',xlim=(-.7,W-.3),ylim=(-.7,5.7),xlabel='x',ylabel='y',title=f'{name}: {len(route)-1 if route else "infeasible"} steps');ax.set_xticks(range(W));ax.set_yticks(range(6))
  fig.suptitle(f"{ident} | final={raw['selected']}, saved={row['saved']}, remaining gap={row['final_gap']}\nGreen=target, blue=history, white=non-target, orange=deferred, dark=blocked; B=base, S=start; e remains a mandatory target",fontsize=10)
  fig.savefig(H/'figures'/f'{ident}.png',dpi=150);fig.savefig(H/'figures'/f'{ident}.svg');plt.close(fig)
 (H/'plot_environment.json').write_text(json.dumps(dict(matplotlib=matplotlib.__version__,python=sys.version,dependency=os.environ.get('SMALLGAP_PLOT_DEPS')),indent=2),encoding='utf-8');print('figures saved')
if __name__=='__main__':main()
