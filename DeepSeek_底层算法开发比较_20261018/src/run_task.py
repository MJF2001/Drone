"""Execute exactly one planned run and save its full record.

Started by ``tools/run_batch.py`` as a child process, so the parent can enforce a
hard per-task cap and keep the evidence of a killed attempt.

Everything is written inside NEW:

    runs/<batch>/results/<run_id>.json   full record: route, audit, status, timings
    runs/<batch>/console/<run_id>.out     child stdout (the summary line)
    runs/<batch>/console/<run_id>.err     child stderr

The child writes its own ``start``/``end`` ledger rows through the registry; the
parent adds an ``end`` row only when the child never got to write one.
"""
import argparse
import datetime
import json
import os
import sys
import traceback
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402
from adapters import registry  # noqa: E402
import inputs  # noqa: E402

PROTOCOL = NEW / "protocol"


def safe_name(run_id):
    return run_id.replace(":", "__").replace("/", "_").replace("\\", "_")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--kind", default="development")
    parser.add_argument("--case", required=True)
    parser.add_argument("--method", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--soft", type=float, required=True)
    parser.add_argument("--hard", type=float, required=True)
    parser.add_argument("--task-set-sha256", default="")
    args = parser.parse_args(argv)

    out_dir = NEW / "runs" / args.batch / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{safe_name(args.run_id)}.json"

    registry.CONTEXT.update({
        "batch": args.batch, "kind": args.kind,
        "plan_id": f"{args.case}::{args.method}",
        "run_id": args.run_id, "soft_limit": args.soft,
        "task_set_sha256": args.task_set_sha256,
    })

    payload = {"run_id": args.run_id, "batch": args.batch, "kind": args.kind,
               "case_id": args.case, "method_id": args.method, "seed": args.seed,
               "soft_limit_seconds": args.soft, "hard_limit_seconds": args.hard,
               "interpreter": sys.executable,
               "module_paths": {}, "started_utc": None}
    try:
        payload["started_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        request = inputs.build_any(args.case, args.soft, args.seed)
        payload["input"] = request.describe()
        payload["module_paths"] = {
            name: path for name, path in registry.source_digest(args.method)["files"].items()}
        result = registry.run(args.method, request)
        row = result.as_row(request)
        payload.update({
            "status": row.get("status"), "reason": row.get("reason"),
            "route_steps": row.get("route_steps"),
            "audit": row.get("audit"), "resource_check": row.get("resource_check"),
            "termination": row.get("termination"),
            "fallback_used": row.get("fallback_used"),
            "fallback_steps": row.get("fallback_steps"),
            "final_source": row.get("final_source"),
            "best_candidate_source": row.get("best_candidate_source"),
            "stage_seconds": row.get("stage_seconds"),
            "errors": row.get("errors"),
            "core_version": (row.get("meta") or {}).get("core_version"),
            "adapter_version": (row.get("meta") or {}).get("adapter_version"),
            "source_sha256": (row.get("meta") or {}).get("source_sha256"),
            "call_total_seconds": (row.get("meta") or {}).get("call_total_seconds"),
            "within_budget": (row.get("meta") or {}).get("within_budget"),
            "budget_overrun_seconds": (row.get("meta") or {}).get("budget_overrun_seconds"),
            "ledger_write_error": (row.get("meta") or {}).get("ledger_write_error"),
            "route": row.get("route"),
            "meta": _slim_meta(row.get("meta") or {}),
            "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
    except BaseException:                      # noqa: BLE001 - record, never hide
        payload["status"] = "runner_exception"
        payload["traceback"] = traceback.format_exc()
        payload["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        raise

    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "status": payload["status"],
                      "route_steps": payload["route_steps"],
                      "call_total": payload["call_total_seconds"],
                      "within_budget": payload["within_budget"]}, ensure_ascii=False))
    return 0


def _slim_meta(meta):
    """Keep the report-relevant metadata but bound the size of one record."""
    out = {}
    for key, value in meta.items():
        if key in ("diagnostic_route", "diagnostic_audit"):
            out[key] = {"omitted": "large", "route_steps": len(value) - 1
                        if isinstance(value, list) and value else None}
            continue
        if key == "etm" and isinstance(value, dict):
            out[key] = {k: v for k, v in value.items() if k != "decisions"}
            continue
        text = json.dumps(value, ensure_ascii=False)
        out[key] = value if len(text) <= 4000 else {"omitted": "large", "chars": len(text)}
    return out


if __name__ == "__main__":
    sys.exit(main())
