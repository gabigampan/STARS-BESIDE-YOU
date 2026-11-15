"""r1: Rover terrain independence. Correlations (step 1), candidate variables (step 3), options in memory (step 4).
Uses audit/p5_common.py as a library (checked against audit/out/w0_reproduce.json first). Reads the config once.
Applies in memory the decided rule (Rover similarity = slope 0.5 + roughness 0.5, no relative elevation).
Writes research/out/r1_measure.json and the supplementary table real_data/supplement/r1_terrain_<body>.csv."""
import copy, json, os, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TL, "audit"))
import p5_common as C
OUT = os.path.join(HERE, "out")

P0 = C.load_params(); T = C.load_tables(P0); D = C.derived(T, P0)
E, M = T["EARTH"], T["MOON"]
dem = {"EARTH": dict(np.load(OUT + "/r1_dem_earth.npz")), "MOON": dict(np.load(OUT + "/r1_dem_moon.npz"))}
RAWT = {"EARTH": pd.read_csv(os.path.join(TL, "output_real/earth_real_1deg.csv"), low_memory=False).sort_values(["row", "col"]),
        "MOON": pd.read_csv(os.path.join(TL, "output_real/moon_real_1deg.csv"), low_memory=False).sort_values(["row", "col"])}
res = {"checks": {}}
for b in ("EARTH", "MOON"):
    land = np.isfinite(D["slope_deg"][b])
    d = dem[b]
    for k in ("slope_iso_chk", "rough1_chk"):
        ref = D["slope_deg"][b] if k.startswith("slope") else D["roughness_m"][b]
        res["checks"][f"{b}_{k}_maxabs"] = float(np.nanmax(np.abs(d[k][land] - ref[land])))
    rr = d["rough2_m"]; r1 = D["roughness_m"][b]
    with np.errstate(all="ignore"):
        d["hurst_h"] = np.where((r1 > 0) & (rr > 0), np.log2(rr / r1), np.nan)
    d["p90_over_mean"] = RAWT[b]["slope_iso_p90_deg"].to_numpy(float) / np.where(D["slope_deg"][b] > 0, D["slope_deg"][b], np.nan)
    d["slope_iso_p90_deg"] = RAWT[b]["slope_iso_p90_deg"].to_numpy(float)
    d["slope_p90_deg"] = RAWT[b]["slope_p90_deg"].to_numpy(float)
    d["roughness_over_slope"] = r1 / np.where(D["slope_deg"][b] > 0, np.tan(np.radians(D["slope_deg"][b])) * 1895.0, np.nan)
    for k in list(d):
        D.setdefault("r1_" + k, {})[b] = d[k]

# ---- baseline reproduction (shipped rule, commit 42d8bba state) ----
r0 = C.run_mission(T, D, "rover", P0)
w0 = json.load(open(os.path.join(TL, "audit/out/w0_reproduce.json")))["rover"]
res["checks"]["baseline"] = {"passing": int(r0["passed"].sum()), "paired": int((r0["twin"] >= 0).sum()),
                             "distinct_twins": int(len(set(r0["twin"][r0["twin"] >= 0]))),
                             "w0": [w0["passing"], w0["paired"], w0["distinct_twins"]],
                             "top5_match": [t["earth_id"] for t in w0["top"][:5]] == ["E%d" % i for i in C.top_ids(r0, 5)]}


def decided(P):
    P = copy.deepcopy(P)
    vs = [v for v in P["missions"]["rover"]["sim"]["variables"] if v["variable"] in ("slope_deg", "roughness_m")]
    for v in vs: v["weight"] = 0.5
    P["missions"]["rover"]["sim"]["variables"] = vs
    return P


def sp(a, b, mask):
    ok = mask & np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 10: return None
    return {"spearman": round(float(spearmanr(a[ok], b[ok])[0]), 3), "pearson": round(float(pearsonr(a[ok], b[ok])[0]), 3), "n": int(ok.sum())}


Pd = decided(P0); rd = C.run_mission(T, D, "rover", Pd)
landE = np.isfinite(D["slope_deg"]["EARTH"]) & np.isfinite(D["roughness_m"]["EARTH"])
zoneM = C.zone_mask(M, "rover", Pd)
ranked = np.zeros(len(E), bool); ranked[rd["pass_ids"][rd["rank"] > 0]] = True
pidx = {int(i): k for k, i in enumerate(rd["pass_ids"])}
twin_of = np.full(len(E), -1); twin_of[rd["pass_ids"]] = rd["twin"]
sets = {"earth_land": ("EARTH", landE), "moon_zone": ("MOON", zoneM), "rover_ranked": ("EARTH", ranked)}
cols = ["slope_deg", "roughness_m", "r1_slope_iso_p90_deg", "r1_slope_p90_deg", "r1_p90_over_mean", "r1_steep_frac_5",
        "r1_steep_frac_10", "r1_steep_frac_15", "r1_rough2_m", "r1_hurst_h", "r1_roughness_over_slope"]
corr = {}
for s, (b, mk) in sets.items():
    corr[s] = {c: {"vs_slope": sp(D[c][b], D["slope_deg"][b], mk), "vs_rough": sp(D[c][b], D["roughness_m"][b], mk)} for c in cols}
# suitability utilities (shipped)
corr["utilities_slope_vs_rough_ranked"] = sp(rd["utils"]["slope_300m_deg"], rd["utils"]["rough_300m_m"], np.ones(len(rd["pass_ids"]), bool)) if "slope_300m_deg" in rd["utils"] else list(rd["utils"])
# pair differences
pe = np.flatnonzero(ranked); tw = twin_of[pe]
pair = {}
dd = {c: D[c]["EARTH"][pe] - D[c]["MOON"][tw] for c in cols}
for c in cols:
    pair[c] = {"vs_dslope": sp(dd[c], dd["slope_deg"], np.ones(len(pe), bool)), "vs_drough": sp(dd[c], dd["roughness_m"], np.ones(len(pe), bool))}
corr["pair_differences_decided_rule"] = pair
res["correlations"] = corr

# ---- distributions & overlap ----
dist = {}
for c in cols:
    row = {}
    for s, (b, mk) in sets.items():
        x = D[c][b][mk]; x = x[np.isfinite(x)]
        row[s] = [round(float(q), 4) for q in np.percentile(x, [0, 5, 25, 50, 75, 95, 100])] + [int(len(x))]
        row[s + "_share_zero"] = round(float((x == 0).mean()), 3)
    xe = D[c]["EARTH"][landE]; xm = D[c]["MOON"][zoneM]
    lo, hi = max(np.nanpercentile(xe, 5), np.nanpercentile(xm, 5)), min(np.nanpercentile(xe, 95), np.nanpercentile(xm, 95))
    row["overlap_5_95"] = [round(float(lo), 4), round(float(hi), 4), bool(lo < hi)]
    dist[c] = row
res["distributions"] = dist

# ---- options in memory ----
def top5_sep(r, sep=2.0):
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")
    out = []
    for k in o:
        if r["rank"][k] <= 0: break
        i = int(r["pass_ids"][k]); la, lo = E.lat[i], E.lon[i]
        if all(np.degrees(np.arccos(np.clip(np.sin(np.radians(la)) * np.sin(np.radians(E.lat[j])) + np.cos(np.radians(la)) * np.cos(np.radians(E.lat[j])) * np.cos(np.radians(lo - E.lon[j])), -1, 1))) >= sep for j, *_ in out):
            t = int(r["twin"][k])
            out.append((i, float(la), float(lo), t, float(M.lat[t]), float(M.lon[t]), round(float(r["sim"][k]), 2), round(float(r["suit"][k]), 2), float(r["final_pub"][k])))
        if len(out) == 5: break
    return out

bench = pd.read_csv(os.path.join(TL, "data/benchmark/analog_benchmark.csv"))
keys = ("Bardenas", "Tabernas", "Dumont", "MDRS", "Yungay", "Erfoud", "Dhofar", "Ramon", "Haughton", "Death Valley", "Qaidam")
sites = []
for k in keys:
    hit = bench[bench.name.str.contains(k, case=False)]
    if len(hit): sites.append((k, float(hit.iloc[0].lat), float(hit.iloc[0].lon)))

def where(r):
    o = {}
    n = int((r["rank"] > 0).sum())
    for k, la, lo in sites:
        i = int(np.floor(90 - la)) * 360 + int(np.floor(lo + 180))
        if i in set(r["pass_ids"].tolist()):
            kk = int(np.flatnonzero(r["pass_ids"] == i)[0]); rk = int(r["rank"][kk])
            o[k] = {"cell": "E%d" % i, "rank": rk, "of": n, "pct_from_top": round(100 * rk / n, 1) if rk else None, "twin": int(r["twin"][kk])}
        else:
            o[k] = {"cell": "E%d" % i, "rank": None, "note": "does not pass the Rover funnel"}
    return o

def summary(r, base_top50=None):
    t50 = C.top_ids(r, 50)
    return {"passing": int(r["passed"].sum()), "paired": int((r["twin"] >= 0).sum()),
            "distinct_twins": int(len(set(r["twin"][r["twin"] >= 0]))), "top5_sep2": top5_sep(r),
            "top50_overlap_with_decided": (len(set(t50) & set(base_top50)) if base_top50 else None), "analogs": where(r), "_t50": t50}

opts = {"A_decided_slope_rough": summary(rd)}
base50 = opts["A_decided_slope_rough"]["_t50"]
opts["A_decided_slope_rough"]["top50_overlap_with_shipped"] = len(set(base50) & set(C.top_ids(r0, 50)))

def add_var(P, var, w_new, tol):
    P = decided(P)
    vs = P["missions"]["rover"]["sim"]["variables"]
    for v in vs: v["weight"] = (1 - w_new) / 2
    vs.append({"variable": var, "role": "secondary", "weight": w_new, "tolerance": tol})
    return P

cand = json.loads(os.environ.get("R1_CANDS", "[]"))
for var, w_new, tol in cand:
    r = C.run_mission(T, D, "rover", add_var(P0, var, w_new, tol))
    opts[f"B_{var}_w{w_new}_tol{tol}"] = summary(r, base50)
for o in opts.values(): o.pop("_t50", None)
res["options"] = opts
res["sites"] = sites
json.dump(res, open(OUT + "/r1_measure.json", "w"), indent=1, default=float)
print(json.dumps(res["checks"], default=float))
