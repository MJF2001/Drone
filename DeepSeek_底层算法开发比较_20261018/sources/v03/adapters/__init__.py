"""Adapter package for revision v0.3.

Only ``registry`` and ``epsilon_star`` are replaced in this revision; every other
adapter is reused read-only from ``revision_v0.2/src_v02/adapters`` by extending
this package's search path.

The v0.2 location is found by searching upwards for the actual file instead of
counting ``parents`` indices, so the package keeps working if the revision tree is
copied to a different depth.
"""
from pathlib import Path


def _find_v02_adapter_package(start):
    for parent in [start, *start.parents]:
        candidate = parent / "revision_v0.2" / "src_v02" / "adapters"
        if (candidate / "reference_methods.py").is_file():
            return candidate
        candidate = parent / "src_v02" / "adapters"
        if (candidate / "reference_methods.py").is_file():
            return candidate
    raise ImportError(f"v0.2 adapter package not found above {start}")


_HERE = Path(__file__).resolve().parent          # .../revision_v0.3/src_v03/adapters
_V02 = _find_v02_adapter_package(_HERE)

if str(_V02) not in __path__:
    __path__.append(str(_V02))
