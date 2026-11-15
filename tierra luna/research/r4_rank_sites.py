"""r4_rank_sites: where the external validation sites come out in a bundle (Solar panels and Lunar base).

    python -I r4_rank_sites.py <bundle folder> [out tag]

Reads only the bundle (docs/DATA_CONTRACT.md: manifest.json columns, earth_base.bin, earth_<mission>.bin,
missions.json reason_codes) and the two site lists data/benchmark/validation_sites_solar.csv and
validation_sites_lunar_base.csv. Nothing of the engine is imported. Deterministic.

For each site: its 1-degree cell (row = floor(90 - lat), col = floor(lon + 180), id = row*360 + col), the
land share (earth_base v.mask_fraction), whether it passes the mission funnel and, if not, the exact reasons
(missions.json reason_codes text of every set fail bit), suitability, twin, similarity, final, the published
rank and the rank percentile 100*rank/passing (lower = better; passing cells without a twin are ranked after
the paired ones, by suitability, as in the bundle), and the best rank in the 3x3 block of cells around it
(diagnostic: a 1-degree cell is not a site). Summary per list: positives and negatives, median percentile,
count in the top quartile (rank <= passing/4), and the separation share = fraction of positive-negative
pairs in which the positive ranks better (eliminated or non-land cells share the worst rank; ties count 1/2).
Writes research/out/r4_rank_sites_<tag>.json and .csv (tag defaults to the bundle folder name).
"""
import csv
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = os.path.dirname(HERE)
LISTS = {"solar": os.path.join(TL, "data", "benchmark", "validation_sites_solar.csv"),
         "lunar_base": os.path.join(TL, "data", "benchmark", "validation_sites_lunar_base.csv")}
DIAG = {"solar": ["v.irradiance_kwh_m2_day", "v.sun_elev_max_deg", "v.sun_low_frac_0_5deg", "v.slope_iso_deg", "d.irradiance_toa_kwh_m2_day"],
        "lunar_base": ["v.tmin_c", "v.lst_diurnal_amp_k", "v.thermal_inertia_class", "v.permafrost_class", "v.elevation_m", "v.slope_iso_deg"]}


def columns(bdir, man, fname):
    ent = [f for f in man["files"] if f["name"] == fname][0]
    raw = open(os.path.join(bdir, fname), "rb").read()
    out = {}
    for c in ent["columns"]:
        dt = "<f4" if c["type"] == "float32" else "<i4"
        a = np.frombuffer(raw, dtype=dt, count=c["length"], offset=c["offset"])
        if c["type"] == "int32":
            miss = a == -2147483648
            a = a.astype(np.float64)
            if c.get("divisor"):
                a = a / float(c["divisor"])
            a[miss] = np.nan
        else:
            a = a.astype(np.float64)
        out[c["name"]] = a
    return out


def cell_id(lat, lon):
    row = min(int(math.floor(90.0 - lat)), 179)
    col = min(int(math.floor(lon + 180.0)), 359)
    return row * 360 + col


def read_sites(path):
    rows = [ln for ln in open(path, encoding="utf-8") if not ln.startswith("#")]
    return list(csv.DictReader(rows))


def fnum(x, d=2):
    return None if x is None or not np.isfinite(x) else round(float(x), d)


def main():
    bdir = os.path.abspath(sys.argv[1])
    tag = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(bdir.rstrip("/"))
    man = json.load(open(os.path.join(bdir, "manifest.json"), encoding="utf-8"))
    ms = json.load(open(os.path.join(bdir, "missions.json"), encoding="utf-8"))
    base = columns(bdir, man, "earth_base.bin")
    land_ids = base["id"].astype(int)
    pos_of = {int(i): k for k, i in enumerate(land_ids)}
    report, flat = {"bundle": bdir, "manifest_build_time": man.get("build_time"), "missions": {}}, []
    for m, lpath in LISTS.items():
        mdef = [x for x in ms["missions"] if x["id"] == m][0]
        codes = {r["bit"]: r["text"] for r in mdef["reason_codes"]}
        mb = columns(bdir, man, "earth_%s.bin" % m)
        n_pass = len(mb["land_index"])
        n_ranked = int(mdef["ranked_count"])
        rank_of, rec_of = {}, {}
        unp = []
        for k, li in enumerate(mb["land_index"].astype(int)):
            cid = int(land_ids[li])
            rec_of[cid] = k
            if np.isfinite(mb["rank"][k]):
                rank_of[cid] = int(mb["rank"][k])
            else:
                unp.append((-mb["suitability"][k], cid))
        # passing cells without a twin follow the paired ones, by published suitability, ties by id (missions.json funnel step 6)
        for j, (_, cid) in enumerate(sorted(unp)):
            rank_of[cid] = n_ranked + 1 + j
        assert max(rank_of.values()) == n_pass and len(rank_of) == n_pass
        top5 = sorted(rec_of, key=lambda c: rank_of[c])[:5]
        sites = []
        for s in read_sites(lpath):
            lat, lon = float(s["lat"]), float(s["lon"])
            cid = cell_id(lat, lon)
            r = {"site_id": s["site_id"], "role": s["role"], "name": s["name"], "lat": lat, "lon": lon, "cell": cid,
                 "cell_lat": 90 - (cid // 360 + 0.5), "cell_lon": -180 + (cid % 360 + 0.5)}
            if cid not in pos_of:
                r.update(land_cell=False, land_share=None, passes=False, reasons=["not a land cell of earth_base.bin"])
            else:
                li = pos_of[cid]
                fb = int(mb["fail_bits"][li])
                r.update(land_cell=True, land_share=fnum(base["v.mask_fraction"][li], 3), passes=fb == 0,
                         reasons=[codes[b] for b in sorted(codes) if fb >> b & 1])
                r["diag"] = {c: fnum(base[c][li] if len(base[c]) == len(land_ids) else base[c][cid // 360], 3) for c in DIAG[m] if c in base}
            if cid in rec_of:
                k = rec_of[cid]
                tw = mb["twin"][k]
                r.update(suitability=fnum(mb["suitability"][k]), twin=None if not np.isfinite(tw) else "M%d" % int(tw),
                         similarity=fnum(mb["similarity"][k]), final=fnum(mb["final"][k]), rank=rank_of[cid],
                         rank_pct=round(100.0 * rank_of[cid] / n_pass, 1))
            else:
                r.update(suitability=None, twin=None, similarity=None, final=None, rank=None, rank_pct=None)
            # 3x3 block (diagnostic)
            row, col = cid // 360, cid % 360
            best = None
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    rr, cc = row + dr, (col + dc) % 360
                    if 0 <= rr < 180 and rr * 360 + cc in rank_of:
                        v = rank_of[rr * 360 + cc]
                        best = v if best is None else min(best, v)
            r["best_rank_3x3"] = best
            # diagnostic: percentile of the cell's rank among the passing cells of the same latitude row
            # (100 * share of same-row passing cells ranked better; tells whether the order says more than latitude)
            same = [v for c2, v in rank_of.items() if c2 // 360 == row]
            r["rank_pct_within_lat_row"] = None if cid not in rank_of else round(100.0 * sum(v < rank_of[cid] for v in same) / len(same), 1)
            r["passing_in_lat_row"] = len(same)
            r["best_rank_3x3_pct"] = None if best is None else round(100.0 * best / n_pass, 1)
            sites.append(r)

        def summ(role, key="rank"):
            g = [x for x in sites if x["role"] == role]
            pct = [100.0 * x[key] / n_pass for x in g if x[key] is not None]
            return {"n": len(g), "passing": sum(x["passes"] for x in g), "with_twin": sum(x["twin"] is not None for x in g),
                    "median_rank_pct_of_passing_sites": None if not pct else round(float(np.median(pct)), 1),
                    "median_rank_pct_all_sites_eliminated_as_100": round(float(np.median([100.0 * x[key] / n_pass if x[key] is not None else 100.0 for x in g])), 1),
                    "in_top_quartile": sum(1 for x in g if x[key] is not None and x[key] <= n_pass / 4)}

        def sep(key="rank"):
            P = [x[key] if x[key] is not None else n_pass + 1 for x in sites if x["role"] == "positive"]
            N = [x[key] if x[key] is not None else n_pass + 1 for x in sites if x["role"] == "negative"]
            w = sum(1.0 if p < q else 0.5 if p == q else 0.0 for p in P for q in N)
            return round(w / (len(P) * len(N)), 3)

        report["missions"][m] = {"passing": n_pass, "ranked_with_twin": n_ranked,
                                 "top5_earth_cells": ["E%d" % c for c in top5],
                                 "positives": summ("positive"), "negatives": summ("negative"),
                                 "separation_share_cell": sep("rank"),
                                 "positives_3x3": summ("positive", "best_rank_3x3"), "negatives_3x3": summ("negative", "best_rank_3x3"),
                                 "separation_share_3x3": sep("best_rank_3x3"), "sites": sites}
        for x in sites:
            flat.append({"mission": m, **{k: (json.dumps(v) if isinstance(v, (list, dict)) else v) for k, v in x.items()}})
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    jp = os.path.join(HERE, "out", "r4_rank_sites_%s.json" % tag)
    json.dump(report, open(jp, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    keys = list(dict.fromkeys(k for r in flat for k in r))
    with open(os.path.join(HERE, "out", "r4_rank_sites_%s.csv" % tag), "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=keys)
        wr.writeheader()
        wr.writerows(flat)
    for m, v in report["missions"].items():
        print(m, "passing", v["passing"], "ranked", v["ranked_with_twin"], "top5", v["top5_earth_cells"])
        print("  positives", v["positives"], "\n  negatives", v["negatives"], "\n  separation", v["separation_share_cell"],
              "| 3x3", v["positives_3x3"], v["negatives_3x3"], v["separation_share_3x3"])
        for x in v["sites"]:
            print("  %-5s %-3s %-48s E%-6d land=%-5s pass=%-5s suit=%-6s twin=%-7s sim=%-6s fin=%-6s rank=%-6s pct=%-5s 3x3=%-5s row=%s %s %s" % (
                x["site_id"], x["role"][:3], x["name"][:48], x["cell"], x["land_share"], x["passes"], x["suitability"], x["twin"],
                x["similarity"], x["final"], x["rank"], x["rank_pct"], x["best_rank_3x3_pct"], str(x["rank_pct_within_lat_row"]) + "/" + str(x["passing_in_lat_row"]), "; ".join(x["reasons"]), x.get("diag")))
    print("wrote", jp)


if __name__ == "__main__":
    main()
