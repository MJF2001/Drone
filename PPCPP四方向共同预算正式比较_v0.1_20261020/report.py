"""Postprocessing only; no solver imports."""
import json,statistics,hashlib,csv
from pathlib import Path
H=Path(__file__).resolve().parent
a=json.loads((H/'analysis.json').read_text(encoding='utf8'));rows=a['rows'];S=a['summary'];methods=['PPCPP','ORIENT4','P2_MULTI']
def table(head,rr):return '\n'.join(['|'+'|'.join(head)+'|','|'+'|'.join(['---']*len(head))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rr])
states=[]
for case in sorted({r['case'] for r in rows}):
 d={'case':case}
 for m in methods:
  rr=[r for r in rows if r['case']==case and r['method']==m]
  assert len(rr)==3
  d[m]=statistics.mean(r['metrics']['length'] for r in rr)
  d[m+'_times_ms']=[r['seconds']*1000 for r in rr]
  d[m+'_lengths']=[r['metrics']['length'] for r in rr]
  if m!='P2_MULTI':assert len(set(d[m+'_lengths']))==1
 states.append(d)
with (H/'54状态比较.csv').open('x',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(states[0]));w.writeheader();w.writerows(states)
def pct(xs,p):
 xs=sorted(xs);v=(len(xs)-1)*p;i=int(v);return xs[i]+(xs[min(i+1,len(xs)-1)]-xs[i])*(v-i)
lines=['# 四方向组合与PPCPP/P2共同预算正式开发比较','2026-10-20。固定54已见状态、3种子、20秒共同预算；486次独立进程入口。未用留出，冻结算法未改。',
table(['方法','合法完整调用','及时','54状态均值总步数','90度转弯','入口均值ms','中位ms','P95ms','最大ms'],[[m,S[m]['n'],S[m]['timely'],round(S[m]['totals']['length'],6),round(S[m]['totals']['turns90'],6),round(S[m]['mean_ms'],4),round(S[m]['median_ms'],4),round(pct([r['seconds']*1000 for r in rows if r['method']==m],.95),4),round(S[m]['max_ms'],4)] for m in methods]),
'## 同批及时配对（调用级）',table(['ORIENT4对比','配对数','短','平','长','步数差总和'],[[m,v['n'],v['short'],v['equal'],v['long'],v['delta_sum']] for m,v in a['pairs'].items()]),
'## 状态级（3种子取均值，不挑最好）',table(['ORIENT4对比','短','平','长'],[[m,sum(s['ORIENT4']<s[m] for s in states),sum(s['ORIENT4']==s[m] for s in states),sum(s['ORIENT4']>s[m] for s in states)] for m in ('PPCPP','P2_MULTI')]),
'## 路程与转向分解',table(['指标']+methods,[[k]+[round(S[m]['totals'][k],6) for m in methods] for k in ('fresh_target_steps','historical_target_steps','repeated_new_target_steps','non_target_steps','completion_step','return_tail_steps','turns90','turns180','active_targets','active_covered','published_targets','published_covered','deferred','missing_active')]),
'## 分层',table(['层','状态数']+methods,[[v,len(rr)]+[round(sum(s[m] for s in rr),6) for m in methods] for pos,vals in ((0,['small','medium','large']),(1,['I','L','Z']),(2,['straight','corner','obstacle'])) for v in vals for rr in [[s for s in states if s['case'].split('_')[pos]==v]]]),
'## 结论与边界',
f"完整组合相对原版省{S['PPCPP']['totals']['length']-S['ORIENT4']['totals']['length']:.2f}步，减少{100*(1-S['ORIENT4']['totals']['length']/S['PPCPP']['totals']['length']):.4f}%；相对P2多{100*(S['ORIENT4']['totals']['length']/S['P2_MULTI']['totals']['length']-1):.4f}%。原版→组合的90度转弯增加{S['ORIENT4']['totals']['turns90']-S['PPCPP']['totals']['turns90']:.0f}次。不能以路线收益替代转弯代价，也不构造能耗权重。",
'全部指标与三重复原值在CSV，失败清单在analysis.json。四类移动与采集前/返航是两种分解，不重复相加；公开目标暂缓不是已完成。三种子不是独立地图；仅9基础道路、单一历史来源及54已见状态，无留出泛化、最优性或主算法结论。',
'本批PPCPP沿用之前共同预算入口，ORIENT4沿用已验收组合入口；后者编码四候选/变换信息，额外开销诚实计入，不声称包装结构等价。P2原生软截止保留，及时由外部入口计时判定。',
'复核所有完整路线的两套指标、每个组合的四候选决策/选择、同批原PPCPP与候选0非时间等价。环境事前封存继承并核对，共10080文件；系统DLL与未发现动态依赖限制保留，不宣称全机镜像。',
'真实核心数：PPCPP162＋ORIENT4内部648＋P2 162＝972；正式入口486。没有新门槛求解/精确搜索。旧门槛只读核验已通过。未调算法或重试正式调用。',
'只读核验命令：`./运行环境/python/python.exe -B -X utf8 ./PPCPP四方向共同预算正式比较_v0.1_20261020/experiment.py verify`。该命令重算审核与统计，不调用规划器。',
'本轮固定批完成即停止，不自行加入LAST/减少方向/增设新奖励。']
(H/'正式比较结果.md').write_text('\n\n'.join(lines),encoding='utf8')
manifest={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in H.rglob('*') if p.is_file() and p.name not in ('manifest.json','verify.log')}
(H/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print('REPORT AND MANIFEST',len(manifest))
