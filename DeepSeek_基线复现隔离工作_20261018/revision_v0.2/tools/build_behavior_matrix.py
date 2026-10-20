"""Build evidence/behavior_matrix.csv.

R5 asked for the claim "the adapter reproduces the frozen behaviour" to be stated
precisely: routes are the reused artefacts; engine statuses are preserved; a
listed set of cases is normalised by the adapter.  This tool compares the sealed
v0.1 saved routes with the v0.2 saved routes and writes one row per
(case, method), plus a summary line.

Read-only: it never starts a planner.
"""
import csv
import json
from collections import Counter
from pathlib import Path

V02 = Path(__file__).resolve().parent.parent
OUT = V02.parent
V01_ROUTES = OUT / "artifacts" / "routes"
V02_ROUTES = V02 / "artifacts_v02" / "routes"
TARGET = V02 / "evidence" / "behavior_matrix.csv"


def load(root):
    out = {}
    for path in sorted(root.glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        out[(payload["case_id"], payload["method_id"])] = payload
    return out


def normalisation_reason(v01_status, v02_status, note):
    if v01_status == v02_status:
        return ""
    if v01_status == "finished" and v02_status == "no_legal_route_within_resource":
        return "v0.1 reported a natural finish with an empty route; v0.2 detects it"
    if v01_status == "finished" and v02_status == "resource_exceeded":
        return "v0.1 did not check the resource in the empty-task branch"
    if v02_status == "coverage_incomplete":
        return "v0.2 requires a full legal completion before reporting success"
    return note or "flagged by the shared finalizer"


def main():
    old = load(V01_ROUTES)
    new = load(V02_ROUTES)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for (case_id, method), payload in sorted(new.items()):
        previous = old.get((case_id, method), {})
        old_route = tuple(map(tuple, previous.get("route") or []))
        new_route = tuple(map(tuple, payload.get("route") or []))
        same_route = old_route == new_route
        rows.append({
            "case_id": case_id,
            "method_id": method,
            "v01_status": previous.get("status", "absent"),
            "v02_status": payload.get("status", ""),
            "status_same": str(previous.get("status") == payload.get("status")),
            "route_same": str(same_route),
            "both_empty": str(not old_route and not new_route),
            "v01_steps": previous.get("route_steps", ""),
            "v02_steps": payload.get("route_steps", ""),
            "v02_audit_valid": str((payload.get("audit") or {}).get("valid")),
            "normalisation": normalisation_reason(previous.get("status"),
                                                  payload.get("status"),
                                                  payload.get("reason", "")),
        })

    with open(TARGET, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    same = sum(1 for row in rows if row["route_same"] == "True")
    both_empty = sum(1 for row in rows if row["both_empty"] == "True")
    nonempty_same = sum(1 for row in rows
                        if row["route_same"] == "True" and row["both_empty"] == "False")
    status_same = sum(1 for row in rows if row["status_same"] == "True")
    by_method = Counter(row["method_id"] for row in rows)
    changed = [row for row in rows if row["status_same"] == "False"]

    print(f"wrote {TARGET} with {len(rows)} rows")
    print(f"routes identical to the sealed v0.1 route: {same}/{len(rows)} "
          f"(of which both-empty: {both_empty}; identical non-empty: {nonempty_same})")
    print(f"statuses identical: {status_same}/{len(rows)}")
    print("rows per method: " + json.dumps(dict(by_method), ensure_ascii=False))
    print(f"status changes: {len(changed)}")
    for row in changed:
        print(f"  {row['case_id']:34s} {row['method_id']:14s} "
              f"{row['v01_status']:>32s} -> {row['v02_status']:<34s} {row['normalisation']}")


if __name__ == "__main__":
    main()
