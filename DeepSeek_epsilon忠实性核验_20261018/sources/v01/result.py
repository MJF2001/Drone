"""Output contract shared by every adapter.

Required fields, all of them serialised even when a method failed:

    method_id, method_version, status, reason, route (cell by cell),
    route_steps, covered_physical, resource_check, termination,
    fallback_used, fallback_steps, best_candidate_source, final_source,
    stage_seconds, errors, meta

``route`` is stored exactly as produced; the auditor recomputes everything from
it.  A method that returns no legal route still produces a record.
"""
import json
import time
from dataclasses import dataclass, field, asdict


def _tupleify(route):
    return tuple((int(p[0]), int(p[1])) for p in route)


@dataclass
class PlanResult:
    method_id: str
    method_version: str
    status: str
    reason: str = ""
    route: tuple = ()
    resource_check: dict = field(default_factory=dict)
    termination: dict = field(default_factory=dict)
    fallback_used: bool = False
    fallback_steps: int = None
    best_candidate_source: str = ""
    final_source: str = ""
    stage_seconds: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    audit: dict = None

    def __post_init__(self):
        self.route = _tupleify(self.route) if self.route else ()

    @property
    def route_steps(self):
        return len(self.route) - 1 if self.route else None

    @property
    def covered_physical(self):
        """Targets physically touched by the route, on top of the given ledger."""
        if not self.audit:
            return frozenset()
        return frozenset(map(tuple, self.audit.get("covered_physical", [])))

    def as_row(self, request=None):
        row = asdict(self) if not isinstance(self, dict) else dict(self)
        row["route"] = [list(p) for p in self.route]
        row["route_steps"] = self.route_steps
        row["covered_physical"] = [list(p) for p in sorted(self.covered_physical)]
        if request is not None:
            row["request"] = request.describe()
            row["pending_remaining"] = [list(p) for p in sorted(request.pending)]
            row["deferred_remaining"] = [list(p) for p in sorted(request.deferred)]
        return row


class StageClock:
    """Explicit stage timings.  Missing stages stay missing; nothing is inferred."""

    def __init__(self):
        self.begin = time.perf_counter()
        self.stages = {}
        self._open = None

    def start(self, name):
        self._open = (name, time.perf_counter())

    def stop(self):
        if self._open is None:
            return
        name, started = self._open
        self.stages[name] = self.stages.get(name, 0.0) + (time.perf_counter() - started)
        self._open = None

    def add(self, name, seconds):
        self.stages[name] = self.stages.get(name, 0.0) + seconds

    def elapsed(self):
        return time.perf_counter() - self.begin

    def as_dict(self):
        out = dict(self.stages)
        out["_total"] = self.elapsed()
        return out


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
