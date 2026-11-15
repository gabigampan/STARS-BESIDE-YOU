"""r2: Solar panels suitability without latitude. In-memory options on the audit library p5_common.
Deterministic; writes research/out/r2_*.json/csv. Changes nothing in engine/config/bundle."""
import os, sys, json, copy
import numpy as np, pandas as pd
from scipy.stats import spearmanr
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TL, "audit"))
import p5_common as C
OUT = os.path.join(HERE, "out")
P0 = C.load_params(); T = C.load_tables(P0); D = C.derived(T, P0)
E = T["EARTH"]
raw = pd.read_csv(os.path.join(TL, "output_real", "earth_real_1deg.csv"), low_memory=False)
raw["id"] = raw["row"] * 360 + raw["col"]; raw = raw.sort_values("id").reset_index(drop=True)
sup = pd.read_csv(os.path.join(TL, "real_data", "supplement", "earth_cloud_isccp_1deg.csv"))
sup["id"] = sup["row"] * 360 + sup["col"]; sup = sup.sort_values("id").reset_index(drop=True)
assert (sup["id"].to_numpy() == E["id"].to_numpy()).all()
E["clear_frac_isccp"] = sup["clear_frac_isccp"].to_numpy()
toaE = D["irradiance_toa_kwh_m2_day"]["EARTH"]
E["kt_worldclim"] = pd.to_numeric(E["irradiance_kwh_m2_day"], errors="coerce").to_numpy() / toaE
cache = {}
def run(P): return C.run_mission(T, D, "solar", P, cache=cache)
def name_of(i): return None
# --- reproduction check against the bundle
r0 = run(P0)
try:
    B = C.bundle_mission("solar")
    bmap = dict(zip(B["ids"].tolist(), B.get("final", B.get("score", np.full(len(B["ids"]), np.nan))).tolist()))
    keys = [k for k in B if "final" in k or "score" in k]
    repro = {"bundle_keys": list(B.keys())[:30]}
except Exception as ex:
    repro = {"error": str(ex)}
top_b = C.top_ids(r0, 5)
repro["top5_model"] = top_b
lat = E["lat"].to_numpy(); lon = E["lon"].to_numpy()
def ang(i, j):
    a1, o1, a2, o2 = map(np.radians, (lat[i], lon[i], lat[j], lon[j]))
    return np.degrees(np.arccos(np.clip(np.sin(a1)*np.sin(a2)+np.cos(a1)*np.cos(a2)*np.cos(o1-o2), -1, 1)))
def top_sep(r, k=5, sep=2.0):
    o = np.argsort(np.where(r["rank"] > 0, r["rank"], 10**9), kind="stable"); o = o[r["rank"][o] > 0]
    out = []
    for q in o:
        i = int(r["pass_ids"][q])
        if all(ang(i, j[0]) >= sep for j in out):
            out.append((i, int(r["twin"][q]), q))
        if len(out) == k: break
    return out
M = T["MOON"]; mlat = dict(zip(M["id"], M["lat"])); mlon = dict(zip(M["id"], M["lon"]))
def describe(r, A50=None):
    pi = r["pass_ids"]; s = r["suit"]; ok = np.isfinite(s)
    rho = spearmanr(s[ok], np.abs(lat[pi][ok])).correlation
    t5 = [{"earth_id": int(i), "lat": float(lat[i]), "lon": float(lon[i]), "twin": int(t),
           "twin_lat": float(mlat.get(t, np.nan)), "twin_lon": float(mlon.get(t, np.nan)),
           "similarity": round(float(r["sim"][q]), 2), "suitability": round(float(r["suit"][q]), 2), "final": float(r["final_pub"][q])}
          for i, t, q in top_sep(r)]
    t50 = C.top_ids(r, 50); t100 = C.top_ids(r, 100)
    trop = float(np.mean(np.abs(lat[t100]) <= 23.44))
    rr = raw.set_index("id").loc[t50]
    art = {"snow_ice_frac>0": int((rr["snow_ice_frac"].fillna(0) > 0).sum()),
           "lc_water_210": int((rr["lc_dominant_cci_code"] == 210).sum()), "lc_ice_220": int((rr["lc_dominant_cci_code"] == 220).sum()),
           "coast_mask_frac<0.999": int((rr["mask_fraction"] < 0.999).sum()), "coast_mask_frac<0.5": int((rr["mask_fraction"] < 0.5).sum())}
    has = r["twin"] >= 0
    return {"passing": int(r["passed"].sum()), "paired": int(has.sum()), "distinct_twins": int(len(set(r["twin"][has].tolist()))),
            "rho_suit_abslat": round(float(rho), 3), "top5_sep2deg": t5,
            "top50_overlap_with_A": None if A50 is None else len(set(t50) & set(A50)),
            "top100_tropics_share": round(trop, 2), "top50_artefacts": art, "_t50": t50, "_r": r}
def with_soft(soft):
    P = copy.deepcopy(P0); P["missions"]["solar"]["soft"] = soft; return P
S0 = P0["missions"]["solar"]["soft"]
# ---------- step 1: decomposition
pi = r0["pass_ids"]; s = r0["suit"]; U = r0["utils"]
crit = list(S0.keys()); wsum = sum(S0[k]["weight"] for k in crit)
dec = []
contrib = {k: S0[k]["weight"] / wsum * 100 * np.nan_to_num(U[k]) for k in crit}
vs = np.var(s)
A50 = C.top_ids(r0, 50); A5 = [x[0] for x in top_sep(r0)]
for k in crit:
    x = pd.to_numeric(E[k], errors="coerce").to_numpy()[pi]
    soft = {kk: vv for kk, vv in S0.items() if kk != k}
    rk = run(with_soft(soft))
    dec.append({"criterion": k, "weight": S0[k]["weight"], "bad": S0[k]["bad"], "good": S0[k]["good"],
                "rho_abslat": round(float(spearmanr(x, np.abs(lat[pi]), nan_policy="omit").correlation), 3),
                "share_of_spread": round(float(np.cov(contrib[k], s)[0, 1] / vs), 3),
                "removed_top5_sep": [y[0] for y in top_sep(rk)], "removed_top50_overlap": len(set(C.top_ids(rk, 50)) & set(A50))})
X = pd.DataFrame({k: pd.to_numeric(E[k], errors="coerce").to_numpy()[pi] for k in crit})
X["clear_frac_isccp"] = E["clear_frac_isccp"].to_numpy()[pi]; X["kt_worldclim"] = E["kt_worldclim"].to_numpy()[pi]; X["abs_lat"] = np.abs(lat[pi])
inter = X.corr(method="spearman").round(3)
# ---------- distribution of the new criteria among passing points
q = lambda v, p: round(float(np.nanpercentile(X[v], p)), 3)
dist = {v: {p: q(v, p) for p in (5, 10, 25, 50, 75, 90, 95)} for v in ("clear_frac_isccp", "kt_worldclim")}
cf_bad, cf_good = dist["clear_frac_isccp"][10], dist["clear_frac_isccp"][90]
kt_bad, kt_good = dist["kt_worldclim"][10], dist["kt_worldclim"][90]
keep = {k: v for k, v in S0.items() if k not in ("sun_elev_max_deg", "sun_low_frac_0_5deg")}
opts = {
 "A_today": S0,
 "B_drop_geometry": keep,
 "C1_clear_frac_isccp": {**keep, "clear_frac_isccp": {"weight": 0.30, "bad": cf_bad, "good": cf_good}},
 "C2_kt_worldclim": {**keep, "kt_worldclim": {"weight": 0.30, "bad": kt_bad, "good": kt_good}},
 "E_clear_frac_replaces_irr_and_geometry": {**{k: v for k, v in keep.items() if k != "irradiance_kwh_m2_day"},
                                            "clear_frac_isccp": {"weight": 0.65, "bad": cf_bad, "good": cf_good}},
 "F_kt_replaces_irr_and_geometry": {**{k: v for k, v in keep.items() if k != "irradiance_kwh_m2_day"},
                                            "kt_worldclim": {"weight": 0.65, "bad": kt_bad, "good": kt_good}},
}
res = {}
for nme, soft in opts.items():
    d = describe(run(with_soft(soft)), A50)
    r = d.pop("_r"); d.pop("_t50")
    ws = sum(v["weight"] for v in soft.values())
    latw = 0.0
    for k, v in soft.items():
        x = pd.to_numeric(E[k], errors="coerce").to_numpy()[r["pass_ids"]]
        rh = spearmanr(x, np.abs(lat[r["pass_ids"]]), nan_policy="omit").correlation
        if abs(rh) >= 0.5: latw += v["weight"]
    d["weight_share_latitude_driven(|rho|>=0.5)"] = round(latw / ws, 3)
    d["soft"] = soft
    res[nme] = d
# sites (coordinates given in the report with their source); cell lookup
sites = {"Plataforma Solar de Almeria (CIEMAT)": (37.09, -2.36), "NREL Solar Radiation Research Laboratory, Golden": (39.742, -105.18),
         "Noor Ouarzazate (MASEN)": (31.0, -6.86)}
site_out = {}
for sn, (la, lo) in sites.items():
    cid = int(np.floor(90 - la)) * 360 + int(np.floor(lo + 180)); row = {}
    for nme, soft in opts.items():
        r = run(with_soft(soft)); w = np.flatnonzero(r["pass_ids"] == cid)
        row[nme] = None if not len(w) else {"rank": int(r["rank"][w[0]]), "of": int((r["rank"] > 0).sum()), "suit": round(float(r["suit"][w[0]]), 1)}
    site_out[sn] = {"cell": f"E{cid}", "ranks": row}
json.dump({"reproduction": repro, "decomposition": dec, "spearman_matrix": inter.to_dict(), "new_criteria_distribution_passing": dist,
           "options": res, "sites": site_out, "corr_clear_vs_kt_spearman": round(float(X[["clear_frac_isccp", "kt_worldclim"]].corr(method="spearman").iloc[0, 1]), 3)},
          open(os.path.join(OUT, "r2_solar_options.json"), "w"), indent=1, default=str)
inter.to_csv(os.path.join(OUT, "r2_spearman_matrix.csv"))
print("done")
