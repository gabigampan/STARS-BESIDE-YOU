"""p3_robustness (point 5): one-at-a-time weight perturbations.

For each mission: every suitability weight and every similarity weight multiplied by
1.1 and by 0.9, the mission's other weights unchanged, then all weights of that block
renormalised to the same total; and every secondary similarity variable removed (weights
of the remaining variables renormalised). Removal is run in two treatments of the pair
filter: 'both' (the variable leaves the weighted mean AND the filter: the rule no longer
knows it) and 'sim_only' (weight 0, its filter bound 2 x tolerance still applies).
Every run recomputes funnel, suitability, twins, similarity, final and rank from scratch
with p3_common. Output: out/p3_robustness.json, out/p3_robustness_runs.csv.
Run: python p3_robustness.py"""
import csv
import os

import numpy as np

from p3_common import (MISSIONS, OUT, audio_pairs, dump, funnel, load_params, load_tables, lunar_base_zone_ids,
                       run_mission, sim_values)


def perturbations(m, P):
    soft = {c: float(s["weight"]) for c, s in P["missions"][m]["soft"].items()}
    simv = P["missions"][m]["sim"]["variables"]
    simw = {x["variable"]: float(x["weight"]) for x in simv}
    out = [("baseline", {}, {})]
    for blk, base in (("suit", soft), ("sim", simw)):
        tot = sum(base.values())
        for v in base:
            for f in (1.1, 0.9):
                w = dict(base)
                w[v] *= f
                s = sum(w.values())
                w = {k: x * tot / s for k, x in w.items()}
                out.append((f"{blk}:{v}:x{f}", {"suit_w": w} if blk == "suit" else {"sim_w": w}, {}))
    for x in simv:
        if x["role"] == "secondary":
            for mode in ("both", "sim_only"):
                out.append((f"drop:{x['variable']}:{mode}", {"drop": x["variable"], "drop_mode": mode}, {}))
    return out


def main():
    P = load_params()
    T = load_tables(P)
    lbz = lunar_base_zone_ids()
    SV = sim_values(T, P)
    pairs = audio_pairs()
    rows = []
    summary = {}
    for m in MISSIONS:
        passE = funnel(T["EARTH"], "EARTH", m, P)
        cache = {}
        mp = [p for p in pairs if p["mission"] == m]
        per = {p["earth_id"]: {"place": p["place"], "audio_rank": p["rank"], "in_top5": 0, "same_rank": 0,
                               "same_twin": 0, "runs": 0, "worst_rank": 0, "worst_run": None, "lost_top5_in": []}
               for p in mp}
        newcomers = {}
        for name, kw, _ in perturbations(m, P):
            r = run_mission(T, m, P, lbz, SV, passE=passE, util_cache=cache, **kw)
            r = r.set_index("id")
            top5 = r[(r["rank"] >= 1) & (r["rank"] <= 5)].sort_values("rank")
            for p in mp:
                x = r.loc[p["earth_id"]]
                rk = int(x["rank"]) if x["rank"] > 0 else 10 ** 6
                d = per[p["earth_id"]]
                if name != "baseline":
                    d["runs"] += 1
                    d["in_top5"] += int(1 <= rk <= 5)
                    d["same_rank"] += int(rk == p["rank"])
                    d["same_twin"] += int(int(x["twin"]) == p["moon_id"])
                    if rk > d["worst_rank"]:
                        d["worst_rank"], d["worst_run"] = rk, name
                    if rk > 5:
                        d["lost_top5_in"].append(f"{name} (rank {rk})")
                rows.append({"mission": m, "run": name, "earth_id": p["earth_id"], "audio_rank": p["rank"],
                             "rank": rk, "twin": int(x["twin"]), "twin_audio": p["moon_id"],
                             "similarity": round(float(x["similarity"]), 4) if np.isfinite(x["similarity"]) else None,
                             "suitability": round(float(x["suitability"]), 4), "final": round(float(x["final"]), 4)
                             if np.isfinite(x["final"]) else None})
            audio_ids = {p["earth_id"] for p in mp}
            for i in top5.index:
                if i not in audio_ids:
                    newcomers.setdefault(int(i), []).append(f"{name} (rank {int(top5.loc[i, 'rank'])})")
            print(m, name, list(top5.index), flush=True)
        n_runs = len(perturbations(m, P)) - 1
        summary[m] = {"perturbations": n_runs, "pairs": per, "new_top5_entrants": newcomers,
                      "pairs_surviving_all": sum(1 for d in per.values() if d["in_top5"] == n_runs)}
    summary["overall_surviving_all"] = sum(summary[m]["pairs_surviving_all"] for m in MISSIONS)
    with open(os.path.join(OUT, "p3_robustness_runs.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(dump("p3_robustness.json", summary))


if __name__ == "__main__":
    main()
