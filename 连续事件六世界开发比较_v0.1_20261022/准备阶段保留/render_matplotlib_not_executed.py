"""Six fixed scientific figures: all inputs/events and saved actual paths only."""
from util import *
def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.collections import LineCollection
    import numpy as np
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
    worlds=read(H/'worlds.json');metadata=read(H/'world_metadata.json')
    for wid,w in worlds.items():
        fig,axes=plt.subplots(1,2,figsize=(13,6),constrained_layout=True);p0=w['published'];A=w['events'][0]['add_targets'];B=w['events'][1]['block'];free=w['free'];maxx=max(x for x,y in free);maxy=max(y for x,y in free)
        for ax,method in zip(axes,('PPCPP','P2_MULTI')):
            file=H/'sessions'/(wid+'_'+method+'.json');s=read(file)['sessions'][method] if file.exists() else None
            ax.add_patch(Rectangle((-.5,-.5),maxx+1,maxy+1,facecolor='#f4f6f8',edgecolor='#9aa0a6',lw=.8,label='F0 (all cells inside)'))
            ax.scatter(*zip(*p0),s=18,marker='s',color='#4c91cf',label='Initial targets',zorder=2)
            ax.scatter(*zip(*A),s=23,marker='s',facecolors='#ffcf80',edgecolors='#b66800',linewidths=.5,label='Event1: added tasks',zorder=3)
            ax.scatter(*zip(*B),s=32,marker='s',color='#262626',label='Event2: blocked',zorder=6)
            ax.scatter(*w['base'],marker='*',s=110,color='#d83432',edgecolor='white',lw=.5,label='Start/base',zorder=7)
            if s:
                moves=[a for a in s['actions'] if a['kind']=='move'];route=[w['start']]+[a['end'] for a in moves]
                if moves:
                    segments=np.array(list(zip(route,route[1:])));lc=LineCollection(segments,cmap='viridis',linewidths=1.1,alpha=.9,zorder=4);lc.set_array(np.array([a['tick'] for a in moves]));lc.set_clim(0,max(1,s['summary']['finish_tick']));ax.add_collection(lc)
                    for i in range(0,len(moves),max(1,len(moves)//14)):
                        a,b=route[i:i+2];ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='->',color='#52366d',lw=.8),zorder=5)
                for e in w['events']:
                    frame=next((v for v in s['frames'] if v['tick']==e['tick']),None)
                    if frame:
                        cur=frame['before']['current'];ax.scatter(*cur,s=75,facecolors='none',edgecolors='#e24a33',marker='o',lw=1.4,zorder=8);ax.annotate('t='+str(e['tick']),cur,xytext=(4,5),textcoords='offset points',fontsize=8,color='#c02716')
                q=s['summary'];end=q['current'];ax.scatter(*end,marker='x' if q['status']!='success' else 'o',s=60,color='#c02716',zorder=8)
                title=f"{method}: {q['status']}\nactual M={q['M']}, tick={q['finish_tick']}, H/U/D={len(q['H'])}/{len(q['U'])}/{len(q['D'])}"
            else:title=method+': NOT RUN (batch stop)'
            ax.set(title=title,xlim=(-1,maxx+1),ylim=(-1,maxy+1),xlabel='Grid x',ylabel='Grid y');ax.set_aspect('equal');ax.grid(alpha=.15);ax.legend(loc='upper right',fontsize=7)
        m=metadata[wid];fig.suptitle(f"DEVELOPMENT {wid} | L={m['L']}, width={m['w']} | events t={w['events'][0]['tick']}, {w['events'][1]['tick']}\nFull F0 shown; colored segments are actual movements; discarded plans are not drawn",fontsize=12)
        for suffix in ('png','svg'):fig.savefig(H/'figures'/(wid+'.'+suffix),dpi=150)
        plt.close(fig)
    # Overview for visual quality check, all six worlds remain separately saved.
    from PIL import Image,ImageOps,ImageDraw
    thumbs=[]
    for wid in worlds:
        im=Image.open(H/'figures'/(wid+'.png')).convert('RGB');im.thumbnail((780,390));thumbs.append(im)
    canvas=Image.new('RGB',(1560,1170),'white')
    for i,im in enumerate(thumbs):canvas.paste(im,((i%2)*780,(i//2)*390))
    canvas.save(H/'figures'/'全部六世界预览.png');print('Saved all6 worlds, both actual trajectories; no new planning/graph calls',flush=True)
if __name__=='__main__':main()
