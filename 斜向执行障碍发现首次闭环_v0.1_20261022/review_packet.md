# Review packet

先读 00_通俗报告与闭环结果.md，再看 figures 的三世界实飞图、合同与查询上限.md、registration.json。六会话完整初态/动作/终态及运行时独立审核在 sessions；逐行 flush 的同一 hash 链在 logs/*_actions.jsonl。十二真实公开输入在 calls/*_public_input.json，原生/后处理原文在 calls/*_return.json，完整计划及主/独立审计在 outputs。已执行前缀与预测路线分开，不求预测长度之和。

worlds_public 与 worlds_private 分开；private 仅环境和审核使用。bindings.json 为逐文件上游来源；原数值管线四函数源码段未改说明及接入 diff 一并保留。H1/P2 核心/奖励/直达及公共资源/几何来自已验收冻结来源，未作算法优化。audit_expected_identity.json、每会话和计划的模块/函数身份，以及 real_freeze.json 证明求解前绑定和前后未变。

technical_freeze.json 固定地图、夹具、合同与初始源码；technical_rounds/round_1 有十二纯会话和手算结果、源 hash、无核心调用收据。真实开始前 real_freeze.json 二次冻结执行器和源码；real_started.json 及 batch_receipt.json 固定六会话一次执行，十二入口已到上限，无真实补跑。old_files.json/external_source_guards.json 保护历史1277记录及外部加载依赖。

调用与查询总账.json 分开纯门槛、世界结构检查、真实管线/执行、运行时审核和保存复核。保存 verify 为独立解析回放，禁止算法入口、选择器、后处理和图搜索；第一次实际收据在 verification_runs/verify_1.json。每次再次 verify 会另存新收据并如实产生新的保存审核几何查询，不是零计算。

本机只读核验命令（不重跑算法）：

    .\运行环境\python\python.exe -B -X utf8 '斜向执行障碍发现首次闭环_v0.1_20261022/verify.py'

manifest.json 绑定封存文件，final_receipt.json 绑定清单及首次 verify；verification_runs 新收据是后续附加审查，不改封存结果。root_before.md/root_after.md 是根进度前后快照，不要求实时根进度永远不变。presentation.py 仅在结果完成后读取保存证据生成文图，无任何算法或几何查询，不属于正式求解后修补。完成即停止交审。
