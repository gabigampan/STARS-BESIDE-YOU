"""p3_montecarlo (point F): propagate input uncertainty to the ranking.

Usage: python p3_montecarlo.py MISSION [RUNS] [SIGMA_FACTOR] [SEED] [SUBSET]
  defaults: RUNS 200, SIGMA_FACTOR 1.0, SEED 20261115, SUBSET all.
  SUBSET (decomposition runs): 'only:BODY:col,BODY:col' perturbs only those entries,
  'except:BODY:col,...' all but those (keys as in SIGMA, e.g. EARTH:irradiance_kwh_m2_day).

Each run adds independent Gaussian noise per cell to the input columns (table below),
then recomputes from scratch with p3_common: derived variables (relative elevation with
its body mean, percentiles within the perturbed populations), funnel, suitability,
twins, similarity, final and rank. Deterministic for a given seed.

SIGMA (1 sigma, multiplied by SIGMA_FACTOR). 'doc' = from the product documentation
(cited in docs/stats_audit/3_robustez_validacion_ranking.md, section F.3); 'illustrative'
= no per-cell figure could be established, stated value labelled as such.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

from p3_common import (OUT, audio_pairs, funnel, load_params, load_tables, lunar_base_zone_ids, num, run_mission,
                       sim_values)

SIGMA = {
    # body, column(s): (kind, value, label)
    ("EARTH", "elevation_m"): ("abs", 7.17, "doc: ETOPO 2022 global RMSE vs ICESat-2 (MacFerrin et al. 2025)"),
    ("EARTH", "slope"): ("rel", 0.05, "illustrative 5 % (no per-cell slope accuracy documented)"),
    ("EARTH", "rough"): ("rel", 0.05, "illustrative 5 % (no per-cell roughness accuracy documented)"),
    ("EARTH", "tmin_c"): ("abs", 1.39, "doc: WorldClim 2 cross-validation RMSE of minimum temperature (Fick & Hijmans 2017, Table 3)"),
    ("EARTH", "irradiance_kwh_m2_day"): ("abs", 1.45 / 3.6, "doc: WorldClim 2 cross-validation RMSE of solar radiation 1.45 MJ/m2/day = 0.403 kWh/m2/day"),
    ("EARTH", "lst_diurnal_amp_k"): ("abs", 2 ** 0.5, "doc-derived: MOD11 QC best class 'average LST error <= 1K' per overpass, day minus night -> sqrt(2) K"),
    ("EARTH", "rock_or_bare_frac"): ("abs", 0.05, "illustrative 0.05 (classification product; per-cell error not documented)"),
    ("MOON", "elevation_m"): ("abs", 10.0, "doc: LOLA geodetic grid ~10 m radial accuracy (Smith et al. 2010)"),
    ("MOON", "slope"): ("rel", 0.05, "illustrative 5 %"),
    ("MOON", "rough"): ("rel", 0.05, "illustrative 5 %"),
    ("MOON", "tmin_c"): ("abs", 1.0, "doc: Diviner NETD < 1 K over 60-120 K (Hayne et al. 2017, citing Paige et al. 2010)"),
    ("MOON", "lst_diurnal_amp_k"): ("abs", 2 ** 0.5, "doc-derived: max minus min, each with 1 K -> sqrt(2) K"),
    ("MOON", "irradiance_kwh_m2_day"): ("rel", 0.02, "illustrative 2 % (geometry formula plus LOLA illumination fraction)"),
}
NOT_PERTURBED = {
    "Earth irradiance_toa (formula)": "same S0 = 1361 W/m2 on both bodies; geometry exact (own integration matches to 6e-6)",
    "sun_elev_max_deg, sun_low_frac_0_5deg": "formulas of latitude, exact",
    "thermal_inertia_class, permafrost_class, mask_fraction": "categories / land share, not perturbed",
}


def perturb(T, rng, f, subset=None):
    out = {}
    for body, df in T.items():
        d = df.copy()
        n = len(d)
        for (b, c), (kind, val, _) in SIGMA.items():
            if b != body:
                continue
            if subset is not None and f"{b}:{c}" not in subset:
                continue
            cols = {"slope": ["slope_deg", "slope_300m_deg"], "rough": ["roughness_m", "rough_300m_m"]}.get(c, [c])
            e = rng.standard_normal(n) * val * f
            for col in cols:     # aliased columns of one source get the same draw
                v = num(d, col)
                v = v * (1 + e) if kind == "rel" else v + e
                if col == "rock_or_bare_frac":
                    v = np.clip(v, 0, 1)
                d[col] = v
        out[body] = d
    return out


def main():
    m = sys.argv[1]
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    f = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 20261115
    sub_arg = sys.argv[5] if len(sys.argv) > 5 else "all"
    subset = None
    if sub_arg != "all":
        mode, keys = sub_arg.split(":", 1)
        keys = set(keys.split(","))
        allk = {f"{b}:{c}" for (b, c) in SIGMA}
        subset = keys if mode == "only" else allk - keys
    P = load_params()
    T = load_tables(P)
    lbz = lunar_base_zone_ids()
    toa = sim_values(T, P)["irradiance_toa_kwh_m2_day"]["EARTH"]
    base = run_mission(T, m, P, lbz).set_index("id")
    pairs = [p for p in audio_pairs() if p["mission"] == m]
    ids = [p["earth_id"] for p in pairs]
    rng = np.random.default_rng(seed + {"rover": 0, "solar": 1, "lunar_base": 2}[m] + int(f * 1000))
    rec = {"rank": [], "twin": [], "top5": [], "n_ranked": [], "n_pass": []}
    tag = f"{m}_f{f:g}" + ("" if sub_arg == "all" else "_" + sub_arg.replace(":", "-").replace(",", "+"))
    t0 = time.time()
    for k in range(runs):
        Tp = perturb(T, rng, f, subset)
        SV = sim_values(Tp, P, toa=toa)
        r = run_mission(Tp, m, P, lbz, SV).set_index("id")
        rr = [int(r.loc[i, "rank"]) if i in r.index and r.loc[i, "rank"] > 0 else 0 for i in ids]
        tw = [int(r.loc[i, "twin"]) if i in r.index else -2 for i in ids]   # -2: fails the funnel, -1: no twin
        rec["rank"].append(rr)
        rec["twin"].append(tw)
        rec["top5"].append([int(x) for x in r[(r["rank"] >= 1) & (r["rank"] <= 5)].sort_values("rank").index])
        rec["n_ranked"].append(int((r["rank"] > 0).sum()))
        rec["n_pass"].append(int(len(r)))
        if (k + 1) % 10 == 0 or k + 1 == runs:
            print(tag, k + 1, round(time.time() - t0), flush=True)
            json.dump({"mission": m, "runs_done": k + 1, "sigma_factor": f, "subset": sub_arg, "seed": seed, "ids": ids,
                       "audio": pairs, "baseline_top5": [int(x) for x in base[(base["rank"] >= 1) & (base["rank"] <= 5)]
                                                         .sort_values("rank").index],
                       "baseline_ranked": int((base["rank"] > 0).sum()), "sigma": {f"{b}:{c}": v for (b, c), v in SIGMA.items()},
                       "not_perturbed": NOT_PERTURBED, **rec},
                      open(os.path.join(OUT, f"p3_mc_{tag}.json"), "w"), indent=0)


if __name__ == "__main__":
    main()
