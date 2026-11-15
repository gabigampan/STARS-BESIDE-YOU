"""Point 8: every figure of the 19 audio tracks against the engine (own code path).

Run:  <venv python> "tierra luna/audit/p4_audio_check.py"
Writes tierra luna/audit/out/p4_audio_facts.json (all recomputed facts) and
tierra luna/audit/out/p4_recompute_summary.json. Deterministic; reads only the bundle,
the real tables, the engine data files (geojson, gazetteer) and the GeoNames copy in the
reverse_geocoder package. Does not import the engine.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p4_common import (BUNDLE, ENGINE_DATA, OUT, R_EARTH, R_MOON, REPO, Bundle, cell_latlon, compass8,  # noqa: E402
                       haversine_km, initial_bearing_deg, load_tables, midrank_pct, pair_all, pct_of_value_in,
                       toa_kwh_m2_day)

import reverse_geocoder  # noqa: E402  (only for the path of its GeoNames cities1000 copy)
from shapely.geometry import Polygon, shape  # noqa: E402

GEONAMES = os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv")


def f32_tenths(x: float) -> Decimal:
    s = np.format_float_positional(np.float32(x), unique=True)
    return Decimal(s).quantize(Decimal("0.1"), ROUND_HALF_UP)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    B = Bundle()
    E, M = load_tables()
    lat_e = E["lat_deg"].values
    lat_m, lon_m = M["lat_deg"].values, M["lon_deg"].values
    base_ids = B.col("earth_base.bin", "id").astype(int)
    summary = {}
    facts = {}

    # ------------------------------------------------------------- own lunar zones
    gj = json.load(open(os.path.join(ENGINE_DATA, "artemis_iii_regions.geojson")))
    regions = [(f["properties"]["name"], shape(f["geometry"])) for f in gj["features"]]

    def stereo(lat, lon):  # south polar stereographic on the 1737.4 km sphere (own code)
        k = 2 * R_MOON * np.tan(np.pi / 4 + np.radians(lat) / 2)
        return k * np.sin(np.radians(lon)), k * np.cos(np.radians(lon))

    reg_proj = []
    for name, g in regions:
        polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
        pp = []
        for p in polys:
            xs, ys = stereo(np.array([c[1] for c in p.exterior.coords]), np.array([c[0] for c in p.exterior.coords]))
            pp.append(Polygon(list(zip(xs, ys))))
        reg_proj.append((name, pp))

    def cell_regions(cid):
        la, lo = cell_latlon(cid)
        t = np.linspace(0, 1, 21)
        edge_lat = np.concatenate([np.full(21, la - .5), la - .5 + t, np.full(21, la + .5), la + .5 - t])
        edge_lon = np.concatenate([lo - .5 + t, np.full(21, lo + .5), lo + .5 - t, np.full(21, lo - .5)])
        x, y = stereo(edge_lat, edge_lon)
        sq = Polygon(list(zip(x, y)))
        return [n for n, pp in reg_proj if any(sq.intersects(p) for p in pp)]

    cand = np.where(lat_m <= -80 + 0.0)[0]
    cand = np.where(lat_m <= -75)[0]
    zone_base = np.array([c for c in cand if cell_regions(c)], dtype=int)
    reg_col = B.col("moon_base.bin", "region")
    mz = B.json("mission_zones.json")
    codes = [r["code"] for r in mz["regions"]]
    bundle_A = np.where(np.array([codes[int(i)] for i in reg_col]) == "A")[0]
    summary["lunar_base_zone_own_cells"] = int(zone_base.size)
    summary["lunar_base_zone_equals_bundle_region_A"] = bool(np.array_equal(np.sort(zone_base), np.sort(bundle_A)))

    zone_rover = np.where(lat_m <= -75.0)[0]
    zone_solar = np.where((np.abs(lat_m) <= 30.0) & (M["elevation_m"].values <= -1200.0))[0]
    summary["rover_zone_cells"] = int(zone_rover.size)
    summary["solar_zone_cells"] = int(zone_solar.size)

    # ------------------------------------------------------------- own funnels (Earth)
    el = E["elevation_m"].values
    mask = E["mask_fraction"].values
    slope = E["slope_iso_deg"].values
    rough = E["roughness_m"].values
    irr = E["irradiance_kwh_m2_day"].values
    sem = E["sun_elev_max_deg"].values
    slf = E["sun_low_frac_0_5deg"].values
    tic = E["thermal_inertia_class"].astype(str).values
    amp = E["lst_diurnal_amp_k"].values
    tmin = E["tmin_c"].values
    common = (el >= 1.0) & (mask >= 0.3)
    with np.errstate(invalid="ignore"):
        pass_rover = common & (slope >= 0.5) & (slope <= 15) & (rough >= 5) & (rough <= 650)
        pass_solar = common & (irr >= 2.5) & (slope <= 15) & (sem >= 10) & (slf <= 0.25) & (tic != "agua") & ~np.isnan(irr) & ~np.isnan(sem) & ~np.isnan(slf) & ~np.isnan(slope)
        pass_base = common & (amp >= 15) & (tmin <= 5) & (tic != "agua") & (tic != "nan")
    own_pass = {"rover": np.where(pass_rover)[0], "solar": np.where(pass_solar)[0], "lunar_base": np.where(pass_base)[0]}

    # relative elevation: area-weighted mean of cells with a value (own)
    def wmean(v, la):
        ok = ~np.isnan(v)
        w = np.cos(np.radians(la[ok]))
        return float(np.sum(v[ok] * w) / np.sum(w)), int(ok.sum())
    e_mean, e_n = wmean(el, lat_e)
    m_mean, m_n = wmean(M["elevation_m"].values, lat_m)
    summary["body_means"] = {"EARTH": [round(e_mean, 4), e_n], "MOON": [round(m_mean, 4), m_n]}
    erel = el - e_mean
    mrel = M["elevation_m"].values - m_mean
    toa_rows = toa_kwh_m2_day(90.0 - (np.arange(180) + 0.5))
    toa_e = toa_rows[E["row"].values]
    m_slope = M["slope_iso_deg"].values
    m_rough = M["roughness_m"].values
    m_irr = M["irradiance_kwh_m2_day"].values
    m_tmin_k = M["tmin_c"].values + 273.15
    m_amp = M["lst_diurnal_amp_k"].values

    sim_vars = {}
    missions = B.json("missions.json")
    for ms in missions["missions"]:
        sim_vars[ms["id"]] = ms["similarity"]["variables"]

    # Earth / Moon compared matrices
    base_pass = own_pass["lunar_base"]
    e_tmin_pct_pass = midrank_pct(tmin[base_pass] + 273.15)
    e_amp_pct_pass = midrank_pct(amp[base_pass])
    m_tmin_pct_zone = midrank_pct(m_tmin_k[zone_base])
    m_amp_pct_zone = midrank_pct(m_amp[zone_base])
    spec = {
        "rover": (np.column_stack([slope, rough, erel]), np.column_stack([m_slope, m_rough, mrel]), zone_rover),
        "solar": (np.column_stack([toa_e, slope, rough]), np.column_stack([m_irr, m_slope, m_rough]), zone_solar),
    }
    own = {}
    for mid in ["rover", "solar", "lunar_base"]:
        v = sim_vars[mid]
        tol = [x["tolerance"] for x in v]
        roles = [x["role"] for x in v]
        w = [x["weight"] for x in v]
        P = own_pass[mid]
        if mid == "lunar_base":
            Ep = np.column_stack([e_tmin_pct_pass, e_amp_pct_pass, slope[P], rough[P]])
            Mz = np.column_stack([m_tmin_pct_zone, m_amp_pct_zone, m_slope[zone_base], m_rough[zone_base]])
            zid = zone_base
        else:
            Eall, Mall, zid = spec[mid]
            Ep = Eall[P]
            Mz = Mall[zid]
        twin, sim, sc = pair_all(Ep, Mz, zid.astype(np.int64), tol, roles, w)
        own[mid] = {"P": P, "twin": twin, "sim": sim, "scores": sc}

    # ------------------------------------------------------------- bundle per mission + rank recompute
    bund = {}
    for mid, f in [("rover", "earth_rover.bin"), ("solar", "earth_solar.bin"), ("lunar_base", "earth_lunar_base.bin")]:
        li = B.col(f, "land_index").astype(int)
        ids = base_ids[li]
        d = {"ids": ids}
        for c in ["suitability", "similarity", "final", "rank", "twin"]:
            d[c] = B.col(f, c)
        bund[mid] = d
        o = own[mid]
        s = {"own_passing": int(o["P"].size), "bundle_passing": int(ids.size),
             "passing_sets_equal": bool(np.array_equal(o["P"], ids))}
        if s["passing_sets_equal"]:
            bt = np.nan_to_num(d["twin"], nan=-1).astype(int)
            s["twins_equal_all"] = int(np.sum(bt == o["twin"]))
            s["paired_own"] = int(np.sum(o["twin"] >= 0))
            s["paired_bundle"] = int(np.sum(bt >= 0))
            ds = np.abs(np.round(o["sim"], 2) - d["similarity"])
            s["similarity_max_abs_diff"] = float(np.nanmax(ds))
            fin = 0.5 * o["sim"] + 0.5 * d["suitability"]
            okf = ~np.isnan(fin)
            key = np.lexsort((ids[okf], -np.round(fin[okf], 2)))
            own_rank = np.full(ids.size, np.nan)
            own_rank[np.where(okf)[0][key]] = np.arange(1, okf.sum() + 1)
            s["ranks_equal"] = int(np.sum(own_rank == d["rank"]))
            s["ranks_compared"] = int(okf.sum())
            s["final_own_vs_bundle_max_abs_diff"] = float(np.nanmax(np.abs(fin - d["final"])))
            # rank re-derived by own sort of the PUBLISHED final (ties by id): must equal the stored rank
            okb = ~np.isnan(d["final"])
            kb = np.lexsort((ids[okb], -d["final"][okb]))
            rb = np.full(ids.size, np.nan)
            rb[np.where(okb)[0][kb]] = np.arange(1, okb.sum() + 1)
            s["rank_from_published_final_equal"] = int(np.sum(rb == d["rank"]))
            # how many places the own-final rank moves a pair (ties within 0.01 only)
            s["own_rank_max_shift"] = int(np.nanmax(np.abs(own_rank - d["rank"])))
            gap = np.abs(np.round(fin, 2) - d["final"])
            s["pairs_where_own_final_2dp_differs"] = int(np.nansum(gap > 0.0001))
            s["top5_bundle"] = [int(ids[np.where(d["rank"] == r)[0][0]]) for r in range(1, 6)]
            s["top5_own"] = [int(ids[np.where(own_rank == r)[0][0]]) for r in range(1, 6)]
            s["distinct_twins_own"] = int(np.unique(o["twin"][o["twin"] >= 0]).size)
            s["unpaired_own"] = int(np.sum(o["twin"] < 0))
        summary[mid] = s
        own[mid]["rank"] = own_rank

    # ------------------------------------------------------------- gazetteers
    gn = []
    with open(GEONAMES, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            gn.append((float(r["lat"]), float(r["lon"]), r["name"], r["admin1"], r["cc"]))
    gn_lat = np.array([g[0] for g in gn])
    gn_lon = np.array([g[1] for g in gn])
    iau = B.json("iau_moon_features.json")
    f_lat = np.array(iau["lat"], float)
    f_lon = np.array(iau["lon"], float)
    # full gazetteer (incl. satellite features) for "is a closer named feature hidden?"
    full = []
    with open(os.path.join(ENGINE_DATA, "iau_moon_nomenclature.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            full.append(r)
    places = B.json("places.json")
    pdj = B.json("place_detail.json")
    np_idx = B.col("earth_place_detail.bin", "nearest_place")
    np_km = B.col("earth_place_detail.bin", "nearest_place_km")
    country = B.col("earth_base.bin", "country")
    region = B.col("earth_base.bin", "region")
    ne = json.load(open(os.path.join(ENGINE_DATA, "ne_110m_admin_0_countries.geojson")))
    ne_shapes = [(f["properties"].get("ADMIN") or f["properties"].get("NAME"), shape(f["geometry"])) for f in ne["features"]]
    from shapely.geometry import Point

    m_feat = B.col("moon_base.bin", "feature")
    m_feat_km = B.col("moon_base.bin", "feature_km")

    # percentile populations
    land_slope = slope[~np.isnan(slope) & (mask > 0)]
    land_rough = rough[~np.isnan(rough) & (mask > 0)]
    land_tmin = tmin[(mask > 0) & ~np.isnan(tmin)]
    land_amp = amp[(mask > 0) & ~np.isnan(amp)]

    pairs_files = {"rover": "earth_rover_pairs.bin", "solar": "earth_solar_pairs.bin", "lunar_base": "earth_lunar_base_pairs.bin"}
    for mid in ["rover", "solar", "lunar_base"]:
        d = bund[mid]
        pf = pairs_files[mid]
        pcols = {c: B.col(pf, c) for c in B.columns(pf)}
        out = []
        for r in range(1, 6):
            i = int(np.where(d["rank"] == r)[0][0])
            eid = int(d["ids"][i])
            tid = int(d["twin"][i])
            la, lo = cell_latlon(eid)
            mla, mlo = cell_latlon(tid)
            k = int(np.where(base_ids == eid)[0][0])
            # earth place
            dist = haversine_km(la, lo, gn_lat, gn_lon, R_EARTH)
            j = int(np.argmin(dist))
            pl = gn[j]
            brg = initial_bearing_deg(pl[0], pl[1], la, lo)
            ctry_poly = [n for n, g in ne_shapes if g.contains(Point(lo, la))]
            bundle_place = pdj["nearest_places"][int(np_idx[k])]
            # moon feature (published primary features)
            fd = haversine_km(mla, mlo, f_lat, f_lon, R_MOON)
            fj = int(np.argmin(fd))
            fd_full = []
            for row in full:
                try:
                    flat = float(row.get("center_lat") or row.get("lat"))
                    flon = float(row.get("center_lon_e360") or row.get("lon"))
                except (TypeError, ValueError):
                    continue
                if flon > 180:
                    flon -= 360
                fd_full.append((float(haversine_km(mla, mlo, flat, flon, R_MOON)), row.get("name"), row.get("type") or row.get("code")))
            fd_full.sort()
            item = {
                "rank": r, "earth_id": eid, "moon_id": tid, "earth_latlon": [la, lo], "moon_latlon": [mla, mlo],
                "own_rank": int(own[mid]["rank"][i]), "own_twin": int(own[mid]["twin"][i]),
                "similarity_bundle": d["similarity"][i], "similarity_own": round(float(own[mid]["sim"][i]), 4),
                "suitability": d["suitability"][i], "final": d["final"][i],
                "earth_place_own": {"name": pl[2], "admin1": pl[3], "cc": pl[4], "km": round(float(dist[j]), 1),
                                    "bearing_deg": round(brg, 1), "compass8": compass8(brg)},
                "earth_place_bundle": {"name": bundle_place, "km": float(np_km[k]),
                                       "country": places["countries"][int(country[k])]["name"] if not np.isnan(country[k]) else None,
                                       "region": places["regions"][int(region[k])] if not np.isnan(region[k]) else None},
                "country_ne110m_own": ctry_poly,
                "moon_feature_own": {"name": iau["name"][fj], "type": iau["type"][fj], "km": round(float(fd[fj]), 1)},
                "moon_feature_bundle": {"name": iau["name"][int(m_feat[tid])], "km": float(m_feat_km[tid])},
                "closest_three_full_gazetteer": [(round(a, 1), b, c) for a, b, c in fd_full[:3]],
                "moon_region_code": codes[int(reg_col[tid])],
                "moon_elevation_m": float(M["elevation_m"].values[tid]),
                "moon_elev_pct_all_moon": round(pct_of_value_in(M["elevation_m"].values, M["elevation_m"].values[tid]), 1),
            }
            if mid == "lunar_base":
                item["nasa_regions_own"] = cell_regions(tid)
            # values: from the real tables (own) and the pairs file
            vals = {}
            if mid in ("rover", "solar", "lunar_base"):
                vals["slope_earth"] = float(slope[eid]); vals["slope_moon"] = float(m_slope[tid])
                vals["rough_earth"] = float(rough[eid]); vals["rough_moon"] = float(m_rough[tid])
                vals["slope_pct_earth_land"] = round(pct_of_value_in(land_slope, slope[eid]), 1)
                vals["slope_pct_moon_all"] = round(pct_of_value_in(m_slope, m_slope[tid]), 1)
                vals["rough_pct_earth_land"] = round(pct_of_value_in(land_rough, rough[eid]), 1)
                vals["rough_pct_moon_all"] = round(pct_of_value_in(m_rough, m_rough[tid]), 1)
            if mid == "rover":
                vals["erel_earth"] = float(erel[eid]); vals["erel_moon"] = float(mrel[tid])
                vals["erel_diff"] = abs(float(erel[eid] - mrel[tid]))
                vals["slope_pct_moon_zone"] = round(pct_of_value_in(m_slope[zone_rover], m_slope[tid]), 1)
                vals["slope_pct_earth_passing"] = round(pct_of_value_in(slope[own_pass["rover"]], slope[eid]), 1)
            if mid == "solar":
                ground = float(irr[eid]); above = float(toa_e[eid])
                vals.update({"toa_earth_own": above, "toa_moon": float(m_irr[tid]), "ground_earth": ground,
                             "lost_share_unrounded": 1 - ground / above})
                A = f32_tenths(pcols["atm.toa_kwh_m2_day"][i]); G = f32_tenths(pcols["atm.ground_kwh_m2_day"][i])
                Mm = f32_tenths(pcols["irradiance_toa_kwh_m2_day.moon"][i])
                a10, g10 = int(A * 10), int(G * 10)
                vals.update({"displayed_toa_earth": str(A), "displayed_toa_moon": str(Mm), "displayed_ground": str(G),
                             "loss_pct_display_rule": (200 * (a10 - g10) + a10) // (2 * a10),
                             "toa_earth_bundle": float(pcols["atm.toa_kwh_m2_day"][i]),
                             "slope_pct_moon_zone": round(pct_of_value_in(m_slope[zone_solar], m_slope[tid]), 1),
                             "s_irr": float(own["solar"]["scores"][i][0]), "s_slope": float(own["solar"]["scores"][i][1]),
                             "s_rough": float(own["solar"]["scores"][i][2])})
            if mid == "lunar_base":
                pi = int(np.where(own_pass["lunar_base"] == eid)[0][0])
                zi = int(np.where(zone_base == tid)[0][0])
                vals.update({
                    "tmin_k_earth": float(tmin[eid] + 273.15), "tmin_k_moon": float(m_tmin_k[tid]),
                    "tmin_diff_k": float(tmin[eid] + 273.15 - m_tmin_k[tid]),
                    "tmin_pct_earth_passing": round(float(e_tmin_pct_pass[pi]), 2), "tmin_pct_moon_zone": round(float(m_tmin_pct_zone[zi]), 2),
                    "amp_earth": float(amp[eid]), "amp_moon": float(m_amp[tid]),
                    "amp_pct_earth_passing": round(float(e_amp_pct_pass[pi]), 2), "amp_pct_moon_zone": round(float(m_amp_pct_zone[zi]), 2),
                    "tmin_pct_earth_all_land": round(pct_of_value_in(land_tmin, tmin[eid]), 1),
                    "amp_pct_earth_all_land": round(pct_of_value_in(land_amp, amp[eid]), 1),
                    "tmin_pct_moon_all": round(pct_of_value_in(m_tmin_k, m_tmin_k[tid]), 1),
                    "bundle_pct": {c: float(pcols[c][i]) for c in ["tmin_k.earth_pct", "tmin_k.moon_pct", "lst_diurnal_amp_k.earth_pct", "lst_diurnal_amp_k.moon_pct", "tmin_k.diff"]},
                })
            # bundle pairs columns for the record
            vals["pairs_bin"] = {c: (None if np.isnan(v[i]) else round(float(v[i]), 4)) for c, v in pcols.items()
                                 if not c.startswith("nopair") and c != "list_order"}
            item["values"] = vals
            out.append(item)
        facts[mid] = out

    # population facts for qualitative words
    pb = own_pass["lunar_base"]
    summary["lunar_base_population"] = {
        "earth_passing_tmin_c_median": float(np.median(tmin[pb])), "earth_land_tmin_c_median": float(np.median(land_tmin)),
        "earth_passing_amp_median": float(np.median(amp[pb])), "earth_land_amp_median": float(np.median(land_amp)),
        "earth_passing_amp_pct_in_land_median": round(float(np.median([pct_of_value_in(land_amp, a) for a in amp[pb]])), 1),
        "earth_passing_tmin_pct_in_land_median": round(float(np.median([pct_of_value_in(land_tmin, t) for t in tmin[pb]])), 1),
        "moon_zone_tmin_pct_in_moon_median": round(float(np.median([pct_of_value_in(m_tmin_k, t) for t in m_tmin_k[zone_base]])), 1),
        "paired_tmin_pct_earth": sorted([round(float(e_tmin_pct_pass[np.where(pb == e)[0][0]]), 1) for e in own["lunar_base"]["P"][own["lunar_base"]["twin"] >= 0]])[::45],
    }
    zs = zone_solar
    summary["solar_zone"] = {"median_slope_zone": float(np.nanmedian(m_slope[zs])), "median_slope_moon": float(np.nanmedian(m_slope)),
                             "median_elev_zone": float(np.median(M["elevation_m"].values[zs])),
                             "zone_elev_max_pct_in_moon": round(pct_of_value_in(M["elevation_m"].values, -1200.0), 1),
                             "zone_irr_range": [float(np.nanmin(m_irr[zs])), float(np.nanmax(m_irr[zs]))]}
    summary["rover_zone"] = {"median_slope_zone": float(np.nanmedian(m_slope[zone_rover]))}
    # twins of rover top 5 identical?
    summary["rover_top5_twins"] = sorted({it["moon_id"] for it in facts["rover"]})
    # audio integrity (read only)
    sums = {}
    adir = os.path.join(REPO, "app", "public", "audio")
    for line in open(os.path.join(adir, "SHA256SUMS.txt"), encoding="utf-8"):
        if line.strip():
            h, n = line.split()[:2]
            n = n.lstrip("*")
            sums[n] = hashlib.sha256(open(os.path.join(adir, n), "rb").read()).hexdigest() == h
    summary["audio_sha256_ok"] = sums

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, float) and np.isnan(o):
            return None
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    json.dump(clean(facts), open(os.path.join(OUT, "p4_audio_facts.json"), "w"), indent=1, ensure_ascii=False, sort_keys=True)
    json.dump(clean(summary), open(os.path.join(OUT, "p4_recompute_summary.json"), "w"), indent=1, ensure_ascii=False, sort_keys=True)
    print(json.dumps(clean(summary), indent=1)[:6000])


if __name__ == "__main__":
    main()
