# LAST实现与开发验收审核包

**执行完成，待负责人审核。** 此实现为独立候选PPCPP_LAST_RESERVE_v0.1，不替换原PPCPP或现有冻结基线；开发可行性通过不等于主算法/创新批准。

|待审核结论/风险|原始证据|只读复核|
|---|---|---|
|输入60已见状态、两批分开、无新增地图|protocol.json、inputs/*及源文件hash|protect核原件与复制一致；原样本/进度不当独立图|
|新增代码仅固定一种e规则|candidate.py、runtime.py|e只依s的U与原图基地距离；P0失败不试P1、U空跳过、同值保P0|
|策略禁入非物理障碍|P1工作trace、真实输入、phase1_end|audit.py核e不早进、原F/T/H/暂缓不变、阶段二完整释放|
|阶段一不错误要求基地可达|base_removed_but_work_ok门槛|e=base，工作任务可完成后才释放返回；无需work.precheck|
|P0与原版完全等价、状态私有|60输入×3门槛、180正式配对、P0 pristine快照|原审核及完整route/trace；P0前后无变；3独立cache图Spy|
|P1局部奖励/恢复仍按原公式，但图不同|每份P1.trace/diagnostic_route|独立标量奖励、工作图BFS最近目标/距离、逐格收集、阶段二原图最短距离|
|共享截止，P0完成后晚到也拒收|gates中9个deadline注入，含编码后|verify检查P0 core_complete且整route空/eligible false；原失败不以P1补救|
|生产不看最优结果|worker/runtime/candidate；360 runtime_reads/imported_modules|唯一允许读取原始输入；生产无精确/分析导入；参考仅完成后analyze|
|360正式全合法及时，3重复稳定|jobs、execution、completion、formal_call_ledger|verify逐输出与输入hash、P0/P1/final动作、120方法状态组稳定|
|主8短28平/430→414，补2短22平/266→262|analysis与两批CSV/完整P0/P1路线|两批各自完整分母、未删原已最优；总量与逐状态比例分开|
|主8差距例均省2，但4例仍有潜力|同输入既有A/C及P1、reference_seal|主全部成功P1>=Lnear；未达例e可达L*，是当前走法未实现潜力|
|旧两正例达到最优|旧global同last见证、当前P1|L*下界+同e的最短合法见证给Lnear=L*，不伪称补做C查询|
|5已知近基地坏例正确保原仍有开销|main36窄I直扩25/60、窄L直扩60、窄Z直扩60/障碍60|每例P1长2；计入全部LAST耗时，不删未选分支|
|保存禁入额外通路代价及失败|analysis.states.audit.work_segments、所有P1状态|F_work实际连接减原F同端点BFS；不能当P1-P0因果差或再次相加|
|计算约增加一倍，转弯有取舍|调用时间分段CSV、analysis、完整指标表|完整总入口为主，P0/candidate/P1/audit/encoding分段仅解释；不推真能耗|
|固定选图缺类不补|analysis.selected、figures/*|改善最多与未完全追回同图；P1更长另一图；正式不可达0不拿夹具补图|

统一命令（不再求解）：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP保留末采集格候选_v0.1_20261020/verify_v02.py
```

版本与缺口：首次gates.py被原冻结audit.py遮蔽，导入即失败、0算法调用，失败保留；gates_v02只修加载路径，全部门槛完成后源码封存，正式不混版本。补24原协议没有全部最近last查询，8成功替代没有对应精确界，此项明确未判，不追加查询。所有分支仍合法/决策独立核验。无正式失败/超时或参考hash失配。

需负责人重点判断：主改善在L/Z四个既有几何组，但均为宽规格规则小图，使用PPCPP单一历史；补改善只是一个旧几何，非独立验证。最终不变长是P0完整保留的构造，不能当创新；真正证据为严格省步及其约2.1倍入口计算/90度转弯增加等取舍。主4未达最优例不授权继续加终点或调用精确补全。生产读审计是求解期Python文件读取allowlist，导入模块在计时前记录来源，不声称操作系统级沙盒。

交付审核首次verify.py因重算坐标tuple与保存JSON list表示不同而整表比较失败；保留失败脚本和delivery_verify_v01_failure.json，verify_v02.py仅规范化JSON表示。正式数据/运行源码不变，0重跑，详见交付审核器v0.2影响说明.md。不要把所有验收说成一遍通过。

没有使用最终留出、没有新大图/强P2排名、没有改旧冻结/历史封存或推送提交。固定360结束即停，建议先审核是否值得独立新开发验证；本稿不自动批准下一轮。
