"""Point B, Earth elevation_m -> elevation_rel_m: sensitivity of the Rover ranking to how the Earth body mean
is weighted (own implementation of the real_value_tolerance rule, not the engine's):
  A  cos(lat) mean over every Earth cell with a value (the shipped definition, 695.92 m)
  B  cos(lat) x land share mean (the mean height of the land area, 810.71 m)
First reproduces the bundle's rover top 5 and its similarities with A, then reruns with B.
Suitability is taken from the bundle (it does not depend on the mean).
Run:  $PY -I "tierra luna/audit/p6_elev_mean_sensitivity.py"      Output: out/p6_elev_mean_sensitivity.json
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p6_common import Bundle, dump, load_tables  # noqa: E402

e, m = load_tables()
B = Bundle()
ids = B.col("earth_base.bin", "id")
li = B.col("earth_rover.bin", "land_index")
suit = B.col("earth_rover.bin", "suitability")
b_rank = B.col("earth_rover.bin", "rank")
b_sim = B.col("earth_rover.bin", "similarity")
b_twin = B.col("earth_rover.bin", "twin")
pid = ids[li]
E = e.set_index(e["cell_id"].str[1:].astype(int)).loc[pid]
x = e.dropna(subset=["elevation_m"])
w = np.cos(np.radians(x.lat_deg))
means = {"A_cos_all_cells": float((x.elevation_m * w).sum() / w.sum()),
         "B_cos_x_land_share": float((x.elevation_m * w * x.mask_fraction).sum() / (w * x.mask_fraction).sum())}
mw = np.cos(np.radians(m.lat_deg))
moon_mean = float((m.elevation_m * mw).sum() / mw.sum())
Z = m[m.lat_deg <= -75.0]
zs, zr, ze, zid = Z.slope_iso_deg.values, Z.roughness_m.values, Z.elevation_m.values - moon_mean, Z.cell_id.str[1:].astype(int).values
es, er = E.slope_iso_deg.values, E.roughness_m.values
out = {"means_m": means, "moon_mean_m": moon_mean}
for tag, mu in means.items():
    ee = E.elevation_m.values - mu
    sim = np.full(len(E), np.nan)
    twin = np.full(len(E), -1)
    for a in range(0, len(E), 256):
        sl = slice(a, a + 256)
        ds = np.abs(es[sl, None] - zs[None])
        dr = np.abs(er[sl, None] - zr[None])
        de = np.abs(ee[sl, None] - ze[None])
        sc = np.round(np.exp(-0.5 * (ds / 2.0) ** 2), 6) * 0.4 + np.round(np.exp(-0.5 * (dr / 30.0) ** 2), 6) * 0.4 + np.round(np.exp(-0.5 * (de / 500.0) ** 2), 6) * 0.2
        ok = (ds <= 2.0) & (dr <= 30.0) & (de <= 1000.0)
        ok &= np.isfinite(es[sl, None]) & np.isfinite(er[sl, None])
        sc = np.where(ok, sc, -1.0)
        # ties to the lowest id: zone cells are in ascending id order already
        j = np.argmax(sc, axis=1)
        best = sc[np.arange(sc.shape[0]), j]
        has = best >= 0
        sim[sl] = np.where(has, 100 * best, np.nan)
        twin[sl] = np.where(has, zid[j], -1)
    sim2 = np.round(sim, 2)
    final = np.round(0.5 * sim2 + 0.5 * suit, 2)
    order = sorted([i for i in range(len(E)) if np.isfinite(final[i])], key=lambda i: (-final[i], pid[i]))
    top = [dict(rank=k + 1, earth=f"E{pid[i]}", moon=f"M{twin[i]}", similarity=float(sim2[i]), suitability=float(suit[i]), final=float(final[i])) for k, i in enumerate(order[:10])]
    res = dict(mean=mu, paired=int(np.isfinite(sim).sum()), top10=top)
    if tag.startswith("A"):
        okb = np.isfinite(b_sim)
        res["check_vs_bundle"] = dict(max_abs_sim_diff=float(np.nanmax(np.abs(sim2[okb] - b_sim[okb]))),
                                      twin_mismatches=int((twin[okb] != b_twin[okb]).sum()),
                                      paired_bundle=int(okb.sum()))
    out[tag] = res
dump("p6_elev_mean_sensitivity.json", out)
import json
print(json.dumps(out, indent=1, default=float))
