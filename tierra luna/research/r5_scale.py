"""r5: Rover similarity desaturation. Measurement scale (S1-S3), score candidates A/B/C in memory, the five, validation.
Library: audit/p5_common.py (independent re-implementation, reproduced bundle 42d8bba). Applies in memory the decided
Rover rule (slope 0.5 + roughness 0.5, both key, filter slope<=2 deg and roughness<=30 m, no relative elevation).
Changes nothing in the engine, config, tables or bundle. Deterministic. Writes research/out/r5_scale.json."""
import copy, json, os, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE); REPO = os.path.dirname(TL)
sys.path.insert(0, os.path.join(TL, "audit"))
import p5_common as C
OUT = os.path.join(HERE, "out")

P0 = C.load_params(); T = C.load_tables(P0); D = C.derived(T, P0)
E, M = T["EARTH"], T["MOON"]
RAWE = pd.read_csv(os.path.join(TL, "output_real/earth_real_1deg.csv"), low_memory=False).sort_values(["row", "col"]).reset_index(drop=True)
RAWM = pd.read_csv(os.path.join(TL, "output_real/moon_real_1deg.csv"), low_memory=False).sort_values(["row", "col"]).reset_index(drop=True)
res = {}

# ---------------------------------------------------------------- 1. the scale
SZ_E, SZ_M = 7.17, 10.0             # ETOPO 2022 global RMSE (MacFerrin et al. 2025); LOLA ~10 m radial (Smith et al. 2010)
DY_E, DY_M = 3706.0 / 2, 1895.2     # one DEM pixel north-south (docs/REAL_DATA.md; build_moon.py dy)
N_E, N_M = 60 * 60, 16 * 16         # pixels per 1-degree cell: ETOPO 60", LDEM_16
# slope: central difference g = (z+ - z-)/(2 dy) -> sd(g) = sqrt(2) sz / (2 dy) = sz / (sqrt(2) dy); small slope: sd(theta) = sd(g) rad
s1_slope_E = np.degrees(SZ_E / (np.sqrt(2) * DY_E)); s1_slope_M = np.degrees(SZ_M / (np.sqrt(2) * DY_M))
# roughness: one pair difference dz = z(x+L) - z(x) -> sd(dz) = sqrt(2) sz
s1_rough_E = np.sqrt(2) * SZ_E; s1_rough_M = np.sqrt(2) * SZ_M
S = {"S1_per_pixel": {"slope_deg": float(np.hypot(s1_slope_E, s1_slope_M)), "roughness_m": float(np.hypot(s1_rough_E, s1_rough_M))},
     "S2_per_cell_independent": {"slope_deg": float(np.hypot(s1_slope_E / np.sqrt(N_E), s1_slope_M / np.sqrt(N_M))),
                                 "roughness_m": float(np.hypot(s1_rough_E / np.sqrt(2 * N_E), s1_rough_M / np.sqrt(2 * N_M)))}}
res["scale_inputs"] = {"sz_earth_m": SZ_E, "sz_moon_m": SZ_M, "dy_earth_m": DY_E, "dy_moon_m": DY_M, "n_px_earth": N_E, "n_px_moon": N_M,
                       "S1_slope_earth_deg": float(s1_slope_E), "S1_slope_moon_deg": float(s1_slope_M),
                       "S1_rough_earth_m": float(s1_rough_E), "S1_rough_moon_m": float(s1_rough_M),
                       "rayleigh_noise_floor_slope_deg": {"earth": float(s1_slope_E * np.sqrt(np.pi / 2)), "moon": float(s1_slope_M * np.sqrt(np.pi / 2))},
                       "roughness_noise_bias_at_30m": {"earth": float(np.sqrt(900 + s1_rough_E ** 2) - 30), "moon": float(np.sqrt(900 + s1_rough_M ** 2) - 30)}}

# ---------------------------------------------------------------- decided rule, baseline
def decided(P):
    P = copy.deepcopy(P)
    vs = [v for v in P["missions"]["rover"]["sim"]["variables"] if v["variable"] in ("slope_deg", "roughness_m")]
    for v in vs: v["weight"] = 0.5
    P["missions"]["rover"]["sim"]["variables"] = vs
    return P

def shipped42(P):
    P = copy.deepcopy(P)
    vs = [v for v in P["missions"]["rover"]["sim"]["variables"] if v["variable"] in ("slope_deg", "roughness_m")]
    for v in vs: v["weight"] = 0.4
    vs.append({"variable": "elevation_rel_m", "role": "secondary", "weight": 0.2, "tolerance": 500.0})
    P["missions"]["rover"]["sim"]["variables"] = vs
    return P

Pd = decided(P0); rd = C.run_mission(T, D, "rover", Pd); r42 = C.run_mission(T, D, "rover", shipped42(P0))
zone = C.zone_mask(M, "rover", Pd); zi = np.flatnonzero(zone)
pi = rd["pass_ids"]; suit = rd["suit"]
names = ["slope_deg", "roughness_m"]; W = np.array([0.5, 0.5]); TOL = np.array([2.0, 30.0])
ev = np.column_stack([D[v]["EARTH"][pi] for v in names]); mv = np.column_stack([D[v]["MOON"][zi] for v in names])
MID = M["id"].to_numpy()

# S3: spread between the two slope definitions inside the tables (slope_deg vs slope_iso_deg), lunar zone and paired Earth
def q(x): x = x[np.isfinite(x)]; return [round(float(v), 4) for v in np.percentile(x, [50, 84, 95])] + [round(float(np.sqrt(np.mean(x ** 2))), 4), int(len(x))]
dz_m = (RAWM["slope_deg"] - RAWM["slope_iso_deg"]).to_numpy(float)[zi]
dz_e = (RAWE["slope_deg"] - RAWE["slope_iso_deg"]).to_numpy(float)[pi[rd["twin"] >= 0]]
res["S3_slope_two_definitions"] = {"moon_zone_abs_p50_p84_p95_rms_n": q(np.abs(dz_m)), "earth_paired_abs_p50_p84_p95_rms_n": q(np.abs(dz_e)),
                                   "note": "differ only in the east-west baseline (1 px vs max(1,1/cos lat) px): a definition difference, not a measurement error"}
S["S3_two_definitions"] = {"slope_deg": float(np.hypot(res["S3_slope_two_definitions"]["moon_zone_abs_p50_p84_p95_rms_n"][3],
                                                       res["S3_slope_two_definitions"]["earth_paired_abs_p50_p84_p95_rms_n"][3])),
                           "roughness_m": None}
res["scales"] = S

# ---------------------------------------------------------------- 2. the score
def score(kind, d, sig):
    if kind == "A": return np.exp(-0.5 * (d / TOL) ** 2)
    if kind == "B": return np.exp(-0.5 * (d / sig) ** 2)
    if kind == "C": return np.exp(-0.5 * np.maximum(0.0, d / sig - 1.0) ** 2)

def run(kind, sig, chunk=128):
    n = len(pi); tw = np.full(n, -1)
    sg = TOL if sig is None else np.asarray(sig, float)
    for a in range(0, n, chunk):
        b = min(n, a + chunk)
        d = np.abs(ev[a:b, None, :] - mv[None, :, :])
        ok = np.all(np.isfinite(d) & (d <= TOL), axis=2)                 # decided pair filter, unchanged
        s = (score(kind, np.where(np.isfinite(d), d, 1e9), sg) * W).sum(axis=2)
        s = np.where(ok, s, -np.inf)
        mx = s.max(axis=1)
        z2 = ((d / sg) ** 2).sum(axis=2)
        z2 = np.where(ok & (s >= mx[:, None]), z2, np.inf)                 # ties of the score: smallest scaled distance, then lowest index
        j = np.argmin(z2, axis=1)
        tw[a:b] = np.where(np.isfinite(mx), j, -1)
    has = tw >= 0
    mvt = np.where(has[:, None], mv[np.maximum(tw, 0)], np.nan)
    diff = np.abs(ev - mvt)
    sc = np.rint(score(kind, diff, sg) * 1e6) / 1e6
    sim_full = 100 * (score(kind, diff, sg) * W).sum(axis=1)
    sim = 100 * (sc * W).sum(axis=1)
    fin = 0.5 * sim + 0.5 * suit
    pub = C.pyround(fin, 2)
    okr = np.isfinite(pub)
    order = np.lexsort((pi, -np.where(okr, pub, -np.inf))); order = order[okr[order]]
    rank = np.zeros(n, int); rank[order] = np.arange(1, len(order) + 1)
    return {"sim": sim, "sim_full": sim_full, "final": fin, "final_pub": pub, "rank": rank,
            "twin": np.where(has, MID[zi][np.maximum(tw, 0)], -1), "diff": diff, "mvt": mvt}

CANDS = {"A_tol": ("A", None)}
for sk in ("S1_per_pixel", "S2_per_cell_independent"):
    for kd in ("B", "C"):
        CANDS[f"{kd}_{sk}"] = (kd, [S[sk]["slope_deg"], S[sk]["roughness_m"]])
R = {k: run(*v) for k, v in CANDS.items()}
res["check_A_vs_p5"] = {"final_pub_equal": bool(np.array_equal(np.nan_to_num(R["A_tol"]["final_pub"], nan=-1), np.nan_to_num(rd["final_pub"], nan=-1))),
                        "twin_equal_share": float(np.mean(R["A_tol"]["twin"] == rd["twin"])),
                        "top20_equal": C.top_ids(rd, 20) == [int(pi[k]) for k in np.argsort(np.where(R["A_tol"]["rank"] > 0, R["A_tol"]["rank"], 10 ** 9), kind="stable")[:20]]}

# ---------------------------------------------------------------- names, ice, distances
bb = C.bundle_columns("earth_base.bin"); places = json.load(open(os.path.join(REPO, "app/public/data/v2/places.json")))
ctry = {int(i): c for i, c in zip(bb["id"], bb["country"])}; regn = {int(i): r for i, r in zip(bb["id"], bb["region"])}
def place(i):
    c = ctry.get(i, np.nan); r = regn.get(i, np.nan)
    cn = places["countries"][int(c)]["name"] if np.isfinite(c) else "-"
    rn = places["regions"][int(r)] if np.isfinite(r) else None
    return f"{rn}, {cn}" if rn else cn
iau = json.load(open(os.path.join(REPO, "app/public/data/v2/iau_moon_features.json")))
fl, fo = np.radians(np.array(iau["lat"])), np.radians(np.array(iau["lon"]))
def gc(la1, lo1, la2, lo2):
    la1, lo1, la2, lo2 = map(np.radians, (la1, lo1, la2, lo2))
    return np.degrees(np.arccos(np.clip(np.sin(la1) * np.sin(la2) + np.cos(la1) * np.cos(la2) * np.cos(lo1 - lo2), -1, 1)))
def feature(t):
    la, lo = np.radians(M.lat[t]), np.radians(M.lon[t])
    d = np.degrees(np.arccos(np.clip(np.sin(la) * np.sin(fl) + np.cos(la) * np.cos(fl) * np.cos(lo - fo), -1, 1)))
    k = int(np.argmin(d)); return f"{iau['name'][k]} ({d[k] * np.pi / 180 * 1737.4:.0f} km)"
snow = RAWE["snow_ice_frac"].to_numpy(float)
ice = np.nan_to_num(snow[pi], nan=-1) >= 0.5

def row(r, k):
    i = int(pi[k]); t = int(r["twin"][k])
    return {"id": "E%d" % i, "lat": float(E.lat[i]), "lon": float(E.lon[i]), "place": place(i), "twin": "M%d" % t, "twin_lat": float(M.lat[t]),
            "twin_lon": float(M.lon[t]), "twin_feature": feature(t), "slope_E": round(float(ev[k, 0]), 3), "slope_M": round(float(r["mvt"][k, 0]), 3),
            "rough_E": round(float(ev[k, 1]), 2), "rough_M": round(float(r["mvt"][k, 1]), 2), "sim": round(float(r["sim_full"][k]), 4),
            "suit": round(float(suit[k]), 2), "final": float(r["final_pub"][k]), "rank": int(r["rank"][k]), "snow_ice_frac": float(snow[i])}

def five_a(r):
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable"); out = []
    for k in o:
        if r["rank"][k] <= 0: break
        if ice[k]: continue
        i = int(pi[k])
        if all(gc(E.lat[i], E.lon[i], E.lat[int(pi[j])], E.lon[int(pi[j])]) >= 2.0 for j in out): out.append(int(k))
        if len(out) == 5: break
    return out

def five_b(r):
    top = np.nanmax(r["final_pub"]); tied = np.flatnonzero((r["final_pub"] == top) & ~ice)
    if len(tied) <= 5: return None, int(len(tied))
    o = tied[np.lexsort((pi[tied], -r["sim_full"][tied]))]; ch = [int(o[0])]
    la, lo = E.lat.to_numpy()[pi[tied]], E.lon.to_numpy()[pi[tied]]
    dmin = gc(la, lo, la[list(tied).index(ch[0])], lo[list(tied).index(ch[0])])
    while len(ch) < 5:
        cand = np.lexsort((pi[tied], -dmin)); nk = int(tied[cand[0]]); ch.append(nk)
        dmin = np.minimum(dmin, gc(la, lo, E.lat[int(pi[nk])], E.lon[int(pi[nk])]))
    return ch, int(len(tied))

def dists(ks):
    return [[round(float(gc(E.lat[int(pi[a])], E.lon[int(pi[a])], E.lat[int(pi[b])], E.lon[int(pi[b])]) * np.pi / 180 * 6371.0)) for b in ks] for a in ks]

# ---------------------------------------------------------------- 4. validation sites
bench = pd.read_csv(os.path.join(TL, "data/benchmark/analog_benchmark.csv"))
KEYS = ("Ramon", "Qaidam", "Haughton", "Yungay", "Erfoud", "MDRS", "Bardenas", "Tabernas", "Death Valley", "Dumont", "Dhofar",
        "Concordia", "NEEMO", "HI-SEAS", "Rio Tinto", "El Soplao")
sites = []
for kname in KEYS:
    h = bench[bench.name.str.contains(kname, case=False, regex=False)]
    if len(h): sites.append((kname, float(h.iloc[0].lat), float(h.iloc[0].lon)))
pos = {int(i): k for k, i in enumerate(pi)}
def where(r):
    npair = int((r["rank"] > 0).sum()); o = {}
    for kname, la, lo in sites:
        i = int(np.floor(90 - la)) * 360 + int(np.floor(lo + 180))
        if i in pos and r["rank"][pos[i]] > 0:
            k = pos[i]; o[kname] = {"cell": "E%d" % i, "rank": int(r["rank"][k]), "pct": round(100 * r["rank"][k] / npair, 1),
                                    "slope": round(float(ev[k, 0]), 3), "rough": round(float(ev[k, 1]), 1), "suit": round(float(suit[k]), 2),
                                    "sim": round(float(r["sim_full"][k]), 3), "final": float(r["final_pub"][k]),
                                    "twin_slope": round(float(r["mvt"][k, 0]), 3), "twin_rough": round(float(r["mvt"][k, 1]), 1)}
        else: o[kname] = {"cell": "E%d" % i, "rank": None}
    return o

def where42():
    npair = int((r42["rank"] > 0).sum()); p42 = {int(i): k for k, i in enumerate(r42["pass_ids"])}; o = {}
    for kname, la, lo in sites:
        i = int(np.floor(90 - la)) * 360 + int(np.floor(lo + 180))
        o[kname] = round(100 * r42["rank"][p42[i]] / npair, 1) if i in p42 and r42["rank"][p42[i]] > 0 else None
    return o

out = {}
for nm, r in R.items():
    ok = r["rank"] > 0; s = r["sim_full"][ok]; spub = C.pyround(r["sim"][ok], 2); fp = r["final_pub"][ok]
    srt = np.sort(fp)[::-1]; fifth = srt[4]; top = srt[0]
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10 ** 9), kind="stable")[:20]
    fa = five_a(r); fb, ntied = five_b(r)
    out[nm] = {"paired": int(ok.sum()),
               "sim_quantiles_0_1_5_25_50_75_95_99_100": [round(float(v), 4) for v in np.percentile(s, [0, 1, 5, 25, 50, 75, 95, 99, 100])],
               "share_sim_ge_99": round(float(np.mean(s >= 99)), 4), "share_ge_99_5": round(float(np.mean(s >= 99.5)), 4),
               "share_ge_99_9": round(float(np.mean(s >= 99.9)), 4), "n_sim_display_100_00": int(np.sum(spub == 100.0)),
               "top_final": float(top), "n_tied_top_final": int(np.sum(fp == top)), "n_tied_top_final_no_ice": ntied, "fifth": float(fifth),
               "n_within_0_1_of_fifth": int(np.sum(fp >= fifth - 0.1)), "n_within_0_5": int(np.sum(fp >= fifth - 0.5)), "n_within_1": int(np.sum(fp >= fifth - 1.0)),
               "spearman_final_suit": round(float(spearmanr(r["final"][ok], suit[ok])[0]), 4),
               "spearman_final_sim": round(float(spearmanr(r["final"][ok], r["sim_full"][ok])[0]), 4),
               "twins_distinct": int(len(set(r["twin"][ok]))),
               "top20": [row(r, int(k)) for k in o],
               "five_a": [row(r, k) for k in fa], "five_a_dist_km": dists(fa),
               "five_b": [row(r, k) for k in fb] if fb else None, "five_b_dist_km": dists(fb) if fb else None,
               "validation": where(r)}
res["candidates"] = out
res["validation_42d8bba_pct"] = where42()
res["moon_zone_ranges"] = {v: [round(float(x), 3) for x in np.nanpercentile(D[v]["MOON"][zi], [0, 5, 25, 50, 75, 95, 100])] for v in names}
res["earth_paired_ranges"] = {v: [round(float(x), 3) for x in np.nanpercentile(ev[rd["rank"] > 0, j], [0, 5, 25, 50, 75, 95, 100])] for j, v in enumerate(names)}
res["suit_paired_quantiles"] = [round(float(x), 2) for x in np.percentile(suit[rd["rank"] > 0], [0, 5, 25, 50, 75, 95, 100])]
res["ice_count_paired"] = int(np.sum(ice & (rd["rank"] > 0)))
json.dump(res, open(os.path.join(OUT, "r5_scale.json"), "w"), indent=1, default=float, ensure_ascii=False)
print(json.dumps({"scales": S, "check": res["check_A_vs_p5"]}, default=float))
for nm, o in out.items():
    print(nm, o["sim_quantiles_0_1_5_25_50_75_95_99_100"][4:], o["share_ge_99_5"], o["n_sim_display_100_00"], "tie", o["n_tied_top_final"], o["n_tied_top_final_no_ice"],
          "w01/05/1", o["n_within_0_1_of_fifth"], o["n_within_0_5"], o["n_within_1"], "rho", o["spearman_final_suit"],
          {k: v.get("pct") for k, v in o["validation"].items()})
print("42d8bba", res["validation_42d8bba_pct"])
