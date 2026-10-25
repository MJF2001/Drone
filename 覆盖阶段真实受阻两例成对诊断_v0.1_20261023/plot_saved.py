"""Scientific static figures from saved paths only. No geometric search."""
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.font_manager import FontProperties
font=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
plt.rcParams['font.family']=font.get_name();plt.rcParams['axes.unicode_minus']=False
COL={'B':'#147eb3','R':'#dc8b20','C':'#7b4faf','old':'#64748b'}
def title(ax,t):ax.set_title(t,fontproperties=font,fontsize=12,pad=10)
def main():
 (H/'figures').mkdir(exist_ok=True);receipts=[]
 for c in read(H/'selection.json')['selected']:
  case=c['id'];seed=20261020;N=read(H/c['N']);E=read(H/c['E']);ob=c['obstacles'][0]
  def out(b,e):return read(H/'outputs'/f'formal__{case}__{seed}__{b}__{e}.json')
  xs={b+e:out(b,e) for b in ('B','R','C') for e in ('N','E')}
  def path(b,e):return xs[b+e]['post']['vertices']
  def base(ax,zoom=False):
   F=ps(N['free']);P=ps(N['published_targets']);HH=ps(N['covered'])
   ax.set_aspect('equal');ax.set_facecolor('#fafcfe')
   pp=sorted(P-HH);hh=sorted(HH)
   ax.scatter(*zip(*sorted(F)),s=1,c='#e5eaf0',zorder=0)
   if pp:ax.scatter(*zip(*pp),s=9 if not zoom else 30,c='#c4cfdb',marker='s',zorder=1)
   if hh:ax.scatter(*zip(*hh),s=8 if not zoom else 28,c='#92a7bb',marker='s',zorder=1)
   ax.add_patch(Rectangle((ob[0]-.5,ob[1]-.5),1,1,facecolor='#c92f38',edgecolor='#8d1820',lw=1,zorder=5))
   ax.scatter(*N['current'],s=65,c='#16996e',marker='o',edgecolors='white',zorder=8)
   ax.scatter(*N['base'],s=95,c='#1c2938',marker='*',zorder=8)
   if zoom:
    ax.set_xlim(ob[0]-4.5,ob[0]+4.5);ax.set_ylim(ob[1]-4.5,ob[1]+4.5)
    for p in pp:
     if abs(p[0]-ob[0])<5 and abs(p[1]-ob[1])<5:ax.add_patch(Rectangle((p[0]-.2,p[1]-.2),.4,.4,facecolor='none',edgecolor='#afb9c4',lw=.6,zorder=2))
   else:
    maxx=max(p[0] for p in P|{tuple(N['current']),tuple(N['base'])});maxy=max(p[1] for p in P|{tuple(N['current']),tuple(N['base'])});ax.set_xlim(-2,maxx+2);ax.set_ylim(-2,maxy+2)
   ax.grid(alpha=.12);ax.tick_params(labelsize=8);ax.set_xlabel('x / m',fontsize=9);ax.set_ylabel('y / m',fontsize=9)
  def line(ax,p,color,ls='-',lw=1.6,alpha=.9,label=None):
   ax.plot([z[0] for z in p],[z[1] for z in p],c=color,ls=ls,lw=lw,alpha=alpha,zorder=4,label=label)
  fig,axes=plt.subplots(2,3,figsize=(17,10.3),layout='constrained')
  tasks=len(ps(N['targets'])-ps(N['covered']));fig.suptitle(f"{case}  |  初始剩余 {tasks} 格  |  seed {seed}",fontproperties=font,fontsize=18)
  ax=axes[0,0];base(ax);line(ax,N['old_route'],COL['old']);title(ax,'旧后缀：红格在事件后成为障碍')
  # Certificates locate failed edges; no fresh geometry queries.
  cert=read(H/c['certificate']);edges=[z['edge'] for z in cert['strict_coverage_blockages']]
  for k in edges:line(ax,N['old_route'][k:k+2],'#f52939',lw=3)
  for ax,b,e,label in [(axes[0,1],'B','N','B 无新增障碍'),(axes[0,2],'B','E','B 新障碍后重规划'),(axes[1,0],'R','E','R 仅修复失效连接'),(axes[1,1],'C','E','C 冻结P2外部参照')]:
   base(ax);line(ax,path(b,e),COL[b]);v=xs[b+e]['views']['C' if b=='C' else 'B']['metrics'];title(ax,f"{label}\n直达 {v['length']:.6f} m；转弯 {v['turns']['total']}")
  ax=axes[1,2];base(ax,True);line(ax,path('B','N'),COL['old'],ls='--',lw=1.5,label='B_N');line(ax,path('B','E'),COL['B'],lw=2,label='B_E');line(ax,path('R','E'),COL['R'],lw=1.7,label='R_E')
  title(ax,'局部：格心顺序与连接均有变化');ax.legend(fontsize=9,loc='lower right')
  # Local first changed recovery goals are actual saved trace fields.
  a,b=[xs['B'+e]['native']['raw']['trace'] for e in ('N','E')];k=next(i for i in range(min(len(a),len(b))) if a[i]!=b[i])
  for event,dy,col,lab in [(a[k],1.1,COL['old'],'N目标'),(b[k],-1.1,COL['B'],'E目标')]:
   q=event['goal'];ax.annotate(f'{lab} {q}',q,xytext=(q[0]-2.3,q[1]+dy),fontsize=9,color=col,fontproperties=font,arrowprops={'arrowstyle':'->','color':col},zorder=10)
  fig.text(.5,.005,'灰蓝方格=已采历史；浅灰=初始未采任务；红方块=本轮新障碍；绿圆=快照S；黑星=基地。线为保存路线，非真实飞行回放。局部小框=中心0.4m开采集区。',ha='center',fontproperties=font,fontsize=10)
  p=H/'figures'/(case+'.png');fig.savefig(p,dpi=150,bbox_inches='tight');plt.close(fig)
  receipts.append({'case':case,'seed':seed,'figure':str(p.relative_to(H)),'sha256':sha(p),'sources':{b+e:sha(H/'outputs'/f'formal__{case}__{seed}__{b}__{e}.json') for b in ('B','R','C') for e in ('N','E')},'selection':'predefined first original seed, no outcome selection; all 3 seeds numeric outputs retained','new_geometry_core_R_post_BFS':0})
 dump(H/'figure_receipts.json',receipts);print({'figures':len(receipts),'new_search_calls':0})
if __name__=='__main__':main()
