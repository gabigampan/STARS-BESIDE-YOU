"""Point B/C, Moon: the LOLA team's own slope product LDSM_16 (PDS, LOLA GDR, 16 px/deg; label: "slope
baseline may vary from 30 to 120 meters" and "slope at a baseline of 240 meters") as an external BOUND for
the tables' km-baseline slope (same altimeter, different processing and much shorter baseline, so the
LDSM value must be the larger one: slopes fall with baseline for Hurst exponents < 1).
Reads the label for layout, checks the longitude alignment against the table by correlation, then gives
global/zone statistics and the 11 distinct lunar cells of the audio pairs.
Run:  $PY -I "tierra luna/audit/p6_lunar_ext.py"      Output: out/p6_lunar_ext.json
"""
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import REPO, dump, load_tables  # noqa: E402

EXT = os.environ.get("P6_EXT", "/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/ext")
lbl = open(os.path.join(EXT, "lola", "ldsm_16.lbl")).read()
lines = int(re.search(r"LINES\s*=\s*(\d+)", lbl).group(1))
samples = int(re.search(r"LINE_SAMPLES\s*=\s*(\d+)", lbl).group(1))
sf = float(re.search(r"SCALING_FACTOR\s*=\s*([\d.]+)", lbl).group(1))
off = float(re.search(r"OFFSET\s*=\s*([\d.\-]+)", lbl).group(1))
a = np.fromfile(os.path.join(EXT, "lola", "ldsm_16.img"), dtype="<i2").reshape(lines, samples).astype(float) * sf + off
# 16 px/deg: block 16x16 -> 1 degree; rows from 90N; columns from 0 E eastward (to be checked)
blk = a.reshape(180, 16, 360, 16)
lat_px = 90 - (np.arange(lines) + 0.5) / 16
w = np.cos(np.radians(lat_px)).reshape(180, 16, 1, 1)
cell = (blk * w).sum(axis=(1, 3)) / (w.sum(axis=1, keepdims=True).sum() / 180 * 16)  # placeholder, replaced below
cell = (blk * w).sum(axis=(1, 3)) / (w * np.ones_like(blk)).sum(axis=(1, 3))
_, m = load_tables()
tab = m["slope_iso_deg"].values.reshape(180, 360)
best = None
for shift in (0, 180):
    c = np.roll(cell, -shift if shift else 0, axis=1) if False else np.roll(cell, shift, axis=1)
    band = slice(30, 150)  # 60S-60N, away from the poles
    r = np.corrcoef(c[band].ravel(), tab[band].ravel())[0, 1]
    if best is None or r > best[1]:
        best = (shift, r)
shift = best[0]
cellg = np.roll(cell, shift, axis=1)
res = dict(label=dict(lines=lines, samples=samples, scaling=sf, offset=off,
                      baseline_text=[s.strip() for s in re.findall(r'"([^"]*baseline[^"]*)"', lbl, flags=re.S)][:2]),
           alignment=dict(roll_columns=shift, corr_60S_60N=round(float(best[1]), 4)))
ratio = cellg / tab
res["global"] = dict(ldsm_cell_mean_median=round(float(np.median(cellg)), 3), table_slope_iso_median=round(float(np.median(tab)), 3),
                     cells_where_table_gt_ldsm=int((tab > cellg).sum()), ratio_p10_p50_p90=[round(float(x), 3) for x in np.percentile(ratio, [10, 50, 90])])
top = json.load(open(os.path.join(REPO, "docs", "AUDIO_TOP5.json"), encoding="utf-8"))
cells = {}
for mis, x in top["missions"].items():
    for p in x["pairs"]:
        cells.setdefault(p["moon_cell_id"], []).append(f"{mis}#{p['rank']}")
res["audio_cells"] = []
for cid, uses in cells.items():
    i = int(cid[1:])
    r, c = divmod(i, 360)
    res["audio_cells"].append(dict(cell=cid, uses=uses, lat=89.5 - r, lon=-179.5 + c, table_slope_iso_deg=float(tab[r, c]),
                                   ldsm_cell_mean_deg=round(float(cellg[r, c]), 3), ldsm_over_table=round(float(cellg[r, c] / tab[r, c]), 2)))
# zones: rover lat <= -75, solar maria |lat|<=30 & elev <= -1200
lat = m["lat_deg"].values.reshape(180, 360)
el = m["elevation_m"].values.reshape(180, 360)
for name, z in {"rover_zone": lat <= -75, "solar_zone": (np.abs(lat) <= 30) & (el <= -1200)}.items():
    res[name] = dict(n=int(z.sum()), ldsm_median=round(float(np.median(cellg[z])), 3), table_median=round(float(np.median(tab[z])), 3))
dump("p6_lunar_ext.json", res)
print(json.dumps(res, indent=1, default=float))
