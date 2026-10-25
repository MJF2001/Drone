import json,hashlib
METHODS=['PPCPP','P2_MULTI','TREE_MST','CSTAR','TRACE','CAP']
def load(folder,name):
 p=folder/name;raw=(p/'results.json').read_bytes();v=json.loads((p/'independent_verification.json').read_text(encoding='utf8'));assert v['passed'] and v['results_sha256']==hashlib.sha256(raw).hexdigest();return json.loads(raw)
def build_continuous(folder):
 d=load(folder,'七算法从零起飞事件演示_v0.3');mixed=load(folder,'六算法综合连续事件演示_v0.2');p=mixed['protocol']
 d['sessions']=[s for s in d['sessions'] if s['method'] in METHODS]
 for w in d['worlds']:
  w['title']={'straight':'直线新增区域','corner':'拐角新增区域','obstacle':'新增障碍'}[w['event']]
  w['events']=[dict(name=w['title'],threshold=len(w['initial']['published'])//2,remove=sorted(set(map(tuple,w['initial']['free']))-set(map(tuple,w['after']['free']))))]
  for s in [s for s in d['sessions'] if s['world']==w['id']]:
   s['events']=[dict(name=w['title'],step=s['event_step'])]
   s['phases']=[dict(start_step=0,plan=s['initial_plan'],seconds=s['initial_seconds'],free=w['initial']['free'],published=w['initial']['published']),dict(start_step=s['event_step'],plan=s['after_plan'],seconds=s['after_seconds'],free=w['after']['free'],published=w['after']['published'])]
 world=dict(id=p['world'],title='综合：两次扩展＋三个障碍',initial=p['initial'],after=p['stages'][-1],events=p['events'])
 d['worlds'].append(world)
 for s in mixed['sessions']:s['world']=p['world'];d['sessions'].append(s)
 from front_views import front_views
 _,fw,fs,front_text=front_views(folder)
 d['worlds'].extend(fw);d['sessions'].extend(fs)
 def table(headers,rows):return '<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table></div>'
 schedule=table(['初始任务覆盖进度','公开事件','变化'],[['20%（12/60）','直线扩展','新增25个待检格'],['35%（21/60）','障碍一','单格障碍'],['50%（30/60）','拐角扩展','新增25个待检格'],['65%（39/60）','障碍二','横向相邻2格'],['80%（48/60）','障碍三','L形3格']])
 rows=[]
 for s in mixed['sessions']:
  rows.append([s['method'],str(s['steps'])+' 步',f"{s['total_seconds']*1000:.3f} ms",str(len(s['completed']))+' / '+str(len(s['deferred'])),str(s['turn90'])+' / '+str(s['turn180']),' → '.join(str(e['step']) for e in s['events'])])
 mixedtable=table(['方法','总路程','6次规划累计耗时','已检 / 暂缓','90° / 180°转弯','五次事件发生的实际步数'],rows)
 oldrows=[]
 for m in METHODS:
  cells=[m]
  for w in d['worlds'][:3]:
   s=next(s for s in d['sessions'] if s['world']==w['id'] and s['method']==m)
   cells.append(f"{s['steps']} 步 / {s['total_seconds']*1000:.3f} ms<br>已检 {len(s['completed'])} / 暂缓 {len(s['deferred'])}")
  oldrows.append(cells)
 h='''<div class="replay" id="continuous-replay"><h3>从零起飞：扩展与障碍接连发生，怎样继续巡检？</h3><p><b>真实路线回放，使用当时冻结版本：四邻接移动、格心采集。</b>不是后来的直达／中心区版本。初始任务全部待检，各方法保留自己实际飞行产生的历史。现在默认展示综合场景，也可切回三个单事件场景。</p><details><summary>历史综合的五次事件（非本次前方阻断验证）</summary>'''+schedule+'''<p>进度固定按最初60个任务中已检查的数量计算，不受新增任务影响。事件坐标、形状和顺序均在求解前固定；同一个障碍在各方法达到指定进度时出现，<b>不是同一时钟时刻出现</b>。障碍持续存在，不清除已完成记录。新增区域只在公开后才交给算法。</p></details><div class="replay-controls"><label>场景 <select id="cr-case">'''+''.join(f'<option value="{i}"'+(' selected' if i==4 else '')+'>'+(('历史非严格前方阻断 · ' if i<4 else '')+w['title'])+'</option>' for i,w in enumerate(d['worlds']))+'''</select></label><button id="cr-play" class="primary">同时起飞</button><button id="cr-reset">回到起点</button><label>跳到 <select id="cr-event-select"></select></label><button id="cr-event">事件出现</button><button id="cr-end">查看完成</button><label>速度 <select id="cr-speed"><option>4</option><option selected>12</option><option>30</option></select>步/秒</label></div><input id="cr-range" type="range" min="0" step="0.1" value="0" aria-label="实际飞行进度"><p id="cr-clock"></p><div id="cr-timeline"></div><p class="small muted">黄＝原待检，紫＝新增待检，绿＝已检，深色＝禁飞，红框＝新障碍；橙点＝无人机，蓝块＝基地，蓝线＝实际飞行，淡线＝当前计划。动画按相同飞行速度播放，不模拟计算等待。“事件出现”跳到最早触发该事件的方法，其余方法可能尚未达到对应进度。</p><div class="replay-grid" id="cr-grid"></div><h3>综合场景结果：完整执行五次事件后返航</h3><p>一张综合开发图、一个固定种子。每种方法初始规划1次、事件后规划5次，共36次成功入口；均及时返回合法路线。累计耗时不包含动画或离线审核；路程包含所有实际执行段，不是六次完整计划的长度相加。</p>'''+mixedtable+'''<div class="note"><b>怎样理解综合结果？</b><ul><li>六种方法都经历两次扩展、三个不同障碍，并完成当前可检任务后返航。PPCPP六次规划合计约7.19毫秒，本例计算耗时最低。</li><li>最终已检量不同：P2检查110格；PPCPP、TREE_MST、CAP检查106格、暂缓4格；C*、TRACE检查104格、暂缓6格。因此不能把全部总步数直接排成优劣榜。</li><li>完成与暂缓的具体任务集合相同的组再比较距离；这仍是一个综合案例，不代表普遍优越或障碍越多越占优。</li></ul></div><details><summary>查看原有三个单事件场景的结果</summary>'''+table(['方法','直线扩展','拐角扩展','新增障碍'],oldrows)+'''<p>两例扩展工作量相同，PPCPP为114、134步，P2为102、124步：PPCPP更快，但并非路线最短。单障碍例PPCPP有1格暂缓，其他方法无暂缓，不能直接排名。原单事件结果未重跑。</p></details><details><summary>数据来源与运行说明</summary><p>综合批：六算法综合连续事件演示_v0.2。独立回放核验通过。前版第三次入口因历史来源字段未累积而失败；修正演示输入账本后复用前两份成功结果，冻结算法未改。36次成功入口，含失败尝试共37次实际入口。原单事件三例保存于七算法从零起飞事件演示_v0.3，失败和历史文件均保留。</p></details></div>'''
 h=h.replace('从零起飞：扩展与障碍接连发生，怎样继续巡检？','前方下一格受阻：同一真实历史，分别接续')
 h=h.replace('初始任务全部待检，各方法保留自己实际飞行产生的历史。现在默认展示综合场景，也可切回三个单事件场景。','默认展示三组新验证：共同真实历史执行到停止点，下一步未飞格出现障碍，再分别接续。三例都不是只阻断返航。历史综合和单事件仍可查阅，但没有保证各方法前方真实受阻，不能作为本硬条件的证据。')
 h=h.replace('<h3>综合场景结果：完整执行五次事件后返航</h3>',front_text+'<details><summary>历史综合结果（未保证前方覆盖路线受阻，不作为本次证据）</summary><h3>原综合场景结果</h3>')
 h=h.replace('<details><summary>查看原有三个单事件场景的结果</summary>','</details><details><summary>查看原有三个单事件场景的结果（非严格前方阻断）</summary>')
 css='#cr-range{width:100%}#cr-grid canvas{width:100%;height:auto;aspect-ratio:auto}#cr-grid .replay-card{padding:12px;min-width:0}#cr-grid h4{margin:0}#cr-grid p{font-size:12px;white-space:pre-line}#continuous-replay table{min-width:640px;font-size:13px}#continuous-replay .replay-controls{flex-wrap:wrap}#cr-timeline{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}#cr-timeline span{font-size:12px;padding:5px 8px;background:#e6edf4;border-radius:4px}#cr-timeline span.active{background:#d7e9df;color:#24503c}'
 js='(()=>{const D='+json.dumps(d,ensure_ascii=False).replace('<','\\u003c')+';'+(folder/'continuous_replay.js').read_text(encoding='utf-8-sig')+'})();'
 return h,css,js
