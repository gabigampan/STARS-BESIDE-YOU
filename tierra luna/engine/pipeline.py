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
from engine.config import (REPO_RULES, EngineConfig, mission_components, mission_ids, mission_similarity_rule,
                           similarity_rules)
from engine.confidence import pair_confidence
from engine.gates import GateResult, evaluate_gates
from engine.pairing import pair_twins
from engine.repo_similarity import RepoContext, published_similarity_check, zone_twins
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
    rule: str = "physical_pooled"       # similarity rule that produced sims / similarity_pct / twins
    components: Dict[str, "ComponentResult"] = field(default_factory=dict)  # info components (lunar_base: ice)
    extra: Dict = field(default_factory=dict)


@dataclass
class ComponentResult:
    """An information component of a mission (lunar_base: ice): gates and suitability
    on Earth, gates on the Moon. Never changes the mission's ranking."""

    mission: str
    earth_gates: GateResult
    moon_gates: GateResult
    earth_suit: SuitabilityResult
    soft_vars: List[str]


def _present(s: pd.Series) -> np.ndarray:
    """True where a cell has a value (numeric finite or a non-empty category)."""
    txt = s.astype(str).str.strip().str.lower()
    return (s.notna() & ~txt.isin(["", "nan"])).to_numpy()


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
                engine_cfg: EngineConfig, reg: Dict, ctx: Optional[RepoContext] = None,
                real: Optional[Dict] = None) -> MissionResult:
    """Compute one mission for both bodies (see module docstring).

    The similarity rule of the mission comes from engine_config ``similarity_rule``;
    the two repository rules need ``ctx`` and the real-value rule ``real`` (both built
    once by :func:`run_all`)."""
    rule = mission_similarity_rule(engine_cfg, mission)
    if rule == "real_value_tolerance":
        return _run_mission_real(mission, earth, moon, mission_cfg, engine_cfg, reg, real)
    if rule != "physical_pooled":
        return _run_mission_repo(mission, earth, moon, mission_cfg, engine_cfg, reg, ctx, rule)
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
    m_has = {v: _present(moon[v]) for v in svars}
    conf: List[Optional[str]] = [None] * len(earth)
    conf_s = np.full(len(earth), np.nan)
    for i in np.flatnonzero(rank > 0):
        e_av = [v for v in svars if np.isfinite(es.utilities[v][i])]
        m_av = [v for v in svars if m_has[v][tpos[i]]]
        both = [v for v in e_av if v in m_av]
        label, score = pair_confidence(e_levels, m_levels, weights_all, both, cell_km, rule, e_av, m_av)
        conf[i], conf_s[i] = label, (np.nan if score is None else score)

    twin_count = np.zeros(len(moon), dtype=np.int64)
    np.add.at(twin_count, tpos[has_twin], 1)
    return MissionResult(
        mission=mission, earth_gates=eg, moon_gates=mg, earth_suit=es, soft_vars=svars,
        sim_vars=sim_vars, sim_excluded=sim_excluded, kinds=kinds, scales=scales, twin_id=twin_full, sims=sims,
        similarity_pct=sim_pct, final=final, final_published=final_pub, rank=rank, confidence=conf, confidence_score=conf_s,
        moon_twin_count=twin_count, alpha=alpha, rule="physical_pooled",
        extra={"cell_km_for_confidence": cell_km, "earth_levels": e_levels, "moon_levels": m_levels},
    )


def _confidence(mission: str, svars: List[str], weights_all: Dict[str, float], earth: pd.DataFrame,
                moon: pd.DataFrame, es: SuitabilityResult, rank: np.ndarray, tpos: Optional[np.ndarray],
                engine_cfg: EngineConfig, reg: Dict):
    """Confidence of every ranked Earth cell (engine_config 'confidence'). The Moon side
    is the twin's cell when there is one; without a twin (repo_global_mean, whose
    target is the whole Moon) a variable counts on the Moon when it has data on the
    lunar table at all."""
    rule = engine_cfg.v("confidence")
    e_levels = {v: provenance.level(reg, v, "EARTH") for v in svars}
    m_levels = {v: provenance.level(reg, v, "MOON") for v in svars}
    cell_km = max(provenance.resolution_km(reg, v, b) for v in svars for b in ("EARTH", "MOON"))
    m_has = {v: _present(moon[v]) for v in svars}
    m_any = [v for v in svars if m_has[v].any()]
    conf: List[Optional[str]] = [None] * len(earth)
    conf_s = np.full(len(earth), np.nan)
    for i in np.flatnonzero(rank > 0):
        e_av = [v for v in svars if np.isfinite(es.utilities[v][i])]
        m_av = [v for v in svars if m_has[v][tpos[i]]] if tpos is not None else m_any
        both = [v for v in e_av if v in m_av]
        label, score = pair_confidence(e_levels, m_levels, weights_all, both, cell_km, rule, e_av, m_av)
        conf[i], conf_s[i] = label, (np.nan if score is None else score)
    return conf, conf_s, {"cell_km_for_confidence": cell_km, "earth_levels": e_levels, "moon_levels": m_levels}


def _run_mission_repo(mission: str, earth: pd.DataFrame, moon: pd.DataFrame, mission_cfg: Dict,
                      engine_cfg: EngineConfig, reg: Dict, ctx: Optional[RepoContext], rule: str) -> MissionResult:
    """One mission with the repository's similarity (repo_global_mean or zone_twin).

    Funnel: gates (both bodies) -> suitability of the surviving Earth cells ->
    similarity -> final = alpha * similarity + (1 - alpha) * suitability -> rank.
    The similarity of an eliminated cell is never used: it has no final and no rank."""
    if ctx is None:
        raise ValueError("the repository similarity rules need a RepoContext")
    eg = evaluate_gates(earth, "EARTH", mission, mission_cfg, engine_cfg)
    mg = evaluate_gates(moon, "MOON", mission, mission_cfg, engine_cfg)
    es = evaluate_suitability(earth, "EARTH", mission, mission_cfg, engine_cfg)
    if not np.array_equal(es.passed, eg.passed):
        raise AssertionError("evaluate() and the gate module disagree on Earth pass flags")
    svars = soft_variables(mission_cfg, mission)
    weights_all = soft_weights(mission_cfg, mission)
    moon_ids = moon["id"].to_numpy()
    twin = np.full(len(earth), -1, dtype=np.int64)
    sim = np.full(len(earth), np.nan)
    passing = np.flatnonzero(eg.passed)
    if rule == "repo_global_mean":
        sim[passing] = ctx.global_similarity[passing]
    elif rule == "zone_twin":
        zone = ctx.zones[mission]["mask"]
        tw, s = zone_twins(ctx, passing, zone, moon_ids, int(engine_cfg.v("pairing_chunk_rows")))
        twin[passing], sim[passing] = tw, s
    else:
        raise ValueError(rule)
    published_similarity_check(sim)
    alpha = float(engine_cfg.v("mix_factor"))
    frame = pd.DataFrame({"similarity_pct": sim, f"score_{mission}": es.score})
    final = mission_scoring.combine_with_similarity(frame, mission, alpha=alpha).to_numpy(dtype=np.float64)
    final = np.where(eg.passed, final, np.nan)  # an eliminated cell never gets a final score
    final_pub = round_like_export(final, int(engine_cfg.v("export_decimals")["score"]))
    rank = rank_scores(final_pub, earth["id"].to_numpy())
    has_twin = twin >= 0
    tpos = np.where(has_twin, np.searchsorted(moon_ids, np.maximum(twin, 0)), 0) if rule == "zone_twin" else None
    conf, conf_s, extra = _confidence(mission, svars, weights_all, earth, moon, es, rank, tpos, engine_cfg, reg)
    twin_count = np.zeros(len(moon), dtype=np.int64)
    if tpos is not None:
        np.add.at(twin_count, tpos[has_twin], 1)
    return MissionResult(
        mission=mission, earth_gates=eg, moon_gates=mg, earth_suit=es, soft_vars=svars,
        sim_vars=list(ctx.active), sim_excluded=dict(ctx.excluded), kinds={v: "numeric" for v in ctx.active},
        scales={}, twin_id=twin, sims={}, similarity_pct=sim, final=final, final_published=final_pub, rank=rank,
        confidence=conf, confidence_score=conf_s, moon_twin_count=twin_count, alpha=alpha, rule=rule, extra=extra,
    )


def build_real_context(earth: pd.DataFrame, moon: pd.DataFrame, engine_cfg: EngineConfig) -> Dict:
    """Derived values of every real-value similarity variable on both bodies (once per build)."""
    from engine.real_similarity import derive_values

    rv = engine_cfg.v("real_value_similarity")
    dv = derive_values(earth, moon, rv["variables"], engine_cfg.v("toa_insolation"))
    return {"settings": rv, "derived": dv}


def _run_mission_real(mission: str, earth: pd.DataFrame, moon: pd.DataFrame, mission_cfg: Dict,
                      engine_cfg: EngineConfig, reg: Dict, real: Optional[Dict]) -> MissionResult:
    """One mission with the real-value rule (engine.real_similarity).

    Funnel unchanged: gates -> suitability of the survivors. Each survivor is compared
    with every lunar cell of the mission's zone on real values; the twin is the cell
    passing the pair filter with the highest similarity. A survivor without a twin keeps
    its suitability and has no similarity, final or rank (it is listed after the paired
    cells by suitability, real_similarity.list_order)."""
    from engine.real_similarity import find_twins, list_order, rule_spec, zone_mask_real

    if real is None:
        real = build_real_context(earth, moon, engine_cfg)
    rv = real["settings"]
    mrule = rv["missions"][mission]
    spec = rule_spec(mrule, rv["filter_bound_multiplier"], int(rv["score_decimals"]))
    eg = evaluate_gates(earth, "EARTH", mission, mission_cfg, engine_cfg)
    mg = evaluate_gates(moon, "MOON", mission, mission_cfg, engine_cfg)
    es = evaluate_suitability(earth, "EARTH", mission, mission_cfg, engine_cfg)
    if not np.array_equal(es.passed, eg.passed):
        raise AssertionError("evaluate() and the gate module disagree on Earth pass flags")
    svars = soft_variables(mission_cfg, mission)
    weights_all = soft_weights(mission_cfg, mission)
    moon_ids = moon["id"].to_numpy()
    zone = zone_mask_real(moon, mrule["zone"])
    zi = np.flatnonzero(zone)
    dv = real["derived"].values
    ev_all = np.column_stack([dv[v]["EARTH"] for v in spec.variables])
    mv_all = np.column_stack([dv[v]["MOON"] for v in spec.variables])
    passing = np.flatnonzero(eg.passed)
    rt = find_twins(ev_all[passing], mv_all[zi], moon_ids[zi], spec, int(engine_cfg.v("pairing_chunk_rows")))
    n = len(earth)
    k = len(spec.variables)

    def full(a, fill=np.nan, dtype=np.float64):
        shape = (n,) + a.shape[1:]
        out = np.full(shape, fill, dtype=dtype)
        out[passing] = a
        return out

    twin = full(rt.twin, -1, np.int64)
    sim = full(rt.similarity)
    alpha = float(engine_cfg.v("mix_factor"))
    frame = pd.DataFrame({"similarity_pct": sim, f"score_{mission}": es.score})
    final = mission_scoring.combine_with_similarity(frame, mission, alpha=alpha).to_numpy(dtype=np.float64)
    final = np.where(eg.passed & (twin >= 0), final, np.nan)  # no twin -> no final
    final_pub = round_like_export(final, int(engine_cfg.v("export_decimals")["score"]))
    rank = rank_scores(final_pub, earth["id"].to_numpy())
    suit_pub = round_like_export(np.where(eg.passed, es.score, np.nan), int(engine_cfg.v("export_decimals")["score"]))
    order = list_order(rank, suit_pub, eg.passed, earth["id"].to_numpy())
    has_twin = twin >= 0
    tpos = np.where(has_twin, np.searchsorted(moon_ids, np.maximum(twin, 0)), 0)
    conf, conf_s, extra = _confidence(mission, svars, weights_all, earth, moon, es, rank, tpos, engine_cfg, reg)
    twin_count = np.zeros(len(moon), dtype=np.int64)
    np.add.at(twin_count, tpos[has_twin], 1)
    info_vars = [v for v in rv["info_differences"].get(mission, []) if v in earth.columns and v in moon.columns]
    info = {}
    for v in info_vars:
        e = pd.to_numeric(earth[v], errors="coerce").to_numpy(dtype=np.float64)
        m = pd.to_numeric(moon[v], errors="coerce").to_numpy(dtype=np.float64)
        mt = np.where(has_twin, m[tpos], np.nan)
        info[v] = {"earth": np.where(has_twin, e, np.nan), "moon": mt, "diff": np.abs(np.where(has_twin, e, np.nan) - mt)}
    extra["real"] = {
        "spec": spec, "mission_rule": mrule, "zone_mask": zone, "zone_cells": int(zone.sum()),
        "scores": full(rt.scores), "earth_values": full(rt.earth_values), "moon_values": full(rt.moon_values),
        "diff": full(rt.diff), "nopair_kind": full(rt.nopair_kind, -1, np.int64),
        "nopair_var": full(rt.nopair_var, -1, np.int64), "nopair_gap": full(rt.nopair_gap),
        "best_gap": full(rt.best_gap), "list_order": order, "info": info, "derived": real["derived"],
        "settings": rv,
    }
    return MissionResult(
        mission=mission, earth_gates=eg, moon_gates=mg, earth_suit=es, soft_vars=svars,
        sim_vars=list(spec.variables), sim_excluded={}, kinds={v: "numeric" for v in spec.variables},
        scales={}, twin_id=twin, sims={v: extra["real"]["scores"][:, q] for q, v in enumerate(spec.variables)},
        similarity_pct=sim, final=final, final_published=final_pub, rank=rank, confidence=conf,
        confidence_score=conf_s, moon_twin_count=twin_count, alpha=alpha, rule="real_value_tolerance", extra=extra,
    )


def run_component(component: str, earth: pd.DataFrame, moon: pd.DataFrame, mission_cfg: Dict,
                  engine_cfg: EngineConfig) -> ComponentResult:
    """Gates and Earth suitability of an information component (e.g. ice for lunar_base)."""
    eg = evaluate_gates(earth, "EARTH", component, mission_cfg, engine_cfg)
    mg = evaluate_gates(moon, "MOON", component, mission_cfg, engine_cfg)
    es = evaluate_suitability(earth, "EARTH", component, mission_cfg, engine_cfg)
    return ComponentResult(mission=component, earth_gates=eg, moon_gates=mg, earth_suit=es,
                           soft_vars=soft_variables(mission_cfg, component))


def run_all(cells: Dict[str, pd.DataFrame], mission_cfg: Dict, engine_cfg: EngineConfig,
            reg: Dict, ctx: Optional[RepoContext] = None) -> Dict[str, MissionResult]:
    """Run every offered mission and its information components. ``cells`` must come
    from table.split_bodies (sorted by id). ``ctx`` (the repository similarity) is
    built here when the rule needs it and none is given."""
    earth, moon = cells["EARTH"], cells["MOON"]
    for body, df in cells.items():
        ids = df["id"].to_numpy()
        if ids.size and np.any(np.diff(ids) <= 0):
            raise ValueError(f"{body} cells must be sorted by unique id")
    missions = mission_ids(mission_cfg, engine_cfg)
    rules = similarity_rules(engine_cfg, missions)
    if any(r in REPO_RULES for r in rules.values()) and ctx is None:
        from engine.similarity_context import build_repo_context
        ctx = build_repo_context(earth, moon, engine_cfg, missions)
    real = build_real_context(earth, moon, engine_cfg) if "real_value_tolerance" in rules.values() else None
    out = {m: run_mission(m, earth, moon, mission_cfg, engine_cfg, reg, ctx, real) for m in missions}
    for m, res in out.items():
        res.components = {c: run_component(c, earth, moon, mission_cfg, engine_cfg)
                          for c in mission_components(mission_cfg, m)["info"]}
        res.extra["repo_context"] = ctx
    return out
