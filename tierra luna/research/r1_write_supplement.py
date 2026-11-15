"""r1: write real_data/supplement/r1_terrain_{earth,moon}.csv (+ provenance) from research/out/r1_dem_*.npz. Deterministic."""
import os, numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); TL = os.path.dirname(HERE); SUP = os.path.join(TL, "real_data", "supplement")
os.makedirs(SUP, exist_ok=True)
for body, tab, pre in (("earth", "earth_real_1deg.csv", "E"), ("moon", "moon_real_1deg.csv", "M")):
    t = pd.read_csv(os.path.join(TL, "output_real", tab), usecols=["row", "col", "cell_id", "slope_iso_deg", "slope_iso_p90_deg", "roughness_m"]).sort_values(["row", "col"])
    d = np.load(os.path.join(HERE, "out", f"r1_dem_{body}.npz"))
    assert (t.cell_id.values == np.array([f"{pre}{i}" for i in range(64800)])).all()
    s, r1 = t.slope_iso_deg.to_numpy(float), t.roughness_m.to_numpy(float)
    with np.errstate(all="ignore"):
        out = pd.DataFrame({"cell_id": t.cell_id,
            "slope_p90_over_mean": np.round(np.where(s > 0, t.slope_iso_p90_deg.to_numpy(float) / s, np.nan), 4),
            "steep_frac_gt15deg": np.round(d["steep_frac_15"], 4),
            "steep_frac_gt10deg": np.round(d["steep_frac_10"], 4),
            "roughness_2lag_m": np.round(d["rough2_m"], 2),
            "hurst_h_1to2lag": np.round(np.where((r1 > 0) & (d["rough2_m"] > 0), np.log2(d["rough2_m"] / r1), np.nan), 4)})
    if body == "earth":
        out.loc[~np.isfinite(s), out.columns[1:]] = np.nan          # land cells only, as the table's relief columns
    out.to_csv(os.path.join(SUP, f"r1_terrain_{body}.csv"), index=False)
    print(body, {c: int(out[c].notna().sum()) for c in out.columns[1:]})
