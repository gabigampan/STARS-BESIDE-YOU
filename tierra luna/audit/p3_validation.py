"""p3_validation (point 6): known analog sites and data-defined absurd pairs.

A. Sites of tierra luna/data/benchmark/analog_benchmark.csv whose coordinates are not
   flagged as unverified (rule below), plus the MOBILITY_POSITIVES / MOBILITY_MISMATCHES
   names of rover_preset.py (matched by name in the benchmark, the same way
   rover_preset.validate_rover_ranking does). For each site and mission: its 1-degree
   cell, whether it passes the funnel, its twin, similarity, final, rank and rank
   percentile among the ranked points; also the best similarity over the zone ignoring
   the pair filter (diagnostic only).
   Unverified-coordinate rule: coord_quality contains 'from memory', or source_status
   starts with 'FROM MEMORY', or source_status says the location is from memory.
B. Absurd pairs defined from the data, compared with the real pairs:
   B1 every ranked Earth point against the zone cell at the far end of each key variable
      (the zone cell with the largest |difference| on that key);
   B2 random Earth-Moon pairs: random passing Earth points against random cells of the
      WHOLE Moon (20,000 pairs, seed fixed; for percentile variables the lunar percentile
      is taken within the whole Moon);
   B3 the steepest 1 % of Earth land cells (slope) against the flattest zone cell;
   B4 Solar panels: Earth land cells poleward of the polar circles (polar night) against
      their best zone cell (filter applied) and against the median zone cell.
Output: out/p3_validation.json. Run: python p3_validation.py"""
import csv
import os
import re
import sys

import numpy as np
import pandas as pd

from p3_common import (MISSIONS, TL, dump, funnel, load_params, load_tables, lunar_base_zone_ids, midrank_pct,
                       rule_arrays, run_mission, sim_values, zone_ids)

sys.path.insert(0, TL)


def unverified(r):
    cq = (r["coord_quality"] or "").lower()
    ss = (r["source_status"] or "")
    return ("from memory" in cq or ss.upper().startswith("FROM MEMORY")
            or bool(re.search(r"location[^;)]*from memory", ss, re.I)))


def cell_id(lat, lon):
    row = int(np.floor(90.0 - lat))
    col = int(np.floor(lon + 180.0))
    return min(row, 179) * 360 + min(col, 359)


def pair_eval(e, mz, roles, w, tau, bound):
    """Similarity (unrounded scores) and filter of Earth rows e (n x k) against Moon rows mz (n x k)."""
    d = np.abs(e - mz)
    fin = np.isfinite(d)
    key = np.array([r == "key" for r in roles])
    ok = np.all(np.where(key, fin & (np.where(fin, d, np.inf) <= bound), True), axis=1) & \
        np.all(np.where(~key, ~fin | (np.where(fin, d, np.inf) <= bound), True), axis=1)
    s = np.exp(-0.5 * (np.where(fin, d, 0) / tau) ** 2)
    wq = np.where(fin, w, 0)
    return 100 * (wq * s).sum(1) / wq.sum(1), ok


def dist(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if not x.size:
        return {"n": 0}
    return {"n": int(x.size), "min": round(float(x.min()), 2), "q05": round(float(np.quantile(x, .05)), 2),
            "q25": round(float(np.quantile(x, .25)), 2), "median": round(float(np.median(x)), 2),
            "q75": round(float(np.quantile(x, .75)), 2), "q95": round(float(np.quantile(x, .95)), 2),
            "max": round(float(x.max()), 2)}


def main():
    P = load_params()
    T = load_tables(P)
    E, Mo = T["EARTH"], T["MOON"]
    lbz = lunar_base_zone_ids()
    SV = sim_values(T, P)
    import rover_preset as rp   # only the two name lists are read
    rows = list(csv.DictReader(open(os.path.join(TL, "data", "benchmark", "analog_benchmark.csv"), encoding="utf-8")))
    used = [r for r in rows if not unverified(r)]
    excluded = [f"{r['id']} {r['name']}" for r in rows if unverified(r)]
    res = {"excluded_unverified": excluded, "used": len(used), "sites": [], "missions": {}}
    results = {m: run_mission(T, m, P, lbz, SV).set_index("id") for m in MISSIONS}
    eid = E["id"].to_numpy()
    for m in MISSIONS:
        r = results[m]
        N = int((r["rank"] > 0).sum())
        names, roles, w, tau, bound, scales, _, _ = rule_arrays(m, P)
        zids = zone_ids(Mo, m, P, lbz)
        zpos = np.searchsorted(Mo["id"].to_numpy(), zids)
        passE = funnel(E, "EARTH", m, P)
        pi = np.flatnonzero(passE)
        ev = np.column_stack([SV[v]["EARTH"] for v in names])     # all Earth cells
        mv = np.column_stack([SV[v]["MOON"][zpos] for v in names])
        evc = ev.copy()
        for q, sc in enumerate(scales):
            if sc == "percentile_within_population":
                pop = np.sort(ev[pi, q][np.isfinite(ev[pi, q])])
                # percentile of ANY Earth value placed in the passing population (mid-rank)
                lo = np.searchsorted(pop, ev[:, q], "left")
                hi = np.searchsorted(pop, ev[:, q], "right")
                evc[:, q] = np.where(np.isfinite(ev[:, q]), 100 * ((lo + hi) / 2) / len(pop), np.nan)
                evc[pi, q] = midrank_pct(ev[pi, q])
                mv[:, q] = midrank_pct(mv[:, q])
        # ---- A. sites
        for s in used:
            c = cell_id(float(s["lat"]), float(s["lon"]))
            i = int(np.searchsorted(eid, c))
            entry = {"mission": m, "site": s["id"], "name": s["name"], "cell": f"E{c}",
                     "analog_type": s["analog_type"], "benchmark_role": s["benchmark_role"],
                     "land": bool(np.isfinite(SV["slope_deg"]["EARTH"][i]) or pd.notna(E.loc[i, "elevation_m"])),
                     "passes_funnel": bool(passE[i])}
            if c in r.index:
                x = r.loc[c]
                entry.update({"twin": int(x["twin"]), "similarity": None if not np.isfinite(x["similarity"]) else round(float(x["similarity"]), 2),
                              "suitability": round(float(x["suitability"]), 2),
                              "final": None if not np.isfinite(x["final"]) else round(float(x["final_pub"]), 2),
                              "rank": int(x["rank"]), "rank_pct_top": None if x["rank"] <= 0 else round(100 * (x["rank"] - 0.5) / N, 1)})
            sv, ok = pair_eval(np.repeat(evc[i][None, :], len(zids), 0), mv, roles, w, tau, bound)
            if np.isfinite(sv).any():
                entry["best_sim_ignoring_filter"] = round(float(np.nanmax(sv)), 2)
                entry["zone_cells_passing_filter"] = int(ok.sum())
            res["sites"].append(entry)
        # ---- B. absurd pairs
        rk = r[r["rank"] > 0]
        rpos = np.searchsorted(eid, rk.index.to_numpy())
        B = {"real_pairs_similarity_all_ranked": dist(rk["similarity"]),
             "real_pairs_similarity_top50": dist(rk.sort_values("rank").head(50)["similarity"])}
        for q, v in enumerate(names):
            if roles[q] != "key":
                continue
            far = np.nanargmax(np.abs(evc[rpos, q][:, None] - mv[None, :, q]), axis=1)
            sv, ok = pair_eval(evc[rpos], mv[far], roles, w, tau, bound)
            B[f"B1_far_end_of_{v}"] = {"similarity": dist(sv), "filter_rejects_share": round(float(1 - ok.mean()), 4)}
        rng = np.random.default_rng(20261115)
        a = rng.choice(pi, 20000)
        b = rng.integers(0, len(Mo), 20000)
        mall = np.column_stack([SV[v]["MOON"] for v in names])
        for q, sc in enumerate(scales):
            if sc == "percentile_within_population":
                mall[:, q] = midrank_pct(mall[:, q])
        sv, ok = pair_eval(evc[a], mall[b], roles, w, tau, bound)
        B["B2_random_whole_moon"] = {"similarity": dist(sv), "filter_rejects_share": round(float(1 - ok.mean()), 4),
                                     "similarity_of_filter_passing": dist(sv[ok]), "n_passing": int(ok.sum())}
        if "slope_deg" in names:
            qs = names.index("slope_deg")
            sl = SV["slope_deg"]["EARTH"]
            thr = np.nanquantile(sl, 0.99)
            steep = np.flatnonzero(sl >= thr)
            flat = int(np.nanargmin(mv[:, qs]))
            sv, ok = pair_eval(evc[steep], np.repeat(mv[flat][None, :], len(steep), 0), roles, w, tau, bound)
            B["B3_steepest_1pct_vs_flattest_zone_cell"] = {"earth_slope_threshold_deg": round(float(thr), 2),
                                                          "zone_cell": int(zids[flat]), "zone_cell_slope": round(float(mv[flat, qs]), 3),
                                                          "similarity": dist(sv), "filter_rejects_share": round(float(1 - ok.mean()), 4),
                                                          "steep_cells_passing_funnel": int(passE[steep].sum())}
        if m == "solar":
            lat = E["lat"].to_numpy()
            polar = np.flatnonzero((np.abs(lat) > 66.56) & np.isfinite(SV["slope_deg"]["EARTH"]))
            best, okb, med = [], [], []
            for i in polar:
                sv, ok = pair_eval(np.repeat(evc[i][None, :], len(zids), 0), mv, roles, w, tau, bound)
                best.append(np.nanmax(np.where(ok, sv, np.nan)) if ok.any() else np.nan)
                okb.append(ok.any())
                med.append(np.nanmedian(sv))
            B["B4_polar_night_cells"] = {"cells": int(len(polar)), "passing_funnel": int(passE[polar].sum()),
                                         "toa_range": [round(float(np.nanmin(SV['irradiance_toa_kwh_m2_day']['EARTH'][polar])), 2),
                                                       round(float(np.nanmax(SV['irradiance_toa_kwh_m2_day']['EARTH'][polar])), 2)],
                                         "zone_moon_irradiance_range": [round(float(np.nanmin(mv[:, 0])), 2), round(float(np.nanmax(mv[:, 0])), 2)],
                                         "any_zone_cell_passes_filter": int(np.sum(okb)),
                                         "best_filtered_similarity": dist(best), "median_unfiltered_similarity": dist(med)}
        res["missions"][m] = {"ranked": N, "absurd": B}
        print(m, {k: (v.get("similarity", v) if isinstance(v, dict) else v) for k, v in B.items()})
    # rover_preset names
    def find(name):
        key = name.lower().replace("-", " ")
        return [s for s in rows if key in s["name"].lower().replace("-", " ")]
    rp_out = {}
    for grp, names_ in (("positives", rp.MOBILITY_POSITIVES), ("mismatches", rp.MOBILITY_MISMATCHES)):
        for n_ in names_:
            hits = find(n_)
            rp_out[f"{grp}:{n_}"] = [{"id": h["id"], "unverified": unverified(h)} for h in hits]
    res["rover_preset_names"] = rp_out
    print(dump("p3_validation.json", res))


if __name__ == "__main__":
    main()
