"""Output contract and timing bookkeeping, revision v0.2.

R3 fix: a stage snapshot is only taken *after* the clock is stopped.  The
end-to-end adapter time is reported once, as ``adapter_call``; internal stages
never contain each other and are never summed to imitate the total.  When a
method has no internal instrumentation, the record says so explicitly instead of
reporting ``0.0`` as if the stage took no time.
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
    """Explicit stage timings.

    ``stage_seconds`` layout produced by :meth:`snapshot`:

        adapter_call : float   end-to-end wall time inside the adapter
        <stage>      : float   one internal stage, disjoint from the others
        _instrumented: [..]    names of stages the method really measures
        _missing     : [..]    stages the method does NOT measure (never faked as 0)
        _total       : float   same value as adapter_call, kept for old readers
        _stopped     : bool    True only after :meth:`stop`

    Reading ``adapter_call`` before :meth:`stop` is what produced the v0.1 bug
    (a real call reported ``adapter_call = 0.0``), so :meth:`snapshot` refuses to
    report a total while the clock is still running.
    """

    def __init__(self):
        self.begin = time.perf_counter()
        self.stages = {}
        self.instrumented = []
        self.missing = []
        self._open = None
        self._stopped = False

    def start(self, name):
        self._open = (name, time.perf_counter())

    def stop(self):
        if self._open is None:
            return
        name, started = self._open
        self.add(name, time.perf_counter() - started)
        self._open = None

    def add(self, name, seconds):
        self.stages[name] = self.stages.get(name, 0.0) + float(seconds)
        if name not in self.instrumented:
            self.instrumented.append(name)

    def declare_missing(self, *names):
        for name in names:
            if name not in self.missing:
                self.missing.append(name)

    def elapsed(self):
        return time.perf_counter() - self.begin

    def stop_total(self):
        """Close the end-to-end measure exactly once."""
        self.stop()
        self.stages["adapter_call"] = self.elapsed()
        if "adapter_call" not in self.instrumented:
            self.instrumented.append("adapter_call")
        self._stopped = True
        return self.stages["adapter_call"]

    def snapshot(self):
        if not self._stopped:
            raise RuntimeError("stage snapshot taken before the clock was stopped (R3)")
        out = {name: value for name, value in self.stages.items()}
        out["_instrumented"] = list(self.instrumented)
        out["_missing"] = list(self.missing)
        out["_total"] = out["adapter_call"]
        out["_stopped"] = True
        return out


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
