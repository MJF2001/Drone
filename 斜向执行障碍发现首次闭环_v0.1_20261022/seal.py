"""Receipt/file checks and seal only. No geometry, solver or saved route auditing."""
from collections import Counter
import json
from loop_utils import HERE,ROOT,read,dump,sha,now

def main():
    assert not (HERE/'final_receipt.json').exists(),'already sealed'
    freeze=read(HERE/'real_freeze.json')
    for relative,digest in freeze['files'].items():
        assert sha(HERE/relative)==digest,('real_frozen_changed',relative)
    for path,digest in read(HERE/'external_source_guards.json').items():
        assert sha(path)==digest,('old_changed',path)
    batch=read(HERE/'batch_receipt.json')
    verify=read(HERE/'verification_runs/verify_1.json')
    assert verify['passed'] and not batch['stopped_on_exception'] and batch['not_run']==[]
    assert len(batch['attempted'])==6 and all(x['passed'] for x in batch['attempted'])
    reg=read(HERE/'registration.json')
    native=Counter();diagonal=0;linkchecks=[]
    for job in reg['jobs']:
        session=read(HERE/'sessions'/(job['id']+'.json'))
        assert session['passed'] and session['completed'] and len(session['plans'])==2
        native.update(session['native_counts'])
        diagonal+=session['independent_execution']['interior_diagonal_detections']
        for row in session['plans']:
            plan=read(HERE/row['file']);ident=row['id']
            assert plan['passed']
            assert read(HERE/row['input'])==plan['snapshot']
            core=read(HERE/'calls'/(ident+'_native_return.json'))
            post=read(HERE/'calls'/(ident+'_post_return.json'))
            assert core['request_utf8']==plan['core_request_utf8'] and core['response']==plan['native_entry']
            assert post['request_utf8']==plan['post_request_utf8']
            assert post['response_utf8']==plan['post_response_utf8'] and post['envelope']==plan['post_envelope']
            assert 'O_truth' not in plan['core_request_utf8'] and 'F_nominal' not in plan['core_request_utf8']
            linkchecks.append({'id':ident,'raw_core_and_post_linked':True,'public_request_sha256':plan['core_request_sha256'],
                              'saved_native_return_sha256':sha(HERE/'calls'/(ident+'_native_return.json')),
                              'saved_post_return_sha256':sha(HERE/'calls'/(ident+'_post_return.json'))})
    assert native['core_started']==native['core_returned']==native['core_complete']==12
    assert diagonal==2
    for w in reg['worlds']:
        for suffix in ('.png','.svg'):
            assert (HERE/'figures'/(w['id']+'_实际路线'+suffix)).is_file()
    dump(HERE/'保存返回关联与封存检查.json',{'utc':now(),'checks':linkchecks,'frozen_files_unchanged':len(freeze['files']),
        'old_guard_records':len(read(HERE/'old_files.json')),'new_core_calls':0,'new_geometry_queries':0,
        'new_distance_queries':0,'new_service_queries':0,'figures_visually_inspected':3})
    prefix='''# 最新完成：首次隐藏障碍发现闭环六会话通过，已封存停止（2026-10-22）

斜向执行障碍发现首次闭环_v0.1_20261022 已按稿完成。先看 00_通俗报告与闭环结果.md、三世界实际路线图及 review_packet.md；最终收据 final_receipt.json。十二类纯探测/执行门槛首轮全通过，12纯会话/固定响应，真实核心0。世界、1/8 L∞ 带和执行器在真实求解前固定，未追路线挪障碍。

正式3世界×H1/P2共6会话全部完成可检目标并实际返航，12真实核心开始/返回/完成（H1 6、P2 6），达到上限即停；失败/中止/未运行0，无修补补跑。每会话发现1个初始已存在隐藏障碍、从真实S重规划1次，事件不是任意时刻生成。六发现中W3两次为斜段内停止：H1 (11/8,21/16)、P2 (21/8,11/16)，四次轴向。独立解析回放未发现碰障、漏检、信用/距离错误；只在本技术模型和六例范围内成立。

W1各采9/暂缓1，实际长度均12.75；W2各采5/暂缓0，均43/4+√10≈13.912278；W3各采4/暂缓1，H1≈16.025437、P2≈14.025437。工作量分列，不能推普遍优劣或创新。遮挡目标留P/D，不算H；距离仅实飞57条非零段，未把中断预测长度累加。实际63动作、12等待；规划器只收当前公开乐观F与实际账，真值分离。

真实直达12次，source/candidate/output几何120/105/67；图搜索133＝context BFS12＋距离行BFS29＋A*92，内部审核162合法。公开主几何340/距离328/服务609，执行主盒95/真值几何63/距离63/服务144；运行时独立公开几何407/距离340/服务2228，执行独立盒95/几何63/距离63/服务405。首连接74候选含6零接入，12管线均在30秒内，不作速度比较。保存verify通过12计划、6实飞、12纯夹具，新增独立几何483/距离417/服务2652、盒124，核心/选择器/后处理/图搜索0；再次审核另记新查询。

旧源码/输入/结果保护不变，1277旧文件记录；已验收核心、奖励、首连接/直达数值与预算保留。仅初始化及动态状态包装独立适配，审核唯一模块身份前后稳定。新执行链不代表一般无理停点、任意时刻事件、现场传感/制动或安全、全未知探索、论文创新/性能优势。留出未用、无扩展/第二事件/优化批或推送。封存后停止交负责人审核。

---
'''
    root=ROOT/'当前进度与下一步.md'
    before=root.read_bytes()
    assert before==(HERE/'root_before.md').read_bytes(),'concurrent root edit; preserve and resolve before sealing'
    root.write_text(prefix+'\n'+before.decode('utf-8-sig'),encoding='utf-8')
    (HERE/'root_after.md').write_bytes(root.read_bytes())
    dump(HERE/'root_progress_update.json',{'utc':now(),'root_path':str(root),'before_sha256':sha(HERE/'root_before.md'),
        'after_sha256':sha(HERE/'root_after.md'),'historical_snapshots_only':True})
    files={str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.rglob('*')) if p.is_file()
           and not p.is_relative_to(HERE/'verification_runs') and p.name not in ('manifest.json','final_receipt.json')
           and '__pycache__' not in p.parts}
    dump(HERE/'manifest.json',{'utc':now(),'files':files,'mutable_additional_verification_receipts':'verification_runs/'})
    for relative,digest in files.items():
        assert sha(HERE/relative)==digest
    receipt={'utc':now(),'status':'COMPLETE_FINITE_CLOSED_LOOP_VERIFIED_SEALED_STOP','passed':True,
        'completed_sessions':6,'failed_sessions':0,'not_run':0,'real_core_calls':12,'core_cap':12,
        'discoveries':6,'interior_diagonal_discoveries':2,'replans_from_real_stops':6,
        'technical_rounds':1,'technical_sessions':12,'fixed_stub_responses':12,
        'saved_verify_passed':True,'first_verify_file':'verification_runs/verify_1.json',
        'first_verify_sha256':sha(HERE/'verification_runs/verify_1.json'),
        'manifest_sha256':sha(HERE/'manifest.json'),'sealed_files':len(files),'frozen_files_unchanged':len(freeze['files']),
        'old_guard_records':len(read(HERE/'old_files.json')),'seal_new_core_calls':0,'seal_new_geometry_queries':0,
        'saved_verify_counts':verify['counts'],'stopped_for_owner_review':True,'no_additional_batches':True}
    dump(HERE/'final_receipt.json',receipt)
    assert sha(HERE/'manifest.json')==read(HERE/'final_receipt.json')['manifest_sha256']
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':
    main()
