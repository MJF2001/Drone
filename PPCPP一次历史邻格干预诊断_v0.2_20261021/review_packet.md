# 完成实验审核入口

先读通俗报告与完整结果.md。两状态×原三seed，处理各多2步、多1个180°、返航尾段不变；全部立即回原起点，采到(5,3)后与原字面后缀相同。当前一次动作不支持，按稿停止。

实际24入口/24核心（12等价+12正式），2准备夹具与8干预桩分账；与v0.1停止包核验区别开。原candidate/两输入字节hash、原while AST、阶段PASS绑定及无P2运行时读取必须核对。所有门槛原版/OFF/历史及正式原版非时间字段一致。

只读完成实验核验：

```powershell
& .\运行环境\python\python.exe -B -X utf8 PPCPP一次历史邻格干预诊断_v0.2_20261021/verify.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

该核验不调用planner；每次独立BFS582次，审核若重跑请另记账，不覆盖原日志/账。日志和收据排除主manifest自引用，实际完成后completion_manifest覆盖。当前不启动后续干预或在线开发。
