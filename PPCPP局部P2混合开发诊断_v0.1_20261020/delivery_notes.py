"""Final interpretation/explicit call ledger; no result or source replacement."""
from support import *
if __name__=='__main__':
 d=read(H/'analysis.json');g=read(H/'gate_index.json');gate_native=0;gate_local=0
 for path in g['records']:
  r=read(H/path);gate_native+=1;gate_local+=r['result']['raw'].get('internal_calls',{}).get('local_P2',0)
 evidence=[]
 for c in d['calls']:
  if c['method']!='LOCAL_P2' or c['local_steps'] is None:continue
  er=read(H/c['output'])['raw']['local'];stages={e['stage'] for e in er['events']};assert er['status']=='finished' and er['core_finished'] and {'H_generate','V_generate','core_finished','deep_finished','shuffle_1_expand'}<=stages
  evidence.append(dict(sequence=c['sequence'],source=er['source'],event_count=len(er['events']),core_finished=True,full_multi_finished=True))
 save(H/'call_ledger.json',dict(formal_entries=324,formal_native=d['internal_calls'],formal_core_total=sum(d['internal_calls'].values()),gate_entries=24,gate_native=dict(PPCPP=gate_native,local_P2=gate_local,global_P2=0),stub_tests=16,stub_real_solver_calls=0,history_solver_calls=0,gate_index_note='gate_index.internal_calls enumerates only counters present in hybrid raw; standalone PPCPP12 are added here for total24. No gate/raw output altered.',local_search_evidence=evidence))
 assert gate_native==24 and gate_local==10 and len(evidence)==102
 text='''# 结果解读与实际调用账

**本固定单窗口没有完整路程收益，未达到有限继续信号。已封存，待负责人审核。**

18事件按三种子均值求和：PPCPP=混合=1098，整体P2=1024.666667；混合比全局P2多73.333333步。18控制：PPCPP=混合=1086，整体P2=1032.666667，仍多53.333333步。两组相对原版均18状态全平（调用级各0短54平0长）；相对全局P2各0短18平36长。所有324调用完整合法及时，不是剔除失败后全平。

事件入口均值PPCPP4.884419ms/混合73.815933ms/整体P2526.055328ms；控制4.371213/88.893687/532.824502ms。混合比原版更慢而没有少步；相对整体P2更快但路线更长，不能据此说达到同预算路线优势。本轮不建议按本固定规则继续投入；是否重立问题由负责人决定，不自行扩窗。

102次非空窗局部P2全部完整finished，均保留其局部old_suffix：局部路线与原窗口长度相等，没有短/长变化；最终混合均保P0。不能说“只跑了保底，没有执行P2”：每次保留完整events，独立核到H/V生成、core_finished、deep_finished和shuffle_1_expand，完整multi阶段确实执行，见call_ledger.local_search_evidence。只说明有限搜索没有接受更短者，不能宣称局部窗口已证明最优。

事件/控制各51次非空、3次空窗；真实任务占比均1/7～1，步长占比事件0.065217～0.628205，控制0.065217～0.701493。任务占比可能达1，但仍固定入口出口和外部步数，不能把任务全包等同全局自由搜索。两组真实局部调用均无外部未采任务提前采集；该机制由显式强制路径桩检查，不伪造实际样本。

因此这批不能声称减少了连接/重复、没有新增采集前或返航收益，转弯与原PPCPP最终路线同值。全局P2差距继续存在；原因可能混合窗口、固定接口及保留外部PPCPP顺序，本轮未独立归因，不能推广为所有混合方案无效或障碍专用结论。

324正式入口不等于核心次数：原PPCPP入口108；混合108内含PPCPP108、局部P2102；整体P2入口108。正式核心合计426。真实门槛24入口包含PPCPP核心24、局部P210（共34）；16桩测试真实求解0；历史准备新增0。gate_index中internal_calls只计混合raw自带字段，因此未含独立PPCPP的12，完整账以单列call_ledger为准，历史原件未改。

基础设施两次失败都在实际求解前：初始审核同名导入冲突、首次门槛启动时异步环境尚未完成。原日志、后继加载器、补完封存后通过的24入口/16桩原件全部保留。没有正式失效或重跑。核验由独立audit重建任务/前后缀/出口/实际采集，未使用混合选窗函数作oracle。
'''
 with (H/'结果解读与调用账.md').open('x',encoding='utf-8') as f:f.write(text)
 print('Interpretation/call ledger written; no solver calls')
