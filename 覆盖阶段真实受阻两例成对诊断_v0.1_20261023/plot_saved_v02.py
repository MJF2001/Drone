"""Pillow scientific route panels from saved coordinates; no searches."""
from common import *
from PIL import Image,ImageDraw,ImageFont
FONT='C:/Windows/Fonts/msyh.ttc'
def font(n):return ImageFont.truetype(FONT,n)
COL={'B':'#147eb3','R':'#d58417','C':'#7b4faf','old':'#64748b'}
def main():
 (H/'figures').mkdir(exist_ok=True);receipts=[]
 for c in read(H/'selection.json')['selected']:
  case=c['id'];seed=20261020;N=read(H/c['N']);E=read(H/c['E']);ob=c['obstacles'][0]
  xs={b+e:read(H/'outputs'/f'formal__{case}__{seed}__{b}__{e}.json') for b in ('B','R','C') for e in ('N','E')}
  def path(b,e):return xs[b+e]['post']['vertices']
  pic=Image.new('RGB',(2200,1460),'white');D=ImageDraw.Draw(pic);tasks=len(ps(N['targets'])-ps(N['covered']))
  D.text((40,22),f'{case}    初始剩余 {tasks} 格    seed {seed}',font=font(37),fill='#192b3b')
  for i,key in enumerate(('old','BN','BE','RE','CE','zoom')):
   col,row=i%3,i//3;ox=25+col*730;oy=100+row*635;zoom=key=='zoom';w,h=650,505
   pane=Image.new('RGB',(w,h),'#fafcfe');d=ImageDraw.Draw(pane)
   P,HH,F=map(ps,(N['published_targets'],N['covered'],N['free']))
   if zoom:bounds=(ob[0]-4.5,ob[0]+4.5,ob[1]-4.5,ob[1]+4.5)
   else:bounds=(-2,max(x for x,y in P|{tuple(N['current']),tuple(N['base'])})+2,-2,max(y for x,y in P|{tuple(N['current']),tuple(N['base'])})+2)
   x0,x1,y0,y1=bounds;scale=min((w-32)/(x1-x0),(h-32)/(y1-y0));sx=(w-(x1-x0)*scale)/2;sy=(h-(y1-y0)*scale)/2
   def xy(p):return (sx+(p[0]-x0)*scale,h-sy-(p[1]-y0)*scale)
   def rect(p,size,fill,outline=None):
    x,y=xy(p);r=size*scale/2;d.rectangle((x-r,y-r,x+r,y+r),fill=fill,outline=outline,width=1)
   if zoom:
    for x in range(int(x0),int(x1)+1):d.line((xy((x,y0)),xy((x,y1))),fill='#e4e8ec')
    for y in range(int(y0),int(y1)+1):d.line((xy((x0,y)),xy((x1,y))),fill='#e4e8ec')
   for p in F:
    x,y=xy(p)
    if 0<=x<w and 0<=y<h:d.ellipse((x-1,y-1,x+1,y+1),fill='#e4e9ee')
   for p in P-HH:rect(p,.32 if zoom else .45,'#c6d2dc')
   for p in HH:rect(p,.32 if zoom else .45,'#91a8ba')
   if zoom:
    for p in P-HH:rect(p,.4,None,'#aeb9c4')
   def line(p,color,width=3):
    if len(p)>1:d.line([xy(z) for z in p],fill=color,width=width,joint='curve')
   if key=='old':
    line(N['old_route'],COL['old']);cert=read(H/c['certificate'])
    for z in cert['strict_coverage_blockages']:line(N['old_route'][z['edge']:z['edge']+2],'#f2323d',5)
    head='旧后缀：红格使两条边失效';sub='事件在当前快照公开，后缀尚未执行'
   elif zoom:
    line(path('B','N'),COL['old'],3);line(path('B','E'),COL['B'],4);line(path('R','E'),COL['R'],3)
    head='局部：B_N灰 / B_E蓝 / R_E橙';sub='中心小框为0.4 m开采集区（边界不计）'
   else:
    b,e=key;line(path(b,e),COL[b]);v=xs[key]['views']['C' if b=='C' else 'B']['metrics']
    head={'BN':'B：无新增障碍','BE':'B：新障碍后重规划','RE':'R：仅修复旧失效连接','CE':'C：P2有限流程外部参照'}[key];sub=f"直达 {v['length']:.6f} m；转弯 {v['turns']['total']}"
   # On N panels red is a location reference, not a forbidden cell in N.
   rect(ob,1,'#cd3540','#921e27')
   for p,color,r in [(N['current'],'#14976c',7),(N['base'],'#142a3a',7)]:
    x,y=xy(p);d.ellipse((x-r,y-r,x+r,y+r),fill=color,outline='white',width=2)
   if zoom:
    a,b=[xs['B'+e]['native']['raw']['trace'] for e in ('N','E')];k=next(j for j in range(min(len(a),len(b))) if a[j]!=b[j])
    for event,lab,color,offset in [(a[k],'N目标',COL['old'],(-155,-45)),(b[k],'E目标',COL['B'],(-155,35))]:
     q=event['goal'];x,y=xy(q);tx,ty=x+offset[0],y+offset[1];d.line((tx+60,ty+15,x,y),fill=color,width=2);d.text((tx,ty),f'{lab} {q}',font=font(19),fill=color)
   D.text((ox+12,oy),head,font=font(26),fill='#1b2b3c');D.text((ox+12,oy+36),sub,font=font(21),fill='#43566b');pic.paste(pane,(ox+35,oy+80));D.rectangle((ox+35,oy+80,ox+35+w,oy+80+h),outline='#bbc6d1',width=1)
   D.text((ox+42,oy+588),f'x∈[{x0:g},{x1:g}], y∈[{y0:g},{y1:g}] m；等比例',font=font(18),fill='#536677')
  D.text((38,1380),'浅灰=初始未采；灰蓝=已采H；绿圆=当前位置S；黑圆=基地；红格=N中仅位置参照、E中禁飞障碍。',font=font(23),fill='#25384a')
  D.text((38,1414),'保存路线示意，非真实飞行回放。固定展示第一个原seed；三seed全量结果见配对表。',font=font(22),fill='#526477')
  p=H/'figures'/(case+'.png');pic.save(p)
  receipts.append({'case':case,'seed':seed,'figure':str(p.relative_to(H)),'sha256':sha(p),'sources':{b+e:sha(H/'outputs'/f'formal__{case}__{seed}__{b}__{e}.json') for b in ('B','R','C') for e in ('N','E')},'export_version':2,'selection':'fixed first original seed, not selected by outcome','new_geometry_core_R_post_BFS':0})
 dump(H/'figure_receipts.json',receipts);print({'figures':len(receipts),'new_search_calls':0})
if __name__=='__main__':main()
