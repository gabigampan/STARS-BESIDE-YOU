"""Self-check of output_real/earth_real_1deg.csv: ranges, coverage and known places.

    <venv>/bin/python real_data/check_earth.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "output_real" / "earth_real_1deg.csv"

MISSION_VARS = ["elevation_m", "mask_fraction", "slope_deg", "roughness_m", "rock_or_bare_frac",
                "temp_k", "lst_diurnal_amp_k", "tmin_c", "irradiance_kwh_m2_day", "sun_elev_max_deg",
                "sun_low_frac_0_5deg", "thermal_inertia_class", "permafrost_class", "rain_mm_day",
                "wind_max_ms"]
# (name, lat, lon): cell containing the point
PLACES = [
    ("Mount Everest", 27.988, 86.925), ("Central Sahara (Algeria-Libya border)", 25.5, 10.5),
    ("Atacama (Yungay)", -24.08, -69.92), ("Tibet (Changtang)", 33.5, 86.5),
    ("Death Valley (Badwater)", 36.25, -116.83), ("Dome C (Concordia)", -75.10, 123.35),
    ("Amazon (Manaus)", -3.10, -60.02), ("Iceland interior", 64.8, -18.5),
    ("Tabernas, Spain", 37.05, -2.39), ("Devon Island (Haughton)", 75.38, -89.68),
    ("Mauna Kea, Hawaii", 19.82, -155.47), ("Hanksville, Utah", 38.37, -110.71),
    ("Yakutsk", 62.03, 129.73), ("Longyearbyen, Svalbard", 78.22, 15.65),
    ("Dead Sea", 31.5, 35.5), ("Greenland Summit", 72.58, -38.46),
    ("South Pole", -89.99, 0.0), ("Equatorial Pacific (ocean)", 0.5, -150.5),
    ("Lut Desert, Iran", 30.5, 58.5), ("McMurdo Dry Valleys", -77.5, 162.5),
]


def cell_of(lat, lon):
    return int(np.floor(90 - lat)) * 360 + int(np.floor(lon + 180))


def main():
    df = pd.read_csv(CSV, keep_default_na=True)
    print(f"rows {len(df)}; unique cell_id {df.cell_id.nunique()}")
    land = df.mask_fraction > 0
    print(f"land cells (mask_fraction > 0): {int(land.sum())}; >= 0.3: {int((df.mask_fraction >= 0.3).sum())}")
    num = df.select_dtypes("number").columns
    print("\nrange of numeric columns (land cells):")
    for c in num:
        s = df.loc[land, c]
        print(f"  {c:28s} n={s.notna().sum():6d}  min={s.min():10.4g}  p50={s.median():10.4g}  max={s.max():10.4g}")
    for c in ("thermal_inertia_class", "permafrost_class"):
        print(f"\n{c}:", df.loc[land, c].fillna("<empty>").value_counts().to_dict())
    print("\nmission-variable completeness on land cells:")
    for v in MISSION_VARS:
        print(f"  {v:24s} {df.loc[land, v].notna().mean():.3f}")
    allp = df.loc[land, MISSION_VARS].notna().all(axis=1)
    print(f"land cells with every mission variable present: {int(allp.sum())} of {int(land.sum())}")
    no_pf = [v for v in MISSION_VARS if v != "permafrost_class"]
    print(f"... ignoring permafrost_class: {int(df.loc[land, no_pf].notna().all(axis=1).sum())}")
    i = df.lst_diurnal_amp_k.idxmax()
    j = df.lst_diurnal_amp_max_k.idxmax()
    print(f"\nlargest annual-mean diurnal amplitude {df.lst_diurnal_amp_k[i]:.2f} K at cell {df.cell_id[i]} "
          f"({df.lat_deg[i]}, {df.lon_deg[i]})")
    print(f"largest monthly diurnal amplitude {df.lst_diurnal_amp_max_k[j]:.2f} K at cell {df.cell_id[j]} "
          f"({df.lat_deg[j]}, {df.lon_deg[j]}) month {df.lst_diurnal_amp_max_month[j]}")
    print("top 5 annual amplitude:")
    print(df.nlargest(5, "lst_diurnal_amp_k")[["cell_id", "lat_deg", "lon_deg", "lst_diurnal_amp_k",
                                                 "lst_diurnal_amp_max_k", "elevation_m", "mask_fraction"]].to_string())
    show = ["cell_id", "elevation_m", "mask_fraction", "slope_deg", "slope_p90_deg", "roughness_m",
            "rock_or_bare_frac", "temp_k", "lst_diurnal_amp_k", "lst_diurnal_amp_max_k", "tmin_c",
            "irradiance_kwh_m2_day", "rain_mm_day", "wind_max_ms", "sun_elev_max_deg",
            "sun_low_frac_0_5deg", "thermal_inertia_class", "permafrost_class", "permafrost_area_frac"]
    print("\nplaces:")
    for name, la, lo in PLACES:
        r = df.iloc[cell_of(la, lo)]
        print(f"- {name} ({la}, {lo}) -> " + "; ".join(f"{k}={r[k]}" for k in show))


if __name__ == "__main__":
    main()
