"""Seal new inventory only; append root progress while preserving original bytes."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(name,value):
    with (H/name).open('x',encoding='utf-8') as f:f.write(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2))
def main():
    assert not (H/'manifest.json').exists()
    v=read(H/'preseal_verify.json');assert v['passed']
    pp=v['pre_post_structure'];obs=[x for x in pp if x['event']=='obstacle' and x['U_after_event_components']>1]
    extra='\n\n## 障碍组的五个分离状态与来源\n\n'
    extra+='|状态|事件前U分量|事件后U分量|事件后片大小|\n|---|---:|---:|---|\n'
    for x in obs:extra+=f"|{x['id']}|{x['U_before_event_components']}|{x['U_after_event_components']}|{x['after_sizes']}|\n"
    extra+='\n其中4例在障碍前就已有两个剩余分量，small_I_obstacle_p30从1变2（8格变为4+3格，一格因障碍暂缓）。这是固定任务集合的结构比较，不是新路径计算或算法收益因果检验。五例仅作已核来源的结构候选，不保证旧实际直达路线受阻、不保证规则可激活。\n'
    for n in ['00_通俗结论与地图入口.md','02_连续性与剩余分片结构.md']:
        p=H/n;p.write_text(p.read_text(encoding='utf-8')+extra,encoding='utf-8')
    write('03_来源与计算边界.md','# 核验和计算边界\n\n54输入逐项核中心区OFF manifest；历史链四份来源按已封存history_evidence中的hash核对。原准备input_audit核原manifest；9次准备返回与其job.input_sha256、54实际截断前缀、H集合、当前/来向/旧后缀逐项比对。只读历史信用见证不重算中心区几何；格心落于中心区的证据沿用固定合同。没有重新执行旧完整实验verify，也没有重跑9次准备。\n\n主分析271次集合连通遍历（270个状态层＋1个G1对照）、访问72470格；独立核验324次并查集（含54组事件前U结构）。这些是新增结构计算，非新增规划/最短路/可视或覆盖搜索。每次核验重跑都会增加结构计算，日志单列。核心/post/新历史/新路线/规则评估均0。\n\n未检集合的四邻接分量不是新算法片区定义；没有按规则触发或路线收益选图。完整索引54行，六组图按先登记的族/基底/进度/ID确定，均为large家族corner事件；不能把这六图当障碍组代表。另附G1原始孤立任务块语义对照。\n')
    write('review_packet.md','# 审核入口\n\n先读00通俗结论和地图对照.html，再看01/02与inventory.json。54状态均P0/P连通，30状态U分离；18障碍状态仅5例U分离。9原几何，不是54独立地图。\n\n`运行环境\\python\\python.exe -B -X utf8 连续道路与剩余任务地图语义盘点_v0.1_20261023\\verify.py`：只读独立并查集/原始历史集合/来源hash/根链核验，无规划器导入。会重新计算集合连通性，不是假装零计算。\n\n本轮未判规则适用、未查直达是否真受阻、未设计新地图/新分区或跑算法。先由用户确认地图符合连续道路场景；当前停止。\n')
    write('protocol.md',(R/'连续道路与剩余任务片区地图校正执行稿_给sol_20261023.md').read_text(encoding='utf-8'))
    previous=(H/'root_before.md').read_bytes();assert (R/'当前进度与下一步.md').read_bytes()==previous
    old=R/'障碍后片区两阶段规则有限验证_v0.2_20261023';assert previous==(old/'root_after.md').read_bytes()
    assert hashlib.sha256(previous).hexdigest()==read(old/'final_receipt.json')['root_sha256']
    write('previous_root_binding.json',dict(previous_final=str(old/'final_receipt.json'),previous_final_sha256=hashlib.sha256((old/'final_receipt.json').read_bytes()).hexdigest(),root_before_sha256=hashlib.sha256(previous).hexdigest()))
    prefix='''# 最新进度：连续道路与剩余任务地图只读盘点完成（2026-10-23）

连续道路与剩余任务地图语义盘点_v0.1_20261023 已完成并停止，入口00_通俗结论与地图入口.md、地图对照.html及review_packet。固定读取中心区OFF批54状态/9基底，原始P0和事件后P全部四邻接连通，当前可检T也全部连通；U有30状态分离。straight18中13、corner18中12、obstacle18中5分离，不能将54状态都称障碍场景。

54份H均核到9次原PPCPP准备路线的真实截断前缀，集合、当前位置/来向、旧后缀与既有中心见证一致；属于四邻接格心历史，当前接口固定H，没有新增斜向执行或扩大信用。没有独立工程道路边界字段；任务P是道路形模型，F含道路外可飞域，不作实地安全/尺度结论。五个障碍U分离状态中4个在事件前已分离，small_I_obstacle_p30由1变2（一未采格暂缓）；仅是任务结构分解，不证明规划收益。

原项目道路任务区连续，与近期G1等原本不相接任务矩形不同，不能将后者局限外推所有旧图。六组图按I/L/Z最小字典序基底、最早/晚进度与ID固定选择，另附G1语义对照；完整任务格面/原轮廓/H/U/D/障碍/实际原生前缀分层。G1图版初稿通用标题已修为起始地图，旧图保留、HTML引用v2；无算法或数据改变。

独立并查集与源历史集合核验通过；核心/post/新历史/新路线/最短路/可视查询/规则评估全部0，主分析271次集合遍历及独立324次并查集计账。未评价新规则、未改旧原标签不相接限制、未核旧实际直达路线是否受阻。先待用户看图确认场景，再决定片区定义；不自动进入新算法实验。旧输入/结果/final不改，当前根仅前缀追加。

---

'''.encode('utf-8')
    after=prefix+previous;(H/'root_after.md').write_bytes(after);(R/'当前进度与下一步.md').write_bytes(after)
    files={str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in H.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    write('manifest.json',dict(files=files,root_sha256=hashlib.sha256(after).hexdigest(),status='sealed_map_inventory_not_algorithm_validation'))
    print('SEALED inventory and appended root; verify separately.')
if __name__=='__main__':main()
