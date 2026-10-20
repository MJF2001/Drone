"""Import bootstrap for this round.

Everything is resolved inside NEW; no module is imported from, and no file is
written to, the earlier deliveries or ``.remote_Drone``.

Resolution order (highest priority first):

1. ``NEW/src``            the modules changed in this round (bootstrap, registry, epsilon-star)
2. ``NEW/sources/v03``     revision v0.3 modules (finalize, grading, deadline, ...)
3. ``NEW/sources/v02``     revision v0.2 modules (epsilon_core, cstar, reference_methods, ...)
4. ``NEW/sources/v01``     sealed v0.1 modules (common_geometry, audit_independent, ...)
5. the frozen v2 source and the pinned deps installed by ``portable_frozen``

This module also carries the names the v0.1 modules expect from ``bootstrap``
(``OUT``, ``FROZEN``), because ``sources/v01/bootstrap.py`` cannot work from its
new location.
"""
import json
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
SOURCES = NEW / "sources"
REF = SOURCES / "reference_tree"
ALGO = REF / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
FROZEN = ALGO / "frozen_baselines" / "v2_20261012"
CANDIDATE = ALGO / "candidate_baselines" / "PPCPP_CORE4" / "v0.1_20261014"
SRC_NEW = NEW / "src"
SRC_V03 = SOURCES / "v03"
SRC_V02 = SOURCES / "v02"
SRC_V01 = SOURCES / "v01"
TMP = NEW / "tmp"
PROTOCOL = NEW / "protocol"
RUNS = NEW / "runs"
LOGS = NEW / "logs"
MANIFESTS = NEW / "manifests"
CASES = SOURCES / "cases"
MICRO = SOURCES / "micro"

#: the sealed delivery root, kept as ``OUT`` because v0.1 modules import that name
OUT = NEW

ORDER = (SRC_V01, SRC_V02, SRC_V03, SRC_NEW)
for _entry in ORDER + (REF, CANDIDATE, TMP):
    while str(_entry) in sys.path:
        sys.path.remove(str(_entry))
for _entry in ORDER:                      # later inserts end up earlier
    sys.path.insert(0, str(_entry))
for _entry in (REF, CANDIDATE, TMP):      # lower priority than the module trees
    sys.path.append(str(_entry))

import portable_frozen  # noqa: E402  (installs FROZEN/source and .deps at the front)

PROFILE = portable_frozen.PROFILE


def load_ppcpp_candidate():
    """Load the PPCPP candidate through its own manifest-checking loader.

    Provided here because the v0.2 adapter module calls
    ``bootstrap.load_ppcpp_candidate()`` and this round replaces ``bootstrap``.
    """
    import load_candidate
    return load_candidate


def resolution_report():
    import importlib
    report = {}
    for name in ("bootstrap", "problem", "result", "finalize", "grading", "deadline",
                 "audit_independent", "common_geometry",
                 "epsilon_core.maps", "epsilon_core.etm",
                 "adapters.registry", "adapters.epsilon_star", "adapters.cstar",
                 "adapters.reference_methods", "cstar_core.planner",
                 "model", "baseline_suite", "portable_frozen"):
        module = importlib.import_module(name)
        report[name] = str(Path(module.__file__).resolve())
    return report


def verify_isolation():
    """Assert that every planner module really comes from inside NEW."""
    report = resolution_report()
    outside = {name: path for name, path in report.items()
               if not Path(path).is_relative_to(NEW)}
    if outside:
        raise RuntimeError(f"modules resolved outside NEW: {outside}")
    if Path(report["adapters.registry"]).parent != SRC_NEW / "adapters":
        raise RuntimeError("this round's registry did not shadow the earlier one")
    return {"new_root": str(NEW), "search_order": [str(p) for p in ORDER],
            "frozen": str(FROZEN), "modules": report}
