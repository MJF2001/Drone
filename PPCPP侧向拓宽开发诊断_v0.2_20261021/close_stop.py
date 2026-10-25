"""Seal the mandatory B_STATIC stop only; never continue production."""
from pathlib import Path
import sys,json,hashlib,datetime
H=Path(__file__).resolve().parent;R=H.parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x',encoding='utf8') as f:json.dump(x,f,ensure_ascii=False,indent=2)
def put(p,b):
    with p.open('xb') as f:f.write(b)
def main():
    if sys.argv[1]=='prepare':
        put(H/'停止前根进度快照.md',(R/'当前进度与下一步.md').read_bytes());save(H/'manifest.json',{str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name not in ('manifest.json','stopped_verify.log','verification_receipt.json','completion_manifest.json')});print('Prepared static-import stop manifest; no production seal or PASS created.')
    else:
        log=(H/'stopped_verify.log').read_text(encoding='utf8');assert 'ALL PASS V02 STATIC-IMPORT STOP PACKAGE ONLY' in log
        for name,h in read(H/'manifest.json').items():assert sha(H/name)==h,name
        save(H/'verification_receipt.json',dict(status='PASS_STATIC_IMPORT_STOP_PACKAGE_ONLY',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),verify_script='verify_stopped_v02.py',verify_log_sha256=sha(H/'stopped_verify.log'),verified_manifest_sha256=sha(H/'manifest.json'),actual_entries=0,actual_cores=0,hypothesis_result='NOT_TESTED',A_syntax_files_passed=12,B_dynamic_imports=0,guard_proposal_applied=False))
        entry='''# 最新停止：侧向拓宽v0.2两处语法修复后，B静态发现worker导入副作用（2026-10-21）

PPCPP侧向拓宽开发诊断_v0.2_20261021已按授权仅修复analysis/verify两处字典语法，初始6输入与冻结参考二进制核对通过，原v0.1和冻结算法未改。实际复跑v0.1停止包verify通过；新版A项12活动源码逐一ast.parse全通过，来源表/最小diff保留，未继承旧seal/PASS。

B静态审查发现worker.py仍在模块顶层读取任务参数、安装审计hook，并有runtime.run_payload/p2_adapter.run_payload及写正式输出路径，无main守卫。该文件与v0.1字节相同，是新定位的既有启动结构风险；不声称已经执行求解。接续稿3B明确要求此时停并报告，不直接做有副作用导入，因此在动态导入前阻断，未删必需worker导入或伪造inventory测试来放行。

真实入口/核心0/306，B动态/C合成/两负向夹具/新版八统计桩均0；预检总PASS、seal1/seal2和正式结果未创建，真实历史/事件输入0，假设仍NOT_TESTED。附worker_main_guard_PROPOSAL_NOT_APPLIED.diff，仅建议将原任务体放入main守卫，body AST不变，尚未应用/未运行；须负责人裁决新增入口结构修复后才能接续，不以两处字典修复授权绕过3B停止条件。

停止包专用verify_stopped_v02实际通过旧证据hash/最小修复/12语法记录/静态风险/未应用提案/306未运行账；stopped_verify.log、verification_receipt及manifest保留，不代表总预检或研究实验通过。普通图搜索/新规划/P2/LAST/覆盖精确/留出均0，未自动重试、未创建后继实验或Git提交推送。先看本目录B静态预检停止报告.md及review_packet.md，封存等待审核。

---

'''
        p=R/'当前进度与下一步.md';old=p.read_text(encoding='utf8');assert not old.startswith('# 最新停止：侧向拓宽v0.2两处语法修复后')
        p.write_bytes((entry+old).encode('utf8'));put(H/'停止后根进度快照.md',(entry+old).encode('utf8'))
        save(H/'completion_manifest.json',dict(files={str(p.relative_to(H)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name!='completion_manifest.json'},note='Primary manifest excludes itself, verify log/receipt and completion manifest to avoid self reference. This scope includes all except itself; root progress only via snapshots.'))
        for name,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/name)==h,name
        print('SEALED B_STATIC stop; original evidence retained; root progress updated; actual entries0/306; guard proposal UNAPPLIED.')
if __name__=='__main__':main()
