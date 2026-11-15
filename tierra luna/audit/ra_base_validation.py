"""Re-audit Lunar base, item 7: where the recognised sites of
data/benchmark/validation_sites_lunar_base.csv come out under each criteria set, own code path.
Convention of research_4 (r4_rank_sites.py) so the figures are comparable: cell id = floor(90-lat)*360
+ floor(lon+180); rank = position by final among the paired, then the passing points without a twin by
suitability; percentile = 100*rank/passing (lower = better); a cell that fails the funnel takes the worst
rank (passing+1); separation = share of positive-negative pairs where the positive ranks better (ties 1/2);
top quartile = rank <= passing/4. Also the best rank in the 3x3 block (diagnostic).
Run: python "tierra luna/audit/ra_base_validation.py" -> out/ra_base_validation.json"""
import csv, io, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_base_common as R
import p5_common as C

SITES = os.path.join(R.TL, "data", "benchmark", "validation_sites_lunar_base.csv")


def read_sites():
    txt = "".join(l for l in open(SITES, encoding="utf-8") if not l.startswith("#"))
    return list(csv.DictReader(io.StringIO(txt)))


def cell_id(lat, lon):
    return min(int(math.floor(90.0 - lat)), 179) * 360 + min(int(math.floor(lon + 180.0)), 359)


def full_rank(r):
    ids = r["pass_ids"]
    paired = np.isfinite(r["final_pub"])
    o1 = np.lexsort((ids[paired], -r["final_pub"][paired]))
    s = np.array([round(float(x), 2) for x in r["suit"]])
    up = ~paired
    o2 = np.lexsort((ids[up], -s[up]))
    order = list(ids[paired][o1]) + list(ids[up][o2])
    return {int(c): k + 1 for k, c in enumerate(order)}


def one_set(set_name, sites, raw):
    P, _, _ = R.params_for_set(set_name)
    T = C.load_tables(P); D = C.derived(T, P)
    r = C.run_mission(T, D, R.M, P)
    rk = full_rank(r)
    n = len(r["pass_ids"])
    pos = {int(i): k for k, i in enumerate(r["pass_ids"])}
    rows = []
    for s in sites:
        cid = cell_id(float(s["lat"]), float(s["lon"]))
        rr = rk.get(cid, n + 1)
        blk = [rk.get(cid + dr * 360 + dc, n + 1) for dr in (-1, 0, 1) for dc in (-1, 0, 1)]
        k = pos.get(cid)
        rows.append({"site_id": s["site_id"], "role": s["role"], "name": s["name"], "cell": cid, "passes": cid in rk,
                     "paired": bool(k is not None and r["twin"][k] >= 0), "rank": rr if cid in rk else None,
                     "pct": round(100 * rr / n, 1) if cid in rk else None, "best_3x3_pct": round(100 * min(blk) / n, 1),
                     "final": float(r["final_pub"][k]) if k is not None and np.isfinite(r["final_pub"][k]) else None})
    pos_r = [x["rank"] or n + 1 for x in rows if x["role"] == "positive"]
    neg_r = [x["rank"] or n + 1 for x in rows if x["role"] == "negative"]
    sep = np.mean([1.0 if a < b else 0.5 if a == b else 0.0 for a in pos_r for b in neg_r])
    pp = [x["pct"] for x in rows if x["role"] == "positive" and x["pct"] is not None]
    return {"passing": n, "rows": rows, "positives": len(pos_r), "positives_passing": len(pp),
            "positives_top_quartile": int(sum(1 for a in pos_r if a <= n / 4)),
            "median_pct_positives_passing": float(np.median(pp)) if pp else None,
            "negatives_passing": sum(1 for b in neg_r if b <= n), "separation": round(float(sep), 3)}


def main():
    sites = read_sites()
    raw = R.load_raw_earth()
    rep = {s: one_set(s, sites, raw) for s in ("corrected", "audited_morning")}
    for s, v in rep.items():
        print(s, {k: v[k] for k in v if k != "rows"})
        for x in v["rows"]:
            if x["passes"]:
                print("  ", x["site_id"], x["name"][:40], x["rank"], x["pct"], x["final"])
    print(R.dump(rep, "ra_base_validation.json"))


if __name__ == "__main__":
    main()
