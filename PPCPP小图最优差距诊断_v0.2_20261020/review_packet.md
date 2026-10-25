# 审核包：待研究负责人审核

执行者自检通过不等于研究结论获批。请审核模型充分性、精确证明/独立实现、历史来源、归因公式与边界，再决定后续方向。

|结论/要求|原始证据|只读复核入口|
|---|---|---|
|先固定几何、4基础图、24槽位及上限|预登记.md、protocol.json，v0.1/protocol.json|verify_delivery.py；protocol保护源码及几何上界|
|真实PPCPP历史，不输入未来事件|prep/*的input/result/完整route/trace；witnesses/*的history/cut|prepare.audit_inputs由verify.py调用，独立坐标重建与逐决策审核|
|4准备/24输入是相同算法版本字节复用|reuse.json、版本影响说明.md、v0.1/prepare.log|verify_delivery.py逐文件哈希，正式未混v0.1|
|原版route/trace包装等价|gates.json与指向的旧execution原结果|verify.py；另有中止门槛1次单列|
|24全局最优，原PPCPP22最优/2多2|execution/*、exact/*/global.json、request与certificate.json.gz|independent.certificate_audit；analysis逐状态核对|
|271精确门槛/截止注入|tests/results.json，13固定夹具压缩证书|独立frozenset Dijkstra对照结果封存；tests.py可在空副本重放|
|8首次恢复检查点损失0，1第二恢复损失0|原trace索引、exact/*/mapping.json和对应查询|verify.py重算采集集合、C/D/R非负及单调|
|两个有差距状态无恢复|s2_L_corner_p25、p60完整trace|run.checkpoints与独立原trace审核；不存在不当作0|
|23固定结束查询，2例结束限制各2|exact/*/fixed_last.json及约束后继闭包证书|last采集时序/合法转移、L*<=Le<=Lp；空任务单列|
|完整指标/暂缓5格次不计完成|analysis.json的ppcpp/optimal/fixed_last metrics|两套独立metrics/crosscheck全字段一致|
|固定规则选正反图，缺正前缀图不补|analysis.selected、figures/*.png/svg、plot.py|verify_delivery.py重算选择；图已目视检查|
|没有改旧冻结/留出/历史封存|protocol上游源码哈希保护、v0.1保留|verify.py；本轮没有提交/推送GitHub|

统一命令：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP小图最优差距诊断_v0.2_20261020/verify_delivery.py
```

精确最优性不是“路线合法”或“两个求解器长度相同”的替代说法。独立审核保存BFS所有发现状态、父边深度、出队前集合的后继闭包；由可达性与无遗漏低层共同支撑不存在更短路线。精确独立夹具采用逐格frozenset剩余任务Dijkstra，不调用主邻接/掩码函数。朝向仅影响PPCPP，不影响精确可行动作或代价；统一宽松距离预算不活跃，不能外推紧资源。

已知疑点/边界：两个正例来自同一基础几何的两进度；16状态无恢复、仅1有第二恢复；形状/尺度/事件共变，不能单因素因果归因。固定last结果只说明该限制代价，不证明所有最短路径终点唯一，不是返航单段可独立追回。任一最短见证的转弯非最优转弯。没有确认创新。唯一线索为结束位置与总返航代价联合考虑，当前证据不足，不推荐立即实现；本轮停在交付点。
