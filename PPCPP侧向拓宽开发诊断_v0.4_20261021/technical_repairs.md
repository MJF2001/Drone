# 准备链技术修复与演练账

v0.3来源逐字节复制记录见source_manifest_initial；最终活动代码hash/用途及完整diff另存。冻结算法、worker原任务体、原生成几何/历史规则、原20秒计时块、指标及判据不变。仅新增预检、输入独立验收和报告控制工具。

参考契约先检查全部继承源hash；三个指定文件不存在时xb创建，存在则检查普通文件/意外重解析路径与原bytes/mtime，冲突立停，创建竞态仅捕获FileExistsError后读验。seal固定工件保持hash绑定，actual_order与根目录持续追加的*_execution.log不在阶段seal中，其最终字节进入最终manifest。

第一轮在A解析前辅助工具编码名utf8-sig错误而停止，未执行其余项；改为Python正确编码名utf-8-sig。失败stdout/源快照保留。

第二轮A、B1真实链无任务导入、四B2真实worker/stub夹具、四参考情形、C真实展平与长字段回读、两独立门控负例、原八统计桩通过；整链在第一seal的清单JSON解析失败，未跑完。原因是stub引导器把闭包诊断额外打印到inventory stdout；仅在该inventory分支将诊断改至stderr。此失败属于测试隔离，未执行真实求解。进一步加入实际seal的不一致参考/过期PASS负例、真实run缺前置阶段和已有输出阻断，并接上事件输入独立审计receipt（生产默认6/12/288不变）。

第三轮将重跑全部检查；其实际通过/失败以round_03/round_result.json为准，不以本说明代替结果。最多三轮，不再追加轮次。每轮未完成阶段明确保留，不把独立夹具成功当整链已通过。

B1使用真实依赖与profile禁止实际求解，监测/拒绝任务audit注册；B2和整链仅注入明确STUB来源接口，实际common hash/require、seal、run、worker和export/csvcheck控制实现仍执行。整链合成计划6准备/12门槛/2正式，保留run固定past-count断言，手工微型任务只验证文件阶段契约；合成事件生成与analysis.compute数据选择明确替代，不能当原48几何已可行。完整verify的研究语义部分留到真实数据，演练已实际调用其csvcheck和common封存/收据逐hash只读校验。

阶段依赖见stage_dependencies.json，无自hash循环。只读核验脚本不导入规划器。全部技术尝试单列，未产生生产actual_order/outputs，真实入口前的修复权限在第一条真实调用后终止。
