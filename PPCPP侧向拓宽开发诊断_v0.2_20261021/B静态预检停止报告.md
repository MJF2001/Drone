# 侧向拓宽v0.2：两处语法修复完成，B项静态预检阻断

本版按接续稿完成了两处已授权字典语法修复，12个活动Python源码全部通过ast.parse。B项静态审查发现worker.py的任务体仍在模块顶层：普通导入会依赖sys.argv读取任务/输出路径、安装审计钩子，具备直接调用runtime.run_payload或p2_adapter.run_payload并写正式结果的路径。没有main守卫。

执行稿第3B节明确要求：**“若静态检查发现导入本身会求解或写正式结果，停并报告，不直接执行有副作用的导入。”** 因此在动态导入前停止，未用inventory分支退出、删掉worker导入或伪造argv来冒充普通导入安全；这些不能证明导入没有副作用。

## 已完成的修复与保全

v0.1停止包只读verify已实际全部通过，日志upstream_verify_stopped.log；原目录和冻结算法未修改。新版source_manifest逐项记录原/新hash：analysis.py和verify.py只做已批准visits_A/pp_first_A_event字典key:value修正，其余接续源码按字节复制。统一diff为v0.1_to_v0.2.diff。

六初始输入和原prep job/map定义逐字节相同；runtime/candidate/p2_adapter从冻结源二进制复制并与v0.1来源预期hash核对。没有复制旧seal、PASS、STOP或manifest充当新状态。旧失败源码仍保留在v0.1，未冒充新版活动源码。

preflight/active_syntax.json记录A项当时全部12活动源码hash和逐项PASS；新增停止包审计程序是停止后工具，不用于继续生产，单独列最终manifest。A通过不代表B/C/实验通过。

## B项具体证据与适用边界

preflight/import_static.json及B_STATIC_BLOCK.json列worker顶层的实际行号和调用表达式：sys.addaudithook、runtime.run_payload、p2_adapter.run_payload和写输出的open。worker.py与v0.1逐字节相同；此缺陷不是新增语法修复引入，而是本轮要求的静态检查新定位到的既有启动结构风险。

静态发现的是“存在导入触发任务的代码路径”，没有实际导入验证或试算。无任务argv时还会在顶层sys.argv访问处失败；提供真实任务argv则可能继续进入任务。无论哪种都不能算所要求的安全导入链。没有断言已经发生求解或写出正式结果。

## 尚未运行

B动态导入0、C合成导出—回读0、两个负向夹具0、新版八统计桩0；没有继承v0.1八桩PASS。技术预检总PASS及两阶段seal均未创建。生产预检门控接线尚未完成，不具备运行资格。

真实入口/核心均0，原6准备＋12门槛＋288正式全部未运行，上限仍306；真实历史/候选表/事件输入0。任务位置规则可生成48状态尚未验证，有限继续信号及路线优劣仍NOT_TESTED。无图搜索、P2/LAST/覆盖精确/留出或额外试运行。

## 未应用的最小修复提案

worker_main_guard_PROPOSAL_NOT_APPLIED.diff仅提出将既有任务体放进main，并以__name__守卫调用；其body AST与原任务体相同，未改几何、seed、预算、求解分支、计时块或算法。proposal JSON记录原hash、结构相同检查和未应用标志。**该提案没有应用到活动worker，也未做动态导入或算法验证。**

这是对两处字典修复之外的worker入口结构新增修复。稿件已规定B发现此问题必须先停，故留给负责人裁决；没有利用“必要门控”解释绕过明示停止条件自动继续。

## 停止包核验

verify_stopped_v02.py只读核对旧包hash、两处最小修复、冻结参考与六输入字节、A记录/B静态调用、无动态/合成/桩/真实运行、未应用提案和306未运行账。它不导入worker或planner，也不代表完成技术总门槛/实验；实际日志与收据另存。

更新根进度为“两处修复完成、A通过、B静态阻断、真实入口0”，封存等待审核；不创建后继实验、不提交推送。
