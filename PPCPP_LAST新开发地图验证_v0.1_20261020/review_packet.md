# LAST新开发地图验证审核包

**执行完成，待负责人审核。** 固定原实现、不运行精确最优，不自动确立主算法或追加改进。

|主结论/要求|原始证据|只读复核接口|
|---|---|---|
|运行与审核核心字节复用，规则未改|protocol.reused、candidate/runtime/worker/audit/common、上轮source_seal|verify_v02逐文件对照原件及依赖哈希|
|几何/共同公开域/障碍在调用前固定|预登记、protocol、spec、几何坐标表/ASCII概览|setup纯几何预检；preflight及input_audit独立坐标谓词|
|Z不再紧凑阶梯，转弯间至少2w|定义L-w=4/9/20、图与坐标|preflight；中心直段不把w角块计长度|
|9真实事件前准备、30%/70%前缀|prep输入/route/trace/日志；54witnesses的cut/history|audit_all逐格首次门槛/H/current/previous/旧后缀|
|扩展有新增、障碍首备/历史/暂缓前置审核|preflight、input_audit、witnesses.blocked/obstacle_choice|独立坐标/可达/双指标；首侧冲突实际1例，不临时第三位置|
|见证仅审核，不给算法|witnesses与worker运行路径|每份runtime_reads仅input，无未来见证或旧结果读取|
|旧143源件核对无原始/平移/D4复制|old_input_catalog、novelty、上游sealed protocols|verify重算全部签名；shape分组另用交换轴/正负号实现成对核验|
|108新输入PPCPP/ONE完整等价|gates、gate_index、input/source_seal|逐route/trace和原逐决策；核心相同引用旧218门槛，不再运行精确|
|540全部完整合法及时且5重复稳定|completion、jobs/execution原结果/日志|compute每份双指标/工作图/原图BFS/奖励/采集/择优；270P0配对|
|54配对27短27平，5530→5476少54|analysis.states/calls、状态CSV|每状态一次，保持全槽位成功率，不选最快或最短重复|
|18非旧复制改善组跨I/L/Z|analysis.family_support/strata/copy_exclusions、novelty|排除旧完整/形状复制后复算；不当18独立随机试验|
|坏P1两例+10/+2均保P0，仍计时间|large_I_straight_p30、medium_I_straight_p70完整分支|选P0规则审核与各自5次时间，不隐藏未选计算|
|P1策略性不可达/空U/迟到本轮0|全部分支状态、call_stats|缺类不补；旧门槛覆盖这些边界，不声称任意地图都可行及时|
|总省不足1%，时间均值约14倍|analysis.timing/phase_timing、540时间CSV|候选距离占约85.46%；只是成本定位，不执行提速|
|指标有取舍，暂缓不算完成|metric_totals与两套重算|90度+44/180度−3，覆盖前+343/尾段−397，净−54；公开暂缓21|
|固定图选与单例占比|analysis.selected、figures/四PNG/SVG|绝对/相对/无改善/坏分支，缺失败类不补；最大例占3.7037%|

统一命令：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP_LAST新开发地图验证_v0.1_20261020/verify_v02.py
```

独立审核适配：audit.py原文件不变，audit_adapter在计时外按输入/图/源点缓存同值BFS距离；每次检查图集合相同，防不同工作图缓存串用。60小图查询重复核未缓存值一致，正式前已通过。此适配不影响原生产截止/缓存，旧边界和截止证据仍针对相同生产/审核核心；本轮没有执行精确搜索。

无矩阵/算法/预算协议变更，无无效/准备失败/门槛失败/正式故障或未解决项；旧复制全部0。唯一交付审核故障为调用级tuple与JSON list表示差异，verify.py及verify_initial.log保留，另版verify_v02规范化比较，正式结果失效/重跑0；详见影响说明，不称所有流程一次通过。

需负责人审查的边界：9个规则I/L/Z合成道路、固定基地/捕食者和单一PPCPP历史，30/70进度及5重复共享图。27形状组/18正组不是统计独立地图；新构造在运行后均为已见开发。每改善状态都只省2步，medium贡献59.26%；非单例主导但净总路程仅少0.9765%。LAST均值90.34ms对6.46ms约14倍，最大0.6395秒，不能以20秒内完成称计算可忽略，也不能外推大图/硬实时或真实能耗。

可接受的有限表述为“本固定新开发矩阵观察到跨形状收益保留”；计算与转弯代价使主算法价值尚未充分成立。结果不授权在本批图提速/改候选/补终点或自动开展强P2排名。本轮停在审核交付，旧数据/最终留出/冻结不改，不提交推送GitHub。
