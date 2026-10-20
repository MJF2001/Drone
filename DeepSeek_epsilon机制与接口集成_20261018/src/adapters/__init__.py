"""Adapter package for this round.

``OUT/src/adapters`` holds the registry and the epsilon-star adapter; the sealed
finalize / grading / deadline / request / result / connector / auditor modules are
imported from ``OUT/sources`` through the bootstrap.  No older delivery is on the
import path at run time, so the v0.3 adapter (which still defaults to ``transit``
and ``turn_cost=0``) can never be loaded by accident.
"""
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent
if not (_SRC / "core" / "maps.py").is_file():
    raise ImportError(f"core modules missing under {_SRC}")
