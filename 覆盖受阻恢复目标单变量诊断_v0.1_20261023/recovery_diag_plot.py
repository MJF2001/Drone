"""Scientific route evidence panels from saved first-seed results, no searches."""
from common import *
from PIL import Image,ImageDraw,ImageFont
def font(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def main():
 (H/'figures').mkdir(exist_ok=True);receipts=[]
 for c in read(H/'selection.json')['selected']:
  case=c['id'];seed=20261020;xs={a:read(H/'outputs'/f'formal__{case}__{seed}__{a}.json') for a in ('OFF','ON')};inp=xs['OFF']['input'];s=read(H/c['spec']);proof=next(x for x in read(H/'逐决策干预证明.json') if x['case']==case and x['seed']==seed);pair=next(x for x in read(H/'6对ON减OFF全指标.json') if x['case']==case and x['seed']==seed)
  pic=Image.new('RGB',(2000,1420),'white');D=ImageDraw.Draw(pic);large=c['base_id']=='large_Z'
  D.text((38,20),f"{case}  |  {'无收益：目标改变，路线相同' if large else '省路：恢复更远，完整路线更短'}",font=font(34),fill='#182d40');D.text((38,68),f'固定首seed {seed}；当前障碍E相同；目标干预OFF/ON（核心profile两臂均关闭）',font=font(23),fill='#50657a')
  ob=sorted(ps(s['source_E'] and inp['covered'])-ps(inp['free']))[0]
  def pane(ox,oy,zoom,paths):
   w,h=910,465;im=Image.new('RGB',(w,h),'#f8fbfd');d=ImageDraw.Draw(im);P,HH,F=map(ps,(inp['published_targets'],inp['covered'],inp['free']))
   bounds=(ob[0]-4.5,ob[0]+4.5,ob[1]-4.5,ob[1]+4.5) if zoom else (-2,max(x for x,y in P|{tuple(inp['current'])})+2,-2,max(y for x,y in P|{tuple(inp['current'])})+2)
   x0,x1,y0,y1=bounds;scale=min((w-24)/(x1-x0),(h-24)/(y1-y0));sx=(w-(x1-x0)*scale)/2;sy=(h-(y1-y0)*scale)/2
   def xy(p):return sx+(p[0]-x0)*scale,h-sy-(p[1]-y0)*scale
   def box(p,size,fill,outline=None):
    x,y=xy(p);a=scale*size/2;d.rectangle((x-a,y-a,x+a,y+a),fill=fill,outline=outline,width=1)
   for p in F:
    x,y=xy(p)
    if 0<x<w and 0<y<h:d.ellipse((x-1,y-1,x+1,y+1),fill='#e3e9ef')
   for p in P:box(p,.4,'#99aebd' if p in HH else '#d2dce4')
   for path,color,width in paths:
    if len(path)>1:d.line([xy(p) for p in path],fill=color,width=width,joint='curve')
   box(ob,1,'#cc3742','#8f1824')
   for p,color in [(inp['current'],'#189b71'),(inp['base'],'#172a3a')]:
    x,y=xy(p);d.ellipse((x-7,y-7,x+7,y+7),fill=color,outline='white',width=2)
   if zoom:
    for q,lab,color,offset in [(s['default_goal'],'默认目标','#cc7e17',(-170,45)),(s['alternative_goal'],'替代目标','#166cbd',(-170,-60))]:
     x,y=xy(q);tx,ty=x+offset[0],y+offset[1];d.line((tx+65,ty+15,x,y),fill=color,width=2);d.text((tx,ty),f'{lab} {q}',font=font(20),fill=color)
   pic.paste(im,(ox,oy));D.rectangle((ox,oy,ox+w,oy+h),outline='#c6d0d9',width=1);D.text((ox+8,oy+h+5),f'x∈[{x0:g},{x1:g}], y∈[{y0:g},{y1:g}] m，等比例',font=font(18),fill='#5d7182')
  for ci,arm in enumerate(('OFF','ON')):
   ox=40+ci*990;oy=120;x=xs[arm];m=x['views']['B']['metrics'];D.text((ox,oy),f"{arm}：原生 {x['views']['A']['metrics']['length']:.0f} m → 直达 {m['length']:.6f} m",font=font(27),fill='#1a3246');D.text((ox,oy+40),f"末采 {pair[arm+'_last_credit'][0]}；转弯 {m['turns']['total']}；目标 {x['native']['diagnostic']['trigger']['chosen_goal']}",font=font(22),fill='#53687a')
   pane(ox,oy+80,False,[(x['post']['vertices'],'#607a91' if arm=='OFF' else '#1388bb',3)])
  ox,oy=40,760;D.text((ox,oy),'局部原生：OFF灰，ON蓝；恢复连接仍用原几何',font=font(26),fill='#213b50');D.text((ox,oy+40),'原生衔接4→5步；途中采集任务必须计账',font=font(22),fill='#53687a');pane(ox,oy+80,True,[(xs['OFF']['views']['A']['path'],'#7d8a98',5),(xs['ON']['views']['A']['path'],'#1689bc',2)])
  ox,oy=1030,760;D.text((ox,oy),'原生完整总账（按实际trace边界，单位米）',font=font(25),fill='#213b50')
  labels=[('common_prefix','共同前缀','#b9c9d5'),('specified_recovery','这次恢复','#e2a64d'),('subsequent_coverage','后续覆盖','#369cbd'),('return_after_last_center_credit','末采后返航','#7e78a7')]
  for ai,arm in enumerate(('OFF','ON')):
   lens=proof['native_partitions'][arm]['unit_lengths'];y=oy+95+ai*140;D.text((ox,y-35),arm+'：'+ ' + '.join(str(lens[k]) for k,_,_ in labels)+f" = {sum(lens.values())}",font=font(24),fill='#284055');x=ox
   for key,label,color in labels:
    w=850*lens[key]/max(pair['OFF_raw'],pair['ON_raw']);D.rectangle((x,y,x+w,y+36),fill=color);x+=w
  D.text((ox,oy+370),'Δ：'+ ' / '.join(f'{proof["native_partition_delta"][k]:+d}' for k,_,_ in labels),font=font(27),fill='#213b50')
  for j,(_,lab,color) in enumerate(labels):x=ox+(j%2)*420;y=oy+420+(j//2)*40;D.rectangle((x,y,x+23,y+23),fill=color);D.text((x+35,y-3),lab,font=font(22),fill='#466074')
  D.text((38,1352),'灰蓝=初始已采H；浅灰=初始未采；红格=E中障碍；绿圆=快照S；黑圆=基地。所有线均取自保存结果。',font=font(22),fill='#344d61')
  D.text((38,1386),'原生分段不强行移植为直达收益分段；中点信用见证不是唯一物理入区时刻。三seed全量数值均保留。',font=font(20),fill='#607589')
  path=H/'figures'/(case+'.png');pic.save(path);receipts.append({'case':case,'seed':seed,'path':str(path.relative_to(H)),'sha256':sha(path),'OFF_source_sha256':sha(H/'outputs'/f'formal__{case}__{seed}__OFF.json'),'ON_source_sha256':sha(H/'outputs'/f'formal__{case}__{seed}__ON.json'),'no_new_core_post_geometry_BFS':True})
 dump(H/'figure_receipts.json',receipts);print({'figures':2,'new_search_calls':0})
if __name__=='__main__':main()
