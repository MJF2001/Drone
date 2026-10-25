# 负责人审核包

**执行完成，待负责人审核。** 此包为36槽位固定开发机制验证，不是算法实现、排名或最终留出证据。预登记最低判据已满足，不能将执行者自检转成研究批准。

|需审判断|原始证据|复核位置|
|---|---|---|
|几何在准备/正式前固定、六族规格无分叉、扩展有新增|预登记.md、protocol.json、几何坐标表.json、几何概览.md|setup.py纯几何上界/矩形不重叠；prepare.reconstruct独立坐标重建|
|6真实准备、不获未来事件，36前缀与覆盖返航见证|prep/*、inputs/*、witnesses/*、input_audit/input_seal|prepare.audit_inputs重放历史/current/previous/H及账本，见证仅用于核验|
|最近结束候选仅来自输入图距离|candidates/*在正式前封存，input_seal|prepare.audit_inputs独立坐标层递推重算distances/tie/current排除|
|原PPCPP未变、20秒完整入口|common.py与旧版字节一致，gates.json、execution/*|verify_delivery校验哈希、两个golden完整route/trace；原独立逐决策审计|
|36中28原最优，8有差距，430对402|execution/*、exact/*/A.json和压缩证书、analysis|verify.py每请求输入/起点/基地/任务核对；独立证书及Dijkstra复算|
|L与Z跨形状重复，四组而非八独立图|analysis.geometry_groups/family_support_groups及全部完整签名|equivalence.py区分shape/state，verify_delivery重算支持和判据|
|旧完全/平移/D4任务状态均无复制，2旧形状槽位无正例|analysis.states的old_*字段|verify.equivalences与上轮24输入只读核对|
|E26/R2，G=E+R；一例E>0/R>0|exact/*/B.json、mapping.json及原逐格采集|verify.py核last约束、L*<=L0<=Lp；不可混淆任意改善必要条件|
|近基地候选8短22平5长，5例确实严格更近|candidates/*，exact/*/B/C，analysis d字段|verify_delivery逐状态d近<d0且Lnear>L0；无曼哈顿替代|
|C约束可无解，但本批0；门槛证明必经点无解|tests/new_gates.json、mandatory_last.gz|independent.certificate_audit+独立oracle；不可当整体输入无解|
|93独立查询复算全完成且一致|rechecks/*、recheck_summary.json、recheck.log|verify_delivery校验逐查询hash/length/墙钟<60；只读核验不再调用求解|
|完整指标/暂缓9格次与历史挡后保留|analysis逐状态四套metrics及汇总|两套metrics/crosscheck逐字段对照；N36和N35明确|
|固定图选择/缺类不补|analysis.selected、figures/*.png/svg、plot.py|verify_delivery重算选择并核图；3张图均已目视检查|
|协议小偏差与顺序披露|结果报告“协议偏差”及supplemental_geometry_audit|额外障碍fallback验收为正式后纯几何补审，0求解；未伪称前置门槛|

统一只读命令（项目根目录）：

```powershell
& ./运行环境/python/python.exe -B -X utf8 PPCPP结束位置跨几何验证_v0.1_20261020/verify_delivery_v02.py
```

需人工特别审查：宽规格Z是两次转弯的阶梯状连续带，尺寸受48格域约束，短段/转弯厚度会形成紧凑阶梯，是否足够代表论文中的折线道路需要负责人判断；不是现场参数。正例集中宽规格、单一PPCPP历史来源和规则图，未测朝向旋转。20个形状组仍共享6基础道路，不是20独立统计样本。一个E>0/R2案例禁止“所有改进均必须变结束点”的泛化。C只提供指定终点下最理想完整成本，不是实用近基地策略。

所有正式查询optimal，无unresolved/失败；C不可行0，只在门槛出现可行性反例。无恢复正E本轮未观察到，与旧轮两个正例不能混计。交付审核首次CSV/Markdown空值表示比较失败另存verify_delivery.py及delivery_audit_v01_failed.json；有效审核器verify_delivery_v02.py只修这一比较，正式数据未改、无重跑，详见交付审核器v0.2影响说明.md。

无新算法、无留出使用、无参数扫描/追加图、无排名、无提交推送。固定矩阵结束即停。唯一后续假设是比较覆盖方向/结束位置的完整含返航成本，不是只给靠基地奖励；由负责人审核再决定是否实现。
