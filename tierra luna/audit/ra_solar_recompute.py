"""Re-audit Solar panels, items 2 and 3: recompute the mission from the tables and a criteria set
with the independent code path (ra_solar_common / p5_common) and compare with a bundle cell by cell.

    python -I ra_solar_recompute.py <criteria set> <bundle folder> <tag>

Writes out/ra_solar_recompute_<tag>.json. Exit code 0 always; the JSON says PASS/FAIL per check.
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_solar_common as R  # noqa: E402
import p5_common as C  # noqa: E402


def own_reasons(E, P, m="solar"):
    """Per land cell: set of reason codes (variable:kind) by my own gate evaluation."""
    mm = P["missions"][m]
    gates = {k: g for k, g in P["common_gates"].items() if "EARTH" in P["common_bodies"].get(k, ["EARTH", "MOON"])}
    gates.update(mm["gates"])
    codes = {}
    for v in set(mm["require_present"]):
        miss = ~C.present(E[v])
        codes[v + ":missing"] = miss
    for v, g in gates.items():
        s = E[v]
        if "min" in g or "max" in g:
            x = pd.to_numeric(s, errors="coerce").to_numpy(float)
            codes[v + ":missing"] = codes.get(v + ":missing", np.zeros(len(E), bool)) | ~np.isfinite(x)
            if g.get("min") is not None:
                codes[v + ":below_min"] = np.isfinite(x) & (np.where(np.isfinite(x), x, 0) < g["min"])
            if g.get("max") is not None:
                codes[v + ":above_max"] = np.isfinite(x) & (np.where(np.isfinite(x), x, 0) > g["max"])
        else:
            t = s.astype(str).str.strip().str.lower()
            pr = (s.notna() & ~t.isin(["", "nan"])).to_numpy()
            codes[v + ":missing"] = codes.get(v + ":missing", np.zeros(len(E), bool)) | ~pr
            if g.get("exclude"):
                codes[v + ":excluded"] = pr & t.isin([a.lower() for a in g["exclude"]]).to_numpy()
            if g.get("allow"):
                codes[v + ":not_allowed"] = pr & ~t.isin([a.lower() for a in g["allow"]]).to_numpy()
    return codes


def q(a, p):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    return None if not len(a) else round(float(np.percentile(a, p)), 4)


def main():
    set_name, bdir, tag = sys.argv[1], os.path.abspath(sys.argv[2]), sys.argv[3]
    P, ec, name, sd = R.load_params_set(set_name)
    T, D = R.tables(P)
    E = T["EARTH"]
    r = R.run(P)
    B = R.bundle_solar(bdir)
    res = {"criteria_set": name, "bundle": bdir, "soft": P["missions"]["solar"]["soft"],
           "similarity_variables": P["missions"]["solar"]["sim"]["variables"], "zone": P["missions"]["solar"]["sim"]["zone"],
           "top5_rule": P["top5"], "checks": {}}
    ck = res["checks"]
    # ---- funnel
    land = B["base"]["id"].astype(int)
    pos = {int(i): j for j, i in enumerate(E["id"].to_numpy())}
    li = np.array([pos[i] for i in land])
    passed_land = r["passed"][li]
    b_pass = B["fail_bits"] == 0
    ck["funnel_passing"] = {"own": int(passed_land.sum()), "bundle": int(b_pass.sum()), "mismatch_cells": int((passed_land != b_pass).sum()),
                            "own_total_incl_nonland": int(r["passed"].sum())}
    codes = own_reasons(E, P)
    bits = {rc["code"]: rc["bit"] for rc in B["mdef"]["reason_codes"]}
    rtab = []
    for c, bit in sorted(bits.items(), key=lambda x: x[1]):
        bset = (B["fail_bits"].astype(np.int64) >> bit) & 1 == 1
        own = codes.get(c)
        rtab.append({"code": c, "bit": bit, "bundle_cells": int(bset.sum()),
                     "own_cells": None if own is None else int(own[li].sum()),
                     "mismatch": None if own is None else int((own[li] != bset).sum())})
    ck["reasons"] = rtab
    # ---- per passing point
    bmap = {int(i): k for k, i in enumerate(B["ids"])}
    k_b = np.array([bmap.get(int(i), -1) for i in r["pass_ids"]])
    ck["passing_ids_equal"] = bool((k_b >= 0).all() and len(k_b) == len(B["ids"]))
    kb = np.maximum(k_b, 0)

    def cmp(own, pub, tol):
        own = np.asarray(own, float)
        pub = np.asarray(pub, float)
        both_nan = ~np.isfinite(own) & ~np.isfinite(pub)
        d = np.abs(own - pub)
        bad = ~both_nan & ~(np.isfinite(d) & (d <= tol))
        return {"n": int(len(own)), "mismatch": int(bad.sum()), "max_abs_diff": None if not np.isfinite(d).any() else float(np.nanmax(d)),
                "first_bad": [int(r["pass_ids"][i]) for i in np.flatnonzero(bad)[:5]]}
    ck["suitability"] = cmp(C.pyround(r["suit"], 2), B["suitability"][kb], 0.0051)
    ck["similarity"] = cmp(C.pyround(r["sim"], 2), B["similarity"][kb], 0.0051)
    ck["final"] = cmp(r["final_pub"], B["final"][kb], 0.0051)
    own_rank = np.where(r["rank"] > 0, r["rank"], np.nan)
    ck["rank"] = cmp(own_rank, B["rank"][kb], 0)
    ck["twin"] = cmp(np.where(r["twin"] >= 0, r["twin"], np.nan), B["twin"][kb], 0)
    for j, v in enumerate(r["vars"]):
        if "s." + v in B:
            ck["score_" + v] = cmp(r["scores"][:, j], B["s." + v][kb], 0.0051 if np.nanmax(B["s." + v]) > 1.5 else 0.00051)
    ck["paired"] = int((r["twin"] >= 0).sum())
    ck["distinct_twins"] = int(len(set(r["twin"][r["twin"] >= 0].tolist())))
    # ---- difference table on surviving pairs + bounds asserted
    has = r["twin"] >= 0
    dt = []
    sim = P["missions"]["solar"]["sim"]["variables"]
    for j, v in enumerate(r["vars"]):
        x = sim[j]
        bound = float(x["tolerance"]) * float(P["mult"][x["role"]])
        dd = r["diff"][has, j]
        row = {"variable": v, "role": x["role"], "weight": x["weight"], "tolerance": x["tolerance"], "bound": bound,
               "median": q(dd, 50), "p90": q(dd, 90), "max": q(dd, 100), "pairs_over_bound": int(np.sum(dd > bound + 1e-9)),
               "pairs_with_value": int(np.isfinite(dd).sum())}
        if B["pairs"] is not None and v + ".diff" in B["pairs"]:
            pp = B["pairs"]
            lo = pp["list_order"] if "list_order" in pp else None
            bd = pp[v + ".diff"]
            row["bundle_pairs_file"] = {"median": q(bd, 50), "p90": q(bd, 90), "max": q(bd, 100), "n_finite": int(np.isfinite(bd).sum())}
        dt.append(row)
    res["difference_table"] = dt
    ck["bounds_all_pairs_ok"] = all(x["pairs_over_bound"] == 0 for x in dt)
    # ---- five
    kept, skipped = R.five(r, P, with_skipped=True)
    own5 = [{"earth_id": int(r["pass_ids"][qq]), "rank": int(r["rank"][qq]), "twin": int(r["twin"][qq]),
             "similarity": round(float(r["sim"][qq]), 2), "suitability": round(float(r["suit"][qq]), 2), "final": float(r["final_pub"][qq])}
            for qq in kept]
    res["five_own"] = own5
    res["five_skipped_before_fifth"] = skipped
    t5 = B["mdef"].get("top5")
    if t5:
        b5 = [int(x) for x in t5["ids"]]
        ck["five_equal"] = {"own": [x["earth_id"] for x in own5], "bundle": b5, "bundle_ranks": t5.get("overall_ranks"),
                            "equal": [x["earth_id"] for x in own5] == b5 and [x["rank"] for x in own5] == t5.get("overall_ranks")}
    else:
        bt = sorted([(B["rank"][k], int(B["ids"][k])) for k in range(len(B["ids"])) if np.isfinite(B["rank"][k])])[:5]
        ck["five_equal"] = {"own": [x["earth_id"] for x in own5], "bundle_ranks_1_5": [i for _, i in bt], "note": "bundle has no missions.json top5: five = ranks 1-5",
                            "equal": [x["earth_id"] for x in own5] == [i for _, i in bt]}
    # ---- verdict of the comparison
    bad = []
    for k2, v in ck.items():
        if isinstance(v, dict) and v.get("mismatch"):
            bad.append(k2)
    if ck["funnel_passing"]["mismatch_cells"]:
        bad.append("funnel")
    bad += ["reason:" + x["code"] for x in rtab if x["mismatch"]]
    if not ck["bounds_all_pairs_ok"]:
        bad.append("bounds")
    if not ck["five_equal"]["equal"]:
        bad.append("five")
    res["mismatches"] = bad
    res["status"] = "PASS" if not bad else "FAIL"
    p = R.jdump(res, "ra_solar_recompute_%s.json" % tag)
    print(res["status"], bad)
    print({k2: (v if not isinstance(v, (dict, list)) else {kk: vv for kk, vv in v.items() if kk in ("mismatch", "max_abs_diff", "own", "bundle", "equal")} if isinstance(v, dict) else len(v)) for k2, v in ck.items()})
    for x in dt:
        print(x)
    print(own5)
    print("wrote", p)


if __name__ == "__main__":
    main()
