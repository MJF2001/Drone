import shutil,datetime
from support import *
S=R/'PPCPP_LAST距离查询等价提速_v0.2_20261020'
def main():
 for name,src in [('runtime.py','runtime.py'),('candidate.py','candidate_v2.py'),('common.py','common.py'),('audit.py','audit.py'),('audit_adapter.py','audit_adapter.py')]:
  shutil.copyfile(S/src,H/name);assert sha(H/name)==sha(S/src)
 slots=read(S/'protocol.json')['slots'];inputs=[]
 for slot in slots:
  source=R/'PPCPP_LAST新开发地图验证_v0.1_20261020/inputs'/(slot['id']+'.json');dest=H/'inputs'/(slot['id']+'.json');dest.parent.mkdir(exist_ok=True);shutil.copyfile(source,dest)
  inputs.append(dict(**slot,path=str(dest),source=str(source),sha256=sha(dest)))
 f={(x,y) for x in range(4) for y in range(3)}
 def fixture(name,t,free=f,h=set(),current=(0,0),base=(0,0),old=None,db=1000000):
  return dict(name=name,free=sorted(free),targets=sorted(t),published_targets=sorted(t|h),covered=sorted(h),deferred_targets=[],initial_targets=sorted(t|h),current=current,base=base,old_route=old or [current],previous=None,predator=(-1,0),distance_budget=db)
 fixtures=[fixture('empty',set()),fixture('single',{(2,1)}),fixture('history',{(0,0),(2,1)},h={(0,0)}),fixture('wide',f),fixture('obstacle',{(2,2)},free=f-{(1,1)}),fixture('suffix_new',{(1,0),(2,1)},old=[(0,0),(1,0),(0,0)]),fixture('broken_suffix',{(2,0)},free=f-{(1,0)},old=[(0,0),(1,0),(2,0),(1,0),(0,0)]),fixture('base_unreachable',{(0,0)},free={(0,0),(2,0)},base=(2,0)),fixture('resource',{(2,1)},db=0)]
 save(H/'fixtures.json',fixtures);order=[];methods=['PPCPP','LAST_V2','P2_MULTI']
 for rep in range(3):
  for i,s in enumerate(inputs):
   for budget in ([1,20] if (i+rep)%2==0 else [20,1]):
    k=(i+rep+(budget==20))%3
    for method in methods[k:]+methods[:k]:order.append(dict(sequence=len(order)+1,case_id=s['id'],method=method,budget=budget,repetition=rep,seed=20261020+rep))
 save(H/'protocol.json',dict(created=datetime.datetime.now().astimezone().isoformat(),inputs=inputs,methods=methods,budgets=[1,20],seeds=[20261020,20261021,20261022],max_formal=972,max_gates=120,planned_gates=49,gate_plan='9 fixed fixtures: original P2 wrapper / adapter plus PPCPP/LAST each =36; LAST9 fixed post-P0 late injections=9; P2 original/adapter before acceptance and after first accepted fallback cutoff=4; total49. P2 gate budget5 seed20261020. Geometry Spy used within first original/adapter pair. No formal-input P2 trial.',clock_plan='P2 gate clock fixed0 in isolated module time references; Geometry.check_time raises before geometry or on second internal audit, after first accepted fallback. Restore all globals. Formal code has no patches. LAST9 hooks advance common clock30; reuse sealed incidental fixture. Late-output classification unit test keeps route.',timing='Original PPCPP/LAST run_payload unchanged with budget1/20. P2 adapter duplicates baseline_suite P2 branch only excluding independent external audit; outer decode/validation/Snapshot/contract/all offer checks/raw JSON encoding timed. All external independent audits after returned entry; no late route deletion for P2.',views=['timely_valid paired','all valid native returns paired; late retained'],resume='Only jobs absent from job directory are unstarted. A started job without final output stops for assessment, never silently rerun. Existing outputs retained even failures.',stop='972 calls then stop; no tuning/maps/extra seeds/other algorithms/exact/holdout/Git',limitations='54 seen development states share nine maps/history. No full-machine image.'))
 save(H/'formal_order.json',order)
 (H/'预登记.md').write_text('# LAST V2与P2共同预算比较预登记\n\n协议、9夹具和972轮换任务在任何本轮规划器调用前固定。54已见原输入原样复制；预算1/20秒，三重复种子20261020/21/22；按状态/重复轮换预算顺序和方法顺序，串行独立进程/线程1。\n\n先完整环境事前封存且等待写入成功，再49次门槛（最多120）验证P2薄包装、保底/无接受截止、LAST原9注入、输出口径和缓存隔离。P2不改offer/搜索/中止频率/保底，仅外部独立audit移出暖入口。完整raw编码仍计时；原生deadline可有路线，按实际entry<budget另判及时。\n\n实际交付和全部合法原生返回两视图分预算、同输入同种子配对，所有失败/迟到保留，不用缺失0步；不取最佳种子。全路线双指标、LAST所有分支独立决策审核，P2来源/接受记录/阶段重核。固定正反图按各预算/重复/视图先过滤类别，按差距及编号排序选；迟到类别按编号预算重复方法序选；缺类不补。\n\n完整事前环境清单范围为包内Python、项目.deps所有源/二进制/元数据、冻结源码配置、实际导入链/可识别非系统DLL；Windows系统DLL仅列路径不封全机。每worker检查完成标志、实际导入hash；运行前后重核全清单，新增未封存导入立即停止。\n\n运行期间逐任务落盘；只续未启动任务，不复跑失败挑成绩。972后停止等待审核，不改LAST/P2，不加图/预算/种子/其他方法，不跑精确最优或留出，不提交推送。\n',encoding='utf-8')
 print('PREREGISTERED54 inputs,9fixtures,972jobs; ZERO planner calls')
if __name__=='__main__':main()
