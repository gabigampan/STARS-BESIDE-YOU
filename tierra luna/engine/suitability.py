"""Suitability 0-100 through the team module ``mission_scoring`` (unchanged).

Utilities run linearly between 'bad' (0) and 'good' (1), category tables map
classes to utilities, and when a weighted variable is missing its weight is
dropped and the remaining weights renormalised; the cell is flagged with the
number of missing weighted variables. Replacement weights can be passed at call
time and go straight to ``evaluate``.

Precision. ``mission_scoring.evaluate`` rounds its score to 2 decimals and its
utilities to 3. The engine does not build on those rounded numbers: it takes the
unrounded utilities from ``mission_scoring.utility`` (the same team function),
rounds them once to the published precision (engine_config export_decimals
'utility'), and computes the published suitability from exactly those published
utilities with the renormalised formula. The browser can therefore reproduce it,
and the final score is built from an unrounded suitability. The team module's own
rounded score is kept as ``score_team`` and checked against the published one.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import mission_scoring
from engine.config import EngineConfig, body_mission_config


@dataclass(frozen=True)
class SuitabilityResult:
    """Suitability of one mission on one body (arrays aligned with the input rows)."""

    passed: np.ndarray                 # bool, mission_scoring's pass flag
    score: np.ndarray                  # float, unrounded published suitability; NaN where eliminated
    coverage: np.ndarray               # share of soft weight with data
    utilities: Dict[str, np.ndarray]   # per weighted variable, published precision, NaN when missing
    missing_n: np.ndarray              # number of weighted variables without data
    score_team: np.ndarray             # mission_scoring.evaluate's score (rounded to 2 decimals by the team module)
    weights: Dict[str, float]          # weights used (JSON soft weights or the replacement)


def soft_variables(mission_cfg: Dict, mission: str) -> List[str]:
    """Weighted variables of a mission, in config order."""
    return list(mission_cfg["missions"][mission].get("soft", {}).keys())


def soft_weights(mission_cfg: Dict, mission: str,
                 replacement: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """Soft weights of a mission, optionally overridden (same rule as mission_scoring.apply_soft)."""
    w = {c: float(s["weight"]) for c, s in mission_cfg["missions"][mission].get("soft", {}).items()}
    if replacement:
        w.update({c: float(x) for c, x in replacement.items() if c in w})
    return w


def round_like_export(values: np.ndarray, decimals: int) -> np.ndarray:
    """Round each finite value with Python's ``round`` (exactly as the JSON export
    does); NaN stays NaN."""
    a = np.asarray(values, dtype=np.float64)
    return np.array([round(float(x), decimals) if np.isfinite(x) else np.nan for x in a], dtype=np.float64)


def evaluate_suitability(df: pd.DataFrame, body: str, mission: str, mission_cfg: Dict,
                         engine_cfg: EngineConfig,
                         weights: Optional[Dict[str, float]] = None) -> SuitabilityResult:
    """Run ``mission_scoring.evaluate`` for one mission on one body (pass flags,
    coverage, the team's rounded score) and compute the published suitability from
    unrounded team utilities (see module docstring).

    ``weights`` = {soft_variable: weight} replaces the JSON soft weights for this call.
    The body-specific config only changes which common gates apply (engine_config.json).
    """
    cfg = body_mission_config(mission_cfg, body, engine_cfg)
    res = mission_scoring.evaluate(df, [mission], cfg, {mission: weights} if weights else None)
    passed = res[f"pass_{mission}"].to_numpy().astype(bool)
    dec = int(engine_cfg.v("export_decimals").get("utility"))
    soft = cfg["missions"][mission].get("soft", {})
    utils = {c: round_like_export(mission_scoring.utility(df[c], spec), dec) for c, spec in soft.items()}
    w = soft_weights(cfg, mission, weights)
    missing = np.zeros(len(df), dtype=int)
    for u in utils.values():
        missing += (~np.isfinite(u)).astype(int)
    score = recompute_from_utilities(utils, w) if utils else np.full(len(df), np.nan)
    score = np.where(passed, score, np.nan)
    team = res[f"score_{mission}"].to_numpy(dtype=np.float64)
    both = np.isfinite(team) & np.isfinite(score)
    if not np.array_equal(np.isfinite(team), np.isfinite(score)) or \
            (both.any() and float(np.max(np.abs(team[both] - score[both]))) > 0.005 + 10.0 ** -dec * 100):
        raise AssertionError("published suitability disagrees with mission_scoring.evaluate's score")
    return SuitabilityResult(
        passed=passed,
        score=score,
        coverage=res[f"coverage_{mission}"].to_numpy(dtype=np.float64),
        utilities=utils,
        missing_n=missing,
        score_team=team,
        weights=w,
    )


def recompute_from_utilities(utilities: Dict[str, np.ndarray], weights: Dict[str, float]) -> np.ndarray:
    """Browser formula: 100 * sum(w*u) / sum(w over variables with a utility).

    Sums run in the order of ``utilities`` (the mission's variable order), so the
    browser, doing the same double arithmetic in the same order, gets the same value.
    This is the published suitability (from published utilities).
    """
    n = len(next(iter(utilities.values())))
    num = np.zeros(n)
    den = np.zeros(n)
    for c, u in utilities.items():
        ok = np.isfinite(u)
        num += np.where(ok, weights[c] * np.where(ok, u, 0.0), 0.0)
        den += np.where(ok, weights[c], 0.0)
    return np.where(den > 0, 100.0 * num / np.where(den > 0, den, 1.0), np.nan)
