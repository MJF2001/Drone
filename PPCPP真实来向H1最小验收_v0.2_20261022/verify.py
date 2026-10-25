"""Saved-data-only audit of reuse and continuation; never import/run a core."""
from pathlib import Path
import json,hashlib
from independent_audit import audit_output,equivalence

HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'PPCPP真实来向H1最小验收_v0.1_20261022'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    frozen=read(HERE/'freeze.json')
    for rel,digest in frozen['package_files'].items():assert sha(HERE/rel)==digest,('frozen package changed',rel)
    bind=read(HERE/'准备与旧包绑定.json');old_manifest=read(OLD/'completion_manifest.json')
    assert sha(OLD/'completion_manifest.json')==bind['old_manifest_sha256']
    for rel,digest in old_manifest['files'].items():assert sha(OLD/rel)==digest,('old sealed artifact changed',rel)
    assert read(OLD/'124槽实际账.json')[0]['status']=='failed' and read(OLD/'status.json')['attempted']==1
    for rel,row in bind['algorithm_bindings'].items():assert sha(HERE/rel)==sha(Path(row['source']))==row['sha256']
    for path,digest in read(HERE/'原来源hash.json').items():assert sha(Path(path))==digest
    assert sha(OLD/'tech/attempt_1_result.json')==bind['legacy_gate_result_sha256']
    rounds=[read(p) for p in sorted((HERE/'repair_rounds').glob('round_*_result.json'))];assert 1<=len(rounds)<=3 and rounds[-1]['passed']
    reuse=read(HERE/'reuse/slot_001_reaudit.json');source=Path(reuse['source_path']);assert sha(source)==reuse['source_sha256']
    old=read(source);assert old['passed'] is False
    reaudit=audit_output(old['input'],old['job']['heading'],old['entry']['raw']['branches']['P0'],False)
    assert all(x['audit']==reaudit for x in reuse['audits']);saved_audits=1
    plan=read(HERE/'计划_124槽.json')['jobs'];ledger=read(HERE/'124槽接续实际账.json');assert len(plan)==len(ledger)==124
    assert ledger[0]['status']=='reused_saved_reaudited' and ledger[0]['old_status']=='failed'
    started=[json.loads(line) for line in (HERE/'attempts.jsonl').read_text(encoding='utf8').splitlines() if json.loads(line)['event']=='started']
    assert len(started)<=123 and [x['slot'] for x in started]==list(range(2,len(started)+2))
    outputs={};accounts={};warm=0;markers_core=0
    for j,s in zip(plan[1:],ledger[1:]):
        assert j['id']==s['id'] and j['slot']==s['slot']
        p=HERE/'outputs'/(j['id']+'.json');markers=HERE/'logs'/(j['id']+'_markers.jsonl')
        if s['status']=='not_run':assert not p.exists() and not markers.exists();continue
        if markers.exists():
            rows=[json.loads(line) for line in markers.read_text(encoding='utf8').splitlines()]
            warm+=sum(x['tag']=='warm_entry_started' for x in rows);markers_core+=sum(x['tag']=='core_started' for x in rows)
        if not p.exists():assert s['status']=='failed';continue
        result=read(p);outputs[j['id']]=result;assert result['job']==j
        assert result['source_input_sha256']==sha(HERE/j['input'])
        assert hashlib.sha256(result['request_utf8'].encode('utf8')).hexdigest()==result['request_sha256']
        req=json.loads(result['request_utf8'])
        if j['method']=='H1':assert 'previous' not in req and req['incoming_heading']==j['heading']
        else:assert req==result['input']
        for path,digest in result['loaded_source_hashes'].items():assert sha(Path(path))==digest
        for key,value in result['accounts'].items():accounts[key]=accounts.get(key,0)+value
        if s['status']=='passed':
            assert result['passed'] and result['entry']['eligible'] and result['entry']['entry_seconds']<20
            audit=audit_output(result['input'],j['heading'],result['entry']['raw']['branches']['P0'],j['method']=='H1')
            assert audit==result['audit'];saved_audits+=1
    assert accounts.get('core_started',0)==markers_core
    assert sum(s['status'] not in ('not_run','reused_saved_reaudited') for s in ledger)==len(started)
    pairs=read(HERE/'54等价证据.json');diags=read(HERE/'16斜向技术证据.json')
    for row in pairs:
        if row['original_origin']=='v0.1_return_reaudited_v0.2':a=dict(entry=old['entry'],audit=reaudit);assert row['original_source_sha256']==sha(source) and row['same_run_timing_pair'] is False
        else:a=outputs['legacy__'+row['case']+'__ORIGINAL']
        b=outputs['legacy__'+row['case']+'__H1'];assert equivalence(a['entry']['raw']['branches']['P0'],b['entry']['raw']['branches']['P0'])
        assert a['audit']['credits']==b['audit']['credits'] and a['audit']['decisions']==b['audit']['decisions']
    for row in diags:
        j=plan[row['slot']-1];a=outputs[row['reference_id']];b=outputs[j['id']]
        assert equivalence(a['entry']['raw']['branches']['P0'],b['entry']['raw']['branches']['P0'])
    accepted=len(pairs)==54 and len(diags)==16 and all(s['status']=='passed' for s in ledger[1:])
    if (HERE/'completion_manifest.json').exists():
        manifest=read(HERE/'completion_manifest.json')
        for rel,digest in manifest['files'].items():assert sha(HERE/rel)==digest,('sealed artifact changed',rel)
        for stage in ('before','after'):
            name='根进度_执行前快照.md' if stage=='before' else '根进度_执行后快照.md'
            assert sha(HERE/name)==manifest['root_progress_'+stage+'_sha256']
    print(json.dumps(dict(file_and_saved_audit_verification=True,acceptance_target_passed=accepted,new_attempted=len(started),new_warm_entries=warm,
        historical_entries=1,cross_version_attempts=len(started)+1,reused_results=1,legacy_pairs=len(pairs),diagonal_entries=len(diags),new_accounts=accounts,
        added_by_this_verify=dict(saved_route_audits=saved_audits,core_calls=0,planning_entries=0,graph_searches=0,LOS_queries=0),
        legacy_slot1_still_failed=True,live_root_equality_required=False,sealed=(HERE/'completion_manifest.json').exists()),ensure_ascii=False))

if __name__=='__main__':main()
