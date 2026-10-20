"""Read-only evidence organization. No geometry generation, planner or tests run.

Before document edits: --snapshot. After edits: --finalize. New output only.
"""
from pathlib import Path
import argparse,hashlib,json,shutil

ROOT=Path(__file__).resolve().parent
ALGO=ROOT/'研究方案_剩余覆盖重规划_20261009/算法小型验证_20261010'
DOCS=ROOT/'研究方案_剩余覆盖重规划_20261009/论文资料汇总_三篇文献与论文主题_20261009'
OUT=ALGO/'study_registry/review_20261015'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,o):
    with p.open('x',encoding='utf-8') as f:json.dump(o,f,ensure_ascii=False,indent=2)

def snapshot():
    OUT.mkdir(parents=True,exist_ok=False);(OUT/'source_snapshots').mkdir()
    records=[]
    for p in (ROOT/'当前进度与下一步.md',DOCS/'00_阅读入口.md'):
        dest=OUT/'source_snapshots'/p.name;shutil.copyfile(p,dest)
        records.append(dict(original_path=str(p),snapshot_path=str(dest),sha256=sha(dest)))
    write(OUT/'before_document_update.json',dict(purpose='Preserve prior progress/index before organization',files=records,
        solver_called=False,tests_rerun=False,holdout_generated=False))
    print(json.dumps(dict(snapshot_files=len(records),output=str(OUT)),ensure_ascii=False))

def finalize():
    previous=read(OUT/'before_document_update.json')
    assert all(sha(Path(r['snapshot_path']))==r['sha256'] for r in previous['files'])
    base=ALGO/'frozen_baselines/v2_20261012';bm=read(base/'manifest.json')
    assert all(sha(base/'source'/n)==h for n,h in bm['source_sha256'].items())
    assert sha(base/'runtime_profile.json')==bm['runtime_profile_sha256']
    candidate=ALGO/'candidate_baselines/PPCPP_CORE4/v0.1_20261014';cm=read(candidate/'manifest.json')
    assert all(sha(candidate/n)==h for n,h in cm['files_sha256'].items())
    evidence=[]
    names=(('scale_inputs/development_v0.1_20261014','completion.json','input_preparation'),
        ('development_preflights/v1_20261014','completion.json','runtime_preflight'),
        ('development_preflights/ppcpp_weight_grid_v0.1_20261014','completion.json','parameter_selection'),
        ('development_preflights/four_method_paired_v1_20261015','completion.json','tuned_state_development_comparison'),
        ('scale_inputs/matched_history_v2_20261015','completion.json','matched_input_preparation'),
        ('development_preflights/matched_history_v2_20261015','completion.json','matched_history_development_comparison'))
    for directory,filename,role in names:
        folder=ALGO/directory;p=folder/filename;completion=read(p)
        manifest=read(folder/'sha256.json');entries=manifest.get('artifacts',manifest)
        assert all(sha(folder/n)==h for n,h in entries.items())
        evidence.append(dict(role=role,directory=str(folder),completion=completion,
            completion_sha256=sha(p),manifest_sha256=sha(folder/'sha256.json'),verified_artifact_entries=len(entries),
            interpretation='Development evidence only; do not pool unrelated protocols or count repeats as maps.'))
    verification=[]
    for directory in ('development_preflights/four_method_paired_v1_20261015_verification',
                      'development_preflights/matched_history_v2_20261015_verification'):
        folder=ALGO/directory
        if (folder/'sha256.json').exists():
            assert all(sha(folder/n)==h for n,h in read(folder/'sha256.json').items())
        if (folder/'supplement_sha256.json').exists():
            assert all(sha(Path(n))==h for n,h in read(folder/'supplement_sha256.json').items())
        verification.append(dict(directory=str(folder),summary=read(folder/'summary.json'),summary_sha256=sha(folder/'summary.json')))
    # Old audit is preserved evidence, not re-executed on this turn.
    historical=ALGO/'results/run_32c_baseline_adaptation_audit_20261012'
    runtime=ROOT/'运行环境/验证记录_20261014/03_runtime_verification.json'
    invalid=ALGO/'scale_inputs/matched_history_v1_20261015/aborted.json'
    stats=ALGO/'development_preflights/matched_history_v2_20261015_verification/ppcpp_directional_summary.json'
    new_stats=[{k:v for k,v in r.items() if k not in ('per_state','per_map_mean_relative')}
        for r in read(stats) if r['subset']=='new_states']
    status=dict(version='research_status_review_v1_20261015',status='organized_not_final_experiment_freeze',
        organizer_sha256=sha(Path(__file__)),
        activity='Existing-file inspection, hash validation and document organization only.',
        solver_called=False,tests_rerun=False,holdout_generated=False,
        models=dict(radius=0,adjacency=4,unit_move_cost=1,mandatory_return=True,future_events_available=False),
        baselines=dict(frozen_three_version=bm['version'],methods=bm['methods'],source_files_hash_verified=len(bm['source_sha256']),
            candidate=cm['candidate'],candidate_version=cm['version'],candidate_files_hash_verified=len(cm['files_sha256'])),
        evidence=evidence,independent_saved_route_verification=verification,
        historical_adaptation_evidence=dict(directory=str(historical),completion=read(historical/'completion.json'),
            completion_sha256=sha(historical/'completion.json'),not_rerun=True),
        runtime_evidence=dict(path=str(runtime),sha256=sha(runtime),not_revalidated_by_execution=True),
        excluded_input_attempt=dict(path=str(invalid),sha256=sha(invalid),record=read(invalid),excluded=True),
        latest_new_state_comparisons=new_stats,
        project_stage='Fair baseline validation/development diagnosis; main algorithm and novelty not established.',
        final_holdout_status='12 map parameter rows and 432 schedule rows defined; holdout geometry and results not generated by this work.',
        formal_run_cost_if_four_methods=dict(planned_states=432,budgets_seconds=[1,5,20],paired_repeats=2,
            methods=4,nominal_runs=10368,nominal_budget_sum_hours=24.96,
            actual_duration_unknown=True,run_authorized_by_this_review=False),
        remaining_gates=['main_method_and_novelty','formal_method_roster','holdout_generation_entry_and_QA',
            'full_matrix_runner_and_resume_accounting','final_statistics_and_failure_policy','candidate_ablation',
            'formal_protocol_manifest','holdout_generation_and_execution'])
    write(OUT/'research_status.json',status)
    document_paths=[ROOT/'当前进度与下一步.md',DOCS/'00_阅读入口.md',
        DOCS/'53_正式评价冻结清单与开跑门槛_20261015.md',DOCS/'54_研究工作目的与当前进度汇报_20261015.md']
    write(OUT/'documentation_manifest.json',{str(p):sha(p) for p in document_paths})
    write(OUT/'sha256.json',{str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()})
    print(json.dumps(dict(status=status['status'],verified_batches=len(evidence),
        baseline_source_hashes=len(bm['source_sha256']),candidate_file_hashes=len(cm['files_sha256']),
        solver_called=False,output=str(OUT)),ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--snapshot',action='store_true');g.add_argument('--finalize',action='store_true');args=p.parse_args()
    snapshot() if args.snapshot else finalize()
