import os,statistics
from support import *
def table(head,rows):return '\n'.join(['|'+'|'.join(map(str,head))+'|','|'+'|'.join('---' for _ in head)+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def write(name,s):
 with (H/name).open('x',encoding='utf-8') as f:f.write(s)
def main():
 d=read(H/'analysis.json');p=read(H/'protocol.json');lines=['# PPCPP＋局部P2受控混合诊断\n\n2026-10-20。**已封存，待负责人审核。** 固定18事件＋18同历史无新增障碍控制，3方法×3种子=324正式入口；固定窗口、20秒、串行新进程，不使用留出/精确/四方向/LAST/新奖励。\n']
 for kind in ('event','control'):
  s=d['summary'][kind];states=[x for x in d['states'] if x['kind']==kind];good=[x for x in states if x['saved'] is not None];saved=sum(x['saved'] for x in good);base=sum(x['methods']['PPCPP']['mean'] for x in good);glob=sum(x['methods']['P2_MULTI']['mean'] for x in good if x['methods']['P2_MULTI']['mean'] is not None);mix=sum(x['methods']['LOCAL_P2']['mean'] for x in good)
  lines += [f'## {kind}：完整入口结果\n',f'18状态三种子均值求和（仅完整配对状态，N={len(good)}/18）：PPCPP={base:.6f}，混合={mix:.6f}，整体P2={glob:.6f}；混合相对原版省{saved:.6f}步（{saved/base*100 if base else 0:.4f}%）。相对整体P2仍差{mix-glob:.6f}步；未取最好种子。\n',table(['方法','调用N','合法','及时','迟到合法','无路线','入口均值/中位/P95/最大ms','原生状态','最终来源'],[[m,v['N'],v['valid'],v['timely'],v['late'],v['no_route'],'/'.join(f'{v["entry"][k]*1000:.6f}' for k in ('mean','median','p95','max')),v['status'],v['sources']] for m,v in s['counts'].items()]),'\n',table(['混合参照','视图','配对N/54','短/平/长','混合/参照总步','省步'],[[x['reference'],x['view'],x['N'],f'{x["short"]}/{x["equal"]}/{x["long"]}',f'{x["local_total"]}/{x["reference_total"]}',x['saved']] for x in s['pairs']]),'\n']
  rr=[x for x in d['calls'] if x['kind']==kind and x['method']=='LOCAL_P2'];active=[x for x in rr if x['window'] and not x['window']['empty']];win=[x['window'] for x in active]
  lines.append(f'混合该组54次：空窗{sum(bool(x["window"] and x["window"]["empty"]) for x in rr)}；实际局部核心{sum(x["internal_calls"].get("local_P2",0) for x in rr)}。非空窗任务占比min/mean/max='+('/'.join(f'{fn([w["task_fraction"] for w in win]):.6f}' for fn in (min,statistics.mean,max)) if win else '不适用')+'；步长占比min/mean/max='+('/'.join(f'{fn([w["step_fraction"] for w in win]):.6f}' for fn in (min,statistics.mean,max)) if win else '不适用')+'。窗口大是观察事实，不加80%切换或扩窗。')
  incidental=sum(bool(x['audit'].get('incidental_external')) for x in active);lines.append(f'实际记录提前采到外部后缀任务的局部调用{incidental}；未出现不等于实现禁止。后缀保持原样，完整逐格指标自然把后续到达记为重复。\n')
 lines += ['## 有限继续信号与边界\n',f'预登记事件收益信号：{d["continue_signal"]}。只按至少两族、四不同base_id且全三重复及时完整严格改善判断；同一几何不同进度不重复计独立几何。达到也不是创新或同预算优于全局P2，未达到也只否定本窗口/固定接口的本批信号。\n',
 '控制也改善时，不能称收益由障碍专门造成；事件/控制任务量因遮挡不同，不能把两者路线差直接当障碍损失。保留外部计划与固定接口可能限制收益，18事件/18控制共享9基础道路和同一PPCPP历史，三种子不是独立地图。混合若更快但仍明显长于整体P2，只是质量—时间折中，不满足主路线优势目标；本轮完成即停止，不扩大窗口追赶。\n',
 '## 接口、责任与预算\n','每混合入口重新计时运行原PPCPP P0，不用计时外旧结果；半径2曼哈顿只做事件位置选区。种子是未采可检目标；按首次有效采集索引min..max各扩一个顶点。局部H=原H加含入口的原前缀目标；required为left<i<=right首次采集，含必要出口任务，不把入口重复分派。局部base是固定出口，不是真实基地；真实基地由保留后缀返航。局部free始终完整当前F，old_route是原窗口合法段，距离额度扣固定外部步数。\n',
 '复用已有range_p2_engine_20261015，不改冻结搜索。local_engine.diff记录其相对冻结P2的既有accept回调差异；回调同时审核局部任务/出口/资源和完整拼接。该混合不复用旧范围的多窗口规则或全局保底：P2的old_suffix/common_fallback均运行在局部Snapshot上，来源完整保留。非时间非法/异常显式失败，不静默成功回P0。无改进/同值保留完整P0，严格全长更短才选拼接。P0包含原候选所以成功时不更长是构造属性。\n',
 '前缀/后缀逐点字面保留；拼接只消除接口重复顶点。每个offer完整审核、选区/局部P2/拼接/比较/完整raw编码均在共同20秒暖入口，局部只获余量。整体晚到清空route，不捞P0；全局P2原生软截止保留，再用真实入口时间分及时/迟到。启动/导入/磁盘/独立外审在外，90秒只作硬看门狗。外审每次时间在analysis.calls单列，工作量不同不拼成算法速度排名。\n',
 f'实际正式核心调用：{d["internal_calls"]}；324是完整入口，不是核心次数。混合P0与同批原版完整route/trace等非时间字段配对{d["P0_pairs"]}/108通过。24门槛入口另账；桩测试不作真实核心调用。\n',
 '## 全指标（均为三种子调用级计数，分母列出）\n',table(['组','方法','视图','N','步数','新采集','历史重复','本轮重复','非目标','90°','180°','采完步号','返航尾段','公开完成/公开','暂缓'],[[r['kind'],r['method'],r['view'],r['totals']['N'],*[r['totals'].get(k) for k in ('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps')],f'{r["totals"].get("published_covered")}/{r["totals"].get("published_targets")}',r['totals'].get('deferred')] for r in d['metric_totals']]),'\n',
 '指标定义：一步为一次四邻接等长移动，落点互斥分成首次未采目标/历史目标/本轮已采目标/非目标，四类之和=length。采集完成步号+返航尾段=length，两类分解不能相加。duplicate_target_arrivals=历史重复+本轮重复；重复率=duplicate/target_arrivals，无到达时不适用。90/180按连续移动向量点积0/-1计数，不推真实能耗。当前可检覆盖和剩余完成独立于公开完成率；deferred不计完成，历史后遮挡H保留。控制恢复本次B后若已在H仍算历史，不重复当新任务。\n',
 '## 分层（同组、同输入/种子及时配对，混合对原版）\n',table(['因素','层','组','N','短/平/长','省步','混合/原版/整体P2均值ms'],[[r['factor'],r['value'],r['kind'],z['N'],f'{z["short"]}/{z["equal"]}/{z["long"]}',z['saved'],'/'.join(f'{r["summary"]["counts"][m]["entry"]["mean"]*1000:.6f}' for m in ('LOCAL_P2','PPCPP','P2_MULTI'))] for r in d['strata'] for z in [next(v for v in r['summary']['pairs'] if v['reference']=='PPCPP' and v['view']=='timely')]]),'\n',
 '完整三种子原值/均值/范围、全部分层对两参照与双视图见36状态三种子与窗口.csv、analysis.strata、324调用完整指标.csv及双视图配对.csv。不把不同成功集的总量直接当全批优势；任何失败保留分母，不补0步。\n']
 # Fixed event-based selection, then attach its control. Repetition0 throughout.
 choices={}
 for family in ('I','L','Z'):
  rr=[s for s in d['states'] if s['kind']=='event' and s['family']==family and s['saved'] is not None];pos=sorted([s for s in rr if s['saved']>0],key=lambda s:(s['saved'],s['id']));zero=sorted([s for s in rr if s['saved']==0],key=lambda s:s['id'])
  choices[family]=dict(maximum=min(pos,key=lambda s:(-s['saved'],s['id']))['id'] if pos else None,median=pos[(len(pos)-1)//2]['id'] if pos else None,zero=zero[0]['id'] if zero else None)
 save(H/'figure_selection.json',choices);plot(d,p,choices)
 lines.append('## 固定案例（重复0，同时附控制）\n')
 for fam,cc in choices.items():
  for role,ident in cc.items():
   if ident is None:lines.append(f'{fam}/{role}缺类，不补。\n');continue
   lines.append(f'### {fam}/{role}：{ident}\n')
   for kind in ('event','control'):
    cid=ident.replace('__event','__'+kind);rec=next(c for c in d['calls'] if c['id']==cid and c['method']=='LOCAL_P2' and c['repetition']==0);cfg=rec['window'];lines.append(f'{kind}：入口/出口={None if cfg["empty"] else (cfg["entry"],cfg["exit"])}，原窗口/局部步长={rec["original_patch_steps"]}/{rec["local_steps"]}，来源={rec["source"]}，局部核心来源={rec["local_source"]}。\n\n![{cid}](figures/{cid}.png)\n')
    lines.append(table(['方法','总步','末采集格','采集前/尾段','非目标','历史/本轮重复','入口秒'],[[m,rec2['metrics']['length'],last(read(next(i['payload'] for i in p['inputs'] if i['id']==cid))['state'],read(H/rec2['output'])['raw']['route']),f'{rec2["metrics"]["completion_step"]}/{rec2["metrics"]["return_tail_steps"]}',rec2['metrics']['non_target_steps'],f'{rec2["metrics"]["historical_target_steps"]}/{rec2["metrics"]["repeated_new_target_steps"]}',f'{rec2["entry_seconds"]:.6f}'] for m in ('PPCPP','LOCAL_P2','P2_MULTI') for rec2 in [next(c for c in d['calls'] if c['id']==cid and c['method']==m and c['repetition']==0)]]))
 lines += ['## 前置证据、失败记录与停止\n','18事件输入源hash与原件一致；每一控制从同基础图事件前prep输入恢复且核history/witness/cut/old_route，不重跑历史。全环境事前封存覆盖包内Python、项目.deps源/二进制/元数据、实际导入、可识别非系统DLL、原始来源/所有输入/协议/执行与独立审核源码；前后重核、每worker导入hash/唯一payload读取均保存。Windows系统DLL只记录路径，未知动态加载限制见environment_seal，不宣称全机复现。\n',
 '前置基础设施故障：environment.py以同名audit导入冻结模块，AttributeError发生在0求解；environment_v02绝对路径加载离线审核，原脚本/日志保留。随后第一次gates_v02因封存异步未写完而FileNotFoundError，仍0求解；等待封存完整后相同gates_v02运行24真实入口及桩门槛通过（completed日志），没有增加门槛或重复正式成绩。两项记录于failures.json，不声称全流程一次通过。\n',
 '桩明确区分：指定局部patch强制经过外部未采目标，核真实采集与后缀不删；不谎称所有可行路径都必经该外部目标，因为合法原窗口本身已经提供另一条路线。非法/异常/同值/更短及共享时钟各阶段也仅为桩，不当真实P2路线证据。\n',
 '局部核心省步与完整拼接省步的恒等关系已逐调用验证，最终严格择优仍保留原PPCPP；不能把未选的较长局部路线当收益。全局未优化的外部段仍可能造成差距；固定接口的约束与PPCPP顺序混在一起，本轮没有独立归因。若固定规则无收益，不推广为所有混合方案无效。\n',
 '固定324调用后停止，不扩大半径/窗口、不加阈值或1秒批、不恢复四方向、不叠加LAST、不自动下一轮。已封存，待负责人审核。\n',
 '只读命令：`./运行环境/python/python.exe -B -X utf8 PPCPP局部P2混合开发诊断_v0.1_20261020/verify.py`。不启动规划器、不追加计时。\n']
 write('混合方案结果报告.md','\n'.join(lines))
 save(H/'failures.json',dict(formal_technical_failures=0,formal_entries=324,gate_entries=24,pre_gate_failures=[dict(log='environment.log',reason='audit name collision;0 solver calls',successor='environment_v02.py'),dict(log='gates_v02.log',reason='async seal not ready;0 solver calls',successor='same gates_v02 after final seal complete')],formal_invalidated=0,formal_reruns=0,formal_statuses={k:v['counts'] for k,v in d['summary'].items()}))
 write('README.md','# PPCPP局部P2混合诊断\n\n已封存，待负责人审核。结果见混合方案结果报告.md。36输入/来源协议、local_engine.diff、事前environment_seal、24门槛及桩、324 jobs/execution/logs/actual_order、analysis/全CSV/固定事件与控制图、failures/review_packet、manifest与verify齐全。旧冻结/历史/留出不改。\n\n原environment.py同名模块故障和一次封存未就绪均发生于0求解，原日志保留；完成后继环境封存后才运行24实际门槛。正式不使用测试钩子。\n\n只读核验：包内Python -B -X utf8 本目录/verify.py。manifest仅排除自身和verify.log。\n')
 write('review_packet.md','# 审核包\n\n已封存，待负责人审核。先核18事件与控制的before/prep/witness原hash及真实前缀，不用猜测差分。protocol/预登记固定radius2单窗口、接口责任、三种子顺序/324上限。local_engine.diff显示复用原accept副本；冻结原算法不修改，局部base为出口、H为真实前缀、fullF、old_route为原窗口。audit.py独立重建first-index/window/H/required并验固定前后缀、local出口/任务、完整双指标及严格择优；不使用hybrid.window作为oracle。\n\n查看门槛24真实入口及stub_gates，前置两次0求解基础设施失败均保留。查看environment_seal完整相关依赖事前字节与系统范围限制；run前后全核，每worker实际导入hash/唯一payload路径。\n\n324不是全部核心次数，真实计数analysis.internal_calls；事件/控制分别三种子均值与原值、两参照/双视图、分层/窗口占比、转弯/时间/重复分解齐全。控制也改善不能称障碍专用。固定图按事件收益预定规则选且附匹配控制，缺类不补，不伪造P2中间路线。\n\nverify只读重审环境/输入来源/324全部路线、窗口责任/接口/选择/计数、配对/CSV；不运行规划器。主目标是同预算完整路线，不因混合更快就宣布胜全局P2；固定批已停，是否继续由负责人裁决。\n')
 print('REPORT/FIGURES/REVIEW COMPLETE')
def last(c,path):
 pending=pts(c['targets'])-pts(c['covered']);v=None
 for q in map(tuple,path):
  if q in pending:pending.remove(q);v=q
 return v
def plot(d,p,choices):
 sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-smallgap-plot-deps'))
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 out=H/'figures';out.mkdir(exist_ok=True)
 ids=sorted({v for c in choices.values() for v in c.values() if v})
 for ident in ids:
  for kind in ('event','control'):
   cid=ident.replace('__event','__'+kind);env=read(next(i['payload'] for i in p['inputs'] if i['id']==cid));c=env['state'];fig,axes=plt.subplots(1,3,figsize=(16,5.5))
   rec=next(x for x in d['calls'] if x['id']==cid and x['method']=='LOCAL_P2' and x['repetition']==0);cfg=rec['window']
   for ax,m in zip(axes,('PPCPP','LOCAL_P2','P2_MULTI')):
    x=next(x for x in d['calls'] if x['id']==cid and x['method']==m and x['repetition']==0);raw=read(H/x['output'])['raw'];route=raw['route'];F=pts(c['free']);pub=pts(c['published_targets'])
    for cells,color,size in [(F,'#eeeeee',8),(pub-F,'#222222',12),(pts(c['targets']),'#b5d8a1',13),(pts(c['covered']),'#888888',8),(pts(env['marker']),'#e94c4c',25)]:
     if cells:xx,yy=zip(*cells);ax.scatter(xx,yy,c=color,s=size,marker='s')
    if not cfg['empty']:
     req=cfg['required']
     if req:xx,yy=zip(*req);ax.scatter(xx,yy,c='gold',s=20,marker='s')
     ax.scatter(*cfg['entry'],c='purple',marker='>',s=65);ax.scatter(*cfg['exit'],c='black',marker='<',s=65)
    if route:xx,yy=zip(*route);ax.plot(xx,yy,c='tab:blue',lw=.9)
    if m=='LOCAL_P2' and raw.get('local') and raw['local']['route']:
     xx,yy=zip(*raw['local']['route']);ax.plot(xx,yy,c='darkorange',lw=1.6)
    ax.scatter(*c['current'],c='red',marker='*',s=70);ax.scatter(*c['base'],c='black',marker='D',s=25);ax.set_aspect('equal');ax.set_title(f'{m}: L={x["metrics"]["length"] if x["metrics"] else "none"}\n{x["entry_seconds"]:.5f}s, timely={x["timely"]}')
   fig.suptitle(cid+' | seed20261020 | B red, responsibility gold, entry/exit arrows\nBlue actual final route; orange local proposal (may be rejected), literal outer route retained');fig.tight_layout();fig.savefig(out/(cid+'.png'),dpi=140);fig.savefig(out/(cid+'.svg'));plt.close(fig)
if __name__=='__main__':main()
