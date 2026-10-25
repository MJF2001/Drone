# PPCPP局部P2混合诊断

已封存，待负责人审核。结果见混合方案结果报告.md。36输入/来源协议、local_engine.diff、事前environment_seal、24门槛及桩、324 jobs/execution/logs/actual_order、analysis/全CSV/固定事件与控制图、failures/review_packet、manifest与verify齐全。旧冻结/历史/留出不改。

原environment.py同名模块故障和一次封存未就绪均发生于0求解，原日志保留；完成后继环境封存后才运行24实际门槛。正式不使用测试钩子。

只读核验：包内Python -B -X utf8 本目录/verify.py。manifest仅排除自身和verify.log。
