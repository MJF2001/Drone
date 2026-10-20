"""Adapters for this round: only the two new references are registered."""
"""Adapters for this round: only the two new references are registered.

The historical OARP_CORE2 adapter is never imported here; its ledger points at the
old delivery and its `old_services` recovery is exactly what this round replaces.
"""
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if not (_HERE.parent / "native.py").is_file():
    raise ImportError("native modules missing under OUT/src")
