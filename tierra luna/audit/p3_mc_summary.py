"""p3_mc_summary (point F.4): summarise the Monte Carlo files out/p3_mc_<mission>_f<factor>.json.
Output: out/p3_mc_summary.json. Run: python p3_mc_summary.py"""
import glob
import json
import os
from collections import Counter

import numpy as np

from p3_common import OUT, dump


def main():
    out = {}
    for path in sorted(glob.glob(os.path.join(OUT, "p3_mc_*_f*.json"))):
        d = json.load(open(path))
        tag = os.path.basename(path)[6:-5]
        R = np.array(d["rank"], dtype=float)
        R[R <= 0] = np.inf
        W = np.array(d["twin"])
        n = R.shape[0]
        pairs = []
        for j, p in enumerate(d["audio"]):
            r = R[:, j]
            fin = r[np.isfinite(r)]
            pairs.append({
                "audio_rank": p["rank"], "earth_id": p["earth_id"], "place": p["place"],
                "top5": round(float((r <= 5).mean()), 3), "top20": round(float((r <= 20).mean()), 3),
                "top50": round(float((r <= 50).mean()), 3), "same_rank": round(float((r == p["rank"]).mean()), 3),
                "rank_p05": float(np.quantile(r, 0.05)), "rank_median": float(np.median(r)),
                "rank_p95": float(np.quantile(r, 0.95)) if np.isfinite(np.quantile(r, 0.95)) else "unranked",
                "unranked_share": round(float((~np.isfinite(r)).mean()), 3),
                "fails_funnel_share": round(float((W[:, j] == -2).mean()), 3),
                "no_twin_share": round(float((W[:, j] == -1).mean()), 3),
                "twin_changed_share": round(float((W[:, j] != p["moon_id"]).mean()), 3),
                "twins_seen": dict(Counter(int(x) for x in W[:, j]).most_common(4)),
            })
        base = d["baseline_top5"]
        tops = d["top5"]
        overlap = [len(set(t) & set(base)) for t in tops]
        members = Counter(i for t in tops for i in t)
        out[tag] = {
            "runs": n, "sigma_factor": d["sigma_factor"], "seed": d["seed"], "pairs": pairs,
            "top5_identical_set_share": round(float(np.mean([set(t) == set(base) for t in tops])), 3),
            "top5_identical_order_share": round(float(np.mean([t == base for t in tops])), 3),
            "top5_overlap_hist": {str(k): int(v) for k, v in sorted(Counter(overlap).items())},
            "top5_overlap_mean": round(float(np.mean(overlap)), 2),
            "top5_members_most_frequent": {str(k): round(v / n, 3) for k, v in members.most_common(12)},
            "distinct_top5_members": len(members),
            "ranked_count": {"baseline": d["baseline_ranked"], "min": int(min(d["n_ranked"])), "max": int(max(d["n_ranked"]))},
            "passing_count": {"min": int(min(d["n_pass"])), "max": int(max(d["n_pass"]))},
            "sigma": d["sigma"], "not_perturbed": d["not_perturbed"],
        }
        print(tag, n, out[tag]["top5_identical_set_share"], out[tag]["top5_overlap_hist"],
              [(q["audio_rank"], q["top5"], q["top20"], q["rank_p05"], q["rank_p95"], q["twin_changed_share"]) for q in pairs])
    print(dump("p3_mc_summary.json", out))


if __name__ == "__main__":
    main()
