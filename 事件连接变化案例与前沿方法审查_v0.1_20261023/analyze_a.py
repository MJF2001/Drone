"""Saved-path summaries and drawings only; geometry budget already consumed once."""
from stage_a import H,R,OFF,HIST,read,dump,sha,ps,source
from collections import Counter
from datetime import datetime,timezone
import json,math
from PIL import Image,ImageDraw,ImageFont
FONT='C:/Windows/Fonts/msyh.ttc'
def font(n):return ImageFont.truetype(FONT,n)
def pct(x):return f'{100*x:.3f}%'
def plot(case,details,path):
    c=case['after'];before=case['before'];F=ps(c['free']);T=ps(c['published_targets']);old=ps(before['published_targets']);hist=ps(c['covered']);removed=ps(case['registration']['free_removed']);new=T-old
    im=Image.new('RGB',(1560,1000),'white');d=ImageDraw.Draw(im)
    d.text((30,15),case['id']+' / '+case['label'],font=font(27),fill='#182942')
    d.text((30,60),'三seed状态等权差 '+pct(case['registration']['state_equal']['B_C_distance_extra'])+'；图固定原首seed '+str(case['registration']['plot_seed']),font=font(21),fill='#182942')
    for panel,v in enumerate(('B','C')):
        x=details[v];pathpts=x['executed_path'];xs=[q[0] for q in F];ys=[q[1] for q in F];xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys)
        scale=min(680/(xmax-xmin+1),570/(ymax-ymin+1));offset=panel*780
        def xy(q):return offset+45+(q[0]-xmin+.5)*scale,750-(q[1]-ymin+.5)*scale
        d.text((offset+30,110),v+(' PPCPP＋直达' if v=='B' else ' P2＋同版直达'),font=font(25),fill='#182942')
        for p in F|removed:
            a=xy((p[0]-.5,p[1]+.5));b=xy((p[0]+.5,p[1]-.5));d.rectangle((*a,*b),fill='#eaf0f6' if p in F else '#333333',outline='#dfe6ed')
        for p in T:
            x0,y0=xy(p);r=max(2,min(4,scale*.15));d.ellipse((x0-r,y0-r,x0+r,y0+r),fill='#e29835' if p in new else '#aaa' if p in hist else '#7191bd')
        d.line([xy(p) for p in pathpts],fill='#1168bd' if v=='B' else '#07806a',width=2)
        for s in case['geometry']:
            if s['kind']=='old_saved_suffix' or v=='B':d.line([xy(s['a']),xy(s['b'])],fill='#ba3aa6' if s['kind']=='old_saved_suffix' else '#de4949',width=4)
        for p,col in ((c['current'],'#c83131'),(c['base'],'#17263c')):
            x0,y0=xy(p);d.ellipse((x0-6,y0-6,x0+6,y0+6),fill=col)
        m=x['metrics'];d.text((offset+30,785),f"距离 {m['length']:.6f} m；共同端到端 {x['common_time_seconds']:.6f} s",font=font(20),fill='#182942')
        d.text((offset+30,825),'原锁定末格 '+str(x['locked_anchor_order'][-1])+'；实际末信用 '+str(x['actual_new_credit_order'][-1]),font=font(18),fill='#182942')
    d.text((30,885),'灰点已采、橙点新增任务、黑格新公开障碍；紫线=已登记旧后缀段，红线=已登记B现有段。',font=font(21),fill='#182942')
    d.text((30,930),'图只画保存路线；12线段前后合法性全相同，不把总差距归给其中一条边，不证明事件致顺序失配。',font=font(20),fill='#182942')
    im.save(path)

def main():
    assert not (H/'A_conclusion_freeze.json').exists()
    reg=read(H/'case_registry.json');geo=read(H/'geometry_receipt.json');cases=[];table=[]
    for r in reg['cases']:
        ident=r['case'];seed=r['plot_seed'];before=read(r['before_map_source']);c=read(r['after_source']);gr=[x for x in geo['records'] if x['case']==ident];gap=r['state_equal']['B_C_distance_extra']
        direct=any(x['visibility_changed'] and x['relation_label']!='new_task_relation_not_old_task_connection' for x in gr)
        label='无支持/反例' if gap<=0 else '直接连接变化证据' if direct else '仅事件后关联'
        allseeds=[];plotdetail={}
        for pair in r['all_three_seed_pairs']:
            per={'seed':pair['seed'],'paired_OFF_metrics':pair,'methods':{}}
            for method,view in (('PPCPP','B'),('P2_MULTI','C')):
                x,file=source(ident,pair['seed'],method);events=x['views'][view]['events'];sequence=[e['cell'] for e in events if e['new']]
                data={'source':str(file),'sha256':sha(file),'locked_anchor_order':[e['point'] for e in x['post']['locked_nominal_anchors']],
                    'locked_anchor_definition':'first visits to remaining target centers on raw route; wrapper anchors, NOT claimed P2 optimizer internal final visit order',
                    'actual_new_credit_order':sequence,'credit_order_definition':'first credited segment, midpoint witness ordering within segment, not unique physical first interior time',
                    'internal_P2_final_visit_sequence':None if method=='P2_MULTI' else 'not_applicable',
                    'internal_P2_order_status':'not saved in native result; cannot infer from route after incidental service/skipping' if method=='P2_MULTI' else 'PPCPP decisions available in trace',
                    'PPCPP_decision_trace':x['native']['raw'].get('trace',[]) if method=='PPCPP' else None,
                    'raw_path':x['native']['raw']['route'],'executed_path':x['views'][view]['path'],'saved_connection_edges':x['post']['edges'],
                    'metrics':x['views'][view]['metrics'],'common_time_seconds':x['timing']['combined_end_to_end'],'native_seconds':x['timing']['native_entry_seconds'],
                    'post_increment_seconds':x['timing']['post_increment'],'return_part_saved':next((p for p in x['post']['parts'] if p['kind']=='last_to_base'),None),
                    'termination':x['timing']['termination'],'saved_independent_pass':x['independent']['passed'],'initial_collect_here':x['initial_collect_here']}
                per['methods'][view]=data
                if pair['seed']==seed:plotdetail[view]=data
            per['wrapper_anchor_orders_equal']=per['methods']['B']['locked_anchor_order']==per['methods']['C']['locked_anchor_order']
            per['first_credit_orders_equal']=per['methods']['B']['actual_new_credit_order']==per['methods']['C']['actual_new_credit_order']
            allseeds.append(per)
        case={'id':ident,'registration':r,'before':before,'after':c,'geometry':gr,'label':label,'direct_connection_change_on_registered_segments':direct,
            'claim_event_caused_order_mismatch':False,'all_seed_saved_evidence':allseeds,'knowledge_source_verified_actual_prep_input':True,
            'interpretation':'obstacle removes free cells but registered saved connections unchanged; relative route gap alone is not event causality' if r['slot']['event']=='obstacle' else 'free domain unchanged; new tasks were not public before event; insertion relation is new responsibility, not loss of old geometric visibility'}
        dump(H/'case_records'/(ident+'.json'),case);cases.append(case)
        plot(case,plotdetail,H/'figures'/(ident+'.png'))
        table.append('|'+ '|'.join([ident,','.join(z['role'] for z in r['roles']),pct(gap),str(len(r['free_removed'])),str(len(r['new_published_targets'])),label])+'|')
    result={'cases':[{'id':c['id'],'label':c['label'],'direct_registered_connection_change':c['direct_connection_change_on_registered_segments'],'state_equal_gap':c['registration']['state_equal']['B_C_distance_extra']} for c in cases],
        'geometry':geo['counts'],'fixed_segment_pairs':12,'changed':sum(s['visibility_changed'] for s in geo['records']),
        'stageA_conclusion':'No registered direct visibility change. Four positive relative gaps are post-event associations; two nonpositive cases are counterexamples. No evidence sufficient to attribute sequence mismatch to event connection change.',
        'hypothesis_status':'do not implement or retain event-connection-loss-triggered selective reordering as a supported main mechanism on this evidence; general route-improvement possibility remains unresolved',
        'new_core_calls':0,'new_path_searches':0,'new_candidates':0,'new_routes':0,'stage_B_must_still_run':True}
    dump(H/'stageA_summary.json',result)
    report='''# 阶段A：正反例审查（先固定，后检索）

数值只来自当前OFF全量包，先完整54状态同seed配对，再按三seed状态等权选例。最多6例、12现有线段已在case_registry及A_registration_freeze里于几何/联网前登记；不因没有正例换例。额外不同几何的判据为原base_id，排除前四例全部已选基础几何，再按障碍/扩展顺序选最大差距者。每图固定原plan首seed20261020；三seed全部原数、路线、名义锚点/信用/决策缺口保留case_records。

|状态|预定角色|B/C状态等权多走|删自由格|新增公开任务|证据档|
|---|---|---:|---:|---:|---|
'''+ '\n'.join(table)+'''

**核心结论：12条已登记线段在前后公开自由域均合法，24次单域判定、可见性变化0。** 此外真实几何计算的闭障碍盒检测次数见geometry_receipt，不能称零计算。4个B更长状态只支持事件后的路线质量关联，2个等长状态是反例；当前不能断言“事件改变连接，导致PPCPP顺序失配”，也不能将总差距归给其中一边。停止把这个触发直觉当已获证据的新主机制，仍按稿完成阶段B有限检索。

事件前地图不是假设的完整真值：逐例追溯原prep/inputs及实际prep result.job.input、runtime_reads，确认旧算法当次确实读取该份自由域与目标。旧规划真实保存返回、采用前缀与当前old_route后缀逐项相等，源hash保留。它们是已运行仿真规划和采用的格心历史前缀，不是新规则自然连续执行或实机轨迹。

三障碍例自由域删格2/8/2，但按预定规则扫描保存旧后缀未找到端点落在删格的旧单元边，登记回退首边；不能事后另搜一条受影响边。三扩展例自由域F前后相同，新增任务6或48格在原已知可飞矩形中；任务公开变化不等于旧连接变不可行。B选段若端点属新公开任务，明确标新增任务关系，不把该目标视作事件前已有责任。12段都合法不证明其他所有连接或最短距离均未变，本轮没有做全图可见性枚举或最短路搜索。

名义锚点顺序与首次信用分开：B/C post.locked_nominal_anchors是原路线首次格心服务顺序，属于共同后处理的锁定名义锚点；PPCPP另有trace决策。P2没有保存优化器最终内部visits序列，不能由含途中采集/跳过的展开路线逆推，因此原始P2名义优化顺序明确未核实。实际信用按保存首次相交段/内部中点见证顺序列，不冒充唯一物理首次内部时刻。

每例case_records列共同当前任务/历史/资源（资源1000000米为给定上限，非真实能耗）、S/来向/捕食者/基地、前后输入及地图hash、B/C锚点和信用序列、全部现有连接、完整总距离/末段返航及时间来源。总距离差同时受覆盖顺序、衔接、收尾/返航影响，不存在本轮已验证的单边因果分解。三seed数值全部保留，不把首seed图当全状态结论。

## 与旧尝试的关系

|旧尝试|这次假设的相同点/可能区别|本轮裁决|
|---|---|---|
|固定窗口局部P2|同样想按事件局部少改；若仍固定窗口＋P2则实质重合|旧窗口已关闭；本轮没有证明新的触发或邻域|
|首次新旧竞争单步|按新/旧目标区别干预访问选择；新目标端点不等于旧连接坏|不能重启已在新开发批失败的固定单步规则|
|恢复入口/FIRST/SECOND/STRUCT|少量入口完整试走、选择完整路线已有|“少候选择短”不能重新命名为贡献|
|LAST|保留/改变末采集位置以影响返航已有|总差距不能忽略末采集与返航，也不自动重启LAST|
|四方向|多个方向候选完整择短已有|当前顺序差不证明需要四方向或组合预算再试|
|普通2-opt|通用访问次序局部搜索已在P2，完整route重接亦有先例|若机制最终只是普通2-opt/ALNS或几何连接更新，只能先称工程组合|

阶段B可以检索动态/增量覆盖及有限选择性改进，但不得让新论文反过来改动这些案例或把关联升级为因果。当前主算法/原创机制仍未确认，本阶段算法/核心/候选/路径搜索/新路线/闭环0。

## 固定现有路线图

'''+ '\n\n'.join('!['+c['id']+']('+(H/'figures'/(c['id']+'.png')).as_posix()+')' for c in cases)+'\n'
    (H/'01_阶段A固定正反例结论.md').write_text(report,encoding='utf-8')
    dump(H/'A_conclusion_freeze.json',{'fixed_before_web':True,'utc':datetime.now(timezone.utc).isoformat(),'files':{str(p.relative_to(H)):sha(p) for p in [H/'case_registry.json',H/'geometry_receipt.json',H/'stageA_summary.json',H/'01_阶段A固定正反例结论.md',*list((H/'case_records').glob('*.json')),*list((H/'figures').glob('*.png'))]},'new_core_calls':0})
    print(result)

if __name__=='__main__':main()
