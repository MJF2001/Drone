# v0.2 Review packet

先读00_通俗接续与中止报告.md、三栏调用与查询账.json、final_receipt.json。原失败保留、保存复核复用、新增执行是三种不同来源。v0.2也按新异常停止，不能当成六会话成功。

changes.json/修复.diff限制改动；采集/核心/路线机制不变。precheck_registration.json和precheck.json是六项12分支零核心预检；preparation_failure_1是预检前依赖登记错误及修复，旧35纯案例只hash复用。reuse_receipt.json及outputs/W1_H1_plan_1.json中的provenance保留原135、旧failed来源hash、派生分类及完整复核。reuse_session_seed.json是旧起点动作及状态，不是新核心。real_freeze.json证明真实开始后程序不变。

sessions/logs保存3条实际会话，两完成一失败；后三未运行在batch_receipt中。outputs中5份新计划含失败W2_P2_plan_2；每份independent_counts_actual_even_on_exception为finally真实落盘计数。calls保留5次新原生/后处理及公开输入；旧首槽原返回仍在v0.1，不拷旧结果冒充新增。实际等待记录绑定完整计划hash，失败的第二返回未执行。

保存核验命令：

    .\运行环境\python\python.exe -B -X utf8 '中心有效采集区统一接入最小验收_v0.2_20261022/run_center.py' verify

verification_runs每次新收据有新增保存几何/区域查询，核心/选择器/后处理搜索0。失败计划未被保存核验改通过。manifest绑定封存原始证据；根进度前后快照不要求实时根文档永远相等。export_and_seal_v02只读取保存结果导出/结构封存，无算法入口。完成后不再修零值键、不自动用剩余额度或补跑。
