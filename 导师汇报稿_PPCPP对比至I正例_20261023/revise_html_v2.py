"""Revise only the HTML report; preserve the long Markdown and experiment files."""
from pathlib import Path
from collections import defaultdict,Counter
from html.parser import HTMLParser
from PIL import Image
import base64,csv,hashlib,html,json,re,shutil,statistics

H=Path(__file__).resolve().parent
ROOT=H.parent
TARGET=H/'导师汇报稿_图文阅读版.html'
BACKUP=H/'导师汇报稿_图文阅读版_原长文版.html'
if not BACKUP.exists():shutil.copyfile(TARGET,BACKUP)
source_manifest=json.loads((H/'source_manifest.json').read_text(encoding='utf-8'))
for item in source_manifest:
 assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
from build_scaled_widgets import build_scaled_widgets
continuous_html,local_replay,direction_replay,continuous_css,continuous_js=build_scaled_widgets(H)
replay_html=replay_css=replay_js=attempt_css=attempt_js=''

timing_dir=ROOT/'七算法共同预算比较_v0.3_Cstar07_20261020'
with (timing_dir/'method_summary.csv').open(encoding='utf-8-sig',newline='') as stream:
 timing_summary={row['method']:row for row in csv.DictReader(stream)}
with (timing_dir/'all_runs.csv').open(encoding='utf-8-sig',newline='') as stream:
 timing_runs=list(csv.DictReader(stream))
method_order=['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP']
timing_rows=[]
for method in method_order:
 summary=timing_summary[method];runs=[row for row in timing_runs if row['method']==method]
 seconds=[float(row['entry_seconds']) for row in runs]
 assert len(runs)==int(summary['calls'])==40
 assert all(row['valid']=='True' for row in runs)
 assert abs(statistics.fmean(seconds)-float(summary['entry_mean']))<1e-10
 assert abs(max(seconds)-float(summary['entry_max']))<1e-10
 assert sum(row['timely']=='True' for row in runs)==int(summary['timely'])
 assert sum(row['valid']=='True' and row['timely']=='False' for row in runs)==int(summary['late_valid'])
 timing_rows.append(('C*' if method=='CSTAR' else method,f"{float(summary['entry_mean']):.4f}",f"{float(summary['entry_max']):.4f}",f"{summary['timely']} / 40",summary['late_valid']))
for filename in ['method_summary.csv','all_runs.csv','七算法共同预算比较报告_20261020.md']:
 path=timing_dir/filename
 if not any(x['path']==str(path) for x in source_manifest):
  data=path.read_bytes();source_manifest.append(dict(id='R01',path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),role='same_batch_timing_evidence'))
for sid,relative in [
 ('R07','PPCPP保留末采集格候选_v0.1_20261020/保留末采集格候选开发结果.md'),
 ('R08','PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/LAST与P2共同预算比较结果.md')]:
 path=ROOT/relative
 if not any(x['path']==str(path) for x in source_manifest):
  data=path.read_bytes();source_manifest.append(dict(id=sid,path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),role='stage_two_progression_evidence'))
for sid,relative in [
 ('R27','任意方向合法直达有限诊断_v0.1_20261022/00_通俗报告.md'),
 ('R28','任意方向直达收益结构只读归因_v0.1_20261022/00_通俗报告.md'),
 ('R29','任意方向固定顺序连接下界核验_v0.1_20261022/00_通俗结论.md')]:
 path=ROOT/relative
 if not any(x['path']==str(path) for x in source_manifest):
  data=path.read_bytes();source_manifest.append(dict(id=sid,path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),role='any_angle_transition_evidence'))
for sid,relative in [
 ('R30','评价指标完整补算与数据审计_v0.1_20261020/评价指标口径_v1_20261020.md'),
 ('R31','任务格与中心采集区设计及资料依据_20261022.md'),
 ('R32','中心有效采集区暂定尺寸确认_20261022.md'),
 ('R33','七算法共同预算比较_v0.3_Cstar07_20261020/protocol.json')]:
 path=ROOT/relative
 if not any(x['path']==str(path) for x in source_manifest):
  data=path.read_bytes();source_manifest.append(dict(id=sid,path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),role='map_and_metrics_definition'))
# Derive the scale description from saved inputs, without importing planners.
map_protocol=json.loads((timing_dir/'protocol.json').read_text(encoding='utf-8'))
scale_rows=[]
for scale,label in [('small','小图'),('medium','中图'),('large','大图')]:
 cases=[c for c in map_protocol['cases'] if c['scale']==scale]
 counts=[]
 for case in cases:
  path=Path(case['input']);data=path.read_bytes()
  assert hashlib.sha256(data).hexdigest()==case['input_sha256']
  counts.append(len(json.loads(data.decode('utf-8-sig'))['targets']))
 scale_rows.append((label,str(len(cases)),f'{min(counts)}～{max(counts)}格'))
mechanism_source=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/candidate_baselines/PPCPP_CORE4/v0.1_20261014/source/candidate_ppcpp_core4_20261014.py'
if not any(x['path']==str(mechanism_source) for x in source_manifest):
 data=mechanism_source.read_bytes();source_manifest.append(dict(id='R34',path=str(mechanism_source),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),role='plain_language_mechanism_explanation'))
for filename in ['七算法真实路线回放_数据核对.json','七算法真实路线回放数据.json','build_route_replay.py']:
 path=H/filename
 if not any(x['path']==str(path) for x in source_manifest):
  data=path.read_bytes();source_manifest.append(dict(id='R35',path=str(path),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),role='historical_core4_replay_evidence'))
(H/'source_manifest.json').write_text(json.dumps(source_manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
original_md_sha=hashlib.sha256((H/'导师汇报稿_研究思路与实验证据.md').read_bytes()).hexdigest()
pairs=json.loads((ROOT/'障碍后接续假设有限扩样_v0.1_20261023/pairs.json').read_text(encoding='utf-8-sig'))
variants=json.loads((ROOT/'障碍后接续正反例受控变体_v0.1_20261023/pairs.json').read_text(encoding='utf-8-sig'))
assert len(pairs)==12 and Counter(x['delta_post_sign'] for x in pairs)=={-1:4,0:7,1:1}
assert len(variants)==7

def ref(*ids):return '<span class="refs">'+''.join(f'<a href="#ref-{i}">{i}</a>' for i in ids)+'</span>'
def table(headers,rows,cls=''):
 return '<div class="table-scroll"><table class="'+cls+'"><thead><tr>'+''.join('<th scope="col">'+x+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def note(label,text,kind=''):
 return f'<p class="note {kind}"><strong>{label}</strong>{text}</p>'
def detail(title,content):return f'<details><summary>{title}</summary><div class="detail-body">{content}</div></details>'
def figure(name,caption):
 p=H/'images'/name;data=base64.b64encode(p.read_bytes()).decode();w,h=Image.open(p).size
 return f'<figure><button class="figure-button" type="button" aria-label="放大路线图"><img src="data:image/png;base64,{data}" width="{w}" height="{h}" alt="{html.escape(caption)}"></button><figcaption>{caption} <span class="muted">点击图片放大。</span></figcaption></figure>'
def flow(items):
 return '<ol class="flow">'+''.join(f'<li><span class="step">{i+1:02d}</span><strong>{t}</strong><span>{b}</span></li>' for i,(t,b) in enumerate(items))+'</ol>'
def bars(data,label,subtitle='',xmin=None,xmax=None,height=None):
 W=900;left=205;right=130;top=42;row=42;bottom=75
 vals=[v for _,v,_ in data if v is not None]
 xmin=min(0,min(vals)) if xmin is None else xmin;xmax=max(0,max(vals)) if xmax is None else xmax
 span=xmax-xmin or 1;xmin-=span*.08;xmax+=span*.08
 scale=lambda v:left+(v-xmin)/(xmax-xmin)*(W-left-right)
 Ht=top+row*len(data)+bottom;zero=scale(0)
 svg=f'<svg class="bar-chart" viewBox="0 0 {W} {Ht}" role="img" aria-label="{html.escape(label)}"><title>{html.escape(label)}</title>'
 for t in [-30,-20,-10,0,10]:
  if xmin<=t<=xmax:
   x=scale(t);svg+=f'<line x1="{x}" y1="27" x2="{x}" y2="{Ht-bottom+6}" class="grid"/><text x="{x}" y="{Ht-40}" text-anchor="middle" class="axis">{t}</text>'
 svg+=f'<line x1="{zero}" y1="27" x2="{zero}" y2="{Ht-bottom+6}" class="zero-line"/>'
 for i,(name,value,text) in enumerate(data):
  y=top+i*row
  svg+=f'<text x="10" y="{y+10}" class="chart-label">{html.escape(name)}</text>'
  if value is None:
   svg+=f'<text x="{left+12}" y="{y+10}" class="chart-muted">{html.escape(text)}</text>';continue
  x=scale(value);color='gain' if value<0 else 'loss' if value>0 else 'neutral'
  if value:svg+=f'<rect x="{min(x,zero)}" y="{y-6}" width="{abs(x-zero)}" height="23" rx="2" class="{color}"/>'
  else:svg+=f'<circle cx="{zero}" cy="{y+5}" r="4" class="neutral"/>'
  inside=value<0 and abs(x-zero)>120
  tx=x+10 if inside else x-9 if value<0 else x+10;anchor='start' if inside or value>=0 else 'end'
  text=text or f'{value:+.3f}米'
  svg+=f'<text x="{tx}" y="{y+10}" text-anchor="{anchor}" class="chart-value {color}-text"'+(' style="fill:white"' if inside else '')+f'>{html.escape(text)}</text>'
 svg+=f'<text x="{W-right}" y="{Ht-8}" text-anchor="end" class="axis">完整距离差（米）</text></svg>'
 return '<figure class="vector"><figcaption class="chart-title">'+label+'</figcaption>'+svg+('<p class="small muted">'+subtitle+'</p>' if subtitle else '')+'</figure>'

sections=[]
def section(sid,kicker,title,body):
 sections.append((sid,title,f'<section id="{sid}"><div class="section-kicker">{kicker}</div><h2>{title}</h2>{body}</section>'))

# Illustrative map: task geometry and free transit space are distinct.
map_svg='<svg class="bar-chart" viewBox="0 0 900 350" role="img" aria-label="道路任务地图示意：区分可飞通路、已检、未检、新增任务、障碍、基地与当前位置"><title>原始地图与任务图例（示意，非实验样本）</title>'
road={(x,y) for x in range(1,11) for y in (3,4,5)}|{(x,y) for x in (8,9,10) for y in (1,2)}
new={(11,y) for y in (3,4,5)}|{(12,4)}
for y in range(7):
 for x in range(14):
  fill='#f4f6f9'
  if (x,y) in road:fill='#f9e8bb' if x>5 else '#cce7d7'
  if (x,y) in new:fill='#dfd0f1'
  if (x,y)==(8,3):fill='#526173'
  map_svg+=f'<rect x="{20+x*35}" y="{25+y*35}" width="35" height="35" fill="{fill}" stroke="#b9c7d4"/>'
map_svg+='<path d="M72.5 182.5 H212.5 V147.5 H247.5" fill="none" stroke="#24754f" stroke-width="4"/><circle cx="72.5" cy="182.5" r="9" fill="#245c96"/><text x="30" y="292" class="chart-label">基地：蓝点</text><circle cx="247.5" cy="147.5" r="9" fill="#bb6022"/><text x="245" y="292" class="chart-label">当前位置：橙点</text>'
for i,(color,label) in enumerate([('#f4f6f9','可飞非目标：可以通行，不需采集'),('#cce7d7','已检任务：保留完成历史'),('#f9e8bb','未检任务：本次需要继续检查'),('#dfd0f1','新增任务：公开后加入责任'),('#526173','障碍：禁飞；遮挡未检任务暂缓')]):
 y=38+i*48
 map_svg+=f'<rect x="550" y="{y}" width="22" height="22" fill="{color}" stroke="#a9b8c7"/><text x="585" y="{y+17}" class="chart-label">{label}</text>'
map_svg+='<text x="550" y="292" class="chart-muted">绿线：已经实际执行的历史前缀</text></svg>'
section('setup','实验基础','地图、任务规则与评价标准',
 '<p class="lead">研究的是：施工待检区域扩展或新障碍公开后，利用已有进度，从当前位置完成剩余巡检并返回基地。不是从头重复检查整张地图。</p>'+
 '<figure class="vector"><figcaption class="chart-title">地图不是只有一条线：待检路面、飞行空间与覆盖历史分开表示</figcaption>'+map_svg+'<p class="small muted">图为规则示意，不是某次实验结果。道路可以有多格宽；一个格子代表一个采集任务单元，不代表无人机机身占满该格。背景格在本示意中均可飞，深色格为障碍。</p></figure>'+
 table(['设计内容','怎样设置','为什么这样设置'],[
 ('地图与尺度','用二维方格表示可飞域和任务；区分小、中、大规模，改变道路长度、宽度和任务量','检查算法随规模与形状变化的表现，不把道路限定成一格宽'),
 ('形状与事件','直线道路、拐角和折线；直线/拐角扩展、新障碍，以及扩展与障碍组合','对应施工区域改变和旧路线受影响的情形'),
 ('历史与起点','输入已完成任务、当前位置、来向与基地；只处理当前未完成责任','避免把已经采集的任务重新当成必做任务'),
 ('公开信息','算法只使用当前公开地图，不知道未来事件','避免预知障碍或新增区域'),
 ('任务与障碍','可飞不等于必须采集；障碍禁飞且遮挡目标，未完成被遮挡任务暂缓','暂缓不能记为已检；历史已完成不因后来遮挡回滚')])+ref('R30','R33')+
 '<h3>地图规模怎样区分？</h3>'+table(['开头算法比较的规模','输入状态数','当前可检任务数量'],scale_rows)+
 '<p class="small muted">任务数量包含已完成部分，不是剩余未检格数。大小指地图与任务规模，不是让大图使用更大的单格。</p>'+
 '<h3>原始移动、采集与公平条件</h3>'+table(['规则','通俗说明'],[
 ('四邻接移动','只向上、下、左、右的相邻可飞格心移动；一格边长记作一个距离单位，每次移动等长'),
 ('格心采集','实际到达任务格心就完成该格；途中经过其他任务格心也采集；重复经过不增加完成数量'),
 ('结束条件','完成所有当前可检的剩余任务，满足距离资源约束，并实际返回基地'),
 ('共同输入','同一对照共享地图、当前位置、覆盖历史、剩余责任和返航要求；算法保留各自的决策机制'),
 ('时间条件','共同预算实验采用相同时间上限；后文质量—时间比较也记录各方法自然完成所需时间')])+ref('R30')+
 '<h3>评价指标：先保证完成，再比较距离、时间与转弯</h3>'+table(['指标','怎样计算或理解','主要看什么'],[
 ('完整路程 / 步数','从重规划起点到返航结束的所有移动；四邻接步数＝路线点数−1','主距离指标，覆盖衔接和返航都要算'),
 ('剩余任务完成率','本次新完成的任务数 ÷ 起点时当前可检的未完成任务数','本轮应做的任务有没有做完'),
 ('当前可检覆盖率','已完成的当前可检任务数 ÷ 全部当前可检任务数，含已有完成历史','当前能检查的区域覆盖是否完整'),
 ('已发布任务完成率','已完成的已发布任务数 ÷ 全部已发布任务数；另列暂缓与漏检数','避免用可检100%掩盖被障碍遮挡的任务'),
 ('转弯','分别统计90°转弯、180°折返及方向变化总数；原规则只看本次路线相邻移动方向','距离缩短是否换来了更多转弯'),
 ('重复覆盖 / 重叠率','重复目标到达次数 ÷ 全部目标到达次数；区分历史重复、本轮重复、非目标转移','是目标访问重复，不是照片面积重叠率'),
 ('返航尾段','最后一个剩余任务首次完成后，到基地的全部剩余距离；已含在总距离里','区分覆盖安排和结束位置带来的收尾代价'),
 ('计算时间','报告平均、中位数、P95和最大耗时，并统计超预算情况','既看典型速度，也看慢例'),
 ('合法性与可靠性','检查起终点、通行安全、任务、资源；分别记录完整合法、及时、迟到与失败','未完成的短路线不算优势；迟到与路线非法分开')])+
 '<p class="small muted">空任务分母时完成率按已定义规则记100%，同时列任务数；没有目标到达时，重复率不填成0。各指标分开评价，不把时间和距离百分比相减，也不从步数或转弯直接推导真实能耗。'+ref('R30')+'</p>')

ppcpp_summary=(
 '<div id="ppcpp-principle" class="research-fork"><h3>阶段一小结：PPCPP表现很好，值得作为快速基础</h3>'+
 '<p>在本批测试里，PPCPP的优势不只是“算得快”：40次调用全部完整、合法、及时，平均入口约17.8毫秒；与C*、TRACE、CAP的当前适配实现相比，平均路线也更短。也就是说，它用很少计算就给出了有竞争力的完整巡检方案。</p>'+
 '<p class="small muted">这里的“表现很好”限定于本项目已测场景与版本，不代表每个状态都更短，也不是全部方法中的距离冠军。P2等参照仍显示路线改善空间。</p>'+ref('R01')+'</div>'+
 '<h3>PPCPP怎样规划？可以理解为“附近继续扫，断开再接上”</h3>'+
 '<p>可以把无人机想成一只正在移动的“猎物”，在地图外放一个虚拟的“捕食者”。猎物倾向于远离它，于是有了向前推进的方向。这里没有真实追赶：捕食者只是算法里的固定参考位置，不是障碍，也不是另一架无人机。</p>'+
 '<p>但无人机不是一味往远处飞。面对身边几个安全、未检的格子，本项目保留的原评分会把三种倾向合起来比较：</p>'+
 table(['评分倾向','通俗理解'],[
 ('远离虚拟捕食者','给移动一个方向偏好，类似“受到一侧压力，往另一侧推进”'),
 ('尽量顺着原方向走','前面能继续检查，就尽量少拐弯，不每走一格就随意换方向'),
 ('偏向未检邻格较少的位置','结合局部边界结构打分；不是保证先扫边界就全程最短')])+
 '<p>例如刚才向右飞，右侧和上侧都有未检格：继续向右会得到更高的直行奖励；哪个方向更远离虚拟捕食者、邻域结构怎样，也会影响最终得分。<strong>这是一种算得快的局部选择，不会在每一步穷举所有后续覆盖路线。</strong>身边都检查完了，再用最近目标恢复规则连接到下一处。</p>'+
 '<div class="research-overview" role="img" aria-label="PPCPP流程：读取地图与历史，判断紧邻未检格，局部评分或最近目标恢复，更新任务，未完成则循环，完成则返航"><span>读取地图、当前位置和历史</span><i>→</i><span>判断身边有无紧邻未检格</span><i>→</i><span>局部继续 / 连接恢复</span><i>→</i><span>更新任务；未完继续，完成返航</span></div>'+
 table(['遇到什么情况','原PPCPP怎么做','直观理解'],[
 ('身边有紧邻未检格','按原局部评分选择相邻未检格，继续扫描；不是一律选择距基地最近者','先把身边能顺着检查的部分往前推进'),
 ('身边没有紧邻未检格，但还有任务','选择当前公开图上路径最近的待检目标，沿合法连接过去，途中按规则采集','这块扫不下去，就到另一处继续扫'),
 ('全部当前可检任务完成','连接回基地，并检查完整路线与资源要求','覆盖和返航共同组成完整任务')])+ref('R03','R34')+
 note('为什么选它作为研究基础？','保留已经验证的快速覆盖能力，针对真正造成后续绕行的选择寻找改进，而不是为了提出新算法就推翻整套方法。'))

baseline=[('P2_MULTI','24','0 / 0 / 24','多15.26%'),('TREE_MST','34','2 / 0 / 32','多7.65%'),('C*','40','24 / 4 / 12','少3.00%'),('TRACE','40','20 / 4 / 16','少3.47%'),('CAP','40','26 / 6 / 8','少6.09%')]
section('compare','阶段一','先看PPCPP与其他方法的表现',
 '<p class="lead">先统一地图、覆盖历史、当前位置与返航要求，再比较实际输出。</p>'+
 table(['实验设计','数量与条件'],[('开发输入','本页展示原批中的20状态 × 2固定种子 × 6方法，共240次入口'),('预算','每次20秒；距离表只统计双方均及时的同输入配对'),('PPCPP自身表现','40次完整合法且及时；平均入口约17.8毫秒')])+ 
 '<h3>计算时间与及时返回情况</h3>'+
 table(['方法','平均入口时间（秒）','最大入口时间（秒）','及时返回 / 调用','合法但迟到'],timing_rows)+
 '<p class="small muted">时间均值和最大值包含各方法全部40次调用，保留迟到结果。原报告以完整入口≤20.010秒计及时；本批严格20秒的及时次数相同。所有方法均返回合法完整路线。该表为早期同批入口计时，后文关闭详细profile的54状态结果按另一批解释。</p>'+
 '<h3>完整路程：以PPCPP为主体配对比较</h3>'+
 table(['对照方法','及时配对数','PPCPP短 / 平 / 长','PPCPP平均相对距离差'],baseline)+
 note('得到的判断：','本批PPCPP平均入口时间最小，40次全部及时；P2和TREE_MST出现合法但迟到的返回。距离对照仍显示PPCPP有改善空间，因此选择它作为快速基础。')+
 '<p class="small muted">各行配对子集不同；两个种子不等于两张独立地图。相对差以各对照为分母。'+ref('R01')+'</p>'+
 detail('查看实现边界与场景归因',
 table(['方法','本项目比较的实现'],[('PPCPP','独立历史适配，固定捕食者、来向及截止合同'),('C* / TRACE / CAP','保留核心机制的场景适配，存在明确复现边界'),('TREE_MST / P2_MULTI','工程对照；TREE_MST不称TRACE/C*，P2不是最优解')])+
 '<p>另用27输入、五方法、两个种子完成270次受控归因，分别改变间距、历史形态和连接屏障。</p>'+
 table(['发现','影响'],[('间距增大时部分绝对差不变','百分比变化不能直接解释为算法退化'),('连通折线历史改变CAP相对表现','历史空间分布确实影响固定实现'),('屏障高度没有统一单调响应','不能说障碍越多某方法就一定越差')])+ref('R02'))+continuous_html+ppcpp_summary)

def research_step(number,title,why,design,headers,rows,lesson,next_step,sources):
 return ('<article class="research-step"><div class="research-step-heading"><span class="research-number">'+str(number)+'</span><h3>'+title+'</h3></div>'+
 '<div class="research-reason"><b>为什么做</b><p>'+why+'</p></div><div class="research-reason"><b>怎样测试</b><p>'+design+'</p></div>'+
 table(headers,rows)+note('保留的认识',lesson)+ref(*sources)+
 ('<div class="research-next"><span aria-hidden="true">↓</span><div><b>因此，下一步</b><p>'+next_step+'</p></div></div>' if next_step else '')+'</article>')

progression=('<div class="research-fork"><b>围绕快速规划基础，尝试两种改进方向</b><div class="two-col"><a href="#research-local">方向A · 只强化一小段搜索 ↓</a><a href="#research-direction">方向B · 比较不同扫描方向 ↓</a></div><p>两者是分别验证的探索分支，不是相互证明的因果关系。</p></div>')
progression+='<div id="research-local">'+research_step(1,'局部P2混合：少量强搜索能否兼顾快与短？',
 '整体P2更费计算，因此尝试让大部分路线仍用PPCPP，只优化选定小窗口。',
 '固定窗口规则，比较事件组及无障碍控制；保留原路线作为未改善时的选择。无收益后再用正控制与精确抽查检查优化链是否有效。',
 ['检查','结果','解释边界'],[('旧批324次正式入口','相对原版均无路线改善','102次局部P2实际搜索，没有接受更短窗口'),('事件组入口均值','约4.9 → 73.8毫秒','本固定规则只增加开销'),('后续有效性检查','冗余窗口6 → 4步；三抽查窗口已最短','优化链可生效；不能推广为102窗口全最优')],
 '旧批关闭的是该批固定规则的继续信号；下方新场景同时保留收益、等长与退化，不能用旧批全无收益概括全部。',
 '',['R09','R10'])+local_replay+'</div>'
progression+='<div id="research-direction">'+research_step(2,'四方向组合：减轻固定扫描方向的限制',
 '除了加强局部搜索，也检查PPCPP的方向偏好是否限制了路线质量。这个分支需要单独验证。',
 '建立独立方向适配接口，冻结原版不改；在同批54状态比较四个方向生成的完整候选路线。',
 ['指标','结果','代价或边界'],[('路线胜负','22短 / 32平','总步数5530 → 5354，少3.18%'),('90°转弯','752 → 1071','增加319次'),('平均入口耗时','约6.71 → 28.72毫秒','距离改善伴随更多计算')],
 '方向确实影响路线，但没有同时改善距离、计算和转弯，尚不能确立主算法。',
 '',['R11'])+direction_replay+'</div>'
section('attempts','阶段二','改进思路',
 '<p class="lead">PPCPP计算很快，但完整路线仍有改善空间。下文先交代两种改进的旧批结果，再用新补齐的小、中、大单障碍与综合案例直观展示；新旧批次不混合统计。</p>'+

 progression+
 '<div id="research-pivot" class="research-fork"><h3>阶段二小结：常规优化收益有限，改变研究切入点</h3>'+
 table(['已尝试的方法','结果告诉我们什么'],[
 ('局部P2混合','旧批无改善；新分尺度与综合案例出现缩短、等长和退化，均有额外计算'),
 ('四方向组合','总步数少3.18%，但90°转弯多319次，计算也增加')])+
 '<p>这些尝试说明：PPCPP原本已经较强，沿已试过的通用规则继续做低开销优化，能取得的收益有限。因此，我们不再把“全面改写PPCPP核心、在所有地图上都更短”作为当前主线，而是寻找其他切入点。</p>'+
 '<p class="small muted">这不是证明PPCPP已全局最优，或所有优化空间都很小；结论是这些已测试办法没有给出足够理想的收益—代价组合。</p></div>'+
 '<h3>新的目标：事件发生后，怎样选下一处、怎样安排后续路线？</h3>'+
 '<p class="lead">保留PPCPP作为快速基础，先利用合法直达减少不必要的横纵绕行；再重点研究：新障碍或地图扩展后，怎样调整下一步目标与后续巡检安排，让完成剩余覆盖并返航的总飞行距离尽量短。</p>'+
 table(['事件','为什么需要重新安排','希望改善什么'],[
 ('出现新障碍','原路线被阻断，或部分连接、任务可达性发生变化','从真实当前位置接续，减少修复后整条路线的额外绕行'),
 ('地图扩展、新增任务','原有剩余任务与新增任务需要重新组织','决定先去哪里、何时进入新区域，减少覆盖与返航总距离')])+
 note('我们要优化的不是“眼前这一格最近”','某一步连接稍远，也可能让后面少绕很多路。判断应落到剩余覆盖加返航的完整总账，同时保留计算开销与转弯指标；不承诺每次都取得全局最优。')+
 '<div class="research-next"><span aria-hidden="true">↓</span><div><b>下一阶段先打好运动模型基础</b><p>先验证无人机允许合法直达后的距离收益，并统一采集与评价标准；之后再研究事件后的具体选择。障碍与扩展可以使用不同机制，不要求强行统一。</p></div></div>')

quality='''<div class="comparison-panels">
<div><h3>直达对原PPCPP的距离改善</h3><p class="small muted">同批总距离归一；原版 = 100</p>
<div class="mini-row"><span>原PPCPP</span><div class="mini-track"><i style="width:100%;background:var(--slate)"></i></div><b>100</b></div>
<div class="mini-row"><span>＋合法直达</span><div class="mini-track"><i style="width:90.438%;background:var(--green)"></i></div><b>90.438</b></div>
<p class="result green-text">总距离减少9.562%</p></div>
<div><h3>共同端到端计算时间</h3><p class="small muted">同批均值；单位：秒</p>
<div class="mini-row"><span>PPCPP＋直达</span><div class="mini-track"><i style="width:12.293%;background:var(--green)"></i></div><b>0.126</b></div>
<div class="mini-row"><span>P2＋直达</span><div class="mini-track"><i style="width:100%;background:var(--blue)"></i></div><b>1.028</b></div>
<p class="result">平均少用0.902秒</p></div></div>'''
coverage='''<div class="rule-grid"><div class="cell-demo" aria-label="1米任务格与中心0.4米有效采集区"><div class="cell-center">有效<br>采集区</div><span class="cell-label">任务格 1米 × 1米</span></div><div><h3>怎样算完成一个格子？</h3><p>后期统一采用中心0.4米 × 0.4米开方区。实际轨迹进入这个区域，才计入该格任务信用。</p><p class="small muted">任务格表示采集面积，无人机并未占满整格。覆盖条件是仿真模型，尚不能证明真实缺陷识别效果。</p></div></div>'''
section('direct','阶段三','后续思路：合法直达与回程采集',
 '<p class="lead">除了调整局部搜索和扫描方向，还可以从两个层面继续思考：一是把连接走得更直接；二是重新安排采集顺序，减少完成任务后的空返航。</p>'+
 '<h3>思路一：在安全与覆盖完整的前提下，允许合法直达</h3>'+
 '<div class="two-col"><div class="plain-box"><h3>通俗地说</h3><p>如果两个位置之间没有障碍，也没有必须停留采集的任务，就尝试直接飞过去，不一定先横着走、再竖着走。</p></div><div class="plain-box"><h3>不能省掉什么？</h3><p>不能穿过障碍，也不能跳过采集责任。直线不仅两个端点要安全，整段都必须合法；经过任务的有效采集区域才计为完成。</p></div></div>'+
 table(['考虑的环节','希望解决的问题','必须保留的约束'],[
 ('任务之间的衔接、最后返航','减少不必要的折线绕行','整段安全，全部可检任务完成，资源满足'),
 ('评价方式','看完整飞行距离，而不是只看线段数量','累计真实线段长度，并记录计算开销')])+
 note('当前定位：','这是已尝试的路线处理思路，收益受地图、起降点和任务安排影响。本稿不再展开其动画与效果数据，也不把它作为已确认有效的核心改进或创新。原始实验与正反结果继续保留。')+
 '<h3 id="return-service-idea">思路二：安排覆盖顺序，让回程也能完成剩余采集</h3>'+
 '<p>不把“全部检查完”和“返回起点”完全割裂。能否在规划时把最后一批任务与回程方向一起考虑，让无人机在逐渐返回起点的过程中，顺路完成采集？</p>'+
 '<div class="two-col"><div class="plain-box"><h3>分开考虑</h3><p><b>先完成全部采集 → 再从结束位置返回</b></p><p>如果最后停在离起点较远的位置，回去的路可能不再产生新的采集。</p></div><div class="plain-box"><h3>联合考虑（待验证）</h3><p><b>安排外侧任务 → 沿回程衔接剩余任务 → 完成采集并回到起点</b></p><p>尝试让一部分回程同时承担采集任务，而不是全部检查完后才单独安排返航。</p></div></div>'+
 table(['问题','这里具体指什么'],[
 ('“回程采集”不是最后返航','回程采集时尚有未完成任务；严格意义的最后返航，是全部采集完成后的剩余路段'),
 ('真正调整什么','剩余任务的访问顺序、衔接路径与最后采集位置，而不是故意留下几格就算改进'),
 ('事件后怎样使用','新障碍或新增区域公开后，依据当前位置和真实已检历史，重新考虑剩余任务如何与回程衔接'),
 ('用什么判断好坏','比较从当前状态完成全部可检任务并返航的总距离，同时检查覆盖完整性、安全、转弯和计算开销'),
 ('可能失败在哪里','刻意留任务可能增加折返或绕行；即使最后返航变短，完整总距离也可能更长')])+
 note('待验证，不预设有效：','目标是减少“剩余巡检＋最终返航”的总距离，不是单独缩短最后一段。是否有收益、与已有方法有何区别、是否具备创新性，都需要进一步核查与实验。本次只是增加汇报思路，没有启动新实验。'))

used_source_ids=set(re.findall(r'href="#ref-(R\d\d)"',''.join(x[2] for x in sections)))
refs_by=defaultdict(list)
for item in source_manifest:
 if item['id'] in used_source_ids:refs_by[item['id']].append(item['path'])
reference_html=''.join(f'<div id="ref-{sid}" class="source-row"><strong>{sid}</strong>'+''.join('<p>'+html.escape(p)+'</p>' for p in paths)+'</div>' for sid,paths in refs_by.items())
source_details=detail('展开实验来源与完整证据索引',
 '<p>数字来自各自有效版本，不能把不同批次相加形成总体胜率。失败、迟到、技术准备和不适用使用各自分母。</p>'+reference_html)

css='''
:root{color-scheme:light;--ink:#203047;--muted:#596b7e;--blue:#245c96;--green:#24754f;--red:#ae343d;--slate:#91a2b3;--line:#d9e2eb;--paper:#fff;--pale:#f1f5f9}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:22px}body{margin:0;background:#f0f3f7;color:var(--ink);font:16px/1.8 "Microsoft YaHei","Noto Sans CJK SC",sans-serif}main{max-width:1150px;margin:28px auto;padding:40px 56px;background:var(--paper);box-shadow:0 3px 20px #2030470b}header{padding-bottom:20px;border-bottom:2px solid var(--line)}.eyebrow,.section-kicker{font-size:12px;letter-spacing:.1em;color:var(--blue);font-weight:700}h1{font-size:32px;line-height:1.45;margin:9px 0 16px}h2{font-size:25px;line-height:1.55;margin:4px 0 18px}h3{font-size:19px;margin:22px 0 11px}p{margin:12px 0}.lead{font-size:17px;line-height:1.85;max-width:62em}.muted{color:var(--muted)}.small{font-size:13px;line-height:1.8}.toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-top:18px}.toolbar button{background:white;border:1px solid #bdcbd8;border-radius:5px;padding:7px 12px;color:var(--ink);font:inherit;font-size:13px;cursor:pointer}.toolbar span{font-size:13px;color:var(--muted)}nav{display:flex;flex-wrap:wrap;gap:6px 17px;padding:17px 0;border-bottom:1px solid var(--line)}a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}nav a{font-size:13px}section{padding-top:34px;margin-top:12px;border-bottom:1px solid var(--line);padding-bottom:26px}.table-scroll{overflow-x:auto;margin:17px 0}table{width:100%;border-collapse:collapse;line-height:1.75;font-size:14px}th,td{border:1px solid var(--line);padding:11px 13px;text-align:left;vertical-align:top}th{background:#edf3f8;font-weight:700}tbody tr:nth-child(even){background:#fafcfe}td:first-child{font-weight:600}.attempt-table td:nth-child(1){width:14%}.attempt-table td:nth-child(2){width:21%}.attempt-table td:nth-child(3){width:31%}.refs{display:inline-flex;gap:5px;font-size:10px;margin-left:5px;white-space:nowrap;font-weight:400}.note{background:#edf4f8;border-left:3px solid var(--blue);padding:12px 16px;margin:20px 0;font-size:14px}.note strong{display:block;color:var(--blue);margin-bottom:3px}.note.warning{background:#fbf3e8;border-color:#b37a27}.note.warning strong{color:#93621a}.flow{list-style:none;margin:20px 0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.flow li{position:relative;border:1px solid var(--line);padding:15px 16px;background:#f7f9fc;min-height:112px;border-radius:5px}.step{display:block;color:var(--blue);font-size:12px;font-weight:700}.flow strong{display:block;font-size:16px;margin:3px 0 6px}.flow li>span:last-child{display:block;font-size:13px;color:var(--muted)}.flow li:not(:last-child):after{content:'→';position:absolute;right:-12px;top:43px;z-index:1;background:white;color:#778a9c;font-size:16px}.two-col,.comparison-panels{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:17px 0}.plain-box,.comparison-panels>div{border:1px solid var(--line);padding:15px 18px;border-radius:5px}.plain-box h3,.comparison-panels h3{margin:0 0 10px}.plain-box p{font-size:14px;margin:0}.mini-row{display:grid;grid-template-columns:105px 1fr 55px;align-items:center;gap:9px;font-size:13px;margin:21px 0}.mini-row b{text-align:right}.mini-track{height:22px;background:#edf1f5}.mini-track i{display:block;height:100%}.result{font-size:19px;font-weight:700;margin:18px 0 0}.green-text{color:var(--green)}.red-text{color:var(--red)}.rule-grid{display:grid;grid-template-columns:190px 1fr;gap:30px;align-items:center;margin:20px 0 28px}.cell-demo{height:165px;border:2px solid #8b9cae;position:relative;background:#fafcfe;display:grid;place-items:center}.cell-center{width:66px;height:66px;background:#d2eadc;border:2px dashed var(--green);display:grid;place-items:center;font-size:12px;line-height:1.3;text-align:center;color:#205f41}.cell-label{position:absolute;bottom:-26px;font-size:12px;color:var(--muted)}.rule-grid h3{margin-top:0}.rule-grid p{font-size:14px}details{border:1px solid var(--line);border-radius:5px;margin:17px 0;font-size:14px}summary{padding:11px 15px;color:var(--blue);cursor:pointer;background:#f7f9fc}.detail-body{padding:3px 18px 16px}.source-row{padding:10px 0;border-bottom:1px solid var(--line);font-size:12px;overflow-wrap:anywhere}.source-row p{margin:4px 0}.bar-chart{display:block;width:100%;height:auto}.chart-title{font-size:16px;font-weight:700;margin-bottom:8px}.chart-label,.chart-value{font:14px "Microsoft YaHei",sans-serif;fill:var(--ink)}.chart-muted,.axis{font:12px "Microsoft YaHei",sans-serif;fill:var(--muted)}.grid{stroke:#e7edf3;stroke-width:1}.zero-line{stroke:#9aaabc;stroke-width:1.2}.gain{fill:var(--green)}.loss{fill:var(--red)}.neutral{fill:#899aaa}.gain-text{fill:var(--green)}.loss-text{fill:var(--red)}.neutral-text{fill:var(--muted)}figure{margin:20px 0 24px}.vector{border:1px solid var(--line);padding:18px 15px 10px;border-radius:5px}.figure-button{display:block;width:100%;background:white;padding:0;border:1px solid var(--line);border-radius:5px;cursor:zoom-in}.figure-button img{width:100%;height:auto;display:block}.figure-button:focus-visible,button:focus-visible,summary:focus-visible{outline:3px solid #78a4d0;outline-offset:3px}figcaption{font-size:13px;line-height:1.8;color:var(--muted);margin:10px 0}.legend{display:flex;gap:9px 18px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:5px 0 15px}.legend span{display:inline-flex;align-items:center;gap:5px}.legend i{width:13px;height:13px;display:inline-block;border:1px solid #a7b4c0}footer{font-size:12px;color:var(--muted);margin-top:22px}.modal[hidden]{display:none}.modal{position:fixed;inset:0;z-index:50;background:#172335ed;overflow:auto;padding:65px 22px 22px}.modal img{display:block;width:auto;max-width:none;height:auto;margin:0 auto}.modal button{position:fixed;top:15px;right:24px;padding:9px 18px;background:white;border:0;border-radius:5px;font:15px "Microsoft YaHei",sans-serif;cursor:pointer;z-index:51}.case-legend{font-size:12px;color:var(--muted)}
@media(max-width:800px){main{margin:0;padding:25px 20px}h1{font-size:27px}h2{font-size:22px}.flow{grid-template-columns:1fr 1fr}.flow li:after{display:none}.two-col,.comparison-panels{grid-template-columns:1fr}.rule-grid{grid-template-columns:130px 1fr;gap:19px}.cell-demo{height:130px}.cell-center{width:52px;height:52px}table{min-width:610px}.mini-row{grid-template-columns:105px 1fr 55px}.table-scroll{margin-right:-2px}.refs{white-space:normal}.chart-label,.chart-value{font-size:15px}nav{gap:8px 14px}}
@media(max-width:480px){main{padding:22px 16px}.rule-grid{grid-template-columns:1fr}.cell-demo{width:150px;margin:0 auto 16px}.flow{gap:9px}.flow li{padding:12px;min-height:128px}.flow strong{font-size:15px}.vector{padding:12px 6px}h1{font-size:25px}.lead{font-size:16px}}
@media print{body{background:white;font-size:9.5pt}main{max-width:none;margin:0;padding:0;box-shadow:none}.toolbar,nav,.modal{display:none!important}section{padding-top:17px;padding-bottom:15px;margin-top:0}h1{font-size:22pt}h2{font-size:15pt;break-after:avoid}h3{font-size:12pt;break-after:avoid}.section-kicker,.eyebrow{font-size:8pt}.lead{font-size:10.5pt}table{font-size:8pt;min-width:0}th,td{padding:6px 7px}.table-scroll{overflow:visible}.note{break-inside:avoid;font-size:9pt;padding:8px 11px}.flow{break-inside:avoid}.flow li{min-height:90px;padding:9px}.flow strong{font-size:10pt}.flow li>span:last-child{font-size:8.5pt}.flow .step{font-size:8pt}.two-col,.comparison-panels{break-inside:avoid}.mini-row{font-size:8.5pt;grid-template-columns:86px 1fr 45px}.plain-box p,.rule-grid p{font-size:9pt}.rule-grid{break-inside:avoid}.vector{padding:8px;break-inside:avoid}.vector p{font-size:8pt}figure{break-inside:avoid}figcaption{font-size:8pt}.refs{font-size:7pt}summary{font-size:9pt}.detail-body{font-size:9pt}details:not([open]){display:none}.result{font-size:12pt}a{color:inherit}footer{font-size:8pt}@page{size:A4;margin:16mm 15mm}}
'''
css+='\n.research-overview{display:flex;flex-wrap:wrap;align-items:center;gap:9px;padding:17px;background:#edf4f8;margin:20px 0 26px;font-size:13px}.research-overview span{background:white;border:1px solid var(--line);border-radius:4px;padding:7px 10px}.research-overview i{font-style:normal;color:var(--blue)}.research-step{border:1px solid var(--line);border-radius:7px;padding:22px 24px;margin:20px 0;background:white}.research-step-heading{display:flex;gap:13px;align-items:flex-start;margin-bottom:17px}.research-step-heading h3{margin:0;font-size:20px;line-height:1.55}.research-number{display:grid;place-items:center;background:var(--blue);color:white;border-radius:50%;width:31px;height:31px;flex:0 0 31px;font-size:15px;font-weight:bold}.research-reason{display:grid;grid-template-columns:78px 1fr;gap:12px;font-size:14px;margin:10px 0}.research-reason>b{color:var(--blue)}.research-reason p{margin:0}.research-step .note{margin:16px 0 8px}.research-next{display:flex;gap:14px;border-top:1px dashed #b9cad9;margin-top:16px;padding-top:13px;font-size:14px}.research-next>span{color:var(--blue);font-size:27px;line-height:1.3}.research-next b{color:var(--blue)}.research-next p{margin:3px 0 0}.research-fork{padding:20px;border:1px dashed #96aec4;background:#f4f8fb;margin:25px 0}.research-fork>b{color:var(--blue)}.research-fork .two-col{margin:10px 0}.research-fork a{padding:10px;background:white;border:1px solid var(--line);font-size:14px}.research-fork p{font-size:13px;color:var(--muted);margin:9px 0 0}\n@media(max-width:600px){.research-step{padding:17px 13px}.research-step-heading{gap:10px}.research-step-heading h3{font-size:18px}.research-reason{grid-template-columns:1fr;gap:3px}.research-step table{min-width:550px}.research-overview{gap:7px;padding:12px}.research-fork{padding:14px}}\n@media print{.research-step{padding:10px 12px;margin:12px 0;break-inside:auto}.research-step-heading,.research-reason,.research-next{break-inside:avoid}.research-step-heading h3{font-size:12pt}.research-number{width:23px;height:23px;flex-basis:23px;font-size:10pt}.research-reason,.research-next{font-size:9pt}.research-overview,.research-fork{break-inside:avoid}.research-step table{min-width:0}}\n'
css+='@media(max-width:800px){.vector{overflow-x:auto}.bar-chart{min-width:710px}}'
nav=''.join(f'<a href="#{sid}">{i+1}. {title}</a>' for i,(sid,title,_) in enumerate(sections))
js='''(()=>{document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{const target=document.getElementById(a.getAttribute('href').slice(1));if(target){let p=target.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement}}}));})();'''
css+='\n'+replay_css+'\n'+continuous_css+'\n'+attempt_css
js+='\n'+replay_js+'\n'+continuous_js+'\n'+attempt_js


document='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>汇报稿</title><style>'''+css+'''</style></head><body><main><header><h1>汇报稿</h1></header>'''+''.join(x[2] for x in sections)+source_details+'''</main><script>'''+js+'''</script></body></html>'''


class VisibleText(HTMLParser):
 def __init__(self):super().__init__();self.stack=[];self.default=[];self.all=[];self.tables=0;self.figures=0
 def handle_starttag(self,tag,attrs):
  if tag in ('details','script','style'):self.stack.append(tag)
  if tag=='table':self.tables+=1
  if tag=='figure':self.figures+=1
 def handle_endtag(self,tag):
  if tag in ('details','script','style') and self.stack and self.stack[-1]==tag:self.stack.pop()
 def handle_data(self,data):
  if any(x in self.stack for x in ('script','style')):return
  t=re.sub(r'\s+','',data)
  if not t:return
  self.all.append(t)
  if 'details' not in self.stack:self.default.append(t)

parser=VisibleText();parser.feed(document)
before=VisibleText();before.feed(BACKUP.read_text(encoding='utf-8'))
ids=set(re.findall(r'\bid="([^"]+)"',document));targets=re.findall(r'href="#([^"]+)"',document)
assert all(x in ids for x in targets)
assert len(ids)==len(re.findall(r'\bid="([^"]+)"',document))
assert [x[0] for x in sections]==['setup','compare','attempts','direct'] and parser.tables>=10
assert hashlib.sha256((H/'导师汇报稿_研究思路与实验证据.md').read_bytes()).hexdigest()==original_md_sha
TARGET.write_text(document,encoding='utf-8')
record=dict(version='HTML_V2_18_CONCEPTS_RETURN_SERVICE',updated_file=str(TARGET),backup=str(BACKUP),source_hashes_rechecked=len(source_manifest),source_reports_modified=0,markdown_unchanged=True,sections=len(sections),tables=parser.tables,figures=parser.figures,default_visible_characters=len(''.join(parser.default)),old_visible_characters=len(''.join(before.default)),details_collapsed_by_default=document.count('<details>'),anchor_links_checked=len(targets),original_pairs_used=len(pairs),variant_pairs_used=len(variants),timing_methods_checked=6,timing_individual_runs_checked=len(timing_runs),timing_table=timing_rows,new_planner_calls=0,new_post_calls=0)
(H/'HTML图表版修改与核对记录.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(record,ensure_ascii=False,indent=2))
