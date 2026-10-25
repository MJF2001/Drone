"""Read saved results only: independent arithmetic/route audit, no core/search."""
from pathlib import Path
import sys,json,hashlib
from independent_audit import audit_output,equivalence

HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    frozen=read(HERE/'freeze.json')
    for rel,digest in frozen['package_files'].items():assert sha(HERE/rel)==digest,('frozen package changed',rel)
    for path,digest in read(HERE/'原来源hash.json').items():assert sha(Path(path))==digest,('source changed',path)
    inputs=read(HERE/'54输入来源清单.json');assert len(inputs)==54
    for item in inputs:assert sha(HERE/item['input'])==item['sha256']==sha(Path(item['source']))
    gates=[read(p) for p in sorted((HERE/'tech').glob('attempt_*_result.json'))]
    assert 1<=len(gates)<=3 and gates[-1]['passed'] and len(gates[-1]['cases'])==26
    assert all(len(v)<=4 for v in read(HERE/'技术门槛预登记.json')['classes'].values())
    for name,digest in gates[-1]['source_hashes'].items():assert sha(HERE/name)==digest
    plan=read(HERE/'计划_124槽.json')['jobs'];ledger=read(HERE/'124槽实际账.json');assert len(plan)==len(ledger)==124
    started=[json.loads(line) for line in (HERE/'attempts.jsonl').read_text(encoding='utf8').splitlines() if json.loads(line)['event']=='started']
    assert len(started)<=124 and len({x['slot'] for x in started})==len(started)
    assert [x['slot'] for x in started]==list(range(1,len(started)+1))
    assert sum(x['status']!='not_run' for x in ledger)==len(started)
    accounts={};saved_audits=0;actual_core_markers=0;warm_starts=0;outputs={}
    for job,slot in zip(plan,ledger):
        assert job['slot']==slot['slot'] and job['id']==slot['id']
        p=HERE/'outputs'/(job['id']+'.json');marker=HERE/'logs'/(job['id']+'_markers.jsonl')
        if slot['status']=='not_run':assert not p.exists() and not marker.exists();continue
        if marker.exists():
            marks=[json.loads(line) for line in marker.read_text(encoding='utf8').splitlines()]
            actual_core_markers+=sum(x['tag']=='core_started' for x in marks);warm_starts+=sum(x['tag']=='warm_entry_started' for x in marks)
        if not p.exists():assert slot['status']=='failed';continue
        result=read(p);outputs[job['id']]=result;assert result['job']==job
        assert result['source_input_sha256']==sha(HERE/job['input'])
        assert hashlib.sha256(result['request_utf8'].encode('utf8')).hexdigest()==result['request_sha256']
        req=json.loads(result['request_utf8'])
        if job['method']=='H1':assert 'previous' not in req and req['incoming_heading']==job['heading']
        else:assert req==result['input']
        for path,digest in result['loaded_source_hashes'].items():assert sha(Path(path))==digest,('loaded bytes changed',path)
        for key,value in result['accounts'].items():accounts[key]=accounts.get(key,0)+value
        if slot['status']=='passed':
            assert result['passed'] and result['entry']['eligible'] and result['entry']['entry_seconds']<20
            audit=audit_output(result['input'],job['heading'],result['entry']['raw']['branches']['P0'],job['method']=='H1')
            assert audit==result['audit'];saved_audits+=1
    assert accounts.get('core_started',0)==actual_core_markers
    pairs=read(HERE/'54等价证据.json');diagonals=read(HERE/'16斜向技术证据.json')
    for item in pairs:
        a=outputs[f"legacy__{item['case']}__ORIGINAL"];b=outputs[f"legacy__{item['case']}__H1"]
        assert equivalence(a['entry']['raw']['branches']['P0'],b['entry']['raw']['branches']['P0'])
        assert a['audit']['credits']==b['audit']['credits'] and a['audit']['decisions']==b['audit']['decisions']
    for row in diagonals:
        j=plan[row['slot']-1];a=outputs[row['reference_id']];b=outputs[j['id']]
        assert equivalence(a['entry']['raw']['branches']['P0'],b['entry']['raw']['branches']['P0'])
    if (HERE/'completion_manifest.json').exists():
        manifest=read(HERE/'completion_manifest.json')
        for rel,digest in manifest['files'].items():assert sha(HERE/rel)==digest,('sealed file changed',rel)
        # Historical snapshots only: legitimate future root progress appends are allowed.
        assert sha(HERE/'根进度_执行前快照.md')==manifest['root_progress_before_sha256']
        assert sha(HERE/'根进度_执行后快照.md')==manifest['root_progress_after_sha256']
    print(json.dumps(dict(passed=True,attempted_slots=len(started),warm_entries=warm_starts,accounts=accounts,
        legacy_pairs=len(pairs),diagonal_entries=len(diagonals),saved_independent_audits=saved_audits,
        this_verify_added=dict(planning_entries=0,cores=0,graph_searches=0,LOS_queries=0,route_audits=saved_audits),
        all_real_passed=all(x['status']=='passed' for x in ledger),
        live_root_equality_required=False,sealed=(HERE/'completion_manifest.json').exists()),ensure_ascii=False))

if __name__=='__main__':main()
