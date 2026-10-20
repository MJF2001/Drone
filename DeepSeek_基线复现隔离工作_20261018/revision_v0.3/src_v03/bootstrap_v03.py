"""v0.3 import bootstrap: v0.3 -> v0.2 -> v0.1, all read-only except v0.3.

Resolution order is explicit and deduplicated so a caller that already put
``src_v03`` on ``sys.path`` cannot end up with an older module winning.
"""
import sys
from pathlib import Path

V03 = Path(__file__).resolve().parent.parent          # revision_v0.3
OUT = V03.parent                                      # the sealed v0.1 delivery root
V02 = OUT / "revision_v0.2"
SRC_V03 = V03 / "src_v03"
SRC_V02 = V02 / "src_v02"
SRC_V01 = OUT / "src"

ORDER = (SRC_V01, SRC_V02, SRC_V03)
for _entry in ORDER:
    while str(_entry) in sys.path:
        sys.path.remove(str(_entry))
for _entry in ORDER:            # inserted at 0 in order -> last one ends up first
    sys.path.insert(0, str(_entry))

import bootstrap as v01_bootstrap  # noqa: E402  (installs frozen source + deps)


def resolution_report():
    import importlib
    report = {}
    for name in ("problem", "result", "finalize", "deadline", "audit_independent",
                 "epsilon_core.maps", "epsilon_core.etm",
                 "adapters.registry", "adapters.epsilon_star", "adapters.cstar",
                 "adapters.reference_methods", "cstar_core.planner", "model",
                 "baseline_suite"):
        module = importlib.import_module(name)
        report[name] = str(Path(module.__file__).resolve())
    return report


def verify_isolation():
    base = v01_bootstrap.verify_isolation()
    import adapters.registry as registry
    import adapters.epsilon_star as epsilon_star
    import finalize as finalize_module
    for module, label in ((registry, "registry"), (epsilon_star, "epsilon_star"),
                          (finalize_module, "finalize")):
        if not Path(module.__file__).resolve().is_relative_to(SRC_V03):
            raise RuntimeError(f"v0.3 module did not shadow {label}")
    base["v03_source"] = str(SRC_V03)
    base["v03_search_order"] = [str(p) for p in ORDER]
    return base
