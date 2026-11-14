"""Per-variable explanation of a ranked Earth cell.

For each weighted variable of the mission:
    earth, moon (twin), difference (earth - moon; null for categories),
    utility u, similarity s, weight w (JSON soft weight),
    suitability_weight  = w / sum(w over variables with a utility)
    similarity_weight   = w / sum(w over similarity variables with a sim)
    suitability_points  = 100 * suitability_weight * u        (sums to the suitability)
    similarity_points   = 100 * similarity_weight * s         (sums to the similarity)
    final_points        = alpha * similarity_points + (1 - alpha) * suitability_points
    lost_points         = alpha * 100 * similarity_weight * (1 - s)
                          + (1 - alpha) * 100 * suitability_weight * (1 - u)
'helps_most' = the ``helps_n`` variables with the largest final_points; 'hurts_most' =
the ``hurts_n`` with the largest lost_points (> 0). Ties keep the mission's variable
order. Both counts come from engine_config.json (explain_helps_n, explain_hurts_n).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if np.isfinite(v) else None


def explain_cell(variables: List[str], kinds: Dict[str, str], earth_values: Dict[str, Any],
                 moon_values: Dict[str, Any], utilities: Dict[str, float], sims: Dict[str, float],
                 weights: Dict[str, float], alpha: float, helps_n: int, hurts_n: int) -> Dict[str, Any]:
    """Explanation of one cell (see module docstring). Pure; values may be None."""
    u_den = sum(weights[v] for v in variables if _f(utilities.get(v)) is not None)
    s_den = sum(weights[v] for v in variables if v in sims and _f(sims.get(v)) is not None)
    rows: List[Dict[str, Any]] = []
    for v in variables:
        u = _f(utilities.get(v))
        s = _f(sims.get(v)) if v in sims else None
        w = float(weights[v])
        uw = w / u_den if (u is not None and u_den > 0) else None
        sw = w / s_den if (s is not None and s_den > 0) else None
        sp = 100.0 * uw * u if uw is not None else None
        mp = 100.0 * sw * s if sw is not None else None
        fp = alpha * (mp or 0.0) + (1 - alpha) * (sp or 0.0)
        lost = alpha * (100.0 * sw * (1 - s) if sw is not None else 0.0) + \
            (1 - alpha) * (100.0 * uw * (1 - u) if uw is not None else 0.0)
        ev, mv = earth_values.get(v), moon_values.get(v)
        if kinds.get(v) == "categorical":
            diff = None
        else:
            ef, mf = _f(ev), _f(mv)
            diff = ef - mf if (ef is not None and mf is not None) else None
        rows.append({
            "variable": v, "earth": ev, "moon": mv, "difference": diff,
            "utility": u, "similarity": s, "weight": w,
            "suitability_weight": uw, "similarity_weight": sw,
            "suitability_points": sp, "similarity_points": mp,
            "final_points": fp, "lost_points": lost,
        })
    order = {v: i for i, v in enumerate(variables)}
    helps = sorted(rows, key=lambda r: (-r["final_points"], order[r["variable"]]))[:helps_n]
    hurts = [r for r in sorted(rows, key=lambda r: (-r["lost_points"], order[r["variable"]])) if r["lost_points"] > 0][:hurts_n]
    return {"variables": rows, "helps_most": [r["variable"] for r in helps],
            "hurts_most": [r["variable"] for r in hurts]}
