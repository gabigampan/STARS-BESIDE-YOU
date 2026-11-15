"""Point 3 (normalisation and similarity): recompute every passing point of the three
missions with the independent implementation (p2_model) and compare with the bundle.

    python "tierra luna/audit/p2_recompute.py"

Writes audit/out/p2_recompute.json (summary), audit/out/p2_pairs_<mission>.csv (one row
per passing Earth point: bundle and recomputed values side by side).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p2_common import BUNDLE, OUT, configs, dump, jload, mission_bundle, read_bin, tables  # noqa: E402
import p2_model  # noqa: E402


def cmp(a, b, tol):
    a, b = np.asarray(a, float), np.asarray(b, float)
    both_nan = ~np.isfinite(a) & ~np.isfinite(b)
    eq = both_nan | (np.isfinite(a) & np.isfinite(b) & (np.abs(a - b) <= tol))
    d = np.abs(a - b)
    return {"n": int(a.size), "equal": int(eq.sum()), "different": int((~eq).sum()),
            "max_abs_diff": float(np.nanmax(d)) if np.isfinite(d).any() else None,
            "first_different_index": [int(x) for x in np.flatnonzero(~eq)[:10]]}


def main():
    eng, ms = configs()
    e, m = tables()
    moon_base = read_bin("moon_base.bin")
    mz = jload(os.path.join(BUNDLE, "mission_zones.json"))
    codes = [r["code"] for r in mz["regions"]]
    region = moon_base["region"].astype(int)
    summary = {"inputs": {"earth_csv": "tierra luna/output_real/earth_real_1deg.csv",
                          "moon_csv": "tierra luna/output_real/moon_real_1deg.csv",
                          "bundle": "app/public/data/v2", "manifest_build_time": jload(os.path.join(BUNDLE, "manifest.json"))["build_time"]},
               "missions": {}}
    rv = eng["real_value_similarity"]["value"]
    # weights
    summary["weights"] = {mi: {"weights": [x["weight"] for x in rv["missions"][mi]["variables"]],
                               "sum": float(sum(x["weight"] for x in rv["missions"][mi]["variables"])),
                               "key_share": float(sum(x["weight"] for x in rv["missions"][mi]["variables"] if x["role"] == "key"))}
                          for mi in p2_model.MISSIONS}
    missions_json = jload(os.path.join(BUNDLE, "missions.json"))
    mj = {x["id"]: x for x in missions_json["missions"]}
    summary["bundle_weights"] = {mi: [(v["variable"], v["weight"], v["tolerance"], v["bound"], v.get("scale", "real"))
                                      for v in mj[mi]["similarity"]["variables"]] for mi in p2_model.MISSIONS}
    summary["alpha_bundle"] = missions_json["alpha"]
    toa_checked = False
    for mi in p2_model.MISSIONS:
        r = p2_model.run(mi, e, m, eng, ms)
        sp = r["spec"]
        base, eb, pr, pass_ids = mission_bundle(mi)
        res = {}
        # funnel
        res["passing_recomputed"] = int(r["ids"].size)
        res["passing_bundle"] = int(pass_ids.size)
        res["passing_same_set"] = bool(np.array_equal(r["ids"], pass_ids))
        # zone
        zi = r["zone"]
        want = {"rover": ["A", "B"], "solar": ["D"], "lunar_base": ["A"]}[mi]
        bz = np.flatnonzero(np.isin(region, [codes.index(c) for c in want]))
        res["zone_cells_recomputed"] = int(zi.size)
        res["zone_cells_bundle_regions"] = int(bz.size)
        res["zone_same_cells"] = bool(np.array_equal(zi, bz))
        if mi == "lunar_base":
            ap = r["zone_extra"]["lunar_base_area_positive"]
            res["zone_cells_with_positive_area_overlap"] = int(ap.sum())
            res["zone_cells_touching_only"] = [int(x) for x in np.flatnonzero(r["zone_mask"] & ~ap)]
        # twins
        btwin = np.where(np.isfinite(eb["twin"]), eb["twin"], -1).astype(int)
        res["paired_recomputed"] = int((r["twin"] >= 0).sum())
        res["paired_bundle"] = int((btwin >= 0).sum())
        res["twin"] = cmp(r["twin"], btwin, 0)
        diff_tw = np.flatnonzero(r["twin"] != btwin)
        res["twin_differences"] = [{"earth_id": int(r["ids"][i]), "twin_recomputed": int(r["twin"][i]),
                                    "twin_bundle": int(btwin[i]), "n_tied_recomputed": int(r["n_tied"][i])} for i in diff_tw[:20]]
        res["twin_in_zone_bundle"] = bool(np.all(np.isin(btwin[btwin >= 0], zi)))
        res["rows_with_exact_tie_at_best"] = int((r["n_tied"] > 1).sum())
        res["rows_where_published_scores_prefer_other_cell"] = int((r["pub_better"] > 0).sum())
        gap = r["best_full"] - r["second_full"]
        res["best_minus_second_full_precision"] = {"lt_1e-6": int(np.sum(gap < 1e-6)), "lt_0.005": int(np.sum(gap < 0.005)),
                                                   "lt_0.01": int(np.sum(gap < 0.01)), "paired": int(np.isfinite(gap).sum()),
                                                   "median": float(np.nanmedian(gap))}
        # filter on the bundle's pairs, with the auditor's values
        has = btwin >= 0
        E = np.column_stack([r["ev"][v] for v in sp["vars"]])
        M = np.column_stack([r["mv"][v] for v in sp["vars"]])
        if any(s != "real" for s in sp["scale"]):
            Ecmp_all = r["cmp_earth"]
            Mcmp = np.full((64800, len(sp["vars"])), np.nan)
            Mcmp[zi] = r["Mcmp_zone"]
            dB = np.abs(Ecmp_all[has] - Mcmp[btwin[has]])
        else:
            dB = np.abs(E[r["ids"][has]] - M[btwin[has]])
        fin = np.isfinite(dB)
        key = sp["key"]
        viol_key = (~fin[:, key]) | (dB[:, key] > sp["bound"][key] + 1e-12)
        viol_sec = fin[:, ~key] & (dB[:, ~key] > sp["bound"][~key] + 1e-12)
        res["filter_on_bundle_pairs"] = {"pairs": int(has.sum()), "key_violations": int(viol_key.any(1).sum()),
                                         "secondary_violations": int(viol_sec.any(1).sum()),
                                         "max_ratio_to_bound": {v: float(np.nanmax(dB[:, q] / sp["bound"][q])) for q, v in enumerate(sp["vars"])},
                                         "secondary_missing_in_pairs": {v: int((~fin[:, q]).sum()) for q, v in enumerate(sp["vars"]) if not key[q]}}
        # scores, similarity, suitability, final, rank
        for q, v in enumerate(sp["vars"]):
            res[f"s.{v}"] = cmp(r["scores"][:, q], eb[f"s.{v}"], 5e-7)
        res["similarity_2dp"] = cmp(np.array([round(float(x), 2) if np.isfinite(x) else np.nan for x in r["sim_pub"]]), eb["similarity"], 1e-9)
        res["suitability_2dp"] = cmp(np.array([round(float(x), 2) if np.isfinite(x) else np.nan for x in r["suit"]]), eb["suitability"], 1e-9)
        res["final_2dp"] = cmp(r["final2"], eb["final"], 1e-9)
        brank = np.where(np.isfinite(eb["rank"]), eb["rank"], 0).astype(int)
        res["rank"] = cmp(r["rank"], brank, 0)
        # pairs file real values (float32)
        for q, v in enumerate(sp["vars"]):
            res[f"pairs.{v}.earth"] = cmp(np.float32(r["real_earth"][:, q]), pr[f"{v}.earth"], 1e-3 * max(1, np.nanmax(np.abs(pr[f'{v}.earth']))) * 1e-3)
            res[f"pairs.{v}.moon"] = cmp(np.float32(r["real_moon"][:, q]), pr[f"{v}.moon"], 1e-6 * max(1, np.nanmax(np.abs(r['real_moon'][:, q]))))
            res[f"pairs.{v}.diff"] = cmp(np.float32(r["real_diff"][:, q]), pr[f"{v}.diff"], 1e-6 * max(1, np.nanmax(np.abs(r['real_earth'][:, q]))))
            if sp["scale"][q] != "real":
                res[f"pairs.{v}.earth_pct"] = cmp(r["cmp_earth"][:, q], pr[f"{v}.earth_pct"], 1e-4)
                res[f"pairs.{v}.moon_pct"] = cmp(r["cmp_moon"][:, q], pr[f"{v}.moon_pct"], 1e-4)
                res[f"pairs.{v}.diff_pct"] = cmp(r["cmp_diff"][:, q], pr[f"{v}.diff_pct"], 1e-4)
        if mi == "lunar_base":
            res["populations_recomputed"] = r["populations"]
            # percentile of the Moon from tmin_c + 273.15 (engine) vs the lunar tmin_k column
            mv = r["mv"]
            a = p2_model.midrank(mv["tmin_k"][zi])
            b = p2_model.midrank(mv["tmin_k_column"][zi])
            res["moon_tmin_pct_from_tmin_c_vs_tmin_k_column"] = {"max_abs_diff_points": float(np.nanmax(np.abs(a - b))),
                                                                 "cells_different": int(np.sum(np.abs(a - b) > 1e-9)),
                                                                 "ties_tmin_c": int(len(zi) - np.unique(mv["tmin_k"][zi]).size),
                                                                 "ties_tmin_k_column": int(len(zi) - np.unique(mv["tmin_k_column"][zi]).size)}
            ep = r["cmp_earth"]
            res["earth_ties_in_population"] = {v: int(np.isfinite(r["real_earth"][:, q]).sum() - np.unique(r["real_earth"][np.isfinite(r["real_earth"][:, q]), q]).size)
                                               for q, v in enumerate(sp["vars"]) if sp["scale"][q] != "real"}
            res["moon_ties_in_zone"] = {v: int(len(zi) - np.unique(r["Mcmp_zone"][:, q]).size)
                                        for q, v in enumerate(sp["vars"]) if sp["scale"][q] != "real"}
        if mi == "solar" and not toa_checked:
            toa_b = base["d.irradiance_toa_kwh_m2_day"]
            lat_rows = 89.5 - np.arange(180)
            mine = p2_model.toa_numeric(lat_rows)
            res["toa_formula_vs_bundle_rows"] = {"max_abs_diff_kwh": float(np.max(np.abs(mine - toa_b))),
                                                 "equator_rows": [float(mine[89]), float(mine[90])],
                                                 "bundle_equator_rows": [float(toa_b[89]), float(toa_b[90])],
                                                 "lat_0.5_29.5_44.5_59.5": [float(mine[89]), float(mine[60]), float(mine[45]), float(mine[30])]}
            toa_checked = True
        res["elevation_body_means"] = r["derived_notes"]["elevation_body_mean"]
        summary["missions"][mi] = res
        # per-point CSV
        df = pd.DataFrame({"earth_id": r["ids"], "twin_bundle": btwin, "twin_recomputed": r["twin"],
                           "similarity_bundle": eb["similarity"], "similarity_recomputed": r["sim_pub"],
                           "suitability_bundle": eb["suitability"], "suitability_recomputed": r["suit"],
                           "final_bundle": eb["final"], "final_recomputed": r["final"], "rank_bundle": brank,
                           "rank_recomputed": r["rank"], "zone_cells_passing_filter": r["n_zone_pass"],
                           "best_minus_second": gap})
        for q, v in enumerate(sp["vars"]):
            df[f"{v}.earth"] = r["real_earth"][:, q]
            df[f"{v}.moon"] = r["real_moon"][:, q]
            df[f"{v}.diff"] = r["real_diff"][:, q]
            df[f"{v}.score"] = r["scores"][:, q]
            if sp["scale"][q] != "real":
                df[f"{v}.earth_pct"] = r["cmp_earth"][:, q]
                df[f"{v}.moon_pct"] = r["cmp_moon"][:, q]
                df[f"{v}.diff_pct"] = r["cmp_diff"][:, q]
        df.to_csv(os.path.join(OUT, f"p2_pairs_{mi}.csv"), index=False, float_format="%.6f")
        print(mi, json.dumps({k: v for k, v in res.items() if k in ("passing_same_set", "zone_same_cells", "twin", "similarity_2dp", "final_2dp", "rank", "filter_on_bundle_pairs")}, default=str)[:1500])
    dump(summary, "p2_recompute.json")


if __name__ == "__main__":
    main()
