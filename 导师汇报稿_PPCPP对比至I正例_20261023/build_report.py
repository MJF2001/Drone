"""Build an illustrated research report from saved evidence; no planner imports."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from collections import Counter
import base64, hashlib, html, json, math, re, shutil

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
IMG=OUT/'images'
IMG.mkdir(exist_ok=True)
FONT='C:/Windows/Fonts/msyh.ttc'
BOLD='C:/Windows/Fonts/msyhbd.ttc'
INK='#1e293b'; MUTED='#526276'; BLUE='#2463a5'; GREEN='#21815b'; RED='#b83c40'; PALE='#eff4f8'

def f(n=30,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def canvas(w,h,title,subtitle=''):
 im=Image.new('RGB',(w,h),'white');d=ImageDraw.Draw(im)
 d.text((55,30),title,font=f(40,True),fill=INK)
 if subtitle:d.text((55,91),subtitle,font=f(25),fill=MUTED)
 return im,d
def wrap(d,s,width,font):
 lines=[]
 for para in s.split('\n'):
  line=''
  for c in para:
   if d.textlength(line+c,font=font)>width and line:lines.append(line);line=c
   else:line+=c
  lines.append(line)
 return lines
def para(d,xy,s,width,size=29,color=INK,b=False):
 x,y=xy;font=f(size,b)
 for line in wrap(d,s,width,font):d.text((x,y),line,font=font,fill=color);y+=size*1.5
 return y
def box(d,rect,title,body,color=BLUE):
 x,y,r,b=rect;d.rounded_rectangle(rect,radius=18,fill=PALE,outline=color,width=3)
 yy=para(d,(x+24,y+19),title,r-x-48,31,color,True)
 para(d,(x+24,yy+13),body,r-x-48,27)
def arrow(d,a,b,color=MUTED):
 d.line((a,b),fill=color,width=4)
 angle=math.atan2(b[1]-a[1],b[0]-a[0]);s=15
 pts=[b,(b[0]-s*math.cos(angle-.5),b[1]-s*math.sin(angle-.5)),(b[0]-s*math.cos(angle+.5),b[1]-s*math.sin(angle+.5))]
 d.polygon(pts,fill=color)
def save(im,name):im.save(IMG/name)

sources={
'R01':['七算法共同预算比较_v0.3_Cstar07_20261020/PPCPP与其他算法新版分析稿_20261020.md'],
'R02':['全方法受控场景归因_v0.2_20261020/全方法受控归因结果与逐算法结论_20261020.md'],
'R03':['PPCPP首次恢复完整试走_v0.1_20261020/首次恢复试走实现与开发结果_20261020.md'],
'R04':['PPCPP结构候选新开发验证_v0.1_20261020/新开发验证结果与候选保留判断_20261020.md'],
'R05':['PPCPP小图最优差距诊断_v0.2_20261020/小图最优差距诊断结果.md'],
'R06':['PPCPP结束位置跨几何验证_v0.1_20261020/结束位置跨几何验证结果.md'],
'R07':['PPCPP_LAST新开发地图验证_v0.1_20261020/LAST新开发地图验证结果.md'],
'R08':['PPCPP_LAST距离查询等价提速_v0.2_20261020/LAST距离查询等价提速结果.md'],
'R09':['PPCPP局部P2混合开发诊断_v0.1_20261020/结果解读与调用账.md'],
'R10':['局部P2最后有效性检查_v0.1_20261020/最后有效性检查报告.md'],
'R11':['PPCPP四方向共同预算正式比较_v0.1_20261020/正式比较结果.md'],
'R12':['复杂障碍压力开发测试_v0.1_20261021/通俗结论.md'],
'R13':['PPCPP首次新旧竞争单步干预诊断_v0.1_20261021/通俗报告与完整结果.md','PPCPP首次新旧竞争单步新开发验证_v0.1_20261021/通俗报告与完整结果.md'],
'R14':['连续事件六世界开发比较_v0.1_20261022/通俗报告与完整结果.md'],
'R15':['连续事件实际成本只读诊断_v0.1_20261022/通俗结论与裁决建议.md'],
'R16':['中心区计时插桩影响核查_v0.1_20261022/00_通俗计时核查报告.md'],
'R17':['中心区OFF全量质量时间开发比较_v0.1_20261022/00_通俗全量开发比较报告.md'],
'R18':['旧计划真实受阻PPCPP成对诊断_v0.1_20261023/00_通俗成对诊断报告.md'],
'R19':['覆盖阶段受阻选例核查_v0.1_20261023/00_通俗选例核查结论.md'],
'R20':['覆盖阶段真实受阻两例成对诊断_v0.1_20261023/00_通俗两例成对诊断报告.md'],
'R21':['覆盖受阻恢复目标单变量诊断_v0.1_20261023/00_通俗单变量诊断结论.md'],
'R22':['恢复目标收益事件依赖性补齐_v0.1_20261023/00_通俗事件依赖性补齐报告.md'],
'R23':['障碍后接续选择研究假设_v1_20261023.md'],
'R24':['障碍后接续假设与扩样协议_v0.1_20261023/01_可执行扩样协议_待核定.md','障碍后接续扩样协议核定与执行稿_给sol_20261023.md'],
'R25':['障碍后接续假设有限扩样_v0.1_20261023/00_通俗扩样结果与结论.md','障碍后接续假设有限扩样_v0.1_20261023/pairs.json'],
'R26':['障碍后接续正反例受控变体_v0.1_20261023/00_通俗受控变体结果.md','障碍后接续正反例受控变体_v0.1_20261023/pairs.json'],
}
manifest=[]
for sid,paths in sources.items():
 for rel in paths:
  p=ROOT/rel;data=p.read_bytes()
  manifest.append(dict(id=sid,path=str(p),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)))

def load(rel):return json.loads((ROOT/rel).read_text(encoding='utf-8-sig'))
pairs=load(sources['R25'][1]);variants=load(sources['R26'][1])
assert len(pairs)==12 and len(variants)==7
assert Counter(x['delta_post_sign'] for x in pairs)=={-1:4,0:7,1:1}
assert Counter(x['delta_post_sign'] for x in variants)=={-1:4,0:1,1:2}
lookup={x['id']:x for x in pairs}
assert abs(lookup['I_gap_B__p60']['delta_post_display']+28.763940280)<1e-8
assert abs(lookup['T_gap_B__p25']['delta_post_display']-8.587181813)<1e-8
assert all(x['valid_pair'] for x in pairs+variants)

im,d=canvas(1740,1020,'研究怎样从算法对比走向障碍后的接续选择','按研究问题组织；已有工程能力和探索结果不自动成为算法创新')
cards=[('比较现有算法','统一任务、历史、返航和预算\n发现PPCPP快，但并非处处最短'),('尝试改进PPCPP','恢复目标、结束位置、局部混合、方向\n同时检查收益、计算和转弯代价'),('统一合法直达','保留采集责任与历史\n关闭详细计时观察后重新比较'),('聚焦旧计划受阻','先确认障碍真正截断旧计划\n从返航端转到覆盖仍未完成的状态'),('一次选择干预','同一E输入：默认与固定备选\n完整计算后续覆盖和返航'),('正反例与受控变体','12组：4短、7平、1长\nI正例与T反例在邻近条件下保持')]
rects=[]
for i,(t,b) in enumerate(cards):
 col=i%3;row=i//3;x=55+col*560;y=175+row*365
 rect=(x,y,x+510,y+270);rects.append(rect);box(d,rect,t,b,GREEN if i==5 else BLUE)
for i in [0,1,3,4]:arrow(d,(rects[i][2]+7,(rects[i][1]+rects[i][3])/2),(rects[i+1][0]-10,(rects[i+1][1]+rects[i+1][3])/2))
arrow(d,(1645,445),(1645,495));d.line(((1645,495),(310,495),(310,530)),fill=MUTED,width=4);arrow(d,(310,520),(310,540))
para(d,(60,925),'当前达到：找到可重复观察的改善空间与反例。仍缺：能在决策前区分它们的可靠规则。',1620,29,GREEN,True)
save(im,'01_研究思路.png')

im,d=canvas(1740,1040,'完整任务费用与覆盖条件','上：评价整条任务；下：后期统一的中心有效采集区模型')
box(d,(60,155,825,380),'完整距离 = 剩余覆盖 + 最后返航','当前连接更近，并不保证完整路线更短。\n两种选择都必须完成相同的可检任务。')
box(d,(875,155,1680,380),'评价同时保留','路线是否合法、任务是否完成、是否返航；\n完整距离、计算时间、90°及其他转弯。')
gx,gy,s=100,475,115
for x in range(5):
 for y in range(3):d.rectangle((gx+x*s,gy+y*s,gx+(x+1)*s,gy+(y+1)*s),outline='#b6c3cf',width=2)
cx,cy=gx+2.5*s,gy+1.5*s
d.rectangle((cx-.2*s,cy-.2*s,cx+.2*s,cy+.2*s),fill='#b8dfc8',outline=GREEN,width=3)
d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=INK)
arrow(d,(gx+15,gy+2.7*s),(gx+4.8*s,gy+.38*s),BLUE)
para(d,(785,470),'任务格：1米 × 1米\n中心有效区：0.4米 × 0.4米开方区\n实际进入中心区，才计入该格任务信用。\n经过格子边缘不自动算完成。',875,31)
para(d,(785,735),'示意图不对应实测成像效果；\n本研究评价几何覆盖与路径规划，\n不据此声称真实裂缝识别已验证。',875,27,MUTED)
para(d,(95,895),'图中蓝线仅用于解释覆盖条件；实际路线必须另外满足全部障碍和任务约束。',1540,27,MUTED)
save(im,'02_完整任务与覆盖.png')

im,d=canvas(1740,940,'早期共同预算对比：PPCPP并非所有方法中都最短','20个开发状态 × 2种子；仅统计双方及时的配对（R01）')
rows=[('P2_MULTI',0,0,24),('OARP_CORE2',8,2,30),('TREE_MST',2,0,32),('C*',24,4,12),('TRACE',20,4,16),('CAP',26,6,8)]
for i,(name,a,b,c) in enumerate(rows):
 y=200+i*94;d.text((65,y),name,font=f(28,True),fill=INK);x=335;scale=19
 for n,col in [(a,GREEN),(b,'#a8b4c0'),(c,RED)]:
  if n:
   d.rectangle((x,y,x+n*scale,y+45),fill=col)
   if n>=2:d.text((x+n*scale/2-12,y+4),str(n),font=f(25,True),fill='white')
   x+=n*scale
 d.text((1130,y+3),f'有效配对 {a+b+c}',font=f(27),fill=MUTED)
for x,col,t in [(70,GREEN,'PPCPP更短'),(415,'#a8b4c0','同长'),(730,RED,'PPCPP更长')]:d.rectangle((x,795,x+30,825),fill=col);d.text((x+45,788),t,font=f(27),fill=INK)
para(d,(70,862),'PPCPP平均入口约17.8毫秒；各行配对子集不同，不能拼成统一总排名。',1600,27,MUTED)
save(im,'03_算法对比.png')

im,d=canvas(1740,900,'允许合法直达后的质量与计算时间','同一54状态开发批，关闭核心详细profile；P2全部自然完成有限流程（R17）')
box(d,(55,155,810,720),'原PPCPP → PPCPP＋直达','距离采用全批总量口径；原版归一为100。')
for j,(label,val,col) in enumerate([('原PPCPP',100,'#8195ab'),('PPCPP＋直达',90.438,GREEN)]):
 y=345+j*140;d.text((85,y-47),label,font=f(30),fill=INK);d.rectangle((85,y,85+val*6,y+52),fill=col);d.text((100+val*6,y+4),f'{val:.3f}',font=f(25),fill=INK)
d.text((85,645),'总距离减少9.562%',font=f(34,True),fill=GREEN)
box(d,(865,155,1680,720),'两种直达方案的端到端均值','含该配置必要包装与信用处理；单位：秒。')
for j,(label,val,col) in enumerate([('PPCPP＋直达',.126426,GREEN),('P2＋直达',1.028451,BLUE)]):
 y=345+j*140;d.text((895,y-47),label,font=f(30),fill=INK);d.rectangle((895,y,895+val*580,y+52),fill=col);d.text((910+val*580,y+4),f'{val:.3f}',font=f(25),fill=INK)
para(d,(895,635),'状态等权：PPCPP＋直达多走14.700%。',735,27,RED)
para(d,(65,770),'平均少用0.902025秒，不据时间与距离百分比大小宣布综合胜出；三个更慢配对保留。',1590,27,MUTED)
save(im,'04_质量时间.png')

im,d=canvas(1740,1060,'一次选择干预：比较的是完整后续结果','实验设计示意；只改一处目标，不代表穷尽全部路线')
box(d,(60,160,500,460),'相同的事件后输入','同一地图、障碍、当前位置、历史、任务、来向、基地和资源。')
box(d,(650,160,1130,460),'共同预测前缀','按PPCPP计算到指定恢复选择：周围没有紧邻未检格，仍有多个未检任务。')
arrow(d,(510,310),(635,310))
box(d,(650,570,1130,790),'OFF：原选择','选择原最近待检目标；按原规则完成后续覆盖与返航。',BLUE)
box(d,(1190,570,1670,790),'ALT：一次替换','只改为固定备选目标；之后全部恢复原PPCPP规则。',GREEN)
arrow(d,(800,470),(800,555));d.line(((1040,470),(1430,470)),fill=MUTED,width=4);arrow(d,(1430,470),(1430,555))
box(d,(60,570,500,790),'比较完整路线','两臂使用同版直达；核对责任、安全、返航、距离、时间和转弯。')
para(d,(65,875),'OFF先复现REF，证明隔离钩子没有改变原行为；ALT只允许一处目标选择例外。',1600,30,BLUE)
para(d,(65,940),'算法在计算机里推演，不是让无人机先后试飞两条路线。',1600,29,MUTED)
save(im,'05_单次干预.png')

im,d=canvas(1740,1250,'12组有限扩样：改善、等长和退化全部保留','ALT减OFF完整直达距离；负数表示备选更短（R25）')
zero=1320;unit=25;left=385
for x in [-30,-20,-10,0,10]:
 px=zero+x*unit;d.line((px,175,px,1080),fill='#e3e9ef',width=2);d.text((px-25,1110),str(x),font=f(24),fill=MUTED)
for i,x in enumerate(pairs):
 y=193+i*73;v=x['delta_post_display'];label=x['id'].replace('gap_','').replace('__p','  ')
 d.text((60,y+2),label,font=f(27),fill=INK)
 end=zero+v*unit
 if v:d.rectangle((min(zero,end),y,max(zero,end),y+38),fill=GREEN if v<0 else RED)
 else:d.ellipse((zero-5,y+14,zero+5,y+24),fill='#7d8fa3')
 text=f'{v:+.3f}米' if v else ('同路' if x['raw_same'] and x['post_same'] else '等长不同路')
 pos=(end-175 if v<0 else end+18)
 if v==0:pos=zero+20
 d.text((pos,y-1),text,font=f(25),fill=GREEN if v<0 else RED if v>0 else MUTED)
para(d,(60,1180),'4短、7平、1长；来自6基础几何的12状态，属于固定受控开发证据。',1610,28,MUTED)
save(im,'06_扩样结果.png')

copies=[('障碍后接续假设有限扩样_v0.1_20261023/figures/I_gap_B__p60.png','07_I正例实际路线.png'),('障碍后接续假设有限扩样_v0.1_20261023/figures/T_gap_B__p25.png','08_T反例实际路线.png')]
for src,dst in copies:
 shutil.copyfile(ROOT/src,IMG/dst)
 manifest.append(dict(id='FIGURE_COPY',path=str(ROOT/src),output='images/'+dst,sha256=hashlib.sha256((ROOT/src).read_bytes()).hexdigest(),bytes=(ROOT/src).stat().st_size))

im,d=canvas(1740,1200,'受控变体：I保持改善，T的障碍变体保持退化','原例为旧参照；L四槽没有合格状态，不补零值（R26）')
zero=1280;unit=25
by={x['id']:x for x in variants}
print(json.dumps({'variant_ids':list(by)},ensure_ascii=False))
vr=[]
for anchor in ['I_gap_B__p60','T_gap_B__p25']:
 vr.append((anchor+' 原例',lookup[anchor]['delta_post_display']))
 for tag in ['A1','A2','B1','B2']:
  key=anchor+'__'+tag
  if key in by:vr.append((anchor+' '+tag,by[key]['delta_post_display']))
  else:vr.append((anchor+' '+tag,None))
for i,(label,v) in enumerate(vr):
 y=190+i*79;d.text((60,y),label.replace('gap_','').replace('__p',' '),font=f(26),fill=INK)
 if v is None:d.text((720,y),'不适用：切点已越过原受阻边',font=f(25),fill=MUTED);continue
 end=zero+v*unit
 if v:d.rectangle((min(zero,end),y,max(zero,end),y+35),fill=GREEN if v<0 else RED)
 else:d.ellipse((zero-5,y+12,zero+5,y+22),fill=MUTED)
 d.text((end-170 if v<0 else end+15,y-3),f'{v:+.3f}米',font=f(25),fill=GREEN if v<0 else RED if v>0 else MUTED)
para(d,(60,1030),'A1/A2只换障碍位置；B1/B2改公开进度。I两个B汇合到相同决策状态。',1610,27,MUTED)
para(d,(60,1090),'T的B1目标对改变且同路；只有3个旧基础几何，不能由本批估计总体胜率。',1610,27,MUTED)
save(im,'09_受控变体.png')

mdpath=OUT/'导师汇报稿_研究思路与实验证据.md'
md=mdpath.read_text(encoding='utf-8')
for sid in set(re.findall(r'R\d\d',md)):
 assert sid in sources,sid
links=re.findall(r'!\[([^]]*)\]\(([^)]+)\)',md)
assert len(links)==9
for _,rel in links:
 p=OUT/rel;assert p.exists();Image.open(p).verify()

evidence=['# 证据来源与核对清单','', '本文用于追溯汇报中的阶段数字。新文稿未运行规划器、后处理或旧实验核验脚本；核对对象是有效报告、关键保存配对及文件来源。','', '## 来源索引','']
for sid,paths in sources.items():
 evidence.extend([f'### {sid}',''])
 for rel in paths:evidence.append(f'- [{rel}]({(ROOT/rel).as_posix()})')
 evidence.append('')
evidence.extend(['## 本次实际检查','', '- 原扩样pairs.json确有12个有效配对，严格符号为4负、7零、1正；变体7对为4负、1零、2正。', '- I、T关键距离差与保存数值核对；12组原始差值用于图6，7组变体用于图9。', '- 两张实际路线图为字节复制，保留原图图例，没有修改路线或绘制虚构实验轨迹。', '- 其他图片为示意图或保存统计重画，正文图注说明来源和限制。', '- 所有数字仍属于各自模型和开发批，不跨批合并为总胜率；后续结构整理不纳入正文完成范围。','', '## 写作指导来源','', '- [Scientific Writing](https://github.com/YuanZHAO321/Scientific-Writing/blob/main/SKILL.md)：用于组织研究论证、段落和图注。','- [Plain Writing](https://github.com/docwriter-org/plain-writing-skill/blob/main/skills/plain-writing/SKILL.md)：用于术语解释和通俗表达。','', '技能内容仅作为写作指导，没有安装任何技能，也没有上传本地实验材料。'])
(OUT/'证据来源与核对清单.md').write_text('\n'.join(evidence)+'\n',encoding='utf-8')
(OUT/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def inline(s):
 s=html.escape(s)
 s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
 s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 s=re.sub(r'\[([^]]+)\]\(([^)]+)\)',lambda m:f'<a href="{html.escape(m.group(2),quote=True)}">{m.group(1)}</a>',s)
 s=re.sub(r'［(R\d\d(?:、R\d\d)*)］',lambda m:'<sup>'+','.join(f'<a href="#ref-{x}">{x}</a>' for x in m.group(1).split('、'))+'</sup>',s)
 return s

def render(md):
 lines=md.splitlines();parts=[];toc=[];i=0
 while i<len(lines):
  s=lines[i].strip()
  if not s:i+=1;continue
  if s.startswith('#'):
   m=re.match(r'^(#+) (.*)',s);level=len(m.group(1));title=m.group(2);aid=f's{len(toc)}'
   parts.append(f'<h{level} id="{aid}">{inline(title)}</h{level}>')
   if level==2:toc.append((aid,title))
   else:toc.append((aid,title))
   i+=1;continue
  if s.startswith('|'):
   rows=[]
   while i<len(lines) and lines[i].strip().startswith('|'):
    r=[c.strip() for c in lines[i].strip().strip('|').split('|')]
    if not all(re.fullmatch(r':?-+:?',c or ' ') for c in r):rows.append(r)
    i+=1
   parts.append('<div class="table-wrap"><table>')
   for ri,r in enumerate(rows):
    tag='th' if ri==0 else 'td';parts.append('<tr>'+''.join(f'<{tag}>{inline(c)}</{tag}>' for c in r)+'</tr>')
   parts.append('</table></div>');continue
  m=re.fullmatch(r'!\[([^]]*)\]\(([^)]+)\)',s)
  if m:
   path=OUT/m.group(2);enc=base64.b64encode(path.read_bytes()).decode()
   parts.append(f'<figure><img src="data:image/png;base64,{enc}" alt="{html.escape(m.group(1))}" loading="lazy" tabindex="0" role="button" aria-label="点击放大：{html.escape(m.group(1))}"><span class="zoom-hint">点击图片可放大查看路线和标注。</span></figure>')
   i+=1;continue
  if s.startswith('*') and s.endswith('*') and not s.startswith('**'):
   parts.append('<p class="caption">'+inline(s[1:-1])+'</p>');i+=1;continue
  paragraph=[s];i+=1
  while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||!\[)',lines[i].strip()):paragraph.append(lines[i].strip());i+=1
  parts.append('<p>'+inline(' '.join(paragraph))+'</p>')
 return ''.join(parts),toc

body,toc=render(md)
toc_html=''.join(f'<a href="#{aid}">{html.escape(title)}</a>' for aid,title in toc if title.startswith(('一、','二、','三、','四、','五、','六、','七、','八、','九、','十、','十一、','十二、','附录')))
refs='<section class="references"><h2>证据来源</h2>'
for sid,paths in sources.items():refs+=f'<p id="ref-{sid}"><strong>{sid}</strong> '+ '<br>'.join(html.escape(p) for p in paths)+'</p>'
refs+='</section>'
css='''
:root{color-scheme:light}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f0f3f7;color:#213047;font-family:"Microsoft YaHei","Noto Sans CJK SC",sans-serif;font-size:17px;line-height:1.95}main{max-width:1080px;margin:34px auto;background:white;padding:48px 68px;box-shadow:0 4px 22px #18324a10}h1{font-size:32px;line-height:1.5;margin-top:12px}h2{font-size:25px;margin-top:48px;padding-bottom:10px;border-bottom:2px solid #dce6ef}h3{font-size:21px;margin-top:32px}p{margin:18px 0}strong{font-weight:700;color:#162d47}nav{background:#eff4f8;padding:22px 26px;border-radius:9px;margin:24px 0 32px}nav strong{display:block;margin-bottom:10px}nav a{display:block;font-size:15px;line-height:2}a{color:#2463a5;text-decoration:none}a:hover{text-decoration:underline}figure{margin:28px -15px 5px}img{display:block;width:100%;height:auto;border:1px solid #e6ecf2;border-radius:5px}.caption{font-size:14px;color:#526276;line-height:1.85;margin:8px 0 30px}.table-wrap{overflow:auto;margin:22px 0}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.75}th,td{padding:10px 12px;border:1px solid #d9e1ea;text-align:left;vertical-align:top}th{background:#edf3f8;font-weight:700}tr:nth-child(even){background:#fafcfe}sup{font-size:11px;margin-left:3px}.references{border-top:1px solid #dde5ec;margin-top:50px}.references p{font-size:13px;line-height:1.8;overflow-wrap:anywhere}code{font-family:Consolas,monospace;font-size:.9em}footer{font-size:13px;color:#6b7c8f;padding-top:30px} @media(max-width:800px){main{margin:0;padding:25px 22px}h1{font-size:27px}h2{font-size:23px}body{font-size:16px}figure{margin:20px 0}}@media print{body{background:white;font-size:10.5pt}main{max-width:none;margin:0;padding:0;box-shadow:none}nav{display:none}h2{break-after:avoid;font-size:15pt;margin-top:25px}h3{break-after:avoid;font-size:12pt}table{font-size:8pt}figure{break-inside:avoid;margin:16px 0 0}img{max-height:23cm;object-fit:contain}.caption{font-size:9pt}.references p{font-size:8pt}a{color:inherit}p{orphans:3;widows:3}@page{size:A4;margin:19mm 17mm}}
'''
css+='''figure img{cursor:zoom-in}.zoom-hint{display:block;font-size:12px;color:#768598;margin-top:4px}.image-modal[hidden]{display:none}.image-modal{position:fixed;inset:0;background:#172335ee;z-index:20;overflow:auto;padding:70px 25px 25px}.image-modal img{width:auto;max-width:none;height:auto;margin:0 auto;border:0}.image-modal button{position:fixed;right:25px;top:18px;background:white;border:0;border-radius:5px;padding:10px 18px;font:16px "Microsoft YaHei",sans-serif;cursor:pointer;z-index:21}@media print{.image-modal,.zoom-hint{display:none!important}}
'''
zoom='''<div id="image-modal" class="image-modal" hidden role="dialog" aria-modal="true" aria-label="放大图件"><button type="button">关闭（Esc）</button><img alt=""></div><script>(()=>{const m=document.getElementById('image-modal'),target=m.querySelector('img'),close=m.querySelector('button');let origin=null;function hide(){m.hidden=true;document.body.style.overflow='';if(origin)origin.focus()}function show(im){origin=im;target.src=im.src;target.alt=im.alt;m.hidden=false;document.body.style.overflow='hidden';close.focus()}document.querySelectorAll('figure img').forEach(im=>{im.addEventListener('click',()=>show(im));im.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();show(im)}})});close.addEventListener('click',hide);m.addEventListener('click',e=>{if(e.target===m)hide()});document.addEventListener('keydown',e=>{if(e.key==='Escape')hide()})})();</script>'''
document='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>无人机研究进展汇报：从PPCPP对比到I正例</title><style>'+css+'</style></head><body><main><nav><strong>阅读目录</strong>'+toc_html+'</nav>'+body+refs+'<footer>2026-10-23 · 根据本地有效报告整理。所有图件已嵌入本文件，可独立打开和浏览器打印。</footer></main>'+zoom+'</body></html>'
(OUT/'导师汇报稿_图文阅读版.html').write_text(document,encoding='utf-8')

# A contact sheet for manual visual inspection of every newly drawn figure.
thumbs=[]
for p in sorted(IMG.glob('*.png')):
 im=Image.open(p).convert('RGB');im.thumbnail((780,470));tile=Image.new('RGB',(820,540),'#e9eef3');tile.paste(im,((820-im.width)//2,45+(470-im.height)//2));ImageDraw.Draw(tile).text((15,10),p.name,font=f(21),fill=INK);thumbs.append(tile)
sheet=Image.new('RGB',(2460,1620),'white')
for i,t in enumerate(thumbs):sheet.paste(t,((i%3)*820,(i//3)*540))
sheet.save(OUT/'图件检查总览.jpg',quality=92)
check=dict(report_scope='PPCPP comparison through I positive example and controlled variants; excludes later structural study',source_groups=len(sources),source_files=len(manifest),main_figures=len(links),source_pairs_checked=len(pairs),variant_pairs_checked=len(variants),new_planner_calls=0,new_post_calls=0,old_files_modified=0,html_embedded_images=document.count('<img src="data:image/png;base64,'),images_verified=True,skills_installed=False)
assert check['html_embedded_images']==9
(OUT/'制作与核对记录.json').write_text(json.dumps(check,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(check,ensure_ascii=False,indent=2))
