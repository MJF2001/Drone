# 负责人审核入口

先读00_通俗报告.md、01_接口与数值合同.md、18类结果与历史分母.md。最终核验实际状态看final_receipt.json及verify_receipts/verify_001.json。

- 门槛事前登记.json / 18类事前预期.md：40槽原始预期、各类至多3子例，预期未改。
- round_1_freeze.json / round_2_freeze.json及repair_rounds：首轮37失败原样保留，第二轮只接续37槽，3槽旧通过hash复用；来源见40槽最终证据来源.json。
- round_2_技术修复.diff / 修复影响与未改项.json：两处表示修复与接续包装，主数值/政策未改。
- 实际预测双账汇总.json：保存实际/预测与手工提交，不是执行器世界模拟。
- 跨轮函数与几何实际账.json / repair_prechecks_result.json：77会话69响应、失败尝试与额外保存审核分别计费；不得说几何查询0。
- source_snapshot / source_bindings.json / 旧H1两版只读哈希.json / 几何复用适配.diff / 独立新增实现.diff：来源、原包保护及实现差异。
- verify.py仅用独立slab/比值/有理二分算法审核保存候选证书、路线和动作，不调用主选择器/stub/提交器。每次运行另写verify_receipts并单列新增几何；现场根进度不要求永远等于历史快照。

复核命令（在项目根）：

```powershell
.\运行环境\python\python.exe -B -X utf8 '真实停止点首连接纯桩验收_v0.1_20261022/verify.py'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

封存后停止。仍需负责人决定是否、如何接入真实H1/P2；本轮不提供性能或创新结论，不读取未来事件或留出。
