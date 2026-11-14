"""Hard filters, one function for both bodies.

Common gates (those applicable to the body, per engine_config.json) and then the
mission's gates are applied through ``mission_scoring.apply_gates``; the pass flag
is exactly the team module's. On top of it this module records every failed
criterion as an English reason code:

    <variable>:missing      value absent (null) in a gated or required variable
    <variable>:below_min    value < min
    <variable>:above_max    value > max
    <variable>:not_allowed  category not in the gate's allow list
    <variable>:excluded     category in the gate's exclude list

A cell failing any criterion is ELIMINATED for that mission.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

import mission_scoring
from engine.config import EngineConfig, body_mission_config

MISSING_TOKENS = ("", "nan", "none")


@dataclass(frozen=True)
class GateResult:
    """Outcome of the hard filters of one mission on one body."""

    passed: np.ndarray            # bool, one per cell
    reasons: List[Tuple[str, ...]]  # failed criteria per cell (empty tuple when passed)


def effective_gates(mission_cfg: Dict, mission: str, body: str, engine_cfg: EngineConfig) -> Dict[str, Dict]:
    """Gates applied to ``body`` for ``mission``: applicable common gates, then mission gates
    (a mission gate on the same variable replaces the common one, as in mission_scoring)."""
    cfg = body_mission_config(mission_cfg, body, engine_cfg)
    m = cfg["missions"][mission]
    gates = {**cfg.get("common_gates", {}), **m.get("gates", {})}
    return {c: {k: v for k, v in g.items() if k != "why"} for c, g in gates.items()}


def gate_origin(mission_cfg: Dict, mission: str, variable: str) -> str:
    """'mission' when the mission defines the gate, else 'common'."""
    return "mission" if variable in mission_cfg["missions"][mission].get("gates", {}) else "common"


def _missing_mask(s: pd.Series, tokens: Tuple[str, ...] = MISSING_TOKENS) -> np.ndarray:
    """Missing-value mask with the same tokens as mission_scoring (require_present
    treats '', 'nan' and 'none' as absent; a categorical gate treats '' and 'nan')."""
    txt = s.astype(str).str.strip().str.lower()
    return (s.isna() | txt.isin(tokens)).to_numpy()


def _reasons_for_gate(s: pd.Series, gate: Dict, var: str) -> List[Optional[str]]:
    """Reason code per cell for one gate (None when the cell passes it)."""
    miss = _missing_mask(s, ("", "nan"))
    out: List[Optional[str]] = [None] * len(s)
    if "min" in gate or "max" in gate:
        v = pd.to_numeric(s, errors="coerce").to_numpy(dtype=np.float64)
        lo, hi = gate.get("min"), gate.get("max")
        for i in range(len(s)):
            if miss[i] or not np.isfinite(v[i]):
                out[i] = f"{var}:missing"
            elif lo is not None and v[i] < lo:
                out[i] = f"{var}:below_min"
            elif hi is not None and v[i] > hi:
                out[i] = f"{var}:above_max"
    else:
        txt = s.astype(str).str.strip().str.lower().to_numpy()
        allow = [a.lower() for a in gate.get("allow", []) or []]
        excl = [e.lower() for e in gate.get("exclude", []) or []]
        for i in range(len(s)):
            if miss[i]:
                out[i] = f"{var}:missing"
            elif allow and txt[i] not in allow:
                out[i] = f"{var}:not_allowed"
            elif excl and txt[i] in excl:
                out[i] = f"{var}:excluded"
    return out


def evaluate_gates(df: pd.DataFrame, body: str, mission: str, mission_cfg: Dict,
                   engine_cfg: EngineConfig) -> GateResult:
    """Apply the hard filters of ``mission`` to the cells of ``body``.

    The pass flag comes from ``mission_scoring.apply_gates`` with the config's
    ``on_missing_gate``; the engine checks that its own reason codes agree with it
    and raises if they do not.
    """
    cfg = body_mission_config(mission_cfg, body, engine_cfg)
    gates = effective_gates(mission_cfg, mission, body, engine_cfg)
    require = list(cfg["missions"][mission].get("require_present", []))
    on_missing = cfg.get("on_missing_gate", "drop")
    passed, _, _ = mission_scoring.apply_gates(df, gates, require, on_missing)

    per_cell: List[List[str]] = [[] for _ in range(len(df))]
    for col in require:
        for i in np.flatnonzero(_missing_mask(df[col])):
            per_cell[i].append(f"{col}:missing")
    for col, g in gates.items():
        codes = _reasons_for_gate(df[col], g, col)
        for i, code in enumerate(codes):
            if code is None:
                continue
            if code.endswith(":missing") and on_missing == "keep":
                continue  # the team module keeps the cell in that mode
            per_cell[i].append(code)
    reasons = [tuple(dict.fromkeys(r)) for r in per_cell]
    mine = np.array([len(r) == 0 for r in reasons], dtype=bool)
    if not np.array_equal(mine, np.asarray(passed, dtype=bool)):
        bad = int(np.flatnonzero(mine != np.asarray(passed, dtype=bool))[0])
        raise AssertionError(f"gate reasons disagree with mission_scoring.apply_gates at row {bad}")
    return GateResult(passed=np.asarray(passed, dtype=bool), reasons=reasons)


def reason_counts(result: GateResult) -> Dict[str, int]:
    """Number of cells failing each reason code (a cell can count under several)."""
    counts: Dict[str, int] = {}
    for r in result.reasons:
        for code in r:
            counts[code] = counts.get(code, 0) + 1
    return counts


def top_reasons(result: GateResult, n: int) -> List[Dict]:
    """The ``n`` commonest reason codes, ties broken by code name."""
    items = sorted(reason_counts(result).items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"reason": k, "cells": v} for k, v in items[:n]]
