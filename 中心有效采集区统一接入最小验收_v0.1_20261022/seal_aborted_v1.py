"""Single writer for aborted seal. Structural hashes only, no geometry queries."""
import json
from center_credit_v01_20261022.utils import HERE,ROOT,read,dump,sha,now

def main():
    assert not (HERE/'final_receipt.json').exists()
    freeze=read(HERE/'real_freeze.json')
    for name,digest in freeze['files'].items():
        assert sha(HERE/name)==digest,('runtime_changed',name)
    guards=read(HERE/'external_source_guards.json')
    for path,digest in guards.items():
        assert sha(path)==digest,('old_changed',path)
    batch=read(HERE/'batch_receipt.json')
    gate=read(HERE/'technical_rounds/round_1/receipt.json')
    verify=read(HERE/'verification_runs/verify_1.json')
    replay=read(HERE/'readonly_failure_replay_v1.json')
    s=read(HERE/'sessions/W1_H1.json');p=read(HERE/'outputs/W1_H1_plan_1.json')
    assert not s['passed'] and not p['passed'] and p['main_passed']
    assert len(batch['attempted'])==1 and len(batch['not_run'])==5 and batch['stopped_on_exception']
    assert len(gate['sessions'])==35 and gate['passed'] and all(x['passed'] for x in gate['sessions'])
    assert s['native_counts']['core_started']==s['native_counts']['core_returned']==s['native_counts']['core_complete']==1
    assert s['native_counts']['post_entry_calls']==1 and s['final']['nonzero_segments']==s['final']['event_count']==0
    assert verify['passed'] and replay['reproduced_original_failure']
    core=read(HERE/'calls/W1_H1_plan_1_native_return.json')
    post=read(HERE/'calls/W1_H1_plan_1_post_return.json')
    assert core['request_utf8']==p['core_request_utf8'] and core['response']==p['native_entry']
    assert post['request_utf8']==p['post_request_utf8'] and post['response_utf8']==p['post_response_utf8']
    assert post['envelope']==p['post_envelope']
    assert 'O_truth' not in p['core_request_utf8']
    for row in read(HERE/'registration.json')['worlds']:
        for ext in ('.png','.svg'):
            assert (HERE/'figures'/(row['id']+'_注册与中止状态'+ext)).exists()
    dump(HERE/'封存结构检查.json',{'utc':now(),'runtime_frozen_files_unchanged':len(freeze['files']),
         'old_guard_records':len(read(HERE/'old_files.json')),'old_guard_distinct_paths':len(guards),
         'saved_raw_request_return_links':True,'failure_preserved':True,'figures_visually_inspected':4,
         'new_core_calls':0,'new_geometry_queries':0,'new_credit_queries':0})
    prefix='''# 最新中止：中心有效采集区纯门槛通过，首槽真实计数审核失败（2026-10-22）

中心有效采集区统一接入最小验收_v0.1_20261022 已按停止条件封存，先看00_通俗中止报告.md和review_packet.md，最终状态见final_receipt.json。分阶段：统一合同/必要适配代码完成，16类35个纯案例首轮通过（2个篡改负控制被拒绝，修复0轮），真实接入失败，真实闭环未验。不能把保存verify通过称为真实验收通过。

固定1米格/每轴严格偏移<1/5，实际前缀交区间及内部见证，不虚构开集首个内部点；零移动只显式采集、预测实际分离、事件先截断结算再更新知识。首连接/预测/直达责任/实际服务共同适配，独立解析审核；H1/P2格点核心、奖励、搜索、随机与预算保留，名义格心锚点仍可能冗余，未做跳过/顺序优化。旧模型结果不改、不混排。

只尝试W1_H1，真实核心开始/返回/完成1（P2 0）、直达1；主管线已完成约0.104595秒。独立审核最后查询数断言失败：观察器135=后处理引擎90＋主管线post_main_audit45，共用中心区函数和phase='post'导致统计范围混合。不是发现搜索或信用几何反例，但原槽passed=false保留。真实第一槽后正式代码未修改，没有修复/补跑，后五会话全部未运行；剩余11入口不自动消耗。

实际只有基地collect_here，S=(0,0)、h=null、H={(0,0)}、D空、E100/M0；移动/转弯/发现/重规划均0。完整返回及预测见证保存，没有提交未飞信用。真实不经格心斜段采集、发现后H接续均未验；纯C13证明手写斜段差异，不替代真实结果。

纯阶段主真值几何39＋首连接输入/候选1/25，主区域查询20，探测/安全盒43/46；独立几何69/距离68/区域查询29，点134/边参数64，盒45/48，含2个负审核；真实算法0。真实公开主几何31/距离30/区域查询144，直达几何10/10/10、区域90；实际盒2/真值几何1/距离1（零长度核算）。图搜索context BFS1＋A*1=2，内部审核2合法。观察器135已标混账，不当引擎查询数。

运行时独立Counter异常未持久化，已诚实留缺口。一次保存原冻结审核器重放复现同一断言，新增几何41/距离31/区域400、点877/边780；相同原运行计数只能标确定性重建，非原始计数。保存verify通过纯门槛与初始动作/失败保留，新增独立几何70/距离69/区域29、点144/边64、盒95；失败计划单列保留。两只读入口核心/选择器/后处理/搜索0，不改失败状态。

三世界注册/中止状态图及纯斜向正控制图、合同/diff/预期/日志/原返回/调用账/来源hash/只读verify已封存，正式代码和旧包原字节不变。仅独立报告导出修改过C13图的标题遮挡版式，首版和QA记录保留，未改正式程序或重求解。按稿停止交负责人审核，不自动接续、性能批、留出、相机/视觉实验或推送。

---
'''
    root=ROOT/'当前进度与下一步.md'
    before=root.read_bytes()
    assert before==(HERE/'root_before.md').read_bytes(),'concurrent root edit; preserve before review'
    root.write_text(prefix+'\n'+before.decode('utf-8-sig'),encoding='utf-8')
    (HERE/'root_after.md').write_bytes(root.read_bytes())
    dump(HERE/'root_progress_update.json',{'utc':now(),'before_sha256':sha(HERE/'root_before.md'),
         'after_sha256':sha(HERE/'root_after.md'),'historical_snapshots_only':True})
    files={str(f.relative_to(HERE)):sha(f) for f in sorted(HERE.rglob('*')) if f.is_file()
           and not f.is_relative_to(HERE/'verification_runs') and f.name not in ('manifest.json','final_receipt.json')
           and '__pycache__' not in f.parts}
    dump(HERE/'manifest.json',{'utc':now(),'files':files,'mutable_additional_verification_receipts':'verification_runs/'})
    for name,digest in files.items():
        assert sha(HERE/name)==digest
    receipt={'utc':now(),'status':'ABORTED_ON_FIRST_REAL_SLOT_COUNTER_SCOPE_FAILURE_SEALED_STOP',
       'passed':False,'artifact_integrity_verified':True,'technical_passed':35,'technical_classes':16,'technical_rounds':1,
       'technical_repairs':0,'audit_negative_controls_rejected':2,'attempted_real_sessions':1,
       'completed_real_sessions':0,'failed_real_sessions':1,'unrun_real_sessions':5,
       'real_H1_core_calls':1,'real_P2_core_calls':0,'real_core_calls':1,'real_post_calls':1,'unused_real_entry_cap':11,
       'actual_nonzero_segments':0,'actual_distance':'0','discoveries':0,'replans':0,
       'contract_complete':True,'pure_gates_passed':True,'real_integration_passed':False,'closed_loop_verified':False,
       'offcenter_diagonal_real_credit_verified':False,'runtime_files_unchanged':len(freeze['files']),
       'old_guard_records':len(read(HERE/'old_files.json')),'sealed_files':len(files),
       'saved_verify_passed':True,'first_verify_file':'verification_runs/verify_1.json',
       'first_verify_sha256':sha(HERE/'verification_runs/verify_1.json'),
       'saved_failed_auditor_replay_file':'readonly_failure_replay_v1.json',
       'saved_failed_auditor_replay_sha256':sha(HERE/'readonly_failure_replay_v1.json'),
       'manifest_sha256':sha(HERE/'manifest.json'),'stopped_for_owner_review':True,
       'no_runtime_fix_or_retry':True,'seal_new_core_calls':0,'seal_new_geometry_queries':0,
       'saved_verify_counts':verify['counts'],'saved_failure_replay_counts':replay['counts']}
    dump(HERE/'final_receipt.json',receipt)
    assert read(HERE/'final_receipt.json')['manifest_sha256']==sha(HERE/'manifest.json')
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':
    main()
