"""Reports from saved outcomes only. No solver/post calls and no parameter changes."""
from region_common import *
from collections import Counter
from fractions import Fraction
from html import escape
def svg(slot,hist,row):
 c=hist['input'];F=ps(c['free']);P=ps(c['published_targets']);scale=21;pad=30;maxx=max(p[0] for p in F);maxy=max(p[1] for p in F)
 def xy(p):return (pad+p[0]*scale,pad+(maxy-p[1])*scale)
 colors={'C0':'#6a6a6a','S':'#b655ad','R':'#e69d30','T':'#42a3b8'}
 out=[f'<svg xmlns="http://www.w3.org/2000/svg" width="780" height="590" viewBox="0 0 780 590"><rect width="780" height="590" fill="white"/>',f'<text x="20" y="20" font-size="16">{slot["id"]}: saved history / {escape(row.get("status","not qualified"))}</text>']
 for x in range(maxx+1):
  for y in range(maxy+1):
   if (x,y) not in F:
    a,z=xy((x,y));out.append(f'<rect x="{a-10}" y="{z-10}" width="20" height="20" fill="#333"/>')
 for label,points in slot['labels'].items():
  for p in points:
   a,z=xy(p);out.append(f'<rect x="{a-5}" y="{z-5}" width="10" height="10" fill="{colors[label]}"/>')
 def line(path,color,width,opacity):
  if len(path)>1:out.append('<polyline fill="none" stroke="'+color+'" stroke-width="'+str(width)+'" opacity="'+str(opacity)+'" points="'+' '.join(f'{xy(p)[0]},{xy(p)[1]}' for p in path)+'"/>')
 line(hist['native']['raw']['route'],'#999',1,.7);line(hist['post']['vertices'],'#1768bf',2,.7)
 if row.get('cut') is not None:line(hist['post']['vertices'][:row['cut']+1],'#16954d',4,.85)
 a,z=xy(slot['obstacle']);out.append(f'<rect x="{a-9}" y="{z-9}" width="18" height="18" fill="none" stroke="red" stroke-width="3"/><text x="{a+9}" y="{z-9}" font-size="12" fill="red">b</text>')
 a,z=xy(c['base']);out.append(f'<circle cx="{a}" cy="{z}" r="7" fill="#111"/>')
 out.append('<text x="20" y="545" font-size="13">gray=native; blue=actual post; green=executed prefix; red=fixed new cell</text><text x="20" y="568" font-size="13">C0 gray / S purple / R orange / T cyan. No rule response shown.</text></svg>')
 (H/'figures'/(slot['id']+'.svg')).write_text('\n'.join(out),encoding='utf-8')
def project(raw):
 r=canonical(raw);r={k:v for k,v in r.items() if k not in ('version','method','rule','geometry_counts')}
 r['trace']=[{k:v for k,v in e.items() if k not in ('phase','Q','allowed','original_options')} for e in r['trace']];return r
def make_reports():
 plan=read(H/'plan.json');status=read(H/'run_status.json');registry=read(H/'state_registry.json') if (H/'state_registry.json').exists() else [];by={r['id']:r for r in registry};ledger=[json.loads(s) for s in (H/'entry_log.jsonl').read_text(encoding='utf-8').splitlines()] if (H/'entry_log.jsonl').exists() else [];actual=Counter((r['phase'],r['kind']) for r in ledger if r['event']=='started');calls={'core':sum(v for (p,k),v in actual.items() if k=='core'),'post':sum(v for (p,k),v in actual.items() if k=='post'),'by_phase':{p:{k:actual[p,k] for k in ('core','post')} for p in ('history','equivalence','formal')}}
 allmetrics=[];missing=[]
 for job in plan['jobs']:
  p=H/'outputs'/(job['id']+'.json')
  if not p.exists():missing.append(dict(id=job['id'],phase=job['phase'],reason=status['status']));continue
  r=read(p);allmetrics.append(dict(id=job['id'],job=job,status=r['status'],passed=r['passed'],eligible=r['eligible'],timing=r.get('timing'),parent=read(H/'logs'/(job['id']+'.json')),views={k:v['metrics'] for k,v in r.get('views',{}).items()},rule=r.get('native',{}).get('raw',{}).get('rule'),decision_audit_passed=r.get('decision_audit',{}).get('passed'),independent_passed=r.get('independent',{}).get('passed'),query_counts={k:v.get('counts') for k,v in r.get('views',{}).items()}))
 for slot in plan['slots']:
  p=H/'outputs'/('history__'+slot['id']+'.json')
  if p.exists() and read(p).get('post'):svg(slot,read(p),by.get(slot['id'],{}))
 pairs=[]
 # Saved radical algebra only, no geometry/planner entry.
 from region_center_v01_20261023.exact import Expr,certificate
 for slot in plan['slots']:
  files=[H/'outputs'/('formal__'+slot['id']+'__'+arm+'.json') for arm in ('ORIGINAL','ON')]
  if not all(p.exists() for p in files):pairs.append(dict(id=slot['id'],status='not_run',qualification=by.get(slot['id'],{}).get('status','not_done'),mechanism_claim_1=None,mechanism_claim_2=None,mechanism_claim_3=None));continue
  a,z=map(read,files)
  if not all(r['passed'] and r['eligible'] for r in (a,z)):pairs.append(dict(id=slot['id'],status='incomplete_or_late'));continue
  rule=z['native']['raw']['rule'];active=bool(rule['check'] and rule['check']['activated']);S=rule['S'];label=ps(slot['labels'].get(S,[])) if S else set();release=ps(rule['release_pending'] or [])
  raw_new=[e for e in z['views']['A']['events'] if e['new']];post_new=[e for e in z['views']['B']['events'] if e['new']];d=Expr.load(z['views']['B']['metrics']['length_certificate']['exact'])-Expr.load(a['views']['B']['metrics']['length_certificate']['exact'])
  inactive_equal=project(a['native']['raw'])==project(z['native']['raw']) and a['post']['vertices']==z['post']['vertices'] and a['views']['B']['metrics']==z['views']['B']['metrics'] if not active else None
  pairs.append(dict(id=slot['id'],status='paired',activated=active,reason=rule['check']['reason'] if rule['check'] else 'no_recovery',post_delta_certificate=certificate(d),post_delta_sign=d.sign(),post_delta=z['views']['B']['metrics']['length']-a['views']['B']['metrics']['length'],native_delta=len(z['native']['raw']['route'])-len(a['native']['raw']['route']),inactive_equivalent=inactive_equal,mechanism_claim_1=z['decision_audit']['passed'] if active else None,mechanism_claim_2=bool(release) and bool(raw_new) and tuple(raw_new[-1]['cell']) in label if active else None,mechanism_claim_3=bool(post_new) and tuple(post_new[-1]['cell']) in label if active else None,S_tasks_retained_to_release=len(release) if active else None))
 # A missing pair is never silently assigned zero.
 group={}
 for g in (f'G{i}' for i in range(1,7)):
  pp=[p for p in pairs if p['id'].startswith(g) and p['status']=='paired'];value=None;cert=None
  if len(pp)==2:
   e=Expr()
   for p in pp:e=e+Expr.load(p['post_delta_certificate']['exact'])
   e=Expr({r:c/Fraction(2) for r,c in e.terms.items()});cert=certificate(e);lo,hi=e.interval();value=float((lo+hi)/2)
  group[g]=dict(pair_count=len(pp),mean_post_delta=value,certificate=cert)
 complete=all(p['status']=='paired' for p in pairs);eligible=False;reason='incomplete matrix / protocol stop'
 if complete:
  total=Expr()
  for g in group.values():total=total+Expr.load(g['certificate']['exact'])
  eligible=all(p['post_delta_sign']<=0 and p.get('inactive_equivalent') is not False for p in pairs) and len({p['id'][:2] for p in pairs if p['post_delta_sign']<0 and p['mechanism_claim_2'] and p['mechanism_claim_3']})>=2 and total.sign()<0
  reason='all registered management gates require independent non-D4 base check as well' if eligible else 'fixed management criteria not met'
  # Conservative: do not certify independence merely from distinct G names.
  if eligible:eligible=False;reason='quality gates met but independent non-D4 proof requires owner audit; not automatically approved'
 dump(H/'all_metrics.json',allmetrics);dump(H/'missing_jobs.json',missing);dump(H/'formal_pairs_and_mechanism.json',pairs);dump(H/'actual_call_summary.json',calls);dump(H/'group_results.json',group);dump(H/'continuation_gate.json',dict(passed=eligible,reason=reason,formal_pairs=sum(p['status']=='paired' for p in pairs),missing_not_zero=True,auto_next_version=False))
 table=['|槽|历史|资格|未通过项|','|---|---|---|---|']
 for s in plan['slots']:
  q=by.get(s['id'],{});hp=H/'outputs'/('history__'+s['id']+'.json');hs=read(hp)['status'] if hp.exists() else '未运行';table.append(f'|{s["id"]}|{hs}|{q.get("status","未检查")}|{", ".join(q.get("failed_checks",[]))}|')
 (H/'01_十二槽历史与资格.md').write_text('# 固定十二槽历史与资格\n\n'+'\n'.join(table)+'\n\n精确坐标在plan.json；所有障碍只检查登记的一个格，固定最早切点，不替换。G1/G2/G6配对物理输入除名称相同，但本次各自支付历史费用；G3/G4变化包含真实历史，不能称单变量因果。首次恢复条件未用于资格挑选。\n',encoding='utf-8')
 headline=f'按固定停止条件结束：{status["status"]}。实际核心{calls["core"]}次、公共post{calls["post"]}次；关闭等价与正式阶段分别{calls["by_phase"]["equivalence"]["core"]}、{calls["by_phase"]["formal"]["core"]}次核心。'
 (H/'00_通俗结果与结论边界.md').write_text('# 本轮结果与边界\n\n'+headline+'\n\n'+('指定等价门槛槽不齐：'+', '.join(status.get('failed_gate_slots',[]))+'。按稿未启动关闭等价或正式比较。' if status['status']=='stopped_fixed_gate_slot_ineligible' else '以run_status、实际调用账和全部失败记录为准。')+'\n\n独立候选和16项固定纯桩已保存。纯桩只验证所列合成条件与包装约束；真实关闭等价、规则启用后的效果与速度仍以实际运行记录为界，不能用纯桩或文档哈希代替。未运行的三项机制（OTHER不主动选S、原生确实留后、post仍以S收尾）记未知，不记成功或零收益。\n\n资格不足说明此次固定构造没有提供完整可比证据，不能据此判规则有效或无效，也不能补图、换障碍或改切点。49/50代理定义、代表格近似、顺带采集可能提前耗尽S等限制保持。未确认主算法或创新；旧LAST已有分阶段留后重合，旧FIRST已有完整分支试走。没有新增无事件控制，不能主张事件专属收益。\n\n[十二槽资格](01_十二槽历史与资格.md) · [审核入口](review_packet.md) · [固定协议](执行稿.md)\n',encoding='utf-8')
 (H/'02_实现差异与审核范围.md').write_text('# 实现与证据范围\n\nregion_native为独立候选；frozen_reference仅改路径定位一行，算法主体与冻结源一致。OFF直接返回原solve结果，不创建Priority。ON完整Q奖励后过滤局部和恢复目标，首次原恢复检查一次，固定S、逐边信用与阶段转换，既定连接不重选；新增规则B/X/rS距离行最多3，原native查询另计。原模块和旧审核/数据未改；公共post整包逐字复制为独立命名空间，public_post_bindings绑定。\n\nregion_audit不用Priority/原reward/原路径库，另行BFS、算奖励和阶段，检查允许集合与完整信用；纯桩手造ON轨迹和篡改拒绝只是局部覆盖。真实每个完成入口还独立审核中心信用、post合法性及原生逐决策。只读verify重算保存路线的根式距离与整数转弯，核保存审核通过、封存/根链；不重跑规划、post、BFS或资格搜索，也不等同全输入形式证明。\n\n计时：详细profile关闭，主内含输入检查、规则/核心、raw全信用指标、公共post、post全信用指标、编码和入口账fsync；冷启动、来源hash、完整文件落盘、独立审核在外，parent/worker wall另列。规则准备/原生/公共post及主时间均单次，无稳定速度结论。不可观测节点展开为null，原版没有独立公开计数时不填0。\n\n历史信用由独立中心区相交算法重建，最早合格post源端点给当前位置/真实单位来向；未把基地伪造为任务。资格只检查一个已登记障碍是否穿过旧实际post后缀内部，双方法核可达性，任务/H/暂缓完整保留。\n',encoding='utf-8')
 (H/'review_packet.md').write_text('# 交负责人审核\n\n先读[通俗结果](00_通俗结果与结论边界.md)、[十二槽资格](01_十二槽历史与资格.md)、[实现与边界](02_实现差异与审核范围.md)。原始plan、源码diff、pure_cases/prechecks、实际entry_log、run_status、state_registry、qualification/history、outputs与logs均留存；all_metrics不混入未运行响应，missing_jobs单列。figures为保存历史机制图：灰原生、蓝旧post、绿实际前缀、红唯一新增格，不表示规则生效。formal_pairs_and_mechanism把未运行留为null。\n\n只读命令：`运行环境\\python\\python.exe -B -X utf8 障碍后片区两阶段规则有限验证_v0.1_20261023\\verify.py`。final_receipt和verify_receipt绑定当前根追加链，旧final原样保留。到此停止，不自动修复真实阶段实现、不补资格槽、不启动第二版。\n',encoding='utf-8')
 return headline
def archive():
 assert not (H/'final_receipt.json').exists();guard();headline=make_reports();before=(H/'root_before.md').read_bytes();assert (ROOT/'当前进度与下一步.md').read_bytes()==before
 text='# 最新进度：片区两阶段固定有限验证封存待审（2026-10-23）\n\n'+headline+'\n\n独立PPCPP_REGION_TAIL_V1、固定12槽坐标/标签/C0/唯一障碍/切点/seed20261023/44+44调用计划、16项纯桩、独立逐决策与信用审核、历史及资格/缺槽、全部指标/时间/查询账/图和只读verify封存。具体纯桩是否完成、修复次数、真实等价/正式是否运行以包内prechecks/run_status/entry_log为准，不能将纯桩或hash通过改称真实规则有效。\n\n目录：障碍后片区两阶段规则有限验证_v0.1_20261023；入口00_通俗结果与结论边界.md、01_十二槽历史与资格.md、02_实现差异与审核范围.md、review_packet.md。不改旧草案/源码/输出/final；根只前缀追加，预算不挪用，未运行机制记未知，不自动第二版，无主算法/创新确认。\n\n---\n\n'
 after=text.encode('utf-8')+before;(ROOT/'当前进度与下一步.md').write_bytes(after);(H/'root_after.md').write_bytes(after)
 from verify import verify
 pre=verify(sealed=False);dump(H/'preseal_verify.json',pre)
 files={str(p.relative_to(H)):sha(p) for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ('final_receipt.json','verify_receipt.json')}
 dump(H/'final_receipt.json',dict(status='sealed_stopped_for_owner_review',files=files,file_count=len(files),root_sha256=sha(ROOT/'当前进度与下一步.md'),root_before_sha256=sha(H/'root_before.md'),actual_calls=read(H/'actual_call_summary.json'),run_status=read(H/'run_status.json')['status'],utc=time.time(),auto_next_version=False))
 result=verify();result['final_receipt_sha256']=sha(H/'final_receipt.json');dump(H/'verify_receipt.json',result);print(headline,flush=True)
if __name__=='__main__':archive()
