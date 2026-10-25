"""Offline report/structure recheck and diagrams only. No planner imports."""
import json,csv,statistics,hashlib,collections,math
from pathlib import Path
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
rows=read(H/'analysis.json');states=read(H/'states.json')
def table(h,rr):return '\n'.join(['|'+'|'.join(h)+'|','|'+'|'.join(['---']*len(h))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rr])
def avg(rr,k):
 xs=[r['metrics'][k] for r in rr if r['metrics'] is not None];return round(statistics.mean(xs),4) if xs else None
summ=[];details=[]
for s in states:
 c=read(H/'inputs'/(s['name']+'.json'));f=set(map(tuple,c['free']));h=set(map(tuple,c['covered']));pub=set(map(tuple,c['published_targets']));base=tuple(c['base'])
 assert set(map(tuple,c['deferred_targets']))==pub-f-h
 seen={base};front=[base]
 while front:
  x,y=front.pop()
  for p in ((x,y-1),(x-1,y),(x,y+1),(x+1,y)):
   if p in f and p not in seen:seen.add(p);front.append(p)
 assert seen==f
 old=read(H/'prep'/(s['prep']+'.json'))['result']['raw']['route'];idx=s['history_index'];assert h==set(map(tuple,old[:idx+1])) and c['current']==old[idx] and c['old_route']==old[idx:]
 rr={m:[r for r in rows if r['case']==s['name'] and r['method']==m] for m in ('PPCPP','P2_MULTI')}
 assert all(len(v)==3 for v in rr.values())
 d=dict(case=s['name'],kind=s['kind'],obstacle_percent=round(s['obstacle_fraction']*100,2),pending=s['pending'],deferred=s['deferred'])
 for m,v in rr.items():
  d[m+'_valid']=sum(r['valid'] for r in v);d[m+'_timely']=sum(r['timely'] for r in v);d[m+'_length']=avg(v,'length');d[m+'_mean_ms']=round(statistics.mean(r['seconds']*1000 for r in v),3)
 details.append(d)
 # Fixed repetition zero for all states, no winner-based selection.
 unit=12;ww=s['w']*unit+45;hh=s['h']*unit+75;svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{2*ww}" height="{hh}"><rect width="100%" height="100%" fill="white"/>']
 for panel,m in enumerate(('PPCPP','P2_MULTI')):
  x=read(H/'outputs'/f'{s["name"]}__0__{m}.json')['result'];route=x['raw'].get('route',[]);ox=panel*ww+20;oy=45
  svg.append(f'<text x="{ox}" y="18" font-size="11">{s["name"]} {m}</text><text x="{ox}" y="33" font-size="11">{len(route)-1 if route else "NO ROUTE"} steps</text>')
  def xy(p):return ox+(p[0]+.5)*unit,oy+(s['h']-p[1]-.5)*unit
  for p in pub:
   x0,y0=xy(p);color='#444' if p not in f else '#b8d4ef' if p in h else '#ddedc9';svg.append(f'<rect x="{x0-unit/2}" y="{y0-unit/2}" width="{unit}" height="{unit}" fill="{color}" stroke="white" stroke-width="0.3"/>')
  coords=' '.join(f'{x},{y}' for x,y in map(xy,route));svg.append(f'<polyline points="{coords}" fill="none" stroke="#c42d20" stroke-width="1"/>')
 svg.append('</svg>');(H/'figures'/(s['name']+'.svg')).write_text('\n'.join(svg),encoding='utf8')
for kind in ('all','control','serpentine','rooms','maze'):
 names={s['name'] for s in states if kind=='all' or s['kind']==kind}
 for m in ('PPCPP','P2_MULTI'):
  rr=[r for r in rows if r['case'] in names and r['method']==m]
  summ.append([kind,m,len(rr),sum(r['valid'] for r in rr),sum(r['timely'] for r in rr),avg(rr,'length'),round(statistics.mean(r['seconds']*1000 for r in rr),3),avg(rr,'turns90'),avg(rr,'turns180')])
pairs=[]
for kind in ('all','control','events','serpentine','rooms','maze'):
 names={s['name'] for s in states if kind=='all' or kind=='events' and s['kind']!='control' or s['kind']==kind};aa=[];bb=[]
 for n in names:
  for rep in range(3):
   g={r['method']:r for r in rows if r['case']==n and r['rep']==rep}
   if all(r['timely'] for r in g.values()):aa.append(g['PPCPP']['metrics']['length']);bb.append(g['P2_MULTI']['metrics']['length'])
 ds=[a-b for a,b in zip(aa,bb)];pairs.append(dict(kind=kind,total_pairs=len(names)*3,timely_pairs=len(ds),PPCPP_short=sum(d<0 for d in ds),equal=ds.count(0),PPCPP_long=sum(d>0 for d in ds),relative_total_gap_percent=100*(sum(aa)/sum(bb)-1) if bb else None))
all_pairs=[]
for kind in ('all','control','events','serpentine','rooms','maze'):
 names={s['name'] for s in states if kind=='all' or kind=='events' and s['kind']!='control' or s['kind']==kind};aa=[];bb=[]
 for n in names:
  for rep in range(3):
   g={r['method']:r for r in rows if r['case']==n and r['rep']==rep}
   if all(r['valid'] for r in g.values()):aa.append(g['PPCPP']['metrics']['length']);bb.append(g['P2_MULTI']['metrics']['length'])
 ds=[a-b for a,b in zip(aa,bb)];all_pairs.append(dict(kind=kind,total_pairs=len(names)*3,legal_pairs=len(ds),PPCPP_short=sum(d<0 for d in ds),equal=ds.count(0),PPCPP_long=sum(d>0 for d in ds),relative_total_gap_percent=100*(sum(aa)/sum(bb)-1) if bb else None))
save=dict(summary=summ,pairs=pairs,all_legal_pairs=all_pairs,states=details,independent_geometry_history_check=True,new_solver_calls=0)
(H/'report_data.json').write_text(json.dumps(save,ensure_ascii=False,indent=2),encoding='utf8')
lines=['# 复杂障碍压力开发测试结果','2026-10-21。2真实历史准备＋96正式入口；16状态中12事件、4无障碍控制。每输入两个冻结方法、3种子；20秒共同预算。无重试/留出/新算法。以下平均步数仅对有合法输出者计算，必须同时阅读及时分母。',table(['布局','方法','调用','合法完整','及时','平均步数','平均入口ms','平均90度','平均180度'],summ),'## PPCPP相对P2：共同及时配对',table(list(pairs[0]),[list(p.values()) for p in pairs]),'## 全部合法返回配对（含迟到，不是20秒成绩）',table(list(all_pairs[0]),[list(p.values()) for p in all_pairs]),'## 全部状态',table(list(details[0]),[list(d.values()) for d in details]),'## 解释边界','实际事件障碍率约28%至55%。迷宫和长墙通道很多，拓扑复杂与高障碍率不意味着所有方法一定困难；不预设PPCPP会失效。三结构由固定模板构造，只有两个基础尺寸、两段历史，不代表现场分布或普遍极端场景。','障碍遮挡的未检目标记暂缓，公开目标覆盖率不能混同当前可检覆盖率。控制与事件的待检任务量不同，不用事件绝对路程变短证明优化。主比较只在同一输入两算法之间进行。P2不是精确最优参照。','图示固定重复0，figures包含全部状态，两方法并排。绿为待检域中的非历史可飞格，蓝为历史可飞格，灰为障碍；灰格含已采后遮挡与未采暂缓，不均计未完成。重叠线不能看出经过次数，以指标CSV为准。','每次入口沿用既有PPCPP/P2完整暖入口，原生P2软截止单列。输入/程序/相关依赖分准备前与正式前封存，实际worker核项目模块；系统DLL/未发现动态依赖限制保留，非全机镜像。','正式结果逐格双指标复核；报告另用独立遍历核对全部连通域、真实历史前缀/旧后缀与暂缓账本。未重新执行全部既有核心机制门槛，也未宣称新增候选优化或最优性证明。','完整数据：完整调用指标.csv、analysis.json、states.json、report_data.json、原始outputs与两阶段seal。只读核验：`./运行环境/python/python.exe -B -X utf8 ./复杂障碍压力开发测试_v0.1_20261021/stress.py verify`。']
(H/'压力测试结果.md').write_text('\n\n'.join(lines),encoding='utf8')
(H/'manifest.json').write_text(json.dumps({str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log')},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(pairs,ensure_ascii=False))
