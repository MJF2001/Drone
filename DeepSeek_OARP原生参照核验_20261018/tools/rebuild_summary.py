"""Rebuild ``artifacts/closed_loop_summary.json`` from the saved artifacts.

The summary is a convenience index; the evidence is the per-case event, plan,
execution and response files.  This tool only re-reads them (it runs no solver) so
that a partial re-run cannot leave the index describing fewer cases than exist.

For a case that was re-run with a prefix (``V2:``), the prefixed responses are the
delivered ones; the earlier attempts stay in the ledger and in
``artifacts/superseded``.
"""
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
ART = NEW / "artifacts"
PROTOCOL = NEW / "protocol"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    cases = load(PROTOCOL / "cases.json")
    responses = []
    for path in sorted((ART / "responses").glob("*.json")):
        payload = load(path)
        responses.append(payload)

    preparations = {}
    for path in sorted((ART / "initial").glob("*.json")):
        payload = load(path)
        preparations[payload["prep"]] = {
            "status": payload["status"], "route_steps": payload["route_steps"],
            "seconds": payload.get("seconds"), "prefix": payload["prefix_steps"],
            "steps": payload["route_steps"]}

    events = []
    for event in cases["events"]:
        case_id = event["case_id"]
        event_file = ART / "events" / f"{case_id}.json"
        if not event_file.is_file():
            continue
        payload = load(event_file)
        state = payload["state"]
        # prefer the prefixed (delivered) attempts when both exist
        # only the newest attempt prefix counts as delivered for this case
        mine = []
        for prefix in ("V3:", "V2:", ""):
            candidate = [r for r in responses
                         if r["case_id"] == case_id
                         and r["plan_id"].startswith(f"{prefix}{case_id}:")]
            if candidate:
                mine = candidate
                break
        rows = []
        for response in sorted(mine, key=lambda r: (r["method_id"], r["cap_override"] or -1)):
            rows.append({"method_id": response["method_id"],
                         "cap": response["cap_override"],
                         "status": response["status"],
                         "steps": response["route_steps"],
                         "fallback": (response.get("flags") or {}).get("fallback_selected"),
                         "valid": (response.get("audit") or {}).get("valid")})
        events.append({"case_id": case_id, "kind": event["kind"],
                       "pending": len(state["pending"]),
                       "deferred": len(state["deferred"]),
                       "remnants": len(payload["remnants"]),
                       "responses": rows})

    summary = {"preparations": preparations, "events": events,
               "rebuilt_by": "tools/rebuild_summary.py",
               "note": "the index is rebuilt from the per-case artifacts; no solver ran"}
    (ART / "closed_loop_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"preparations={len(preparations)} events={len(events)} "
          f"responses={sum(len(e['responses']) for e in events)}")
    for item in events:
        print(f"  {item['case_id']}: pending={item['pending']} "
              f"deferred={item['deferred']} responses={len(item['responses'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
