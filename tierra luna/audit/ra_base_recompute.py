"""Re-audit Lunar base, items 2, 3 and 8: own recomputation of both criteria sets, compared cell by
cell with the bundle in the checkout (corrected) and with the morning bundle (audited_morning).
Run: python "tierra luna/audit/ra_base_recompute.py" [morning_bundle_folder]
 -> out/ra_base_recompute.json"""
import json, os, sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_base_common as R
import p5_common as C

MORNING = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("RA_MORNING_BUNDLE")


def funnel_reasons(E, P):
    """Exclusion counts, gate by gate (each counted on its own, and the first failing in order)."""
    mm = P["missions"][R.M]
    gates = {k: g for k, g in P["common_gates"].items() if "EARTH" in P["common_bodies"].get(k, ["EARTH", "MOON"])}
    gates.update(mm["gates"])
    out, alone = {}, {}
    alive = np.ones(len(E), bool)
    for v in mm["require_present"]:
        okv = C.present(E[v]); alone[f"present:{v}"] = int((~okv).sum())
    for v, g in gates.items():
        P2 = {**P, "common_gates": {}, "missions": {R.M: {**mm, "require_present": [], "gates": {v: g}}}}
        okv = C.gate_pass(E, "EARTH", R.M, P2)
        alone[f"gate:{v}"] = int((~okv).sum())
    return alone


def diff_table(r):
    rows = []
    has = r["twin"] >= 0
    sim = r["sim_cfg"]
    for q, v in enumerate(r["vars"]):
        vc = [x for x in sim["variables"] if x["variable"] == v][0]
        d = r["diff"][has, q]
        d = d[np.isfinite(d)]
        bound = float(vc["tolerance"]) * float(R.C.load_params()["mult"][vc["role"]])
        rows.append({"variable": v, "scale": vc.get("scale", "real"), "role": vc["role"], "tolerance": vc["tolerance"],
                     "bound": bound, "n": int(len(d)), "median": float(np.median(d)), "p90": float(np.percentile(d, 90)),
                     "max": float(d.max()), "all_within_bound": bool((d <= bound + 1e-9).all())})
    return rows


def describe(r, P, E, raw, k=10):
    o = R.ranked_order(r)[:k]
    res = []
    for i in o:
        cid = int(r["pass_ids"][i])
        rw = raw.set_index("id").loc[cid]
        res.append({"rank": int(r["rank"][i]), "earth": cid, "lat": float(rw["lat_deg"]), "lon": float(rw["lon_deg"]),
                    "twin": int(r["twin"][i]), "similarity": round(float(r["sim"][i]), 2), "suitability": round(float(r["suit"][i]), 2),
                    "final": float(r["final_pub"][i]), "amp_k": float(rw["lst_diurnal_amp_k"]), "tmin_c": float(rw["tmin_c"]),
                    "mask_fraction": float(rw["mask_fraction"]), "snow_ice_frac": float(rw["snow_ice_frac"])})
    return res


def main():
    t0 = time.time()
    raw = R.load_raw_earth()
    rep = {}
    cache = {}
    for set_name in ("corrected", "audited_morning"):
        P, ec, sb = R.params_for_set(set_name)
        T = C.load_tables(P); D = C.derived(T, P)
        r = C.run_mission(T, D, R.M, P)
        r["sim_cfg"] = P["missions"][R.M]["sim"]
        five, skipped = R.select_five(r, P, T["EARTH"], raw, return_skips=True)
        cache[set_name] = r
        e = {"soft": P["missions"][R.M]["soft"], "soft_weight_sum": sum(float(s["weight"]) for s in P["missions"][R.M]["soft"].values()),
             "top5_rule": P["_top5"], "funnel_exclusions_each_alone": funnel_reasons(T["EARTH"], P),
             "passed": int(r["passed"].sum()), "paired": int((r["twin"] >= 0).sum()),
             "distinct_twins": int(len(set(r["twin"][r["twin"] >= 0].tolist()))), "zone_cells": r["zone_n"],
             "five": five, "skipped_before_fifth": skipped, "top10": describe(r, P, T["EARTH"], raw),
             "difference_table": diff_table(r)}
        b_folder = C.BUNDLE if set_name == "corrected" else MORNING
        if b_folder and os.path.isdir(b_folder):
            b = R.bundle_mission_at(b_folder)
            e["vs_bundle"] = {"folder": b_folder, **R.compare(r, b), "bundle_top5": R.bundle_top5(b_folder)}
        rep[set_name] = e
        print(set_name, json.dumps({k: v for k, v in e.items() if k in ("passed", "paired", "distinct_twins", "five", "vs_bundle")}, default=str), flush=True)
    # twins and similarities identical between the two sets?
    a, m = cache["corrected"], cache["audited_morning"]
    same_ids = np.array_equal(a["pass_ids"], m["pass_ids"])
    rep["corrected_vs_morning"] = {
        "same_pass_ids": bool(same_ids),
        "twin_differences": int((a["twin"] != m["twin"]).sum()) if same_ids else None,
        "similarity_max_diff": float(np.nanmax(np.abs(a["sim"] - m["sim"]))) if same_ids else None,
        "suitability_changed_points": int((np.abs(C.pyround(a["suit"], 2) - C.pyround(m["suit"], 2)) > 0).sum()) if same_ids else None,
        "rank_changed_points": int((a["rank"] != m["rank"]).sum()) if same_ids else None,
        "top50_overlap": len(set(C.top_ids(a, 50)) & set(C.top_ids(m, 50))),
    }
    rep["seconds"] = round(time.time() - t0, 1)
    print(json.dumps(rep["corrected_vs_morning"]))
    print(R.dump(rep, "ra_base_recompute.json"))


if __name__ == "__main__":
    main()
