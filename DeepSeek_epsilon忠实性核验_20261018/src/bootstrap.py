"""Import bootstrap for the epsilon-star fidelity revision.

The revision is self-contained: the only executable code it reuses is the sealed
v0.1 glue (``problem``, ``result``, ``common_geometry``, ``audit_independent``),
copied next to this file.  The old epsilon core is copied only as *evidence* and
is imported under an explicit alias by the probes, never by the new implementation.

``problem.py`` imports ``FROZEN`` and ``OUT`` from ``bootstrap``; the frozen v2
bundle is not used by this revision, so both names are provided here as plain
values with a comment, instead of dragging in the 190 MB dependency tree.
"""
import sys
from pathlib import Path

NEW = Path(__file__).resolve().parent.parent
SRC = NEW / "src"
V01 = NEW / "sources" / "v01"
V02_OLD = NEW / "sources" / "v02_epsilon_core"
LITERATURE = NEW / "sources" / "literature" / "epsilon_star_author_preprint.txt"
REPORTS = NEW / "reports"
LOGS = NEW / "logs"
ARTIFACTS = NEW / "artifacts"
TMP = NEW / "tmp"
MANIFESTS = NEW / "manifests"

#: names the sealed v0.1 modules expect from ``bootstrap``
OUT = NEW
FROZEN = None

for _entry in (SRC, V01):
    if str(_entry) in sys.path:
        sys.path.remove(str(_entry))
for _entry in (V01, SRC):
    sys.path.insert(0, str(_entry))


def resolution_report():
    import importlib
    out = {}
    for name in ("problem", "result", "common_geometry", "audit_independent",
                 "maps_faithful", "etm_faithful", "adapter"):
        try:
            module = importlib.import_module(name)
        except Exception as exc:                      # noqa: BLE001
            out[name] = f"<not importable: {exc}>"
            continue
        out[name] = str(Path(module.__file__).resolve())
    return out


def verify_isolation():
    report = resolution_report()
    outside = {name: path for name, path in report.items()
               if not path.startswith(str(NEW))}
    if outside:
        raise RuntimeError(f"modules resolved outside NEW: {outside}")
    return {"new_root": str(NEW), "modules": report}
