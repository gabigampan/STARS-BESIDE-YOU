"""Earth-Moon similarity per variable, in physical units on a common scale.

    numeric:      sim = max(0, 1 - |earth - moon| / scale)
    categorical:  sim = 1 if earth == moon else 0
    missing:      sim is null (the variable drops out and weights renormalise)

The scale of each numeric variable is the pooled robust range (5th to 95th
percentile, configurable) of the variable over the cells of BOTH bodies that pass
the mission's hard filters. It is computed at build time and written to the bundle.
Per-body z-scores and percentile ranks are never used.

Variables: the mission's weighted (soft) variables that have data on both bodies and
that the provenance registry marks as the same physical quantity on both bodies
(engine_config similarity_comparability). Excluded variables still count in suitability.

Weighted similarity (0-100):
    similarity_pct = 100 * sum(w_v * sim_v) / sum(w_v over variables with a sim)
where w_v are the mission's soft weights applied directly to the variables.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def similarity_variables(soft_vars: List[str], earth: pd.DataFrame, moon: pd.DataFrame,
                         reg: Optional[Dict] = None,
                         exclude_non_comparable: bool = False) -> Tuple[List[str], Dict[str, str]]:
    """Weighted variables of a mission used in the Earth-Moon similarity.

    A variable is used when its column exists and is not all missing on both bodies
    and, if ``exclude_non_comparable`` is set, when the provenance registry marks it as
    the same physical quantity on both bodies. Returns (used variables in config order,
    {excluded variable: reason}).
    """
    used: List[str] = []
    excluded: Dict[str, str] = {}
    for v in soft_vars:
        if not (v in earth.columns and v in moon.columns and earth[v].notna().any() and moon[v].notna().any()):
            excluded[v] = "no data on at least one body"
        elif exclude_non_comparable and reg is not None and not reg["variables"][v]["comparable_across_bodies"]:
            excluded[v] = "not the same quantity on both bodies: " + reg["variables"][v]["comparability_note"]
        else:
            used.append(v)
    return used, excluded


def pooled_scale(earth_values: np.ndarray, moon_values: np.ndarray,
                 lower_pct: float, upper_pct: float) -> Dict[str, Optional[float]]:
    """Pooled robust range of a numeric variable over the given cells of both bodies.

    Returns {"scale", "p_low", "p_high", "n"}; scale is None when no value exists.
    """
    vals = np.concatenate([np.asarray(earth_values, dtype=np.float64),
                           np.asarray(moon_values, dtype=np.float64)])
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return {"scale": None, "p_low": None, "p_high": None, "n": 0}
    lo = float(np.percentile(vals, lower_pct))
    hi = float(np.percentile(vals, upper_pct))
    return {"scale": hi - lo, "p_low": lo, "p_high": hi, "n": int(vals.size)}


def numeric_similarity(earth: np.ndarray, moon: np.ndarray, scale: float) -> np.ndarray:
    """max(0, 1 - |earth - moon| / scale), NaN where either value is missing.

    With scale == 0 the rule is exact match (1 if equal, else 0), per engine_config.
    Arrays broadcast, so (n,1) x (1,m) gives an (n, m) matrix.
    """
    e = np.asarray(earth, dtype=np.float64)
    m = np.asarray(moon, dtype=np.float64)
    diff = np.abs(e - m)
    if scale > 0:
        sim = np.maximum(0.0, 1.0 - diff / scale)
    else:
        sim = (diff == 0).astype(np.float64)
    return np.where(np.isfinite(diff), sim, np.nan)


def categorical_similarity(earth: np.ndarray, moon: np.ndarray) -> np.ndarray:
    """1 when the category labels are equal, 0 otherwise, NaN when either is missing.

    Inputs are integer codes with -1 for missing (see :func:`encode_categories`).
    """
    e = np.asarray(earth)
    m = np.asarray(moon)
    sim = (e == m).astype(np.float64)
    return np.where((e < 0) | (m < 0), np.nan, sim)


def encode_categories(earth: pd.Series, moon: pd.Series):
    """Shared integer codes for a categorical variable on both bodies (-1 = missing)."""
    def clean(s: pd.Series) -> pd.Series:
        t = s.astype(str).str.strip().str.lower()
        return t.where(~(s.isna() | t.isin(["", "nan"])), None)
    e, m = clean(earth), clean(moon)
    cats = sorted(set(e.dropna()) | set(m.dropna()))
    lut = {c: i for i, c in enumerate(cats)}
    enc = lambda s: np.array([lut[x] if x is not None else -1 for x in s], dtype=np.int64)  # noqa: E731
    return enc(e), enc(m), cats


def weighted_similarity(sims: Dict[str, np.ndarray], weights: Dict[str, float]) -> np.ndarray:
    """100 * sum(w*sim) / sum(w over variables with a sim); NaN when no variable has one."""
    n = len(next(iter(sims.values())))
    num = np.zeros(n)
    den = np.zeros(n)
    for v, s in sims.items():
        ok = np.isfinite(s)
        num += np.where(ok, weights[v] * np.where(ok, s, 0.0), 0.0)
        den += np.where(ok, weights[v], 0.0)
    return np.where(den > 0, 100.0 * num / np.where(den > 0, den, 1.0), np.nan)
