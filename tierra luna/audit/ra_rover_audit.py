"""ra_rover_audit: re-audit of Rover, items 2, 3, 7 and 8 and the slope-minimum check, in my own code path
(ra_rover_common, on the first audit's p5_common). Nothing of the engine is imported.

    python ra_rover_audit.py [bundle folder] [morning bundle folder]

bundle folder: default app/public/data/v2 (the corrected bundle under audit);
morning bundle folder: the bundle of commit a493514 extracted to a folder (git show), for item 3.
Writes out/ra_rover_audit.json. Deterministic.
"""
import copy
import json
import math
import os
import re
import sys
import time

import numpy as np
import pandas as pd

import ra_rover_common as R

C = R.C
t0 = time.time()
BDIR = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else C.BUNDLE
MDIR = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
res = {"bundle": BDIR, "morning_bundle": MDIR}

Pc = R.params("corrected")
Pm = R.params("audited_morning")
T = R.tables(Pc)
D = R.derived_rover(T, Pc)
E, M = T["EARTH"], T["MOON"]
rc = R.run(T, D, Pc)
rm = R.run(T, D, Pm)
res["sim_spec_corrected"] = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in R.sim_spec(Pc).items()}
res["sim_spec_morning"] = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in R.sim_spec(Pm).items()}
res["top5_rule_corrected"] = Pc["rover_top5"]

# ------------------------------------------------------------------ funnel (own), reasons
def funnel(P):
    mm = P["missions"]["rover"]
    gates = {k: g for k, g in P["common_gates"].items() if "EARTH" in P["common_bodies"].get(k, ["EARTH", "MOON"])}
    gates.update(mm["gates"])
    n_all = len(E)
    land = C.present(E["elevation_m"]) | (pd.to_numeric(E["mask_fraction"], errors="coerce").fillna(0).to_numpy() > 0)
    fails = {}
    for v in mm["require_present"]:
        fails[f"{v}:missing"] = ~C.present(E[v])
    for v, g in gates.items():
        x = pd.to_numeric(E[v], errors="coerce").to_numpy(float)
        fails[f"{v}:missing"] = fails.get(f"{v}:missing", np.zeros(n_all, bool)) | ~np.isfinite(x)
        if g.get("min") is not None:
            fails[f"{v}:below_min"] = np.isfinite(x) & (x < g["min"])
        if g.get("max") is not None:
            fails[f"{v}:above_max"] = np.isfinite(x) & (x > g["max"])
    anyf = np.zeros(n_all, bool)
    for a in fails.values():
        anyf |= a
    return {"cells_in_table": int(n_all), "passing": int((~anyf).sum()),
            "fail_counts_among_cells_with_elevation": {k: int((a & C.present(E["elevation_m"])).sum()) for k, a in fails.items()},
            "fail_counts_all_cells": {k: int(a.sum()) for k, a in fails.items()},
            "passing_equals_model": bool(((~anyf) == rc["passed"]).all())}


res["funnel"] = funnel(Pc)

# ------------------------------------------------------------------ compare with the bundle
B = R.bundle_rover(BDIR)
res["compare_corrected_vs_bundle"] = R.compare(rc, B)
mission = B["mission"]
res["bundle_mission_top5"] = mission.get("top5")
# bundle fail-bit counts
try:
    codes = {r["bit"]: r["code"] for r in mission["reason_codes"]}
    fb = B["fail_bits"].astype(int)
    res["bundle_fail_bit_counts"] = {codes[b]: int(((fb >> b) & 1).sum()) for b in sorted(codes)}
    res["bundle_fail_bits_len"] = int(len(fb))
except Exception as ex:  # noqa: BLE001
    res["bundle_fail_bit_counts"] = repr(ex)

# ------------------------------------------------------------------ difference table, bounds asserted
def dtable(r, P):
    S = R.sim_spec(P)
    ok = r["twin"] >= 0
    out = []
    for q, v in enumerate(S["names"]):
        d = r["diff"][ok, q]
        row = {"variable": v, "role": S["role"][q], "weight": float(S["w"][q]), "tolerance": float(S["tol"][q]),
               "filter_bound": float(S["bound"][q]), "sigma": None if S["sig"] is None else float(S["sig"][q]),
               "n_pairs": int(ok.sum()), "median": round(float(np.median(d)), 4), "p90": round(float(np.percentile(d, 90)), 4),
               "max": round(float(d.max()), 4), "all_within_bound": bool((d <= S["bound"][q] + 1e-9).all())}
        if S["sig"] is not None:
            row["share_within_sigma"] = round(float(np.mean(d <= S["sig"][q])), 5)
        out.append(row)
        assert row["all_within_bound"], v
    both = np.ones(ok.sum(), bool)
    if S["sig"] is not None:
        for q in range(len(S["names"])):
            both &= r["diff"][ok, q] <= S["sig"][q]
    return out, (int(both.sum()) if S["sig"] is not None else None)


res["difference_table_corrected"], res["pairs_both_within_sigma"] = dtable(rc, Pc)
res["difference_table_morning"], _ = dtable(rm, Pm)
# information row: relative elevation of the corrected pairs (not compared)
zi = np.flatnonzero(C.zone_mask(M, "rover", Pc))
mid_pos = {int(i): k for k, i in enumerate(M["id"].to_numpy())}
okc = rc["twin"] >= 0
er = D["elevation_rel_m"]["EARTH"][rc["pi"]][okc]
mr = D["elevation_rel_m"]["MOON"][[mid_pos[int(t)] for t in rc["twin"][okc]]]
de = np.abs(er - mr)
res["info_elevation_rel_corrected"] = {"median": round(float(np.median(de)), 1), "p90": round(float(np.percentile(de, 90)), 1), "max": round(float(de.max()), 1)}

# ------------------------------------------------------------------ general figures
def general(r):
    ok = r["rank"] > 0
    tw = r["twin"][ok]
    u, c = np.unique(tw, return_counts=True)
    fp = r["final_pub"][ok]
    srt = np.sort(fp)[::-1]
    fifth = float(srt[4])
    return {"passing": int(len(r["pi"])), "paired": int(ok.sum()), "distinct_twins": int(len(u)),
            "largest_twin": "M%d" % int(u[np.argmax(c)]), "largest_twin_points": int(c.max()), "largest_twin_share": round(float(c.max() / ok.sum()), 4),
            "top_final": float(srt[0]), "n_final_eq_top": int((fp == srt[0]).sum()), "fifth_of_ranking": fifth,
            "n_within_0_1_of_fifth": int((fp >= fifth - 0.1).sum()), "n_within_0_5": int((fp >= fifth - 0.5).sum()), "n_within_1": int((fp >= fifth - 1.0).sum()),
            "n_sim_pub_100": int((C.pyround(r["sim"][ok], 2) == 100).sum()),
            "spearman_final_suit": round(float(pd.Series(r["final"][ok]).corr(pd.Series(r["suit"][ok]), method="spearman")), 4),
            "top10_ids": [int(r["ids"][k]) for k in np.argsort(np.where(ok, r["rank"], 10 ** 9), kind="stable")[:10]]}


res["general_corrected"] = general(rc)
res["general_morning"] = general(rm)

# ------------------------------------------------------------------ places (own: brute force over GeoNames cities1000 of reverse_geocoder)
import reverse_geocoder  # noqa: E402  (data file only)
GN = pd.read_csv(os.path.join(os.path.dirname(reverse_geocoder.__file__), "rg_cities1000.csv"))
gla, glo = np.radians(GN.lat.to_numpy(float)), np.radians(GN.lon.to_numpy(float))
IAU = json.load(open(os.path.join(BDIR, "iau_moon_features.json"), encoding="utf-8"))


def nearest_place(la, lo):
    a, b = math.radians(la), math.radians(lo)
    c = np.sin(a) * np.sin(gla) + np.cos(a) * np.cos(gla) * np.cos(glo - b)
    k = int(np.argmax(c))
    return {"name": str(GN.name[k]), "admin1": str(GN.admin1[k]), "cc": str(GN.cc[k]), "km": round(float(np.degrees(np.arccos(min(1, c[k]))) * math.pi / 180 * 6371.0), 1)}


def nearest_feature(t):
    k = mid_pos[t]
    la, lo = float(M.lat[k]), float(M.lon[k])
    d = R.gc_deg(la, lo, np.array(IAU["lat"]), np.array(IAU["lon"]))
    j = int(np.argmin(d))
    return {"name": IAU["name"][j], "km": round(float(d[j]) * math.pi / 180 * 1737.4, 1)}


try:
    PD = json.load(open(os.path.join(BDIR, "place_detail.json"), encoding="utf-8"))
    PDB = R.bundle_cols(BDIR, "earth_place_detail.bin")
    BASE = R.bundle_cols(BDIR, "earth_base.bin")
    base_pos = {int(i): k for k, i in enumerate(BASE["id"])}
except Exception:  # noqa: BLE001
    PD = PDB = BASE = None
    base_pos = {}

# distance to the sea, from the table: nearest cell centre with mask_fraction == 0 (all water) -- a 1-degree proxy
mf_all = pd.to_numeric(E["mask_fraction"], errors="coerce").fillna(0).to_numpy(float)
water_cells = np.flatnonzero(mf_all == 0)
wla, wlo = E.lat.to_numpy(float)[water_cells], E.lon.to_numpy(float)[water_cells]


def coast_km(la, lo):
    return round(float(R.gc_deg(la, lo, wla, wlo).min()) * math.pi / 180 * 6371.0, 0)


def describe(r, ks, P):
    out = []
    for k in ks:
        i = int(r["ids"][k]); t = int(r["twin"][k]); tk = mid_pos[t]
        row = {"id": "E%d" % i, "lat": float(r["lat"][k]), "lon": float(r["lon"][k]), "rank": int(r["rank"][k]),
               "final": float(r["final_pub"][k]), "sim": round(float(r["sim"][k]), 4), "sim_full": round(float(r["sim_full"][k]), 6),
               "suit": round(float(r["suit"][k]), 3), "twin": "M%d" % t, "twin_lat": float(M.lat[tk]), "twin_lon": float(M.lon[tk]),
               "twin_in_zone": bool(M.lat[tk] <= -75.0), "twin_feature": nearest_feature(t),
               "slope_E": round(float(r["ev"][k, 0]), 3), "slope_M": round(float(r["mvt"][k, 0]), 3),
               "rough_E": round(float(r["ev"][k, 1]), 2), "rough_M": round(float(r["mvt"][k, 1]), 2),
               "land_share": float(r["land"][k]), "water_share": round(1 - float(r["land"][k]), 4), "snow_ice_frac": float(r["snow"][k]),
               "lc_dominant_cci": int(E["raw_lc_dominant_cci_code"][r["pi"][k]]) if np.isfinite(E["raw_lc_dominant_cci_code"][r["pi"][k]]) else None,
               "bare_frac": float(E["raw_bare_frac"][r["pi"][k]]), "rock_or_bare_frac": float(E["raw_rock_or_bare_frac"][r["pi"][k]]),
               "elevation_m": float(E["raw_elevation_m"][r["pi"][k]]), "dist_to_all_water_cell_km": coast_km(float(r["lat"][k]), float(r["lon"][k])),
               "nearest_place_own": nearest_place(float(r["lat"][k]), float(r["lon"][k]))}
        if PDB is not None and i in base_pos:
            j = base_pos[i]
            npi = PDB["nearest_place"][j]
            row["nearest_place_bundle"] = {"name": PD["nearest_places"][int(npi)] if np.isfinite(npi) else None, "km": round(float(PDB["nearest_place_km"][j]), 1)}
            row["place_name_agrees"] = row["nearest_place_bundle"]["name"] is not None and \
                re.sub(r"\W", "", row["nearest_place_bundle"]["name"].lower()) == re.sub(r"\W", "", row["nearest_place_own"]["name"].lower())
        out.append(row)
    dmin = min((float(R.gc_deg(r["lat"][a], r["lon"][a], r["lat"][b], r["lon"][b])) for a in ks for b in ks if a != b), default=None)
    return out, dmin


fc, fc_info = R.five(rc, Pc)
fm, fm_info = R.five(rm, Pm)
res["five_corrected"], res["five_corrected_min_sep_deg"] = describe(rc, fc, Pc)
res["five_corrected_info"] = fc_info
res["five_morning"], res["five_morning_min_sep_deg"] = describe(rm, fm, Pm)
res["five_corrected_ids"] = [int(rc["ids"][k]) for k in fc]
res["five_morning_ids"] = [int(rm["ids"][k]) for k in fm]
bt = mission.get("top5") or {}
res["five_bundle_ids"] = [int(x) for x in bt.get("ids", [])] if isinstance(bt, dict) else None
res["five_equal_bundle"] = res["five_bundle_ids"] == res["five_corrected_ids"]
# alternative rules on the corrected model (sensitivity of the rule for the five)
alt = {}
for nm, rule in {"rank_with_skips": {**Pc["rover_top5"], "rule": "rank_with_skips"},
                 "spread_ice_only": {**Pc["rover_top5"], "skips": {"ice": Pc["rover_top5"].get("skips", {}).get("ice", {"enabled": True, "value": 0.5}), "water": {"enabled": False}}},
                 "min_separation_no_skips": {"rule": "min_separation", "min_separation_deg": 2.0}}.items():
    alt[nm] = [int(rc["ids"][k]) for k in R.five(rc, Pc, rule)[0]]
res["five_corrected_alternative_rules"] = alt
# tied group composition
top = np.nanmax(rc["final_pub"])
tied = np.flatnonzero(rc["final_pub"] == top)
bad = R._skipped(rc, Pc["rover_top5"])
res["tied_group"] = {"n": int(len(tied)), "n_ice_skipped": int((np.nan_to_num(rc["snow"][tied], nan=-1) >= 0.5).sum()),
                     "n_water_skipped": int((rc["land"][tied] < 0.5).sum()), "n_eligible": int((~bad[tied]).sum()),
                     "lc_dominant_counts": pd.Series(E["raw_lc_dominant_cci_code"][rc["pi"][tied]]).value_counts().head(10).to_dict(),
                     "lat_bands": pd.cut(rc["lat"][tied], [-90, -60, -30, 0, 30, 60, 90]).value_counts().sort_index().astype(int).to_dict()}
res["tied_group"]["lat_bands"] = {str(k): int(v) for k, v in res["tied_group"]["lat_bands"].items()}
res["tied_group"]["lc_dominant_counts"] = {str(int(k)): int(v) for k, v in res["tied_group"]["lc_dominant_counts"].items()}

# ------------------------------------------------------------------ external validation
bench = pd.read_csv(os.path.join(C.TL, "data", "benchmark", "analog_benchmark.csv"))
sys.path.insert(0, C.TL)
import rover_preset as rp  # noqa: E402  (only the two name lists)


def unverified(r):
    cq = str(r["coord_quality"] or "").lower(); ss = str(r["source_status"] or "")
    return "from memory" in cq or ss.upper().startswith("FROM MEMORY") or bool(re.search(r"location[^;)]*from memory", ss, re.I))


def cell_id(lat, lon):
    return min(int(math.floor(90 - lat)), 179) * 360 + min(int(math.floor(lon + 180)), 359)


def site_rank(r, cid):
    pos = {int(i): k for k, i in enumerate(r["ids"])}
    n = int((r["rank"] > 0).sum())
    if cid not in pos or r["rank"][pos[cid]] <= 0:
        return None
    k = pos[cid]
    fp = r["final_pub"]
    better = int((fp[r["rank"] > 0] > fp[k]).sum()); equal = int((fp[r["rank"] > 0] == fp[k]).sum())
    return {"rank": int(r["rank"][k]), "pct": round(100 * r["rank"][k] / n, 2),
            "tie_aware_pct": round(100 * (better + (equal + 1) / 2) / n, 2), "tied_with": equal,
            "final": float(fp[k]), "sim": round(float(r["sim"][k]), 4), "suit": round(float(r["suit"][k]), 3),
            "slope": round(float(r["ev"][k, 0]), 3), "rough": round(float(r["ev"][k, 1]), 2),
            "twin": "M%d" % int(r["twin"][k]), "twin_slope": round(float(r["mvt"][k, 0]), 3), "twin_rough": round(float(r["mvt"][k, 1]), 2),
            "utils": {u: (None if not np.isfinite(v[k]) else round(float(v[k]), 4)) for u, v in r["utils"].items()}}


def validation(r, P):
    n = int((r["rank"] > 0).sum())
    rows = []
    roles = {}
    for nm in rp.MOBILITY_POSITIVES:
        roles[nm] = "positive"
    for nm in rp.MOBILITY_MISMATCHES:
        roles[nm] = "negative"
    used = set()
    for nm, role in roles.items():
        h = bench[bench.name.str.lower().str.replace("-", " ").str.contains(nm.lower().replace("-", " "), regex=False)]
        if not len(h):
            rows.append({"name": nm, "role": role, "found": False}); continue
        b = h.iloc[0]; used.add(b.id)
        cid = cell_id(float(b.lat), float(b.lon))
        i = cid
        reasons = []
        if not r["passed"][i]:
            for v, g in {**{k: g for k, g in P["common_gates"].items()}, **P["missions"]["rover"]["gates"]}.items():
                x = pd.to_numeric(E[v], errors="coerce").to_numpy(float)[i]
                if not np.isfinite(x): reasons.append(f"{v} missing")
                elif g.get("min") is not None and x < g["min"]: reasons.append(f"{v}={x:.3g} < {g['min']}")
                elif g.get("max") is not None and x > g["max"]: reasons.append(f"{v}={x:.3g} > {g['max']}")
        rows.append({"name": nm, "bench_id": b.id, "role": role, "found": True, "cell": "E%d" % cid, "unverified_coords": unverified(b),
                     "passes": bool(r["passed"][i]), "reasons": reasons, **(site_rank(r, cid) or {"rank": None})})
    # other usable benchmark rows (verified coordinates), informative
    other = []
    for _, b in bench.iterrows():
        if b.id in used or unverified(b):
            continue
        cid = cell_id(float(b.lat), float(b.lon))
        sr = site_rank(r, cid)
        other.append({"bench_id": b.id, "name": b["name"], "benchmark_role": b.benchmark_role, "analog_type": b.analog_type,
                      "cell": "E%d" % cid, "passes": bool(r["passed"][cid]), **({"pct": sr["pct"], "tie_aware_pct": sr["tie_aware_pct"], "rank": sr["rank"]} if sr else {"rank": None})})

    def summ(key, verified_only=False):
        sel = [x for x in rows if x["found"] and (not verified_only or not x["unverified_coords"])]
        P_ = [x.get(key) if x.get("rank") else None for x in sel if x["role"] == "positive"]
        N_ = [x.get(key) if x.get("rank") else None for x in sel if x["role"] == "negative"]
        pv = [v for v in P_ if v is not None]
        w = 0.0
        for p in P_:
            for q in N_:
                pp = 101 if p is None else p; qq = 101 if q is None else q
                w += 1.0 if pp < qq else 0.5 if pp == qq else 0.0
        return {"positives_found": len(P_), "positives_ranked": len(pv), "median_pct_ranked": round(float(np.median(pv)), 2) if pv else None,
                "positives_in_top_quartile": int(sum(v <= 25 for v in pv)), "negatives_found": len(N_),
                "negatives_ranked": int(sum(v is not None for v in N_)),
                "separation_share": round(w / (len(P_) * len(N_)), 3) if P_ and N_ else None}
    ob = [x for x in other if x.get("rank")]
    return {"n_ranked": n, "sites": rows, "summary_published_rank": summ("pct"), "summary_tie_aware": summ("tie_aware_pct"),
            "summary_verified_published_rank": summ("pct", True), "summary_verified_tie_aware": summ("tie_aware_pct", True),
            "other_usable_rows": other,
            "other_usable_positive_ranked_median_pct": round(float(np.median([x["pct"] for x in ob if str(x["benchmark_role"]).startswith("positive")])), 2) if ob else None}


res["validation_corrected"] = validation(rc, Pc)
res["validation_morning"] = validation(rm, Pm)

# recognised analogs skipped by the rule for the five (in the tied group / above the fifth, not shown)
rec_cells = {x["cell"]: x["name"] for x in res["validation_corrected"]["sites"] if x.get("found")}
rec_cells.update({x["cell"]: x["name"] for x in res["validation_corrected"]["other_usable_rows"]})
tied_ids = {"E%d" % int(rc["ids"][k]) for k in tied}
res["recognised_in_tied_group"] = {c: n for c, n in rec_cells.items() if c in tied_ids}

# ------------------------------------------------------------------ Bardenas and Tabernas
bt_ = {}
for nm in ("Bardenas", "Tabernas"):
    s = [x for x in res["validation_corrected"]["sites"] if x["name"] == nm][0]
    sm = [x for x in res["validation_morning"]["sites"] if x["name"] == nm][0]
    i = int(s["cell"][1:])
    bt_[nm] = {"cell": s["cell"], "corrected": s, "morning": sm,
               "rock_or_bare_frac": float(E["raw_rock_or_bare_frac"][i]), "land_share": float(E["raw_mask_fraction"][i]),
               "lc_dominant_cci": float(E["raw_lc_dominant_cci_code"][i])}
ok = rc["rank"] > 0
res["paired_suitability_quantiles_0_5_25_50_75_95_100"] = [round(float(x), 2) for x in np.percentile(rc["suit"][ok], [0, 5, 25, 50, 75, 95, 100])]
res["paired_rock_or_bare_quantiles"] = [round(float(x), 3) for x in np.nanpercentile(E["raw_rock_or_bare_frac"][rc["pi"][ok]].astype(float), [5, 25, 50, 75, 95])]
res["bardenas_tabernas"] = bt_
res["moon_zone_quantiles_0_5_25_50_75_95_100"] = {v: [round(float(x), 3) for x in np.nanpercentile(D[v]["MOON"][zi], [0, 5, 25, 50, 75, 95, 100])] for v in ("slope_deg", "roughness_m")}

# ------------------------------------------------------------------ slope minimum 0.5 deg: with and without
def no_min(P):
    P = copy.deepcopy(P)
    P["missions"]["rover"]["gates"]["slope_300m_deg"]["min"] = None
    return P


def no_sigma(P):
    P = copy.deepcopy(P)
    for v in P["missions"]["rover"]["sim"]["variables"]:
        v.pop("uncertainty_scale", None)
    return P


def slope_min_study(P):
    a = R.run(T, D, P); b = R.run(T, D, no_min(P))
    ida = set(map(int, a["ids"])); idb = set(map(int, b["ids"]))
    added = np.array([int(i) not in ida for i in b["ids"]])
    top50a = [int(a["ids"][k]) for k in np.argsort(np.where(a["rank"] > 0, a["rank"], 10 ** 9), kind="stable")[:50]]
    ob = np.argsort(np.where(b["rank"] > 0, b["rank"], 10 ** 9), kind="stable")[:50]
    top50b = [int(b["ids"][k]) for k in ob]
    lc = E["raw_lc_dominant_cci_code"].to_numpy(float)
    sn = E["raw_snow_ice_frac"].to_numpy(float)

    def stats(r, top50):
        ok = r["rank"] > 0
        u, c = np.unique(r["twin"][ok], return_counts=True)
        t50 = np.array(top50)
        return {"passing": int(len(r["pi"])), "paired": int(ok.sum()), "distinct_twins": int(len(u)), "largest_twin_share": round(float(c.max() / ok.sum()), 4),
                "largest_twin": "M%d" % int(u[np.argmax(c)]), "largest_twin_points": int(c.max()),
                "top5_full_ranking": top50[:5], "water_cci210_in_top50": int((lc[t50] == 210).sum()),
                "ice_in_top50_snow_ge_0_5": int((np.nan_to_num(sn[t50], nan=-1) >= 0.5).sum()), "cci220_in_top50": int((lc[t50] == 220).sum()),
                "land_lt_0_5_in_top50": int((pd.to_numeric(E["mask_fraction"], errors="coerce").to_numpy(float)[t50] < 0.5).sum()),
                "n_final_eq_top": int((r["final_pub"][ok] == np.nanmax(r["final_pub"])).sum()),
                "five_shipped_rule": R.five_ids(r, P)}
    addi = b["pi"][added]
    out = {"with_min": stats(a, top50a), "without_min": stats(b, top50b),
           "added": int(added.sum()), "added_snow_or_ice_cci220_or_snow_ge_0_5": int(((lc[addi] == 220) | (np.nan_to_num(sn[addi], nan=-1) >= 0.5)).sum()),
           "added_cci220": int((lc[addi] == 220).sum()), "added_water_cci210": int((lc[addi] == 210).sum()),
           "added_bare_200_202": int(((lc[addi] >= 200) & (lc[addi] <= 202)).sum()),
           "top50_overlap": len(set(top50a) & set(top50b)), "top50_added_points": int(sum(i not in ida for i in top50b)),
           "top50_added_slope_lt_0_5": int(sum((i not in ida) and float(E["slope_300m_deg"][i]) < 0.5 for i in top50b))}
    va = validation(a, P); vb = validation(b, no_min(P))
    out["validation_pct_with"] = {x["name"]: x.get("pct") for x in va["sites"] if x.get("found")}
    out["validation_pct_without"] = {x["name"]: x.get("pct") for x in vb["sites"] if x.get("found")}
    out["validation_tie_aware_with"] = {x["name"]: x.get("tie_aware_pct") for x in va["sites"] if x.get("found")}
    out["validation_tie_aware_without"] = {x["name"]: x.get("tie_aware_pct") for x in vb["sites"] if x.get("found")}
    out["summary_with"] = va["summary_tie_aware"]; out["summary_without"] = vb["summary_tie_aware"]
    out["summary_verified_with"] = va["summary_verified_tie_aware"]; out["summary_verified_without"] = vb["summary_verified_tie_aware"]
    return out


res["slope_min_study_rule_1123_tolerance_score"] = slope_min_study(no_sigma(Pc))   # reproduces DECISIONS.md 11:23 table
res["slope_min_study_corrected"] = slope_min_study(Pc)                             # the shipped rule

# ------------------------------------------------------------------ item 3 fallback
if MDIR:
    Bm = R.bundle_rover(MDIR)
    cm = R.compare(rm, Bm)
    om = np.argsort(np.where(np.isfinite(Bm["rank"]), Bm["rank"], 1e9))[:5]
    res["fallback"] = {"compare": cm, "five_mine": res["five_morning_ids"], "five_bundle": [int(Bm["ids"][k]) for k in om]}
    res["fallback"]["all_equal"] = all(v["mismatch"] == 0 and v.get("nan_pattern_mismatch", 0) == 0 for k, v in cm.items() if isinstance(v, dict)) \
        and cm["same_passing_set"] and res["fallback"]["five_mine"] == res["fallback"]["five_bundle"]


# ------------------------------------------------------------------ suitability saturation (team lead 12:10, point 1)
okp = rc["rank"] > 0
soft = Pc["missions"]["rover"]["soft"]
sat = {"n_suit_100": int((C.pyround(rc["suit"], 2) == 100).sum()), "n_suit_100_full": int((rc["suit"] >= 100 - 1e-9).sum()), "per_criterion": {}}
tmask = rc["final_pub"] == np.nanmax(rc["final_pub"])
for v, sp in soft.items():
    u = rc["utils"][v]
    x = pd.to_numeric(E[v], errors="coerce").to_numpy(float)[rc["pi"]]
    sat["per_criterion"][v] = {"weight": sp["weight"], "bad": sp["bad"], "good": sp["good"],
                               "share_passing_at_utility_1": round(float(np.mean(u >= 1 - 1e-12)), 4), "n_passing_at_1": int((u >= 1 - 1e-12).sum()),
                               "tied_group_all_at_1": bool((u[tmask] >= 1 - 1e-12).all()), "tied_group_n_at_1": int((u[tmask] >= 1 - 1e-12).sum()),
                               "tied_group_value_range": [round(float(np.nanmin(x[tmask])), 3), round(float(np.nanmax(x[tmask])), 3)]}
allone = np.ones(len(rc["pi"]), bool)
for v in soft:
    allone &= rc["utils"][v] >= 1 - 1e-12
sat["n_all_three_utilities_1"] = int(allone.sum())
sat["tied_group_equals_all_utilities_1_and_sim_100"] = bool(set(np.flatnonzero(tmask)) == set(np.flatnonzero(allone & (C.pyround(rc["sim"], 2) == 100))))
sat["n_all_utilities_1_but_sim_lt_100"] = int((allone & (C.pyround(rc["sim"], 2) < 100)).sum())
sat["share_of_suitability_eq_100_among_sim_100"] = None
res["suitability_saturation"] = sat
# Bardenas / Tabernas criterion by criterion (corrected)
for nm, v in res["bardenas_tabernas"].items():
    i = int(v["cell"][1:]); k = int(np.flatnonzero(rc["ids"] == i)[0])
    rows = {}
    lost = 0.0
    for c, sp in soft.items():
        x = float(pd.to_numeric(E[c], errors="coerce").to_numpy(float)[i]); u = float(rc["utils"][c][k])
        rows[c] = {"value": round(x, 3), "bad": sp["bad"], "good": sp["good"], "utility": round(u, 4), "weight": sp["weight"],
                   "points_lost_of_suitability": round(100 * sp["weight"] * (1 - u), 2)}
        lost += 100 * sp["weight"] * (1 - u)
    v["criterion_by_criterion"] = rows
    v["suitability_check"] = round(100 - lost, 2)
    v["points_below_top_final"] = round(100 - float(rc["final_pub"][k]), 2)
    v["n_ranked_better"] = int((rc["final_pub"][okp] > rc["final_pub"][k]).sum())
# what each rule of the five excludes (team lead 12:10, point 2)
ice = np.nan_to_num(rc["snow"], nan=-1) >= 0.5
wat = np.nan_to_num(rc["land"], nan=1) < 0.5
ex = {"tied_n": int(tmask.sum()), "tied_ice": int((tmask & ice).sum()), "tied_land_lt_half": int((tmask & wat).sum()),
      "tied_both": int((tmask & ice & wat).sum()), "ranked_ice": int((okp & ice).sum()), "ranked_land_lt_half": int((okp & wat).sum()),
      "tied_land_lt_half_ids": ["E%d" % int(rc["ids"][k]) for k in np.flatnonzero(tmask & wat)],
      "tied_land_lt_half_lc210": int(((E["raw_lc_dominant_cci_code"].to_numpy(float)[rc["pi"]] == 210) & tmask & wat).sum())}
# 2-degree rule: inside the spread rule, how many picks were constrained? count tied eligible points within 2 deg of a chosen one
el = np.flatnonzero(tmask & ~ice & ~wat)
ch = fc
near = [int(k) for k in el if k not in ch and min(float(R.gc_deg(rc["lat"][k], rc["lon"][k], rc["lat"][j], rc["lon"][j])) for j in ch) < 2.0]
ex["eligible_tied_within_2deg_of_a_chosen"] = len(near)
ex["min_sep_of_five_deg"] = res["five_corrected_min_sep_deg"]
ex["two_degree_rule_binding"] = bool(res["five_corrected_min_sep_deg"] < 2.0 + 1e-9) or False
r_nosep = R.five(rc, Pc, {**Pc["rover_top5"], "min_separation_deg": 0.0})[0]
ex["five_without_2deg_rule"] = [int(rc["ids"][k]) for k in r_nosep]
r_noskip = R.five(rc, Pc, {**Pc["rover_top5"], "skips": {}})[0]
ex["five_without_ice_and_land_skips"] = [int(rc["ids"][k]) for k in r_noskip]
r_noland = R.five(rc, Pc, {**Pc["rover_top5"], "skips": {"ice": Pc["rover_top5"]["skips"]["ice"]}})[0]
ex["five_without_land_skip"] = [int(rc["ids"][k]) for k in r_noland]
r_noice = R.five(rc, Pc, {**Pc["rover_top5"], "skips": {"water": Pc["rover_top5"]["skips"]["water"]}})[0]
ex["five_without_ice_skip"] = [int(rc["ids"][k]) for k in r_noice]
res["five_rule_exclusions"] = ex

res["seconds"] = round(time.time() - t0)
json.dump(res, open(os.path.join(R.OUT, "ra_rover_audit.json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o), ensure_ascii=False)
print("written out/ra_rover_audit.json", res["seconds"], "s")
for k in ("funnel", "compare_corrected_vs_bundle", "general_corrected", "general_morning", "five_corrected_ids", "five_bundle_ids", "five_corrected_info",
          "five_corrected_alternative_rules", "tied_group", "recognised_in_tied_group", "pairs_both_within_sigma"):
    print(k, json.dumps(res.get(k), default=str)[:1500])
for k in ("difference_table_corrected",):
    for x in res[k]: print(x)
for m in ("corrected", "morning"):
    v = res["validation_" + m]
    print(m, "ALL", v["summary_published_rank"], v["summary_tie_aware"])
    print(m, "VERIFIED", v["summary_verified_published_rank"], v["summary_verified_tie_aware"])
    print("   ", {x["name"]: (x.get("pct"), x.get("tie_aware_pct")) for x in v["sites"] if x.get("found")})
for k in ("slope_min_study_rule_1123_tolerance_score", "slope_min_study_corrected"):
    s = res[k]; print(k, json.dumps({kk: s[kk] for kk in s if not kk.startswith("validation_tie")}, default=str)[:3000])
print("SAT", json.dumps(res["suitability_saturation"]))
print("BT", json.dumps({k: {kk: v[kk] for kk in ("criterion_by_criterion", "suitability_check", "points_below_top_final", "n_ranked_better")} for k, v in res["bardenas_tabernas"].items()}))
print("EXCL", json.dumps(res["five_rule_exclusions"]))
if MDIR:
    print("fallback all_equal", res["fallback"]["all_equal"])
