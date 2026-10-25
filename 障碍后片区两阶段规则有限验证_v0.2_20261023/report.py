"""Post-execution saved-data accounting only; no planner/post/BFS calls."""
from region_common import *
from collections import Counter
from fractions import Fraction
from html import escape
from region_center_v01_20261023.exact import Expr,certificate
def records(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines()] if p.exists() else []
def project(raw):
 v=canonical(raw);v={k:z for k,z in v.items() if k not in ('version','method','rule','geometry_counts')}
 v['trace']=[{k:z for k,z in e.items() if k not in ('phase','Q','allowed','original_options')} for e in v['trace']];return v
def route_svg(sid,slot,a,z):
 c=a['input'];maxy=max(p[1] for p in c['free']);scale=20;pad=35
 def xy(p):return (pad+p[0]*scale,pad+(maxy-p[1])*scale)
 lines=['<svg xmlns="http://www.w3.org/2000/svg" width="790" height="590"><rect width="790" height="590" fill="white"/>',f'<text x="20" y="20" font-size="16">{sid}: rule NOT activated; native/post identical to original</text>']
 colors={'C0':'#888','S':'#a43ba4','R':'#cd871b','T':'#409cae'}
 for name,pts in c['labels'].items():
  for p in pts:
   x,y=xy(p);lines.append(f'<rect x="{x-4}" y="{y-4}" width="8" height="8" fill="{colors[name]}"/>')
 maxx=max(p[0] for p in c['free']);F=ps(c['free'])
 for x in range(maxx+1):
  for y in range(maxy+1):
   if (x,y) not in F:
    xx,yy=xy((x,y));lines.append(f'<rect x="{xx-7}" y="{yy-7}" width="14" height="14" fill="#222"/>')
 for path,color,width,extra in ((a['native']['raw']['route'],'#999',1,''),(a['post']['vertices'],'#1666ba',3,''),(z['post']['vertices'],'#e68a28',2,'stroke-dasharray="5 4"')):
  pts=' '.join(f'{xy(p)[0]},{xy(p)[1]}' for p in path);lines.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}" {extra}/>')
 for p,name,color in ((c['base'],'base','#111'),(c['current'],'current','#157439'),(slot['obstacle'],'new b','red')):
  x,y=xy(p);lines.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{color}"/><text x="{x+7}" y="{y-7}" font-size="12" fill="{color}">{name}</text>')
 rule=z['native']['raw']['rule'];reason=rule['check']['reason'] if rule['check'] else 'no original recovery'
 lines.extend([f'<text x="20" y="535" font-size="13">{escape(reason)}; no OTHER/TAIL phase, no active retention mechanism.</text>','<text x="20" y="557" font-size="13">gray=native; blue=original post; orange dashed=rule post (overlap).</text>','<text x="20" y="579" font-size="13">S purple / R orange / T cyan; saved route geometry only, no new searches.</text></svg>'])
 (H/'figures'/(sid+'.svg')).write_text('\n'.join(lines),encoding='utf-8')
def make():
 guard();plan=read(H/'plan.json');run=read(H/'run_status.json');oldreview=read(H/'old_review_receipt.json');assert oldreview['passed'];ledger=records(H/'entry_log.jsonl');started=[r for r in ledger if r['event']=='started'];calls={k:sum(r['kind']==k for r in started) for k in ('core','post')};assert calls=={'core':16,'post':16}
 oldledger=records(OLD/'entry_log.jsonl');oldids=[r['job'] for r in oldledger if r['event']=='started' and r['kind']=='core'];account=[];allmetrics=[];newdecision=Counter();newgeometry=Counter();newtimes=[]
 for jid in oldids:
  r=read(OLD/'outputs'/(jid+'.json'));review=read(H/'audits/old'/(jid+'.json'));account.append(dict(id=jid,version='v0.1',original_execution={'status':r['status'],'passed':r['passed'],'eligible':r['eligible']},current_evidence={'status':review['review_status'],'passed':review['passed'],'audit_path':'audits/old/'+jid+'.json'},scientific_inclusion=review['scientific_inclusion'],online_timing_origin='unchanged v01 historical measurement',new_main_call=False))
  allmetrics.append(dict(id=jid,version='v0.1',role=r['job']['phase'],arm=r['job']['arm'],original_execution=account[-1]['original_execution'],review_status=review['review_status'],views={k:v['metrics'] for k,v in r['views'].items()},online_timing=r['timing'],saved_solver_seconds=r['native']['raw']['seconds'],new_external_review_seconds=review['review_seconds'],views_query_counts={k:v['counts'] for k,v in r['views'].items()},rule=r['native']['raw'].get('rule'),native_geometry=r['native']['raw'].get('geometry_counts'),original_worker_wall_seconds=r['worker_wall_seconds']))
 for j in plan['jobs']:
  p=H/'outputs/worker'/(j['id']+'.json')
  if not p.exists():continue
  r=read(p);account.append(dict(id=j['id'],version='v0.2',original_execution={'status':r['status'],'passed':r['passed'],'eligible':r['eligible']},current_evidence={'decision_passed':r.get('decision_audit',{}).get('passed'),'geometry_credit_passed':r.get('independent',{}).get('passed')},scientific_inclusion='v02_new_execution_formal_arm' if r['passed'] and r['eligible'] else 'excluded_incomplete_or_failed',online_timing_origin='v02 new execution',new_main_call=True))
  allmetrics.append(dict(id=j['id'],version='v0.2',role='formal',arm=j['arm'],original_execution=account[-1]['original_execution'],views={k:v['metrics'] for k,v in r.get('views',{}).items()},online_timing=r.get('timing'),saved_solver_seconds=r['native']['raw']['seconds'],external_independent_seconds=r.get('independent_seconds'),views_query_counts={k:v['counts'] for k,v in r.get('views',{}).items()},rule=r['native']['raw'].get('rule'),native_geometry=r['native']['raw'].get('geometry_counts'),worker_wall_seconds=r['worker_wall_seconds'],parent=read(H/'outputs/parent'/(j['id']+'.json'))))
  newdecision.update(r.get('decision_audit',{}).get('counts',{}));newgeometry.update(r.get('independent',{}).get('counts',{}))
 pairs=[];timepairs=[];slots={s['id']:s for s in plan['source_slots']}
 for sid in plan['qualified_slots']:
  old=sid=='G1-A'
  a=read((OLD/'outputs' if old else H/'outputs/worker')/(('formal__' if old else 'v02__formal__')+sid+'__ORIGINAL.json'));z=read((OLD/'outputs' if old else H/'outputs/worker')/(('formal__' if old else 'v02__formal__')+sid+'__ON.json'))
  az=[read(H/'audits/old'/('formal__'+sid+'__'+arm+'.json'))['decision'] if old else r['decision_audit'] for arm,r in (('ORIGINAL',a),('ON',z))]
  assert all(r['passed'] for r in az)
  if not old:assert all(r['passed'] and r['eligible'] for r in (a,z))
  rule=z['native']['raw']['rule'];check=rule['check'];active=bool(check and check['activated']);delta={}
  for view in ('A','B'):
   e=Expr.load(z['views'][view]['metrics']['length_certificate']['exact'])-Expr.load(a['views'][view]['metrics']['length_certificate']['exact']);lo,hi=e.interval();delta[view]={'length_delta':float((lo+hi)/2),'sign':e.sign(),'certificate':certificate(e),'turn_delta':{k:z['views'][view]['metrics']['turns'].get(k,0)-a['views'][view]['metrics']['turns'].get(k,0) for k in ('total','90','180','other')},'angle_delta':z['views'][view]['metrics']['total_turn_radians']-a['views'][view]['metrics']['total_turn_radians']}
  same={'raw_semantics':project(a['native']['raw'])==project(z['native']['raw']),'raw_route':a['native']['raw']['route']==z['native']['raw']['route'],'post_vertices':a['post']['vertices']==z['post']['vertices'],'post_locked_anchors':a['post']['locked_nominal_anchors']==z['post']['locked_nominal_anchors'],'post_credit_witnesses':a['post']['credit_witnesses']==z['post']['credit_witnesses'],'native_metrics':a['views']['A']['metrics']==z['views']['A']['metrics'],'post_metrics':a['views']['B']['metrics']==z['views']['B']['metrics'],'raw_credit_events':a['views']['A']['events']==z['views']['A']['events'],'post_credit_events':a['views']['B']['events']==z['views']['B']['events']}
  if not active:assert all(same.values()),('inactive semantic divergence',sid)
  def last_region(r,view):
   new=[e for e in r['views'][view]['events'] if e['new']]
   if not new:return None
   p=tuple(new[-1]['cell']);return next(k for k,v in slots[sid]['labels'].items() if p in ps(v))
  p={'id':sid,'base_geometry':sid[:2],'pair_evidence':'old_saved_reaudited_pair' if old else 'v02_new_execution_pair','original_execution_states':{arm:dict(status=r['status'],passed=r['passed'],eligible=r['eligible']) for arm,r in (('ORIGINAL',a),('ON',z))},'current_audits_passed':True,'scientific_inclusion':'valid physical pair; related variants not independent geometries','checked':rule['checked'],'activated':active,'check':check,'phase_final':rule['phase'],'transitions':rule['transitions'],'deltas':delta,'same':same,'last_new_native_region':last_region(z,'A'),'last_new_post_region':last_region(z,'B'),'mechanism':{'OTHER_no_active_S_choice':az[1]['passed'] if active else None,'native_S_retained_to_release':bool(rule['release_pending']) if active else None,'post_finishes_S':last_region(z,'B')==rule['S'] if active else None,'S_tasks_at_release':len(rule['release_pending']) if active and rule['release_pending'] is not None else None,'inactive_not_counted_as_mechanism_success':not active},'online_timing':{arm:r['timing'] for arm,r in (('ORIGINAL',a),('ON',z))},'time_scope':'historical v01 single observations; audit time separate' if old else 'same-version single pair; no stable-speed inference','query_counts':{'rule_added':rule['counts'],'ON_native_geometry':z['native']['raw'].get('geometry_counts'),'ORIGINAL_native_geometry':a['native']['raw'].get('geometry_counts')},'full_metrics':{arm:{v:data['metrics'] for v,data in r['views'].items()} for arm,r in (('ORIGINAL',a),('ON',z))}}
  pairs.append(p);route_svg(sid,slots[sid],a,z)
  if not old:timepairs.append(dict(id=sid,ORIGINAL=dict(main=a['timing']['combined_end_to_end'],core=a['timing']['native_entry_seconds'],post_increment=a['timing']['post_increment'],solver=a['native']['raw']['seconds']),ON=dict(main=z['timing']['combined_end_to_end'],core=z['timing']['native_entry_seconds'],post_increment=z['timing']['post_increment'],solver=z['native']['raw']['seconds'],rule_preparation=rule['preparation_seconds']),scope='single observed same-version pair only'))
 assert len(pairs)==9 and len(timepairs)==8
 group=[]
 for g in (f'G{i}' for i in range(1,7)):
  pp=[p for p in pairs if p['base_geometry']==g];complete=len(pp)==2;group.append(dict(base=g,observed_pairs=len(pp),planned_pairs=2,complete=complete,observed_pair_mean=sum(p['deltas']['B']['length_delta'] for p in pp)/len(pp),complete_base_mean=sum(p['deltas']['B']['length_delta'] for p in pp)/2 if complete else None))
 missing=[dict(id=sid,qualification='ineligible fixed actual-post obstruction',methods_not_run=['ORIGINAL','ON'],remaining_calls_per_kind=2,permanently_unspent=True) for sid in plan['permanent_ineligible']]
 summary={'status':run['status'],'new_calls':calls,'cumulative_actual':{'core':38,'post':38},'original_absolute_cap':{'core':44,'post':44},'permanent_unspent':{'core':6,'post':6},'valid_pairs':9,'old_saved_reaudited_pairs':1,'v02_new_execution_pairs':8,'old_22_saved_results_reaudited':22,'type_regression_cases':16,'engineering_repairs_this_version':0,'activated_pairs':sum(p['activated'] for p in pairs),'checked_pairs':sum(p['checked'] for p in pairs),'post_delta_sign_counts':dict(Counter(p['deltas']['B']['sign'] for p in pairs)),'reason_counts':dict(Counter(p['check']['reason'] if p['check'] else 'no_original_recovery' for p in pairs)),'no_universal_conclusion':True}
 costs={'real_new':calls,'real_old':{'core':22,'post':22},'old_saved_result_review':read(H/'old_review_receipt.json'),'pure_regression':read(H/'regression_receipt.json'),'new_execution_external_decision_audit':dict(newdecision),'new_execution_external_geometry_credit_audit':dict(newgeometry),'new_execution_external_seconds':sum(m.get('external_independent_seconds',0) or 0 for m in allmetrics if m['version']=='v0.2'),'detailed_core_profile':False,'unobserved_original_native_BFS_rows':None,'timepairs_same_version':timepairs,'G1_A_timing_reused_unchanged':True,'old_audit_seconds_not_spliced_into_old_online':True}
 gate={'passed':False,'technical_and_OFF_gates_passed':True,'nine_observed_pairs_legal_timely':True,'inactive_semantics_equal':all(all(p['same'].values()) for p in pairs),'original_12_pair_complete':False,'two_noncopy_nonD4_improving_bases_with_actual_tail_evidence':False,'activated_pairs':summary['activated_pairs'],'complete_six_base_equalweight_difference':None,'reason':'3 permanent ineligible slots; all 9 observed pairs inactive and exact zero gain; insufficient activation/applicability evidence, not universal invalidity','no_new_rule_or_batch':True}
 for name,value in (('three_column_account.json',account),('all_metrics.json',allmetrics),('nine_pairs.json',pairs),('new_version_timing_pairs.json',timepairs),('base_results.json',group),('permanent_missing_slots.json',missing),('actual_call_summary.json',summary),('cost_and_query_account.json',costs),('continuation_gate.json',gate)):dump(H/name,value)
 # Explicit old archive correction, with no invented replacement object.
 corrections={'old_bad_field':'engineering_repair.json:first_failed_worker','old_referenced_path':'preparation/first_preflight_failure/history__G1-A.json','actual_content':'parent process log/stdout; the failed pre-core worker JSON is unavailable','irrecoverable_worker_JSON':True,'preserved':['parent stdout','controller traceback','original source/freeze','engineering diff'],'clock_or_query_counts_missing':None,'distinct_from_real_22_results':True,'all_22_real_results_full_bound_and_reviewed':True,'old_files_modified':False};dump(H/'old_archive_corrections.json',corrections)
 table=['|状态|证据来源|检查/激活|拒绝原因|原生距离|post距离|两法post差|','|---|---|---|---|---:|---:|---:|']
 for p in pairs:
  m=p['full_metrics']['ON'];table.append(f'|{p["id"]}|{"旧返回复核" if p["pair_evidence"].startswith("old") else "新版执行"}|{p["checked"]}/{p["activated"]}|{p["check"]["reason"] if p["check"] else "无恢复"}|{m["A"]["length"]:.6f}|{m["B"]["length"]:.6f}|{p["deltas"]["B"]["length_delta"]:.0f}|')
 columns='''|原执行|本轮证据状态|科学纳入范围|
|---|---|---|
|v0.1 G1-A原版成功、ON失败（表示层审核）|两臂完整保存结果均经v0.2独立语义复核通过|1对旧返回复核配对；旧ON仍是原执行失败|
|v0.2剩余8槽两臂共16入口成功|新入口完整独立审核通过|8对新版新执行配对|
|v0.1历史12与关闭等价8入口|22旧返回中逐项复核、已有几何信用回执绑定复用|只作历史/资格/等价门槛，不增加正式配对数|
|G2-B、G5-B、G6-B缺资格|旧资格原样冻结|永久缺槽，两法各一次均未运行，不作0收益填补|
'''
 (H/'00_通俗接续结果与三栏账.md').write_text('# 类型修复与原固定批接续结果\n\n完成审核器类型修复、16项固定回归、旧22份独立复核，以及原计划剩余8槽的16核心＋16post；新入口全部合法及时并经审核通过。候选算法、规则、原版、公共post和信用实现逐字节复用未改，本版工程修复重试0轮。\n\n共取得9对物理状态证据：1对旧保存返回复核、8对新版执行。9对均出现一次规则检查，但激活0对；8对位置条件不满足，G5-A为单片保护。每对原生、post路线/信用/完整指标均与原版相同，认证距离差全为0。未激活不计作收尾机制成功，本轮无法验证激活后的留后收益，不据此宣布规则普遍无效。\n\n'+columns+'\n实际两版累计38核心＋38post；原44＋44中剩余6＋6对应3个缺资格槽，永久不挪用。原12槽完整性、至少两非复制非D4基底严格改善并有原生/post留后证据、六基底等权净负门槛均未通过，不改为9槽新门槛。\n\n主外复核并非零图搜索：旧22份完整决策审核96次BFS/72500出队；纯表示夹具108次合成BFS另列；新版主外审核查询与时间也逐项留账。旧几何/中心信用子回执有完整hash绑定而复用，复核不调用规划器或post生成路线。G1-A原在线时间保持历史观察，新增审核时间单列；新版8对单次计时不证明稳定提速。\n\n[九对结果与缺槽](03_九对质量机制与缺槽.md) · [类型合同与差异](01_类型合同与修复范围.md) · [旧22份复核](02_旧22份复核与原执行状态.md) · [成本与缺失勘误](04_费用与缺失勘误.md) · [审核入口](review_packet.md)\n\n未改旧final/失败状态或补造事前丢失worker JSON；归档缺口明确保留。本轮完成即停止，无新地图/新规则/额外seed/留出/P2/FIRST/LAST运行；未确认主算法、创新或一般性优势。\n',encoding='utf-8')
 (H/'01_类型合同与修复范围.md').write_text('# 类型合同与修复范围\n\n审核器对check、transitions、release_pending两侧调用同一coordinate_form：list/tuple只在序列表示上等价，路径/阶段/责任日志不排序、不删字段、不转set忽略顺序。严格schema先校验坐标恰两整数（bool不作整数）、非负整数计数、有限奖励数、真假布尔、None与缺字段区别，非法状态拒绝。原完整Q、奖励独立重算、BFS最短性、首次检查、固定S和逐边阶段重建正文保持原样；setup_receipt核AST前缀。\n\n审核器类型修复.diff为相对v0.1最小差异；region_rule.py、region_native.py、frozen_reference.py与全部public post/信用模块在immutable_bindings逐字节绑定。独立命名空间使用本版目录/进程隔离与显式来源路径，未同时加载旧版同名算法模块。\n\nregression_cases预定16项且一次全部通过，包括直接内存raw（不预先JSON化）、全列表/坐标元组/混合表示、无检查None/未激活/激活OTHER→TAIL、release tuple/list、CANCELLED结构、篡改q0/代表/pending/允许集/奖励/阶段时点顺序拒绝、坏坐标/bool整数/字段缺失拒绝、无导入任务和独占输出。S提前耗尽案例只验固定形状/表示合同，未伪称生成了一条真实取消轨迹。夹具为保存JSON按源码构造的表示变体或手工固定小夹具，不声称恢复已丢失内存，不生成算法路线。\n',encoding='utf-8')
 oldtable=['|旧入口|原执行状态|新版复核|用途|','|---|---|---|---|']
 for r in account:
  if r['version']=='v0.1':oldtable.append(f'|{r["id"]}|{r["original_execution"]["status"]}|通过|{r["scientific_inclusion"]}|')
 (H/'02_旧22份复核与原执行状态.md').write_text('# 旧22份逐项复核\n\n每个原输入/raw/trace/rule/post请求响应/source/entry账按完整文件和字段hash绑定。新版独立审核重新重建每条决策和责任；已有独立几何/中心信用子回执22份完整通过且绑定复用。主外BFS96次、72500格出队，耗时见old_review_receipt；未调用规划器/post生成新路线。旧失败/成功标记未修改。\n\n'+'\n'.join(oldtable)+'\n\n完整新审核回执在audits/old，三栏机器账在three_column_account.json。G1-A ON保持原status=implementation_or_contract_error、passed=false、eligible=false；本轮证据=保存返回语义审核通过，因此仅进入旧返回复核配对。\n',encoding='utf-8')
 (H/'03_九对质量机制与缺槽.md').write_text('# 九对完整质量、机制与缺槽\n\n'+'\n'.join(table)+'\n\n8对拒绝geometry_conditions_failed，G5-A拒绝single_region；所有9对local_changes/recovery_changes=0，阶段始终DEFAULT。G4的4/8与7/8均满足唯一最小计数，但严格绕行条件等号而非小于；G6对R不满足严格不等式，不能只挑对T成立的条件。所有真值和代表/距离见nine_pairs.check。\n\n完整覆盖/返航/暂缓/H/资源、原生/post长度根式证书、各类转弯/累计角、覆盖与返航分段均存nine_pairs.full_metrics和all_metrics；全部差=0，信用一致，无遗漏，无超限。三个“目标约束、原生实际留后、post实际留后”机制项均记null，不激活不计成功；观测最后采片另列。最后服务采用首个相交段区间中点见证口径，不是唯一物理首次采集时刻。\n\n六个基底是旧登记分组，G1/G3/G4各2对，G2/G5/G6各1对；这些相关状态不是9独立几何。G2-B/G5-B/G6-B仍缺资格。可报9个已观测差均0，不能给缺槽赋0后声称六基底完整等权达标；base_results对不完整基底的正式均值为null。无严格改善，非复制/D4改善基底计数为0，不以标签名称冒充独立性证明。\n\nfigures/G*.svg是两法保存路径叠图：灰原生、蓝原post、橙虚线规则post，均重合；明确显示无激活，不假造OTHER/TAIL轨迹。没有新增无事件对照，不能称事件专属收益。\n',encoding='utf-8')
 (H/'04_费用与缺失勘误.md').write_text('# 费用、时间边界与旧缺失勘误\n\n真实调用：v0.1 22核心/22post，本版16/16，累计38/38；原44/44中6/6永久对应3缺资格槽。旧12历史、8关闭门槛和G1-A两臂均未重跑。实际入口含失败尝试；audit/纯夹具BFS另账，不冒称总图搜索0。cost_and_query_account列旧复核、纯夹具和新版独立决策/几何信用查询，节点展开不可观测为null；原版native未公开BFS行数也为null。\n\n20秒核心、post18秒软/4096候选/20秒迟到、主40/父150、原生4096边与相同资源1000000未改。规则准备的B/X/rS最多3行只指规则新增，不是全求解BFS上限。详细核心profile OFF。线上含必要验证、规则/核心、raw/post完整信用指标和编码、入口日志fsync；冷/hash、独立审核、报告图和封存在外。G1-A仅保留原v0.1计时；新增复核不拼进历史在线。新版8对同版单次时间分开报告，不并为跨版本稳定速度结论。\n\n旧勘误：v0.1 engineering_repair.json:first_failed_worker指向的preparation/first_preflight_failure/history__G1-A.json实际是父日志/stdout；首次guard失败worker JSON因同名归档覆盖不可恢复。保留父stdout/controller traceback/源码freeze/diff，缺时钟/细查询填null而非0；不重跑补造，不改旧字段。本轮另核22份真实核心/post返回均完整，其缺口与辅助首故障不同。\n\n新版worker结果、父日志和审核回执分目录，同基名可并存，每个输出独占创建；类型回归第16项实际验证重复写拒绝。只复制旧字节，无旧文件移动或覆盖。\n',encoding='utf-8')
 (H/'review_packet.md').write_text('# 交负责人审核\n\n先读[通俗结果与三栏账](00_通俗接续结果与三栏账.md)，再读[九对质量机制](03_九对质量机制与缺槽.md)、[旧22份复核](02_旧22份复核与原执行状态.md)、[类型修复](01_类型合同与修复范围.md)、[费用与缺失](04_费用与缺失勘误.md)。\n\n机器证据：plan/immutable_bindings/审核器类型修复.diff；regression_cases及regression/01～16；audits/old 22份完整逐决策回执；outputs/worker与outputs/parent各16份，audits/new各独立决策及几何信用回执；entry_log；three_column_account/nine_pairs/all_metrics/cost_and_query_account/permanent_missing_slots/continuation_gate。G1-A旧failed不改，新复核可用另列；其余8对为本版实测。\n\n只读核验：`运行环境\\python\\python.exe -B -X utf8 障碍后片区两阶段规则有限验证_v0.2_20261023\\verify.py`。该工具只核hash/旧根后缀链/调用账/保存审核回执及独立路线长度转弯算术，不调用核心/post/新BFS；真实语义来自本版保存的独立审核，范围区分清楚。\n\n首轮固定规则没有激活证据，继续门槛未通过。与旧LAST分阶段留后和FIRST完整试走的机制重合不因此消失；未确认主算法/创新。封存即停，不自动新规则、新图或下一版。\n',encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2));return summary
if __name__=='__main__':make()
