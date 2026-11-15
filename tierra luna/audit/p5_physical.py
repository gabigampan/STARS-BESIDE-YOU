"""Point D (reviewer 5): does each variable do real work in its mission?

For every mission, from the auditor's own run (p5_common, equal to the bundle):
  * suitability variables: share of funnel points with the utility at 0 and at 1 (saturation),
    Spearman correlation of the utility with |latitude| and with the other utilities, and the share
    of the suitability spread (variance of weight x utility / variance of the weighted sum, a
    simple decomposition) each one carries;
  * similarity variables: over the paired points, the distribution of |difference| / tolerance,
    the share of pairs whose score is >= 0.999 (saturated), the share of the similarity spread
    each one carries, and the value range on each body (funnel points / zone cells);
  * categorical classes present among the funnel points.
Run: <python> "tierra luna/audit/p5_physical.py"  -> out/p5_physical.json
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p5_common import MISSIONS, OUT, derived, load_params, load_tables, run_mission, zone_mask  # noqa: E402


def q(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    if not len(a):
        return None
    return {k: round(float(v), 4) for k, v in zip(("min", "p10", "median", "p90", "max"), np.percentile(a, [0, 10, 50, 90, 100]))} | {"n": int(len(a))}


def share_of_spread(parts):
    tot = np.nansum(np.column_stack(parts), axis=1)
    vt = np.nanvar(tot)
    return [round(float(np.nanvar(p) / vt), 3) if vt > 0 else None for p in parts]


def main():
    P = load_params()
    T = load_tables(P)
    D = derived(T, P)
    E, M = T["EARTH"], T["MOON"]
    rep = {}
    for m in MISSIONS:
        r = run_mission(T, D, m, P)
        pi = np.flatnonzero(r["passed"])
        lat = np.abs(E["lat"].to_numpy(float)[pi])
        soft = P["missions"][m]["soft"]
        sr = {}
        wsum = sum(float(s["weight"]) for s in soft.values())
        parts = []
        for v, s in soft.items():
            u = r["utils"][v]
            ok = np.isfinite(u)
            d = {"weight": s["weight"], "n_with_value": int(ok.sum()), "n_funnel": int(len(u)),
                 "share_u0": round(float((u[ok] <= 1e-9).mean()), 4), "share_u1": round(float((u[ok] >= 1 - 1e-9).mean()), 4),
                 "utility": q(u), "spearman_with_abs_lat": round(float(spearmanr(u[ok], lat[ok]).correlation), 3) if ok.sum() > 2 and np.nanstd(u[ok]) > 0 else None}
            if "map" in s:
                d["classes"] = E[v].iloc[pi].astype(str).value_counts().to_dict()
            else:
                d["raw"] = q(pd.to_numeric(E[v].iloc[pi], errors="coerce"))
            sr[v] = d
            parts.append(float(s["weight"]) / wsum * np.where(ok, u, np.nan))
        for (v, d), sh in zip(sr.items(), share_of_spread(parts)):
            d["share_of_suitability_spread"] = sh
        names = list(soft)
        cm = {}
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                x, y = r["utils"][a], r["utils"][b]
                ok = np.isfinite(x) & np.isfinite(y)
                if ok.sum() > 2 and np.std(x[ok]) > 0 and np.std(y[ok]) > 0:
                    cm[f"{a}~{b}"] = round(float(spearmanr(x[ok], y[ok]).correlation), 3)
        has = r["twin"] >= 0
        sim_vars = P["missions"][m]["sim"]["variables"]
        sv = {}
        sparts = []
        wtot = sum(float(x["weight"]) for x in sim_vars)
        zone = zone_mask(M, m, P)
        for qn, x in enumerate(sim_vars):
            v = x["variable"]
            ratio = r["diff"][has, qn] / float(x["tolerance"])
            sc = r["scores"][has, qn]
            sv[v] = {"role": x["role"], "weight": x["weight"], "tolerance": x["tolerance"],
                     "diff_over_tol": q(ratio), "share_score_ge_0.999": round(float(np.nanmean(sc >= 0.999)), 4),
                     "share_score_eq_1": round(float(np.nanmean(sc >= 1.0)), 4),
                     "earth_funnel_values": q(r["ev"][:, qn]), "moon_zone_values": q(D[v]["MOON"][zone]) if x.get("scale", "real") == "real" else "percentiles",
                     "earth_real_values_if_percentile": q(D[v]["EARTH"][pi]) if x.get("scale") == "percentile_within_population" else None,
                     "moon_real_values_if_percentile": q(D[v]["MOON"][zone]) if x.get("scale") == "percentile_within_population" else None}
            sparts.append(float(x["weight"]) / wtot * sc)
        for (v, d), sh in zip(sv.items(), share_of_spread(sparts)):
            d["share_of_similarity_spread"] = sh
        o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")[:5]
        top5 = []
        for i in o:
            top5.append({"rank": int(r["rank"][i]), "earth": int(r["pass_ids"][i]), "moon": int(r["twin"][i]),
                         "suitability": round(float(r["suit"][i]), 2), "similarity": round(float(r["sim"][i]), 2),
                         "scores": {x["variable"]: round(float(r["scores"][i, k]), 6) for k, x in enumerate(sim_vars)},
                         "diff": {x["variable"]: round(float(r["diff"][i, k]), 4) for k, x in enumerate(sim_vars)},
                         "utilities": {v: (round(float(r["utils"][v][i]), 4) if np.isfinite(r["utils"][v][i]) else None) for v in soft}})
        rep[m] = {"funnel": int(len(pi)), "paired": int(has.sum()), "distinct_twins": int(len(set(r["twin"][has].tolist()))),
                  "suitability_variables": sr, "utility_spearman": cm, "similarity_variables": sv, "top5": top5,
                  "similarity_of_pairs": q(r["sim"][has]), "share_similarity_ge_99.99": round(float(np.nanmean(r["sim"][has] >= 99.99)), 4)}
        print(m, "done", flush=True)
    json.dump(rep, open(os.path.join(OUT, "p5_physical.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
