"""Re-audit Solar panels, item 6: Monte Carlo of input uncertainty on one criteria set.

    python -I ra_solar_montecarlo.py <criteria set> [runs=200] [seed=20261115] [procs=4] [sigma_isccp=0.05]

Each run adds independent Gaussian noise per cell to the input columns (sigmas of the first audit,
audit/p3_montecarlo.py SIGMA, with their sources; plus clear_frac_isccp), recomputes the derived values,
funnel, suitability, twins, similarity, final, rank and the five by the set's shipped rule
(independent code path ra_solar_common / p5_common). The baseline five is the unperturbed one.
clear_frac_isccp sigma: ILLUSTRATIVE (no per-cell uncertainty of the 5-year mean ISCCP-H cloud
amount found in the product documentation in this session), stated value 0.05 absolute, clipped to [0, 1].
bad/good of the new criterion stay at the configured 0.308/0.671 in every run (configuration numbers).
Writes out/ra_solar_mc_<set>.json.
"""
import copy
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_solar_common as R  # noqa: E402
import p5_common as C  # noqa: E402

SIGMA = {
    ("EARTH", "elevation_m"): ("abs", 7.17, "doc: ETOPO 2022 global RMSE vs ICESat-2 (first audit p3_montecarlo)"),
    ("EARTH", "slope_deg"): ("rel", 0.05, "illustrative 5 % (first audit)"),
    ("EARTH", "roughness_m"): ("rel", 0.05, "illustrative 5 % (first audit)"),
    ("EARTH", "irradiance_kwh_m2_day"): ("abs", 1.45 / 3.6, "doc: WorldClim 2 CV RMSE 1.45 MJ/m2/day (Fick & Hijmans 2017)"),
    ("EARTH", "lst_diurnal_amp_k"): ("abs", 2 ** 0.5, "doc-derived: MOD11 <= 1 K per overpass, day-night -> sqrt(2) K"),
    ("EARTH", "clear_frac_isccp"): ("abs", None, "ILLUSTRATIVE (this re-audit): no documented per-cell uncertainty of the 2012-2016 mean found"),
    ("MOON", "elevation_m"): ("abs", 10.0, "doc: LOLA ~10 m radial (Smith et al. 2010)"),
    ("MOON", "slope_deg"): ("rel", 0.05, "illustrative 5 % (first audit)"),
    ("MOON", "roughness_m"): ("rel", 0.05, "illustrative 5 % (first audit)"),
    ("MOON", "irradiance_kwh_m2_day"): ("rel", 0.02, "illustrative 2 % (first audit)"),
    ("MOON", "lst_diurnal_amp_k"): ("abs", 2 ** 0.5, "doc-derived (first audit)"),
}
G = {}


def _init(set_name, sig_isccp):
    P, _, _, _ = R.load_params_set(set_name)
    T, D = R.tables(P)
    G.update(P=P, T=T, D=D, sig=sig_isccp)


def perturb(T, rng, sig_isccp):
    out = {}
    for body, df in T.items():
        d = df.copy()
        n = len(d)
        for (b, c), (kind, val, _) in SIGMA.items():
            if b != body or c not in d:
                continue
            val = sig_isccp if val is None else val
            e = rng.standard_normal(n) * val
            v = pd.to_numeric(d[c], errors="coerce").to_numpy(float)
            v = v * (1 + e) if kind == "rel" else v + e
            if c == "clear_frac_isccp":
                v = np.clip(v, 0, 1)
            if c in ("slope_deg", "roughness_m"):
                v = np.maximum(v, 0)
            d[c] = v
        out[body] = d
    return out


def one(seed):
    P, T, D0 = G["P"], G["T"], G["D"]
    rng = np.random.default_rng(seed)
    Tp = perturb(T, rng, G["sig"])
    D = C.derived(Tp, P)
    D["irradiance_toa_kwh_m2_day"]["EARTH"] = D0["irradiance_toa_kwh_m2_day"]["EARTH"]  # exact formula, not perturbed
    r = C.run_mission(Tp, D, "solar", P)
    _T_saved = R._T.get("T")
    R._T["T"] = Tp   # five() reads the table for the skip columns (unperturbed columns) and coordinates
    k5 = R.five(r, P)
    R._T["T"] = _T_saved
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    o = o[r["rank"][o] > 0]
    top50 = [int(r["pass_ids"][q]) for q in o[:50]]
    fifth = float(r["final_pub"][k5[-1]])
    fp = r["final_pub"][np.isfinite(r["final_pub"])]
    return {"seed": seed, "five": [int(r["pass_ids"][q]) for q in k5], "five_twins": [int(r["twin"][q]) for q in k5],
            "rank_of": None, "top50": top50,
            "twin_of": {int(i): int(t) for i, t in zip(r["pass_ids"], r["twin"])},
            "rank_map": {int(i): int(k) for i, k in zip(r["pass_ids"], r["rank"])},
            "near_fifth": {str(t): int(np.sum(np.abs(fp - fifth) <= t)) - 1 for t in (0.1, 0.5, 1.0)},
            "n_pass": int(r["passed"].sum()), "n_paired": int((r["twin"] >= 0).sum())}


def main():
    set_name = sys.argv[1]
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    seed0 = int(sys.argv[3]) if len(sys.argv) > 3 else 20261115
    procs = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    sig = float(sys.argv[5]) if len(sys.argv) > 5 else 0.05
    _init(set_name, sig)
    P, T, D = G["P"], G["T"], G["D"]
    r0 = C.run_mission(T, D, "solar", P)
    k5 = R.five(r0, P)
    base5 = [int(r0["pass_ids"][q]) for q in k5]
    base_tw = {int(r0["pass_ids"][q]): int(r0["twin"][q]) for q in k5}
    fp = r0["final_pub"][np.isfinite(r0["final_pub"])]
    fifth = float(r0["final_pub"][k5[-1]])
    base_near = {str(t): int(np.sum(np.abs(fp - fifth) <= t)) - 1 for t in (0.1, 0.5, 1.0)}
    t0 = time.time()
    seeds = [seed0 + k for k in range(runs)]
    with Pool(procs, initializer=_init, initargs=(set_name, sig)) as pool:
        res = []
        for k, x in enumerate(pool.imap(one, seeds)):
            res.append(x)
            if (k + 1) % 20 == 0:
                print(set_name, k + 1, round(time.time() - t0), flush=True)
    per = {}
    for e in base5:
        in5 = sum(e in x["five"] for x in res)
        r20 = sum(0 < x["rank_map"].get(e, 0) <= 20 for x in res)
        r50 = sum(0 < x["rank_map"].get(e, 0) <= 50 for x in res)
        tw = sum(x["twin_of"].get(e, -2) == base_tw[e] for x in res)
        in5tw = sum(e in x["five"] and x["twin_of"].get(e) == base_tw[e] for x in res)
        ranks = [x["rank_map"].get(e, 0) for x in res]
        per["E%d" % e] = {"baseline_twin": "M%d" % base_tw[e], "share_in_five": round(in5 / runs, 3), "share_top20": round(r20 / runs, 3),
                          "share_top50": round(r50 / runs, 3), "share_keeps_twin": round(tw / runs, 3),
                          "share_in_five_and_keeps_twin": round(in5tw / runs, 3),
                          "median_rank": float(np.median([q if q > 0 else 10 ** 6 for q in ranks]))}
    exact = sum(x["five"] == base5 for x in res)
    same_set = sum(set(x["five"]) == set(base5) for x in res)
    near = {t: {"median": float(np.median([x["near_fifth"][t] for x in res])), "p10": float(np.percentile([x["near_fifth"][t] for x in res], 10)),
                "p90": float(np.percentile([x["near_fifth"][t] for x in res], 90))} for t in ("0.1", "0.5", "1.0")}
    from collections import Counter
    cnt = Counter(e for x in res for e in x["five"])
    out = {"criteria_set": set_name, "runs": runs, "seed0": seed0, "sigma_isccp_illustrative": sig,
           "sigma": {"%s:%s" % k: [v[0], sig if v[1] is None else v[1], v[2]] for k, v in SIGMA.items()},
           "not_perturbed": {"Earth irradiance_toa": "exact formula", "sun_elev_max_deg, sun_low_frac_0_5deg": "formulas of latitude",
                             "snow_ice_frac, mask_fraction, thermal_inertia_class": "classes / land share (also the skip columns of the five)"},
           "baseline_five": ["E%d" % e for e in base5], "baseline_points_within_of_fifth": base_near, "per_analog": per,
           "five_exact_same_order": round(exact / runs, 3), "five_same_set": round(same_set / runs, 3),
           "points_within_of_fifth_runs": near, "most_frequent_in_five": [("E%d" % e, round(c / runs, 3)) for e, c in cnt.most_common(12)],
           "n_pass_range": [min(x["n_pass"] for x in res), max(x["n_pass"] for x in res)],
           "n_paired_range": [min(x["n_paired"] for x in res), max(x["n_paired"] for x in res)], "seconds": round(time.time() - t0)}
    p = R.jdump(out, "ra_solar_mc_%s.json" % set_name)
    print(json.dumps({k: v for k, v in out.items() if k not in ("sigma",)}, indent=1))
    print("wrote", p)


if __name__ == "__main__":
    main()
