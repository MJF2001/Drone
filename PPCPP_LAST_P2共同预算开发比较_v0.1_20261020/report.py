"""Report, fixed diagnostic figures and review packet from saved outputs."""
import os,statistics,difflib
from collections import defaultdict
from support import *
def table(head,rows):return '\n'.join(['|'+'|'.join(map(str,head))+'|','|'+'|'.join('---' for _ in head)+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])
def write(name,s):
 with (H/name).open('x',encoding='utf-8') as f:f.write(s)
def main():
 d=read(H/'analysis.json');protocol=read(H/'protocol.json');calls=d['calls'];lines=['# LAST V2与P2共同预算开发比较\n\n2026-10-20。**执行完成，待负责人审核。** 54已见状态、三方法、1/20秒、三种子，972调用全部保留。不是留出/最优性/论文创新证据，不预设赢家。\n']
 lines += ['**本批结果不支持LAST相对P2的路线竞争优势。** 20秒双方162/162及时合法，LAST对P2为0短38平124长，总16428对13180步（按54状态三种子均值求和为5476对4393.333333），LAST多24.6434%。P2显著多花实际计算时间，但路线更短；不能称LAST支配。1秒P2全部162返回合法，其中125及时、37迟到；及时配对LAST0短38平87长（N125），软返回配对0短38平124长（N162），不能把后者当严格截止胜率。\n',
 'LAST原PPCPP上的收益仍存在（每预算5530→5476、27短27平），但不足支持本批强主算法竞争力。本轮停止，不立即添加规则追赶P2。\n',
 '流程记录：独立审核与analysis.json已成功生成，随后CSV导出因重复lengths/entry_times关键字报TypeError；原analyze.py/analysis.log保留。export_v02.py只从未改analysis.json补出剩余CSV和失败说明，0正式失效/重跑，不把这次导出故障隐藏为全流程一次通过。\n']
 for b in ('1','20'):
  summ=d['summary'][b];lines += [f'## {b}秒：完整交付与原生返回\n',table(['方法','N','合法','及时','迟到合法','无路线','非法','>10ms','入口均值/中位/P95/最大秒','外审均值秒','原生状态','来源'],[[m,v['N'],v['valid'],v['timely'],v['late'],v['no_route'],v['invalid'],v['overrun_gt_10ms'],'/'.join(f'{v["entry"][k]:.6f}' for k in ('mean','median','p95','max')),f'{v["external_audit"]["mean"]:.6f}',v['native_status'],v['sources']] for m,v in summ['counts'].items()]),'\n',table(['a','b','视图','配对N/162','a短/平/长','同配对a/b总步数','a−b','逐配对相对差均值'],[[c['a'],c['b'],c['view'],c['N'],f'{c["short"]}/{c["equal"]}/{c["long"]}',f'{c["a_total"]}/{c["b_total"]}',c['delta'],c['mean_relative']] for c in summ['comparisons']]),'\n']
  for c in summ['comparisons']:
   if c['a']!='LAST_V2' or c['b']!='P2_MULTI':continue
   groups=defaultdict(list)
   for x in c['pairs']:groups[x['case_id']].append(x)
   complete={k:v for k,v in groups.items() if len(v)==3};means=[statistics.mean(x['delta'] for x in v) for v in complete.values()]
   lines.append(f'{c["view"]}：LAST–P2共有{len(complete)}/54状态三种子均成对，按三种子均值LAST短/平/长={sum(v<0 for v in means)}/{sum(v==0 for v in means)}/{sum(v>0 for v in means)}。不完整状态不补0步。')
   if c['N']==162:lines.append(f'该视图三种子均完整的54状态等权总量（每状态三种子均值再求和）：LAST={c["a_total"]/3:.6f}，P2={c["b_total"]/3:.6f}；原配对总量是162次，不能叫162张图。')
   if c['N']==0:lines.append('没有及时合法配对，无法据本视图判断谁路线更短。软截止合法返回视图只能诊断路线质量，不是严格截止胜率。')
   contributions={k:sum(x['delta'] for x in v) for k,v in groups.items()};den=sum(abs(v) for v in contributions.values())
   if contributions:
    key=min(contributions,key=lambda k:(-abs(contributions[k]),k));lines.append(f'最大绝对状态贡献：{key}，三种子配对有符号差合计{contributions[key]}，占所有状态绝对贡献和{abs(contributions[key])/den if den else 0:.6f}；正负贡献可能抵消，不能把此占比误作净差占比。')
  lines.append('\n')
 lines += ['## 协议、接口和计时解释\n','预算是最大可用时间，PPCPP/LAST自然结束即返回，不空等；相同上限不等于相同CPU用量。共同暖入口包含解码/验证/Snapshot、契约、全部几何/搜索/offer内部合法性检查及完整原raw JSON编码；启动/导入/磁盘和独立外审在外。P2薄适配复现baseline_suite的P2分支，仅绕过其设置seconds之后的外部audit；源码p2_adapter.py、接口差异adapter_scope.md。原P2搜索/保底/权重/缓存/中止频率不变。\n',
 '原生deadline可以返回内部已接受路线，P2不清空；LAST保持原整体晚到拒收，不捞中间P0。实际交付按route_valid且entry_seconds<budget；软视图只要求实际返回合法路线，保留所有迟到。两个视图分预算、同输入同种子配对；失败不计0步，不从不同成功集合总量造排名。P2若贴线迟到是原生预算耗尽加返回/编码成本的观测，不能据此说LAST全面优越。\n',
 '外审时间是本轮离线审核阶段独立测量，未加入入口；LAST包含全分支奖励/BFS/采集审核，P2只对实际原生返回及阶段/接受记录审核，两种外审任务不同，不能把外审时间拼成算法速度排名。native_seconds与entry_seconds起点不同；原生接受记录相对P2内核开始，不能直接用它替代实际入口交付时刻。原事件和全部接受记录完整保存，未把最后接受时间当按时交付。\n',
 '## 门槛和环境\n','49固定门槛完成：9夹具×原P2/适配器/PPCPP/LAST=36；LAST九个已完成P0后的共同截止注入=9；P2原/适配在接受前/保底接受后截止=4。九P2夹具自然完成或原环境不可行处理的完整非时间结果对照一致；时钟插桩仅隔离门槛，正式未插桩。保底已观察，未观察到的来源不臆称覆盖；门槛原件及来源见gates/。缓存Spy证明两个求解对象不共享cache/distance_rows；合法迟到分类单元验证保留路线但不进入及时视图。\n',
 f'事前最终封存{len(read(H/"environment_seal.json")["files"])}文件，覆盖包内Python、.deps全源/二进制/元数据、冻结源码配置、实际导入链和可识别非系统DLL、项目生产/审核/输入/配置。在任何规划器调用前，先发现并补足独立审核与输入配置范围，再封存最终清单；environment_discovery_v01保留，非事后补录。每worker验证完成标志、实际导入哈希和唯一输入读取，整批前后全清单重核；Windows系统DLL仅记路径，未覆盖全机或不可发现动态加载依赖，限制明确保留。没有升级依赖或改导入链。\n',
 f'LAST所有完成分支逐决策及双指标重核；P0与同批原PPCPP自然完成配对{d["P0_pairs"]}/324一致。三方法每条返回路线均双指标核验原F/四邻接/覆盖/历史/暂缓/返航和距离预算。P2来源必须等于最后改进记录来源、路线步数必须等于最后接受步数，接受改进严格变短；原阶段和core_finished保留。\n',
 '## 分层\n',table(['因素','层','状态','预算','及时N 短/平/长','软返回N 短/平/长','软返回LAST−P2'],[[s['factor'],s['value'],s['states'],b,*[f'{c["N"]} {c["short"]}/{c["equal"]}/{c["long"]}' for c in [next(c for c in s['summary'][b]['comparisons'] if c['a']=='LAST_V2' and c['b']=='P2_MULTI' and c['view']==v) for v in ('timely_valid','route_valid')]],next(c['delta'] for c in s['summary'][b]['comparisons'] if c['a']=='LAST_V2' and c['b']=='P2_MULTI' and c['view']=='route_valid')] for s in d['strata'] for b in ('1','20')]),'\n',
 '## 完整指标与三种子\n','972调用与完整指标.csv含每次所有指标，324状态预算方法三种子.csv列三原值/均值/范围/计时/稳定性；不得取最好种子代表P2。analysis.metric_totals保留各方法各视图分母，覆盖率等比例不能跨不同成功集直接比较。下列按各自返回合法视图列分母和重复级计数，并非不同成功集上的胜负判定。\n',table(['预算','方法','N','总步','新采集','历史重复','本轮重复','非目标','90度','180度','完成步号合计','返航尾段','公开完成/公开','暂缓'],[[r['budget'],r['method'],r['N'],*[r['totals'].get(k) for k in ('length','fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','turns90','turns180','completion_step','return_tail_steps')],f'{r["totals"].get("published_covered")}/{r["totals"].get("published_targets")}',r['totals'].get('deferred')] for r in d['metric_totals'] if r['view']=='route_valid']),'\n']
 # Budget increase: pair exact same input/seed, native-valid in both budgets.
 ix={(x['case_id'],x['repetition'],x['budget']):x for x in calls if x['method']=='P2_MULTI'};delta=[]
 for i in protocol['inputs']:
  for rep in range(3):
   a=ix[i['id'],rep,1];b=ix[i['id'],rep,20]
   if a['route_valid'] and b['route_valid']:delta.append(b['metrics']['length']-a['metrics']['length'])
 lines += [f'P2预算增加1→20秒，同状态同种子双方合法返回配对N={len(delta)}；20秒短/平/长={sum(x<0 for x in delta)}/{sum(x==0 for x in delta)}/{sum(x>0 for x in delta)}，步数差合计{sum(delta)}。这是预算敏感诊断，未把20秒成绩混入1秒。\n',
 'native_seconds列在PPCPP/LAST中是P0内核秒数（LAST不包含P1），在P2中是适配器原生分支秒数，不能混作三方法完整内核排名。统一排名只看完整entry_seconds。P2没有PPCPP式trace，状态CSV中的stable_trace对P2只反映字段缺省，不构成P2决策稳定证据；P2实际路线稳定性与三种子范围另列。\n']
 # Figure selectors fixed in preregistration, soft native-valid view.
 pairs=[dict(**q,budget=int(b),view='route_valid') for b,s in d['summary'].items() for c in s['comparisons'] if c['a']=='LAST_V2' and c['b']=='P2_MULTI' and c['view']=='route_valid' for q in c['pairs']]
 choices={}
 for label,pred,key in [('LAST_short',lambda q:q['delta']<0,lambda q:(q['delta'],q['case_id'],q['budget'],q['repetition'])),('P2_short',lambda q:q['delta']>0,lambda q:(-q['delta'],q['case_id'],q['budget'],q['repetition'])),('equal',lambda q:q['delta']==0,lambda q:(q['case_id'],q['budget'],q['repetition']))]:
  arr=sorted(filter(pred,pairs),key=key);choices[label]=arr[0] if arr else None
 bad=sorted([x for x in calls if x['late_valid'] or not x['has_returned_route']],key=lambda x:(x['case_id'],x['budget'],x['repetition'],x['method']));choices['late_or_missing']=bad[0] if bad else None
 save(H/'figure_selection.json',choices);plot(choices,calls,protocol)
 lines.append('## 固定正反图\n')
 for label,q in choices.items():
  if q:
   lines.append(f'{label}：{q["case_id"]}，预算{q["budget"]}秒、seed={20261020+q["repetition"]}，视图={q.get("view","actual delivery: late/missing")}。\n\n![{label}](figures/{label}.png)\n')
  else:lines.append(f'{label}类别缺失，不补图。\n')
 lines += ['## 结论边界与停止\n','根据上列两预算/两视图的配对结果判断路线差距；及时配对不足时必须保持无法判断，不能利用P2原生软截止状态制造全面胜出。LAST在原PPCPP上的既有改进并不自动说明相对P2竞争力；P2是强自建工程基线，不是论文算法，也不能推导其他基线更弱。总步数、90/180度转弯、计算及交付率分别列出，不新增能耗权重改变胜负。\n','54全是已见开发状态，共享9道路与单一历史规划器；无未知大图、紧资源、多历史规划器或留出证据，不确认主算法/创新。固定972调用结束即停，不加算法/地图/种子/预算、不调LAST/P2、不跑最优或留出、不提交推送。\n','复核：`./运行环境/python/python.exe -B -X utf8 PPCPP_LAST_P2共同预算开发比较_v0.1_20261020/verify.py`。只读复核，不运行规划器。\n']
 write('LAST与P2共同预算比较结果.md','\n'.join(lines))
 write('adapter_scope.md','''# P2薄适配范围

p2_adapter.solve逐项对应冻结baseline_suite.solve的P2分支：begin、check_contract、remaining、multi/seed调用、仅捕获精确infeasible input的ValueError、seconds/method/budget/seed/fallback/超限标记不改。省略且仅省略外部independent_audit字段和assert，该审计在本轮计时外用双指标执行；原offer的single_cell_audit仍留在冻结内核。外层run_payload添加与LAST相同的解码/验证/Snapshot和原raw完整JSON编码，不改原生deadline路线。三方法同输入，保底/旧后缀利用是方法差异，不抹掉。

原baseline_suite.solve本体和p2_search_audit均不修改；适配器是透明重写薄包装，不称原函数直接字节调用。9固定夹具原包装与适配完整非时间结果门槛通过，比较仅去时间/外部审核字段；截止钩子另验保底保留与无接受不补全。正式不作插桩。
''')
 write('README.md','''# LAST V2与P2共同预算开发比较

执行完成，待负责人审核。先读LAST与P2共同预算比较结果.md；完整证据为protocol/预登记、9381事前环境封存（初次发现记录另存）、54输入hash、49门槛、972 jobs/execution/logs/actual_order、analysis双视图/三种子CSV/分层/全部指标、固定正反图、adapter_scope/p2_adapter源码、failures、manifest与verify.py。旧冻结及历史不改，最终留出不用。

只读命令：包内Python -B -X utf8 本目录/verify.py。manifest排除自身、verify.log，其余交付全封存；验证不发起规划器。系统DLL/未知动态依赖限制见environment_seal。外审时间是离线独立测量，与暖入口分开。原生deadline、迟到合法、无路线分别保留，严格截止和软返回视图不可互换。
''')
 write('review_packet.md','''# 审核包

执行完成，待负责人审核。请先查环境事前封存9381与原发现清单（任何规划器调用前已补齐审核/配置/输入），再查49门槛原P2包装/薄适配对照与确定性截止。生产冻结源码未改；P2只移外部审核出暖入口，offer和原生保底返回保留。

972任务全部按formal_order和actual_order可追踪，worker各自唯一输入读取/导入链/源码哈希；environment_seal覆盖相关Python/deps源二进制元数据和可识别非系统原生依赖，运行前后重核。Windows系统范围只列路径不冻结；不宣称全机复现。

分析以原始route和entry_seconds判断has_returned_route/route_valid/timely_valid/late_valid。逐预算两视图配对表明确162分母，54状态三种子原值/均值/范围；不能取最佳种子或把迟到路线算及时。P2最后source/长度与接受记录核对，LAST全分支独立奖励/BFS/采集/择优和P0配对；所有返回双指标。analysis.strata/metric_totals、完整CSV和固定正反图保留不利证据。外审计时单列，不并入速度。

verify.py只读重核环境/manifest/输入/顺序、门槛非时间对照、972双指标和LAST审核/P0/P2接受记录/双视图统计。审核后再讨论研究价值；执行方固定矩阵结束停止，不确认主算法或追结果调参。
''')
 print('REPORT/REVIEW/FIGURES COMPLETE')
def plot(choices,calls,protocol):
 sys.path.insert(0,str(Path(os.environ['TEMP'])/'codex-smallgap-plot-deps'))
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 out=H/'figures';out.mkdir(exist_ok=True)
 for label,q in choices.items():
  if not q:continue
  inp=next(i for i in protocol['inputs'] if i['id']==q['case_id']);c=read(inp['path']);fig,axes=plt.subplots(1,2,figsize=(12,6))
  for ax,m,color in zip(axes,['LAST_V2','P2_MULTI'],['tab:blue','tab:orange']):
   rec=next(x for x in calls if x['case_id']==q['case_id'] and x['budget']==q['budget'] and x['repetition']==q['repetition'] and x['method']==m);x=read(H/rec['output']);route=x['raw']['route']
   for p in c['free']:ax.add_patch(Rectangle((p[0]-.5,p[1]-.5),1,1,facecolor='#f3f3f3',edgecolor='none'))
   if c['targets']:xs,ys=zip(*c['targets']);ax.scatter(xs,ys,s=16,c='#a8d5a2',marker='s')
   if c['covered']:xs,ys=zip(*c['covered']);ax.scatter(xs,ys,s=8,c='#888888',marker='s')
   if route:xs,ys=zip(*route);ax.plot(xs,ys,color=color,lw=1,alpha=.8)
   ax.scatter(*c['current'],marker='*',s=90,c='red');ax.scatter(*c['base'],marker='D',s=35,c='black');ax.set_aspect('equal');ax.autoscale();ax.set_title(f'{m}: L={rec["metrics"]["length"] if rec["metrics"] else "none"}, entry={rec["entry_seconds"]:.4f}s\ntimely={rec["timely_valid"]}, native={rec["native_status"]}')
  fig.suptitle(f'{label} | {q["case_id"]} | budget={q["budget"]} | seed={20261020+q["repetition"]}\nNative-valid route diagnostic; late does not imply timely delivery');fig.tight_layout();fig.savefig(out/(label+'.png'),dpi=150);fig.savefig(out/(label+'.svg'));plt.close(fig)
if __name__=='__main__':main()
