"""Auditor 2: an independent re-implementation of the funnel, the suitability, the
derived similarity variables, the zones, the percentiles, the pair filter, the twin
search, the similarity, the final score and the rank, written from the documented rules
(engine_config.json, mission_scoring.json, DATA_CONTRACT.md) without importing the engine.

Differences of method from the engine, on purpose (so a match is a real confirmation):
* percentiles with scipy.stats.rankdata(method='average') instead of the engine's loop;
* the top-of-atmosphere insolation by numerical integration over the hour angle with a
  Newton-solved Kepler equation instead of the engine's closed form and fixed point;
* the Lunar base zone by intersecting each 1-degree cell square with the nine region
  polygons (shapely), instead of the engine's mask;
* the twin: maximum similarity, then the smallest lunar id among the cells within
  1e-12 of that maximum (explicit tie set) instead of numpy argmax.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from p2_common import TL, configs, tables, jload
import os

MISSIONS = ["rover", "solar", "lunar_base"]
_trapz = getattr(np, "trapezoid", None) or np.trapz


# --------------------------------------------------------------------------- columns
def mission_column(var, body):
    """Mission variable -> real column (real_data/column_aliases.json then the dataset's
    column_overrides: slope_deg is read from slope_iso_deg on both bodies)."""
    al = _ALIASES[body]
    col = al[var]["column"] if var in al and isinstance(al[var], dict) else var
    return _OVERRIDES.get(col, col)


_ALIASES = jload(os.path.join(TL, "real_data", "column_aliases.json"))
_OVERRIDES = jload(os.path.join(TL, "engine", "datasets.json"))["datasets"]["real_1deg"]["settings"]["column_overrides"]["value"]


def num(df, col):
    return pd.to_numeric(df[col], errors="coerce").to_numpy(dtype=np.float64)


# --------------------------------------------------------------------------- funnel
def gates_earth(e, mission, ms):
    """Pass flag of every Earth cell (land = mask_fraction > 0 is the bundle's row set)."""
    ok = np.ones(len(e), dtype=bool)
    # common gates, Earth: elevation_m >= 1 and mask_fraction >= 0.3 (missing -> drop)
    for v, g in ms["common_gates"].items():
        x = num(e, mission_column(v, "EARTH"))
        ok &= np.isfinite(x) & (x >= g["min"])
    b = ms["missions"][mission]
    for v in b.get("require_present", []):
        c = mission_column(v, "EARTH")
        x = e[c]
        ok &= x.notna().to_numpy() & (x.astype(str).str.len() > 0).to_numpy()
    for v, g in b.get("gates", {}).items():
        c = mission_column(v, "EARTH")
        if "exclude" in g or "allow" in g:
            s = e[c].astype(object)
            present = s.notna().to_numpy()
            if "exclude" in g:
                ok &= present & ~s.isin(g["exclude"]).to_numpy()
            if "allow" in g:
                ok &= present & s.isin(g["allow"]).to_numpy()
            continue
        x = num(e, c)
        ok &= np.isfinite(x)
        if "min" in g:
            ok &= x >= g["min"]
        if "max" in g:
            ok &= x <= g["max"]
    return ok


def utility(e, var, spec):
    c = mission_column(var, "EARTH")
    if "map" in spec:
        s = e[c]
        u = s.map(lambda k: spec["map"].get(k, spec.get("default")) if isinstance(k, str) else np.nan)
        return pd.to_numeric(u, errors="coerce").to_numpy(dtype=np.float64)
    x = num(e, c)
    u = (x - spec["bad"]) / (spec["good"] - spec["bad"])
    return np.clip(u, 0.0, 1.0)


def suitability(e, mission, ms, decimals=6):
    soft = ms["missions"][mission]["soft"]
    num_ = np.zeros(len(e))
    den = np.zeros(len(e))
    for v, spec in soft.items():
        u = utility(e, v, spec)
        u = np.where(np.isfinite(u), np.round(u, decimals), np.nan)   # published utilities (6 decimals)
        ok = np.isfinite(u)
        num_ += np.where(ok, spec["weight"] * np.nan_to_num(u), 0.0)
        den += np.where(ok, spec["weight"], 0.0)
    return np.where(den > 0, 100.0 * num_ / np.where(den > 0, den, 1), np.nan)


# --------------------------------------------------------------------------- derived values
def cos_mean(x, lat):
    ok = np.isfinite(x)
    w = np.cos(np.radians(lat))
    return float(np.sum(x[ok] * w[ok]) / np.sum(w[ok]))


def toa_numeric(lat_deg, S0=1361.0, eps_deg=23.44, ecc=0.0167, peri_deg=282.9, n_t=4000, n_h=2001):
    """Annual-mean daily TOA insolation, kWh/m2/day: Kepler by Newton, daily mean by
    trapezoidal integration of max(0, cos zenith) over the hour angle."""
    M = (np.arange(n_t) + 0.5) / n_t * 2 * np.pi
    E = M.copy()
    for _ in range(50):
        E = E - (E - ecc * np.sin(E) - M) / (1 - ecc * np.cos(E))
    nu = 2 * np.arctan(np.sqrt((1 + ecc) / (1 - ecc)) * np.tan(E / 2))
    r = 1 - ecc * np.cos(E)
    L = nu + np.radians(peri_deg)
    dec = np.arcsin(np.sin(np.radians(eps_deg)) * np.sin(L))
    H = np.linspace(-np.pi, np.pi, n_h)
    out = {}
    for la in np.unique(lat_deg):
        phi = np.radians(la)
        cz = np.sin(phi) * np.sin(dec)[:, None] + np.cos(phi) * np.cos(dec)[:, None] * np.cos(H)[None, :]
        daily = _trapz(np.maximum(cz, 0), H, axis=1) / (2 * np.pi)
        out[la] = float(np.mean(S0 / r ** 2 * daily) * 24 / 1000)
    return np.array([out[x] for x in lat_deg])


def derived(e, m, eng):
    """Similarity variables on both bodies (real values)."""
    late, latm = e["lat_deg"].to_numpy(float), m["lat_deg"].to_numpy(float)
    ev, mv, notes = {}, {}, {}
    ev["slope_deg"], mv["slope_deg"] = num(e, "slope_iso_deg"), num(m, "slope_iso_deg")
    ev["roughness_m"], mv["roughness_m"] = num(e, "roughness_m"), num(m, "roughness_m")
    ee, me = num(e, "elevation_m"), num(m, "elevation_m")
    be, bm = cos_mean(ee, late), cos_mean(me, latm)
    ev["elevation_rel_m"], mv["elevation_rel_m"] = ee - be, me - bm
    notes["elevation_body_mean"] = {"EARTH": be, "MOON": bm}
    t = eng["toa_insolation"]["value"]
    ev["irradiance_toa_kwh_m2_day"] = toa_numeric(late, t["solar_constant_w_m2"], t["obliquity_deg"],
                                                  t["eccentricity"], t["sun_longitude_at_perihelion_deg"])
    mv["irradiance_toa_kwh_m2_day"] = num(m, "irradiance_kwh_m2_day")
    ev["tmin_k"] = num(e, "tmin_c") + 273.15
    mv["tmin_k"] = num(m, "tmin_c") + 273.15
    mv["tmin_k_column"] = num(m, "tmin_k")          # the lunar table's own K column (for the check)
    ev["lst_diurnal_amp_k"], mv["lst_diurnal_amp_k"] = num(e, "lst_diurnal_amp_k"), num(m, "lst_diurnal_amp_k")
    for v in ("temp_k", "irradiance_kwh_m2_day"):
        ev[v], mv[v] = num(e, v), num(m, v)
    return ev, mv, notes


# --------------------------------------------------------------------------- zones
def lunar_base_zone(m):
    """Cells whose 1-degree square intersects one of the nine region polygons."""
    from shapely.geometry import box, shape
    from shapely.strtree import STRtree
    g = jload(os.path.join(TL, "engine", "data", "artemis_iii_regions.geojson"))
    polys = [shape(f["geometry"]) for f in g["features"]]
    names = [f["properties"]["name"] for f in g["features"]]
    lat, lon = m["lat_deg"].to_numpy(float), m["lon_deg"].to_numpy(float)
    cand = np.flatnonzero(lat < -60)
    inter = np.zeros(len(m), dtype=bool)
    area_pos = np.zeros(len(m), dtype=bool)
    region_of = {}
    for i in cand:
        b = box(lon[i] - 0.5, lat[i] - 0.5, lon[i] + 0.5, lat[i] + 0.5)
        for k, p in enumerate(polys):
            if b.intersects(p):
                inter[i] = True
                if b.intersection(p).area > 0:
                    area_pos[i] = True
                region_of.setdefault(int(i), []).append(names[k])
    return inter, area_pos, region_of


def zones(m, eng):
    lat = m["lat_deg"].to_numpy(float)
    el = num(m, "elevation_m")
    rv = eng["real_value_similarity"]["value"]["missions"]
    zr = rv["rover"]["zone"]
    zs = rv["solar"]["zone"]
    inter, area_pos, region_of = lunar_base_zone(m)
    return {"rover": lat <= zr["lat_max"],
            "solar": (np.abs(lat) <= zs["abs_lat_max"]) & (el <= zs["elevation_max_m"]),
            "lunar_base": inter}, {"lunar_base_area_positive": area_pos, "region_of": region_of}


# --------------------------------------------------------------------------- the rule
def spec(eng, mission):
    rv = eng["real_value_similarity"]["value"]
    mult = rv["filter_bound_multiplier"]
    vs = rv["missions"][mission]["variables"]
    return {"vars": [x["variable"] for x in vs], "role": [x["role"] for x in vs],
            "w": np.array([x["weight"] for x in vs], float), "tau": np.array([x["tolerance"] for x in vs], float),
            "bound": np.array([x["tolerance"] * mult[x["role"]] for x in vs], float),
            "scale": [x.get("scale", "real") for x in vs], "key": np.array([x["role"] == "key" for x in vs])}


def midrank(x):
    out = np.full(len(x), np.nan)
    ok = np.isfinite(x)
    out[ok] = 100.0 * (rankdata(x[ok], method="average") - 0.5) / ok.sum()
    return out


def pair_matrix(ev_row, mv, sp):
    """d (zone x k), pass flag, full-precision similarity of one Earth row against the zone."""
    d = np.abs(ev_row[None, :] - mv)
    fin = np.isfinite(d)
    key = sp["key"]
    within = fin & (np.nan_to_num(d, nan=np.inf) <= sp["bound"][None, :])
    ok = np.all(np.where(key[None, :], within, True), axis=1) & np.all(np.where(~key[None, :], ~fin | within, True), axis=1)
    s = np.exp(-0.5 * (np.nan_to_num(d) / sp["tau"][None, :]) ** 2)
    w = np.where(fin, sp["w"][None, :], 0.0)
    sim = 100.0 * np.sum(w * s, axis=1) / np.sum(w, axis=1)
    return d, ok, sim, s


def run(mission, e=None, m=None, eng=None, ms=None, keep_matrix_for=None):
    """Full recompute of one mission. Returns a dict of per-Earth-cell arrays over the
    passing cells (ids ascending) plus the zone, the compared values and populations."""
    if eng is None:
        eng, ms = configs()
    if e is None:
        e, m = tables()
    ev, mv, notes = derived(e, m, eng)
    zmask, zextra = zones(m, eng)
    sp = spec(eng, mission)
    passing = np.flatnonzero(gates_earth(e, mission, ms))
    zi = np.flatnonzero(zmask[mission])
    E = np.column_stack([ev[v] for v in sp["vars"]])
    M = np.column_stack([mv[v] for v in sp["vars"]])
    Ecmp = E[passing].copy()
    Mcmp = M[zi].copy()
    pops = {}
    for q, sc in enumerate(sp["scale"]):
        if sc == "percentile_within_population":
            Ecmp[:, q] = midrank(E[passing, q])
            Mcmp[:, q] = midrank(M[zi, q])
            pops[sp["vars"][q]] = {"EARTH": int(np.isfinite(E[passing, q]).sum()), "MOON": int(np.isfinite(M[zi, q]).sum())}
    n = len(passing)
    k = len(sp["vars"])
    twin = np.full(n, -1)
    best = np.full(n, np.nan)
    second = np.full(n, np.nan)
    n_pass = np.zeros(n, dtype=int)
    n_tied = np.zeros(n, dtype=int)
    pub_better = np.zeros(n, dtype=int)
    top3 = {}
    for i in range(n):
        d, ok, sim, s = pair_matrix(Ecmp[i], Mcmp, sp)
        n_pass[i] = ok.sum()
        if not ok.any():
            continue
        sv = np.where(ok, sim, -np.inf)
        mx = sv.max()
        tie = np.flatnonzero(sv >= mx - 1e-12)
        n_tied[i] = tie.size
        j = tie[np.argmin(zi[tie])]
        twin[i] = zi[j]
        best[i] = mx
        # would the published (6-decimal) scores have chosen another cell?
        sr = np.round(s, 6)
        wr = np.where(np.isfinite(d), sp["w"][None, :], 0.0)
        simr = np.where(ok, 100.0 * np.sum(wr * sr, axis=1) / np.sum(wr, axis=1), -np.inf)
        pub_better[i] = int(np.sum(simr > simr[j] + 1e-12))
        rest = np.sort(sv[np.isfinite(sv)])[::-1]
        second[i] = rest[1] if rest.size > 1 else np.nan
        if keep_matrix_for is not None and passing[i] in keep_matrix_for:
            o = np.lexsort((zi, -sv))[:3]
            top3[int(passing[i])] = [{"moon_id": int(zi[t]), "passes": bool(ok[t]), "similarity": float(sim[t]),
                                      "per_var_score": {sp["vars"][q]: float(s[t, q]) for q in range(k)},
                                      "per_var_diff": {sp["vars"][q]: float(d[t, q]) for q in range(k)}}
                                     for t in o]
            top3[int(passing[i])].append({"zone_cells_passing_filter": int(ok.sum())})
    # published per-variable scores and similarity
    has = twin >= 0
    pos = np.searchsorted(zi, np.maximum(twin, 0))
    Mt = np.where(has[:, None], Mcmp[pos], np.nan)
    D = np.abs(Ecmp - Mt)
    S = np.where(np.isfinite(D), np.round(np.exp(-0.5 * (np.nan_to_num(D) / sp["tau"]) ** 2), 6), np.nan)
    W = np.where(np.isfinite(S), sp["w"], 0.0)
    sim_pub = np.where(has, 100 * np.nansum(W * np.nan_to_num(S), axis=1) / np.where(W.sum(1) > 0, W.sum(1), 1), np.nan)
    suit = suitability(e, mission, ms)[passing]
    alpha = float(eng["mix_factor"]["value"])
    final = np.where(has, alpha * sim_pub + (1 - alpha) * suit, np.nan)
    final2 = np.array([round(x, 2) if np.isfinite(x) else np.nan for x in final])
    ids = passing
    order = np.lexsort((ids, -np.nan_to_num(final2, nan=-1e9)))
    rank = np.zeros(n, dtype=int)
    rk = 1
    for o in order:
        if has[o]:
            rank[o] = rk
            rk += 1
    real_E = E[passing]
    real_Mt = np.where(has[:, None], M[np.maximum(twin, 0)], np.nan)
    return {"mission": mission, "spec": sp, "ids": ids, "twin": twin, "best_full": best, "second_full": second,
            "n_zone_pass": n_pass, "n_tied": n_tied, "pub_better": pub_better, "scores": S, "sim_pub": sim_pub, "suit": suit, "final": final,
            "final2": final2, "rank": rank, "cmp_earth": Ecmp, "cmp_moon": Mt, "cmp_diff": D, "real_earth": real_E,
            "real_moon": real_Mt, "real_diff": np.abs(real_E - real_Mt), "zone": zi, "zone_mask": zmask[mission],
            "zones_all": zmask, "zone_extra": zextra, "populations": pops, "derived_notes": notes, "ev": ev, "mv": mv,
            "Mcmp_zone": Mcmp, "top3": top3}
