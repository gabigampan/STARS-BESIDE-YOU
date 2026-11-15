"""Similarity on REAL values within stated tolerances (rule ``real_value_tolerance``).

Team decision of 2026-11-15 (morning; the team lead's delegate on his behalf), applied
to the Rover and Solar panels missions (engine_config ``similarity_rule``); Lunar base
keeps the z-score ``zone_twin`` rule until the team confirms a new proposal.

For an Earth cell e and a lunar cell m of the mission's zone, per similarity variable v
(engine_config ``real_value_similarity``):

    d_v = |value_e(v) - value_m(v)|                    real values, the variable's unit
    s_v = exp(-0.5 * (d_v / tau_v)^2)                  published at score_decimals (q / 1e6)
    similarity = 100 * sum_v w_v * s_v / sum_v w_v     over the variables with a value on both
                                                       sides, summed in the configured order

Pair filter: every key variable with d_v <= key_multiplier * tau_v (a missing key value
fails), every secondary variable with d_v <= secondary_multiplier * tau_v (a missing
secondary value is left out of the filter and of the similarity, its weight
renormalised). The twin is the zone cell that passes the filter with the highest
similarity (ties: lowest lunar id). A cell with no zone cell passing has no twin, no
similarity, no final and no rank; the reason is recorded (which variable and the
smallest gap found).

Derived variables (DERIVED, never MEASURED):

* ``elevation_rel_m``: elevation_m minus the area-weighted (cos latitude) mean of
  elevation_m over every cell of the same body that has a value.
* ``irradiance_toa_kwh_m2_day`` on Earth: annual-mean daily sunlight on a horizontal
  surface at the top of the atmosphere, from the latitude alone (Kepler orbit,
  engine_config ``toa_insolation``). On the Moon the variable is the lunar table's
  surface irradiance (no atmosphere), column irradiance_kwh_m2_day.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

NOPAIR_KINDS = ["key_value_missing_on_earth", "no_zone_cell_within_bound", "no_joint_match"]


# ----------------------------------------------------------------------------- derived values
def toa_daily_insolation_kwh(lat_deg: np.ndarray, cfg: Dict) -> np.ndarray:
    """Annual-mean daily insolation on a horizontal surface at the top of Earth's
    atmosphere, kWh/m2/day, for each latitude (degrees).

    Kepler orbit sampled uniformly in time: mean anomaly M on ``mean_anomaly_samples``
    equal steps; eccentric anomaly E from M = E - e sin E (fixed-point iteration,
    ``kepler_iterations`` times); true anomaly nu; Sun-Earth distance r = 1 - e cos E (au);
    solar longitude L = nu + sun_longitude_at_perihelion; declination
    d = asin(sin(eps) sin(L)); sunset hour angle h0 = acos(clip(-tan(phi) tan(d), -1, 1));
    daily mean Q = S0 / pi / r^2 * (h0 sin(phi) sin(d) + cos(phi) cos(d) sin(h0)) W/m2;
    annual mean of Q times hours_per_day / 1000. (The checker's corrected formula of
    docs/ANALOG_PRINCIPLE.md, section "Comprobación", item 1.)"""
    lat = np.asarray(lat_deg, dtype=np.float64)
    uniq, inv = np.unique(lat, return_inverse=True)
    phi = np.radians(uniq)[:, None]
    n = int(cfg["mean_anomaly_samples"])
    ecc = float(cfg["eccentricity"])
    mean_anom = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    ecc_anom = mean_anom.copy()
    for _ in range(int(cfg["kepler_iterations"])):
        ecc_anom = mean_anom + ecc * np.sin(ecc_anom)
    nu = 2.0 * np.arctan2(np.sqrt(1.0 + ecc) * np.sin(ecc_anom / 2.0), np.sqrt(1.0 - ecc) * np.cos(ecc_anom / 2.0))
    r = 1.0 - ecc * np.cos(ecc_anom)
    lam = nu + np.radians(float(cfg["sun_longitude_at_perihelion_deg"]))
    dec = np.arcsin(np.sin(np.radians(float(cfg["obliquity_deg"]))) * np.sin(lam))[None, :]
    h0 = np.arccos(np.clip(-np.tan(phi) * np.tan(dec), -1.0, 1.0))
    q = float(cfg["solar_constant_w_m2"]) / np.pi / r[None, :] ** 2 * (
        h0 * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(h0))
    out = q.mean(axis=1) * float(cfg["hours_per_day"]) / 1000.0
    return out[inv]


def area_weighted_mean(values: np.ndarray, lat_deg: np.ndarray) -> Optional[float]:
    """Mean of the finite values weighted by cos(latitude) (cell area on a sphere)."""
    v = np.asarray(values, dtype=np.float64)
    w = np.cos(np.radians(np.asarray(lat_deg, dtype=np.float64)))
    ok = np.isfinite(v)
    if not ok.any():
        return None
    return float((v[ok] * w[ok]).sum() / w[ok].sum())


@dataclass
class DerivedValues:
    """Per-body arrays of every real-value similarity variable, and how they were made."""

    values: Dict[str, Dict[str, np.ndarray]]      # variable -> body -> array over the body's rows
    notes: Dict[str, Dict[str, Dict]]             # variable -> body -> {source, formula, level, ...}


def derive_values(earth: pd.DataFrame, moon: pd.DataFrame, var_defs: Dict[str, Dict], toa_cfg: Dict) -> DerivedValues:
    """Build every variable of engine_config ``real_value_similarity.variables`` on both
    bodies. Source kinds: ``column`` (the frame column as it is), ``relative_to_body_mean``
    (column minus its area-weighted body mean), ``toa_insolation`` (latitude formula)."""
    vals: Dict[str, Dict[str, np.ndarray]] = {}
    notes: Dict[str, Dict[str, Dict]] = {}
    for v, d in var_defs.items():
        vals[v], notes[v] = {}, {}
        for body, df in (("EARTH", earth), ("MOON", moon)):
            src = d["sources"][body]
            kind = src["kind"]
            if kind == "column":
                a = pd.to_numeric(df[src["column"]], errors="coerce").to_numpy(dtype=np.float64)
                note = {"kind": kind, "column": src["column"]}
            elif kind == "relative_to_body_mean":
                raw = pd.to_numeric(df[src["column"]], errors="coerce").to_numpy(dtype=np.float64)
                mean = area_weighted_mean(raw, df["lat_deg"].to_numpy(dtype=np.float64))
                a = raw - (mean if mean is not None else np.nan)
                note = {"kind": kind, "column": src["column"], "body_mean": mean,
                        "cells_in_mean": int(np.isfinite(raw).sum())}
            elif kind == "toa_insolation":
                a = toa_daily_insolation_kwh(df["lat_deg"].to_numpy(dtype=np.float64), toa_cfg)
                note = {"kind": kind}
            else:
                raise ValueError(f"unknown source kind {kind!r} for {v} on {body}")
            note.update({"level": src.get("level"), "text": src.get("text")})
            vals[v][body], notes[v][body] = a, note
    return DerivedValues(values=vals, notes=notes)


def zone_mask_real(moon: pd.DataFrame, zone: Dict) -> np.ndarray:
    """Lunar cells of a real-value zone. ``lat_max``: centre latitude <= lat_max;
    ``abs_lat_max_elevation_max``: |latitude| <= abs_lat_max and elevation_m <= elevation_max_m
    (analog_finder.build_lunar_reference_zones' equatorial maria); ``all``: every cell."""
    lat = moon["lat_deg"].to_numpy(dtype=np.float64)
    if zone["kind"] == "lat_max":
        return lat <= float(zone["lat_max"])
    if zone["kind"] == "abs_lat_max_elevation_max":
        el = pd.to_numeric(moon[zone["elevation_column"]], errors="coerce").to_numpy(dtype=np.float64)
        return (np.abs(lat) <= float(zone["abs_lat_max"])) & (el <= float(zone["elevation_max_m"]))
    if zone["kind"] == "all":
        return np.ones(len(moon), dtype=bool)
    raise ValueError(f"unknown real-value zone kind {zone['kind']!r}")


# ----------------------------------------------------------------------------- the rule
@dataclass(frozen=True)
class RuleSpec:
    """One mission's real-value rule, in the configured variable order."""

    variables: List[str]
    roles: List[str]            # "key" or "secondary"
    weights: np.ndarray
    tau: np.ndarray
    bound: np.ndarray           # tau * multiplier of the role
    score_decimals: int

    @property
    def key(self) -> np.ndarray:
        return np.array([r == "key" for r in self.roles])


def rule_spec(mission_rule: Dict, multipliers: Dict[str, float], score_decimals: int) -> RuleSpec:
    vs = mission_rule["variables"]
    roles = [x["role"] for x in vs]
    bad = [r for r in roles if r not in multipliers]
    if bad:
        raise ValueError(f"unknown variable role(s) {bad}")
    tau = np.array([float(x["tolerance"]) for x in vs])
    return RuleSpec(variables=[x["variable"] for x in vs], roles=roles,
                    weights=np.array([float(x["weight"]) for x in vs]), tau=tau,
                    bound=np.array([float(multipliers[r]) for r in roles]) * tau, score_decimals=score_decimals)


def quantise(s: np.ndarray, decimals: int) -> np.ndarray:
    """rint(s * 10^d) / 10^d: exactly the double the browser decodes from q (q / 10^d)."""
    div = 10.0 ** decimals
    return np.rint(s * div) / div


def scores(d: np.ndarray, tau: np.ndarray, decimals: int) -> np.ndarray:
    """Published per-variable scores of absolute differences ``d`` (last axis = variables)."""
    return quantise(np.exp(-0.5 * (d / tau) ** 2), decimals)


def weighted_similarity(s: np.ndarray, present: np.ndarray, w: np.ndarray) -> np.ndarray:
    """100 * sum(w * s) / sum(w) over present variables, summed in variable order
    (the browser's order); NaN when nothing is present."""
    num = np.zeros(s.shape[:-1])
    den = np.zeros(s.shape[:-1])
    for k in range(s.shape[-1]):
        ok = present[..., k]
        num = num + np.where(ok, w[k] * np.where(ok, s[..., k], 0.0), 0.0)
        den = den + np.where(ok, w[k], 0.0)
    return np.where(den > 0, 100.0 * num / np.where(den > 0, den, 1.0), np.nan)


def passes_filter(d: np.ndarray, spec: RuleSpec) -> np.ndarray:
    """Pair filter on absolute differences ``d`` (NaN = a value missing on a side)."""
    fin = np.isfinite(d)
    key = spec.key
    within = fin & (np.where(fin, d, np.inf) <= spec.bound)
    ok_key = np.where(key, within, True).all(axis=-1)
    ok_sec = np.where(~key, ~fin | within, True).all(axis=-1)
    return ok_key & ok_sec


@dataclass
class RealTwins:
    twin: np.ndarray                  # lunar id, -1 when no pair
    similarity: np.ndarray            # unrounded similarity from published scores, NaN when no pair
    scores: np.ndarray                # n x k published scores (NaN: no pair or value missing)
    earth_values: np.ndarray          # n x k
    moon_values: np.ndarray           # n x k (NaN when no pair)
    diff: np.ndarray                  # n x k absolute differences (NaN when no pair or missing)
    nopair_kind: np.ndarray           # index into NOPAIR_KINDS, -1 when paired
    nopair_var: np.ndarray            # variable index, -1 when paired
    nopair_gap: np.ndarray            # the smallest gap found for that variable (NaN when paired)
    best_gap: np.ndarray              # n x k: smallest |d| over the zone per variable (every row)
    extra: Dict = field(default_factory=dict)


def find_twins(ev: np.ndarray, mv: np.ndarray, zone_ids: np.ndarray, spec: RuleSpec, chunk_rows: int) -> RealTwins:
    """Twin of every Earth row of ``ev`` (n x k real values) among the zone rows ``mv``
    (z x k, ids ``zone_ids`` strictly increasing)."""
    zone_ids = np.asarray(zone_ids)
    if zone_ids.size and np.any(np.diff(zone_ids) <= 0):
        raise ValueError("zone ids must be strictly increasing")
    n, k = ev.shape
    twin = np.full(n, -1, dtype=np.int64)
    sim = np.full(n, np.nan)
    tpos = np.full(n, -1, dtype=np.int64)
    best_gap = np.full((n, k), np.nan)
    nk = np.full(n, -1, dtype=np.int64)
    nv = np.full(n, -1, dtype=np.int64)
    ng = np.full(n, np.nan)
    key = spec.key
    if mv.shape[0] == 0:
        raise ValueError("the real-value zone has no lunar cell")
    for a in range(0, n, chunk_rows):
        b = min(a + chunk_rows, n)
        d = np.abs(ev[a:b, None, :] - mv[None, :, :])                # rows x zone x k
        fin = np.isfinite(d)
        ok = passes_filter(d, spec)
        s = np.where(fin, scores(np.where(fin, d, 0.0), spec.tau, spec.score_decimals), np.nan)
        sv = weighted_similarity(s, fin, spec.weights)
        sv = np.where(ok & np.isfinite(sv), sv, -np.inf)
        j = np.argmax(sv, axis=1)                                     # first maximum = lowest id
        best = sv[np.arange(b - a), j]
        got = np.isfinite(best)
        twin[a:b] = np.where(got, zone_ids[j] if zone_ids.size else -1, -1)
        tpos[a:b] = np.where(got, j, -1)
        sim[a:b] = np.where(got, best, np.nan)
        if d.shape[1]:
            best_gap[a:b] = np.where(fin.any(axis=1), np.min(np.where(fin, d, np.inf), axis=1), np.nan)
        # reasons for the rows without a pair
        for r in np.flatnonzero(~got):
            i = a + r
            miss_key = [q for q in range(k) if key[q] and not np.isfinite(ev[i, q])]
            if miss_key:
                nk[i], nv[i], ng[i] = 0, miss_key[0], np.nan
                continue
            alone = [q for q in range(k) if np.isfinite(ev[i, q]) and (
                (np.isfinite(best_gap[i, q]) and best_gap[i, q] > spec.bound[q])
                or (key[q] and not np.isfinite(best_gap[i, q])))]
            if alone:
                nk[i], nv[i], ng[i] = 1, alone[0], best_gap[i, alone[0]]
                continue
            ratio = np.where(fin[r], d[r] / spec.bound, 0.0)            # zone x k
            worst = ratio.max(axis=1)
            c = int(np.argmin(worst))
            q = int(np.argmax(ratio[c]))
            nk[i], nv[i], ng[i] = 2, q, d[r, c, q]
    moon_vals = np.full((n, k), np.nan)
    has = tpos >= 0
    moon_vals[has] = mv[tpos[has]]
    diff = np.abs(ev - moon_vals)
    fin = np.isfinite(diff)
    sc = np.where(fin, scores(np.where(fin, diff, 0.0), spec.tau, spec.score_decimals), np.nan)
    sc[~has] = np.nan
    sim2 = np.where(has, weighted_similarity(sc, fin, spec.weights), np.nan)
    if not np.array_equal(np.isnan(sim2), np.isnan(sim)) or np.any(sim2[has] != sim[has]):
        raise AssertionError("twin similarity is not reproduced from the published scores")
    return RealTwins(twin=twin, similarity=sim, scores=sc, earth_values=ev, moon_values=moon_vals,
                     diff=np.where(has[:, None], diff, np.nan), nopair_kind=nk, nopair_var=nv, nopair_gap=ng,
                     best_gap=best_gap)


def list_order(rank: np.ndarray, suitability_published: np.ndarray, passing: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """Display order of the passing cells: the paired cells by rank, then the cells without
    a twin by published suitability descending, ties by id; 0 for cells not passing."""
    n = len(rank)
    order = np.zeros(n, dtype=np.int64)
    paired = np.flatnonzero(passing & (rank > 0))
    paired = paired[np.argsort(rank[paired], kind="mergesort")]
    un = np.flatnonzero(passing & (rank <= 0))
    un = un[np.lexsort((ids[un], -suitability_published[un]))]
    seq = np.concatenate([paired, un])
    order[seq] = np.arange(1, seq.size + 1)
    return order


def nopair_summary(rt: RealTwins, spec: RuleSpec, rows: np.ndarray, decimals: int) -> List[Dict]:
    """Counts of the no-pair reasons among ``rows`` (Earth rows passing the funnel), by
    kind and variable, commonest first, with the smallest and median gap."""
    from engine.export import rnd

    out: Dict[Tuple[int, int], List[float]] = {}
    for i in rows:
        if rt.nopair_kind[i] >= 0:
            out.setdefault((int(rt.nopair_kind[i]), int(rt.nopair_var[i])), []).append(float(rt.nopair_gap[i]))
    res = []
    for (kd, q), gaps in out.items():
        g = np.array(gaps)
        g = g[np.isfinite(g)]
        res.append({"kind": NOPAIR_KINDS[kd], "variable": spec.variables[q], "role": spec.roles[q],
                    "bound": rnd(spec.bound[q], 6), "earth_cells": len(gaps),
                    "gap_min": rnd(g.min(), decimals) if g.size else None,
                    "gap_median": rnd(float(np.median(g)), decimals) if g.size else None,
                    "gap_max": rnd(g.max(), decimals) if g.size else None})
    res.sort(key=lambda r: (-r["earth_cells"], r["kind"], r["variable"]))
    return res
