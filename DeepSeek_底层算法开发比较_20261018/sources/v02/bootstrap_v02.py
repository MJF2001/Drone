"""v0.2 import bootstrap: patched modules first, sealed v0.1 modules second.

Nothing in ``../src`` is modified.  This module only decides resolution order:

1. ``revision_v0.2/src_v02``          the changed/new modules of this revision
2. ``../src``                          the sealed v0.1 modules (read-only)
3. the frozen v2 source + pinned deps installed by v0.1's ``bootstrap``

The sealed v0.1 tree keeps its own hashes; ``verify_v02.py`` checks that none of
its files changed.
"""
import sys
from pathlib import Path

V02 = Path(__file__).resolve().parent.parent          # revision_v0.2
OUT = V02.parent                                      # the sealed v0.1 delivery root
SRC_V02 = V02 / "src_v02"
SRC_V01 = OUT / "src"

# Resolution order is set explicitly, not left to whichever path was already in
# sys.path: a caller that put src_v02 on sys.path to import this module would
# otherwise leave src_v01 *ahead* of it and silently reuse the v0.1 modules.
for _entry in (str(SRC_V01), str(SRC_V02)):
    while _entry in sys.path:
        sys.path.remove(_entry)
sys.path.insert(0, str(SRC_V01))
sys.path.insert(0, str(SRC_V02))

import bootstrap as v01_bootstrap  # noqa: E402  (installs frozen source + deps)


def resolution_report():
    """Which modules come from v0.2 and which are reused read-only from v0.1."""
    import importlib
    report = {}
    for name in ("problem", "result", "audit_independent", "finalize", "deadline",
                 "epsilon_core.maps", "epsilon_core.etm",
                 "adapters.registry", "adapters.epsilon_star", "adapters.cstar",
                 "adapters.reference_methods", "cstar_core.planner", "model",
                 "baseline_suite"):
        module = importlib.import_module(name)
        report[name] = str(Path(module.__file__).resolve())
    return report


def verify_isolation():
    """v0.1's own isolation check, plus a v0.2 assertion."""
    base = v01_bootstrap.verify_isolation()
    import adapters.epsilon_star as epsilon_star
    if not Path(epsilon_star.__file__).resolve().is_relative_to(SRC_V02):
        raise RuntimeError("v0.2 adapter did not shadow the v0.1 module")
    base["v02_source"] = str(SRC_V02)
    return base
