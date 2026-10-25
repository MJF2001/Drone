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
 start=time.perf_counter();reg=read(H/'state_registry.json');pairs={p['id']:p for p in read(H/'derived_pairs.json')};sources={s['id']:s for s in read(H/'source_bindings.json')};files=[]
 for r in reg:
  ident=r['id'];src=sources[r['origin']]
  if ident in pairs:
   p=pairs[ident];off=read(H/'outputs'/(ident+'__OFF.json'));alt=read(H/'outputs'/(ident+'__ALT1.json'));c=off['input'];hist=read(H/'history'/(ident+'.json'));tr=off['diagnostic']['trigger'];im=Image.new('RGB',(2340,770),'white');d=ImageDraw.Draw(im)
   d.text((24,15),f"{ident}   Δ恢复=+{p['delta_recovery']}米   Δ直达={p['delta_post_display']:+.6f}米",font=f26,fill='#172d40')
   d.text((24,55),f"新障碍={r['selected_obstacle']}；S={c['current']}；H/U={len(r['H'])}/{len(r['U0'])}；q0={tr['default_goal']}→q1={tr['alternative_goal']}",font=f20,fill='#4c5b65')
   panel(im,(0,95,780,590),c,hist['old_actual_post_suffix'],'新E与旧实际post（已受阻）',obstacle=r['selected_obstacle'],trigger=tr,old=True)
   panel(im,(780,95,780,590),c,off['post']['vertices'],f"OFF   L={p['length_OFF']:.6f}",raw=off['native']['raw']['route'],obstacle=r['selected_obstacle'],trigger=tr,p=p['H2'].get('p'))
   panel(im,(1560,95,780,590),c,alt['post']['vertices'],f"ALT1   L={p['length_ALT1']:.6f}",raw=alt['native']['raw']['route'],obstacle=r['selected_obstacle'],trigger=tr,p=p['H2'].get('p'))
   for j,(key,label) in enumerate([('free','F内非目标可飞区'),('target','P待检区'),('history','H物理已采'),('obstacle','本变体新障碍'),('raw','原生细线')]):
    x=25+j*420;d.rectangle((x,705,x+22,723),fill=COL[key]);d.text((x+30,700),label,font=f17,fill='#354956')
   d.text((25,738),'红圈S/红线真实来向；菱形基地；0/1为目标；彩线公共直达。B变体责任与起点联合变化，跨进度绝对长度不作改善量。',font=f17,fill='#526470')
  else:
   c=read(Path(src['old_input']));hist=read(Path(src['history_output']));cut=r.get('cut',src['old_registry']['cut']);rawidx=r.get('source_raw_index',src['old_registry']['source_raw_index'])
   c.update(current=r.get('current',c['current']),previous=r.get('previous',c['previous']),covered=r.get('H',c['covered']),old_route=hist['native']['raw']['route'][rawidx:])
   im=Image.new('RGB',(1100,790),'white');d=ImageDraw.Draw(im);d.text((20,15),ident+'：未运行响应',font=f26,fill='#172d40');d.text((20,55),'不适用/缺槽：'+r['status'],font=f20,fill='#a33c35')
   panel(im,(0,100,1080,610),c,hist['post']['vertices'][cut:],'保存计划与拟议切点定位；非新算法输出',obstacle=src['old_obstacle'],old=True)
   d.text((20,724),'浅灰F内非目标区；黄P；绿H；黑为原固定b0参考。遮挡未采任务不删除责任。',font=f17,fill='#43586a');d.text((20,752),'A缺槽图只显示原位置参考；B图显示固定新进度。均不能当作持平或合法响应结果。',font=f17,fill='#43586a')
  pth=H/'figures'/(ident+'.png');im.save(pth);files.append(dict(id=ident,file=str(pth.relative_to(H)),status=r['status'],dimensions=list(im.size)))
 original=[]
 for src in sources.values():
  p=Path(read(H/'plan.json')['old_package'])/'figures'/(src['id']+'.png');dest=H/'figures'/('origin__'+src['id']+'.png');dest.write_bytes(p.read_bytes());original.append(dict(id=src['id'],file=str(dest.relative_to(H)),scope='unchanged old reference image, not a new run'))
 contact=Image.new('RGB',(2340,900),'#d6dee4')
 for i,f in enumerate(files):
  im=Image.open(H/f['file']);im.thumbnail((585,290));contact.paste(im,((i%4)*585,(i//4)*300))
 contact.save(H/'figures/十二槽图版总览.png');(H/'图版索引.json').write_text(json.dumps(dict(figures=files,old_reference_images=original,contact_sheet='figures/十二槽图版总览.png',render_wall_seconds=time.perf_counter()-start,new_core=0,new_post=0,new_geometry=0,new_BFS=0),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(new_slot_images=len(files),copied_reference_images=3,seconds=time.perf_counter()-start)))
if __name__=='__main__':render()
