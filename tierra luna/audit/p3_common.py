"""Auditor's own model implementation for points 5, 6 and F (report 3: robustness,
external validation, statistics of the ranking).

Independent re-implementation, written for this audit, of: column resolution, funnel
(common gates, required variables, hard filters), suitability (linear utilities, category
tables, renormalised weights), derived similarity variables (relative elevation with a
cos-latitude body mean, top-of-atmosphere insolation by numerical integration over the
day and the year), mid-rank percentiles (scipy.stats.rankdata), pair filter, Gaussian
per-variable scores, twin search (argmax, ties to the lowest lunar id), final score and
rank (published 2-decimal final, ties by id).

It reads only: output_real/*.csv, real_data/column_aliases.json, mission_scoring.json,
engine/engine_config.json, engine/datasets.json, and the bundle app/public/data/v2 (for
the 280-cell Lunar base zone, read from moon_base.bin 'region', and for comparison).
No module of tierra luna/engine, mission_scoring.py or another auditor's script is
imported.
"""
from __future__ import annotations

import copy
import json
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = os.path.dirname(os.path.abspath(__file__))
TL = os.path.dirname(HERE)
REPO = os.path.dirname(TL)
OUT = os.path.join(HERE, "out")
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
MISSIONS = ("rover", "solar", "lunar_base")
os.makedirs(OUT, exist_ok=True)


# ------------------------------------------------------------------ configuration
def load_params() -> Dict:
    ms = json.load(open(os.path.join(TL, "mission_scoring.json"), encoding="utf-8"))
    ec = json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))
    ds = json.load(open(os.path.join(TL, "engine", "datasets.json"), encoding="utf-8"))
    dsv = ds["datasets"][ds["default_dataset"]["value"]]["settings"]
    rv = ec["real_value_similarity"]["value"]
    keep = ("min", "max", "allow", "exclude")
    P = {
        "common_gates": {k: {kk: vv for kk, vv in g.items() if kk in keep} for k, g in ms["common_gates"].items()},
        "common_bodies": {k: v["bodies"] for k, v in ec["gate_body_applicability"]["value"].items()},
        "alpha": float(ec["mix_factor"]["value"]),
        "score_dec": int(rv["score_decimals"]),
        "util_dec": int(ec["export_decimals"]["value"]["utility"]),
        "final_dec": int(ec["export_decimals"]["value"]["score"]),
        "mult": dict(rv["filter_bound_multiplier"]),
        "toa": dict(ec["toa_insolation"]["value"]),
        "overrides": dict(dsv["column_overrides"]["value"]),
        "var_sources": rv["variables"],
        "missions": {},
    }
    for m in MISSIONS:
        b = ms["missions"][m]
        P["missions"][m] = {
            "require": list(b.get("require_present", [])),
            "gates": {k: {kk: vv for kk, vv in g.items() if kk in keep} for k, g in b.get("gates", {}).items()},
            "soft": {k: {kk: vv for kk, vv in s.items() if kk in ("weight", "bad", "good", "map", "default")}
                     for k, s in b.get("soft", {}).items()},
            "sim": copy.deepcopy(rv["missions"][m]),
        }
    return P


# ------------------------------------------------------------------ bundle reader
def _manifest():
    return json.load(open(os.path.join(BUNDLE, "manifest.json"), encoding="utf-8"))


def bundle_col(fname: str, col: str) -> np.ndarray:
    man = _manifest()
    f = next(x for x in man["files"] if x["name"] == fname)
    c = next(x for x in f["columns"] if x["name"] == col)
    dt = {"float32": "<f4", "int32": "<i4"}[c["type"]]
    a = np.fromfile(os.path.join(BUNDLE, fname), dtype=dt, count=c["length"], offset=c["offset"])
    if c["type"] == "int32":
        out = a.astype(np.float64)
        out[a == -2147483648] = np.nan
        if c.get("divisor"):
            out = out / float(c["divisor"])
        return out
    return a.astype(np.float64)


def bundle_mission(m: str) -> pd.DataFrame:
    """Published per-point results of a mission (passing Earth cells)."""
    land_id = bundle_col("earth_base.bin", "id").astype(np.int64)
    li = bundle_col(f"earth_{m}.bin", "land_index").astype(np.int64)
    df = pd.DataFrame({"id": land_id[li]})
    for c in ("suitability", "similarity", "final", "rank", "twin"):
        df[c] = bundle_col(f"earth_{m}.bin", c)
    return df


def lunar_base_zone_ids() -> np.ndarray:
    """The 280 lunar cells of region A (NASA's nine regions) from moon_base.bin."""
    mz = json.load(open(os.path.join(BUNDLE, "mission_zones.json"), encoding="utf-8"))
    codes = [r["code"] for r in mz["regions"]]
    reg = bundle_col("moon_base.bin", "region")
    return np.flatnonzero(reg == codes.index("A")).astype(np.int64)


# ------------------------------------------------------------------ data
NEEDED = ["elevation_m", "mask_fraction", "slope_300m_deg", "rough_300m_m", "slope_deg", "roughness_m",
          "rock_or_bare_frac", "temp_k", "lst_diurnal_amp_k", "tmin_c", "irradiance_kwh_m2_day",
          "sun_elev_max_deg", "sun_low_frac_0_5deg", "thermal_inertia_class", "permafrost_class"]


def load_tables(P: Dict) -> Dict[str, pd.DataFrame]:
    aliases = json.load(open(os.path.join(TL, "real_data", "column_aliases.json"), encoding="utf-8"))
    out = {}
    for body, f in (("EARTH", "earth_real_1deg.csv"), ("MOON", "moon_real_1deg.csv")):
        raw = pd.read_csv(os.path.join(TL, "output_real", f), low_memory=False)
        raw["id"] = raw["row"].astype(int) * 360 + raw["col"].astype(int)
        raw = raw.sort_values("id").reset_index(drop=True)
        df = pd.DataFrame({"id": raw["id"].to_numpy(), "lat": raw["lat_deg"].astype(float).to_numpy(),
                           "lon": raw["lon_deg"].astype(float).to_numpy()})
        for v in NEEDED:
            col = aliases[body][v]["column"] if v in aliases[body] else v
            col = P["overrides"].get(col, col)
            df[v] = raw[col].to_numpy()
        df["elevation_raw_m"] = pd.to_numeric(raw["elevation_m"], errors="coerce").to_numpy()
        out[body] = df
    return out


def num(df: pd.DataFrame, c: str) -> np.ndarray:
    return pd.to_numeric(df[c], errors="coerce").to_numpy(dtype=np.float64)


def present(s: pd.Series) -> np.ndarray:
    t = s.astype(str).str.strip().str.lower()
    return np.array((s.notna() & ~t.isin(["", "nan", "none"])).to_numpy(), dtype=bool)


# ------------------------------------------------------------------ funnel
def funnel(df: pd.DataFrame, body: str, m: str, P: Dict) -> np.ndarray:
    M = P["missions"][m]
    ok = np.ones(len(df), dtype=bool)
    for c in M["require"]:
        ok &= present(df[c])
    gates = {k: g for k, g in P["common_gates"].items() if body in P["common_bodies"].get(k, [body])}
    gates.update(M["gates"])
    for c, g in gates.items():
        if "min" in g or "max" in g:
            v = num(df, c)
            gk = np.isfinite(v)
            if "min" in g:
                gk &= v >= float(g["min"])
            if "max" in g:
                gk &= v <= float(g["max"])
        else:
            t = df[c].astype(str).str.strip().str.lower().to_numpy()
            gk = present(df[c])
            if g.get("allow"):
                gk &= np.isin(t, [a.lower() for a in g["allow"]])
            if g.get("exclude"):
                gk &= ~np.isin(t, [a.lower() for a in g["exclude"]])
        ok &= gk
    return ok


def utility(df: pd.DataFrame, c: str, spec: Dict) -> np.ndarray:
    if "map" in spec:
        t = df[c].astype(str).str.strip().str.lower()
        mp = {k.lower(): float(v) for k, v in spec["map"].items()}
        u = np.array([mp.get(x, float(spec.get("default", 0.5))) for x in t], dtype=np.float64)
        u[~present(df[c])] = np.nan
        return u
    v = num(df, c)
    b, g = float(spec["bad"]), float(spec["good"])
    return np.clip((v - b) / (g - b), 0.0, 1.0)


def suitability(df: pd.DataFrame, m: str, P: Dict, weights: Optional[Dict[str, float]] = None,
                cache: Optional[Dict] = None) -> np.ndarray:
    soft = P["missions"][m]["soft"]
    w = {c: float(s["weight"]) for c, s in soft.items()}
    if weights:
        w.update(weights)
    num_ = np.zeros(len(df))
    den = np.zeros(len(df))
    for c, s in soft.items():
        if cache is not None and c in cache:
            u = cache[c]
        else:
            u = np.round(utility(df, c, s), P["util_dec"])
            if cache is not None:
                cache[c] = u
        ok = np.isfinite(u)
        num_ += np.where(ok, w[c] * np.where(ok, u, 0.0), 0.0)
        den += np.where(ok, w[c], 0.0)
    return np.where(den > 0, 100.0 * num_ / np.where(den > 0, den, 1.0), np.nan)


# ------------------------------------------------------------------ derived variables
def toa_insolation(lat_deg: np.ndarray, cfg: Dict, n_days: int = 730, n_h: int = 720) -> np.ndarray:
    """Annual-mean daily TOA insolation on a horizontal surface (kWh/m2/day), by brute
    numerical integration: time steps uniform over one orbit (Kepler equation solved by
    Newton), and for each day the hour angle integrated numerically (n_h steps)."""
    lat = np.asarray(lat_deg, dtype=np.float64)
    uniq, inv = np.unique(lat, return_inverse=True)
    e = float(cfg["eccentricity"])
    M = (np.arange(n_days) + 0.5) / n_days * 2 * np.pi
    E = M.copy()
    for _ in range(50):
        E = E - (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    nu = 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))
    r = 1 - e * np.cos(E)
    lam = nu + np.radians(float(cfg["sun_longitude_at_perihelion_deg"]))
    dec = np.arcsin(np.sin(np.radians(float(cfg["obliquity_deg"]))) * np.sin(lam))
    H = (np.arange(n_h) + 0.5) / n_h * 2 * np.pi - np.pi
    out = np.empty(len(uniq))
    S0 = float(cfg["solar_constant_w_m2"])
    for i, phi in enumerate(np.radians(uniq)):
        sinh = np.sin(phi) * np.sin(dec)[:, None] + np.cos(phi) * np.cos(dec)[:, None] * np.cos(H)[None, :]
        q = S0 / r[:, None] ** 2 * np.maximum(0.0, sinh)
        out[i] = q.mean() * float(cfg["hours_per_day"]) / 1000.0
    return out[inv]


def coslat_mean(v: np.ndarray, lat: np.ndarray) -> float:
    ok = np.isfinite(v)
    w = np.cos(np.radians(lat[ok]))
    return float((v[ok] * w).sum() / w.sum())


def sim_values(T: Dict[str, pd.DataFrame], P: Dict, toa: Optional[np.ndarray] = None) -> Dict[str, Dict[str, np.ndarray]]:
    """Every similarity variable on both bodies (real values)."""
    E, Mo = T["EARTH"], T["MOON"]
    out = {}
    out["slope_deg"] = {"EARTH": num(E, "slope_deg"), "MOON": num(Mo, "slope_deg")}
    out["roughness_m"] = {"EARTH": num(E, "roughness_m"), "MOON": num(Mo, "roughness_m")}
    ee, me = num(E, "elevation_m"), num(Mo, "elevation_m")
    out["elevation_rel_m"] = {"EARTH": ee - coslat_mean(ee, E["lat"].to_numpy()),
                              "MOON": me - coslat_mean(me, Mo["lat"].to_numpy())}
    if toa is None:
        toa = toa_insolation(E["lat"].to_numpy(), P["toa"])
    out["irradiance_toa_kwh_m2_day"] = {"EARTH": toa, "MOON": num(Mo, "irradiance_kwh_m2_day")}
    out["tmin_k"] = {"EARTH": num(E, "tmin_c") + 273.15, "MOON": num(Mo, "tmin_c") + 273.15}
    out["lst_diurnal_amp_k"] = {"EARTH": num(E, "lst_diurnal_amp_k"), "MOON": num(Mo, "lst_diurnal_amp_k")}
    return out


def zone_ids(Mo: pd.DataFrame, m: str, P: Dict, lb_zone: np.ndarray) -> np.ndarray:
    z = P["missions"][m]["sim"]["zone"]
    lat = Mo["lat"].to_numpy()
    if z["kind"] == "lat_max":
        mask = lat <= float(z["lat_max"])
    elif z["kind"] == "abs_lat_max_elevation_max":
        mask = (np.abs(lat) <= float(z["abs_lat_max"])) & (num(Mo, "elevation_m") <= float(z["elevation_max_m"]))
    elif z["kind"] == "similarity_zone":
        return np.sort(lb_zone)
    else:
        raise ValueError(z["kind"])
    return Mo["id"].to_numpy()[mask]


def midrank_pct(v: np.ndarray) -> np.ndarray:
    out = np.full(v.shape, np.nan)
    ok = np.isfinite(v)
    n = ok.sum()
    if n:
        out[ok] = 100.0 * (rankdata(v[ok], method="average") - 0.5) / n
    return out


# ------------------------------------------------------------------ rule
def rule_arrays(m: str, P: Dict, sim_w: Optional[Dict[str, float]] = None, drop: Optional[str] = None,
                drop_mode: str = "both"):
    """(variables, roles, weights, tau, bound, scales, in_sim, in_filter).
    drop_mode 'both': the variable leaves the similarity and the filter;
    'sim_only': it leaves the similarity (weight 0) but stays in the filter."""
    vs = P["missions"][m]["sim"]["variables"]
    names = [x["variable"] for x in vs]
    roles = [x["role"] for x in vs]
    w = np.array([float((sim_w or {}).get(x["variable"], x["weight"])) for x in vs])
    tau = np.array([float(x["tolerance"]) for x in vs])
    bound = tau * np.array([float(P["mult"][r]) for r in roles])
    scales = [x.get("scale", "real") for x in vs]
    in_sim = np.ones(len(vs), dtype=bool)
    in_f = np.ones(len(vs), dtype=bool)
    if drop is not None:
        q = names.index(drop)
        in_sim[q] = False
        if drop_mode == "both":
            in_f[q] = False
    w = np.where(in_sim, w, 0.0)
    w = w / w.sum()
    return names, roles, w, tau, bound, scales, in_sim, in_f


def twins(ev: np.ndarray, mv: np.ndarray, mids: np.ndarray, roles, w, tau, bound, in_sim, in_f,
          chunk: int = 256):
    """Own twin search. ev n x k, mv z x k (mids increasing). Returns twin id (-1),
    similarity from per-variable scores rounded to 6 decimals (published rule), NaN if none."""
    n, k = ev.shape
    key = np.array([r == "key" for r in roles])
    twin = np.full(n, -1, dtype=np.int64)
    tpos = np.full(n, -1, dtype=np.int64)
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        d = np.abs(ev[a:b, None, :] - mv[None, :, :])
        fin = np.isfinite(d)
        dd = np.where(fin, d, np.inf)
        within = dd <= bound
        okf = np.ones(d.shape[:2], dtype=bool)
        for q in range(k):
            if not in_f[q]:
                continue
            if key[q]:
                okf &= within[..., q]
            else:
                okf &= (~fin[..., q]) | within[..., q]
        s = np.exp(-0.5 * (np.where(fin, d, 0.0) / tau) ** 2)
        wq = np.where(fin & in_sim, w, 0.0)
        den = wq.sum(-1)
        sv = np.where(den > 0, (wq * s).sum(-1) / np.where(den > 0, den, 1), np.nan)
        sv = np.where(okf & np.isfinite(sv), sv, -np.inf)
        j = np.argmax(sv, axis=1)
        got = np.isfinite(sv[np.arange(b - a), j])
        tpos[a:b] = np.where(got, j, -1)
        twin[a:b] = np.where(got, mids[j], -1)
    has = tpos >= 0
    sim = np.full(n, np.nan)
    if has.any():
        d = np.abs(ev[has] - mv[tpos[has]])
        fin = np.isfinite(d) & in_sim
        sc = np.round(np.exp(-0.5 * (np.where(fin, d, 0.0) / tau) ** 2), 6)
        wq = np.where(fin, w, 0.0)
        sim[has] = 100.0 * (wq * sc).sum(-1) / wq.sum(-1)
    return twin, sim, tpos


def run_mission(T: Dict[str, pd.DataFrame], m: str, P: Dict, lb_zone: np.ndarray,
                SV: Optional[Dict] = None, suit_w=None, sim_w=None, drop=None, drop_mode="both",
                passE: Optional[np.ndarray] = None, util_cache: Optional[Dict] = None) -> pd.DataFrame:
    """Funnel, suitability, twins, similarity, final and rank for every passing Earth cell."""
    E, Mo = T["EARTH"], T["MOON"]
    if SV is None:
        SV = sim_values(T, P)
    if passE is None:
        passE = funnel(E, "EARTH", m, P)
    pi = np.flatnonzero(passE)
    suit = suitability(E.iloc[pi], m, P, suit_w, util_cache)
    names, roles, w, tau, bound, scales, in_sim, in_f = rule_arrays(m, P, sim_w, drop, drop_mode)
    zids = zone_ids(Mo, m, P, lb_zone)
    zpos = np.searchsorted(Mo["id"].to_numpy(), zids)
    ev = np.column_stack([SV[v]["EARTH"][pi] for v in names])
    mv = np.column_stack([SV[v]["MOON"][zpos] for v in names])
    for q, sc in enumerate(scales):
        if sc == "percentile_within_population":
            ev[:, q] = midrank_pct(ev[:, q])
            mv[:, q] = midrank_pct(mv[:, q])
    twin, sim, tpos = twins(ev, mv, zids, roles, w, tau, bound, in_sim, in_f)
    final = P["alpha"] * sim + (1 - P["alpha"]) * suit
    fpub = np.round(final, P["final_dec"])
    ids = E["id"].to_numpy()[pi]
    ok = np.isfinite(fpub)
    order = np.lexsort((ids, -np.where(ok, fpub, -np.inf)))
    order = order[ok[order]]
    rank = np.zeros(len(pi), dtype=np.int64)
    rank[order] = np.arange(1, len(order) + 1)
    return pd.DataFrame({"id": ids, "suitability": suit, "similarity": sim, "final": final,
                         "final_pub": fpub, "rank": rank, "twin": twin})


def audio_pairs() -> List[Dict]:
    d = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
    out = []
    for m, v in d["missions"].items():
        for p in v["pairs"]:
            out.append({"mission": m, "rank": int(p["rank"]), "earth_id": int(p["earth_cell_id"][1:]),
                        "moon_id": int(p["moon_cell_id"][1:]), "place": p["earth_place"]["speakable"],
                        "similarity": p["similarity"], "suitability": p["suitability"], "final": p["final"]})
    return out


def dump(name: str, obj) -> str:
    path = os.path.join(OUT, name)

    def conv(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.ndarray):
            return [conv(x) for x in o.tolist()]
        raise TypeError(type(o))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=conv)
    return path
