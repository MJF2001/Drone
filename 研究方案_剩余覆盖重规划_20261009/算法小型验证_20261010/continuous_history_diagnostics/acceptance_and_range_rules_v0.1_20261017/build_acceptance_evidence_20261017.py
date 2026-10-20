"""Create non-destructive errata and execution-history evidence."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json, re, statistics

ROOT=Path(__file__).resolve().parents[4]
ALGO=ROOT/"研究方案_剩余覆盖重规划_20261009"/"算法小型验证_20261010"
SUP=ALGO/"continuous_history_diagnostics"/"acceptance_and_range_rules_v0.1_20261017"
RUN=ALGO/"continuous_history_diagnostics"/"old_plan_warm_global_v0.1_20261017"
OLD69=ALGO/"continuous_history_diagnostics"/"comparison_v0.1_20261016"

def read(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rows(p): return [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
def write_json(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")

def error_info(row, result_path):
    if not Path(result_path).exists():
        return {"exception_type":"missing_result","exception_text":None,"failure_phase":"unknown","traceback":None}
    d=read(result_path);tb=d.get("traceback","")
    if not tb:
        return {"exception_type":None,"exception_text":None,"failure_phase":"none","traceback":None}
    lines=tb.strip().splitlines();last=lines[-1] if lines else ""
    m=re.match(r"([A-Za-z_][\w.]*(?:Error|Exception|Interrupt|Exit)?):\s*(.*)",last)
    typ=m.group(1) if m else last.split(":",1)[0]
    msg=m.group(2) if m else last
    phase="before_planner_dispatch" if "LITERAL" in msg or "baseline_suite.solve" in tb else "input_path_resolution_before_planner" if "read_text" in tb and "AttributeError" in last else "unknown_pre_or_in_planner"
    return {"exception_type":typ,"exception_text":msg,"failure_phase":phase,"traceback":tb}

def main():
    protocol=read(RUN/"protocol.json");final=read(RUN/"completion_final.json")
    original=read(RUN/"audit_summary.json");orig_sha=sha(RUN/"audit_summary.json")
    batches=[("initial",RUN/"execution_ledger.jsonl",RUN/"runs"),
             ("recovery1",RUN/"recovery"/"recovery_ledger.jsonl",RUN/"recovery"/"runs"),
             ("recovery2",RUN/"recovery2"/"recovery_ledger.jsonl",RUN/"recovery2"/"runs")]
    all_attempts=[];batch_summaries=[]
    for batch,path,rundir in batches:
        attempt_rows=rows(path);errs=Counter();meth=Counter();status=Counter();seq=[]
        for i,r in enumerate(attempt_rows,1):
            meth[r.get("method")]+=1;status[r.get("worker_status")]+=1
            result_path=rundir/(r["run_id"]+".json")
            e=error_info(r,result_path)
            if e["exception_type"]: errs[(e["exception_type"],e["exception_text"],e["failure_phase"])]+=1
            data={"batch":batch,"batch_sequence":i,"run_id":r.get("run_id"),"map_id":r.get("map_id"),
                  "method":r.get("method"),"budget":r.get("budget"),"repeat":r.get("repeat"),"seed":r.get("seed"),
                  "worker_status":r.get("worker_status"),"returncode":r.get("returncode"),
                  "watchdog_timeout":r.get("watchdog_timeout"),"valid":r.get("valid"),
                  "steps":r.get("steps"),"seconds":r.get("seconds"),"source":r.get("source"),
                  "process_wall_seconds":r.get("process_wall_seconds"),"result_path":str(result_path.resolve()),
                  "worker_log_path":str((rundir/(r["run_id"]+".log")).resolve()),
                  "worker_log_bytes":(rundir/(r["run_id"]+".log")).stat().st_size if (rundir/(r["run_id"]+".log")).exists() else None,
                  **e}
            all_attempts.append(data);seq.append(r["run_id"])
        batch_summaries.append({"batch":batch,"attempts":len(attempt_rows),"valid":sum(bool(r.get("valid")) for r in attempt_rows),
            "exceptions":sum(r.get("worker_status")=="exception" for r in attempt_rows),
            "watchdog_timeouts":sum(bool(r.get("watchdog_timeout")) for r in attempt_rows),
            "method_counts":dict(sorted(meth.items())),"worker_status_counts":dict(sorted(status.items())),
            "exception_groups":[{"type":k[0],"message":k[1],"phase":k[2],"count":n} for k,n in sorted(errs.items())],
            "sequence_first":seq[:6],"sequence_last":seq[-6:],"ledger_path":str(path.resolve()),"ledger_sha256":sha(path),
            "reported_serial_process_seconds_sum":sum(r.get("process_wall_seconds") or 0 for r in attempt_rows)})
    assert len(all_attempts)==197
    planned=[j["run_id"] for j in protocol["jobs"]]
    initial=[a["run_id"] for a in all_attempts if a["batch"]=="initial"]
    assert initial==planned[:len(initial)]
    valid_success=[a["run_id"] for a in all_attempts if a["valid"]]
    assert len(valid_success)==120 and len(set(valid_success))==120
    # All 17 protocol hashes, including the one explicitly disclosed exception.
    hash_rows=[]
    for path,expected in protocol["protected_hashes"].items():
        actual=sha(path) if Path(path).is_file() else None
        hash_rows.append({"path":path,"expected_sha256":expected,"actual_sha256":actual,"matches":actual==expected})
    mismatches=[x for x in hash_rows if not x["matches"]]
    assert len(hash_rows)==17 and len(mismatches)==1
    runner=ROOT/"run_p2_warm_global_20261017.py"
    assert Path(mismatches[0]["path"]).resolve()==runner.resolve()
    errata={"document":"audit_summary_errata_20261017","created_date":"2026-10-17",
      "replaces":"protocol_deviations field only in the original audit_summary.json",
      "original_path":str((RUN/"audit_summary.json").resolve()),"original_sha256":orig_sha,
      "original_is_preserved":True,
      "original_protocol_deviations":original.get("protocol_deviations"),
      "corrected_protocol_deviations":[
        "Initial batch attempted 38 jobs: 25 returned valid outputs and 13 LITERAL dispatch attempts raised ValueError before planner invocation.",
        "Recovery batch 1 attempted 64 jobs: 0 valid and 64 str.read_text path-type exceptions before planner invocation.",
        "Recovery batch 2 attempted the 95 incomplete/failed jobs: all 95 returned valid outputs; prior valid outputs were not rerun.",
        "Across all batches there are 120 unique valid successes. The actual method rotation was interrupted; all 40 LITERAL outputs were produced in recovery batch 2.",
        "Execution was serial according to the runner loops and per-attempt ledgers. These ledgers do not contain wall-clock timestamps, so exact launch times/order across batches are not established.",
        "The first-run runner file currently differs from the protocol's sealed hash; this is a post-run source-state observation, not proof of the exact source loaded at process start."],
      "evidence_paths":[str((SUP/"execution_timeline_20261017.json").resolve()),str((SUP/"execution_attempt_timeline.csv").resolve()),
        str((RUN/"execution_ledger.jsonl").resolve()),str((RUN/"recovery"/"recovery_ledger.jsonl").resolve()),
        str((RUN/"recovery2"/"recovery_ledger.jsonl").resolve())],
      "must_not_use_original_deviation_counts":"10 and 60 are superseded; corrected counts are 13 initial exceptions and 64 recovery1 exceptions.",
      "protocol_hashes":hash_rows,"protocol_hash_mismatch_count":len(mismatches),"protocol_hash_mismatch":mismatches[0]}
    write_json(SUP/"audit_summary_errata_20261017.json",errata)
    # Warm path instrumentation: stage wall time is observed, sequence_cost time is not separately timed.
    warm=[]
    for item in rows(RUN/"final_120.jsonl"):
        job=item["job"]
        if job["method"]!="P2_WARM_GLOBAL":continue
        raw=item["result"]["raw"];events=raw.get("events",[])
        stage=next((e for e in events if e.get("stage")=="warm_optimize"),{})
        inner=next((e for e in events if e.get("stage")=="warm_2opt"),{})
        duration=(stage.get("end",0)-stage.get("start",0)) if stage else None
        accepted=inner.get("accepted_moves",[])
        warm.append({"run_id":job["run_id"],"map_id":job["map_id"],"budget":job["budget"],"repeat":job["repeat"],
            "stage_status":stage.get("status"),"warm_optimize_seconds":duration,"passes":inner.get("passes"),
            "swaps":inner.get("swaps"),"termination":inner.get("termination"),
            "completed_sequence_cost_logs":len(accepted),"swaps_without_completed_sequence_cost_log":max(0,(inner.get("swaps") or 0)-len(accepted)),
            "warm_candidate_expansion_event":next((e.get("status","completed") for e in events if e.get("stage")=="warm_expand_accept"),None),
            "final_source":raw.get("source"),"active_stage":raw.get("active_stage")})
    assert len(warm)==40
    warm_groups=[]
    for budget in (1,20):
        g=[x for x in warm if x["budget"]==budget];ds=[x["warm_optimize_seconds"] for x in g if x["warm_optimize_seconds"] is not None]
        warm_groups.append({"budget_seconds":budget,"calls":len(g),
            "warm_stage_termination_counts":dict(Counter(x["termination"] for x in g)),
            "warm_stage_status_counts":dict(Counter(x["stage_status"] for x in g)),
            "warm_optimize_stage_seconds_mean":statistics.mean(ds) if ds else None,
            "warm_optimize_stage_seconds_median":statistics.median(ds) if ds else None,
            "warm_optimize_stage_seconds_max":max(ds) if ds else None,
            "recorded_swaps":sum(x["swaps"] or 0 for x in g),
            "completed_sequence_cost_logs":sum(x["completed_sequence_cost_logs"] for x in g),
            "swaps_without_completed_sequence_cost_log":sum(x["swaps_without_completed_sequence_cost_log"] for x in g),
            "calls_with_later_warm_expansion_skipped":sum(x["warm_candidate_expansion_event"]=="skipped_after_deadline" for x in g)})
    warm_diag={"created_date":"2026-10-17","method":"source and saved event log review; no profiling and no formal reruns",
       "source_path":str((ALGO/"candidate_baselines"/"P2_WARM_GLOBAL"/"v0.1_20261017"/"p2_search_audit_warm.py").resolve()),
       "source_sha256":sha(ALGO/"candidate_baselines"/"P2_WARM_GLOBAL"/"v0.1_20261017"/"p2_search_audit_warm.py"),
       "confirmed_extra_operations":[
         "warm 2-opt calls g.check_time once before each pass and once for every candidate pair; each g.distance call performs additional deadline-checked graph path/distance work.",
         "After each accepted reversal, sequence_cost recomputes the entire current→visits→base proxy cost using g.distance for every adjacent visit pair.",
         "The accepted-move log timestamps elapsed() before evaluating sequence_cost. The elapsed field therefore does not include that call; warm_optimize stage duration does include it.",
         "If sequence_cost raises DeadlineExceeded, warm_two_opt records termination=deadline and rethrows; warm_expand_accept is marked skipped. The solver returns the best legal route accepted earlier (usually old_suffix/common_fallback), so an unfinished warm sequence is not returned as a legal candidate."],
       "unmeasured":"No profiler/timer isolates check_time or sequence_cost; neither per-check overhead nor an overhead percentage can be claimed.",
       "logged_move_counts_by_budget":warm_groups,"per_call":warm}
    write_json(SUP/"warm_overhead_analysis_20261017.json",warm_diag)
    counted_tests=read(SUP/"counted_25_regression_summary_20261017.json")
    warm_regression=read(SUP/"posthoc_warm_regressions_20261017.json")
    # Cross-batch pair timing and stage comparisons already have complete route-level data in CSV.
    pairs=list(csv.DictReader((SUP/"cross_batch_69_70_all_pairs.csv").open(encoding="utf-8-sig")))
    deltas=[float(x["seconds_delta_70_minus_69"]) for x in pairs if x["seconds_delta_70_minus_69"]]
    stagechanged=[x for x in pairs if x["stage_status_changes"] not in ("[]","")]
    timeline={"created_date":"2026-10-17","repository_head":"5e366a58b7272a7a4723c077b10820c68664dfe2",
       "attempt_count":len(all_attempts),"unique_valid_successes":len(valid_success),"duplicate_valid_successes":len(valid_success)-len(set(valid_success)),
       "batch_summaries":batch_summaries,"serial_execution_evidence":{
          "initial_runner":"run_p2_warm_global_20261017.py iterates the job sequence with a blocking subprocess.run in a single for loop.",
          "recovery_runner_1":"resume_p2_warm_global_20261017.py uses a single blocking job loop.",
          "recovery_runner_2":"resume2_p2_warm_global_20261017.py uses a single blocking job loop.",
          "exact_wall_clock_timestamps":"not present in the saved ledgers; batch order is recoverable from ledger order, exact launch times are not."},
       "attempt_timeline_csv":str((SUP/"execution_attempt_timeline.csv").resolve()),
       "formal_smoke_preflight":{"reported_attempt_count":final.get("smoke_preflight_attempts"),
          "saved_individual_preflight_rows":0,"completion_evidence_path":str((RUN/"completion_final.json").resolve()),
          "status":"count survives, individual case IDs/results/logs were not found in the 70 deliverable tree; cannot reconstruct each preflight input/result without inventing evidence."},
       "posthoc_regression_call_counts":{"exact_25_test_suite":{"tests":counted_tests["tests_run"],"passed":counted_tests["status"]=="PASS",
           "range_engine_planner_calls":counted_tests["counted_range_engine_planner_calls"],"formal_development_map_calls":0,
           "log":str((SUP/"counted_25_regression_run_20261017.log").resolve())},
          "warm_edge_fixture_suite":{"tests":len(warm_regression["results"]),"candidate_solver_calls":warm_regression["candidate_planner_calls"],
           "frozen_P2_calls":warm_regression["frozen_P2_planner_calls"],"total_planner_calls":warm_regression["total_planner_calls"],
           "formal_development_map_calls":0,"log":str((SUP/"posthoc_warm_regressions_20261017.log").resolve())},
          "total_posthoc_synthetic_planner_calls":counted_tests["counted_range_engine_planner_calls"]+warm_regression["total_planner_calls"]},
       "runner_source_hashes":{"protocol_expected":mismatches[0]["expected_sha256"],"current_after_run":mismatches[0]["actual_sha256"],
          "runner_path":mismatches[0]["path"],"other_protected_hashes_match":len(hash_rows)-len(mismatches)},
       "recovery_source_hashes":{"resume1_path":str((ROOT/"resume_p2_warm_global_20261017.py").resolve()),
          "resume1_current_sha256":sha(ROOT/"resume_p2_warm_global_20261017.py"),
          "resume2_path":str((ROOT/"resume2_p2_warm_global_20261017.py").resolve()),
          "resume2_current_sha256":sha(ROOT/"resume2_p2_warm_global_20261017.py"),
          "limitation":"These are current file hashes. The execution ledger does not record source hashes at each process start."},
       "method_rotation_fact":"Initial batch and recovery1 were interrupted; recovery2 contains all 40 LITERAL result rows. This is an execution-schedule deviation, not a validity defect by itself.",
       "cross_batch_69_70":{"paired_rows":len(pairs),"rows_with_any_route_or_stage_record_change":read(SUP/"cross_batch_summary.json")["rows_with_any_recorded_change"],
          "route_step_changed_rows":sum(x["route_length_changed"]=="True" for x in pairs),
          "route_content_changed_rows":sum(x["route_same"]=="False" for x in pairs),
          "source_changed_rows":sum(x["source_changed"]=="True" for x in pairs),
          "stage_status_changed_rows":len(stagechanged),"elapsed_seconds_differed_rows":len(deltas),
          "seconds_delta_70_minus_69_mean":statistics.mean(deltas) if deltas else None,
          "seconds_delta_70_minus_69_median":statistics.median(deltas) if deltas else None,
          "seconds_delta_70_minus_69_min":min(deltas) if deltas else None,
          "seconds_delta_70_minus_69_max":max(deltas) if deltas else None,
          "large_g1_budget20":{"69_P2_steps":941,"70_P2_steps":1073,"69_LITERAL_steps":939,"70_LITERAL_steps":941,
             "70_warm_steps":1243,"70_P2_active_stage":"H_scan_opt","70_warm_active_stage":"warm_optimize",
             "interpretation":"Across-batch difference cannot be attributed to the new warm mechanism; P2/LITERAL also shifted under different elapsed execution conditions."},
          "all_80_rows_path":str((SUP/"cross_batch_69_70_all_pairs.csv").resolve()),
          "changed_route_or_stage_rows_path":str((SUP/"cross_batch_69_70_changed_pairs.csv").resolve())},
       "source_evidence_note":"The run protocol has a single runner SHA mismatch. Post-hoc on-disk hashes do not establish which code bytes were loaded at initial process start."}
    write_json(SUP/"execution_timeline_20261017.json",timeline)
    with (SUP/"execution_attempt_timeline.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(all_attempts[0]));w.writeheader();w.writerows(all_attempts)
    # Seven-point A-stage evidence matrix; statuses explicitly separate reproducible post-hoc evidence.
    matrix=[
      {"item":"A1 existing independent audit","status":"pass","evidence":"prior 120-route audit, warm sequence audit, 416-item deliverable check; repeated by verify_acceptance_range_20261017.py --check"},
      {"item":"A2 independent read-only checker","status":"pass","evidence":"verify_acceptance_range_20261017.py; fixture suite; new 40-core/range rows and exact hash checks"},
      {"item":"A3 tests, warm-off and preflights","status":"partial","evidence":"25 regression tests reproduced post-hoc with seven counted range-engine planner calls; five additional frozen/warm micro-solver calls cover warm-off and edge cases. Total new synthetic planner calls: 12; no development-map calls. Six formal smoke preflights survive only as a scalar in completion_final.json, without individual rows/logs; original multi-case warm-off log not found."},
      {"item":"A4 errata, timeline, overhead and 69/70","status":"pass_with_limits","evidence":"audit_summary_errata_20261017.json; execution_timeline_20261017.json; warm_overhead_analysis_20261017.json; complete 80-row cross-batch pair CSV. Exact wall-clock batch timestamps and launch-time source hash not recorded; no overhead percentage available."},
      {"item":"A5 scope to B gate","status":"pass_disclosed","evidence":"No damaged input, invalid route, or incorrect R_PLUS1 core found; all ten frozen state/range inputs matched independent reconstruction. Continue B with A3 gap disclosed."},
      {"item":"B1-B4 current ten-state diagnosis","status":"pass","evidence":"range_details_final.json; 10-state overview, 40 ranges, 40 LITERAL results; B planner calls=0."},
      {"item":"C delivery/hash/hand-off","status":"in_progress","evidence":"Awaiting final original-manifest recheck and final deliverables SHA256 manifest."}
    ]
    with (SUP/"acceptance_evidence_matrix_20261017.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(matrix[0]));w.writeheader();w.writerows(matrix)
    print(json.dumps({"status":"PASS","attempts":len(all_attempts),"unique_valid":len(valid_success),
        "batch_method_counts":{x["batch"]:x["method_counts"] for x in batch_summaries},
        "hash_mismatch":mismatches,"warm_calls":len(warm),"warm_groups":warm_groups,
        "cross_batch_elapsed_changes":len(deltas),"artifacts":["audit_summary_errata_20261017.json","execution_timeline_20261017.json","execution_attempt_timeline.csv","warm_overhead_analysis_20261017.json","acceptance_evidence_matrix_20261017.csv"]},ensure_ascii=False,indent=2))

if __name__=="__main__": main()
