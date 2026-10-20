"""Serial batch driver with a per-task hard watchdog and a sealed ledger prefix.

For every row of a frozen plan it starts ``src/run_task.py`` as a child process,
waits at most the row's hard cap, and records what the parent observed: stdout,
stderr, wall time, exit code and termination reason.  If the child never wrote its
``end`` row the parent closes it with an explicit ``hard_timeout``/``runner_crash``
status -- it never fabricates a completion.

At the end the ledger prefix is sealed: appends stay legal, rewrites do not.

Usage:
  python -B -X utf8 tools/run_batch.py --plan protocol/planned_runs.csv --batch INTEGRATION
"""
import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(NEW / "src"))

import bootstrap  # noqa: E402,F401

from adapters.registry import LEDGER, LEDGER_COLUMNS  # noqa: E402

ARTIFACTS = NEW / "artifacts"
MANIFESTS = NEW / "manifests"


def safe_name(run_id):
    return run_id.replace(":", "__").replace("/", "_")


def read_ledger():
    if not LEDGER.is_file():
        return []
    with open(LEDGER, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def append_row(row):
    new = not LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER, "a", newline="", encoding="utf-8-sig" if new else "utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEDGER_COLUMNS)
        if new:
            writer.writeheader()
        writer.writerow({key: row.get(key, "") for key in LEDGER_COLUMNS})
        handle.flush()
        os.fsync(handle.fileno())


def seal(batch):
    raw = LEDGER.read_bytes()
    payload = {"batch": batch, "sealed_utc": datetime.now(timezone.utc).isoformat(),
               "ledger": str(LEDGER.relative_to(NEW)), "bytes": len(raw),
               "lines": raw.count(b"\n"),
               "sha256_of_prefix": hashlib.sha256(raw).hexdigest(),
               "rule": "appends are legal; the first <bytes> bytes must keep this hash"}
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    path = MANIFESTS / f"ledger_seal_{batch}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--kind", default="integration")
    parser.add_argument("--wall-hours", type=float, default=1.0)
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    with open(plan_path, encoding="utf-8-sig", newline="") as handle:
        plan = list(csv.DictReader(handle))

    console = ARTIFACTS / "console"
    console.mkdir(parents=True, exist_ok=True)
    status_path = ARTIFACTS / f"status_{args.batch}.csv"
    fields = ["order_index", "run_id", "case_id", "seed", "state", "termination",
              "wall_seconds", "child_exit", "status", "route_steps", "note"]

    python = sys.executable
    started = time.perf_counter()
    rows_out = []

    for position, row in enumerate(plan, 1):
        run_id = row["run_id"]
        if (time.perf_counter() - started) / 3600.0 > args.wall_hours:
            rows_out.append({"order_index": row["order_index"], "run_id": run_id,
                             "case_id": row["case_id"], "seed": row["seed"],
                             "state": "not_started", "termination": "wall_clock_cap"})
            continue
        already = {r["run_id"] for r in read_ledger() if r.get("phase") == "end"}
        if run_id in already:
            rows_out.append({"order_index": row["order_index"], "run_id": run_id,
                             "case_id": row["case_id"], "seed": row["seed"],
                             "state": "already_recorded", "termination": "skipped_existing"})
            continue

        hard = float(row["hard_limit_seconds"])
        env = dict(os.environ)
        env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
                    "PYTHONIOENCODING": "utf-8",
                    "TEMP": str(NEW / "tmp" / args.batch),
                    "TMP": str(NEW / "tmp" / args.batch)})
        Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)

        command = [python, "-B", "-X", "utf8", str(NEW / "src" / "run_task.py"),
                   "--run-id", run_id, "--kind", args.kind, "--case", row["case_id"],
                   "--seed", row["seed"], "--soft", row["soft_limit_seconds"],
                   "--hard", str(hard), "--max-steps", row["max_control_iterations"],
                   "--task-set-sha256", plan_hash]
        begin = time.perf_counter()
        termination = "exit"
        note = ""
        try:
            completed = subprocess.run(command, env=env, cwd=str(NEW / "src"),
                                       capture_output=True, text=True,
                                       timeout=hard + 3.0, check=False)
            stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as exc:
            termination = "hard_timeout"
            stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            code = -1
            note = f"killed at the hard cap {hard + 3.0:.0f}s"
        wall = time.perf_counter() - begin

        (console / f"{safe_name(run_id)}.out").write_text(stdout or "", encoding="utf-8")
        (console / f"{safe_name(run_id)}.err").write_text(stderr or "", encoding="utf-8")

        result_path = ARTIFACTS / "runs" / f"{safe_name(run_id)}.json"
        payload = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else None

        ends = {r["run_id"] for r in read_ledger() if r.get("phase") == "end"}
        if run_id not in ends:
            start_row = next((r for r in read_ledger()
                              if r.get("run_id") == run_id and r.get("phase") == "start"), {})
            tail = (stderr or "").strip().splitlines()
            append_row({**start_row, "phase": "end",
                        "status": "hard_timeout" if termination == "hard_timeout" else "runner_crash",
                        "natural": "False",
                        "call_total_seconds": f"{wall:.6f}",
                        "note": note or (tail[-1][:200] if tail else "no stderr capture")})
            note = note or "parent wrote the missing end row"

        state = "ok" if code == 0 and payload and payload.get("status") not in (
            None, "runner_exception") else termination
        rows_out.append({
            "order_index": row["order_index"], "run_id": run_id, "case_id": row["case_id"],
            "seed": row["seed"], "state": state, "termination": termination,
            "wall_seconds": f"{wall:.3f}", "child_exit": code,
            "status": (payload or {}).get("status", ""),
            "route_steps": (payload or {}).get("route_steps", ""), "note": note,
        })
        with open(status_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows_out)
        print(f"[{position}/{len(plan)}] {run_id}  {state:12s} {wall:6.2f}s "
              f"{(payload or {}).get('status', '')}", flush=True)

    with open(status_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_out)

    summary = {
        "batch": args.batch, "plan": str(plan_path), "plan_sha256": plan_hash,
        "planned": len(plan),
        "executed": sum(1 for row in rows_out
                        if row["state"] not in ("not_started", "already_recorded")),
        "not_started": sum(1 for row in rows_out if row["state"] == "not_started"),
        "hard_timeouts": sum(1 for row in rows_out if row["termination"] == "hard_timeout"),
        "wall_seconds_total": round(time.perf_counter() - started, 1),
        "seal": seal(args.batch),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    (ARTIFACTS / f"batch_{args.batch}.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("planned", "executed", "not_started",
                                              "hard_timeouts", "wall_seconds_total")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
