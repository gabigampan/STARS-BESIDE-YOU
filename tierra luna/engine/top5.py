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
from typing import Any, Dict, List

import numpy as np

RULES = ("by_rank", "min_separation")


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


def select(rank: np.ndarray, lat: np.ndarray, lon: np.ndarray, rule: Dict[str, Any]) -> List[int]:
    """Row positions of the five (``rule['count']``) analogs, in the order shown.

    ``rank`` is the full ranking (1 = best, 0 = not ranked), ``lat``/``lon`` the cell
    centres of the same rows."""
    n = int(rule["count"])
    kind = rule["rule"]
    if kind not in RULES:
        raise ValueError(f"unknown top-5 rule {kind!r}")
    ranked = np.flatnonzero(rank > 0)
    ranked = ranked[np.argsort(rank[ranked], kind="mergesort")]
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
    sep = rule.get("min_separation_deg") if rule["rule"] == "min_separation" else None
    km = round(arc_km(float(sep), radius_km), km_decimals) if sep is not None else None
    text = rule["sentence"].replace("{deg}", f"{float(sep):g}" if sep is not None else "").replace(
        "{km}", f"{km:.{km_decimals}f}" if km is not None else "")
    return {"rule": text, "min_separation_deg": float(sep) if sep is not None else None,
            "min_separation_km": km, "ids": [int(ids[i]) for i in rows],
            "overall_ranks": [int(rank[i]) for i in rows]}
