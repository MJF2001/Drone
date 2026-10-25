from pathlib import Path
import json,hashlib

def front_views(H):
 p=H/'前方未飞覆盖路段受阻展示_v0.1_20261024';raw=(p/'results.json').read_bytes();d=json.loads(raw);v=json.loads((p/'independent_verification.json').read_text(encoding='utf8'));assert v['passed'] and v['results_sha256']==hashlib.sha256(raw).hexdigest()
 local=[];direction=[];worlds=[];sessions=[];names={'I':'直路','L':'转角路','Z':'折线路'}
 def metric(r):
  v=[(b[0]-a[0],b[1]-a[1]) for a,b in zip(r,r[1:])];dots=[a[0]*b[0]+a[1]*b[1] for a,b in zip(v,v[1:])];return dict(steps=len(r)-1,turn90=dots.count(0),turn180=dots.count(-1))
 for c in d['protocol']['cases']:
  cid=c['id'];s=c['snapshot'];initial=c['initial'];pre=c['prefix'];cut=c['cut'];group={r['method']:r for r in d['records'] if r['case']==cid};name=names[cid.split('_')[1]]+' · 下一格受阻（新验证）'
  def panel(method,label):
   r=group[method];route=pre+r['route'][1:];return dict(name=label,route=route,remaining=len(r['route'])-1,seconds=r['seconds'],**metric(route))
  mix=json.loads(Path(group['LOCAL_P2']['source']).read_text(encoding='utf8'))['result']['raw'];ori=json.loads(Path(group['ORIENT4']['source']).read_text(encoding='utf8'))['result']['raw']
  p0=panel('PPCPP','原PPCPP');pm=panel('LOCAL_P2','局部P2混合');pm.update(selected=mix['selected'],window=mix['window'],local_steps=len(mix['local']['route'])-1 if mix['local'] and mix['local'].get('route') else None,local_status=mix['local'].get('status') if mix['local'] else 'not_called')
  base=dict(id=cid,label=name,initial=initial,snapshot=s,prefix=pre,cut=cut,event='下一格新增障碍',marker=c['marker'],evidence=c['evidence'])
  local.append(dict(**base,panels=[p0,pm]));direction.append(dict(**base,panels=[p0,panel('ORIENT4','四方向组合')],selected_degree=ori['selected_degree'],candidates=[dict(degree=a['degree'],route=a['inverse']['route'],steps=len(a['inverse']['route'])-1,seconds=a['seconds']) for a in ori['candidates']]))
  ini=dict(initial,published=initial['published_targets']);worlds.append(dict(id=cid,title=name,initial=ini,after=dict(free=s['free'],published=s['published_targets']),events=[dict(name='下一格新增障碍',remove=c['marker'])],front_verified=True))
  for method in ['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP']:
   r=group[method];route=pre+r['route'][1:];sessions.append(dict(world=cid,method=method,status='complete',route=route,steps=len(route)-1,total_seconds=r['seconds'],completed=s['targets'],deferred=s['deferred_targets'],events=[dict(name='下一格新增障碍',step=cut)],phases=[dict(start_step=0,plan=c['old_plan'],seconds=0,free=initial['free'],published=initial['published_targets']),dict(start_step=cut,plan=r['route'],seconds=r['seconds'],free=s['free'],published=s['published_targets'])],shared_prefix=True,**{k:z for k,z in metric(route).items() if k!='steps'}))
 rows=[]
 for method in ['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP','LOCAL_P2','ORIENT4']:
  cells=[]
  for c in d['protocol']['cases']:
   r=next(r for r in d['records'] if r['case']==c['id'] and r['method']==method);cells.append(f"{len(r['route'])-1}步 / {r['seconds']*1000:.3f} ms")
  rows.append('<tr><td>'+method+'</td>'+''.join('<td>'+x+'</td>' for x in cells)+'</tr>')
 table='<div class="table-scroll"><table><thead><tr><th>方法</th><th>直路</th><th>转角路</th><th>折线路</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
 text='<h3>新验证：下一格未飞覆盖路段被阻断</h3><p><b>三例均严格满足：障碍就在旧计划下一步，且该格此前从未飞过；其后仍有未检任务，绕行后其余任务和基地可达。</b>六种方法共用真实历史前缀与同一个障碍，事件后再分别规划，不是各自独立从零规划。共24次新入口（含两种改进），全部通过核验。</p>'+table+'<p class="small muted">上表为事件后剩余步数与本次入口耗时，卡片全程另含共同前缀。每例各方法完成同一组可检任务，障碍遮挡的1格统一暂缓。本批是三例新开发展示，不能替换旧批平均结论。</p><p class="note">局部混合在转角例83→79步，其余两例不变；四方向分别34→32、83→65、104→92步。这里是新条件下的实测结果，不是给旧数据挪动障碍。</p>'
 return [dict(id='local-demo',kind='local',cases=local,default=0),dict(id='direction-demo',kind='direction',cases=direction,default=0)],worlds,sessions,text
