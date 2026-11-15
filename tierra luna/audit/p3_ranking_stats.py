"""p3_ranking_stats (point F.1-F.2): dispersion of similarity, suitability and final over
ALL ranked points of each mission (auditor's own recompute, p3_common), practical ties
near the fifth place, and the gaps between consecutive ranks down to rank 50.
Output: out/p3_ranking_stats.json. Run: python p3_ranking_stats.py"""
import numpy as np

from p3_common import MISSIONS, dump, load_params, load_tables, lunar_base_zone_ids, run_mission, sim_values

Q = [0, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.0]


def quant(x):
    x = x[np.isfinite(x)]
    return {f"q{int(q * 100):02d}": round(float(np.quantile(x, q)), 3) for q in Q} | {
        "n": int(x.size), "mean": round(float(x.mean()), 3), "sd": round(float(x.std(ddof=1)), 3)}


def hist(x, edges):
    x = x[np.isfinite(x)]
    h, _ = np.histogram(x, bins=edges)
    return [{"from": float(edges[i]), "to": float(edges[i + 1]), "n": int(h[i])} for i in range(len(h))]


def main():
    P = load_params()
    T = load_tables(P)
    lbz = lunar_base_zone_ids()
    SV = sim_values(T, P)
    out = {}
    for m in MISSIONS:
        r = run_mission(T, m, P, lbz, SV)
        ranked = r[r["rank"] > 0].sort_values("rank")
        f = ranked["final_pub"].to_numpy()
        f5 = f[4]
        sim = ranked["similarity"].to_numpy()
        res = {
            "passing": int(len(r)), "ranked": int(len(ranked)), "without_twin": int((r["rank"] == 0).sum()),
            "similarity": quant(sim), "suitability_ranked": quant(ranked["suitability"].to_numpy()),
            "suitability_all_passing": quant(r["suitability"].to_numpy()), "final": quant(f),
            "hist_final_10": hist(f, np.arange(0, 101, 10)),
            "hist_similarity_10": hist(sim, np.arange(0, 101, 10)),
            "hist_suitability_10": hist(ranked["suitability"].to_numpy(), np.arange(0, 101, 10)),
            "hist_final_top": hist(f, np.array([f[0] - 10, f[0] - 5, f[0] - 2, f[0] - 1, f[0] - 0.5, f[0] + 0.01])),
            "fifth_final": float(f5), "first_final": float(f[0]),
            "within_of_fifth": {str(d): int((np.abs(f - f5) <= d + 1e-9).sum()) for d in (0.1, 0.5, 1.0, 2.0)},
            "below_fifth_within": {str(d): int(((f5 - f) <= d + 1e-9).sum() - 5) for d in (0.1, 0.5, 1.0, 2.0)},
            "gaps_1_to_50": [round(float(f[i] - f[i + 1]), 2) for i in range(min(50, len(f) - 1))],
            "final_at_rank": {str(k): float(f[k - 1]) for k in (1, 5, 10, 20, 50, 100, 500, 1000) if k <= len(f)},
            "similarity_ge_99_99": int((np.round(sim, 2) >= 99.99).sum()),
            "similarity_eq_100_pub": int((np.round(sim, 2) >= 100.0).sum()),
            "similarity_ge_99": int((sim >= 99.0).sum()),
            "top5": ranked.head(5)[["rank", "id", "twin", "similarity", "suitability", "final_pub"]].to_dict("records"),
            "distinct_twins_top50": int(ranked.head(50)["twin"].nunique()),
            "top50_twin_counts": {str(k): int(v) for k, v in ranked.head(50)["twin"].value_counts().head(5).items()},
        }
        g = np.array(res["gaps_1_to_50"])
        res["gaps_summary"] = {"max": float(g.max()), "argmax_between_ranks": [int(g.argmax()) + 1, int(g.argmax()) + 2],
                               "zero_gaps": int((g == 0).sum()), "gap_4_5": float(g[3]), "gap_5_6": float(g[4])}
        out[m] = res
        print(m, res["within_of_fifth"], res["gaps_summary"], res["similarity_ge_99_99"])
    print(dump("p3_ranking_stats.json", out))


if __name__ == "__main__":
    main()
