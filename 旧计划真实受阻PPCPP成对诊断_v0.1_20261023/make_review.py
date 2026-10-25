from common import *
from collections import Counter
def main():
 assert not (H/'review_packet.json').exists()
 s=read(H/'summary.json');l=read(H/'ledger.json');extra=read(H/'行为补充与阶段分解.json');fallbacks=Counter();late=Counter()
 for j in read(H/'plan.json')['jobs']:
  x=read(H/'outputs'/(j['id']+'.json'));fallbacks[str(x['post_envelope']['fallback'])]+=1
  for k in ('native_late','raw_stage_late','combined_late','post_late'):late[k]+=bool(x['timing'][k])
 assert fallbacks=={'None':108} and all(v==0 for v in late.values())
 dump(H/'review_packet.json',{'status':'completed_pending_seal_stop_for_owner_review','draft':'v2 only; suspended prior draft not executed','primary':'B_E vs B_N from actual PPCPP calls in both environments','processing':l,'complete_views':216,'selected_cases':6,'shapes':['I','L','Z'],'obstacle_position_for_all':[0,1],'scope':'pre-event preparation cuts; introduced-at-cut non-target return corridor obstacle only; no new target event/sensing/closed loop; no small cases; distinct bases do not imply diverse obstruction patterns','B_delta_meters':s['delta_B_state_equal'],'B_relative_delta_state_equal':s['relative_delta_B_state_equal'],'B_time_delta':s['B_time_delta_pairs'],'B_full_trace_anchor_credit_same_pairs':18,'B_prefix_through_last_anchor_same_pairs':18,'B_raw_length_delta':0,'R_raw_length_delta':2,'B_E_R_E_same_post_route_pairs':18,'B_E_R_E_same_raw_route_pairs':extra['same_B_R_raw_E'],'all_B_delta_in_saved_return_stage':True,'C_shorter_in_N_and_E':'18/18 paired, already shorter in N; not optimum/lower bound/event-causal loss','classification':'all six tier2, no new event-driven coverage-order decision mechanism justified','post_fallback_counts':dict(fallbacks),'late_counts':dict(late),'preparation_failure_retained':True,'preparation_repairs':1,'export_correction':'report v0.2 only; original raw-edge-count draft retained; no solver rerun','new_innovation_claim':False,'new_intervention_recommended':False,'stop_after_seal':True})
 dump(H/'图版目视核验.json',{'figures':7,'viewed_all':True,'scope':'saved first-seed N/E × B/R/C routes plus return-only enlargement, legible labels, common map extent within case, no new route calculations','seed':20261020,'new_core_R_post_geometry_BFS':0})
 (H/'review_packet.md').write_text('''# 负责人审核入口

先读00_通俗成对诊断报告.md（报告v0.2），再读02配对及03时间/转弯/阶段。研究对象是PPCPP＋直达，R为诊断工具，P2为外部参照。

108处理=72核心+36 R，216视图全部完成责任返航，无正式失败/触顶/迟到/未运行。12固定纯案例经1轮修复通过，首轮失败和源码保留；报告草稿误归原生+2步已留首版并仅据保存指标纠正，无重跑。

6个base、3形状族，但全部返航端[0,1]，不是多样内部阻断。18组B完整trace/锚点/信用不变，至末锚点前缀逐点相同；B原生边数N/E不变，直达平均增程0.402383米，全部落在保存返航标签内。R原生多2步，直达后与B_E相同。P2在N已短，不把E差距归为障碍造成顺序失配。全部第二档，未建议干预覆盖顺序，不宣布局部修复最优或普遍无需重排。

selection/input_freeze/history保留共同快照、真实旧计划来源、阻断严格内部参数与可达性；plan/active_freeze/bindings保留实现/顺序/预算。attempts/status/outputs是108槽实账与原始返回、post及独立审核。216视图、18配对、行为与阶段证书、原生与直达变化澄清和全查询/BFS账单独可查。最终verify仅读绑定与hash，不运行核心/R/post/几何/BFS。

封存停止交审；无留出、新图、新任务扩展、新闭环、安装训练或推送。
''',encoding='utf-8')
 print({'review_packet':True,'post_fallbacks':dict(fallbacks),'late':dict(late),'new_calls':0})
if __name__=='__main__':main()
