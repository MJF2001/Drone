"""Load the 10 real continuous-history development states into the unified input.

Authoritative source (verified this round):

``.remote_Drone/.../continuous_history_diagnostics/preparation_verification_v0.1_20261016/cases/*.json``
copied to ``sources/cases/``.  Those files are byte-identical to the independent
replay copy in ``saved_initial_route_replay_v0.1_20261016`` and match the hash
manifest ``preparation_verification.../sha256.json``.

What the files are:

* ``free``             F, the currently published free cells
* ``targets``          P ∩ F, i.e. published targets that are still free
* ``covered``          C, the real coverage ledger
* ``metadata.published_targets``  P (may contain a covered-but-now-blocked cell)
* ``metadata.deferred_targets``   D = (P − C) − F, deferred, never completed
* ``metadata.initial_targets``    pre-event targets (used only as the OARP rank reference)
* ``current`` / ``base`` / ``old_route`` / ``distance_budget``  as recorded

The post-event authority is the state *after* the event was published; the files
under ``preparation_v0.1_20261016`` are pre-event initial plans and are NOT used
as states.
"""
import hashlib
import json
from pathlib import Path

import bootstrap
from problem import PlanRequest, Termination

CASES_DIR = bootstrap.CASES
CASE_MANIFEST = bootstrap.SOURCES / "cases_manifest" / "sha256.json"
PROVENANCE = bootstrap.SOURCES / "cases_manifest" / "report_record.json"

#: fixed by the execution draft (section 7); the order is only presentation
MAP_IDS = ("small_g2_development", "small_g3_development", "small_g4_development",
           "medium_g1_development", "medium_g2_development", "medium_g4_development",
           "large_g1_development", "large_g2_development", "large_g3_development",
           "large_g4_development")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def case_path(map_id):
    return CASES_DIR / f"{map_id}.json"


def raw_case(map_id):
    return json.loads(case_path(map_id).read_text(encoding="utf-8"))


def describe(map_id):
    """Sizes and provenance for the input index."""
    payload = raw_case(map_id)
    meta = payload["metadata"]
    published = frozenset(map(tuple, meta["published_targets"]))
    covered = frozenset(map(tuple, payload["covered"]))
    free = frozenset(map(tuple, payload["free"]))
    pending = (published - covered) & free
    deferred = (published - covered) - free
    path = case_path(map_id)
    return {
        "map_id": map_id,
        "name": payload["name"],
        "source_path": str(path),
        "source_sha256": sha256(path),
        "event": meta.get("event"),
        "split": meta.get("split"),
        "actual_progress": meta.get("actual_progress"),
        "free": len(free),
        "published": len(published),
        "targets_in_free": len(payload["targets"]),
        "covered": len(covered),
        "pending": len(pending),
        "deferred": len(deferred),
        "deferred_cells": [list(p) for p in sorted(deferred)],
        "current": list(payload["current"]),
        "base": list(payload["base"]),
        "old_route_len": len(payload["old_route"]),
        "distance_budget": payload["distance_budget"],
        "radius": payload["radius"],
        "initial_targets": len(meta["initial_targets"]),
    }


def build(map_id, seconds, seed, natural="method_specific"):
    """Normalise one saved state into the unified request."""
    payload = raw_case(map_id)
    meta = payload["metadata"]
    return PlanRequest(
        case_id=map_id,
        free=frozenset(map(tuple, payload["free"])),
        published_targets=frozenset(map(tuple, meta["published_targets"])),
        covered=frozenset(map(tuple, payload["covered"])),
        current=tuple(payload["current"]),
        base=tuple(payload["base"]),
        old_route=tuple(map(tuple, payload["old_route"])),
        remaining_resource=payload["distance_budget"],
        seed=seed,
        termination=Termination(time_limit_seconds=float(seconds), natural=natural),
        initial_targets=frozenset(map(tuple, meta["initial_targets"])),
        meta={"map_id": map_id, "event": meta.get("event"), "split": meta.get("split"),
              "authoritative_source": str(case_path(map_id)),
              "source_sha256": sha256(case_path(map_id))},
    )


def build_fixture(path, seconds, seed, natural="method_specific"):
    """Normalise one synthetic preflight fixture (same ``grid`` shape)."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    grid = payload["grid"]
    return PlanRequest(
        case_id=payload["case_id"],
        free=frozenset(map(tuple, grid["free"])),
        published_targets=frozenset(map(tuple, grid["published_targets"])),
        covered=frozenset(map(tuple, grid["covered"])),
        current=tuple(grid["current"]),
        base=tuple(grid["base"]),
        old_route=tuple(map(tuple, grid["old_route"])),
        remaining_resource=grid["remaining_resource"],
        seed=seed,
        termination=Termination(time_limit_seconds=float(seconds), natural=natural),
        initial_targets=frozenset(map(tuple, grid["initial_targets"])),
        meta={"map_id": payload["case_id"], "synthetic": True,
              "authoritative_source": str(path), "source_sha256": sha256(path)},
    )


def build_any(case_id, seconds, seed, natural="method_specific"):
    """Dispatch between a real development state and a synthetic preflight map."""
    if case_id.startswith("pf_"):
        return build_fixture(bootstrap.NEW / "preflight" / "inputs" / f"{case_id}.json",
                             seconds, seed, natural)
    return build(case_id, seconds, seed, natural)


def verify_sources():
    """Check the copied cases against their own manifest and the replay copy."""
    known = json.loads(CASE_MANIFEST.read_text(encoding="utf-8"))
    # the manifest uses Windows separators; normalise before looking up
    normalised = {key.replace("\\", "/"): value for key, value in known.items()}
    problems = []
    for map_id in MAP_IDS:
        relative = f"cases/{map_id}.json"
        expected = normalised.get(relative)
        if expected is None:
            problems.append(f"{map_id}: not listed in the verification manifest")
            continue
        actual = sha256(case_path(map_id))
        if actual != expected:
            problems.append(f"{map_id}: hash {actual[:16]} != manifest {expected[:16]}")
        replay = bootstrap.SOURCES / "replay_cases" / f"{map_id}.json"
        if not replay.is_file():
            problems.append(f"{map_id}: replay copy missing")
        elif sha256(replay) != actual:
            problems.append(f"{map_id}: replay copy differs from the verified copy")
    return {"ok": not problems, "problems": problems,
            "manifest": str(CASE_MANIFEST), "checked": len(MAP_IDS)}
