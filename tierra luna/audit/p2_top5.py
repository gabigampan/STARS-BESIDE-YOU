"""Point 4 (the top 5): ordering quantity, ties, duplicates and distances, minimum-separation
alternatives (design question, NOT applied), and why the five Rover pairs share one twin.

    python "tierra luna/audit/p2_top5.py"

Reads the bundle (own decoder, p2_common), the tables and the configuration; the per-cell
lunar comparison of the Rover top 5 uses the auditor's own implementation (p2_model).
Writes audit/out/p2_top5.json. Deterministic; no network.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p2_common import (BUNDLE, R_EARTH, configs, dump, gc_km, jload, latlon, mission_bundle,  # noqa: E402
                       qtl, read_bin, tables)
import p2_model  # noqa: E402

MISSIONS = ["rover", "solar", "lunar_base"]
SEPARATIONS_KM = {"2deg_222km": float(np.radians(2.0) * R_EARTH),  # 2 degrees of great circle = 222.4 km
                  "500km": 500.0, "1000km": 1000.0}


def ranked(mission):
    base, eb, pr, pass_ids = mission_bundle(mission)
    rk = eb["rank"]
    ok = np.isfinite(rk) & (rk > 0)
    idx = np.flatnonzero(ok)
    idx = idx[np.argsort(rk[idx], kind="mergesort")]
    lat, lon = latlon(pass_ids[idx])
    return {"pos": idx, "id": pass_ids[idx], "rank": rk[idx].astype(int), "final": eb["final"][idx],
            "sim": eb["similarity"][idx], "suit": eb["suitability"][idx], "twin": eb["twin"][idx].astype(int),
            "lat": lat, "lon": lon, "eb": eb, "pr": pr, "pass_ids": pass_ids}


def greedy_separated(r, km, n=5):
    chosen = []
    for i in range(len(r["id"])):
        if all(gc_km(r["lat"][i], r["lon"][i], r["lat"][j], r["lon"][j], R_EARTH) >= km for j in chosen):
            chosen.append(i)
        if len(chosen) == n:
            break
    return chosen


def main():
    out = {"bundle_build_time": jload(os.path.join(BUNDLE, "manifest.json"))["build_time"], "missions": {}}
    twins_json = jload(os.path.join(BUNDLE, "twins.json"))
    audio = jload(os.path.join(os.path.dirname(BUNDLE), "..", "..", "..", "docs", "AUDIO_TOP5.json"))
    moon_base = read_bin("moon_base.bin")
    for mi in MISSIONS:
        r = ranked(mi)
        res = {}
        n = len(r["id"])
        # 1. the stored rank is the order of the stored final (2 dp) descending, ties by Earth id
        order = np.lexsort((r["id"], -r["final"]))
        res["rank_follows_final_desc_then_id"] = bool(np.array_equal(order, np.arange(n)))
        res["rank_is_1_to_n"] = bool(np.array_equal(r["rank"], np.arange(1, n + 1)))
        res["ranked"] = n
        # what if the list were ordered by similarity instead
        so = np.lexsort((r["id"], -r["sim"]))
        res["top5_by_similarity_instead"] = [{"earth_id": int(r["id"][i]), "similarity": float(r["sim"][i]),
                                              "suitability": float(r["suit"][i]), "final": float(r["final"][i]),
                                              "rank_by_final": int(r["rank"][i])} for i in so[:5]]
        res["cells_with_max_similarity"] = int(np.sum(r["sim"] == r["sim"].max()))
        res["max_similarity"] = float(r["sim"].max())
        # top 5 and top 20
        res["top20"] = [{"rank": int(r["rank"][i]), "earth_id": int(r["id"][i]), "lat": float(r["lat"][i]),
                         "lon": float(r["lon"][i]), "final": float(r["final"][i]), "similarity": float(r["sim"][i]),
                         "suitability": float(r["suit"][i]), "twin": int(r["twin"][i])} for i in range(min(20, n))]
        # how much of the top is ordered by similarity and how much by suitability
        spread = {}
        for N in (5, 20, 100):
            s, u, f = r["sim"][:N], r["suit"][:N], r["final"][:N]
            spread[f"top{N}"] = {"similarity_range": [float(s.min()), float(s.max())], "suitability_range": [float(u.min()), float(u.max())],
                                 "final_range": [float(f.min()), float(f.max())],
                                 "var_share_0.25var_sim": float(0.25 * np.var(s) / np.var(f)) if np.var(f) > 0 else None,
                                 "var_share_0.25var_suit": float(0.25 * np.var(u) / np.var(f)) if np.var(f) > 0 else None,
                                 "spearman_final_vs_similarity": float(spearmanr(f, s).correlation),
                                 "spearman_final_vs_suitability": float(spearmanr(f, u).correlation)}
        s, u, f = r["sim"], r["suit"], r["final"]
        spread["all"] = {"spearman_final_vs_similarity": float(spearmanr(f, s).correlation),
                         "spearman_final_vs_suitability": float(spearmanr(f, u).correlation),
                         "spearman_similarity_vs_suitability": float(spearmanr(s, u).correlation),
                         "sd_similarity": float(np.std(s)), "sd_suitability": float(np.std(u))}
        res["what_orders_the_top"] = spread
        # ties on the stored final
        vals, cnt = np.unique(r["final"], return_counts=True)
        tied_vals = set(vals[cnt > 1].tolist())
        res["ties"] = {"rows_sharing_their_final_with_another_row": int(np.sum(np.isin(r["final"], list(tied_vals)))),
                       "within_top5": int(np.sum(np.isin(r["final"][:5], list(tied_vals)))),
                       "within_top20": int(np.sum(np.isin(r["final"][:20], list(tied_vals)))),
                       "within_top100": int(np.sum(np.isin(r["final"][:100], list(tied_vals)))),
                       "rank5_final": float(r["final"][4]), "rank6_final": float(r["final"][5]),
                       "rows_with_final_equal_to_rank5": int(np.sum(r["final"] == r["final"][4])),
                       "gap_rank5_rank6": float(r["final"][4] - r["final"][5]),
                       "tie_groups_in_top20": [[int(r["rank"][i]) for i in np.flatnonzero(r["final"][:20] == v)]
                                               for v in np.unique(r["final"][:20]) if np.sum(r["final"][:20] == v) > 1]}
        # distances among the five (Earth, great circle, km) and grid adjacency
        top = list(range(5))
        D = [[float(gc_km(r["lat"][i], r["lon"][i], r["lat"][j], r["lon"][j], R_EARTH)) for j in top] for i in top]
        adj = [[int(r["rank"][i]), int(r["rank"][j])] for i in top for j in top if i < j and
               abs(r["lat"][i] - r["lat"][j]) <= 1 and min(abs(r["lon"][i] - r["lon"][j]), 360 - abs(r["lon"][i] - r["lon"][j])) <= 1]
        res["top5_distance_km"] = D
        res["top5_min_distance_km"] = float(min(D[i][j] for i in top for j in top if i < j))
        res["top5_adjacent_cell_pairs_by_rank"] = adj
        res["top5_same_cell"] = len(set(r["id"][:5].tolist())) < 5
        res["top5_distinct_twins"] = len(set(r["twin"][:5].tolist()))
        # minimum-separation alternatives (design question; nothing applied)
        alt = {}
        base_sum = float(np.sum(r["final"][:5]))
        for name, km in SEPARATIONS_KM.items():
            ch = greedy_separated(r, km)
            alt[name] = {"min_km": float(km), "ranks": [int(r["rank"][i]) for i in ch], "earth_ids": [int(r["id"][i]) for i in ch],
                         "finals": [float(r["final"][i]) for i in ch], "similarities": [float(r["sim"][i]) for i in ch],
                         "twins": [int(r["twin"][i]) for i in ch],
                         "sum_final_lost_vs_current": round(base_sum - float(np.sum(r["final"][ch])), 2),
                         "fifth_final": float(r["final"][ch[-1]]), "fifth_final_lost": round(float(r["final"][4] - r["final"][ch[-1]]), 2),
                         "members_changed": int(len(set(ch) - set(top)))}
        res["min_separation_alternatives"] = alt
        # one-twin-per-five alternative (distinct lunar twins)
        ch, seen = [], set()
        for i in range(n):
            if r["twin"][i] not in seen:
                ch.append(i)
                seen.add(r["twin"][i])
            if len(ch) == 5:
                break
        res["distinct_twin_alternative"] = {"ranks": [int(r["rank"][i]) for i in ch], "finals": [float(r["final"][i]) for i in ch],
                                            "twins": [int(r["twin"][i]) for i in ch],
                                            "sum_final_lost_vs_current": round(base_sum - float(np.sum(r["final"][ch])), 2)}
        # twin concentration
        tw, tc = np.unique(r["twin"], return_counts=True)
        o = np.argsort(-tc, kind="mergesort")
        tj = twins_json["missions"][mi]
        res["twins"] = {"distinct": int(tw.size), "largest": {"twin": int(tw[o[0]]), "points": int(tc[o[0]]), "share": float(tc[o[0]] / n)},
                        "top5_twins_by_points": [[int(tw[k]), int(tc[k])] for k in o[:5]],
                        "twins_json_distinct": tj["distinct_twins"], "twins_json_largest": tj["largest_share"],
                        "share_of_top20_on_most_used_twin_of_top5": None}
        t1 = int(r["twin"][0])
        res["twins"]["points_on_twin_of_rank1"] = int(np.sum(r["twin"] == t1))
        res["twins"]["top20_on_twin_of_rank1"] = int(np.sum(r["twin"][:20] == t1))
        res["twins"]["top100_on_twin_of_rank1"] = int(np.sum(r["twin"][:100] == t1))
        # AUDIO_TOP5 vs bundle
        ap = audio["missions"][mi]["pairs"]
        res["audio_top5_matches_bundle"] = [{"rank": p["rank"], "earth": p["earth_cell_id"], "moon": p["moon_cell_id"],
                                             "bundle_earth": f"E{int(r['id'][k])}", "bundle_moon": f"M{int(r['twin'][k])}",
                                             "same": p["earth_cell_id"] == f"E{int(r['id'][k])}" and p["moon_cell_id"] == f"M{int(r['twin'][k])}"}
                                            for k, p in enumerate(ap)]
        out["missions"][mi] = res
        print(mi, "rank rule:", res["rank_follows_final_desc_then_id"], "min dist top5 km:", round(res["top5_min_distance_km"], 1),
              "ties top5:", res["ties"]["within_top5"], "gap5-6:", round(res["ties"]["gap_rank5_rank6"], 2))

    # ------------------------------------------------------------------ Rover: why one twin
    eng, ms = configs()
    e, m = tables()
    ev, mv, _ = p2_model.derived(e, m, eng)
    zmask, _ = p2_model.zones(m, eng)
    sp = p2_model.spec(eng, "rover")
    zi = np.flatnonzero(zmask["rover"])
    M = np.column_stack([mv[v] for v in sp["vars"]])[zi]
    r = ranked("rover")
    why = {"zone_cells": int(zi.size), "per_point": []}
    for k in range(5):
        eid = int(r["id"][k])
        E = np.array([ev[v][eid] for v in sp["vars"]])
        d, ok, sim, s = p2_model.pair_matrix(E, M, sp)
        sv = np.where(ok, sim, -np.inf)
        o = np.lexsort((zi, -sim))[:3]          # best three zone cells by similarity, filter or not
        why["per_point"].append({
            "rank": k + 1, "earth_id": eid, "earth_values": {v: float(E[q]) for q, v in enumerate(sp["vars"])},
            "zone_cells_passing_filter": int(ok.sum()),
            "zone_cells_with_slope_and_roughness_within_tolerance": int(np.sum((d[:, 0] <= sp["bound"][0]) & (d[:, 1] <= sp["bound"][1]))),
            "zone_cells_with_slope_within_tolerance": int(np.sum(d[:, 0] <= sp["bound"][0])),
            "zone_cells_with_roughness_within_tolerance": int(np.sum(d[:, 1] <= sp["bound"][1])),
            "zone_cells_passing_with_similarity_ge_99": int(np.sum(ok & (sim >= 99))),
            "best3": [{"moon_id": int(zi[t]), "passes_filter": bool(ok[t]), "similarity": round(float(sim[t]), 4),
                       "scores": {v: round(float(s[t, q]), 6) for q, v in enumerate(sp["vars"])},
                       "diff": {v: round(float(d[t, q]), 3) for q, v in enumerate(sp["vars"])},
                       "moon_values": {v: round(float(M[t, q]), 3) for q, v in enumerate(sp["vars"])}} for t in o]})
    tw = int(r["twin"][0])
    tpos = int(np.searchsorted(zi, tw))
    sl, ro, el = M[:, 0], M[:, 1], M[:, 2]

    def pct(a, x):
        a = a[np.isfinite(a)]
        return float(100.0 * (np.sum(a < x) + 0.5 * np.sum(a == x)) / a.size)
    why["twin"] = {"moon_id": tw, "lat": float(latlon(tw)[0]), "lon": float(latlon(tw)[1]),
                   "values": {"slope_deg": float(sl[tpos]), "roughness_m": float(ro[tpos]), "elevation_rel_m": float(el[tpos])},
                   "percentile_in_zone": {"slope_deg": pct(sl, sl[tpos]), "roughness_m": pct(ro, ro[tpos]), "elevation_rel_m": pct(el, el[tpos])}}
    why["zone_distribution"] = {"slope_deg": qtl(sl), "roughness_m": qtl(ro), "elevation_rel_m": qtl(el)}
    gentle = (sl <= 2.0) & (ro <= 60)
    why["zone_cells_slope_le_2_and_rough_le_60"] = int(gentle.sum())
    why["zone_cells_slope_le_1.5_and_rough_le_50"] = int(np.sum((sl <= 1.5) & (ro <= 50)))
    # Earth top-100 rover values against the zone: the low-slope, moderate-roughness corner
    E100 = np.column_stack([ev[v][r["id"][:100]] for v in sp["vars"]])
    why["earth_top100"] = {v: qtl(E100[:, q], (0.0, 0.5, 1.0)) for q, v in enumerate(sp["vars"])}
    why["earth_ranked_all"] = {v: qtl(np.column_stack([ev[v][r["id"]]])[:, 0], (0.1, 0.5, 0.9)) for v in sp["vars"]}
    # rover suitability utilities favour gentle slopes: show the soft spec
    why["rover_soft_spec"] = ms["missions"]["rover"]["soft"]
    out["rover_one_twin"] = why
    dump(out, "p2_top5.json")


if __name__ == "__main__":
    main()
