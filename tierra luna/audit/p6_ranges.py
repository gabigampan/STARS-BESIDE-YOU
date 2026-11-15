"""Point B (report point 11): every variable a mission uses, in both tables: min, P10, median,
P90, max (unweighted and area-weighted by cos(lat)), cells of the min and max, and physical
consistency checks (own code). Run:
    $PY -I "tierra luna/audit/p6_ranges.py"
Outputs: out/p6_ranges.csv, out/p6_ranges_checks.json
"""
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import OUT, dump, load_tables, toa_daily_mean_kwh, weighted_quantile  # noqa: E402

e, m = load_tables()

# TOA by latitude row, own formula (Earth eps IAU 2006; Moon eps 1.54 deg, S0 1361 as the tables)
lats = np.arange(89.5, -90, -1.0)
toa_e = {round(float(la), 1): toa_daily_mean_kwh(la) for la in lats}
toa_m = {round(float(la), 1): toa_daily_mean_kwh(la, eps_deg=1.54) for la in lats}
e["irradiance_toa_kwh_m2_day"] = e["lat_deg"].round(1).map(toa_e)
m["irradiance_toa_flat_kwh_m2_day"] = m["lat_deg"].round(1).map(toa_m)
e["tmin_k"] = e["tmin_c"] + 273.15
mm_e = (e["elevation_m"] * np.cos(np.radians(e["lat_deg"]))).sum() / np.cos(np.radians(e.loc[e["elevation_m"].notna(), "lat_deg"])).sum()
mm_m = (m["elevation_m"] * np.cos(np.radians(m["lat_deg"]))).sum() / np.cos(np.radians(m["lat_deg"])).sum()
e["elevation_rel_m"] = e["elevation_m"] - mm_e
m["elevation_rel_m"] = m["elevation_m"] - mm_m

# variables used by at least one mission (gates, soft criteria, similarity), mission column names
EARTH_VARS = {
    "elevation_m": "common gate (>=1 m); elevation_rel_m for rover similarity",
    "elevation_rel_m": "rover similarity (secondary, tol 500 m)",
    "mask_fraction": "common gate (>=0.3)",
    "slope_iso_deg": "slope_deg of every mission (column_overrides) and rover gate slope_300m_deg",
    "roughness_m": "rover gate/soft/similarity; solar soft/similarity; lunar_base similarity",
    "rock_or_bare_frac": "rover soft; lunar_base soft",
    "irradiance_kwh_m2_day": "solar gate/soft; lunar_base soft (ground, WorldClim srad)",
    "irradiance_toa_kwh_m2_day": "solar similarity key (Earth side, formula)",
    "sun_elev_max_deg": "solar gate/soft (formula)",
    "sun_low_frac_0_5deg": "solar gate/soft (formula)",
    "lst_diurnal_amp_k": "solar soft; lunar_base gate/soft/similarity key",
    "tmin_c": "lunar_base gate/soft/similarity key (as tmin_k)",
    "temp_k": "info difference only (rover, solar, lunar_base)",
    "permafrost_area_frac": "behind permafrost_class (lunar_base soft 5 %)",
}
MOON_VARS = {
    "elevation_m": "rover zone? no (solar zone elevation <= -1200 m); elevation_rel_m",
    "elevation_rel_m": "rover similarity",
    "slope_iso_deg": "slope_deg (all missions, filters and similarity)",
    "roughness_m": "all missions",
    "irradiance_kwh_m2_day": "solar similarity key (Moon side) and filters",
    "irradiance_toa_flat_kwh_m2_day": "auditor's flat-ground formula, for comparison",
    "sun_elev_max_deg": "solar gate",
    "sun_low_frac_0_5deg": "solar gate",
    "lst_diurnal_amp_k": "lunar_base similarity key",
    "tmin_k": "lunar_base similarity key",
    "tmax_k": "behind lst_diurnal_amp_k",
    "temp_k": "info difference",
    "illum_frac": "behind polar irradiance",
}

rows = []


def stats(df, body, var, use):
    x = df[var].astype(float)
    ok = x.notna()
    xs = x[ok]
    w = np.cos(np.radians(df.loc[ok, "lat_deg"]))
    if body == "EARTH" and var != "mask_fraction":
        w2 = w * df.loc[ok, "mask_fraction"].fillna(0)  # land-area weight
    else:
        w2 = w
    q = np.percentile(xs, [10, 50, 90])
    wq = weighted_quantile(xs, w2, [0.0, 0.1, 0.5, 0.9, 1.0])
    imin, imax = xs.idxmin(), xs.idxmax()
    rows.append(dict(body=body, variable=var, use=use, n=int(ok.sum()),
                     min=xs.min(), p10=q[0], median=q[1], p90=q[2], max=xs.max(),
                     w_p10=wq[1], w_median=wq[2], w_p90=wq[3],
                     weight="cos(lat)" + (" x land share" if w2 is not w else ""),
                     min_cell=f"{df.at[imin, 'cell_id']} ({df.at[imin, 'lat_deg']}, {df.at[imin, 'lon_deg']})",
                     max_cell=f"{df.at[imax, 'cell_id']} ({df.at[imax, 'lat_deg']}, {df.at[imax, 'lon_deg']})"))


for v, u in EARTH_VARS.items():
    stats(e, "EARTH", v, u)
# gate-passing land subset (mask >= 0.3, elevation >= 1) for the key climate variables
land = e[(e["mask_fraction"] >= 0.3) & (e["elevation_m"] >= 1)]
for v in ["slope_iso_deg", "roughness_m", "tmin_c", "lst_diurnal_amp_k", "irradiance_kwh_m2_day"]:
    stats(land, "EARTH_common_gates", v, "same, cells passing the common gates")
for v, u in MOON_VARS.items():
    stats(m, "MOON", v, u)
df = pd.DataFrame(rows)
for c in ["min", "p10", "median", "p90", "max", "w_p10", "w_median", "w_p90"]:
    df[c] = df[c].astype(float).round(4)
df.to_csv(os.path.join(OUT, "p6_ranges.csv"), index=False)

# ---------------------------------------------------------------- physical consistency checks
chk = {}
# 1. Earth ground irradiance cannot exceed the TOA value at the same latitude (annual mean)
r = e["irradiance_kwh_m2_day"] / e["irradiance_toa_kwh_m2_day"]
chk["earth_ground_over_toa"] = dict(
    n=int(r.notna().sum()), max=float(r.max()), cells_above_1=int((r > 1).sum()),
    cells_above_0_80=int((r > 0.80).sum()), p50=float(r.median()), p99=float(r.quantile(0.99)),
    max_cell=str(e.loc[r.idxmax(), ["cell_id", "lat_deg", "lon_deg", "irradiance_kwh_m2_day", "irradiance_toa_kwh_m2_day", "mask_fraction"]].to_dict()),
    top10=e.assign(r=r).nlargest(10, "r")[["cell_id", "lat_deg", "lon_deg", "elevation_m", "mask_fraction", "irradiance_kwh_m2_day", "irradiance_toa_kwh_m2_day", "r"]].round(4).to_dict("records"))
# 2. Moon irradiance vs flat-ground TOA formula (equal outside the polar caps, <= at the poles)
d = m["irradiance_kwh_m2_day"] - m["irradiance_toa_flat_kwh_m2_day"]
low = m["lat_deg"].abs() < 65
chk["moon_irr_minus_flat_formula"] = dict(
    abs_lat_lt_65_maxabs=float(d[low].abs().max()),
    polar_min=float(d[~low].min()), polar_max=float(d[~low].max()),
    polar_cells_above_formula=int((d[~low] > 0.01).sum()),
    polar_above_examples=m.loc[(~low) & (d > 0.01), ["cell_id", "lat_deg", "lon_deg", "illum_frac", "irradiance_kwh_m2_day", "irradiance_toa_flat_kwh_m2_day"]].head(10).round(4).to_dict("records"))
# 3. bounds
def cnt(s, cond):
    return int(cond(s).sum())
chk["bounds"] = {
    "earth_slope_iso_outside_0_90": cnt(e["slope_iso_deg"], lambda s: (s < 0) | (s > 90)),
    "moon_slope_iso_outside_0_90": cnt(m["slope_iso_deg"], lambda s: (s < 0) | (s > 90)),
    "earth_roughness_negative": cnt(e["roughness_m"], lambda s: s < 0),
    "earth_mask_outside_0_1": cnt(e["mask_fraction"], lambda s: (s < 0) | (s > 1)),
    "earth_lst_amp_negative": cnt(e["lst_diurnal_amp_k"], lambda s: s < 0),
    "earth_tmin_below_-89.2C": cnt(e["tmin_c"], lambda s: s < -89.2),
    "earth_tmin_above_35C": cnt(e["tmin_c"], lambda s: s > 35),
    "moon_tmin_below_20K": cnt(m["tmin_k"], lambda s: s < 20),
    "moon_tmax_above_400K": cnt(m["tmax_k"], lambda s: s > 400),
    "moon_tmin_gt_tmax": int((m["tmin_k"] > m["tmax_k"]).sum()),
    "moon_amp_ne_tmax_minus_tmin_gt_0.02": int(((m["tmax_k"] - m["tmin_k"] - m["lst_diurnal_amp_k"]).abs() > 0.02).sum()),
    "moon_tmin_c_ne_tmin_k_minus_273.15_gt_0.02": int(((m["tmin_k"] - 273.15 - m["tmin_c"]).abs() > 0.02).sum()),
    "earth_elev_below_-430m_mask_ge_0.3": int(((e["elevation_m"] < -430) & (e["mask_fraction"] >= 0.3)).sum()),
    "earth_elev_below_-430m_any": int((e["elevation_m"] < -430).sum()),
    "earth_elev_below_-430m_cells": e.loc[e["elevation_m"] < -430, ["cell_id", "lat_deg", "lon_deg", "elevation_m", "mask_fraction", "n_dem_land_px"]].round(3).to_dict("records")[:20],
    "earth_lst_amp_max": float(e["lst_diurnal_amp_k"].max()),
}
# 4. tmin consistency on Earth: air minimum vs land surface mean
chk["earth_tmin_c_vs_temp_k"] = dict(cells_tmin_above_mean_lst=int(((e["tmin_c"] + 273.15) > e["temp_k"]).sum()),
                                      n=int((e["tmin_c"].notna() & e["temp_k"].notna()).sum()))
# 5. Earth Antarctic/Greenland: where are the coldest tmin cells
chk["earth_coldest_tmin_cells"] = e.nsmallest(5, "tmin_c")[["cell_id", "lat_deg", "lon_deg", "elevation_m", "tmin_c"]].to_dict("records")
chk["earth_tmin_dome_c_like_cells"] = e[(e["lat_deg"] == -75.5) & (e["lon_deg"].between(122, 125))][["cell_id", "lat_deg", "lon_deg", "elevation_m", "tmin_c"]].to_dict("records")
chk["earth_hottest_ground_irr"] = e.nlargest(5, "irradiance_kwh_m2_day")[["cell_id", "lat_deg", "lon_deg", "elevation_m", "irradiance_kwh_m2_day"]].to_dict("records")
chk["moon_coldest"] = m.nsmallest(5, "tmin_k")[["cell_id", "lat_deg", "lon_deg", "tmin_k", "tmax_k"]].to_dict("records")
chk["moon_hottest"] = m.nlargest(5, "tmax_k")[["cell_id", "lat_deg", "lon_deg", "tmax_k"]].to_dict("records")
chk["moon_equatorial_band_0_10N"] = {k: float(m.loc[m["lat_deg"].between(0, 10), k].median()) for k in ["tmax_k", "tmin_k", "lst_diurnal_amp_k"]}
chk["moon_slope_median_by_band"] = {f"{a}-{a+30}": float(m.loc[m["lat_deg"].abs().between(a, a + 30), "slope_iso_deg"].median()) for a in (0, 30, 60)}
chk["earth_toa_checks"] = {"equator": toa_e[0.5], "lat_16.5S": toa_e[-16.5], "lat_89.5": toa_e[89.5], "lat_-89.5": toa_e[-89.5]}
chk["moon_flat_toa"] = {"equator": toa_m[0.5], "22.5": toa_m[22.5]}
chk["body_mean_elevation"] = {"earth": float(mm_e), "moon": float(mm_m)}
# permafrost extent: area of cells where permafrost_area_frac is set, weighted
cell_area = (111.32 ** 2) * np.cos(np.radians(e["lat_deg"]))  # km2, spherical approx
pf = e["permafrost_area_frac"].fillna(0) * e["mask_fraction"].fillna(0) * cell_area
chk["permafrost_area_km2_approx"] = dict(all=float(pf.sum()), NH=float(pf[e["lat_deg"] > 0].sum()), SH=float(pf[e["lat_deg"] < 0].sum()),
                                         note="sum of permafrost_area_frac x land share x spherical cell area; permafrost_area_frac is the mean PERPROB probability of the land pixels")
chk["earth_land_area_km2_approx"] = float((e["mask_fraction"].fillna(0) * cell_area).sum())
dump("p6_ranges_checks.json", chk)
print(df.to_string())
print(json.dumps if False else "")
import json as _j
print(_j.dumps({k: chk[k] for k in ["earth_ground_over_toa", "moon_irr_minus_flat_formula", "bounds", "earth_tmin_c_vs_temp_k", "permafrost_area_km2_approx", "earth_toa_checks", "moon_flat_toa", "body_mean_elevation", "moon_equatorial_band_0_10N", "moon_slope_median_by_band", "earth_coldest_tmin_cells", "earth_tmin_dome_c_like_cells", "earth_hottest_ground_irr", "moon_coldest", "moon_hottest", "earth_land_area_km2_approx"]}, indent=1, default=float))
