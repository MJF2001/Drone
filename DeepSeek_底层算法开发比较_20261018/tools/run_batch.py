"""Serial batch driver with a per-task hard watchdog.

For every row of a frozen plan it starts ``src/run_task.py`` as a child process,
waits at most the row's hard cap, and keeps everything the parent observed:

* the child's stdout/stderr,
* the wall time of the whole task (including interpreter start-up),
* the termination reason (``exit``, ``hard_timeout``, ``crash``),
* an ``end`` ledger row when the child never managed to write one.

No task is retried, a successful task is never rerun, and a task that never
started gets no fabricated row.

At the end it seals the ledger prefix for this batch.
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

import bootstrap  # noqa: E402
from adapters.registry import LEDGER, LEDGER_COLUMNS  # noqa: E402,F401

RUNS = NEW / "runs"
MANIFESTS = NEW / "manifests"


def safe_name(run_id):
    return run_id.replace(":", "__").replace("/", "_").replace("\\", "_")


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
               "lines": raw.count(b"\n"), "sha256_of_prefix": hashlib.sha256(raw).hexdigest(),
               "rule": "appends are legal; the first <bytes> bytes must keep this hash"}
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    path = MANIFESTS / f"ledger_seal_{batch}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--batch", required=True)
    parser.add_argument("--kind", default="development")
    parser.add_argument("--wall-hours", type=float, default=6.0)
    parser.add_argument("--limit", type=int, default=0, help="stop after N tasks (0 = all)")
    parser.add_argument("--only-batch", default=None, help="run only rows of this batch")
    args = parser.parse_args(argv)

    plan_path = Path(args.plan)
    plan_bytes = plan_path.read_bytes()
    task_hash = hashlib.sha256(plan_bytes).hexdigest()
    with open(plan_path, encoding="utf-8-sig", newline="") as handle:
        plan = list(csv.DictReader(handle))
    if args.only_batch:
        plan = [row for row in plan if row.get("batch") == args.only_batch]

    out_dir = RUNS / args.batch
    (out_dir / "console").mkdir(parents=True, exist_ok=True)
    (out_dir / "task_set.json").write_text(
        json.dumps({"plan": str(plan_path), "sha256": task_hash,
                    "rows": len(plan)}, ensure_ascii=False, indent=1), encoding="utf-8")
    status_path = out_dir / "status.csv"
    status_fields = ["order_index", "run_id", "case_id", "method_id", "seed", "state",
                     "termination", "wall_seconds", "child_exit", "call_total_seconds",
                     "route_steps", "status", "within_budget", "note"]

    python = sys.executable
    started = time.perf_counter()
    rows_out = []
    known_end = {row["run_id"] for row in read_ledger() if row.get("phase") == "end"}
    ledger_rows_before = len(read_ledger())

    for position, row in enumerate(plan, 1):
        run_id = row["run_id"]
        elapsed_hours = (time.perf_counter() - started) / 3600.0
        if elapsed_hours > args.wall_hours:
            rows_out.append({**{k: row[k] for k in ("order_index", "run_id", "case_id",
                                                    "method_id", "seed")},
                             "state": "not_started", "termination": "wall_clock_cap",
                             "note": f"wall clock cap {args.wall_hours}h reached"})
            continue
        if args.limit and position > args.limit:
            rows_out.append({**{k: row[k] for k in ("order_index", "run_id", "case_id",
                                                    "method_id", "seed")},
                             "state": "not_started", "termination": "limit_flag"})
            continue
        if run_id in known_end:
            rows_out.append({**{k: row[k] for k in ("order_index", "run_id", "case_id",
                                                    "method_id", "seed")},
                             "state": "already_recorded", "termination": "skipped_existing"})
            continue

        soft = float(row["soft_limit_seconds"])
        hard = float(row["hard_limit_seconds"])
        env = dict(os.environ)
        env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONUTF8": "1",
                    "PYTHONIOENCODING": "utf-8",
                    "TEMP": str(NEW / "tmp" / args.batch),
                    "TMP": str(NEW / "tmp" / args.batch),
                    "DSH_CACHE": str(NEW / "tmp" / "cache" / args.batch)})
        Path(env["TEMP"]).mkdir(parents=True, exist_ok=True)
        Path(env["DSH_CACHE"]).mkdir(parents=True, exist_ok=True)

        command = [python, "-B", "-X", "utf8", str(NEW / "src" / "run_task.py"),
                   "--run-id", run_id, "--batch", args.batch, "--kind", args.kind,
                   "--case", row["case_id"], "--method", row["method_id"],
                   "--seed", row["seed"], "--soft", str(soft), "--hard", str(hard),
                   "--task-set-sha256", task_hash]
        begin = time.perf_counter()
        termination = "exit"
        note = ""
        try:
            completed = subprocess.run(command, env=env, cwd=str(NEW / "src"),
                                       capture_output=True, text=True,
                                       timeout=hard + 5.0, check=False)
            stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired as exc:
            termination = "hard_timeout"
            stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            code = -1
            note = f"killed at the hard cap {hard + 5.0:.0f}s"
        wall = time.perf_counter() - begin

        console = out_dir / "console"
        (console / f"{safe_name(run_id)}.out").write_text(stdout or "", encoding="utf-8")
        (console / f"{safe_name(run_id)}.err").write_text(stderr or "", encoding="utf-8")

        result_path = out_dir / "results" / f"{safe_name(run_id)}.json"
        payload = None
        if result_path.is_file():
            payload = json.loads(result_path.read_text(encoding="utf-8"))

        # re-read: the child may have written its own end row for this run
        current_ends = {row["run_id"] for row in read_ledger() if row.get("phase") == "end"}
        if run_id not in current_ends:
            # the child died before writing its end row: the parent closes it
            record = read_ledger()
            start_row = next((r for r in record
                              if r.get("run_id") == run_id and r.get("phase") == "start"), {})
            tail = (stderr or "").strip().splitlines()
            parent_note = note or (tail[-1][:200] if tail else "no stderr capture")
            append_row({**start_row, "phase": "end",
                        "status": "hard_timeout" if termination == "hard_timeout" else "runner_crash",
                        "natural": "False", "within_budget": "False",
                        "call_total_seconds": f"{wall:.6f}",
                        "note": parent_note})
            known_end.add(run_id)
            note = note or "parent wrote the missing end row"

        state = "ok" if code == 0 and payload and payload.get("status") not in (None, "runner_exception") else termination
        rows_out.append({
            "order_index": row["order_index"], "run_id": run_id, "case_id": row["case_id"],
            "method_id": row["method_id"], "seed": row["seed"], "state": state,
            "termination": termination, "wall_seconds": f"{wall:.3f}",
            "child_exit": code,
            "call_total_seconds": (payload or {}).get("call_total_seconds", ""),
            "route_steps": (payload or {}).get("route_steps", ""),
            "status": (payload or {}).get("status", ""),
            "within_budget": (payload or {}).get("within_budget", ""),
            "note": note,
        })
        with open(status_path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=status_fields)
            writer.writeheader()
            writer.writerows(rows_out)
        print(f"[{position}/{len(plan)}] {run_id}  {state:12s} {wall:7.2f}s "
              f"steps={(payload or {}).get('route_steps')}", flush=True)

    with open(status_path, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=status_fields)
        writer.writeheader()
        writer.writerows(rows_out)

    seal_info = seal(args.batch)
    started_rows = ledger_rows_before
    final_rows = len(read_ledger())
    summary = {
        "batch": args.batch, "plan": str(plan_path), "planned": len(plan),
        "executed": sum(1 for r in rows_out if r["state"] not in ("not_started", "already_recorded", "skipped_existing")),
        "not_started": sum(1 for r in rows_out if r["state"] == "not_started"),
        "hard_timeouts": sum(1 for r in rows_out if r["termination"] == "hard_timeout"),
        "crashes": sum(1 for r in rows_out if r["termination"] not in ("exit", "hard_timeout")),
        "wall_seconds_total": round(time.perf_counter() - started, 1),
        "ledger_rows_before": started_rows, "ledger_rows_after": final_rows,
        "seal": seal_info,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "batch_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("planned", "executed", "not_started",
                                              "hard_timeouts", "crashes",
                                              "wall_seconds_total")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
