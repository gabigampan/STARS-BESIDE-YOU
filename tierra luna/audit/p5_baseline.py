"""Reproduce the shipped bundle with the auditor's own code (p5_common) and compare.
Run: <python> "tierra luna/audit/p5_baseline.py"  -> out/p5_baseline.json"""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p5_common import (pyround, MISSIONS, OUT, load_params, load_tables, derived, run_mission, bundle_mission, top_pairs)

def main():
    t = time.time()
    P = load_params(); T = load_tables(P); D = derived(T, P)
    rep = {"body_means_m": D["_body_mean"]}
    for m in MISSIONS:
        r = run_mission(T, D, m, P)
        b = bundle_mission(m)
        same_set = np.array_equal(np.sort(b["ids"]), np.sort(r["pass_ids"]))
        pos = {i: k for k, i in enumerate(r["pass_ids"])}
        idx = np.array([pos[i] for i in b["ids"]])
        tw_b = np.where(np.isfinite(b["twin"]), b["twin"], -1).astype(int)
        rk_b = np.where(np.isfinite(b["rank"]), b["rank"], 0).astype(int)
        def mx(a, c):
            ok = np.isfinite(a) & np.isfinite(c)
            return float(np.max(np.abs(a[ok] - c[ok]))) if ok.any() else None
        rep[m] = {
            "earth_pass_mine": int(r["passed"].sum()), "earth_pass_bundle": int(len(b["ids"])), "same_pass_set": bool(same_set),
            "zone_cells": r["zone_n"], "moon_pass_mine": int(r["moon_pass"].sum()),
            "paired_mine": int((r["twin"] >= 0).sum()), "paired_bundle": int((tw_b >= 0).sum()),
            "twin_mismatch": int((r["twin"][idx] != tw_b).sum()),
            "rank_mismatch": int((r["rank"][idx] != rk_b).sum()),
            "max_abs_diff_suitability_vs_published2dec": mx(pyround(r["suit"][idx], 2), b["suitability"]),
            "max_abs_diff_similarity_vs_published2dec": mx(pyround(r["sim"][idx], 2), b["similarity"]),
            "max_abs_diff_final_pub": mx(r["final_pub"][idx], b["final"]),
            "top5_mine": top_pairs(r, 5),
        }
        print(m, json.dumps({k: v for k, v in rep[m].items() if k != "top5_mine"}), flush=True)
    rep["seconds"] = round(time.time() - t, 1)
    json.dump(rep, open(os.path.join(OUT, "p5_baseline.json"), "w"), indent=1, default=float)
    print(json.dumps(rep["body_means_m"]), rep["seconds"])

if __name__ == "__main__":
    main()
