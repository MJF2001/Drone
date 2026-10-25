import shutil,datetime,difflib
from support import *
S=R/'PPCPP_LAST新开发地图验证_v0.1_20261020';OLD=R/'PPCPP_LAST_P2共同预算开发比较_v0.1_20261020'
def main():
 assert not (H/'protocol.json').exists();shutil.copyfile(OLD/'p2_adapter.py',H/'p2_adapter.py')
 p=read(OLD/'protocol.json');slots=[s for s in p['inputs'] if s['event']=='obstacle'];assert len(slots)==18;manifest=read(S/'manifest.json');sources={};items=[]
 def evidence(path):
  path=Path(path);h=sha(path)
  if path.is_relative_to(S):assert manifest[str(path.relative_to(S))]==h
  sources[str(path)]=h;return h
 for slot in slots:
  ident=slot['id'];source=Path(slot['path']);c=read(source);assert sha(source)==slot['sha256'];evidence(source)
  base=slot['base_id'];before_path=S/'prep/inputs'/(base+'.json');prep_path=S/'prep/results'/(base+'.json');wit_path=S/'witnesses'/(ident+'.json')
  for q in (before_path,prep_path,wit_path):evidence(q)
  before=read(before_path);prep=read(prep_path);w=read(wit_path);B=pts(w['blocked']);prefix=prep['raw']['route'][:w['cut']+1]
  assert prefix==w['history'] and c['old_route']==prep['raw']['route'][w['cut']:] and c['current']==prefix[-1] and c['previous']==prefix[-2]
  assert pts(c['covered'])==pts(prefix)&pts(before['targets']);assert pts(before['free'])-B==pts(c['free']);assert pts(before['published_targets'])==pts(c['published_targets']);assert B<=pts(before['free'])
  for kind in ('event','control'):
   cid=ident+'__'+kind;dest=H/'inputs'/(cid+'.json');dest.parent.mkdir(exist_ok=True)
   if kind=='event':shutil.copyfile(source,dest);cc=read(dest);assert sha(dest)==slot['sha256']
   else:
    cc=norm(c);cc['name']=cid;cc['free']=before['free'];cc['targets']=before['targets'];cc['published_targets']=before['published_targets'];cc['deferred_targets']=sorted(pts(cc['published_targets'])-pts(cc['free'])-pts(cc['covered']));save(dest,cc)
   for field in ('current','previous','base','predator','covered','old_route','initial_targets','distance_budget'):assert cc[field]==c[field]
   env=dict(state=cc,marker=sorted(B));payload=H/'payloads'/(cid+'.json');save(payload,env)
   items.append(dict(id=cid,pair=ident,kind=kind,family=slot['family'],size=slot['size'],progress=slot['progress'],base_id=base,input=str(dest),input_sha256=sha(dest),payload=str(payload),sha256=sha(payload),source=str(source),history_source=str(prep_path),witness=str(wit_path),marker=sorted(B)))
 # Fixed12 fixtures, two real entries each; other adverse cases are stubs.
 square={(x,y) for x in range(4) for y in range(3)};line={(x,0) for x in range(4)}
 def fx(name,t,free=square,h=set(),pub=None,current=(0,0),base=(0,0),B={(2,1)},db=1000000):
  pub=(t|h) if pub is None else pub
  return dict(state=dict(name=name,free=sorted(free),targets=sorted(t),covered=sorted(h),published_targets=sorted(pub),deferred_targets=sorted(pub-free-h),current=current,base=base,previous=None,predator=(-1,0),initial_targets=sorted(pub),old_route=[current],distance_budget=db),marker=sorted(B))
 fixtures=[fx('empty_window',{(2,1)},B={(50,50)}),fx('single_target',{(2,0)},free=line,B={(2,1)}),fx('entry_exit_task',line,free=line,base=(3,0),B={(1,1)}),fx('touch_start',{(1,0)},free=line,B={(0,1)}),fx('touch_end',{(3,0)},free=line,base=(3,0),B={(3,1)}),fx('deferred',{(2,1)},free=square-{(1,1)},pub={(1,1),(2,1)},B={(1,1)}),fx('blocked_history',{(2,1)},free=square-{(1,1)},h={(1,1)},B={(1,1)}),fx('external_target',{(1,0),(2,2),(3,0)},B={(3,1)}),fx('repeated_interface',{(2,0),(3,0)},free=line,B={(2,1)}),fx('no_gain',{(1,0)},free=line,B={(1,1)}),fx('fixed_exit',{(1,0),(2,0)},free=line,base=(3,0),B={(1,1)}),fx('resource',{(2,1)},db=0)]
 save(H/'fixtures.json',fixtures)
 order=[];methods=['PPCPP','LOCAL_P2','P2_MULTI']
 for rep in range(3):
  for i,item in enumerate(items):
   k=(i+rep)%3
   for m in methods[k:]+methods[:k]:order.append(dict(sequence=len(order)+1,id=item['id'],method=m,repetition=rep,seed=20261020+rep,budget=20))
 save(H/'formal_order.json',order)
 save(H/'protocol.json',dict(created=datetime.datetime.now().astimezone().isoformat(),inputs=items,sources=sources,max_formal_entries=324,max_gate_entries=24,gate_real_entries=24,gate_plan='12 frozen fixtures x [PPCPP,LOCAL_P2]; independent full/prefix/task/exit audit. Pure stub tests cover internal deadline/invalid/exception/tie/shorter/mandatory incidental external target. Gate actual internal counts saved individually.',window='Exactly radius2 Manhattan-to-B first effective captures in freshPPCPP P; min..max envelope plus one vertex each side, clipped; required all first captures with left<i<=right, localH=originalH | target(prefix through left), fullF, fixed entry/exit, old local fallback=original_patch, local remaining distance subtract fixed prefix/suffix; incidental captures kept and suffix unedited.',budget=20,watchdog=90,seeds=[20261020,20261021,20261022],methods=methods,stage_A='Input/control provenance and local interface reviewed before any planner call; no new history solve',return_policy='No time/invalid/exception rescue. Strictly shorter assembled full route chosen, tiesP0; empty windowP0. Global P2 native soft return retained and separately classified by actual entry.',environment='Seal before gates, final full verify before/after formal; threads1 fresh processes; all transforms/selection/splice/acceptance/encoding included',stop='Fixed324 then stop; gates fail stop; no expanding radius/windows/other strategies/exact/holdout/Git'))
 (H/'预登记.md').write_text('# PPCPP局部P2混合预登记\n\n36固定输入=全部18obstacle原件+18同历史控制。事件来源before输入、准备原始路线、前缀/障碍见证均由原manifest核hash；仅恢复本次B。原事件原样复制，控制保留当前位置/前步/H/基地/捕食者/旧后缀。worker只读包含原状态与B标记的公开payload，三方法均在暖入口解码；事件原件另存核hash。控制B仅为选区标记。\n\n单窗口固定radius2/minmax首次采集包络±1，不加阈值/多窗口。完整F固定入口出口，局部H是真实前缀已采（包含原H），required为left<i<=right首次采集；入口已由前缀即时采集，不重复分配。局部Snapshot.targets=required, covered=localH（允许H在任务子集外），current=入口，base=出口，old_route=原局部窗口；距离额度减去固定外部步数。全图实际移动计账，后缀字面保留。\n\n复用range_p2_engine_20261015原件，不修改冻结P2搜索。该副本仅原有accept回调差异；callback同时审local任务/出口和full拼接，非法抛显式失败，不静默回P0。原PPCPP生成计时内；全局P2复用上轮薄包装原件。\n\n24真实门槛=12夹具×原PPCPP/混合；空窗/单目标/入口出口任务/两端触及/暂缓/历史遮挡/外部目标/重复接口/无收益/固定出口/资源，纯桩另验必经外部目标与后缀不删、非法/异常/同长/短选、P0前后/窗口/局部内部/拼接/终审/编码截止。桩不计核心求解。\n\n每方法20秒暖入口；混合共享绝对截止，局部只获余量，整入口晚到无route；原PPCPP整体晚到也无route，整体P2原生软截止保留并另分及时/迟到。90秒硬看门狗；串行新进程/线程1。36×3×3=324，轮换顺序formal_order。正式最多原PPCPP108、混合内部PPCPP108+局部108、全局P2108，按实际调用账统计。\n\n事件/控制分别双视图、全部原值/三种子均值/分层。有限信号只按事件至少两族四base_id且三重复完整收益；控制也改善不得称障碍专用。固定每族事件收益最大/正收益下中位/零收益字典序最多9组，重复0且附对应控制，不补缺类。任何门槛失败保存停止；324后停止待审核。\n',encoding='utf-8')
 frozen=R/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010/frozen_baselines/v2_20261012/source/p2_search_audit.py'
 (H/'local_engine.diff').write_text(''.join(difflib.unified_diff(frozen.read_text(encoding='utf-8').splitlines(True),(R/'range_p2_engine_20261015.py').read_text(encoding='utf-8').splitlines(True),fromfile='frozen_p2',tofile='existing_local_engine')),encoding='utf-8')
 print('StageA provenance/36inputs/window/interfaces preregistered; ZERO planner calls')
if __name__=='__main__':main()
