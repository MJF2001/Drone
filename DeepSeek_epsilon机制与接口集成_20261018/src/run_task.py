"""Execute one planned run and save the full record.

Started as a child process by ``tools/run_batch.py`` so the parent can enforce the
hard watchdog and keep the evidence of a killed attempt.
"""
import argparse
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

import inputs  # noqa: E402
from adapters import registry  # noqa: E402


def safe_name(run_id):
    return run_id.replace(":", "__")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--kind", default="integration")
    parser.add_argument("--case", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--soft", type=float, required=True)
    parser.add_argument("--hard", type=float, required=True)
    parser.add_argument("--max-steps", type=int, default=20000)
    parser.add_argument("--task-set-sha256", default="")
    args = parser.parse_args(argv)

    out_dir = NEW / "artifacts" / "runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{safe_name(args.run_id)}.json"

    registry.CONTEXT.update({
        "batch": args.kind == "integration" and "INTEGRATION" or args.kind.upper(),
        "kind": args.kind,
        "plan_id": args.run_id,
        "run_id": args.run_id,
        "soft_limit": args.soft,
        "task_set_sha256": args.task_set_sha256,
    })

    payload = {"run_id": args.run_id, "kind": args.kind, "case_id": args.case,
               "seed": args.seed, "soft_limit_seconds": args.soft,
               "hard_limit_seconds": args.hard, "max_control_iterations": args.max_steps,
               "started_utc": datetime.now(timezone.utc).isoformat()}
    try:
        request = inputs.load_case(args.case, args.seed, args.soft)
        payload["request"] = request.describe()
        result = registry.run(registry.METHOD_ID, request,
                              max_steps=args.max_steps)
        row = result.as_row(request)
        decisions = list((row.get("meta") or {}).pop("decisions", []) or [])
        payload.update({
            "status": row["status"], "reason": row["reason"],
            "route_steps": row["route_steps"], "audit": row["audit"],
            "resource_check": row["resource_check"],
            "termination": row["termination"], "errors": row["errors"],
            "stage_seconds": row["stage_seconds"], "route": row["route"],
            "meta": _slim(row["meta"]), "covered_physical": row["covered_physical"],
            "pending_remaining": row["pending_remaining"],
            "deferred_remaining": row["deferred_remaining"],
            "finished_utc": datetime.now(timezone.utc).isoformat(),
        })
    except BaseException:                                  # noqa: BLE001
        payload["status"] = "runner_exception"
        payload["traceback"] = traceback.format_exc()
        payload["finished_utc"] = datetime.now(timezone.utc).isoformat()
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        raise

    traces = NEW / "artifacts" / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    (traces / f"{safe_name(args.run_id)}.json").write_text(
        json.dumps({"run_id": args.run_id, "case_id": args.case, "seed": args.seed,
                    "decisions": decisions}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    payload["decision_count"] = len(decisions)

    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "status": payload["status"],
                      "route_steps": payload["route_steps"]}, ensure_ascii=False))
    return 0


def _slim(meta):
    """Keep everything except the per-decision list, which lives in its own file."""
    out = {}
    for key, value in (meta or {}).items():
        if key == "decisions":
            out[key] = {"omitted": "see artifacts/traces", "count": len(value)}
            continue
        text = json.dumps(value, ensure_ascii=False)
        out[key] = value if len(text) <= 6000 else {"omitted": "large", "chars": len(text)}
    return out


if __name__ == "__main__":
    sys.exit(main())
