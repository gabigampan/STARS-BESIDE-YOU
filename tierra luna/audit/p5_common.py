"""Auditor's own implementation (points A and D of the audit, reviewer 5).

Independent re-implementation of the funnel, suitability, real-value similarity, pair
filter, mid-rank percentiles, twin search, final score and rank. It reads ONLY:
  * the real tables  output_real/earth_real_1deg.csv, moon_real_1deg.csv
  * mission_scoring.json, engine/engine_config.json, engine/datasets.json (numbers)
  * engine/data/artemis_iii_regions.geojson (Lunar base zone)
  * the bundle app/public/data/v2 (for comparison only)
No module of the engine (tierra luna/engine) or mission_scoring.py is imported here.
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
TL = os.path.dirname(HERE)                      # ".../tierra luna"
REPO = os.path.dirname(TL)
OUT = os.path.join(HERE, "out")
BUNDLE = os.path.join(REPO, "app", "public", "data", "v2")
MISSIONS = ("rover", "solar", "lunar_base")


# ------------------------------------------------------------------ configuration
def load_params() -> Dict:
    """Every number the model uses, read from the three configuration files."""
    ms = json.load(open(os.path.join(TL, "mission_scoring.json"), encoding="utf-8"))
    ec = json.load(open(os.path.join(TL, "engine", "engine_config.json"), encoding="utf-8"))
    ds = json.load(open(os.path.join(TL, "engine", "datasets.json"), encoding="utf-8"))
    dsv = ds["datasets"][ds["default_dataset"]["value"]]["settings"]
    rv = ec["real_value_similarity"]["value"]
    P = {
        "on_missing_gate": ms["on_missing_gate"],
        "common_gates": {k: {kk: vv for kk, vv in g.items() if kk in ("min", "max", "allow", "exclude")}
                         for k, g in ms["common_gates"].items()},
        "common_bodies": {k: v["bodies"] for k, v in ec["gate_body_applicability"]["value"].items()},
        "missions": {},
        "alpha": float(ec["mix_factor"]["value"]),
        "score_decimals": int(rv["score_decimals"]),
        "utility_decimals": int(ec["export_decimals"]["value"]["utility"]),
        "final_decimals": int(ec["export_decimals"]["value"]["score"]),
        "mult": dict(rv["filter_bound_multiplier"]),
        "toa": dict(ec["toa_insolation"]["value"]),
        "kelvin_offset": float(rv["variables"]["tmin_k"]["sources"]["EARTH"]["offset_k"]),
        "body_mean_weighting": "coslat",
        "percentile_rule": "midrank",
        "overrides": dict(dsv["column_overrides"]["value"]),
        "zones_cfg": ec["similarity_zones"]["value"],
        "regions_file": os.path.join(TL, ec["similarity_zones"]["value"]["lunar_base"]["regions_file"]),
        "body_mean_scale": {"EARTH": 1.0, "MOON": 1.0},
    }
    for m in MISSIONS:
        b = ms["missions"][m]
        P["missions"][m] = {
            "require_present": list(b.get("require_present", [])),
            "gates": {k: {kk: vv for kk, vv in g.items() if kk in ("min", "max", "allow", "exclude")}
                      for k, g in b.get("gates", {}).items()},
            "soft": {k: {kk: vv for kk, vv in s.items() if kk in ("weight", "bad", "good", "map", "default")}
                     for k, s in b.get("soft", {}).items()},
            "sim": copy.deepcopy(rv["missions"][m]),
        }
    return P


# ------------------------------------------------------------------ data
def load_tables(P: Dict) -> Dict[str, pd.DataFrame]:
    """Both tables with the mission variable names resolved (column aliases + overrides)."""
    aliases = json.load(open(os.path.join(TL, "real_data", "column_aliases.json"), encoding="utf-8"))
    out = {}
    for body, f in (("EARTH", "earth_real_1deg.csv"), ("MOON", "moon_real_1deg.csv")):
        raw = pd.read_csv(os.path.join(TL, "output_real", f), low_memory=False)
        raw["id"] = raw["row"].astype(int) * 360 + raw["col"].astype(int)
        raw = raw.sort_values("id").reset_index(drop=True)
        df = pd.DataFrame({"id": raw["id"], "lat": raw["lat_deg"].astype(float), "lon": raw["lon_deg"].astype(float)})
        for var, a in aliases[body].items():
            if var.startswith("_"):
                continue
            col = a["column"]
            col = P["overrides"].get(col, col)            # slope_deg -> slope_iso_deg on both bodies
            df[var] = raw[col]
        df["__raw_tmin_k"] = raw["tmin_k"] if "tmin_k" in raw.columns else np.nan
        out[body] = df
    return out


def present(s: pd.Series) -> np.ndarray:
    txt = s.astype(str).str.strip().str.lower()
    return (s.notna() & ~txt.isin(["", "nan", "none"])).to_numpy()


# ------------------------------------------------------------------ funnel
def gate_pass(df: pd.DataFrame, body: str, m: str, P: Dict) -> np.ndarray:
    mm = P["missions"][m]
    ok = np.ones(len(df), dtype=bool)
    gates = {}
    for k, g in P["common_gates"].items():
        if body in P["common_bodies"].get(k, ["EARTH", "MOON"]):
            gates[k] = g
    gates.update(mm["gates"])
    for v in mm["require_present"]:
        ok &= present(df[v])
    for v, g in gates.items():
        s = df[v]
        if "min" in g or "max" in g:
            x = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
            okv = np.array(np.isfinite(x), dtype=bool)
            if g.get("min") is not None:
                okv &= np.where(np.isfinite(x), x, -np.inf) >= g["min"]
            if g.get("max") is not None:
                okv &= np.where(np.isfinite(x), x, np.inf) <= g["max"]
        else:
            t = s.astype(str).str.strip().str.lower()
            okv = np.array((s.notna() & ~t.isin(["", "nan"])).to_numpy(), dtype=bool)
            if g.get("allow"):
                okv &= t.isin([a.lower() for a in g["allow"]]).to_numpy()
            if g.get("exclude"):
                okv &= ~t.isin([a.lower() for a in g["exclude"]]).to_numpy()
        ok &= okv
    return ok


def pyround(a: np.ndarray, d: int) -> np.ndarray:
    return np.array([round(float(x), d) if np.isfinite(x) else np.nan for x in np.asarray(a, float)])


def suitability(df: pd.DataFrame, m: str, P: Dict, passed: np.ndarray):
    soft = P["missions"][m]["soft"]
    num = np.zeros(len(df))
    den = np.zeros(len(df))
    utils = {}
    for v, s in soft.items():
        if "map" in s:
            t = df[v].astype(str).str.strip().str.lower()
            mp = {k.lower(): float(x) for k, x in s["map"].items()}
            u = t.map(mp).astype(float).to_numpy()
            pr = (df[v].notna() & ~t.isin(["", "nan"])).to_numpy()
            u = np.where(np.isnan(u) & pr, float(s.get("default", 0.5)), u)
            u = np.where(pr, u, np.nan)
        else:
            x = pd.to_numeric(df[v], errors="coerce").to_numpy(dtype=float)
            u = np.clip((x - float(s["bad"])) / (float(s["good"]) - float(s["bad"])), 0, 1)
        u = np.where(passed, u, np.nan)
        u = pyround(u, P["utility_decimals"]) if P["utility_decimals"] is not None else u
        utils[v] = u
        ok = np.isfinite(u)
        w = float(s["weight"])
        num += np.where(ok, w * np.where(ok, u, 0), 0)
        den += np.where(ok, w, 0)
    score = np.where(passed & (den > 0), 100 * num / np.where(den > 0, den, 1), np.nan)
    return score, utils


# ------------------------------------------------------------------ derived values
def toa_kwh(lat: np.ndarray, c: Dict) -> np.ndarray:
    """Annual-mean daily TOA insolation on a horizontal surface, by integration over the
    TRUE anomaly with the time weight dt ~ r^2 dnu (Kepler's second law); a different
    numerical route from the engine's mean-anomaly sampling. Daily mean
    Q = S0/pi/r^2 (h0 sin phi sin d + cos phi cos d sin h0)."""
    e = float(c["eccentricity"])
    n = 20000
    nu = (np.arange(n) + 0.5) * 2 * np.pi / n
    r = (1 - e * e) / (1 + e * np.cos(nu))            # au
    wt = r ** 2
    wt = wt / wt.sum()
    L = nu + np.radians(float(c["sun_longitude_at_perihelion_deg"]))
    dec = np.arcsin(np.sin(np.radians(float(c["obliquity_deg"]))) * np.sin(L))
    out = {}
    for la in np.unique(lat):
        phi = np.radians(la)
        x = np.clip(-np.tan(phi) * np.tan(dec), -1, 1)
        h0 = np.arccos(x)
        q = float(c["solar_constant_w_m2"]) / np.pi / r ** 2 * (h0 * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(h0))
        out[la] = float((q * wt).sum()) * float(c["hours_per_day"]) / 1000.0
    return np.array([out[x] for x in lat])


def body_mean(x: np.ndarray, lat: np.ndarray, how: str) -> float:
    ok = np.isfinite(x)
    w = np.cos(np.radians(lat)) if how == "coslat" else np.ones_like(lat)
    return float((x[ok] * w[ok]).sum() / w[ok].sum())


def derived(T: Dict[str, pd.DataFrame], P: Dict) -> Dict[str, Dict[str, np.ndarray]]:
    E, M = T["EARTH"], T["MOON"]
    d: Dict[str, Dict[str, np.ndarray]] = {}
    for v in ("slope_deg", "roughness_m"):
        d[v] = {b: pd.to_numeric(T[b][v], errors="coerce").to_numpy(float) for b in T}
    d["elevation_rel_m"] = {}
    d["_body_mean"] = {}
    for b in T:
        x = pd.to_numeric(T[b]["elevation_m"], errors="coerce").to_numpy(float)
        mu = body_mean(x, T[b]["lat"].to_numpy(float), P["body_mean_weighting"]) * P["body_mean_scale"][b]
        d["_body_mean"][b] = mu
        d["elevation_rel_m"][b] = x - mu
    d["irradiance_toa_kwh_m2_day"] = {"EARTH": toa_kwh(E["lat"].to_numpy(float), P["toa"]),
                                      "MOON": pd.to_numeric(M["irradiance_kwh_m2_day"], errors="coerce").to_numpy(float)}
    d["tmin_k"] = {b: pd.to_numeric(T[b]["tmin_c"], errors="coerce").to_numpy(float) + P["kelvin_offset"] for b in T}
    d["lst_diurnal_amp_k"] = {b: pd.to_numeric(T[b]["lst_diurnal_amp_k"], errors="coerce").to_numpy(float) for b in T}
    return d


# ------------------------------------------------------------------ zones
_REGION_CACHE: Dict[str, np.ndarray] = {}


def artemis_mask(M: pd.DataFrame, path: str) -> np.ndarray:
    """Lunar cells whose 1-degree square intersects a region polygon (geopandas sjoin)."""
    if path in _REGION_CACHE:
        return _REGION_CACHE[path]
    import geopandas as gpd
    from shapely.geometry import box
    reg = gpd.read_file(path)
    lat, lon = M["lat"].to_numpy(float), M["lon"].to_numpy(float)
    sel = np.flatnonzero(lat < -60)
    cells = gpd.GeoDataFrame({"i": sel}, geometry=[box(lon[i] - .5, lat[i] - .5, lon[i] + .5, lat[i] + .5) for i in sel],
                             crs=reg.crs)
    j = gpd.sjoin(cells, reg[["geometry"]], predicate="intersects", how="inner")
    mask = np.zeros(len(M), dtype=bool)
    mask[np.unique(j["i"].to_numpy())] = True
    _REGION_CACHE[path] = mask
    return mask


def zone_mask(M: pd.DataFrame, m: str, P: Dict) -> np.ndarray:
    z = P["missions"][m]["sim"]["zone"]
    lat = M["lat"].to_numpy(float)
    if z["kind"] == "lat_max":
        return lat <= float(z["lat_max"])
    if z["kind"] == "abs_lat_max_elevation_max":
        el = pd.to_numeric(M[z["elevation_column"]], errors="coerce").to_numpy(float)
        return (np.abs(lat) <= float(z["abs_lat_max"])) & (el <= float(z["elevation_max_m"]))
    if z["kind"] == "similarity_zone":
        if "override_mask" in z:
            return z["override_mask"]
        return artemis_mask(M, P["regions_file"])
    raise ValueError(z["kind"])


def percentile(x: np.ndarray, rule: str = "midrank") -> np.ndarray:
    out = np.full(x.shape, np.nan)
    ok = np.isfinite(x)
    n = ok.sum()
    if n == 0:
        return out
    r = rankdata(x[ok], method="average")
    if rule == "midrank":
        out[ok] = 100 * (r - 0.5) / n
    elif rule == "rank_over_n":
        out[ok] = 100 * r / n
    elif rule == "weibull":
        out[ok] = 100 * r / (n + 1)
    else:
        raise ValueError(rule)
    return out


# ------------------------------------------------------------------ the pairing
def run_mission(T, D, m: str, P: Dict, chunk: int = 96) -> Dict:
    E, M = T["EARTH"], T["MOON"]
    passed = gate_pass(E, "EARTH", m, P)
    suit, utils = suitability(E, m, P, passed)
    sim_cfg = P["missions"][m]["sim"]
    vs = [x for x in sim_cfg["variables"] if float(x.get("weight", 0)) >= 0 and not x.get("_removed")]
    names = [x["variable"] for x in vs]
    w = np.array([float(x["weight"]) for x in vs])
    tau = np.array([float(x["tolerance"]) for x in vs])
    key = np.array([x["role"] == "key" for x in vs])
    bound = tau * np.array([P["mult"][x["role"]] for x in vs])
    scales = [x.get("scale", "real") for x in vs]
    zone = zone_mask(M, m, P)
    zi = np.flatnonzero(zone)
    pi = np.flatnonzero(passed)
    ev = np.column_stack([D[v]["EARTH"][pi] for v in names]) if names else np.zeros((len(pi), 0))
    mv = np.column_stack([D[v]["MOON"][zi] for v in names]) if names else np.zeros((len(zi), 0))
    for q, sc in enumerate(scales):
        if sc == "percentile_within_population":
            ev[:, q] = percentile(ev[:, q], P["percentile_rule"])
            mv[:, q] = percentile(mv[:, q], P["percentile_rule"])
    n = len(pi)
    twin_pos = np.full(n, -1)
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        d = np.abs(ev[a:b, None, :] - mv[None, :, :])
        fin = np.isfinite(d)
        dd = np.where(fin, d, np.inf)
        okk = np.all(~key | (fin & (dd <= bound)), axis=2)
        oks = np.all(key | ~fin | (dd <= bound), axis=2)
        ok = okk & oks
        s = np.exp(-0.5 * (np.where(fin, d, 0) / tau) ** 2)
        num = (np.where(fin, s, 0) * w).sum(axis=2)
        den = (np.where(fin, 1.0, 0.0) * w).sum(axis=2)
        sv = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
        sv = np.where(ok & np.isfinite(sv), sv, -np.inf)
        j = np.argmax(sv, axis=1)
        got = np.isfinite(sv[np.arange(b - a), j])
        twin_pos[a:b] = np.where(got, j, -1)
    has = twin_pos >= 0
    twin_id = np.where(has, M["id"].to_numpy()[zi][np.maximum(twin_pos, 0)], -1)
    mvt = np.where(has[:, None], mv[np.maximum(twin_pos, 0)], np.nan)
    diff = np.abs(ev - mvt)
    fin = np.isfinite(diff)
    sc = np.where(fin, np.rint(np.exp(-0.5 * (np.where(fin, diff, 0) / tau) ** 2) * 10 ** P["score_decimals"]) / 10 ** P["score_decimals"], np.nan)
    num = np.zeros(n)
    den = np.zeros(n)
    for q in range(len(names)):
        ok = fin[:, q]
        num = num + np.where(ok, w[q] * np.where(ok, sc[:, q], 0), 0)
        den = den + np.where(ok, w[q], 0)
    sim = np.where(has & (den > 0), 100 * num / np.where(den > 0, den, 1), np.nan)
    a = P["alpha"]
    fin_score = a * sim + (1 - a) * suit[pi]
    fin_pub = pyround(fin_score, P["final_decimals"])
    ids = E["id"].to_numpy()[pi]
    okr = np.isfinite(fin_pub)
    order = np.lexsort((ids, -np.where(okr, fin_pub, -np.inf)))
    order = order[okr[order]]
    rank = np.zeros(n, dtype=int)
    rank[order] = np.arange(1, len(order) + 1)
    return {"mission": m, "passed": passed, "pass_ids": ids, "suit": suit[pi], "sim": sim, "final": fin_score,
            "final_pub": fin_pub, "rank": rank, "twin": twin_id, "scores": sc, "ev": ev, "mvt": mvt,
            "diff": diff, "vars": names, "zone_n": int(zone.sum()), "moon_pass": gate_pass(M, "MOON", m, P),
            "utils": {k: v[pi] for k, v in utils.items()}}


def top_ids(r: Dict, k: int) -> List[int]:
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    o = o[r["rank"][o] > 0][:k]
    return [int(r["pass_ids"][i]) for i in o]


def top_pairs(r: Dict, k: int) -> List[tuple]:
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    o = o[r["rank"][o] > 0][:k]
    return [(int(r["pass_ids"][i]), int(r["twin"][i])) for i in o]


# ------------------------------------------------------------------ bundle reader
def bundle_columns(fname: str) -> Dict[str, np.ndarray]:
    man = json.load(open(os.path.join(BUNDLE, "manifest.json"), encoding="utf-8"))
    ent = [f for f in man["files"] if f["name"] == fname][0]
    raw = open(os.path.join(BUNDLE, fname), "rb").read()
    out = {}
    for c in ent["columns"]:
        dt = "<f4" if c["type"] == "float32" else "<i4"
        a = np.frombuffer(raw, dtype=dt, count=c["length"], offset=c["offset"]).astype(np.float64 if dt == "<f4" else np.int64)
        if c["type"] == "int32":
            miss = a == -2147483648
            if c.get("divisor"):
                a = a.astype(np.float64) / float(c["divisor"])
                a[miss] = np.nan
            else:
                a = a.astype(np.float64)
                a[miss] = np.nan
        out[c["name"]] = a
    return out


def bundle_mission(m: str) -> Dict[str, np.ndarray]:
    base = bundle_columns("earth_base.bin")
    mb = bundle_columns(f"earth_{m}.bin")
    ids = base["id"][mb["land_index"].astype(int)].astype(int)
    out = {"ids": ids, **{k: v for k, v in mb.items() if k not in ("fail_bits",)}}
    return out
