import shutil,difflib,datetime
from common_orient import *
def main():
 assert not (H/'protocol.json').exists();source=R/'基线复现准备_20261019/独立版_v0.2/ppcpp.py';a=source.read_bytes();b=a.replace(b"VERSION='PPCPP_CORE4_FIXED_HISTORY_v0.2_20261019'",b"VERSION='PPCPP_CORE4_ROTATION_INTERFACE_v0.1'")
 old=b"predator[0]>max(x for x,y in s.free)";new=old+b" or predator[1]<min(y for x,y in s.free) or predator[1]>max(y for x,y in s.free)";assert b.count(old)==1;b=b.replace(old,new).replace(b'predator outside fixed flight-domain x bounds required',b'predator strictly outside flight-domain bounding rectangle required')
 dest=H/'interface/ppcpp.py';dest.parent.mkdir(exist_ok=True);dest.write_bytes(b)
 (H/'interface.diff').write_text(''.join(difflib.unified_diff(a.decode().splitlines(True),b.decode().splitlines(True),fromfile='frozen_original',tofile='new_interface_copy')),encoding='utf-8')
 prior=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020';protocol=read(prior/'protocol.json');items=[]
 for item in protocol['inputs']:
  src=Path(item['path']);target=H/'inputs'/(item['id']+'.json');target.parent.mkdir(exist_ok=True);shutil.copyfile(src,target);assert sha(target)==sha(src)==item['sha256'];items.append(dict(id=item['id'],input=str(target),source=str(src),sha256=sha(target),family=item['family'],size=item['size'],event=item['event'],progress=item['progress'],golden=str(next((prior/'execution').glob(f"*{item['id']}__b20__r0__PPCPP.json")))))
 f=[(x,y) for x in range(4) for y in range(3)]
 def fixture(name,pred,free=f,targets=[(2,1)],current=(0,0),previous=None):return dict(name=name,free=free,targets=targets,covered=[],published_targets=targets,deferred_targets=[],initial_targets=targets,current=current,base=(0,0),previous=previous,predator=pred,old_route=[current],distance_budget=1000000)
 specs=[('left_old','OLD',(-1,0),None,'core_complete'),('left_new','NEW',(-1,0),None,'core_complete'),('right_old','OLD',(4,0),None,'core_complete'),('right_new','NEW',(4,0),None,'core_complete'),('above_new','NEW',(1,3),None,'core_complete'),('below_new','NEW',(1,-1),None,'core_complete'),('boundary_new','NEW',(0,0),None,'exception'),('hole_new','NEW',(1,1),None,'exception'),('nan_new','NEW',(-1,0),'nan','exception'),('inf_new','NEW',(-1,0),'inf','exception'),('empty_task_previous','NEW',(1,3),None,'core_complete'),('empty_free_new','NEW',(-1,0),None,'exception')];fixtures=[]
 for name,mode,pred,mutation,expected in specs:
  c=fixture(name,pred)
  if name=='hole_new':c['free']=[q for q in f if q!=(1,1)]
  if name=='empty_task_previous':c=fixture(name,pred,targets=[],current=(3,2),previous=(3,1))
  if name=='empty_free_new':c=fixture(name,pred,free=[],targets=[])
  path=H/'fixtures'/(name+'.json');save(path,c);fixtures.append(dict(id=name,mode=mode,input=str(path),mutation=mutation,expected=expected))
 order=[]
 for item in items:
  for mode,deg in [('OLD',0),('NEW',0),('NEW',90),('NEW',180),('NEW',270)]:order.append(dict(sequence=len(order)+1,stage='B1',id=item['id'],mode=mode,degree=deg,input=item['input'],expected='core_complete',mutation=None))
 for fx in fixtures:order.append(dict(sequence=len(order)+1,stage='B2',**fx,degree=0))
 for ident in ('small_I_obstacle_p70','medium_L_obstacle_p30','large_Z_corner_p30'):
  item=next(i for i in items if i['id']==ident);order.append(dict(sequence=len(order)+1,stage='B3',id=ident,mode='COMBO',degree=0,input=item['input'],expected='core_complete',mutation=None))
 save(H/'order.json',order);save(H/'protocol.json',dict(created=datetime.datetime.now().astimezone().isoformat(),inputs=items,fixtures=fixtures,old_native=str(source),old_native_sha256=sha(source),new_native_sha256=sha(dest),max_entries=285,max_core_calls=294,planned_entries=285,expected_core_calls=293,budget=20,seed=20261020,watchdog=90,whitelist='For single native raw equality only version and explicit time fields seconds/budget(remaining)/accepted_seconds/overrun_gt_10ms ignored; method, trace/options/goal/state all retained. Wrapper is new and not claimed byte-identical to old wrapper. Candidate raw encoding complete; stage results are gates not speed rank.',stop='Any B1 invalid/timeout/non-time mismatch => STOP; B2 expected ValueError is passed rejection; B3 any candidate failure invalid late => failure, no salvage. No486 formal comparison, P2/exact/maps/mirror/LAST/mix/reward/optimizer/Git.',ordering='54 fixed order x OLD0,NEW0,90,180,270 then12 preregistered fixtures then3 fixed COMBO. No effect-based reordering.',transforms='13-field point-specific bijection, list order retained.0 direct; 90/180/270 common shift to minF0; predator moves with scene. Outputs inverse mapping applies only coordinate fields, not weights/rewards/time/seed.'))
 (H/'接口依赖审查与变换表.md').write_text('''# 旋转接口依赖审查（任何求解前）

唯一允许改动：独立副本中predator合法域由严格x范围外扩至严格轴对齐包围矩形外；版本和错误文案另改。副本在interface/ppcpp.py，保持与原相同parents[2]目录深度，因此ROOT/sys.path语句无须改写；其余solve逐字节保留，diff可逆验证。旧原件SHA固定，不修改共享几何或冻结奖励/历史/截止。

实际native经ppcpp_independent绑定core.reward_options/choose_neighbor。它们只用欧氏距离归一化、previous点积、邻接数及坐标tie，没有仅x外才能成立的除法/符号/朝向假设。恢复用精确图距离/坐标tie，UnifiedGeometry用sorted端点及A*，独立audit_ppcpp用math.dist/acos与BFS，没有predator.x先决条件。旧predator_for不被当前native.solve调用，绝不重新生成。共同check_contract验证单格、free/current/base/H/initial/budget，不检查捕食者方向；唯一x-only条件就是已授权新副本那一行。没有发现需扩大改动的机制依赖；不是论文创新或证明旋转路线等变。

13字段：free/targets/covered/published_targets/deferred_targets/initial_targets/old_route逐点R+t、保留列表时间/存储顺序；current/base/previous/predator逐点映射（None保持）；name、distance_budget不变。R分别(x,y),(-y,x),(-x,-y),(y,-x)。非0共同t=-min R(F)，空F用t0；0直接原对象不重排。逆映射R^-1(q-t)。90/270显示包围矩形宽高交换；入口无bitmap/W/H字段；坐标可偏置，障碍/H/暂缓/真实历史不增删。输出route、trace.current/previous/goal/options.cell、predator/initial_previous逆映射，标量权重/奖励/index/pending_count/阶段/时间/种子不转。全字段往返/四次90/非方形/偏置/历史/空集门槛在pure_tests里。

旧域是x<xmin或x>xmax，新域是旧域或y<ymin或y>ymax，严格不等；包围矩形边界、内部孔洞和仅predator不在F一律未获准。有限长度和值检查保留，空F仍先由原check_contract处理current_not_free，不额外求min/max。上下实际入口由预定fixtures验证；空F旧新源码合同相同，纯合同检查和新实际入口拒绝分开计账。

单候选与组合暖入口包含解码/validate/Snapshot/旋转/核心/逆变换/必要内审/完整raw编码；导入/启动/磁盘/独立外审在外。组合四候选共享20秒绝对截止、余时传递，任一失败或编码晚到则route空，不捞0。原core预算嵌套保持不改。90秒硬看门狗。新wrapper结构含各候选完整raw/逆映射/输入及元数据，不称新旧wrapper字节等价；0度比较native.raw而非外层时间结构。

最多285真实门槛入口，空F验证在核心前拒绝使预计真实核心293（上限294）；纯变换/合同/截止桩另账。不生成新开发地图，不跑正式486/P2/精确，不叠LAST/混合/镜像/2-opt或新奖励。原模型和旧阶段A暂停证据保持。到此仅协议和实现，未运行规划器。
''',encoding='utf-8')
 print('PREREGISTER285 entries; old frozen retained; ZERO solver calls')
if __name__=='__main__':main()
