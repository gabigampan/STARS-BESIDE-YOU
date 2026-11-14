"""Physical sanity of both tables: ranges, fill values, correlations, Earth-Moon contrast."""
import json
import numpy as np, pandas as pd
from scipy import stats

T = "/home/user/stars-beside-you/tierra luna/output_real/"
E = pd.read_csv(T + "earth_real_1deg.csv", keep_default_na=False, na_values=[""])
M = pd.read_csv(T + "moon_real_1deg.csv", keep_default_na=False, na_values=[""])
res = {}
for name, d in (("EARTH", E), ("MOON", M)):
    # grid
    assert len(d) == 64800 and d.cell_id.is_unique
    assert (d.lat_deg == 89.5 - d.row).all() and (d.lon_deg == -179.5 + d.col).all()
    assert (d.cell_id == name[0] + (d.row * 360 + d.col).astype(str)).all()
    assert d.row.iloc[0] == 0 and d.lat_deg.iloc[0] == 89.5 and d.lon_deg.iloc[0] == -179.5
    fills = {}
    for c in d.columns:
        if d[c].dtype.kind in "fi":
            v = d[c].values.astype(float)
            bad = np.isin(v, [-9999, -32768, -32767, 65535, -99999, 32767]) | (np.abs(v) > 1e20)
            if bad.any(): fills[c] = int(bad.sum())
        else:
            s = d[c].dropna().astype(str)
            bad = s.str.lower().isin(["nan", "none", "null", "-9999"])
            if bad.any(): fills[c] = int(bad.sum())
    res[name + "_fill_values"] = fills
    summ = {}
    for c in d.columns:
        if d[c].dtype.kind == "f":
            v = d[c].dropna()
            if len(v): summ[c] = dict(n=len(v), min=round(v.min(), 4), p1=round(v.quantile(.01), 4), med=round(v.median(), 4), p99=round(v.quantile(.99), 4), max=round(v.max(), 4))
        elif d[c].dtype == object or str(d[c].dtype).startswith("str"):
            summ[c] = d[c].fillna("<empty>").value_counts().to_dict() if d[c].nunique() < 12 else "many"
    res[name + "_summary"] = summ
land = E[E.mask_fraction >= 0.5]
alat = land.lat_deg.abs()
r = {}
r["earth_temp_vs_abslat_spearman"] = stats.spearmanr(alat, land.temp_k, nan_policy="omit").statistic
# partial correlation of temp with elevation, controlling latitude by 1-degree-row anomalies
anom = land.temp_k - land.groupby("row").temp_k.transform("mean")
eanom = land.elevation_m - land.groupby("row").elevation_m.transform("mean")
ok = anom.notna() & eanom.notna()
r["earth_temp_anom_vs_elev_anom_pearson"] = stats.pearsonr(eanom[ok], anom[ok]).statistic
sl = stats.linregress(eanom[ok], anom[ok]); r["earth_lapse_K_per_km"] = sl.slope * 1000
r["earth_tminc_vs_temp_k_pearson"] = stats.pearsonr(*land[["tmin_c", "temp_k"]].dropna().values.T).statistic
x = land[["lst_diurnal_amp_k", "rain_mm_day"]].dropna()
r["earth_amp_vs_rain_spearman"] = stats.spearmanr(x.lst_diurnal_amp_k, x.rain_mm_day).statistic
x = land[["rock_or_bare_frac", "rain_mm_day"]].dropna()
r["earth_bare_vs_rain_spearman"] = stats.spearmanr(x.rock_or_bare_frac, x.rain_mm_day).statistic
x = land[["irradiance_kwh_m2_day"]].assign(a=alat).dropna()
r["earth_irr_vs_abslat_spearman"] = stats.spearmanr(x.a, x.irradiance_kwh_m2_day).statistic
x = land[["slope_deg", "roughness_m"]].dropna()
r["earth_slope_vs_rough_spearman"] = stats.spearmanr(x.slope_deg, x.roughness_m).statistic
# a formula would show zero spread within a latitude row
for c in ("temp_k", "lst_diurnal_amp_k", "tmin_c", "irradiance_kwh_m2_day", "rain_mm_day"):
    r[f"earth_within_row_sd_median_{c}"] = float(land.groupby("row")[c].std().median())
r["moon_temp_vs_abslat_spearman"] = stats.spearmanr(M.lat_deg.abs(), M.temp_k, nan_policy="omit").statistic
r["moon_tmax_vs_abslat_spearman"] = stats.spearmanr(M.lat_deg.abs(), M.tmax_k, nan_policy="omit").statistic
for c in ("temp_k", "tmax_k", "tmin_k", "lst_diurnal_amp_k", "elevation_m", "rock_abundance_frac", "irradiance_kwh_m2_day", "sun_low_frac_0_5deg"):
    r[f"moon_within_row_sd_median_{c}"] = float(M.groupby("row")[c].std().median())
eq = M[M.lat_deg.abs() < 30]
x = eq[["rock_abundance_frac", "tmin_k"]].dropna()
tmin_anom = x.tmin_k - eq.loc[x.index].groupby("row").tmin_k.transform("mean")
r["moon_rock_vs_tmin_anom_spearman_|lat|<30"] = stats.spearmanr(x.rock_abundance_frac, tmin_anom).statistic
# Earth-Moon contrast
r["contrast_amp_median_earth_land"] = float(land.lst_diurnal_amp_k.median()); r["contrast_amp_max_earth"] = float(E.lst_diurnal_amp_k.max())
r["contrast_amp_median_moon"] = float(M.lst_diurnal_amp_k.median()); r["contrast_amp_min_moon"] = float(M.lst_diurnal_amp_k.min())
r["moon_cells_amp_le_earth_max"] = int((M.lst_diurnal_amp_k <= E.lst_diurnal_amp_k.max()).sum())
for c in ("slope_deg", "slope_iso_deg", "roughness_m", "slope_p90_deg"):
    r[f"contrast_{c}_median_earth_land"] = float(land[c].median()); r[f"contrast_{c}_median_moon"] = float(M[c].median())
    r[f"contrast_{c}_p99_earth_land"] = float(land[c].quantile(.99)); r[f"contrast_{c}_p99_moon"] = float(M[c].quantile(.99))
# R2 latitude profile (moon)
for lo, hi in ((0, 10), (40, 50), (80, 90)):
    s = M[(M.lat_deg > lo) & (M.lat_deg < hi)]
    r[f"moon_{lo}-{hi}N_median_tmax_tmin_amp"] = [round(float(s.tmax_k.median()), 1), round(float(s.tmin_k.median()), 1), round(float(s.lst_diurnal_amp_k.median()), 1)]
s = M[M.lat_deg < -80]; r["moon_80-90S_median_tmax_tmin_amp"] = [round(float(s.tmax_k.median()), 1), round(float(s.tmin_k.median()), 1), round(float(s.lst_diurnal_amp_k.median()), 1)]
r["moon_min_tmin_k_and_cell"] = [float(M.tmin_k.min()), M.loc[M.tmin_k.idxmin(), ["lat_deg", "lon_deg"]].tolist()]
r["moon_cells_tmax_below_110K"] = int((M.tmax_k < 110).sum())
r["earth_temp_k_max_and_cell"] = [float(E.temp_k.max()), E.loc[E.temp_k.idxmax(), ["lat_deg", "lon_deg"]].tolist()]
r["earth_elev_max_min"] = [float(E.elevation_m.max()), float(E.elevation_m.min())]
r["moon_elev_max_min"] = [float(M.elevation_m.max()), float(M.elevation_m.min())]
res["relations"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}
print(json.dumps(res["relations"], indent=1))
print("fill values:", res["EARTH_fill_values"], res["MOON_fill_values"])
json.dump(res, open("/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/verify/sanity.json", "w"), indent=1, default=str)
