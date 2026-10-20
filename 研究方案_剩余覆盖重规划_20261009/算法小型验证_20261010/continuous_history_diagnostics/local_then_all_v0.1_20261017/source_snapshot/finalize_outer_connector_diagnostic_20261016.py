"""Supplemental saved-input replay, acceptance checks, and descriptive figure."""
import copy,json
from pathlib import Path
from run_outer_connector_diagnostic_20261016 import ROOT,BASE,INPUT,OUT,A,read,write,sha,manifest
from verify_outer_connector_diagnostic_20261016 import VERIFY,normalize
def main():
    manifest(INPUT);manifest(OUT);manifest(VERIFY)
    protocol=read(OUT/'protocol.json');assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    replay=BASE/'inputs_saved_reference_replay_v0.1_20261016';replay.mkdir(exist_ok=False)
    records=read(INPUT/'records.json');matches=[];acceptance_checks=[]
    import portable_frozen
    from road_range_candidate_20261015 import digest
    for e in records:
        c=copy.deepcopy(read(Path(e['source_case'])))
        if e['reference']=='P2_REF':c['old_route']=read(Path(e['saved_preparation']))['raw']['route']
        dest=replay/Path(e['case']).name;write(dest,c)
        assert sha(dest)==e['case_sha256'];matches.append(dict(case=dest.name,sha256=sha(dest),matched=True))
    for j in protocol['jobs']:
        p=OUT/'runs'/(j['run_id']+'.json')
        if not p.exists() or read(p)['worker_status']!='returned' or j['method']=='P2_MULTI':continue
        raw=read(p)['raw'];d=raw['detail'];e=next(e for e in records if e['case']==j['case'])
        if raw['route']:
            assert d['acceptances'] and d['acceptances'][-1]['route_sha256']==digest(raw['route'])
            assert d['acceptances'][-1]['label']==raw['source']
        if raw['core_route']:
            assert d['core_acceptances'] and d['core_acceptances'][-1]['route_sha256']==digest(raw['core_route'])
            assert all(a['steps']>b['steps'] for a,b in zip(d['core_acceptances'],d['core_acceptances'][1:]))
        assert all(a['steps']>b['steps'] for a,b in zip(d['acceptances'],d['acceptances'][1:]))
        stages=list(d['stages'].values());assert stages==sorted(stages) and all(0<=v<=raw['seconds'] for v in stages)
        acceptance_checks.append(dict(run_id=j['run_id'],selected_matches_acceptance=True,core_matches_acceptance=True,stages_monotonic=True))
    write(replay/'completion.json',dict(cases=len(matches),all_match=True,optimization_calls=0,holdout_used=False))
    write(replay/'sha256.json',{str(p.relative_to(replay)):sha(p) for p in replay.rglob('*') if p.is_file()})
    write(VERIFY/'supplementary_record.json',dict(input_replay=matches,acceptance_checks=acceptance_checks,
        outside_identical=sum(e['segments']['LITERAL']==e['segments']['RECONNECT'] for e in records),
        no_additional_solves=True,holdout_used=False))
    write(VERIFY/'supplement_sha256.json',{'supplementary_record.json':sha(VERIFY/'supplementary_record.json')})
    print('20 saved-input hashes replayed; acceptance/stage checks:',len(acceptance_checks))
def figure():
    from PIL import Image,ImageDraw,ImageFont
    records=read(INPUT/'records.json');rows=[json.loads(v) for v in (OUT/'execution_ledger.jsonl').read_text(encoding='utf-8').splitlines()]
    lookup={(r['case'],r['budget'],r['method']):r for r in rows}
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20);title=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',27)
    im=Image.new('RGB',(1490,1070),'white');d=ImageDraw.Draw(im)
    d.text((25,18),'B1 开发诊断：20输入逐项结果（步数越小越好）',font=title,fill='#162b45')
    d.text((25,61),'固定R_PLUS1端点/责任点顺序；20项外部段逐点相同，理论节省均为0。非留出结果。',font=font,fill='#333333')
    cols=[25,390,535,665,795,945,1075,1205,1350]
    headers=['地图 / 参考','外部省步','1s 字面','1s 重连','1s P2','20s 字面','20s 重连','20s P2','有效']
    for x,h in zip(cols,headers):d.text((x,105),h,font=font,fill='#162b45')
    for i,e in enumerate(records):
        y=145+i*41
        if i%2==0:d.rectangle((15,y-2,1470,y+37),fill='#edf3f8')
        vals=[e['map_id'].replace('_development','')+' / '+e['reference'],'0']
        vals += [str(lookup[e['case'],b,m]['steps']) for b in (1,20) for m in ('LITERAL','RECONNECT','P2_MULTI')]
        vals += [str(sum(lookup[e['case'],b,m]['valid'] for b in (1,20) for m in ('LITERAL','RECONNECT','P2_MULTI')) )+'/6']
        for x,v in zip(cols,vals):d.text((x,y),v,font=font,fill='#202d3d')
    d.text((25,993),'注意：20输入来自10地图；两参考不共享同总准备预算；同预算时序差异不是几何节省。',font=font,fill='#333333')
    dest=VERIFY/'all_case_steps.png';im.save(dest);write(VERIFY/'figure_sha256.json',{'all_case_steps.png':sha(dest)})
    print(dest)
def check():
    from run_outer_connector_diagnostic_20261016 import route_check
    from verify_outer_connector_diagnostic_20261016 import check_inputs
    checks=check_inputs()
    for p in (INPUT,OUT,VERIFY,BASE/'inputs_saved_reference_replay_v0.1_20261016'):manifest(p)
    for name in ('supplement_sha256.json','figure_sha256.json'):
        assert all(sha(VERIFY/n)==h for n,h in read(VERIFY/name).items())
    protocol=read(OUT/'protocol.json');assert all(sha(Path(p))==h for p,h in protocol['protected_hashes'].items())
    valid=cores=0
    for j in protocol['jobs']:
        p=OUT/'runs'/(j['run_id']+'.json')
        if not p.exists() or read(p)['worker_status']!='returned':continue
        c=read(Path(j['case']));raw=read(p)['raw']
        if raw['route']:assert route_check(c,raw['route'])['valid'];valid+=1
        if raw.get('core_route'):assert route_check(c,raw['core_route'])['valid'];cores+=1
    print(json.dumps(dict(read_only=True,input_checks=len(checks),valid_final=valid,valid_core=cores,protected=len(protocol['protected_hashes']),all_hashes_match=True,holdout_used=False)))
if __name__=='__main__':
    import sys
    if '--check' in sys.argv:check()
    elif '--figure' in sys.argv:figure()
    else:main()
