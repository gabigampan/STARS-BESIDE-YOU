"""p3_baseline: reproduce the shipped ranking of each mission with the auditor's own code
(p3_common) and compare it with the bundle and with docs/AUDIO_TOP5.json.
Output: out/p3_baseline.json. Run: python p3_baseline.py"""
import numpy as np

from p3_common import (MISSIONS, audio_pairs, bundle_col, bundle_mission, dump, load_params, load_tables,
                       lunar_base_zone_ids, run_mission, sim_values)


def main():
    P = load_params()
    T = load_tables(P)
    lbz = lunar_base_zone_ids()
    SV = sim_values(T, P)
    # TOA: own numerical integration vs the bundle's published column (float32, per grid row)
    toa_b = bundle_col("earth_base.bin", "d.irradiance_toa_kwh_m2_day")
    lat_rows = 90 - (np.arange(180) + 0.5)
    from p3_common import toa_insolation
    toa_own = toa_insolation(lat_rows, P["toa"])
    res = {"toa_max_abs_diff_vs_bundle": float(np.nanmax(np.abs(toa_own - toa_b))),
           "toa_reference_check": {k: float(toa_insolation(np.array([float(k)]), P["toa"])[0])
                                   for k in P["toa"]["reference_values_kwh_m2_day"]},
           "toa_reference_config": P["toa"]["reference_values_kwh_m2_day"],
           "lunar_base_zone_cells": int(len(lbz)), "missions": {}}
    pairs = audio_pairs()
    for m in MISSIONS:
        mine = run_mission(T, m, P, lbz, SV)
        b = bundle_mission(m).set_index("id")
        j = mine.set_index("id").join(b, rsuffix="_b")
        both = j["rank"].gt(0) | j["rank_b"].gt(0)
        r = {
            "passing_mine": int(len(mine)), "passing_bundle": int(len(b)),
            "ranked_mine": int((mine["rank"] > 0).sum()), "ranked_bundle": int((b["rank"] > 0).sum()),
            "rank_equal_share": float((j.loc[both, "rank"] == j.loc[both, "rank_b"]).mean()),
            "twin_equal_share": float((j["twin"].fillna(-1).astype(int) == j["twin_b"].fillna(-1).astype(int)).mean()),
            "max_abs_diff_similarity": float(np.nanmax(np.abs(j["similarity"] - j["similarity_b"]))),
            "max_abs_diff_suitability": float(np.nanmax(np.abs(j["suitability"] - j["suitability_b"]))),
            "max_abs_diff_final_pub": float(np.nanmax(np.abs(j["final_pub"] - j["final_b"]))),
        }
        top = mine[mine["rank"].between(1, 5)].sort_values("rank")
        r["top5_mine"] = top[["rank", "id", "twin", "similarity", "suitability", "final_pub"]].to_dict("records")
        r["audio_match"] = []
        for p in pairs:
            if p["mission"] != m:
                continue
            row = mine[mine["id"] == p["earth_id"]].iloc[0]
            r["audio_match"].append({"audio_rank": p["rank"], "earth": p["earth_id"], "rank_mine": int(row["rank"]),
                                     "twin_ok": int(row["twin"]) == p["moon_id"],
                                     "final_ok": abs(round(float(row["final_pub"]), 2) - p["final"]) < 0.006})
        res["missions"][m] = r
        print(m, {k: v for k, v in r.items() if k not in ("top5_mine",)})
    print(dump("p3_baseline.json", res))


if __name__ == "__main__":
    main()
