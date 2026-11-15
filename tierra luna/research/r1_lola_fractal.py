"""r1: LOLA EXTRAS/FRACTAL (Rosenburg et al. 2011) median absolute along-track slope at 57 m (MAS_57M_16) and Hurst
exponent (HE_8), reduced to 1-degree cells (cos-lat weighted mean, missing excluded), and correlation with the table's
slope and roughness in the Rover zone (lat <= -75). Moon only: no Earth equivalent at 57 m in a single open file."""
import os, sys, numpy as np, pandas as pd
from scipy.stats import spearmanr
RAW = "/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/research-raw/lola_fractal"
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE)
def red(f, lines, ppd, sc, off):
    dn = np.fromfile(f"{RAW}/{f}", dtype="<i2").reshape(lines, lines * 2)
    bad = (dn == -32768)
    v = np.where(bad, np.nan, dn * sc + off)
    v = np.roll(v, -v.shape[1] // 2, axis=1)              # 0..360 -> -180..180
    lat = 90 - (np.arange(lines) + 0.5) / ppd
    w = np.repeat(np.cos(np.radians(lat))[:, None], v.shape[1], 1)
    ok = np.isfinite(v)
    b = lambda a: a.reshape(180, ppd, 360, ppd).sum((1, 3))
    num, den = b(np.where(ok, v * w, 0)), b(np.where(ok, w, 0))
    return np.where(den > 0, num / den, np.nan).ravel(), b(ok.astype(float)).ravel() / ppd ** 2
mas, cm = red("MAS_57M_16.IMG", 2880, 16, 0.0015, 45.0)
he, ch = red("HE_8.IMG", 1440, 8, 0.000025, 0.5)
M = pd.read_csv(os.path.join(TL, "output_real/moon_real_1deg.csv"), usecols=["row", "col", "cell_id", "lat_deg", "lon_deg", "slope_iso_deg", "roughness_m"]).sort_values(["row", "col"])
z = (M.lat_deg <= -75).to_numpy()
out = {"zone_cells": int(z.sum()), "mas_valid_zone": int(np.isfinite(mas[z]).sum()), "he_valid_zone": int(np.isfinite(he[z]).sum()),
       "mas_cov_median_zone": float(np.nanmedian(cm[z])), "he_cov_median_zone": float(np.nanmedian(ch[z])),
       "mas_q": np.nanpercentile(mas[z], [5, 50, 95]).round(3).tolist(), "he_q": np.nanpercentile(he[z], [5, 50, 95]).round(3).tolist()}
for n, a in (("mas57", mas), ("hurst_lola", he)):
    for c in ("slope_iso_deg", "roughness_m"):
        ok = z & np.isfinite(a) & M[c].notna().to_numpy()
        out[f"{n}_vs_{c}"] = round(float(spearmanr(a[ok], M[c].to_numpy()[ok])[0]), 3)
    ok = np.isfinite(a)
    out[f"{n}_vs_slope_global"] = round(float(spearmanr(a[ok], M.slope_iso_deg.to_numpy()[ok])[0]), 3)
# orientation check: Shackleton (~-89.9, 0) area and Tycho-ish? use the table: highest slope cell in zone vs mas there
i = int(np.nanargmax(np.where(z, M.slope_iso_deg, -1))); out["max_slope_zone_cell"] = [M.cell_id.iloc[i], float(M.lat_deg.iloc[i]), float(M.lon_deg.iloc[i]), float(M.slope_iso_deg.iloc[i]), float(mas[i])]
print(out)
pd.DataFrame({"cell_id": M.cell_id, "lola_mas57_deg": np.round(mas, 3), "lola_hurst": np.round(he, 4)}).to_csv(os.path.join(TL, "real_data/supplement/r1_lola_fractal_moon.csv"), index=False)
