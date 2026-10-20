"""Import bootstrap for the epsilon integration round.

Everything executable is loaded from OUT; the earlier deliveries and
``.remote_Drone`` are read-only and never imported at run time.

Search order (highest priority first):

1. ``OUT/src``            the integrated core, adapter and local protections
2. ``OUT/sources/v03``    the sealed v0.3 finalize / grading (reused verbatim)
3. ``OUT/sources/v02``    the sealed v0.2 Deadline
4. ``OUT/sources/v01``    the sealed request / result / connector / auditor
5. ``OUT/sources/frozen``  ``model.py`` that ``problem.py`` imports

``problem.py`` imports ``FROZEN`` and ``OUT`` from ``bootstrap``; the frozen v2
suite is not used here, so those names are provided as plain values instead of
dragging in the 190 MB dependency tree.
"""
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
SRC = NEW / "src"
V03 = NEW / "sources" / "v03"
V02 = NEW / "sources" / "v02"
V01 = NEW / "sources" / "v01"
FROZEN_SRC = NEW / "sources" / "frozen"
MECHANISM = NEW / "sources" / "mechanism"
LITERATURE = NEW / "sources" / "literature" / "epsilon_star_author_preprint.txt"
PROTOCOL = NEW / "protocol"
ARTIFACTS = NEW / "artifacts"
LOGS = NEW / "logs"
MANIFESTS = NEW / "manifests"
REPORTS = NEW / "reports"
TMP = NEW / "tmp"

#: names the sealed v0.1 modules expect from ``bootstrap``
OUT = NEW
FROZEN = FROZEN_SRC

ORDER = (V01, FROZEN_SRC, V02, V03, SRC)
for _entry in ORDER:
    while str(_entry) in sys.path:
        sys.path.remove(str(_entry))
for _entry in ORDER:                       # later inserts end up earlier
    sys.path.insert(0, str(_entry))


def resolution_report():
    import importlib
    out = {}
    for name in ("problem", "result", "common_geometry", "audit_independent",
                 "model", "deadline", "finalize", "grading",
                 "core.maps", "core.etm", "adapters.registry",
                 "adapters.epsilon_star"):
        try:
            module = importlib.import_module(name)
        except Exception as exc:                      # noqa: BLE001
            out[name] = f"<not importable: {exc}>"
            continue
        out[name] = str(Path(module.__file__).resolve())
    return out


def verify_isolation():
    """Every project module must come from OUT; nothing from an older delivery."""
    report = resolution_report()
    outside = {name: path for name, path in report.items()
               if not path.startswith(str(NEW))}
    if outside:
        raise RuntimeError(f"modules resolved outside OUT: {outside}")
    if Path(report["adapters.registry"]).parent != SRC / "adapters":
        raise RuntimeError("this round's registry did not shadow the v0.3 one")
    return {"out": str(NEW), "order": [str(p) for p in ORDER], "modules": report}
