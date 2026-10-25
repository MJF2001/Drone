"""Export only saved statistics/paths after fixed experiments; no graph search."""
from pathlib import Path
import sys,statistics,json,html,difflib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from probe_common import *
from stage_control import require
require('formal');a=read(H/'analysis.json');g=read(H/'gate_analysis.json');fig=H/'figures';fig.mkdir()
def textfile(name,s):
    with (H/name).open('xb') as f:f.write(s.encode('utf8'))
def table(head,rows):return '\n'.join(['| '+' | '.join(head)+' |','|'+'|'.join(['---']*len(head))+'|']+['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'
def picture(p):
    case=p['case'];c=read(H/'inputs'/f'{case}.json');free=set(map(tuple,c['free']));hist=set(map(tuple,c['covered']));out=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="940" viewBox="0 0 1500 940">','<rect width="1500" height="940" fill="white"/>','<style>text{font-family:Arial,"Microsoft YaHei",sans-serif;fill:#172033}</style>']
    def txt(x,y,s,n=18):out.append(f'<text x="{x}" y="{y}" font-size="{n}">{html.escape(str(s))}</text>')
    txt(30,35,case+' | 指定一次历史邻格干预（seed 20261020）',25);txt(30,67,'蓝：采集前段；橙：返航；紫：处理组最初三步。全图重叠不代表经过次数相同，见数表与局部步序。',18)
    for col,(method,key) in enumerate([('FROZEN','FROZEN_id'),('ON','ON_id')]):
        x=48+col*745;y=126;u=19;m=p[method];path=read(H/'outputs'/f'{p[key]}.json')['result']['raw']['route'];C=m['completion_step']
        txt(x,105,f'{method}：L={m["length"]}，C={C}，R={m["return_tail_steps"]}；90°/180°={m["turns90"]}/{m["turns180"]}',20)
        for yy in range(21):
            for xx in range(31):
                cell=(xx,yy);color='#374151' if cell not in free else '#d8e8ec' if cell in hist else '#f0f4f8';out.append(f'<rect x="{x+xx*u}" y="{y+yy*u}" width="{u}" height="{u}" fill="{color}" stroke="white" stroke-width=".5"/>')
        def xy(q):return (x+(q[0]+.5)*u,y+(q[1]+.5)*u)
        def poly(seq,color,w=2):
            pts=' '.join(f'{xy(q)[0]},{xy(q)[1]}' for q in seq);out.append(f'<polyline points="{pts}" stroke="{color}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity=".85"/>')
        poly(path[:C+1],'#2867d9');poly(path[C:],'#e77d18',3)
        if col:poly(path[:4],'#a42fe1',4)
        for q,label,color in [(c['base'],'B','#111827'),(c['current'],'S','#059669'),(path[C],'E','#dc2626')]:
            xx,yy=xy(q);out.append(f'<circle cx="{xx}" cy="{yy}" r="6" stroke="{color}" fill="white" stroke-width="2"/>');txt(xx+7,yy-5,label,13)
        txt(x,555,f'历史到达 {m["historical_target_steps"]}；本轮重复 {m["repeated_new_target_steps"]}；末格 {p[method+"_E"]}',17)
        seq=path[:2] if col==0 else path[:4];txt(x,592,'最初实际步序（按时间排列，非空间比例）：',17)
        for i,q in enumerate(seq):
            xx=x+i*156;out.append(f'<rect x="{xx}" y="620" width="135" height="57" rx="6" fill="#f3e8ff" stroke="#a42fe1"/>');txt(xx+13,644,f'步{i}: {q}',16)
            if i<len(seq)-1:txt(xx+137,655,'→',21)
        txt(x,705,'先一步采到(5,3)。' if col==0 else '强制(5,1)后，恢复段马上回到(5,2)，第3步才采到(5,3)。',17)
    txt(30,765,'两状态全部三seed：ΔL=+2=ΔC(+2)+ΔR(0)；历史到达+2，90°不变，180°+1。',23)
    txt(30,805,'首次共同决策状态：原第1步=处理第3步，current=(5,3)、previous=(5,2)、pending相同，此后字面后缀完全相同。',19)
    txt(30,839,'处理组剩余距离资源少2，时钟/缓存过程也不等同；不能称完整运行状态相同。最后采集格、返航尾段和覆盖结果均不变。',18)
    txt(30,874,'所有实际动作、转弯与耗时见6正式配对及24调用表；P2未新跑。本次一次指定动作未获得支持，按稿停止。',18)
    txt(30,910,'固定选例：每状态原首seed，不挑成绩；原版与处理均完整合法且入口严格<20秒。',17)
    out.append('</svg>');return '\n'.join(out)
examples=[]
for case in CASES:
    p=next(p for p in a['pairs'] if p['case']==case and p['seed']==SEEDS[0]);textfile('figures/'+case+'.svg',picture(p));save(fig/(case+'.json'),dict(case=case,seed=SEEDS[0],pair=p,source='saved original outputs only',graph_searches=0));examples.append(dict(case=case,seed=SEEDS[0],svg=case+'.svg',png=case+'.png'))
save(H/'figure_index.json',examples)
save(H/'failures.json',[]);save(H/'unrun_slots.json',[])
ledger=dict(v01_real_entries=0,v02_real_entries=len(read(H/'fixed_order.json')),actual_logged_entries=len((H/'actual_order.jsonl').read_text(encoding='utf8').splitlines()),actual_core_calls=sum(len(read(H/'outputs'/f'{r["id"]}.json')['actual_core_calls']) for r in a['rows']),gate_entries=len([r for r in a['rows'] if r['phase']=='gate']),formal_entries=len([r for r in a['rows'] if r['phase']=='formal']),preparation_fixture_cases=2,expected_negative_preparation_cases=1,intervention_stub_cases=8,force_helper_stub_invocations=7,entry_wrapper_stub_invocations=1,cold_import_inventory_processes=len(read(H/'import_inventory.json')),upstream_stopped_package_verify=1,upstream_graph_searches=0,ordinary_BFS_gate_analysis=g['ordinary_BFS_total'],ordinary_BFS_full_analysis=a['ordinary_BFS_total'],ordinary_BFS_final_verify_expected=a['ordinary_BFS_total']+g['ordinary_BFS_total'],ordinary_BFS_delivery_total_if_verify_passes=2*(a['ordinary_BFS_total']+g['ordinary_BFS_total']),ordinary_BFS_note='These are independent saved-output audit traversals; native geometry work remains inside actual core timings, not counted again as independent verification.',coverage_exact_searches=0,P2_calls=0,LAST_calls=0,four_direction_calls=0,extra_actions=0,action_candidate_enumeration=0,extra_maps=0,new_seeds=0,new_budget_tiers=0,holdout_uses=0,technical_failures=0,retries=0,unrun_slots=0,final_verify_status='See actual verify.log and verification_receipt.json; expected audit count is not a success claim.')
save(H/'call_ledger.json',ledger)
changes=[]
old=R/'PPCPP一次历史邻格干预诊断_v0.1_20261021'
for name in ('build_v02.py','probe_common.py','probe_hook.py','decision_audit.py','analyze.py','stub_gate.py','worker.py','run_fixed.py','preseal.py','verify.py','candidate.py','runtime.py','native_probe.py'):
    p=H/name;q=old/name;changes.append(dict(file=name,v01_sha256=sha(q) if q.exists() else None,v02_sha256=sha(p),same_bytes=q.exists() and p.read_bytes()==q.read_bytes()))
save(H/'v01_to_v02_changes.json',changes)
change=''
for name in ('stub_gate.py','worker.py','run_fixed.py','preseal.py','verify.py','candidate.py','runtime.py','native_probe.py'):
    change+=''.join(difflib.unified_diff((old/name).read_text(encoding='utf8').splitlines(True),(H/name).read_text(encoding='utf8').splitlines(True),fromfile='v0.1/'+name,tofile='v0.2/'+name))
textfile('v01_to_v02_auxiliary.diff',change)
report='# 指定一次历史邻格干预：v0.2完整结果与停止结论\n\n'
report+='本轮两个原始状态、各原三个种子全部运行完成：处理均比原版多2步、多1次180°转弯，没有严格长度收益。强制向历史格移动后，恢复逻辑第二步立即回原起点，随后重新接回原完整后缀。因此“只改这一初始一步、随后恢复原PPCPP”在本次两指定状态未获支持；按稿封存停止，不追加第二步或换动作。\n\n'
report+='## 1. 修复与门槛确实通过\n\nv0.1整个停止包保持不动。上游verify_stopped实际通过，当前v0.2完成实验核验与该停止包核验分开。candidate.py从冻结原始源用二进制复制，实际字节/hash相同；两输入亦与原压力批字节相同。原native循环AST不变，runtime仅替换native导入，强制helper在原while前恰调用一次，完整最小diff、文件分类与源码出处均交付。辅助程序从v0.1接续不当已验收；本轮实际重新通过。\n\n实际顺序：静态PASS→2准备流程夹具PASS（其中预期字节失败非零退出、未创建夹具preseal/哨兵）→预封存10347来源文件→8干预桩PASS→12关闭等价门槛PASS→12全新正式入口PASS。每阶段PASS收据绑定52份代码/协议/输入/任务hash及相应产物，源码不变才可进入下一阶段。所有PowerShell外部命令检查LASTEXITCODE；subprocess结果显式检查。\n\n12等价入口的6槽中，FROZEN/OFF与原压力批完整非时间字段逐项相同，未忽略trace/detail。仅7条预登记时间路径排除，版本无需排除；正式FROZEN也再与门槛/历史一致，未用漂移控制制造收益。所有24入口均单核心、完整合法且严格及时，技术失败0、重试0、未运行0；准备负例不混正式失败。\n\n'
report+='## 2. 六个正式配对，方向ON−原版\n\n'
report+=table(['状态','seed','原/处理L','原/处理C','原/处理R','ΔL/ΔC/ΔR','原/处理90°','原/处理180°','入口毫秒 原/处理'],[[p['case'],p['seed'],f'{p["FROZEN"]["length"]}/{p["ON"]["length"]}',f'{p["FROZEN"]["completion_step"]}/{p["ON"]["completion_step"]}',f'{p["FROZEN"]["return_tail_steps"]}/{p["ON"]["return_tail_steps"]}','2/2/0',f'{p["FROZEN"]["turns90"]}/{p["ON"]["turns90"]}',f'{p["FROZEN"]["turns180"]}/{p["ON"]["turns180"]}',f'{1000*p["FROZEN_seconds"]:.6f}/{1000*p["ON_seconds"]:.6f}'] for p in a['pairs']])
report+='\n每状态合格n=3，ΔL均值2、范围[2,2]，ΔC均值2、范围[2,2]，ΔR均值0、范围[0,0]，90°差0，180°差1，历史到达差2，新目标重复差0、非目标移动差0。全部三seed原值及其余指标见CSV；仅两个独立指定几何，不能把6配对当6独立几何，不作显著性推断。\n\n'
report+=table(['状态','当前可检覆盖 原/处理','公开已检/公开总量','暂缓未计完成','末采集位置 原/处理','旧P2长度仅背景'],[[p['case'],'1 / 1',f'{p["FROZEN"]["published_covered"]}/{p["FROZEN"]["published_targets"]}',p['FROZEN']['deferred'],f'{p["FROZEN_E"]} / {p["ON_E"]}',p['background_old_P2_length']] for p in a['pairs'] if p['seed']==SEEDS[0]])
report+='\n当前目标和暂缓账与原输入完全相同。公开覆盖率不足1的部分来自暂缓遮挡，不能称全部公开目标已检完。完整路线步数均不超过原距离预算6510；强制一步与随后回到历史起点共增加历史到达2次，没有额外采集信用。全部24调用的覆盖/暂缓、历史与本轮重复、非目标、90/180、资源与耗时在24调用完整指标.csv保留。\n\n'
report+='## 3. 动作后具体发生了什么\n\n全部6处理输出forced_history_step恰1，原pending前后全量集合相同（maze217、serpentine219）。第0→1步强制(5,2)→(5,1)，current变(5,1)、previous变(5,2)，已用距离1、剩余6509。第一次后续常规决策是recovery，候选目标按原最近图距规则选(5,3)；该点无未检邻格，真实路径是(5,1)→(5,2)→(5,3)。第2步立即回到原起点；第3步首次新采集(5,3)，原版第1步即采到同格。\n\n在原版第1步/处理第3步，current=(5,3)、previous=(5,2)、pending完全相同，固定图/捕食者/权重/tie/正常阶段也一致；从此两条字面已有后缀完全相同。原剩余距离6509、处理6507，时钟和缓存过程不同，因此仅称相同的确定性决策状态，不称完全相同运行状态。两方法末采集位置与返航尾段不变，ΔL=+2=ΔC(+2)+ΔR(0)。新增往返引入1个180°，90°不变；转弯未加权抵消长度结论。\n\n逐事件独立复核保存的local全部选项/奖励/分数/tie；恢复最近目标与字面恢复/返航段最短长度用普通BFS距离核验，不调用planner、不补新路线。正常local/recovery每段pending减少，强制段独立不采集。全部动作计入原输入完整双审计，不重开20秒、不重置previous、不藏步或拼P2后缀。\n\n'
for ex in examples:report+=f'- [{ex["case"]}固定首seed单页图](figures/{ex["png"]})：原版/处理全路线、初始步序、成本和转弯并列。\n'
report+='\n## 4. 计时、运行条件与调用账\n\n20秒共享暖完整入口，输入解析/校验、ON读取封存动作与干预、核心、完整审计、编码都计入；90秒进程看门狗、隔离串行、OMP/OPENBLAS/MKL线程1。所有正式配对双方都及时合法完整，主表6/6，没有迟到/非法/中止可补捞。只有少量短入口计时、ON含完整动作与pending记录开销，不据此称新的速度优势或稳健性能排名。\n\n'
for mode in ('FROZEN','ON'):
    rr=[r['seconds']*1000 for r in a['rows'] if r['phase']=='formal' and r['mode']==mode];report+=f'- 正式{mode}入口毫秒：mean={statistics.mean(rr):.6f}，min/max={min(rr):.6f}/{max(rr):.6f}；逐seed在上表及raw。\n'
report+=f'\n实际总入口24、核心24（12门槛+12正式），上限已到，不继续。2准备夹具、8干预桩（7helper+1编码wrapper stub）、2冷导入清单进程分别记账；v0.1真实调用仍0。历史准备/P2/LAST/四方向/覆盖精确/动作枚举/留出/新图/新seed/新预算/重试均0。\n\n普通图距离均为保存输出独立审计BFS：门槛分析{g["ordinary_BFS_total"]}，完成批分析{a["ordinary_BFS_total"]}（含门槛再次审核），最终verify预计再{a["ordinary_BFS_total"]+g["ordinary_BFS_total"]}，实际成功以verify.log及收据为准。若成功合计{2*(a["ordinary_BFS_total"]+g["ordinary_BFS_total"])}次；上游停止包核验图距离0。原生核心内部几何工作已包含核心时间，不把它冒称额外独立核验；独立BFS不算覆盖最优或新规划入口。图文导出无图搜索，只用保存结果。\n\n'
report+='## 5. 结论边界与停止\n\n当前这个事后指定的一次动作没有带来长度收益，只产生立即往返。它未得到这两指定原状态的支持；不能因此证明所有历史通道策略都无效，也不能证明PPCPP最优。旧P2比原版短8/70步是其整条后续路线的背景，强制第一步无法继承那些收益；本轮没有运行P2、精确最优或任何在线触发/选格算法。\n\n完成即停止，不加第二步/整条通道，不换格、不调奖励/转弯权重，不扩图、不用留出，不自动开发或Git提交推送。当前没有新PPCPP在线改进算法或已确认创新点。封存交负责人审核。\n\n'
report+='## 6. 审核证据\n\n版本修复与预登记.md、copy_manifest/source_contract/minimal.diff、v01_to_v02_changes.json与辅助diff、binding_files及receipts/全阶段hash收据；fixtures/两准备夹具、stub_results八项；preseal/真实导入hash、fixed_order与actual_order、jobs/inputs/outputs/logs；gate_analysis、analysis、all_decision_audits及三张CSV；两状态图与其数据；call_ledger、failures与unrun均完整。verify.py是首次真实入口前已封存的纯只读完成实验核验；图文生成仅在实验结束后使用现有统计导出，列最终manifest，不冒称运行前已有图文。最终实际通过日志与收据另封以避免自引用，根进度更新为实际完成与停止。\n'
textfile('通俗报告与完整结果.md',report)
textfile('review_packet.md','# 完成实验审核入口\n\n先读通俗报告与完整结果.md。两状态×原三seed，处理各多2步、多1个180°、返航尾段不变；全部立即回原起点，采到(5,3)后与原字面后缀相同。当前一次动作不支持，按稿停止。\n\n实际24入口/24核心（12等价+12正式），2准备夹具与8干预桩分账；与v0.1停止包核验区别开。原candidate/两输入字节hash、原while AST、阶段PASS绑定及无P2运行时读取必须核对。所有门槛原版/OFF/历史及正式原版非时间字段一致。\n\n只读完成实验核验：\n\n```powershell\n& .\\运行环境\\python\\python.exe -B -X utf8 PPCPP一次历史邻格干预诊断_v0.2_20261021/verify.py\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n```\n\n该核验不调用planner；每次独立BFS582次，审核若重跑请另记账，不覆盖原日志/账。日志和收据排除主manifest自引用，实际完成后completion_manifest覆盖。当前不启动后续干预或在线开发。\n')
print('Exported complete fixed results, 2 SVGs, change records, calls/failure/unrun ledgers and report; new planner/graph search=0')
