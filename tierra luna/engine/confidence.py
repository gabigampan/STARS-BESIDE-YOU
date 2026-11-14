"""Confidence label (high / medium / low) of a ranked Earth cell and its twin.

Rule (all numbers in engine_config.json "confidence"):
    body score  = sum(w_v * level_score[level(v, body)]) / sum(w_v)  over the mission's
                  weighted variables with data on that cell
    pair score  = min(Earth score, Moon score) * coverage
    coverage    = share of the mission's soft weight with data on both cells
    label       = high   if pair score >= high_min and the coarser cell <= high_max_cell_km
                  medium if pair score >= medium_min (or high blocked by resolution)
                  low    otherwise
    no data    : when no weighted variable has data on the cell, there is no confidence:
                 label and score are None (exported as null), never 0.

Levels are per variable and body, not per cell, so with no missing data the score is
the same for every ranked cell of a mission (missions.json says so per mission).
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Tuple


def body_score(levels: Dict[str, str], weights: Dict[str, float], available: Iterable[str],
               level_scores: Dict[str, float]) -> Optional[float]:
    """Weight-averaged level score over the available weighted variables (None if none)."""
    avail = [v for v in available if v in weights]
    den = sum(weights[v] for v in avail)
    if den <= 0:
        return None
    return sum(weights[v] * level_scores[levels[v]] for v in avail) / den


def pair_confidence(earth_levels: Dict[str, str], moon_levels: Dict[str, str], weights: Dict[str, float],
                    available: Iterable[str], cell_km: float,
                    rule: Dict) -> Tuple[Optional[str], Optional[float]]:
    """Return (label, score) for an Earth cell and its twin; (None, None) without data."""
    avail = [v for v in available if v in weights]
    total = sum(weights.values())
    ls = rule["level_scores"]
    e_s = body_score(earth_levels, weights, avail, ls)
    m_s = body_score(moon_levels, weights, avail, ls)
    if e_s is None or m_s is None or total <= 0:
        return None, None
    coverage = sum(weights[v] for v in avail) / total
    score = min(e_s, m_s) * coverage
    if score >= rule["high_min"] and cell_km <= rule["high_max_cell_km"]:
        return "high", score
    if score >= rule["medium_min"]:
        return "medium", score
    return "low", score
