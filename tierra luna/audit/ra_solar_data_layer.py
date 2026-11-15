"""Re-audit Solar panels, item 4: the new supplementary column clear_frac_isccp.

    python -I ra_solar_data_layer.py [raw_isccp_dir]

1. Own reduction from the NOAA NCEI ISCCP-H HGM v01r00 monthly files (if the folder is given):
   cldamt (%) per 1-degree equal-angle cell, mean of the monthly means 2012-01..2016-12 with >= 48
   valid months, mapped to our grid by the cell CENTRE coordinates read from the file (lat/lon
   variables), not by an assumed flip/roll; compared with the supplement cell by cell.
2. Range, missing values among the passing points, orientation at known places (clear deserts vs
   cloudy belts, with coordinates stated here from general geography, each checked by sign only).
3. Behaviour over bright deserts, snow/ice and coasts: distribution by land-cover class and land share.
4. Correlations (Spearman) with |lat|, the criteria that stay, WorldClim irradiance and the TOA sunlight,
   among the passing points and among the paired points.
5. bad/good = P10/P90 of clear_frac_isccp over the passing points (decision) recomputed.
Writes out/ra_solar_data_layer.json.
"""
import glob
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ra_solar_common as R  # noqa: E402


def own_reduction(raw_dir, E):
    import netCDF4
    files = sorted(glob.glob(os.path.join(raw_dir, "ISCCP-Basic.HGM.v01r00.GLOBAL.201[2-6].*.nc")))
    stack, meta = [], {}
    for f in files:
        ds = netCDF4.Dataset(f)
        v = ds.variables["cldamt"]
        a = np.ma.filled(v[:].astype(float), np.nan).squeeze()
        if not meta:
            meta = {"units": getattr(v, "units", None), "long_name": getattr(v, "long_name", None), "shape": list(a.shape),
                    "license": getattr(ds, "license", None), "title": getattr(ds, "title", None),
                    "lat_first_last": [float(ds.variables["lat"][0]), float(ds.variables["lat"][-1])],
                    "lon_first_last": [float(ds.variables["lon"][0]), float(ds.variables["lon"][-1])],
                    "valid_range": [float(x) for x in getattr(v, "valid_range", [np.nan, np.nan])],
                    "scale_factor": float(getattr(v, "scale_factor", 1.0)), "time_coverage_start": getattr(ds, "time_coverage_start", None)}
            lat = np.array(ds.variables["lat"][:], float)
            lon = np.array(ds.variables["lon"][:], float)
        stack.append(a)
        ds.close()
    S = np.array(stack)
    nvalid = np.isfinite(S).sum(axis=0)
    mean = np.where(nvalid >= 48, np.nanmean(S, axis=0), np.nan) / 100.0
    # map by centre coordinates
    lon180 = np.where(lon > 180, lon - 360, lon)
    rows = np.floor(90 - lat).astype(int)
    cols = np.floor(lon180 + 180).astype(int)
    own = np.full(180 * 360, np.nan)
    nv = np.zeros(180 * 360)
    for i, rr in enumerate(rows):
        own[rr * 360 + cols] = mean[i]
        nv[rr * 360 + cols] = nvalid[i]
    sup = E["cloud_frac_isccp"].to_numpy(float)
    ids = E["id"].to_numpy()
    o = own[ids]
    both = np.isfinite(o) & np.isfinite(sup)
    d = np.abs(o - sup)
    return {"files": len(files), "meta": meta,
            "cells_both": int(both.sum()), "cells_own_only": int((np.isfinite(o) & ~np.isfinite(sup)).sum()),
            "cells_supp_only": int((~np.isfinite(o) & np.isfinite(sup)).sum()),
            "max_abs_diff_cloud_frac": float(np.nanmax(d[both])), "p99_abs_diff": float(np.percentile(d[both], 99)),
            "n_months_equal": int((nv[ids] == E["n_months_isccp"].to_numpy(float)).sum())}


def main():
    raw_dir = sys.argv[1] if len(sys.argv) > 1 else None
    P, _, _, _ = R.load_params_set("corrected")
    T, D = R.tables(P)
    E = T["EARTH"]
    r = R.run(P)
    out = {}
    if raw_dir:
        out["own_reduction"] = own_reduction(raw_dir, E)
    cf = E["clear_frac_isccp"].to_numpy(float)
    land = E["__mask_fraction"].to_numpy(float) > 0
    out["range_all_cells"] = [float(np.nanmin(cf)), float(np.nanmax(cf))]
    out["missing_all_cells"] = int(np.isnan(cf).sum())
    pos = {int(i): j for j, i in enumerate(E["id"].to_numpy())}
    pj = np.array([pos[int(i)] for i in r["pass_ids"]])
    cp = cf[pj]
    out["passing_n"] = int(len(pj))
    out["passing_missing"] = [int(r["pass_ids"][k]) for k in np.flatnonzero(np.isnan(cp))]
    out["passing_pcts"] = {p: round(float(np.nanpercentile(cp, p)), 4) for p in (0, 5, 10, 25, 50, 75, 90, 95, 100)}
    soft = P["missions"]["solar"]["soft"]["clear_frac_isccp"]
    out["configured_bad_good"] = [soft["bad"], soft["good"]]
    out["recomputed_P10_P90_3dp"] = [round(float(np.nanpercentile(cp, 10)), 3), round(float(np.nanpercentile(cp, 90)), 3)]
    out["bad_good_match"] = out["recomputed_P10_P90_3dp"] == [round(soft["bad"], 3), round(soft["good"], 3)]
    # orientation (expected sign only; places from general geography)
    places = {"Sahara, Libya (24.5N 25.5E) expected clear": (24.5, 25.5, "clear"), "Atacama (23.5S 69.5W) expected clear": (-23.5, -69.5, "clear"),
              "Rub al Khali (19.5N 50.5E) expected clear": (19.5, 50.5, "clear"), "Western Australia desert (25.5S 125.5E) expected clear": (-25.5, 125.5, "clear"),
              "Congo basin (0.5S 20.5E) expected cloudy": (-0.5, 20.5, "cloudy"), "Amazon (3.5S 59.5W) expected cloudy": (-3.5, -59.5, "cloudy"),
              "Southern Ocean (58.5S 0.5E) expected cloudy": (-58.5, 0.5, "cloudy"), "Scotland (56.5N 4.5W) expected cloudy": (56.5, -4.5, "cloudy"),
              "Borneo (0.5N 113.5E) expected cloudy": (0.5, 113.5, "cloudy"), "Mojave (35.5N 115.5W) expected clear": (35.5, -115.5, "clear")}
    ori = {}
    for k, (la, lo, exp) in places.items():
        c = int(np.floor(90 - la)) * 360 + int(np.floor(lo + 180))
        v = float(cf[pos[c]])
        ori[k] = {"cell": "E%d" % c, "clear_frac": round(v, 3), "ok": (v > 0.5) if exp == "clear" else (v < 0.4)}
    out["orientation"] = ori
    # by surface type, land cells
    lc = E["__lc_dominant_cci_code"].to_numpy(float)
    si = E["__snow_ice_frac"].to_numpy(float)
    mf = E["__mask_fraction"].to_numpy(float)
    bare = E["__bare_frac"].to_numpy(float)

    def dsc(mask):
        v = cf[mask & np.isfinite(cf)]
        return {"n": int(len(v)), "median": None if not len(v) else round(float(np.median(v)), 3),
                "p10": None if not len(v) else round(float(np.percentile(v, 10)), 3), "p90": None if not len(v) else round(float(np.percentile(v, 90)), 3)}
    lat = E["lat"].to_numpy(float)
    out["by_surface_land_cells"] = {
        "bare >= 0.8 (bright desert)": dsc(land & (bare >= 0.8)),
        "bare >= 0.8 and |lat| <= 35": dsc(land & (bare >= 0.8) & (np.abs(lat) <= 35)),
        "snow_ice >= 0.5": dsc(land & (si >= 0.5)),
        "snow_ice >= 0.5, Greenland/Antarctica lat |>=60|": dsc(land & (si >= 0.5) & (np.abs(lat) >= 60)),
        "coast 0.3 <= land < 0.9": dsc(land & (mf >= 0.3) & (mf < 0.9)),
        "inland land >= 0.999": dsc(land & (mf >= 0.999)),
        "passing points": dsc(np.isin(np.arange(len(E)), pj)),
    }
    # coastal effect among passing: same latitude band, coast vs inland
    pm = np.zeros(len(E), bool)
    pm[pj] = True
    out["passing_coast_vs_inland_same_lat"] = {}
    for band in ((0, 15), (15, 30), (30, 45)):
        b = pm & (np.abs(lat) >= band[0]) & (np.abs(lat) < band[1])
        out["passing_coast_vs_inland_same_lat"]["%d-%d" % band] = {"coast(<0.9 land)": dsc(b & (mf < 0.9)), "inland(>=0.999)": dsc(b & (mf >= 0.999))}
    # correlations
    cols = {"abs_lat": np.abs(lat), "clear_frac_isccp": cf,
            "irradiance_worldclim": pd.to_numeric(E["irradiance_kwh_m2_day"], errors="coerce").to_numpy(float),
            "irradiance_toa": D["irradiance_toa_kwh_m2_day"]["EARTH"],
            "slope_deg": pd.to_numeric(E["slope_deg"], errors="coerce").to_numpy(float),
            "roughness_m": pd.to_numeric(E["roughness_m"], errors="coerce").to_numpy(float),
            "lst_diurnal_amp_k": pd.to_numeric(E["lst_diurnal_amp_k"], errors="coerce").to_numpy(float),
            "sun_elev_max_deg": pd.to_numeric(E["sun_elev_max_deg"], errors="coerce").to_numpy(float),
            "sun_low_frac_0_5deg": pd.to_numeric(E["sun_low_frac_0_5deg"], errors="coerce").to_numpy(float),
            "rain_mm_day": pd.to_numeric(E.get("rain_mm_day", pd.Series(np.nan, index=E.index)), errors="coerce").to_numpy(float) if "rain_mm_day" in E else None}
    cols = {k: v for k, v in cols.items() if v is not None}
    has = r["twin"] >= 0
    for nm, sel in (("passing", pj), ("paired", pj[has])):
        X = pd.DataFrame({k: v[sel] for k, v in cols.items()})
        X["suitability"] = r["suit"] if nm == "passing" else r["suit"][has]
        out["spearman_" + nm] = X.corr(method="spearman").round(3)["clear_frac_isccp"].to_dict()
        out["spearman_suitability_" + nm] = X.corr(method="spearman").round(3)["suitability"].to_dict()
    # share of suitability spread per criterion
    ws = sum(v["weight"] for v in P["missions"]["solar"]["soft"].values())
    sv = np.var(r["suit"])
    out["share_of_spread"] = {k: round(float(np.cov(v["weight"] / ws * 100 * np.nan_to_num(r["utils"][k]), r["suit"])[0, 1] / sv), 3)
                              for k, v in P["missions"]["solar"]["soft"].items()}
    p = R.jdump(out, "ra_solar_data_layer.json")
    import json
    print(json.dumps(out, indent=1, default=str)[:6000])
    print("wrote", p)


if __name__ == "__main__":
    main()
