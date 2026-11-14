"""Lunar twin pairing.

Each Earth cell that passes a mission is paired with its lunar twin: the lunar
cell passing the same mission's hard filters with the highest weighted similarity
(see similarity.py). Ties go to the lowest lunar cell id. Vectorised with numpy
in blocks of Earth rows against all candidate lunar cells.
"""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np

from engine.similarity import categorical_similarity, numeric_similarity


def _has_missing(values: np.ndarray, kind: str) -> bool:
    return bool(np.any(values < 0)) if kind == "categorical" else bool(np.any(~np.isfinite(values)))


def _block_similarity_complete(earth: Dict[str, np.ndarray], moon: Dict[str, np.ndarray], kinds: Dict[str, str],
                               scales: Dict[str, Optional[float]], weights: Dict[str, float],
                               start: int, stop: int, n_m: int) -> np.ndarray:
    """Weighted similarity (0-1) of a block when no value is missing.

    Same arithmetic as numeric_similarity/categorical_similarity, done in place to
    save memory passes: per variable w * max(0, 1 - |e - m| / scale).
    """
    acc = np.zeros((stop - start, n_m))
    tmp = np.empty_like(acc)
    for v, w in weights.items():
        e = earth[v][start:stop, None]
        m = moon[v][None, :]
        if kinds[v] == "categorical":
            acc += w * (e == m)
            continue
        scale = float(scales[v])
        np.subtract(e, m, out=tmp)
        np.abs(tmp, out=tmp)
        if scale > 0:
            np.divide(tmp, scale, out=tmp)
            np.subtract(1.0, tmp, out=tmp)
            np.maximum(tmp, 0.0, out=tmp)
        else:
            tmp[:] = (tmp == 0)
        tmp *= w
        acc += tmp
    acc /= sum(weights.values())
    return acc


def _block_similarity_general(earth: Dict[str, np.ndarray], moon: Dict[str, np.ndarray], kinds: Dict[str, str],
                              scales: Dict[str, Optional[float]], weights: Dict[str, float],
                              start: int, stop: int) -> np.ndarray:
    """Weighted similarity (0-1) of a block with missing values renormalised; -inf when none comparable."""
    num = None
    den = None
    for v, w in weights.items():
        e = earth[v][start:stop, None]
        m = moon[v][None, :]
        s = categorical_similarity(e, m) if kinds[v] == "categorical" else numeric_similarity(e, m, float(scales[v]))
        ok = np.isfinite(s)
        part_n = np.where(ok, w * np.where(ok, s, 0.0), 0.0)
        part_d = np.where(ok, w, 0.0)
        num = part_n if num is None else num + part_n
        den = part_d if den is None else den + part_d
    return np.where(den > 0, num / np.where(den > 0, den, 1.0), -np.inf)


def pair_twins(earth: Dict[str, np.ndarray], moon: Dict[str, np.ndarray], kinds: Dict[str, str],
               scales: Dict[str, Optional[float]], weights: Dict[str, float], moon_ids: np.ndarray,
               chunk_rows: int = 512) -> Tuple[np.ndarray, np.ndarray]:
    """Return (twin_id, best_similarity_pct) for every Earth row.

    ``earth[v]`` / ``moon[v]``: values of variable v for the candidate Earth and lunar
    cells (numeric floats with NaN for missing, or categorical integer codes with -1).
    ``weights``: the mission's soft weights for the similarity variables.
    ``moon_ids`` must be strictly increasing so that argmax (first maximum) returns the
    lowest id on ties. Earth rows with no comparable variable get twin -1 and NaN.
    """
    moon_ids = np.asarray(moon_ids)
    if moon_ids.size and np.any(np.diff(moon_ids) <= 0):
        raise ValueError("moon_ids must be strictly increasing")
    weights = {v: float(w) for v, w in weights.items() if v in earth and v in moon}
    n_e = len(next(iter(earth.values()))) if earth else 0
    twin = np.full(n_e, -1, dtype=np.int64)
    best = np.full(n_e, np.nan)
    if n_e == 0 or moon_ids.size == 0 or not weights:
        return twin, best
    complete = not any(_has_missing(earth[v], kinds[v]) or _has_missing(moon[v], kinds[v]) for v in weights)
    for start in range(0, n_e, chunk_rows):
        stop = min(start + chunk_rows, n_e)
        if complete:
            sim = _block_similarity_complete(earth, moon, kinds, scales, weights, start, stop, moon_ids.size)
        else:
            sim = _block_similarity_general(earth, moon, kinds, scales, weights, start, stop)
        idx = np.argmax(sim, axis=1)                      # first maximum = lowest id
        val = sim[np.arange(stop - start), idx]
        has = np.isfinite(val)
        twin[start:stop] = np.where(has, moon_ids[idx], -1)
        best[start:stop] = np.where(has, 100.0 * val, np.nan)
    return twin, best
