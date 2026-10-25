"""Adapted C* core: historical C* mechanically ported to the current model.

Modules
-------
``public_map``  published-map occupancy + the historical ideal-grid ray sensor
``rcg``         RCG expansion, Def. III.8/9 pruning, Alg. 2, RCG A*
``planner``     Algorithms 1--4, retreat nodes, coverage holes, Alg. 3 TSP

Adaptation label ``cstar_adapt_v0.1_20261018``.  The mechanism-to-source table
and the list of losses are in ``specs/cstar_adaptation.md``.
"""
from .public_map import (PublicMap, PublishedWorld, published_observation,
                         dist, lap_points, point_segment_distance, supercover)
from .planner import CStar, WallClockCap, optimize_tsp
from .rcg import RCG, RCGCut

ADAPTATION_LABEL = "cstar_adapt_v0.1_20261018"

__all__ = [
    "PublicMap", "PublishedWorld", "published_observation",
    "dist", "lap_points", "point_segment_distance", "supercover",
    "RCG", "RCGCut",
    "CStar", "WallClockCap", "optimize_tsp",
    "ADAPTATION_LABEL",
]
