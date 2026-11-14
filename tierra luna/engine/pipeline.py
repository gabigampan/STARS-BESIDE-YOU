"""Engine pipeline: gates -> suitability -> similarity scales -> twins -> final score
-> rank -> confidence, for every mission. Pure: inputs in, results out, no I/O.

Precision (engine_config export_decimals): utilities and per-variable similarities
are rounded once to their published precision; suitability, similarity and the final
score are computed, unrounded, from those published values, so the browser can
reproduce them. The final score is rounded to its published precision only for the
rank, which therefore follows the contract rule on the stored values: final
descending, ties by Earth cell id ascending.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

import mission_scoring
from engine import provenance
from engine.config import EngineConfig, mission_ids
from engine.confidence import pair_confidence
from engine.gates import GateResult, evaluate_gates
from engine.pairing import pair_twins
from engine.similarity import (categorical_similarity, encode_categories, numeric_similarity,
                               pooled_scale, similarity_variables, weighted_similarity)
from engine.suitability import (SuitabilityResult, evaluate_suitability, round_like_export, soft_variables,
                                soft_weights)


@dataclass
class MissionResult:
    """Everything the engine computes for one mission (arrays over all cells of a body)."""

    mission: str
    earth_gates: GateResult
    moon_gates: GateResult
    earth_suit: SuitabilityResult
    soft_vars: List[str]
    sim_vars: List[str]
    sim_excluded: Dict[str, str]        # weighted variables left out of the similarity, with the reason
    kinds: Dict[str, str]
    scales: Dict[str, Dict]
    twin_id: np.ndarray                 # Earth cells: lunar twin id, -1 if none
    sims: Dict[str, np.ndarray]         # Earth cells: per-variable similarity to the twin
    similarity_pct: np.ndarray          # Earth cells: weighted similarity 0-100
    final: np.ndarray                   # Earth cells: combine_with_similarity (unrounded)
    final_published: np.ndarray         # Earth cells: final rounded to the published precision
    rank: np.ndarray                    # Earth cells: 1..n on final_published, 0 when not ranked
    confidence: List[Optional[str]]
    confidence_score: np.ndarray
    moon_twin_count: np.ndarray         # Moon cells: Earth cells that chose it as twin
    alpha: float
    extra: Dict = field(default_factory=dict)


def rank_scores(final: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """Rank 1..n by final score descending, ties by cell id ascending; 0 when NaN."""
    final = np.asarray(final, dtype=np.float64)
    ok = np.isfinite(final)
    order = np.lexsort((np.asarray(ids), -np.where(ok, final, -np.inf)))
    order = [i for i in order if ok[i]]
    rank = np.zeros(len(final), dtype=np.int64)
    rank[order] = np.arange(1, len(order) + 1)
    return rank


def run_mission(mission: str, earth: pd.DataFrame, moon: pd.DataFrame, mission_cfg: Dict,
                engine_cfg: EngineConfig, reg: Dict) -> MissionResult:
    """Compute one mission for both bodies (see module docstring)."""
    eg = evaluate_gates(earth, "EARTH", mission, mission_cfg, engine_cfg)
    mg = evaluate_gates(moon, "MOON", mission, mission_cfg, engine_cfg)
    es = evaluate_suitability(earth, "EARTH", mission, mission_cfg, engine_cfg)
    if not np.array_equal(es.passed, eg.passed):
        raise AssertionError("evaluate() and the gate module disagree on Earth pass flags")

    svars = soft_variables(mission_cfg, mission)
    weights_all = soft_weights(mission_cfg, mission)
    comp = engine_cfg.v("similarity_comparability")
    sim_vars, sim_excluded = similarity_variables(svars, earth, moon, reg, bool(comp["exclude_non_comparable"]))
    kinds = {v: provenance.kind(reg, v) for v in sim_vars}
    sim_w = {v: weights_all[v] for v in sim_vars}

    scale_cfg = engine_cfg.v("similarity_scale")
    e_idx = np.flatnonzero(eg.passed)
    m_idx = np.flatnonzero(mg.passed)
    scales: Dict[str, Dict] = {}
    e_vals: Dict[str, np.ndarray] = {}
    m_vals: Dict[str, np.ndarray] = {}
    for v in sim_vars:
        if kinds[v] == "categorical":
            ec, mc, cats = encode_categories(earth[v], moon[v])
            e_vals[v], m_vals[v] = ec, mc
            scales[v] = {"kind": "categorical", "rule": "1 if equal else 0", "categories": cats}
        else:
            e_vals[v] = pd.to_numeric(earth[v], errors="coerce").to_numpy(dtype=np.float64)
            m_vals[v] = pd.to_numeric(moon[v], errors="coerce").to_numpy(dtype=np.float64)
            sc = pooled_scale(e_vals[v][e_idx], m_vals[v][m_idx],
                              scale_cfg["lower_percentile"], scale_cfg["upper_percentile"])
            scales[v] = {"kind": "numeric", **sc}

    numeric_ok = all(kinds[v] == "categorical" or scales[v]["scale"] is not None for v in sim_vars)
    moon_ids = moon["id"].to_numpy()
    twin_full = np.full(len(earth), -1, dtype=np.int64)
    if e_idx.size and m_idx.size and numeric_ok:
        tw, _ = pair_twins({v: e_vals[v][e_idx] for v in sim_vars},
                           {v: m_vals[v][m_idx] for v in sim_vars},
                           kinds, {v: scales[v].get("scale") for v in sim_vars}, sim_w,
                           moon_ids[m_idx], int(engine_cfg.v("pairing_chunk_rows")))
        twin_full[e_idx] = tw

    # Per-variable similarity of each Earth cell to its twin (twin id -> lunar row position).
    has_twin = twin_full >= 0
    tpos = np.where(has_twin, np.searchsorted(moon_ids, np.maximum(twin_full, 0)), 0)
    if len(moon_ids) == 0:
        sim_vars = []  # nothing to compare with
    sdec = int(engine_cfg.v("export_decimals")["similarity"])
    sims: Dict[str, np.ndarray] = {}
    for v in sim_vars:
        if kinds[v] == "categorical":
            s = categorical_similarity(e_vals[v], m_vals[v][tpos])
        else:
            s = numeric_similarity(e_vals[v], m_vals[v][tpos], float(scales[v]["scale"]))
        sims[v] = round_like_export(np.where(has_twin, s, np.nan), sdec)  # published precision
    sim_pct = weighted_similarity(sims, sim_w) if sim_vars else np.full(len(earth), np.nan)
    sim_pct = np.where(has_twin, sim_pct, np.nan)

    alpha = float(engine_cfg.v("mix_factor"))
    frame = pd.DataFrame({"similarity_pct": sim_pct, f"score_{mission}": es.score})
    final = mission_scoring.combine_with_similarity(frame, mission, alpha=alpha).to_numpy(dtype=np.float64)
    final = np.where(eg.passed, final, np.nan)  # a gate-failed cell never gets a final score
    final_pub = round_like_export(final, int(engine_cfg.v("export_decimals")["score"]))
    rank = rank_scores(final_pub, earth["id"].to_numpy())

    rule = engine_cfg.v("confidence")
    e_levels = {v: provenance.level(reg, v, "EARTH") for v in svars}
    m_levels = {v: provenance.level(reg, v, "MOON") for v in svars}
    cell_km = max(provenance.resolution_km(reg, v, b) for v in svars for b in ("EARTH", "MOON"))
    conf: List[Optional[str]] = [None] * len(earth)
    conf_s = np.full(len(earth), np.nan)
    for i in np.flatnonzero(rank > 0):
        avail = [v for v in svars if np.isfinite(es.utilities[v][i])
                 and (v not in sim_vars or np.isfinite(sims[v][i]))]
        label, score = pair_confidence(e_levels, m_levels, weights_all, avail, cell_km, rule)
        conf[i], conf_s[i] = label, (np.nan if score is None else score)

    twin_count = np.zeros(len(moon), dtype=np.int64)
    np.add.at(twin_count, tpos[has_twin], 1)
    return MissionResult(
        mission=mission, earth_gates=eg, moon_gates=mg, earth_suit=es, soft_vars=svars,
        sim_vars=sim_vars, sim_excluded=sim_excluded, kinds=kinds, scales=scales, twin_id=twin_full, sims=sims,
        similarity_pct=sim_pct, final=final, final_published=final_pub, rank=rank, confidence=conf, confidence_score=conf_s,
        moon_twin_count=twin_count, alpha=alpha,
        extra={"cell_km_for_confidence": cell_km, "earth_levels": e_levels, "moon_levels": m_levels},
    )


def run_all(cells: Dict[str, pd.DataFrame], mission_cfg: Dict, engine_cfg: EngineConfig,
            reg: Dict) -> Dict[str, MissionResult]:
    """Run every configured mission. ``cells`` must come from table.split_bodies (sorted by id)."""
    earth, moon = cells["EARTH"], cells["MOON"]
    for body, df in cells.items():
        ids = df["id"].to_numpy()
        if ids.size and np.any(np.diff(ids) <= 0):
            raise ValueError(f"{body} cells must be sorted by unique id")
    return {m: run_mission(m, earth, moon, mission_cfg, engine_cfg, reg)
            for m in mission_ids(mission_cfg, engine_cfg)}
