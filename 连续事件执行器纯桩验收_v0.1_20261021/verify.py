"""One-command saved acceptance verification; no callbacks or real algorithms.
Independent audit performs and reports its own ordinary BFS count.
"""
from pathlib import Path
import json,hashlib,sys
from auditor import audit
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    initial=read(H/'initial_seal.json');assert initial['binding']=={n:sha(H/n) for n in read(H/'fixed_files.json')}
    for p,v in read(H/'source_hashes.json').items():assert sha(Path(p))==v,p
    pointer=read(H/'acceptance_pointer.json');assert sha(H/pointer['path'])==pointer['sha256'];accept=read(H/pointer['path']);assert accept['status']=='PASS' and accept['binding']==initial['binding']
    d=(H/pointer['path']).parent;spec=read(H/'fixture_spec.json');assert spec['planned_stub_responses']==43 and spec['cumulative_stub_cap_all_rounds']==48
    journal=[json.loads(x) for x in (H/'actual_stub_responses.jsonl').read_text(encoding='utf8').splitlines()];assert len(journal)==43<=48 and [r['global_sequence'] for r in journal]==list(range(1,44))
    counter={'BFS':0};proofs=[];expected_journal=[];sessions=main_bfs=0;category_counts={str(i):0 for i in range(1,13)}
    for ci,c in enumerate(spec['ordered_cases']):
        result=read(d/'results'/(c['id']+'.json'));z=audit(result,c,counter);assert z==read(d/'results'/(c['id']+'.audit.json'));proofs.append(z);category_counts[str(c['category'])]+=1;sessions+=len(result['sessions']);main_bfs+=len(result['environment_BFS'])
        rr=[]
        for name,s in result['sessions'].items():
            for req in s['requests']:rr.append((req['tick'],name,req))
        for tick,name,req in sorted(rr,key=lambda v:(v[0],v[1])):
            expected_journal.append(dict(global_sequence=len(expected_journal)+1,round=pointer['round'],subcase=c['id'],method=name,response_sequence=req['sequence'],payload_sha256=req['payload_sha256'],input_fields_read=sorted(req['input']),kind='HANDWRITTEN_STUB_CALLBACK'))
        assert bool(result['fatal_technical_error'])==bool(c.get('expected_technical_stop'))
    assert journal==expected_journal and proofs==accept['proofs'] and counter['BFS']==accept['independent_audit_BFS'] and main_bfs==accept['main_environment_BFS'] and sessions==25
    aa=read(d/'results/12a_merged_future_A.json');bb=read(d/'results/12b_merged_future_B.json');assert aa['world_hash']!=bb['world_hash'] and aa['sessions']['A']['requests'][0]['payload_utf8']==bb['sessions']['A']['requests'][0]['payload_utf8']
    assert all(aa['sessions']['A']['requests'][i]['tick']==bb['sessions']['A']['requests'][i]['tick'] for i in (0,1))
    if (H/'completion_manifest.json').exists():
        for p,h in read(H/'completion_manifest.json')['files'].items():assert sha(H/p)==h,p
    forbidden={'runtime','candidate','portable_frozen','model','baseline_suite','ppcpp_independent','p2_search_audit'};assert not forbidden.intersection(sys.modules)
    print(json.dumps(dict(status='ALL PASS',categories=12,subcases=23,category_subcase_counts=category_counts,simulated_sessions_saved=sessions,stub_responses_saved=43,new_stub_responses_this_verify=0,real_planner_entries=0,real_cores=0,main_environment_BFS_saved=main_bfs,ordinary_BFS_this_verify=counter['BFS'],Astar=0,Dijkstra=0,new_closed_loop_runs_this_verify=0,claim='Handwritten stub executor acceptance only; real algorithm integration/performance not tested'),ensure_ascii=False))
if __name__=='__main__':main()
