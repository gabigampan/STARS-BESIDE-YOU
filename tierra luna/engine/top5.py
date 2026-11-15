"""The five analogs shown per mission (engine_config ``top5_selection``).

Decision of 2026-11-15 11:23 CET (decision 2, taken by the delegate on the team lead's
behalf; the director's reading: a rule for choosing the FIVE, the full ranking stays by
final score). Two rules, chosen per mission in the configuration (no mission is named
here):

* ``by_rank``: ranks 1 to n of the full ranking.
* ``min_separation``: greedy down the full ranking: keep the best, skip any ranked point
  whose cell centre lies within ``min_separation_deg`` degrees of arc (great circle on the
  sphere of engine_config ``body_radius_km``) of a point already kept, until n are kept.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np

RULES = ("by_rank", "min_separation", "rank_with_skips", "spread_within_top_tie")
#
# Rules added at 2026-11-15 11:28/11:36 CET (docs/DECISIONS.md, 'Decisiones de las 11:28 y 11:36'):
#
# * ``rank_with_skips``: down the full ranking, skip a point whose cell fails a named,
#   separately switchable skip (``skips``: e.g. ``ice`` = snow_ice_frac >= 0.5, ``water`` =
#   mask_fraction < 0.5), and skip one within ``min_separation_deg`` of arc of a kept point.
# * ``spread_within_top_tie``: when more than ``count`` ranked points share the highest
#   published final score, choose among THOSE (skips applied) by farthest-point selection:
#   start from the tied point with the highest similarity at full precision (ties lowest
#   id), then repeatedly add the tied point whose smallest great-circle distance to the
#   chosen ones is largest (ties lowest id). With ``count`` or fewer tied, ``rank_with_skips``.



def central_angle_deg(lat1: float, lon1: float, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """Great-circle central angle in degrees (haversine, numerically stable at small angles)."""
    p1, p2 = math.radians(lat1), np.radians(lat2)
    dphi = p2 - p1
    dl = np.radians(lon2) - math.radians(lon1)
    a = np.sin(dphi / 2.0) ** 2 + math.cos(p1) * np.cos(p2) * np.sin(dl / 2.0) ** 2
    return np.degrees(2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0))))


def arc_km(deg: float, radius_km: float) -> float:
    """Length of an arc of ``deg`` degrees on a sphere of ``radius_km``."""
    return math.radians(deg) * radius_km


def skip_mask(rule: Dict[str, Any], columns: Optional[Dict[str, np.ndarray]], n_rows: int) -> np.ndarray:
    """True for rows that an enabled skip of ``rule['skips']`` removes from the five.

    Each skip: {"enabled": bool, "column": name, "op": ">=" | "<", "value": x}; a missing
    value never skips (only a stated share does)."""
    out = np.zeros(n_rows, dtype=bool)
    for name, sk in (rule.get("skips") or {}).items():
        if not sk.get("enabled"):
            continue
        if columns is None or sk["column"] not in columns:
            raise KeyError(f"top-5 skip {name!r} needs column {sk['column']!r}")
        v = np.asarray(columns[sk["column"]], dtype=np.float64)
        fin = np.isfinite(v)
        x = float(sk["value"])
        if sk["op"] == ">=":
            out |= fin & (np.where(fin, v, -np.inf) >= x)
        elif sk["op"] == "<":
            out |= fin & (np.where(fin, v, np.inf) < x)
        else:
            raise ValueError(f"unknown skip op {sk['op']!r}")
    return out


def top_tie(rank: np.ndarray, final_published: np.ndarray) -> np.ndarray:
    """Rows of ranked points whose published final equals the best one."""
    if not (rank > 0).any():
        return np.zeros(0, dtype=int)
    best = float(np.max(final_published[rank > 0]))
    return np.flatnonzero((rank > 0) & (final_published == best))


def farthest_point(cand: np.ndarray, lat: np.ndarray, lon: np.ndarray, start: int, n: int,
                   ids: np.ndarray) -> List[int]:
    """Greedy farthest-point selection among ``cand`` rows from ``start`` (ties lowest id)."""
    chosen = [int(start)]
    mind = central_angle_deg(float(lat[start]), float(lon[start]), lat[cand], lon[cand])
    order = np.argsort(ids[cand], kind="mergesort")
    while len(chosen) < min(n, len(cand)):
        md = np.where(np.isin(cand, chosen), -np.inf, mind)
        # largest smallest distance, ties to the lowest id
        best = max(order, key=lambda k: (md[k], -int(ids[cand[k]])))
        nxt = int(cand[best])
        chosen.append(nxt)
        mind = np.minimum(mind, central_angle_deg(float(lat[nxt]), float(lon[nxt]), lat[cand], lon[cand]))
    return chosen


def select(rank: np.ndarray, lat: np.ndarray, lon: np.ndarray, rule: Dict[str, Any],
           columns: Optional[Dict[str, np.ndarray]] = None, final_published: Optional[np.ndarray] = None,
           similarity: Optional[np.ndarray] = None, ids: Optional[np.ndarray] = None) -> List[int]:
    """Row positions of the five (``rule['count']``) analogs, in the order shown.

    ``rank`` is the full ranking (1 = best, 0 = not ranked), ``lat``/``lon`` the cell
    centres of the same rows; ``columns`` the Earth columns the skips read;
    ``final_published``, ``similarity`` and ``ids`` are needed by spread_within_top_tie."""
    n = int(rule["count"])
    kind = rule["rule"]
    if kind not in RULES:
        raise ValueError(f"unknown top-5 rule {kind!r}")
    ranked = np.flatnonzero(rank > 0)
    ranked = ranked[np.argsort(rank[ranked], kind="mergesort")]
    if kind in ("rank_with_skips", "spread_within_top_tie"):
        skip = skip_mask(rule, columns, len(rank))
        if kind == "spread_within_top_tie":
            tied = top_tie(rank, final_published)
            tied = tied[~skip[tied]]
            if len(tied) > n:
                sim = np.asarray(similarity, dtype=np.float64)
                o = np.lexsort((ids[tied], -sim[tied]))
                return farthest_point(tied, lat, lon, int(tied[o[0]]), n, np.asarray(ids))
        ranked = ranked[~skip[ranked]]
        kind = "min_separation"
    if kind == "by_rank":
        return [int(i) for i in ranked[:n]]
    sep = float(rule["min_separation_deg"])
    kept: List[int] = []
    for i in ranked:
        if kept:
            d = central_angle_deg(float(lat[i]), float(lon[i]), lat[kept], lon[kept])
            if np.any(d < sep):
                continue
        kept.append(int(i))
        if len(kept) == n:
            break
    return kept


def top5_block(rule: Dict[str, Any], rows: List[int], ids: np.ndarray, rank: np.ndarray,
               radius_km: float, km_decimals: int) -> Dict[str, Any]:
    """missions.json 'top5' of one mission (the shape the web was given)."""
    sep = rule.get("min_separation_deg") if rule["rule"] != "by_rank" else None
    km = round(arc_km(float(sep), radius_km), km_decimals) if sep is not None else None
    text = rule["sentence"].replace("{deg}", f"{float(sep):g}" if sep is not None else "").replace(
        "{km}", f"{km:.{km_decimals}f}" if km is not None else "")
    return {"rule": text, "min_separation_deg": float(sep) if sep is not None else None,
            "min_separation_km": km, "ids": [int(ids[i]) for i in rows],
            "overall_ranks": [int(rank[i]) for i in rows]}
