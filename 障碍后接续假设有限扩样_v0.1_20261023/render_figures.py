"""Static scientific maps from saved vertices only. No route/geometry queries."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math,time
H=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
fontpath='C:/Windows/Fonts/msyh.ttc'
f20=ImageFont.truetype(fontpath,20);f17=ImageFont.truetype(fontpath,17);f14=ImageFont.truetype(fontpath,14);f26=ImageFont.truetype(fontpath,26)
COL=dict(free='#edf1f4',target='#f4d989',history='#9bd5b0',obstacle='#242a31',old='#9a75ad',OFF='#2265c6',ALT1='#b0449b',raw='#b6bec6')
def panel(im,box,c,path,title,raw=None,obstacle=None,trigger=None,p=None,old=False):
 d=ImageDraw.Draw(im);x0,y0,w,h=box;F=set(map(tuple,c['free']));P=set(map(tuple,c['published_targets']));HH=set(map(tuple,c['covered']));xmax=max(x for x,y in F);ymax=max(y for x,y in F)
 if obstacle:xmax=max(xmax,obstacle[0]);ymax=max(ymax,obstacle[1])
 s=min(12,(w-110)/(xmax+1),(h-145)/(ymax+1));ox=x0+48;oy=y0+85+ymax*s
 def xy(p):return (round(ox+p[0]*s),round(oy-p[1]*s))
 def cell(q,col):
  x,y=xy(q);r=.47*s;d.rectangle((x-r,y-r,x+r,y+r),fill=col)
 d.text((x0+14,y0+10),title,fill='#202b36',font=f20)
 a=xy((-.5,ymax+.5));b=xy((xmax+.5,-.5));d.rectangle((*a,*b),fill=COL['free'],outline='#93a3af')
 for q in sorted(P):cell(q,COL['target'])
 for q in sorted(HH):cell(q,COL['history'])
 for i in range(0,xmax+1,10):x,y=xy((i,0));d.text((x-7,b[1]+6),str(i),fill='#65717a',font=f14)
 for i in range(0,ymax+1,10):x,y=xy((0,i));d.text((x0+8,y-8),str(i),fill='#65717a',font=f14)
 def line(points,color,width,dashed=False):
  for a,b in zip(points,points[1:]):
   a,b=xy(a),xy(b)
   if dashed:
    n=max(1,math.ceil(math.dist(a,b)/6))
    for i in range(0,n,2):
     u=i/n;v=min(i+1,n)/n;d.line((a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u,a[0]+(b[0]-a[0])*v,a[1]+(b[1]-a[1])*v),fill=color,width=width)
   else:d.line((a,b),fill=color,width=width)
 if raw:line(raw,COL['raw'],1)
 if path:line(path,COL['old'] if old else COL['ALT1'] if 'ALT1' in title else COL['OFF'],2,old)
 if obstacle:
  cell(obstacle,COL['obstacle']);x,y=xy(obstacle);r=max(3,s*.28);d.line((x-r,y-r,x+r,y+r),fill='#f7f7f7',width=1);d.line((x-r,y+r,x+r,y-r),fill='#f7f7f7',width=1)
 base=xy(c['base']);d.polygon([(base[0],base[1]-7),(base[0]+7,base[1]),(base[0],base[1]+7),(base[0]-7,base[1])],fill='#173447',outline='white')
 x,y=xy(c['current']);d.ellipse((x-7,y-7,x+7,y+7),outline='#dd4935',width=3)
 if c.get('previous') is not None:d.line((xy(c['previous']),xy(c['current'])),fill='#dd4935',width=3)
 if trigger:
  for key,color,lab in [('default_goal',COL['OFF'],'0'),('alternative_goal',COL['ALT1'],'1')]:
   if trigger.get(key) is not None:
    x,y=xy(trigger[key]);d.ellipse((x-5,y-5,x+5,y+5),outline=color,width=2);d.text((x+6,y-12),lab,fill=color,font=f14)
 if p:
  x,y=xy(p);d.rectangle((x-4,y-4,x+4,y+4),outline='#d08800',width=2)
 d.text((x0+18,y0+h-34),f"F内格数={len(F)}  P={len(P)}  物理H={len(HH)}",fill='#4c5d68',font=f17)
def render():
 begin=time.perf_counter();registry=read(H/'state_registry.json');pairs={r['id']:r for r in read(H/'derived_pairs.json')};files=[]
 for row in registry:
  if row['status']!='qualified':continue
  ident=row['id'];c=read(H/row['input']);history=read(H/'history'/(ident+'.json'));off=read(H/'outputs'/(ident+'__OFF.json'));alt=read(H/'outputs'/(ident+'__ALT1.json'));p=pairs[ident];tr=off['diagnostic']['trigger']
  im=Image.new('RGB',(2340,770),'white');d=ImageDraw.Draw(im)
  d.text((24,15),f"{ident}    Δ恢复=+{p['delta_recovery']}米    Δ直达={p['delta_post_display']:+.6f}米 ({p['delta_percent']:+.3f}%)",fill='#172d40',font=f26)
  d.text((24,55),f"S={c['current']}；新障碍={row['selected_obstacle']}；默认0={tr['default_goal']}；备选1={tr['alternative_goal']}",fill='#4c5b65',font=f20)
  panel(im,(0,95,780,590),c,history['old_actual_post_suffix'],'事件状态 / 旧实际直达（障碍后非法）',obstacle=row['selected_obstacle'],trigger=tr,old=True)
  panel(im,(780,95,780,590),c,off['post']['vertices'],f"OFF 最近目标   L={p['length_OFF']:.6f}",raw=off['native']['raw']['route'],obstacle=row['selected_obstacle'],trigger=tr,p=p['H2'].get('p'))
  panel(im,(1560,95,780,590),c,alt['post']['vertices'],f"ALT1 旧计划次序备选   L={p['length_ALT1']:.6f}",raw=alt['native']['raw']['route'],obstacle=row['selected_obstacle'],trigger=tr,p=p['H2'].get('p'))
  legend=[('free','F内非目标可飞区'),('target','P待检区'),('history','H已采（含被封格仍保留）'),('obstacle','新障碍'),('raw','原生细线')]
  for i,(key,label) in enumerate(legend):x=25+i*420;d.rectangle((x,705,x+22,723),fill=COL[key],outline='#89949c');d.text((x+30,700),label,fill='#354956',font=f17)
  d.text((25,738),'红圈S / 红线真实来向；菱形基地；0/1为两个目标；黄框为首次物理分歧p。宽矩形F不是道路形状，旧直达虚线只作受阻参考。',fill='#526470',font=f17)
  dest=H/'figures'/(ident+'.png');im.save(dest);files.append(dict(id=ident,file=str(dest.relative_to(H)),size=list(im.size)))
 overview=Image.new('RGB',(2340,1490),'white');dd=ImageDraw.Draw(overview);dd.text((20,15),'六张历史准备地图：F宽矩形，P为分段待检布局；H为空、无新增障碍，线为真实旧直达',font=f26,fill='#172d40')
 for i,m in enumerate(read(H/'plan.json')['maps']):
  o=read(H/'outputs'/('history__'+m['id']+'.json'));panel(overview,((i%3)*780,75+(i//3)*690,780,680),o['input'],o['post']['vertices'],m['id']+' / history_prepare',old=True)
 overview.save(H/'figures/六图历史准备.png')
 contact=Image.new('RGB',(2340,810),'#d6dee4')
 for i,f in enumerate(files):
  im=Image.open(H/f['file']);im.thumbnail((585,260));contact.paste(im,((i%4)*585,(i//4)*270))
 contact.save(H/'figures/12例图版总览.png')
 (H/'图版索引.json').write_text(json.dumps(dict(figures=files,history_overview='figures/六图历史准备.png',contact_sheet='figures/12例图版总览.png',render_wall_seconds=time.perf_counter()-begin,source='saved inputs and vertices only',new_core=0,new_post=0,new_geometry=0,new_BFS=0),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'figures':len(files)+2,'render_seconds':time.perf_counter()-begin}))
if __name__=='__main__':render()
