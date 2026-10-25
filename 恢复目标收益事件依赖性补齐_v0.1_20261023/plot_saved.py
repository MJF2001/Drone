"""Four-cell scientific panels from saved routes, first seed fixed."""
from common import *
from PIL import Image,ImageDraw,ImageFont
def font(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def main():
 (H/'figures').mkdir(exist_ok=True);receipts=[]
 for c in read(H/'selection.json')['selected']:
  case=c['id'];seed=20261020;spec=read(H/c['spec']);proof=next(r for r in read(H/'四格路径与local机制证据.json') if r['case']==case and r['seed']==seed);g=next(r for r in read(H/'6组四格对照.json') if r['case']==case and r['seed']==seed)
  xs={}
  for arm,t in [('OFF','T0'),('ON','T1')]:xs['N_'+t]=read(H/'outputs'/f'formal_N__{case}__{seed}__{arm}.json')
  for ref in read(H/'reused_E/index.json')['references']:
   if ref['case']==case and ref['seed']==seed:xs['E_'+ref['target_label']]=read(H/ref['wrapper'])['saved_output']
  P=ps(xs['N_T0']['input']['published_targets']);HH=ps(xs['N_T0']['input']['covered']);ob=sorted(ps(xs['N_T0']['input']['free'])-ps(xs['E_T0']['input']['free']))[0]
  pic=Image.new('RGB',(2400,1500),'white');D=ImageDraw.Draw(pic);D.text((36,22),f'{case}  |  固定T0/T1的N/E四格对照  |  seed {seed}',font=font(36),fill='#183249')
  D.text((36,72),f"T0={spec['T0']}；T1={spec['T1']}。N两臂新运行，E两臂只读复用；路径与目标身份始终分开。",font=font(25),fill='#50667b')
  cols={'T0':'#147fab','T1':'#d28b22'}
  for ri,env in enumerate(('N','E')):
   inp=xs[env+'_T0']['input'];free=ps(inp['free'])
   for ci,t in enumerate(('T0','T1','local')):
    ox=30+ci*795;oy=125+ri*620;zoom=t=='local';w,h=730,465
    if not zoom:
     x=xs[env+'_'+t];m=x['views']['B']['metrics'];title=f"{env},{t}（{'新增' if env=='N' else '复用'}）原生{x['views']['A']['metrics']['length']:.0f} m"
     sub=f"直达{m['length']:.6f} m；转弯{m['turns']['total']}；末采{proof['cells'][env+'_'+t]['last_post_credit'][0]}"
    else:title=f'{env}局部原生：T0蓝 / T1橙';sub='目标不同是否真正改变后续行动，按保存路线核对'
    D.text((ox+8,oy),title,font=font(26),fill='#1e3549');D.text((ox+8,oy+37),sub,font=font(21),fill='#52697c')
    im=Image.new('RGB',(w,h),'#f9fbfe');d=ImageDraw.Draw(im)
    b=(ob[0]-4.5,ob[0]+4.5,ob[1]-4.5,ob[1]+4.5) if zoom else (-2,max(x for x,y in P|{tuple(inp['current'])})+2,-2,max(y for x,y in P|{tuple(inp['current'])})+2)
    x0,x1,y0,y1=b;scale=min((w-20)/(x1-x0),(h-20)/(y1-y0));sx=(w-scale*(x1-x0))/2;sy=(h-scale*(y1-y0))/2
    def xy(p):return sx+(p[0]-x0)*scale,h-sy-(p[1]-y0)*scale
    def rect(p,size,fill,outline=None):
     x,y=xy(p);r=size*scale/2;d.rectangle((x-r,y-r,x+r,y+r),fill=fill,outline=outline,width=1)
    for p in free:
     x,y=xy(p)
     if 0<x<w and 0<y<h:d.ellipse((x-1,y-1,x+1,y+1),fill='#e3e9ee')
    for p in P:rect(p,.4,'#98aebd' if p in HH else '#d2dce4')
    for target in (('T0','T1') if zoom else (t,)):
     path=xs[env+'_'+target]['views']['A' if zoom else 'B']['path'];d.line([xy(p) for p in path],fill=cols[target],width=3 if target=='T0' else 2,joint='curve')
    rect(ob,1,'#cb3742' if env=='E' else None,'#b65d64')
    for p,color in [(inp['current'],'#199b70'),(inp['base'],'#172d3e')]:
     x,y=xy(p);d.ellipse((x-6,y-6,x+6,y+6),fill=color,outline='white',width=2)
    if zoom:
     for key,offset in [('T0',(-170,-65)),('T1',(-170,40))]:
      x,y=xy(spec[key]);tx,ty=x+offset[0],y+offset[1];d.line((tx+70,ty+12,x,y),fill=cols[key],width=2);d.text((tx,ty),f'{key} {spec[key]}',font=font(19),fill=cols[key])
    pic.paste(im,(ox+18,oy+77));D.rectangle((ox+18,oy+77,ox+18+w,oy+77+h),outline='#c6d0d9');D.text((ox+22,oy+548),f'x∈[{x0:g},{x1:g}], y∈[{y0:g},{y1:g}] m，等比例',font=font(18),fill='#65798a')
  eff=g['effects']['post'];D.text((38,1380),'直达效应：'+ '；'.join(f"{k}={eff[k]['display']:+.9f} m" for k in ('D_N','D_E','I')),font=font(28),fill='#19384d')
  D.text((38,1422),'D<0为T0短；I=D_E−D_N。N的红框仅标新增障碍位置；E红块禁飞。灰蓝=已采H，浅灰=初始未采，绿圆=S，黑圆=基地。',font=font(22),fill='#536b7e')
  D.text((38,1458),'固定首seed示意，非真实飞行回放；所有路线合法，三seed全量保存。交互不是最优绕行代价、现场总体因果效应或新算法收益。',font=font(21),fill='#667b8c')
  p=H/'figures'/(case+'.png');pic.save(p);receipts.append({'case':case,'seed':seed,'path':str(p.relative_to(H)),'sha256':sha(p),'new_core_post_geometry_BFS':0,'sources':'four-cell source index and saved route evidence, fixed first original seed'})
 dump(H/'figure_receipts.json',receipts);print({'figures':2,'new_search_calls':0})
if __name__=='__main__':main()
