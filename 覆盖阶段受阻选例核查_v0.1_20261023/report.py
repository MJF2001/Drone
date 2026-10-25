"""Reports and figures from saved old routes and saved scan receipts, no geometry."""
from common import *
from collections import Counter,defaultdict
import csv,json,math
from PIL import Image,ImageDraw,ImageFont
def main():
 assert not (H/'summary.json').exists()
 s=read(H/'scan_results.json');usable=read(H/'usable_snapshots_v02.json');rows=s['rows'];full=[r for r in rows if 'physical_cut_sha256' in r];no=[r for r in rows if r['status']=='no_allowed_coverage_cell']
 assert len(full)==44 and len(no)==42 and s['gap_count']==0
 assert all(r['eligible_single_cells']==r['eligible_adjacent_pairs']==0 for r in no)
 byshape={shape:dict(Counter(r['status'] for r in rows if r['shape']==shape)) for shape in ('I','L','Z')}
 summary={'source_labels_considered':len(rows),'source_labels_detailed_suffix_analysis':len(full),'duplicate_selected_base_labels_skipped':len(rows)-len(full),'bases_considered':s['distinct_base_ids_scanned'],'physical_cuts_detailed':s['distinct_physical_cuts'],'unqualified_labels':len(no),'unqualified_physical_cuts':len({r['physical_cut_sha256'] for r in no}),'qualified_distinct_bases':len(usable['selected']),'qualified_shapes':sorted({r['shape'] for r in usable['selected']}),'status_counts':s['status_counts'],'by_shape':byshape,'initial_pending_or_S_base_exhaust_all_unqualified_coverage_cells':all(r['coverage_endpoint_unique_cells'].get('initial_H_allowed',0)==r['coverage_endpoint_unique_cells'].get('non_target_transit_allowed',0)==0 for r in no),'unreachable_rejections':sum(t['status']=='reject_free_but_unreachable' for r in rows for t in r['candidate_checks']),'no_strict_interior_rejections':sum(t['status']=='reject_no_qualifying_strict_interior' for r in rows for t in r['candidate_checks']),'candidate_cap_exhausted_states':sum(r['status']=='no_qualified_within_20_unchecked_pool_retained' for r in rows),'counts':s['counts'],'selected':[],'new_algorithm_core_R_candidate_route_shortcut_performance_calls':0,'scope':'selection feasibility only; two Z bases do not provide multi-shape evidence, no algorithm behavior or reward evidence; no rerun of previous108'}
 for x in usable['selected']:
  r=read(H/'records'/(x['id']+'.json'));c=read(H/x['certificate']);contract=read(H/x['contract_certificate']);n,e=read(H/x['N']),read(H/x['E']);t=c['strict_coverage_blockages'][0]
  summary['selected'].append(dict(x,obstacle=c['obstacles'][0],first_invalid_edge=t['edge'],other_invalid_edges=[t['edge'] for t in c['strict_coverage_blockages'][1:]],pending_at_start=t['pending_at_start'],last_first_service_index=t['last_first_service_index'],remaining_at_snapshot=r['summary']['remaining_tasks'],H_witness_prefix_index=contract['blocked_initial_H_evidence'][0]['first_original_prefix_index'],N_active_targets=len(n['targets']),E_active_targets=len(e['targets']),published_targets=len(n['published_targets']),H_count=len(n['covered']),current=n['current'],previous=n['previous'],base=n['base'],resource=n['distance_budget']))
 dump(H/'summary.json',summary)
 ledger={'algorithm_or_core':0,'R_repair':0,'candidate_coverage_routes':0,'shortcut':0,'performance_batches':0,'new_closed_loops':0,'geometry_and_connectivity_selection':s['counts'],'source_label_cap':54,'per_state_candidate_cap':20,'distinct_base_selected_cap':6,'observed_selected':2,'snapshot_contract_normalizations':2,'contract_fix_replayed_geometry':0,'hypothetical_occlusion_examples':6,'hypothetical_occlusion_geometry_BFS_calls':0,'old_108_reexecuted':False,'new_base_maps':0,'holdout':False,'push':False,'stop_for_owner_review':True}
 dump(H/'ledger.json',ledger)
 # Every source label appears, including the ten same-base skips. They are not
 # silently counted as ten negative geometric tests.
 fields=['id','base_id','shape','size','progress','status','remaining_tasks','suffix_edges','last_first_service_vertex','phase_edges','coverage_endpoint_unique_cells','eligible_single_cells','eligible_adjacent_pairs','allowed_any_suffix_cells','allowed_return_only_cells','candidate_checks_count','candidate_checks','physical_cut_sha256','counts']
 with (H/'54来源完整分类账.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(r[k],ensure_ascii=False) if isinstance(r.get(k),(dict,list)) else r.get(k) for k in fields})
 text=['# 全来源分类账与索引','', '54个来源标签均按ID考虑；44个后缀完成逐点/逐边分类。10个标签因同base已冻结首个合格样本而跳过，不当负例或几何失败；这些含同base其他进度，未进一步证明它们可选或不可选。详细分析共16个物理切点，不是54个独立场景。','', '|来源ID|base|结果|未采U|末次首次服务顶点|≥2未采覆盖边数|仅余1个的边数|返航边数|合法单格池|候选检查|','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:
  p=r.get('phase_edges',{})
  text.append('|'+r['id']+'|'+r['base_id']+'|'+r['status']+'|'+ '|'.join(str(r.get(k,'未分析')) for k in ('remaining_tasks','last_first_service_vertex'))+'|'+ '|'.join(str(p.get(k,'未分析')) for k in ('coverage_at_least_2_pending','before_last_but_only_1_pending','return_after_last_service'))+'|'+str(r.get('eligible_single_cells','未分析'))+'|'+str(r.get('candidate_checks_count',0))+'|')
 text+=['', 'no_allowed_coverage_cell不是达到20次上限，而是满足覆盖阶段/剩余数量条件的格心单位边，其所有可穿内部端点格均是初始未采任务或S。对这种边，禁飞格内部相交只能发生于其两个端点格；因此空单格池亦无符合身份限制的两格组合。每条边和每个首次服务位置保存于records/，按source_state.json查找。','', '覆盖边的pending_at_start只统计first_service_index>edge_index的初始剩余任务：走到边起点时已经首次服务的格不再计未完成；但初始U身份仍禁止作为此时公开的新障碍，不能用未来计划采集来追认已采。']
 (H/'01_全扫描分类账与索引.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
 receipts=['# 两个可用覆盖阶段阻断快照','', '本轮只证明选例存在和责任/可达性条件，不运行恢复、PPCPP、P2或直达，不证明任何路线收益。下面均为已采目标格阻断；正式可用E指E_contract_v02.json，初始仅复制F的E.json保留为未规范化草稿，不能投入算法。','', '|来源/base|障碍格|原前缀首次见证索引|失效旧后缀边|边起点未完成|末次服务顶点索引|快照未采U|P/H|active T：N→E|','|---|---|---:|---|---:|---:|---:|---|---|']
 for x in summary['selected']:receipts.append(f"|{x['id']} / {x['base_id']}|{x['obstacle']}|{x['H_witness_prefix_index']}|{x['first_invalid_edge']}, {x['other_invalid_edges']}|{x['pending_at_start']}|{x['last_first_service_index']}|{x['remaining_at_snapshot']}|{x['published_targets']}/{x['H_count']}|{x['N_active_targets']}→{x['E_active_targets']}|")
 for x in summary['selected']:
  cert=read(H/x['certificate']);record=read(H/'records'/(x['id']+'.json'));n=read(H/x['N']);ct=read(H/x['contract_certificate'])
  receipts+=['','## '+x['id'],'',f"S={x['current']}，来向点={x['previous']}，基地={x['base']}，给定资源={x['resource']}米；捕食者={n['predator']}。公开目标P、原H、初始未采U、S/来向/基地/资源完全保留。",'', '严格内部失效证书：']
  for t in cert['strict_coverage_blockages']:receipts.append(f"- 边{t['edge']}：{t['a']}→{t['b']}，开参数区间({t['open_t_interval'][0]}, {t['open_t_interval'][1]})，内部点t={t['interior_witness_t']}、坐标{t['point']}；起点仍有{t['pending_at_start']}个未完成任务。")
  for kind in ('N','E','certificate','contract_certificate'):
   p=H/x[kind];receipts+=['',f"{kind}：[{p.name}]({str(p.resolve()).replace(chr(92),'/')})；SHA256 {sha(p)}"]
  receipts+=['','![旧后缀与首次服务位置]('+str((H/'figures'/(x['id']+'.png')).resolve()).replace('\\','/')+')']
 receipts+=['','## 字段契约修正的边界','', '当前接口规定targets=T=P∩F、deferred=P−F−H。阻断已完成任务格后，该格离开可飞有效T，但仍留在P和H；U=T−H完全不变，D仍空。初始输出只改F使T仍包含该已采禁飞格，属于输入规范化缺口；旧文件与首轮冻结原样保留，新E以v02另存并附新hash/冻结。此修正未换障碍、未动任何未采任务、未改S/来向/资源、未重跑几何/BFS，更没有运行算法。两张自由域与原合格证书一致，BFS检查的原U也一致。']
 (H/'02_可用快照与阻断证书.md').write_text('\n'.join(receipts)+'\n',encoding='utf-8')
 # Two figures: full saved suffix + local completed-cell detail + service timeline.
 font=lambda n:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
 for x in summary['selected']:
  r=read(H/'records'/(x['id']+'.json'));n=r['N_source_reconstruction'];F=ps(n['free']);P=ps(n['published_targets']);hh=ps(n['covered']);suffix=r['suffix'];last=r['last_first_service_vertex_index'];first=r['first_services'];ob=tuple(x['obstacle']);im=Image.new('RGB',(1700,1220),'white');d=ImageDraw.Draw(im)
  d.text((25,18),x['id']+'：覆盖阶段阻断已采格，非返航端',font=font(27),fill='#152943');d.text((25,62),'绿=至少2个未采时的旧后缀；黄=仅剩1个；灰=末采后返航；橙=新增障碍；点色表示旧首次服务位置',font=font(18),fill='#34445a')
  allp=suffix+n['published_targets'];xmin=min(p[0] for p in allp);ymin=min(p[1] for p in allp);xmax=max(p[0] for p in allp);ymax=max(p[1] for p in allp);scale=min(870/(xmax-xmin+2),690/(ymax-ymin+2));ox=35;oy=120
  def xy(p):return ox+(p[0]-xmin+.75)*scale,oy+710-(p[1]-ymin+.75)*scale
  for p in F:
   if not (xmin<=p[0]<=xmax and ymin<=p[1]<=ymax):continue
   a=xy((p[0]-.5,p[1]+.5));b=xy((p[0]+.5,p[1]-.5));d.rectangle((*a,*b),fill='#f2f5f8',outline='#e0e6ed',width=1)
  for p in hh:
   xx,yy=xy(p);d.ellipse((xx-2,yy-2,xx+2,yy+2),fill='#9b9fa6')
  for i,f in enumerate(first):
   xx,yy=xy(f['cell']);v=i/max(1,len(first)-1);color=(40,90+int(90*v),190-int(50*v));d.ellipse((xx-3,yy-3,xx+3,yy+3),fill=color)
  for e in r['edges']:
   color={'coverage_at_least_2_pending':'#248065','before_last_but_only_1_pending':'#d6a521','return_after_last_service':'#929eab'}[e['phase']];d.line([xy(e['a']),xy(e['b'])],fill=color,width=2)
  aa=xy((ob[0]-.5,ob[1]+.5));bb=xy((ob[0]+.5,ob[1]-.5));d.rectangle((*aa,*bb),fill='#f37945',outline='#bc4025',width=2)
  for key,label,fill in [('current','S','#b9273d'),('base','基地','#17263c')]:
   xx,yy=xy(n[key]);d.ellipse((xx-5,yy-5,xx+5,yy+5),fill=fill);d.text((xx+6,yy-20),label,font=font(18),fill=fill)
  p=next(z['cell'] for z in first if z['vertex_index']==last);xx,yy=xy(p);d.ellipse((xx-6,yy-6,xx+6,yy+6),outline='#185bb6',width=3);d.text((xx+8,yy+3),'末次新任务 #'+str(last),font=font(16),fill='#185bb6')
  d.text((35,850),'空间图裁剪至旧路线/任务外框；原公开F不变。全部首次服务位置及索引见records/'+x['id']+'.json',font=font(16),fill='#34445a')
  # Local 7x7 existing cells, drawn directly from stored coordinates.
  zx=1030;zy=155;zs=64
  def zoom(p):return zx+(p[0]-ob[0]+3.5)*zs,zy+(3.5-(p[1]-ob[1]))*zs
  d.text((1000,115),'阻断位置放大（原H的已采目标）',font=font(22),fill='#17263c')
  for dx in range(-3,4):
   for dy in range(-3,4):
    p=(ob[0]+dx,ob[1]+dy)
    if p not in F:continue
    a=zoom((p[0]-.5,p[1]+.5));b=zoom((p[0]+.5,p[1]-.5));d.rectangle((*a,*b),fill='#e9eef4',outline='#c5d0dd',width=1)
    if p in hh or p in ps(n['targets']):
     px,py=zoom(p);d.ellipse((px-4,py-4,px+4,py+4),fill='#8c929c' if p in hh else '#286ab3')
  # Crop line layer to this inset; this is rendering only, no legality query.
  layer=Image.new('RGBA',im.size,(0,0,0,0));ld=ImageDraw.Draw(layer)
  for edge in r['edges']:
   ld.line([zoom(edge['a']),zoom(edge['b'])],fill=(25,126,93,255) if edge['phase']=='coverage_at_least_2_pending' else (140,148,160,255),width=3)
  crop=layer.crop((zx,zy,zx+7*zs,zy+7*zs));im.paste(crop,(zx,zy),crop);d=ImageDraw.Draw(im)
  a=zoom((ob[0]-.5,ob[1]+.5));b=zoom((ob[0]+.5,ob[1]-.5));d.rectangle((*a,*b),fill='#f37945',outline='#bc4025',width=3)
  d.text((1000,635),'障碍 '+str(x['obstacle'])+'；前缀见证索引 '+str(x['H_witness_prefix_index']),font=font(20),fill='#17263c');d.text((1000,675),f"旧边 {x['first_invalid_edge']}/{x['other_invalid_edges']}，仍有 {x['pending_at_start']} 个未完成",font=font(20),fill='#17263c');d.text((1000,715),'末次服务顶点 '+str(last)+'；并未进入返航阶段',font=font(20),fill='#17263c');d.text((1000,755),'全部剩余任务和基地可达；本轮不生成新路线',font=font(19),fill='#17263c')
  # Pending count at edge start and all first-service locations as a time index.
  left=90;right=1600;top=920;bottom=1120;maxu=r['summary']['remaining_tasks'];num=max(1,len(suffix)-1)
  d.text((35,890),'旧后缀行进索引：未完成目标数（边起点已完成的首次服务已扣除）',font=font(20),fill='#17263c')
  def tp(i,p):return left+(right-left)*i/num,bottom-(bottom-top)*p/maxu
  d.line([(left,top),(left,bottom),(right,bottom)],fill='#495e76',width=2);d.line([tp(e['edge'],e['pending_at_start']) for e in r['edges']],fill='#2469ac',width=3)
  for f in first:
   xx,_=tp(f['vertex_index'],0);d.line([(xx,bottom+4),(xx,bottom+12)],fill='#749fc6',width=1)
  for i,color,label in [(x['first_invalid_edge'],'#c84327','阻断边'),(last,'#687888','末次服务')]:
   xx,_=tp(i,0);d.line([(xx,top),(xx,bottom)],fill=color,width=2);d.text((xx+4,top-22),label+' '+str(i),font=font(17),fill=color)
  d.text((left-45,top-10),str(maxu),font=font(17),fill='#17263c');d.text((left-30,bottom-10),'0',font=font(17),fill='#17263c');d.text((left,bottom+20),'0',font=font(17),fill='#17263c');d.text((right-25,bottom+20),str(num),font=font(17),fill='#17263c');d.text((35,1180),'仅图示已保存旧后缀、首次格心服务与选例证据；算法/R修复/候选覆盖路线/直达/性能批均0。',font=font(19),fill='#17263c')
  im.save(H/'figures'/(x['id']+'.png'))
 dump(H/'review_packet.json',{'status':'selection_only_pending_seal','source_labels_considered':54,'detailed_suffixes':44,'same_selected_base_labels_skipped_not_negatives':10,'physical_cuts_detailed':16,'distinct_qualified_bases':2,'qualified_shape_only':'Z','selected':summary['selected'],'compare_previous_return_case':'old block[0,1] at suffix74+ / last service after; new candidate edges61/30 before last205/78 with141/46 pending','snapshot_contract_v02_required':True,'original_E_draft_retained':True,'core_R_post_performance_calls':0,'no_108_batch_started':True,'stop_for_owner_review':True})
 print(json.dumps({'qualified':2,'shape':'Z only','labels':54,'detailed':44,'duplicate_skips':10,'figures':2,'new_algorithm_geometry_BFS_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
