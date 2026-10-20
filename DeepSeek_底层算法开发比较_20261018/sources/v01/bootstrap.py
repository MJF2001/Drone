"""Isolation bootstrap.

Every execution of this delivery runs the OUT-local copies of the historical
sources.  Nothing here imports from ``.remote_Drone`` at run time: the SRC tree
is only read once, by ``tmp/stage_a_copy.py``, to produce
``sources/reference_tree``.

Import order matters and is deliberate:

``portable_frozen`` is imported from ``sources/reference_tree`` and installs
``frozen_baselines/v2_20261012/source`` (and the pinned ``.deps``) at the front
of ``sys.path``.  Adding the enclosing ``算法小型验证_20261010`` directory to
``sys.path`` would shadow the frozen ``baseline_suite``/``model``/``audit`` with
the newer working copies, which the PPCPP candidate integrity check rejects on
purpose.  So this module never adds that directory.
"""
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
REF = OUT / "sources" / "reference_tree"
ALGO = REF / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
FROZEN = ALGO / "frozen_baselines" / "v2_20261012"
CANDIDATE = ALGO / "candidate_baselines" / "PPCPP_CORE4" / "v0.1_20261014"
CSTAR_SRC = OUT / "sources" / "cstar_historical"
ARTIFACTS = OUT / "artifacts"
LOGS = OUT / "logs"
TMP = OUT / "tmp"
FIXTURES = OUT / "tests" / "fixtures"

for _path in (REF, CANDIDATE, TMP):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import portable_frozen  # noqa: E402  (installs the frozen source and .deps)


def _check_inside(path, label):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(OUT.resolve()):
        raise RuntimeError(f"{label} resolved outside OUT: {resolved}")
    return resolved


def verify_isolation():
    """Assert that the imported planner code really lives in the OUT copy."""
    import baseline_suite
    import model
    report = {
        "out": str(OUT),
        "frozen": str(_check_inside(portable_frozen.FROZEN, "portable_frozen.FROZEN")),
        "baseline_suite": str(_check_inside(baseline_suite.__file__, "baseline_suite")),
        "model": str(_check_inside(model.__file__, "model")),
        "methods": list(portable_frozen.METHODS),
        "sys_path_head": sys.path[:5],
    }
    if Path(baseline_suite.__file__).resolve().parent != (FROZEN / "source").resolve():
        raise RuntimeError("frozen source is not first on sys.path")
    return report


def load_ppcpp_candidate():
    """Load the PPCPP_CORE4 v0.1 candidate through its own integrity-checking loader."""
    import load_candidate
    return load_candidate


def profile():
    return portable_frozen.PROFILE
