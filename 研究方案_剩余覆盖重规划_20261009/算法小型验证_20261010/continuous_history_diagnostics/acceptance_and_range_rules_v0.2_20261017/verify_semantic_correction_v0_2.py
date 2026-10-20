"""Read-only semantic and run_id audit for the v0.2 correction package."""
from pathlib import Path
import argparse, csv, hashlib, json

ROOT=Path(__file__).resolve().parents[4]
ALGO=ROOT/"研究方案_剩余覆盖重规划_20261009"/"算法小型验证_20261010"
DIAG=ALGO/"continuous_history_diagnostics"
SUP=DIAG/"acceptance_and_range_rules_v0.2_20261017"
BASE_SUP=DIAG/"acceptance_and_range_rules_v0.1_20261017"
RUN=DIAG/"old_plan_warm_global_v0.1_20261017"
PREP=DIAG/"preparation_verification_v0.1_20261016"/"cases"
INITIAL=DIAG/"preflight_v0.1_20261016"/"initial_cases"
EXPECTED_RUNNER_SHA="f7168fe617b62c27d7db51fb885b922d6baaf7edd7604c4a2e199f02c396d68f"
DISCLOSED_RUNNER_SHA="e8ff1d405546e0d01976a7a9cb803569092717d198fda7b22367fc4f24cbc72c"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_package_manifest():
    manifest=SUP/"sha256_manifest_v0.2.json";doc=read(manifest)
    assert doc["version"]=="v0.2" and doc["manifest_excludes_itself"] is True
    listed={x["path"]:x for x in doc["files"]}
    actual={p.relative_to(SUP).as_posix():p for p in SUP.rglob("*") if p.is_file() and p!=manifest}
    assert doc["entry_count"]==len(listed)==len(actual)
    assert set(listed)==set(actual)
    for rel,p in actual.items():
        entry=listed[rel]
        assert p.stat().st_size==entry["size_bytes"] and sha(p)==entry["sha256"],("package hash mismatch",rel)
    return {"manifest_entries":len(actual),"all_hashes_match":True}


def points(values):
    return {tuple(p) for p in values}


def first_positions(route, goals):
    goals=set(map(tuple,goals));out={}
    for i,p in enumerate(map(tuple,route)):
        if p in goals and p not in out:out[p]=i
    return out


def verify_goal_partition(states):
    rows={r["map_id"]:r for r in csv_rows(SUP/"goal_partition_v0.2.csv")}
    assert len(rows)==10
    checked=0;covered_obstructed=[]
    for s in states:
        mid=s["map_id"];case=read(PREP/(mid+".json"));initial_case=read(INITIAL/(mid+".json"));meta=case["metadata"]
        initial=points(meta["initial_targets"]);published=points(meta["published_targets"])
        targets=points(case["targets"]);covered=points(case["covered"]);free=points(case["free"])
        explicit=points(meta.get("deferred_targets",[]));deferred=(published-covered)-free
        not_current=initial-targets;covered_not_current=not_current&covered
        deferred_not_current=not_current&deferred
        other=not_current-covered_not_current-deferred_not_current
        assert deferred==explicit,(mid,"deferred formula mismatch")
        assert targets==published&free,(mid,"current inspectable target relation mismatch")
        assert initial<=published,(mid,"initial goals absent from published metadata")
        ev=s["event_analysis"]
        for key,expected in (("metadata_published_targets",published),("current_inspectable_targets",targets),
            ("covered_history_targets",covered),("event_deferred_uncompleted_targets",deferred),
            ("initial_targets_not_published",initial-published),
            ("initial_targets_not_currently_inspectable",not_current),
            ("not_currently_inspectable_initial_targets_already_covered",covered_not_current),
            ("not_currently_inspectable_initial_targets_uncompleted_deferred",deferred_not_current),
            ("not_currently_inspectable_initial_targets_other",other)):
            assert points(ev[key])==expected,(mid,key)
        assert ev["deferred_formula_matches_metadata"] is True
        row=rows[mid]
        csv_expected={"initial_target_cells_json":initial,"metadata_published_target_cells_json":published,
            "current_inspectable_target_cells_json":targets,"covered_history_cells_json":covered,
            "event_deferred_uncompleted_cells_json":deferred}
        for key,expected in csv_expected.items():assert points(json.loads(row[key]))==expected,(mid,key)
        assert int(row["event_deferred_uncompleted_count"])==len(deferred)
        assert row["deferred_formula_matches_metadata"]=="True"
        assert row["current_targets_equal_published_intersect_free"]=="True"
        blocked_hist=covered_not_current& (points(initial_case["free"])-free)
        covered_obstructed.extend((mid,p) for p in blocked_hist)
        assert len(s["ranges"])==4
        checked+=1
    assert len(covered_obstructed)==6
    assert sorted(mid for mid,_ in covered_obstructed)==[
        "large_g4_development"]*5+["small_g4_development"]
    return {"states":checked,"deferred_formula_matches":checked,
        "covered_obstructed_initial_goals":len(covered_obstructed),
        "covered_obstructed_by_state":{"large_g4_development":5,"small_g4_development":1}}


def verify_blocked_route_roles(states):
    rows=csv_rows(SUP/"blocked_route_roles_v0.2.csv")
    saved={(r["map_id"],int(r["route_index"])):r for r in rows}
    assert len(saved)==27 and len(rows)==27
    expected_indices={
        "large_g2_development":[470,471,472,473,474,475,476],
        "large_g3_development":[195,202,311,318,427,434,543,550],
        "large_g4_development":[75,128,283],
        "medium_g1_development":[113,114],
        "medium_g2_development":[121,122,123,124,125,126,127],
    }
    checked=0
    for s in states:
        mid=s["map_id"];case=read(PREP/(mid+".json"));meta=case["metadata"]
        initial=points(meta["initial_targets"]);covered=points(case["covered"]);cur=tuple(case["current"])
        free=points(case["free"]);published=points(meta["published_targets"])
        deferred=(published-covered)-free;route=list(map(tuple,case["old_route"]))
        remaining=initial-covered-{cur};hits=first_positions(route,remaining)
        assert set(hits)==remaining,(mid,"pre-event old route misses remaining task")
        last=max(hits.values(),default=-1)
        blocked=[i for i,p in enumerate(route) if p not in free]
        assert blocked==s["event_analysis"]["old_route_blocked_indices"]
        expected_for_state=expected_indices.get(mid,[])
        assert blocked==expected_for_state,(mid,blocked,expected_for_state)
        ev=s["event_analysis"]
        assert ev["last_pre_event_service_route_index"]==last
        assert ev["pre_event_route_ends_at_base"] is True
        assert ev["pre_event_remaining_targets_after_last_service_count"]==0
        assert ev["blocked_return_before_remaining_service_count"]==0
        for i in blocked:
            cell=route[i]
            role="first_service" if hits.get(cell)==i else ("return" if i>last else "connection")
            status=("uncompleted_deferred_target" if cell in deferred else
                    "covered_history_obstructed" if cell in covered else
                    "published_but_not_currently_inspectable" if cell in published else "not_a_published_target")
            assert cell in deferred and role=="first_service",(mid,i,"blocked route cell is not an uncompleted first-service goal")
            row=saved[(mid,i)]
            assert tuple(json.loads(row["cell_json"]))==cell
            assert row["old_plan_role"]==role
            assert row["event_post_target_status"]==status
            assert row["old_plan_first_service"]=="True" if role=="first_service" else row["old_plan_first_service"]=="False"
            assert (row["uncompleted_deferred_target_cell"]=="True")== (cell in deferred)
        checked+=len(blocked)
    assert checked==27
    return {"blocked_route_indices":checked,"all_are_pre_event_first_service":True,
        "expected_indices_by_state":expected_indices,"return_before_unfinished_task_indices":0}


def verify_range_reasons(states):
    rows=csv_rows(SUP/"range_inclusion_reasons_v0.2.csv")
    csv_map={(r["map_id"],r["range"],int(r["block_id"])):r for r in rows}
    assert len(csv_map)==len(rows)
    total=0;summary={}
    for s in states:
        mid=s["map_id"]
        for rr in s["ranges"]:
            for b in rr["old_service_blocks"]:
                key=(mid,rr["name"],int(b["block_id"]))
                assert key in csv_map,("missing inclusion CSV row",key)
                assert "single_interval_enclosure_only" not in b["inclusion_reasons"]
                assert b["necessity_or_unnecessary_claim"] is False
                assert b["inclusion_reasons"]
                row=csv_map[key]
                assert json.loads(row["inclusion_reasons_json"])==b["inclusion_reasons"]
                assert row["attribution_status"]==b["attribution_status"]
                summary.setdefault((mid,rr["name"]),{"blocks":0,"tasks":0,"reasons":{}})
                q=summary[(mid,rr["name"])];q["blocks"]+=1;q["tasks"]+=b["pending_target_count"]
                for reason in b["inclusion_reasons"]:q["reasons"][reason]=q["reasons"].get(reason,0)+1
                total+=1
    assert total==len(rows)
    old_doc=read(BASE_SUP/"range_details_final.json")
    old_states={s["map_id"]:s for s in old_doc["states"]}
    old_meaning={"large_g2_development":(1,13),"medium_g1_development":(27,108),"medium_g2_development":(14,112)}
    for mid,expected in old_meaning.items():
        old_blocks=old_states[mid]["ranges"][0]["old_service_blocks"]
        flagged=[b for b in old_blocks if "single_interval_enclosure_only" in b["inclusion_reasons"]]
        assert (len(flagged),sum(b["pending_target_count"] for b in flagged))==expected
    assert summary[("medium_g1_development","R_SEED")]["reasons"].get("multi_contact_or_anchor_enclosing_hull_gap")==27
    assert summary[("medium_g2_development","R_SEED")]["reasons"].get("multi_contact_or_anchor_enclosing_hull_gap")==14
    return {"included_service_block_rows":total,"forbidden_old_only_label_absent":True,
        "mechanical_categories":sorted({z for s in states for rr in s["ranges"] for b in rr["old_service_blocks"] for z in b["inclusion_reasons"]}),
        "legacy_count_reinterpretation":{"large_g2_R_SEED":{"blocks":1,"tasks":13,"current_reason":"contact/service-boundary closure co-occurs with direct contact; not uniquely collateral"},
          "medium_g1_R_SEED":{"blocks":27,"tasks":108,"current_reason":"multi-contact/anchor hull gap; reason non-unique"},
          "medium_g2_R_SEED":{"blocks":14,"tasks":112,"current_reason":"multi-contact/anchor hull gap; reason non-unique"}}}


def verify_protocol_join(states):
    protocol=read(RUN/"protocol.json");jobs=protocol["jobs"];pmap={x["run_id"]:x for x in jobs}
    assert len(jobs)==120 and len(pmap)==120
    files=["execution_ledger.jsonl","recovery/recovery_ledger.jsonl","recovery2/recovery_ledger.jsonl"]
    attempts=[]
    for rel in files:
        attempts.extend(json.loads(x) for x in (RUN/rel).read_text(encoding="utf-8").splitlines() if x.strip())
    good=[x for x in attempts if x.get("worker_status")=="returned" and x.get("valid") is True and
          x.get("returncode")==0 and not x.get("watchdog_timeout")]
    good_map={}
    for x in good:
        assert x["run_id"] not in good_map,("duplicate successful run_id",x["run_id"])
        good_map[x["run_id"]]=x
    assert set(good_map)==set(pmap)
    final=[json.loads(x) for x in (RUN/"final_120.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    fmap={x["job"]["run_id"]:x for x in final}
    assert len(fmap)==120 and set(fmap)==set(pmap)
    fields=("run_id","case","map_id","repeat","budget","seed","method")
    joined=csv_rows(SUP/"protocol_runid_join_v0.2.csv");jmap={x["run_id"]:x for x in joined}
    assert len(joined)==120 and set(jmap)==set(pmap)
    for rid,job in pmap.items():
        assert all(good_map[rid].get(k)==job.get(k) for k in fields)
        assert all(fmap[rid]["job"].get(k)==job.get(k) for k in fields)
        assert jmap[rid]["protocol_job_match"]==jmap[rid]["final_120_match"]=="True"
        assert jmap[rid]["success_ledger"] in files
    runner=[(k,v) for k,v in protocol["protected_hashes"].items() if k.endswith("run_p2_warm_global_20261017.py")]
    assert len(runner)==1 and runner[0][1]==EXPECTED_RUNNER_SHA
    actual=sha(ROOT/"run_p2_warm_global_20261017.py")
    assert actual==DISCLOSED_RUNNER_SHA
    saved=read(SUP/"range_details_final.json")["protocol_runid_audit"]
    assert saved["protocol_jobs"]==saved["final_120_rows"]==saved["unique_success_run_ids"]==120
    assert saved["attempt_rows"]==len(attempts) and saved["successful_attempt_rows"]==120
    assert saved["runner_hash_exception"]["exact_protocol_expected_sha256"]==EXPECTED_RUNNER_SHA
    assert saved["runner_hash_exception"]["exact_disclosed_current_sha256"]==DISCLOSED_RUNNER_SHA
    return {"protocol_jobs":120,"final_rows":120,"original_attempt_rows":len(attempts),
        "unique_successes":120,"run_id_joins":120,"runner_hash_exception_exact_values":True,
        "attempt_ledgers":files}


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--check",action="store_true",help="run read-only semantic checks")
    ap.parse_args()
    doc=read(SUP/"range_details_final.json");states=doc["states"]
    assert doc["mode"]=="offline_read_only_no_planner_calls" and doc["planner_calls_in_this_analysis"]==0
    assert len(states)==10
    report={"status":"PASS","read_only":True,"planner_calls":0,
        "package_manifest":verify_package_manifest(),
        "goal_partition":verify_goal_partition(states),
        "blocked_route_roles":verify_blocked_route_roles(states),
        "range_inclusion_reasons":verify_range_reasons(states),
        "protocol_run_id_join":verify_protocol_join(states)}
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=="__main__":main()
