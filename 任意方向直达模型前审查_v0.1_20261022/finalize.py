from pathlib import Path
import json,hashlib,shutil
R=Path.cwd(); H=R/'任意方向直达模型前审查_v0.1_20261022'; B=R/'连续事件六世界开发比较_v0.1_20261022'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
sources=json.loads((H/'来源hash.json').read_text(encoding='utf8')); manifest=json.loads((B/'completion_manifest.json').read_text(encoding='utf8'))['files']; checked=[]
for name,digest in sources.items():
 p=Path(name)
 if p.is_relative_to(B):
  rel=p.relative_to(B); key=str(rel) if str(rel) in manifest else rel.as_posix(); assert key in manifest,str(p); assert manifest[key]==digest==sha(p),str(p); checked.append(str(rel))
assert checked
sources[str(B/'completion_manifest.json')]=sha(B/'completion_manifest.json')
for name in ('任意方向直达模型与差距分解审查执行稿_给sol_20261022.md','研究工作全路径与思路衔接总结_20261022.md'):
 p=R/name; sources[str(p)]=sha(p)
dump(H/'来源hash.json',sources);dump(H/'新增六世界来源封存核对.json',{'passed':True,'checked_files':checked,'source_manifest':str(B/'completion_manifest.json'),'sha256':sha(B/'completion_manifest.json')})
shutil.copyfile(R/'任意方向直达模型与差距分解审查执行稿_给sol_20261022.md',H/'执行稿原文快照.md')
(H/'只读核验.ps1').write_text("$ErrorActionPreference = 'Stop'\n$projectRoot = Split-Path -Parent $PSScriptRoot\n& (Join-Path $projectRoot '运行环境\\python\\python.exe') -B -X utf8 (Join-Path $PSScriptRoot 'verify.py')\nif ($LASTEXITCODE -ne 0) { throw '只读核验失败' }\n",encoding='utf-8-sig')
(H/'review_packet.md').write_text('''# 任意方向合法直达前审查交付

本轮已完成零求解前审查并停止。先读 [通俗结论](00_通俗结论.md)，再审 [模型合同与待裁决](01_模型合同与待裁决.md)。全量保存数据见 [段账审查](02_保存数据与段账审查.md) 与 60份字段与原路线段账.json；后续有限草案见 [差距分解与有限实验草案](03_差距分解与有限实验草案.md)。

54 原状态与六份末次响应均可恢复原路线与首次服务段账。六世界只有 L_S、L_M、T_M 的末次物理输入可与 P2 配对。本批起点新采集及空任务均为零例，不能据此声称两种边界情形通过验收。

负责人需裁决格心服务与顺带信用、自由域及边界/间隙、距离资源映射及取整、严格首次服务顺序语义。严格开放自由域可能只有下确界而无最短路径。可实施捷径收益、固定顺序最优差距、改变顺序最优收益必须分开；当前数值全部未知。

只读复核入口：只读核验.ps1，使用项目便携 Python，仅解析保存 JSON、核查集合/原相邻移动/首次服务/哈希，不导入生产规划器。来源hash.json 绑定原始来源，新增六世界来源封存核对.json 交叉核对旧封存记录；completion_manifest.json 绑定本交付。零调用账.json 记录全部规划/核心/图搜索/可视查询/捷径/新路线/闭环均为零。草案尚未执行，未实现新算法，未证明创新，旧包与留出不变，停止待审核。
''',encoding='utf8')
progress=R/'当前进度与下一步.md';before=progress.read_bytes();(H/'根进度_更新前快照.md').write_bytes(before)
notice='''# 最新完成：任意方向直达模型与差距分解前审查（2026-10-22）

任意方向直达模型前审查_v0.1_20261022 已完成零求解审查，见该目录 review_packet.md 与 00_通俗结论.md。54 原状态和六份末次响应均恢复字段、实际首次采集索引和完整不重不漏原路线段账；六世界只有 L_S、L_M、T_M 的双方末次物理输入相同。本批无起点新采集及空任务实例，需在后续门槛单列，不能称已验证。来源哈希及独立只读复核通过；新增六世界来源另与其旧封存清单交叉核对。

明确保留采集责任、真实当前位置/基地/H/U/D及距离资源；格心服务、严格自由域边界/正间隙、顺带采集与严格首次服务顺序、距离单位及取整仍列负责人裁决。严格开放自由域可能只有下确界而无可取最短路径；启发式参照差不能全部归为顺序差。现有证据不提供直达节省量，几何收益与顺序收益均未知。已提出下一轮最多24门槛夹具、117条固定保存路线的有限草案，尚未执行。

本轮规划/核心/图搜索/精确搜索/可视查询/候选与捷径求解/新路线/连续闭环全部0；未实现新算法、未证明创新，不改冻结源、旧结果和留出，不提交推送。完成封存后停止，等待负责人审核，不自动启动草案。

---
'''
progress.write_text(notice+'\n'+before.decode('utf-8-sig'),encoding='utf8');(H/'根进度_更新后快照.md').write_bytes(progress.read_bytes())
print(json.dumps({'frozen_six_world_sources_verified':len(checked),'source_hashes':len(sources),'root_progress_updated':True},ensure_ascii=False))
