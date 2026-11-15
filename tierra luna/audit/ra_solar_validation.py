"""Re-audit Solar panels, item 7: where the recognised sites (data/benchmark/validation_sites_solar.csv)
come out, corrected vs this morning, overall and WITHIN EACH SITE'S OWN LATITUDE ROW.

    python -I ra_solar_validation.py [set_a=corrected] [set_b=audited_morning]

Own code path (ra_solar_common): ranks recomputed from the tables. Rank of a passing cell without a
twin: after the paired ones, by suitability (desc), ties by id (missions.json funnel step 6, as r4).
Percentile = 100*rank/passing (lower = better). Within-row percentile = 100 * share of passing cells
of the same 1-degree latitude row ranked better (r4 definition), and a second within-row figure that
uses the SUITABILITY alone (share of the same-row passing cells with higher suitability), which is the
direct answer to "is the suitability better than latitude alone" (latitude is constant within a row).
Separation share = fraction of positive-negative pairs in which the positive ranks better (eliminated
cells share the worst rank; ties 1/2). Writes out/ra_solar_validation.json and .csv.
"""
import csv
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_solar_common as R  # noqa: E402

SITES = os.path.join(R.TL, "data", "benchmark", "validation_sites_solar.csv")


def read_sites():
    rows = [ln for ln in open(SITES, encoding="utf-8") if not ln.startswith("#")]
    return list(csv.DictReader(rows))


def cell_id(lat, lon):
    return min(int(math.floor(90 - lat)), 179) * 360 + min(int(math.floor(lon + 180)), 359)


def full_rank(r):
    n_ranked = int((r["rank"] > 0).sum())
    rank = {int(i): int(k) for i, k in zip(r["pass_ids"], r["rank"]) if k > 0}
    unp = sorted((-float(s), int(i)) for i, s, k in zip(r["pass_ids"], r["suit"], r["rank"]) if k <= 0)
    for j, (_, i) in enumerate(unp):
        rank[i] = n_ranked + 1 + j
    return rank


def evaluate(set_name):
    P, _, _, _ = R.load_params_set(set_name)
    T, _ = R.tables(P)
    E = T["EARTH"]
    r = R.run(P)
    n = int(r["passed"].sum())
    rank = full_rank(r)
    suit = {int(i): float(s) for i, s in zip(r["pass_ids"], r["suit"])}
    pos = {int(i): j for j, i in enumerate(E["id"].to_numpy())}
    rows_of = {}
    for i in rank:
        rows_of.setdefault(i // 360, []).append(i)
    out = []
    for s in read_sites():
        lat, lon = float(s["lat"]), float(s["lon"])
        c = cell_id(lat, lon)
        j = pos[c]
        x = {"site_id": s["site_id"], "role": s["role"], "name": s["name"], "cell": "E%d" % c, "passes": c in rank,
             "land_share": None if not np.isfinite(E["__mask_fraction"].iloc[j]) else round(float(E["__mask_fraction"].iloc[j]), 3),
             "clear_frac_isccp": None if not np.isfinite(E["clear_frac_isccp"].iloc[j]) else round(float(E["clear_frac_isccp"].iloc[j]), 3),
             "irradiance_kwh_m2_day": None if not np.isfinite(float(E["irradiance_kwh_m2_day"].iloc[j] if E["irradiance_kwh_m2_day"].iloc[j] == E["irradiance_kwh_m2_day"].iloc[j] else np.nan)) else round(float(E["irradiance_kwh_m2_day"].iloc[j]), 3)}
        if c in rank:
            same = rows_of[c // 360]
            x.update(rank=rank[c], rank_pct=round(100 * rank[c] / n, 1), suitability=round(suit[c], 2),
                     twin=None if r["twin"][list(r["pass_ids"]).index(c)] < 0 else "M%d" % r["twin"][list(r["pass_ids"]).index(c)],
                     row_passing=len(same),
                     rank_pct_within_row=round(100 * sum(rank[o] < rank[c] for o in same) / len(same), 1),
                     suit_pct_within_row=round(100 * sum(suit[o] > suit[c] for o in same) / len(same), 1))
        else:
            reasons = []
            x.update(rank=None, rank_pct=None, suitability=None, twin=None, row_passing=len(rows_of.get(c // 360, [])),
                     rank_pct_within_row=None, suit_pct_within_row=None)
        out.append(x)

    def summ(role, key):
        g = [x for x in out if x["role"] == role]
        v = [x[key] for x in g if x[key] is not None]
        return {"n": len(g), "passing": sum(x["passes"] for x in g), "median_pct_passing": None if not v else round(float(np.median(v)), 1),
                "median_pct_eliminated_as_100": round(float(np.median([x[key] if x[key] is not None else 100.0 for x in g])), 1),
                "in_top_quartile": sum(1 for x in v if x <= 25.0)}

    def sep(key):
        Pv = [x[key] if x[key] is not None else 101.0 for x in out if x["role"] == "positive"]
        Nv = [x[key] if x[key] is not None else 101.0 for x in out if x["role"] == "negative"]
        w = sum(1.0 if p < q else 0.5 if p == q else 0.0 for p in Pv for q in Nv)
        return round(w / (len(Pv) * len(Nv)), 3)
    return {"criteria_set": set_name, "passing": n, "paired": int((r["rank"] > 0).sum()),
            "overall": {"positives": summ("positive", "rank_pct"), "negatives": summ("negative", "rank_pct"), "separation": sep("rank_pct")},
            "within_row_rank": {"positives": summ("positive", "rank_pct_within_row"), "negatives": summ("negative", "rank_pct_within_row"),
                                "separation": sep("rank_pct_within_row")},
            "within_row_suitability": {"positives": summ("positive", "suit_pct_within_row"), "negatives": summ("negative", "suit_pct_within_row"),
                                       "separation": sep("suit_pct_within_row")},
            "sites": out}


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "corrected"
    b = sys.argv[2] if len(sys.argv) > 2 else "audited_morning"
    res = {"sites_file": SITES, "note_within_row": "latitude is constant within a row: a within-row percentile near 50 means the model says nothing beyond latitude; below 50 = better than latitude alone",
           a: evaluate(a), b: evaluate(b)}
    p = R.jdump(res, "ra_solar_validation.json")
    with open(os.path.join(R.OUT, "ra_solar_validation.csv"), "w", newline="", encoding="utf-8") as fh:
        keys = ["criteria_set"] + list(res[a]["sites"][0].keys())
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        for s in (a, b):
            for x in res[s]["sites"]:
                wr.writerow({"criteria_set": s, **x})
    for s in (a, b):
        v = res[s]
        print(s, "passing", v["passing"])
        for k in ("overall", "within_row_rank", "within_row_suitability"):
            print("  ", k, v[k])
    print("%-5s %-3s %-34s %-7s | %s" % ("site", "rol", "name", "cell", "  corrected: pct row suitrow | morning: pct row suitrow"))
    for xa, xb in zip(res[a]["sites"], res[b]["sites"]):
        print("%-5s %-3s %-34s %-7s | %6s %6s %6s | %6s %6s %6s  clear=%s" % (xa["site_id"], xa["role"][:3], xa["name"][:34], xa["cell"],
              xa["rank_pct"], xa["rank_pct_within_row"], xa["suit_pct_within_row"], xb["rank_pct"], xb["rank_pct_within_row"], xb["suit_pct_within_row"], xa["clear_frac_isccp"]))
    print("wrote", p)


if __name__ == "__main__":
    main()
