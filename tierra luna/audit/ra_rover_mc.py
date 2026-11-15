"""ra_rover_mc (item 6): Monte Carlo of the Rover ranking under the documented input uncertainty, own code path.

    python ra_rover_mc.py CRITERIA [RUNS] [SEED] [SIGMA_SET] [WORKERS]
      CRITERIA  corrected | audited_morning
      RUNS      default 200;  SEED default 20261115;  WORKERS default 4
      SIGMA_SET first_audit (default) | s1_pixel

Run k draws its noise from default_rng([SEED, k]) (common random numbers: both criteria sets see the same
perturbations). Each run perturbs the input columns, recomputes everything (funnel, suitability, relative elevation
with its body mean, twins, similarity, final, rank) with ra_rover_common, and records for the five of the
unperturbed model: rank, published final, in the five shown (rule of the set), in the top 20 / 50, in the tied top
group, twin kept; and the five shown, the size of the top tie, the counts within 0.1/0.5/1 final points of the
fifth shown.

SIGMA sets (1 sigma):
 first_audit = audit/p3_montecarlo.py (docs/stats_audit/3_robustez_validacion_ranking.md F.3):
   EARTH elevation_m 7.17 m abs (doc: ETOPO 2022 RMSE, MacFerrin et al. 2025); EARTH slope, roughness 5 % rel
   (illustrative); EARTH rock_or_bare_frac 0.05 abs (illustrative); MOON elevation_m 10 m abs (doc: LOLA,
   Smith et al. 2010); MOON slope, roughness 5 % rel (illustrative).
 s1_pixel = as first_audit but slope and roughness with the per-pixel figures of research 5 (ILLUSTRATIVE upper
   bound: per-pixel error applied to a whole cell): slope EARTH 0.1567 deg, MOON 0.2138 deg abs; roughness EARTH
   10.140 m, MOON 14.142 m abs.
Writes out/ra_rover_mc_<criteria>_<sigma set>.json.
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np

import ra_rover_common as R

CRIT = sys.argv[1]
RUNS = int(sys.argv[2]) if len(sys.argv) > 2 else 200
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 20261115
SSET = sys.argv[4] if len(sys.argv) > 4 else "first_audit"
WORKERS = int(sys.argv[5]) if len(sys.argv) > 5 else 4

SIGMAS = {
    "first_audit": {("EARTH", "elevation_m"): ("abs", 7.17), ("EARTH", "slope"): ("rel", 0.05), ("EARTH", "rough"): ("rel", 0.05),
                    ("EARTH", "rock_or_bare_frac"): ("abs", 0.05), ("MOON", "elevation_m"): ("abs", 10.0),
                    ("MOON", "slope"): ("rel", 0.05), ("MOON", "rough"): ("rel", 0.05)},
}
SIGMAS["s1_pixel"] = dict(SIGMAS["first_audit"])
SIGMAS["s1_pixel"].update({("EARTH", "slope"): ("abs", float(np.degrees(7.17 / (np.sqrt(2) * 1853.0)))),
                           ("MOON", "slope"): ("abs", float(np.degrees(10.0 / (np.sqrt(2) * 1895.2)))),
                           ("EARTH", "rough"): ("abs", float(np.sqrt(2) * 7.17)), ("MOON", "rough"): ("abs", float(np.sqrt(2) * 10.0))})
ALIASES = {"slope": ["slope_deg", "slope_300m_deg"], "rough": ["roughness_m", "rough_300m_m"]}

P = R.params(CRIT)
T0 = R.tables(P)
D0 = R.derived_rover(T0, P)
r0 = R.run(T0, D0, P)
F0, _ = R.five(r0, P)
IDS = [int(r0["ids"][k]) for k in F0]
TW0 = [int(r0["twin"][k]) for k in F0]
_top0 = np.nanmax(r0["final_pub"])
_bad0 = R._skipped(r0, P["rover_top5"]) if P["rover_top5"]["rule"] in ("spread_within_top_tie", "rank_with_skips") else np.zeros(len(r0["ids"]), bool)
TIED0 = set(map(int, r0["ids"][r0["final_pub"] == _top0]))
TIED0_EL = set(map(int, r0["ids"][(r0["final_pub"] == _top0) & ~_bad0]))


def perturb(k):
    rng = np.random.default_rng([SEED, k])
    T = {}
    for body in ("EARTH", "MOON"):
        d = T0[body].copy()
        n = len(d)
        for (b, c), (kind, val) in SIGMAS[SSET].items():   # fixed order: same draws for both criteria sets
            e = rng.standard_normal(n) * val
            if b != body:
                continue
            for col in ALIASES.get(c, [c]):
                v = np.asarray(d[col], dtype=float) if col in d else None
                if v is None:
                    continue
                v = v * (1 + e) if kind == "rel" else v + e
                if col == "rock_or_bare_frac":
                    v = np.clip(v, 0, 1)
                d[col] = v
        T[body] = d
    return T


def one(k):
    T = perturb(k)
    D = R.derived_rover(T, P)
    r = R.run(T, D, P)
    f, info = R.five(r, P)
    five_ids = [int(r["ids"][j]) for j in f]
    pos = {int(i): j for j, i in enumerate(r["ids"])}
    top = np.nanmax(r["final_pub"])
    fifth_final = float(r["final_pub"][f[-1]]) if f else np.nan
    ok = r["rank"] > 0
    fp = r["final_pub"][ok]
    rec = {"k": k, "five": five_ids, "n_tied_top": int((fp == top).sum()), "top": float(top), "fifth_final": fifth_final,
           "within_0_1": int((fp >= fifth_final - 0.1).sum()), "within_0_5": int((fp >= fifth_final - 0.5).sum()),
           "within_1": int((fp >= fifth_final - 1.0).sum()), "n_ranked": int(ok.sum()), "n_pass": int(len(r["ids"])),
           "analogs": []}
    badr = R._skipped(r, P["rover_top5"]) if P["rover_top5"]["rule"] in ("spread_within_top_tie", "rank_with_skips") else np.zeros(len(r["ids"]), bool)
    tied = set(map(int, r["ids"][r["final_pub"] == top])); tied_el = set(map(int, r["ids"][(r["final_pub"] == top) & ~badr]))
    rec["tied_n"] = len(tied); rec["tied_eligible_n"] = len(tied_el)
    rec["base_tied_still_tied_share"] = len(TIED0 & tied) / max(1, len(TIED0))
    rec["tied_jaccard"] = len(TIED0 & tied) / max(1, len(TIED0 | tied))
    rec["base_eligible_still_eligible_tied_share"] = len(TIED0_EL & tied_el) / max(1, len(TIED0_EL))
    rec["eligible_jaccard"] = len(TIED0_EL & tied_el) / max(1, len(TIED0_EL | tied_el))
    for i, t0 in zip(IDS, TW0):
        if i not in pos or r["rank"][pos[i]] <= 0:
            rec["analogs"].append({"id": i, "rank": None}); continue
        j = pos[i]
        fpj = float(r["final_pub"][j])
        rec["analogs"].append({"id": i, "rank": int(r["rank"][j]), "final": fpj, "in_five": i in five_ids,
                               "tied_top": bool(fpj == top), "n_better": int((fp > fpj).sum()),
                               "twin_kept": int(r["twin"][j]) == t0})
    return rec


def main():
    t0 = time.time()
    with Pool(WORKERS) as pool:
        recs = []
        for rec in pool.imap(one, range(RUNS)):
            recs.append(rec)
            if len(recs) % 20 == 0:
                print(CRIT, SSET, len(recs), round(time.time() - t0), flush=True)
    n = len(recs)
    per = []
    for q, (i, t) in enumerate(zip(IDS, TW0)):
        a = [r["analogs"][q] for r in recs]
        ranked = [x for x in a if x["rank"]]
        per.append({"id": i, "twin": t,
                    "in_five_share": round(sum(x.get("in_five", False) for x in a) / n, 4),
                    "top20_share_rank": round(sum(1 for x in ranked if x["rank"] <= 20) / n, 4),
                    "top50_share_rank": round(sum(1 for x in ranked if x["rank"] <= 50) / n, 4),
                    # tie-aware: fewer than 20 / 50 points strictly better (ties at the top are not ordered by the data)
                    "top20_share_tie_aware": round(sum(1 for x in ranked if x["n_better"] < 20) / n, 4),
                    "top50_share_tie_aware": round(sum(1 for x in ranked if x["n_better"] < 50) / n, 4),
                    "tied_top_share": round(sum(1 for x in ranked if x["tied_top"]) / n, 4),
                    "twin_kept_share": round(sum(1 for x in ranked if x["twin_kept"]) / n, 4),
                    "passes_share": round(len(ranked) / n, 4),
                    "rank_median": float(np.median([x["rank"] for x in ranked])) if ranked else None})
    fives = [tuple(r["five"]) for r in recs]
    summary = {"criteria": CRIT, "sigma_set": SSET, "sigmas": {f"{b}:{c}": v for (b, c), v in SIGMAS[SSET].items()},
               "runs": n, "seed": SEED, "base_five": IDS, "base_twins": TW0, "per_analog": per,
               "five_repeat_exact_share": round(sum(f == tuple(IDS) for f in fives) / n, 4),
               "five_repeat_as_set_share": round(sum(set(f) == set(IDS) for f in fives) / n, 4),
               "distinct_fives": len(set(fives)),
               "n_tied_top_median_p5_p95": [float(np.percentile([r["n_tied_top"] for r in recs], q)) for q in (50, 5, 95)],
               "within_of_fifth_median": {w: float(np.median([r[w] for r in recs])) for w in ("within_0_1", "within_0_5", "within_1")},
               "within_of_fifth_p5_p95": {w: [float(np.percentile([r[w] for r in recs], q)) for q in (5, 95)] for w in ("within_0_1", "within_0_5", "within_1")},
               "tied_group": {"base_tied_n": len(TIED0), "base_eligible_n": len(TIED0_EL),
                              **{f"{k}_median_p5_p95": [round(float(np.percentile([r[k] for r in recs], q)), 4) for q in (50, 5, 95)]
                                 for k in ("tied_n", "tied_eligible_n", "base_tied_still_tied_share", "tied_jaccard",
                                           "base_eligible_still_eligible_tied_share", "eligible_jaccard")}},
               "seconds": round(time.time() - t0), "records": recs}
    out = os.path.join(R.OUT, f"ra_rover_mc_{CRIT}_{SSET}.json")
    json.dump(summary, open(out, "w"), indent=0)
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, indent=1))


if __name__ == "__main__":
    main()
