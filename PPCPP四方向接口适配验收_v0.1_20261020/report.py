from common_orient import *
def table(h,rr):return '\n'.join(['|'+'|'.join(map(str,h))+'|','|'+'|'.join('---' for _ in h)+'|']+['|'+'|'.join(map(str,r))+'|' for r in rr])
def write(n,s):
 with (H/n).open('x',encoding='utf-8') as f:f.write(s)
def main():
 d=read(H/'analysis.json');p=read(H/'protocol.json');a=d['totals']['baseline'];b=d['totals']['selected'];pure=read(H/'pure_tests.json')
 lines=['# PPCPP四方向接口适配验收结果\n\n2026-10-20。**已封存，待负责人审核。** 本轮仅新接口与有限门槛，不是486次正式比较。\n',
 f'**新接口保留了旧域0°行为，且上下严格外侧已通过实际入口验收。** 54新旧0°完整native非时间输出/trace与旧封存54结果一致，左右专用夹具旧新一致。216新方向都完整合法及时、逐决策独立审核与原图双指标通过；3组合入口四候选与对应单候选逐字段一致，共12对。\n',
 f'**方向候选确实可能改变完整路线。** 本54已见状态最短方向相对0°为{d["short"]}短、{d["equal"]}平，{a["length"]}→{b["length"]}，少{a["length"]-b["length"]}步（{(a["length"]-b["length"])/a["length"]*100:.4f}%）。选择方向计数={d["selected_counts"]}。这是四次独立单候选的门槛潜力观察；不能将耗时相加称20秒组合实测成绩，未对54全部做组合入口。原方向包含在候选内，不更长是构造属性，不是独立优势证明。\n',
 '## 接口和语义\n','独立interface/ppcpp.py仅三处diff：版本号、严格外部合法域由x外扩到x或y严格外、对应错误文案。目录层级保留parents[2]，ROOT/sys.path等代码不改；有限长度/数值、空F、合同/奖励/previous/恢复/坐标平局/几何/返航/截止/原生method字段全保留。旧入口及共享冻结源码hash不变。没有调用旧predator_for，捕食者与地图/目标/H/previous/基地/旧后缀共同旋转平移。\n',
 '奖励math.hypot归一化、直行点积、邻域计数没有左右外侧假设，独立math.dist/acos审核同样不依赖x外。允许四侧外部不等于“predator not in F”；矩形边界和内部孔洞的实际入口ValueError拒绝。Nan/Inf由既有有限值检查拒绝，空F由原合同在构造/检查阶段拒绝，未执行min/max。旧左右域和新增上下域的12固定夹具原始输出全部保留；异常是明确失败记录，不吞成成功。\n',
 '0°直接原输入，不排序/平移；非0用整数旋转后全体共同平移到minF0。13字段及输出空间字段明列于接口依赖审查与变换表.md/transform.py，列表时序不重排；权重/奖励/index/pending_count/时间/种子不转。字典序tie、恢复同距目标和A*坐标堆tie不旋转等变，路线变化允许来自这些原实现坐标偏好；没有增加机制。奖励保持同一实现，但未做逐步因果消融去给每个收益分配唯一tie来源。\n',
 f'纯测试：{pure["transform_cases"]}状态×4={pure["transform_checks"]}变换检查，含原54、偏置非方形/previous=None、空集，四次未平移90复原、各方向逆变换、邻接/数量/包围矩形交换/顺序保持通过；严格合同纯谓词反例、原空F合同检查通过。{len(pure["deadline_stubs"])}组合阶段时钟桩覆盖每方向前/核心前后/之后及变换/逆映射/检查/编码，另两次native函数体假几何循环/连接截止桩，无真实求解。\n',
 '## 真实门槛与调用数\n',
 f'270单候选=54×(OLD0+NEW0/90/180/270)，12专用入口，3固定组合=285真实入口；真实core调用{d["core_calls"]}（270+11+12，空F夹具在核心前拒绝，故小于294上限）。其中B2七成功、五预期ValueError拒绝；预期拒绝不混作算法随机失败。全部B1/B3均完整合法及时，非预期技术/超时/非法/语义差异0。纯桩另记，不冒充真实求解或额外种子。没有P2/精确/混合/LAST/正式486调用。\n',
 '共享暖入口解码/变换/快照/全部求解/逆映射/必要内审/完整raw编码均计时；20秒绝对截止，每候选只拿余时，任一候选不完整/非法/异常或整体编码迟到均route空，不捞0。90秒硬看门狗仅技术上限。新wrapper编码候选原始raw、逆映射和变换输入，因此其输出结构与旧wrapper不同；等价结论仅指native.raw去除声明时间/版本字段，不冒充整个入口字节/耗时等价。\n',
 '## 54状态四方向\n',table(['状态','0°','90°','180°','270°','最短方向','省步'],[[s['id'],*[r['metrics']['length'] for r in s['directions']],s['selected_degree'],s['saved']] for s in d['states']]),'\n',
 '## 完整指标（每状态一次0°/最短方向；非正式同预算排名）\n',table(['指标','0°','最短方向','差'],[[k,a[k],b[k],b[k]-a[k]] for k in a]),'\n',
 f'采集完成前步数差{b["completion_step"]-a["completion_step"]}、返航尾段差{b["return_tail_steps"]-a["return_tail_steps"]}，两者之和等于总步数差；四类移动差也之和等于总差，但两个分解不能再相加。90°转向差{b["turns90"]-a["turns90"]}、180°差{b["turns180"]-a["turns180"]}，单列成本，不新增能耗权重。当前可检/本轮剩余覆盖100%，公开目标中暂缓不当完成，历史后遮挡H保留；全部细项/重复率/单方向原值在54四方向完整指标.csv。\n',
 table(['因素','层','状态','短/平','0°步数','最短步数','省步'],[[s['factor'],s['value'],s['N'],f'{s["short"]}/{s["equal"]}',s['baseline'],s['selected'],s['saved']] for s in d['strata']]),'\n',
 '## 时间：门槛观察，不是正式性能比较\n',table(['入口类','N','均值ms','中位ms','P95ms','最大ms'],[[m,s['N'],*[f'{s[k]*1000:.6f}' for k in ('mean','median','p95','max')]] for m,s in d['timing'].items()]),'\n',
 table(['组合状态','实测入口ms','选择方向','四候选步数'],[[c['id'],f'{c["entry_seconds"]*1000:.6f}',read(H/c['output'])['raw']['selected_degree'],[len(q['raw']['route'])-1 for q in read(H/c['output'])['raw']['candidates']]] for c in d['calls'] if c['stage']=='B3']),'\n',
 'B1旧0°54次、新方向216次是不同方向集合，不能直接用总体均值比作新接口速度；B3只有固定3状态，不外推54/更大图。即使观察收益，仍需另行批准共同预算正式实验；没有新P2调用，不拼旧P2时间/路线作新排名。\n',
 '## 来源与证据边界\n','实际旧worker source_hashes在此前阶段A核实，本轮继承并逐hash核旧冻结、原54输入与旧结果；原输入按字节复制。任何规划器调用前封存程序/协议/输入/夹具/审核器及相关Python/deps二进制/配置环境；前后全清单核验，每worker记录实际导入hash和唯一输入读取。环境系统Windows DLL只记路径，未知动态加载范围限制保留，不将路径记录称字节冻结或全机认证。\n',
 '独立逐决策审核在旋转坐标系重算捕食者距离/归一化/直行/边界奖励、邻居同分择优、恢复图距离/目标；另用独立A*重建固定端点连接，原图逆映射路线双指标审核。没有要求各方向原路线相同；逆映射trace仍保留旋转坐标偏好下的options顺序。版本和明确时间字段之外不删决策字段。\n',
 '本54已见开发数据共享9基础道路/单一历史，不是独立留出、泛化、统计普遍性或最优性证据。四候选可以视作固定多表示启发式，不自动成为论文创新。到此封存本接口与门槛；有收益也只供负责人决定下一轮，不自动执行原稿486批、P2排名、更多方向/镜像/新规则或恢复混合。\n\n已封存，待负责人审核。\n',
 '只读：`./运行环境/python/python.exe -B -X utf8 PPCPP四方向接口适配验收_v0.1_20261020/verify.py`。不调用规划器或追加门槛。\n']
 write('四方向接口适配验收结果.md','\n'.join(lines));save(H/'call_ledger.json',dict(real_entries=285,real_core_calls=d['core_calls'],B1_entries=270,B2_entries=12,B3_entries=3,B3_internal_core_calls=12,pure_combo_clock_stubs=len(pure['deadline_stubs']),pure_native_body_fake_geometry_stubs=2,non_expected_failures=0,expected_rejections=5,formal_comparison_entries=0,P2_calls=0,exact_calls=0))
 write('README.md','# 四方向接口适配与有限门槛\n\n已封存，待负责人审核。结果见四方向接口适配验收结果.md。接口依赖审查/13字段表、interface.diff、旧新源与事前环境、54原输入/固定夹具/order、pure_tests、285 jobs/execution/logs/actual_order、analysis/字段等价/双指标/全CSV、call_ledger、review_packet与manifest/verify均交付。旧冻结/历史不改。本轮没有正式486、P2或精确搜索。\n\nverify.py只读重核，不再执行求解或桩；manifest仅排除自身与verify.log。\n')
 write('review_packet.md','# 审核包\n\n已封存，待负责人审核。请先检查interface.diff仅版本/严格矩形外合法域/文案三处；原文件hash不变，副本目录深度相同不需改ROOT。核心奖励/previous/恢复/几何/审核无仅左右依赖。predator实际坐标随场景旋转，绝不重置或调用旧生成器。\n\n源输入/程序/审核/环境在调用前封存；285真实门槛/实际core数call_ledger，原生raw新旧54对和旧封存54对只忽略声明时间/version，方法/trace/options/goal等全保留。216方向逐决策在旋转框架重算并独立重建A*连接，再原图逆映射双指标。12专用夹具七成功五预期拒绝，上下已实际通过，矩形孔洞/边界/非有限/空F拒绝不是成功。纯变换与截止桩另账。3组合各四候选与B1相符，严格同长先者，整体失败不捞原候选。\n\n全部原门槛结果/输入/元数据/源hash/读路径可审，时间是新完整wrapper门槛成本，不冒充核心字节等价或新旧/P2正式速度排名。54方向最小值不是54次组合入口实测，3组合不能外推。未进行486正式批或新P2。\n\nverify只读重审env/输入/diff/变换/字段等价/逐决策/指标/选择/调用账，无求解。是否批准下一轮需负责人判断；有无收益都在本轮固定上限停止。\n')
 print('REPORT/LEDGER COMPLETE; no formal comparison')
if __name__=='__main__':main()
