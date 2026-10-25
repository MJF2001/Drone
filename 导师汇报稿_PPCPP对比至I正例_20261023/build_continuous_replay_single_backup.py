import json,hashlib

def build_continuous(folder):
 p=folder/'七算法从零起飞事件演示_v0.3'
 raw=(p/'results.json').read_bytes(); d=json.loads(raw)
 v=json.loads((p/'independent_verification.json').read_text(encoding='utf8'))
 assert v['passed'] and v['results_sha256']==hashlib.sha256(raw).hexdigest()
 rows=[]
 for m in ['PPCPP','P2_MULTI','OARP_CORE2','TREE_MST','CSTAR','TRACE','CAP']:
  cells=[]
  for w in d['worlds']:
   s=next(s for s in d['sessions'] if s['world']==w['id'] and s['method']==m)
   cells.append('不支持空旧路线初始化' if s['status']!='complete' else f"<b>{s['steps']} 步</b> / {s['total_seconds']*1000:.3f} ms<br>已检 {len(s['completed'])}，暂缓 {len(s['deferred'])}<br>90°/180°转弯 {s['turn90']}/{s['turn180']}")
  rows.append('<tr><th>'+m+'</th>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr>')
 h='''<div class="replay" id="continuous-replay"><h3>从零起飞：覆盖到50%时出现事件</h3><p><b>使用当时冻结版本重新求解，四邻接移动、到格心采集；不是现在的直达／中心区版本。</b>初始任务全部待检。各方法独立飞行，达到初始任务50%后公开固定事件，再规划剩余任务并返航。各方法的触发步数不同。</p><div class="replay-controls"><select id="cr-case"><option value="0">直线新增区域</option><option value="1">拐角新增区域</option><option value="2">新增障碍</option></select><button id="cr-play" class="primary">同时起飞</button><button id="cr-reset">回到起点</button><button id="cr-event">首个事件</button><button id="cr-end">查看完成</button><label>速度 <select id="cr-speed"><option>4</option><option selected>12</option><option>30</option></select>步/秒</label></div><input id="cr-range" type="range" min="0" step="0.1" value="0" aria-label="实际飞行进度"><p id="cr-clock"></p><p>黄色＝原待检，紫色＝新增待检，绿色＝已检，深色＝禁飞，红框＝新障碍；橙点＝无人机，蓝块＝基地，蓝线＝实际轨迹。淡线只表示当前计划。动画按相同飞行速度播放，不模拟计算等待。</p><div class="replay-grid" id="cr-grid"></div><h3>全过程距离与计算时间</h3><p>时间是初始规划＋事件后规划的入口耗时，步数包括事件前实际飞行。新增任务使覆盖率分母增加，不会清除已完成记录。三张原开发小图、单种子；成功入口全部及时返回。</p><div style="overflow-x:auto"><table><thead><tr><th>方法</th><th>直线扩展</th><th>拐角扩展</th><th>新增障碍</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div><div class="note"><b>连续事件比较的小结</b><ul><li>六种支持从零初始化的方法均完成可检任务并返航；PPCPP在这三例计算耗时最低。</li><li>两例扩展的工作量相同：PPCPP为114、134步，P2为102、124步。PPCPP更快，但路线并非最短；其他方法的距离表现随场景变化。</li><li>障碍例PPCPP有1格在检查前被遮挡，其余方法此前已经检查。65已检＋1暂缓与66已检不能直接按总步数排优劣。</li><li>OARP_CORE2冻结入口要求已有旧路线，不能从空历史初始化；未另换初始化算法，下方保留其原快照结果。</li></ul>这只是三个演示性开发案例，不代表普遍优势，不与原批统计混算。</div><details><summary>本次运行与证据说明</summary><p>18个成功会话，36次成功入口；包含OARP旧版失败尝试共37次实际入口。4份成功返回复用、32次新增；v0.2缓存类型检查失败时没有新增核心调用。原始失败均保留。独立审核已核对从零状态、50%触发、真实历史、距离资源、路线与任务账。</p><p>本报告目录：七算法从零起飞事件演示_v0.3/results.json、protocol.json、independent_verification.json。</p></details></div>'''
 css='#cr-range{width:100%}#cr-grid canvas{width:100%;height:auto}#cr-grid .replay-card{padding:12px;min-width:0}#cr-grid h4{margin:0}#cr-grid p{font-size:12px;white-space:pre-line}#continuous-replay table{min-width:640px;font-size:13px}#continuous-replay .replay-controls{flex-wrap:wrap}'
 js='(()=>{const D='+json.dumps(d,ensure_ascii=False).replace('<','\\u003c')+';'+(folder/'continuous_replay.js').read_text(encoding='utf8')+'})();'
 return h,css,js
