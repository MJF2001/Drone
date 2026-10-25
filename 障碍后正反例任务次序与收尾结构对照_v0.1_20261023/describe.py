"""Exploratory description of saved sequences, never a rule or new H2 test."""
from common import *
def run_cost(rows,start_index):
 # Rows are new-service events, not physical boundary crossings.
 rr=[r for r in rows if r['marker']['native_vertex']>start_index];groups=[]
 for r in rr:
  if not groups or groups[-1]['block']!=r['block']:groups.append(dict(block=r['block'],rows=[r]))
  else:groups[-1]['rows'].append(r)
 spans=[];gaps=[]
 for g in groups:
  a,z=g['rows'][0],g['rows'][-1];i,j=a['marker']['native_vertex'],z['marker']['native_vertex'];spans.append(dict(block=g['block'],first_task=a['task'],last_task=z['task'],first_vertex=i,last_vertex=j,service_count=len(g['rows']),span_edges=j-i,first_tasks=[r['task'] for r in g['rows'][:8]]))
 for a,z in zip(spans,spans[1:]):gaps.append(dict(from_block=a['block'],to_block=z['block'],from_task=a['last_task'],to_task=z['first_task'],start_vertex=a['last_vertex'],end_vertex=z['first_vertex'],edges=z['first_vertex']-a['last_vertex']))
 lead=spans[0]['first_vertex']-start_index if spans else 0;total=lead+sum(z['span_edges'] for z in spans)+sum(z['edges'] for z in gaps)
 assert not spans or total==spans[-1]['last_vertex']-start_index
 return dict(start_vertex=start_index,to_first_new_service_edges=lead,service_run_spans=spans,between_service_runs=gaps,span_sum=sum(z['span_edges'] for z in spans),gap_sum=sum(z['edges'] for z in gaps),total_to_last_service=total,scope='disjoint native-edge partition by credit-run indices; spans need not stay inside a rectangle; gaps are not shortest-distance or waste')
def main():
 start=time.perf_counter();index=read(H/'pair_index.json');details={};lines=[]
 for row in index:
  p=read(H/row['file']);costs={};shared=p['after_route_known']['shared_p_C']
  for arm,a in p['after_route_known']['arms'].items():
   source=read(p['source'][arm]);tr=source['diagnostic']['trigger'];k=shared['common_index'] if shared else tr['route_index'];rows=a['native_full']['task_sequence'];costs[arm]=run_cost(rows,k)
  details[p['key']]=dict(partition_start='common physical p' if shared else 'same-path trigger, no divergent p',arms=costs)
 dump(H/'descriptive_run_costs.json',details)
 schema=['# 决策前可用信息与事后信息','', '以下均为本轮从已保存资料提取；没有在线观测、没有反馈选择、没有训练或阈值筛选。','', '|决策时可提取（不读取未来尾部）|路线完成后才能知道|','|---|---|','|current、previous、完整pending/hash、各原始矩形块pending计数|真实首次服务任务序及块序、块交错与完成顺序|','|q0/q1坐标、所属块、是否同块；已保存d0/d1|原生/直达首次物理分歧、后续进入/完成各块的位置|','|原旧锚点rank、默认是否已优先旧序|末采格、最后完成块、返航与整条路线长度|','|当前所在原始块/非目标通行区、公开障碍F、基地、给定资源、捕食者|共同p/C、Δraw/Δpost/ΔG、实际转弯代价|','|事件物理H/U按原矩形计数；不拆碎片|post边界映射及是否比原生提前获得信用，不能反馈到当时pending|','', '事后已知：I中一格左侧任务被留到最后、T中块序不变但块内序及连接端点变化。决策前仍未知：原局部规则实际将怎样采完该块、从何处离开、最后落在哪里，以及公共直达会如何改变总费用。','', '**轨迹解释更清楚，但仍无可用判断规则。** q0/q1是否同块、剩余块数、旧序优先等标签只作描述，未搜索任何能分开正负例的组合。不能把此批事后描述当独立验证或上一轮H2通过。']
 (H/'02_决策前与事后信息分栏.md').write_text('\n'.join(schema)+'\n',encoding='utf-8')
 table=['# 全部十九对索引（不拼总体胜率）','', '基础扩样12对与受控变体7对分别列出；另有5个无资格槽只见gaps.json，不补轨迹。B编号取原地图矩形登记次序，在各自基础几何内使用，不能跨图把B02当同一物理块。','']
 for dataset,title in [('base','基础扩样：12对'),('variants','受控变体：7对')]:
  table+=['## '+title,'','|配对|q0/q1块(触发剩余数)|原生压缩块序 OFF→ALT|末采 OFF→ALT|ΔC / Δ原生返航|Δpost 米|','|---|---|---|---|---|---:|']
  for r in index:
   if r['dataset']!=dataset:continue
   table.append(f"|[{r['id']}]({r['file']})|{r['q0_block']}({r['q0_block_pending']}) / {r['q1_block']}({r['q1_block_pending']})|{'→'.join(r['native_OFF_runs'])} / {'→'.join(r['native_ALT1_runs'])}|{r['native_OFF_last']['cell']} / {r['native_ALT1_last']['cell']}|{r['delta_C'] if r['delta_C'] is not None else '同路无分歧p'} / {r['delta_return']:+d}|{r['delta_post']:+.9f}|")
 dup=read(H/'duplicate_levels.json');table+=['','## 分层重复关系','', '完整E及旧序签名没有重复，19对均保留。局部触发重复组与完整输入差异不能混为一谈。']
 for level,groups in dup['groups'].items():
  table+=['',level+':']
  for g in groups:table.append('- '+'；'.join(g['members']))
  if not groups:table.append('- 无重复组。')
 table+=['', 'I原例与B50/B70两臂原生尾部重复，不是新增独立决策模式。I两个A虽局部触发相同，F不同且OFF尾部不同；T两个A的F与ALT尾部不同。F/物理H/旧序/基地/资源/捕食者逐项比较见duplicate_levels.relations。']
 (H/'01_19对完整索引与重复关系.md').write_text('\n'.join(table)+'\n',encoding='utf-8')
 main=['# 任务次序与收尾结构：正反例的保存轨迹对照','', '已整理基础扩样12对与受控变体7对，共19个保存配对、38条处理路线、76个原生/直达视图；本轮所有规划、post、历史准备、BFS、最短路、可视查询和反事实路线新增均0。算术、标签和文件处理费用另记。19对不是19个独立几何，也不拼总体胜率。','', '## I正例：交换两片剩余任务的先后，把一格左侧任务留作收尾','', 'I_gap_B__p60触发在[24,9]附近（完整current/来向见配对），剩余33格：B02左侧只剩[13,7]这一格，B04右侧还有32格。默认先去B02，再扫B04；备选先扫B04，最后回B02。原生和公共直达的块服务/完成顺序都由B02→B04变成B04→B02。','', '默认末采[37,7]在右侧B04，备选末采[13,7]在左侧B02；原生返航44→20，少24步。从同一物理分歧p到完成覆盖再少4步，净少28步；公共直达净少28.763940280米。公共末信用见证之后的费用约37.756341→14.864823米，见证口径不是唯一物理首次入区时刻。','', '两臂不是在同一恢复路径上先后采两个候选：OFF恢复只采到q0，ALT恢复只采到q1，另一片留给后续。A1/A2仍采用相反块完成次序和相同收尾格，原生费用差相同、直达幅度略变；B50/B70汇合到同一触发和两臂尾部，不能当三条独立模式。','', '## T反例：块序没有变，块内采集和连接端点变了','', 'T_gap_B__p25的q0=[24,31]、q1=[25,31]同在B04（触发时剩16格），之后还有右近B07、右远B08、左近B05、左远B06。两臂都按B04→B07→B08→B05→B06采集并完成，不能把退化解释为调换了左右块顺序。','', 'OFF恢复在q0结束，随后先沿[24,32]向上；ALT恢复途中先采q0，再到q1，随后沿该方向继续。同一块的首8个新采格、块内首末位置及原生索引已保存：例如B04末采从[27,31]变为[26,32]，B07入口从[32,31]变为[32,32]。这些改变沿后续连接和块内次序传播，最后仍在B06收尾，但末采从[6,32]变为[3,31]。','', '原生返航38→34虽少4步，共同p之后的覆盖却多10步，净多6步；直达净多8.587181813米。按固定新信用块段的索引分账，首个新采格前都是9步，段内采集跨度总长117→122、段间行程46→51，合计共同覆盖172→182。跨度内行程不保证始终位于块内部；这些只是无重叠保存边数分账，不是最短路或可删除浪费，也不是独立机制贡献。','', '两个T障碍变体保持相同块序和相同费用差，但ALT恢复路径改变。T较早公开变体的q0/q1已换成B02中的[24,15]/[24,16]，全程物理同路；不能把这个零效应称同一对目标优劣反转。','', '## 全批反证：这些描述还不足以预判收益','', '- I_gap_A__p60两臂都只剩B03一块，块序完全一样，却因末采[38,6]→[30,8]，原生覆盖C不变、返航少6步，直达少6.793888511米。因此“块序没变”不等于没有收益。','- I_gap_A__p25也保持B02→B03，仍少14.372543110米；块级标签掩盖了块内顺序和末端位置差异。','- L_gap_B的两个等长不同路例保持相同块完成序、相同末采与返航费用，却有不同任务/路径展开；“目标不同/路径不同”不等于总长必变。','- L_gap_A__p25默认采集块序B02→B03→B04→B05→B02，备选先完成B02再走后续；不再回收B02遗留任务，但共同覆盖少32步被返航多34步抵消，原生反而多2步，只有公共直达后净少0.979486872米。不能说减少块交错就必然缩短完整路线。','- 同块候选在本批同时有改善、等长和退化。跨块候选只集中在I_gap_B这一已见模式及其相关变体，不能据此立“先去另一块”规则。','', 'A→B→A只表示新信用的交错，未声称一定两次穿越物理边界或存在可删除空飞。post块序、全任务ID、首末信用见证、源原生索引及边界绑定与原生分别保存。本批38条post都能在原生触发的精确源顶点切分，未发现触发pending在post边界之前已被采的任务；这不是所有地图的保证。','', '## 已知解释与未知判断依据','', '|事后已经解释|决策前仍不知道|','|---|---|','|I把一格左侧任务留到最后，末采与返航更省|仅由当前33任务和旧计划，如何可靠预判两块内部的完成位置与总费用|','|T块序相同，但进入/退出位置和块内次序变化，覆盖多10抵消返航少4|仅凭同块q0/q1与当前来向，何时会传播出额外连接/块内行程|','|同块/相同块序也能改善或退化，减少交错也可能使原生更长|哪些稳定的决策前依据能区分这些情形；当前没有被验证的阈值或评分|','', '**轨迹解释更清楚，但仍无可用判断规则。** 本轮没有训练、阈值筛选、有限前瞻或新机制；任务块序列是新登记的探索性描述，旧H2仍不适用/未确认，不回填为H2通过，也不输出新机制通过率。','', '## 范围、索引与停止','', '固定块来自原地图矩形组成，pending分裂也不另拆。它不是飞行域连通分量或必须一次扫完的单位；F仍是宽矩形，不能推广成连续施工道路天然分块。变体5个无资格槽仅保存缺口，不生成轨迹或零收益。','', '[19对完整索引与重复关系](01_19对完整索引与重复关系.md)、[决策前/事后信息](02_决策前与事后信息分栏.md)、[审核入口](review_packet.md)。全部原始任务序、信用与块完成时点见pairs/；图和只读verify另存。完成后停止交负责人讨论，不自动设计或实现规则。']
 (H/'00_通俗结构对照报告.md').write_text('\n'.join(main)+'\n',encoding='utf-8')
 review=['# 审核入口','', '1. 00报告先看I两块交换与收尾、T同块序但块内/连接变化，再看其他原批反证。','2. pair_index/pairs：基础扩样12、变体7，38处理/76保存视图；gaps保留5无资格槽。source_guards先核完整来源及旧回执，旧包只读。','3. decision_available是保存触发前缀/输入提取；after_route_known包含实际服务序、块序、完成/末采、共同费用。严禁把后者当决策前特征。','4. block_systems沿原矩形顺序编号；不运行连通分量，P格归属唯一。native_full/from_trigger与post_full/from_mapped_trigger分开，保留任务ID/事件索引/见证。','5. post_boundary依原生源索引与post顶点映射。本批38条精确对应，无跨前提前信用；一般不唯一时应保整序并标未知。','6. duplicate_levels保留全19、完整E不合并：I B进度两变体与原例尾部相同，A的F不同，局部相同不等于完整状态相同。','7. descriptive_run_costs只是保存边数的互不重叠分账，不是新H2或最短费用。verify独立读取原始点串及engine信用而非复读派生表，核块计数、顺序、完成时点、证书及共同费用。','8. 所有新增规划/post/历史/BFS/可视/反事实均0，算术/读取/报告/图计时有账；旧H2未确认，未造评分或规则。根进度仅前缀追加，旧final及旧正文不改。']
 (H/'review_packet.md').write_text('\n'.join(review)+'\n',encoding='utf-8')
 dump(H/'description_receipt.json',dict(passed=True,pairs=len(index),wall_seconds=time.perf_counter()-start,counts=dict(COUNTS),new_core=0,new_post=0,new_BFS=0,new_visibility=0,new_counterfactual=0,new_rule=0))
 print(json.dumps(dict(described=len(index),seconds=time.perf_counter()-start),ensure_ascii=False))
if __name__=='__main__':main()
