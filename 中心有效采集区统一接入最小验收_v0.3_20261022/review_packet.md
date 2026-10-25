# v0.3 最终接续 review packet

先读00_通俗最终接续报告.md、三栏与跨版本查询总账.json及final_receipt.json。跨版本六会话完成返航，但真实不经格心斜段信用0例未验，不能泛称所有覆盖目标均通过。

计数契约.json、schema修复.diff和changes.json列明修改范围。schema.py对新观测要求完整零schema/严格类型/守恒/原1200保护/已启用且正常完成；旧兼容层逐字段证据补齐，不任意缺失默认0。precheck_registration.json/precheck.json为八项首轮预检，旧测试仅核来源/适用范围不重跑。real_freeze.json证明真实开始后实现不变。

reuse_receipt.json、reuse_audit_actual_counts.json、outputs/W2_P2_plan_2.json保留兼容新增字段、原native_counts、来源sha及完整独立复核。原v0.2返回和会话仍failed。resume_seed/resume_plan_rows恢复旧日志链，首份计划引用绝对旧路径，第二份保存复用；没有重跑或复飞旧段。

W1两完成会话仍在v0.2目录；本版sessions含W2_P2续飞及后三新会话，旧来源通过verification_runs检查表source绝对指针完整引用。calls/outputs有6次新核心及直达原返回，原timing逐入口保留不混作同轮性能。失败来源与新实际执行三栏在报告和总账分开。每份新计划finally计数真实落盘，旧异常缺口不覆盖。

只读保存核验：

    .\运行环境\python\python.exe -B -X utf8 '中心有效采集区统一接入最小验收_v0.3_20261022/run_center.py' verify

每次新增verification_runs收据及保存几何/区域查询，禁止核心/选择器/后处理/图搜索。manifest绑定封存文件；root_before/root_after是历史快照，不要求实时根文档永远不变。export_final_v03只读保存证据做文图和结构封存，不修运行时或重新求解。完成后停止，无自动追加批。
