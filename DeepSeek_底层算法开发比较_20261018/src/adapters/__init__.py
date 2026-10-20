"""Adapter package for this round.

``NEW/src/adapters`` holds the modules changed here; the untouched adapters are
reused read-only from the copied source trees:

1. ``NEW/src/adapters``    registry (this round), epsilon-star (this round)
2. ``sources/v03/adapters``  (only as a fallback; its registry/epsilon-star are shadowed)
3. ``sources/v02/adapters``  cstar, reference_methods
"""
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SOURCES = _HERE.parents[1] / "sources"
for _entry in (_SOURCES / "v03" / "adapters", _SOURCES / "v02" / "adapters"):
    if not _entry.is_dir():
        raise ImportError(f"adapter source tree missing: {_entry}")
    if str(_entry) not in __path__:
        __path__.append(str(_entry))
