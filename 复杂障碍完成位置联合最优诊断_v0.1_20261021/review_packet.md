# 审核入口

先读通俗结论与最优分解报告.md、16状态最优分解.csv、protocol.md。16张三路线图均为原数据，类别首例与缺类见analysis.selected/missing_categories。

原始prep/inputs/histories、outputs、requests/exact/certificates、gate_fixtures、actual_order与两阶段seal保留；两套源码exact_bfs.py/exact_dijkstra.py没有共用转移，joint_proof.py只核保存证明。

一键只读：运行环境/python/python.exe -B -X utf8 本目录/joint_verify.py；不运行规划器/覆盖精确搜索。显式重新求解只可在新的空目录按同setup/prep/build/seal/gate/formal/exact流程新建批次，所有操作重新计账，不在verify中隐藏复算；本轮不自动执行。

已封存，待负责人审核。
