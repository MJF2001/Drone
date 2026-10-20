"""Import bootstrap for the OARP native-reference round.

All project modules come from OUT.  The only things taken from outside are the
locked external dependencies (SCIP / GLNS) and the read-only interpreter, both of
which the execution brief explicitly allows without copying.

Search order (highest priority first):

1. ``OUT/src``                  native structures, the two references, the entry
2. ``OUT/sources/v03``          sealed finalize / grading
3. ``OUT/sources/v02``          sealed Deadline
4. ``OUT/sources/v01``          sealed request / result / connector / auditor
5. ``OUT/sources/frozen/source``  the frozen v2 ``model`` module and ``oarp_replan``
6. ``<reference_tree>/.deps``   locked external deps (read-only, never written)
"""
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
SRC = NEW / "src"
V03 = NEW / "sources" / "v03"
V02 = NEW / "sources" / "v02"
V01 = NEW / "sources" / "v01"
FROZEN = NEW / "sources" / "frozen" / "source"
PROBE = NEW / "sources" / "probe"
LITERATURE = NEW / "sources" / "literature"
PROTOCOL = NEW / "protocol"
ARTIFACTS = NEW / "artifacts"
LOGS = NEW / "logs"
MANIFESTS = NEW / "manifests"
REPORTS = NEW / "reports"
TMP = NEW / "tmp"

WORKSPACE = NEW.parent
REFERENCE_TREE = (WORKSPACE / "DeepSeek_底层算法开发比较_20261018" / "sources"
                  / "reference_tree")
DEPS = (REFERENCE_TREE / "研究方案_剩余覆盖重规划_20261009" / "算法小型验证_20261010"
        / ".deps")

#: names the sealed v0.1 modules expect from ``bootstrap``
OUT = NEW

ORDER = (V01, V02, V03, FROZEN, SRC)
for _entry in ORDER + (DEPS,):
    while str(_entry) in sys.path:
        sys.path.remove(str(_entry))
for _entry in ORDER:                     # later inserts end up earlier
    sys.path.insert(0, str(_entry))
sys.path.append(str(DEPS))


def resolution_report():
    import importlib
    out = {}
    for name in ("problem", "result", "common_geometry", "audit_independent",
                 "deadline", "finalize", "grading", "model", "oarp_replan",
                 "native", "methods", "entry", "adapters.registry"):
        try:
            module = importlib.import_module(name)
        except Exception as exc:                      # noqa: BLE001
            out[name] = f"<not importable: {exc}>"
            continue
        out[name] = str(Path(module.__file__).resolve())
    return out


def verify_isolation():
    report = resolution_report()
    external_ok = {str(DEPS)}
    outside = {name: path for name, path in report.items()
               if not path.startswith(str(NEW)) and path not in external_ok}
    if outside:
        raise RuntimeError(f"project modules resolved outside OUT: {outside}")
    return {"out": str(NEW), "order": [str(p) for p in ORDER],
            "deps": str(DEPS), "modules": report}
