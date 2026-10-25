"""Static research diagrams from saved integer-coordinate routes only."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,time,hashlib
H=Path(__file__).resolve().parent;ROOT=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc',n)
F18=font(18);F20=font(20);F24=font(24,True);F30=font(30,True)
def txt(d,xy,s,f=F18,c='#243344'):d.text(xy,str(s),font=f,fill=c)
def save(im,name):
 p=H/'figures'/name;im.save(p);return dict(file=str(p.relative_to(H)),width=im.width,height=im.height,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def chart(rows):
 im=Image.new('RGB',(1640,1260),'white');d=ImageDraw.Draw(im);txt(d,(30,20),'固定19对：估计与真实的 q1 − q0 距离差（米）',F30);txt(d,(30,68),'负值表示 q1 更短；基础与变体分隔显示，不汇总总体胜率。蓝色=真实，橙色=估计。',F20)
 left,right=560,1500;lo,hi=-35,35;xx=lambda v:left+(v-lo)/(hi-lo)*(right-left)
 for v in range(-30,31,10):d.line((xx(v),120,xx(v),1170),fill='#c6ced8' if v else '#435369',width=2 if not v else 1);txt(d,(xx(v)-12,1180),v,F20)
 for i,r in enumerate(rows):
  y=145+i*51+(24 if i>=12 else 0)
  if i==12:d.line((25,y-36,1600,y-36),fill='#42566d',width=2);txt(d,(30,y-31),'受控变体7对（相关已见案例）',font(14),c='#63758b')
  label=r['key'].replace('base__','基础 ').replace('variants__','变体 ');txt(d,(30,y-12),label,F18)
  a,b=r['delta_true'],r['delta_hat'];d.line((xx(a),y,xx(b),y),fill='#adb9c9',width=3)
  d.ellipse((xx(a)-6,y-6,xx(a)+6,y+6),fill='#2563ae');d.rectangle((xx(b)-5,y-5,xx(b)+5,y+5),fill='#da8517')
  # Put both numerical labels on stable subrows to preserve exact ties.
  txt(d,(xx(a)-34,y+7),f'{a:.2f}',font(14),c='#17549c');txt(d,(xx(b)-34,y-25),f'{b:.2f}',font(14),c='#a65d00')
 txt(d,(30,1220),'I主正例与T反例均发生符号翻转；等长案例也有预测偏差。显示小数不决定胜负。',F20)
 return save(im,'19对估计与真实差.png')
def routefigure(key,title,name):
 rows=read(H/'joined_results.json');r=next(x for x in rows if x['key']==key);crops={a:read(H/'crops'/(key+'__'+a+'.json')) for a in ('OFF','ALT1')};out={a:read(H/'outputs'/(key+'__'+a+'.json')) for a in ('OFF','ALT1')};old={a:read(r['arms'][a]['source']) for a in ('OFF','ALT1')};c=crops['OFF']['event'];free=set(map(tuple,c['free']));P=set(map(tuple,c['published_targets']));HH=set(map(tuple,c['covered']));pending=set(map(tuple,crops['OFF']['choice_state']['pending']));xmax=max(x for x,y in free);ymax=max(y for x,y in free)
 im=Image.new('RGB',(1700,1330),'white');d=ImageDraw.Draw(im);txt(d,(30,18),title,F30);txt(d,(30,63),f"估计差 {r['delta_hat']:+.3f} 米；真实差 {r['delta_true']:+.3f} 米。每一幅都从同一事件初始H独立评价。",F20)
 for row,arm in enumerate(('OFF','ALT1')):
  for col,mode in enumerate(('actual','estimate')):
   ox=35+col*835;oy=110+row*555;scale=min(735/(xmax+2),430/(ymax+2));mx=ox+45;my=oy+490
   def point(p):return mx+p[0]*scale,my-p[1]*scale
   estimate=mode=='estimate';o=out[arm] if estimate else old[arm];raw=o['raw']['route'] if estimate else o['native']['raw']['route'];post=o['post']['vertices'];length=r['arms'][arm]['Jhat_post' if estimate else 'J_true'];txt(d,(ox,oy),f"{'q0 OFF' if arm=='OFF' else 'q1 ALT'}  {'旧序替代估计' if estimate else '保存真实PPCPP'}",F24);txt(d,(ox,oy+36),f"直达 {length:.3f} 米，原生 {len(raw)-1} 步",F18)
   for x in range(xmax+1):
    for y in range(ymax+1):
     p=(x,y);px,py=point(p);r0=max(2,scale*.34);color='#f2f3f5'
     if p in P:color='#ffe3a1' if p in pending else '#b4d7d3' if p not in HH else '#c3e4bf'
     if p not in free:color='#242b32'
     d.rectangle((px-r0,py-r0,px+r0,py+r0),fill=color)
   d.line([point(p) for p in raw],fill='#c4cad3',width=2)
   d.line([point(p) for p in post],fill='#8055a5' if estimate else '#2866a8',width=3)
   finite=crops[arm]['finite_prefix'];d.line([point(p) for p in finite],fill='#e8992d',width=4)
   # Base, event start, fixed choice point, cutoff, last native collection.
   for p,label,color in [(c['base'],'B','#24435c'),(crops[arm]['choice_state']['current'],'选择点','#4d4d4d')]:
    px,py=point(p);d.ellipse((px-5,py-5,px+5,py+5),outline=color,width=2);txt(d,(px+6,py-24),label,font(15),c=color)
   stop=crops[arm]['stop_state']['current'];px,py=point(stop);d.line((px-7,py-7,px+7,py+7),fill='#c57014',width=3);d.line((px-7,py+7,px+7,py-7),fill='#c57014',width=3)
   U=set(map(tuple,c['targets']))-HH;seen=set();last=None
   for p in raw:
    if tuple(p) in U-seen:last=p;seen.add(tuple(p))
   if last:
    px,py=point(last);d.ellipse((px-6,py-6,px+6,py+6),outline='#c92f48',width=3);txt(d,(px+8,py-4),'末采',font(15),c='#b5243b')
   txt(d,(ox,oy+515),f"截断 {stop}；{crops[arm]['stop_state']['reason']}；补尾前剩 {len(crops[arm]['stop_state']['pending'])} 格",font(16))
   for x in range(0,xmax+1,10):px,py=point((x,0));txt(d,(px-5,py+10),x,font(13),c='#778395')
   for y in range(10,ymax+1,10):px,py=point((0,y));txt(d,(px-28,py-8),y,font(13),c='#778395')
 txt(d,(35,1235),'橙线=固定有限前缀（原生）；灰线=完整原生；蓝/紫线=整条真实/替代路线经同版直达。红圈=原生末采。',F18)
 txt(d,(35,1267),'绿格=事件物理已采H；青格=共同规划前缀已采；黄格=选择点尚待采；黑格=公开障碍；浅灰=非目标通行格。',F18)
 txt(d,(35,1297),'截断点是规划状态，不是新的真实停止事件；图上末采为原生格心，不冒称直达信用的唯一首次入区时刻。',font(16))
 return save(im,name)
def main():
 start=time.perf_counter();rows=read(H/'joined_results.json');files=[chart(rows)]
 for args in [('base__I_gap_B__p60','I主正例：旧序补尾改变真实候选的收尾安排','I主正例_真实与替代.png'),('base__T_gap_B__p25','T反例：两臂估计都偏长，排序仍然反了','T反例_真实与替代.png'),('base__L_gap_A__p25','L小收益例：识别方向，却把不到1米估成10米','L小收益例_真实与替代.png')]:files.append(routefigure(*args))
 with (H/'figure_receipt.json').open('x',encoding='utf-8') as f:json.dump(dict(files=files,seconds=time.perf_counter()-start,source='saved paths and joined estimates only; no geometric legality/route generation',new_core=0,new_post=0,new_BFS=0,new_geometry=0),f,ensure_ascii=False,indent=2)
 print(dict(figures=len(files),seconds=time.perf_counter()-start))
if __name__=='__main__':main()
