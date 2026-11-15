"""Point 1 (input data): levels and sources of every variable a mission uses, units at every
step, and the treatment of ocean, ice and missing values, with own code.

    <venv>/bin/python "tierra luna/audit/p1_inputs.py"

Deterministic. Writes out/p1_inputs.json and out/p1_variables.csv.

Own implementations (not the engine's):
* Earth top-of-atmosphere insolation: day-by-day numerical integration of the instantaneous
  flux over the hour angle (midpoint rule, 1440 steps), declination and distance from a Newton
  solution of Kepler's equation on 3653 days; NOT the closed-form sunset-angle formula of
  engine/real_similarity.py. Same physical constants (solar constant 1361 W/m2, obliquity 23.44,
  e = 0.0167, perihelion longitude 282.9) read from engine_config.json.
* Moon flat-ground irradiance (|lat| < 65.5): same integration with obliquity 1.54 deg (the value
  REAL_DATA.md cites), to test the lunar table's irradiance definition and unit.
* body-mean elevations for elevation_rel_m: own cos-lat weighted means from the tables.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p1_common as C  # noqa: E402

MISSIONS = ["rover", "solar", "lunar_base"]


def kepler_E(M, e):
    E = M.copy()
    for _ in range(50):
        E = E - (E - e * np.sin(E) - M) / (1 - e * np.cos(E))
    return E


def insolation_numeric(lat_deg, S0, eps_deg, ecc, lperi_deg, ndays=3653, nh=1440):
    """Annual-mean daily insolation on a horizontal surface, kWh/m2/day (own integration)."""
    M = (np.arange(ndays) + 0.5) / ndays * 2 * np.pi
    E = kepler_E(M, ecc)
    nu = 2 * np.arctan2(math.sqrt(1 + ecc) * np.sin(E / 2), math.sqrt(1 - ecc) * np.cos(E / 2))
    r = 1 - ecc * np.cos(E)
    dec = np.arcsin(math.sin(math.radians(eps_deg)) * np.sin(nu + math.radians(lperi_deg)))
    H = (np.arange(nh) + 0.5) / nh * 2 * np.pi - np.pi
    out = []
    for la in np.atleast_1d(lat_deg):
        p = math.radians(la)
        mu = math.sin(p) * np.sin(dec)[:, None] + math.cos(p) * np.cos(dec)[:, None] * np.cos(H)[None, :]
        q = S0 / r[:, None] ** 2 * np.clip(mu, 0, None)        # W/m2 instantaneous
        out.append(q.mean() * 24 / 1000.0)                     # kWh/m2/day, mean over days and hours
    return np.array(out)


def main():
    b = C.Bundle()
    e, m = C.load_tables()
    cfg = C.jload(os.path.join(C.TL, "engine", "engine_config.json"))
    toa = cfg["toa_insolation"]["value"]
    res = {}

    # ---------------------------------------------------------------- 1. levels, everywhere
    pe = pd.read_csv(os.path.join(C.TL, "real_data", "provenance_earth.csv"))
    pm = pd.read_csv(os.path.join(C.TL, "real_data", "provenance_moon.csv"))
    var = b.json("variables.json")
    rows = []
    for x in var["variables"]:
        for body, prov in (("EARTH", pe), ("MOON", pm)):
            bb = x["bodies"].get(body, {})
            col = bb.get("column")
            pr = prov[prov["variable"] == col]
            rows.append({"variable": x["name"], "body": body, "column": col, "unit_bundle": x["unit"],
                         "level_bundle": bb.get("level"),
                         "level_provenance": pr["level"].iloc[0] if len(pr) else None,
                         "product": pr["product"].iloc[0] if len(pr) else None,
                         "version": pr["version"].iloc[0] if len(pr) else None,
                         "native_resolution": pr["native_resolution"].iloc[0] if len(pr) else None,
                         "url": pr["url"].iloc[0] if len(pr) else None,
                         "used_by": json.dumps(x.get("used_by")), "stored": bb.get("stored")})
    vt = pd.DataFrame(rows)
    vt["level_agrees"] = [(a == b_) or (a == "NO_DATA" and b_ == "no data") for a, b_ in
                          zip(vt["level_bundle"], vt["level_provenance"])]
    vt.to_csv(os.path.join(C.OUT, "p1_variables.csv"), index=False)
    res["level_disagreements"] = vt[~vt["level_agrees"]][["variable", "body", "level_bundle", "level_provenance"]].to_dict("records")

    # ---------------------------------------------------------------- 2. units
    u = {}
    # Moon: tmin_c = tmin_k - 273.15 ; amplitude = tmax - tmin
    u["moon_tmin_c_minus_tmin_k_plus_273.15_max_abs"] = float(np.abs(m["tmin_c"] - (m["tmin_k"] - 273.15)).max())
    u["moon_amp_minus_tmax_minus_tmin_max_abs"] = float(np.abs(m["lst_diurnal_amp_k"] - (m["tmax_k"] - m["tmin_k"])).max())
    # Earth tmin_k in the bundle pairs = tmin_c + 273.15 (land_index -> earth_base)
    tmin_c_bundle = b.col("earth_base.bin", "v.tmin_c")
    li = b.col("earth_lunar_base.bin", "land_index").astype(int)
    rank = b.col("earth_lunar_base.bin", "rank")
    lo = b.col("earth_lunar_base_pairs.bin", "list_order")
    pk = b.files["earth_lunar_base_pairs.bin"]
    tk_e = b.col("earth_lunar_base_pairs.bin", "tmin_k.earth")
    tk_m = b.col("earth_lunar_base_pairs.bin", "tmin_k.moon")
    # list_order -> rows of earth_lunar_base.bin
    order = lo.astype(int)
    base_rows = np.flatnonzero(np.isfinite(rank))
    # pairs rows correspond to the mission file rows given by list_order (contract): test both
    cand = {}
    for name, idx in (("pairs_row_is_mission_row", np.arange(len(tk_e))), ("pairs_row_by_list_order", order)):
        try:
            k = li[idx]
            d = tk_e - (tmin_c_bundle[k] + 273.15)
            cand[name] = float(np.nanmax(np.abs(d)))
        except Exception as exc:  # noqa
            cand[name] = repr(exc)
    u["earth_tmin_k_pairs_minus_tmin_c_plus_273.15"] = cand
    u["pairs_file_rows"] = int(len(tk_e))
    u["lunar_base_mission_rows"] = int(len(li))
    # tmin_k.moon vs lunar table tmin_k of the twin
    twin = b.col("earth_lunar_base.bin", "twin")
    if len(tk_m) == len(twin):
        ok = np.isfinite(twin)
        u["moon_tmin_k_pairs_minus_table_tmin_k"] = float(np.nanmax(np.abs(tk_m[ok] - m["tmin_k"].to_numpy()[twin[ok].astype(int)])))
    # TOA insolation, own numerical integration vs the bundle d.irradiance_toa_kwh_m2_day
    lat_b = b.col("earth_base.bin", "lat")                      # per grid row (180)
    toa_rows = b.col("earth_base.bin", "d.irradiance_toa_kwh_m2_day")
    u["earth_base_lat_rows_ok"] = bool(np.allclose(lat_b, 89.5 - np.arange(180)))
    own = insolation_numeric(lat_b, toa["solar_constant_w_m2"], toa["obliquity_deg"], toa["eccentricity"],
                             toa["sun_longitude_at_perihelion_deg"])
    d = toa_rows - own
    u["earth_toa_bundle_minus_own_max_abs_kwh"] = float(np.nanmax(np.abs(d)))
    u["earth_toa_rows_stored"] = int(np.isfinite(toa_rows).sum())
    land_row = b.col("earth_base.bin", "id").astype(int) // 360
    toa_b = toa_rows[land_row]
    u["earth_toa_own_at"] = {str(k): round(float(insolation_numeric([k], toa["solar_constant_w_m2"], toa["obliquity_deg"],
                                                                     toa["eccentricity"], toa["sun_longitude_at_perihelion_deg"])[0]), 3)
                             for k in (0.0, 30.0, 45.0, 60.0, -16.5)}
    u["earth_toa_reference_values_config"] = toa["reference_values_kwh_m2_day"]
    # Moon irradiance definition: own flat-ground integration with eps 1.54 deg at |lat| < 65.5
    mlat = np.unique(m["lat_deg"][np.abs(m["lat_deg"]) < 65.5])
    mown = dict(zip(mlat, insolation_numeric(mlat, 1361.0, 1.54, toa["eccentricity"], toa["sun_longitude_at_perihelion_deg"])))
    md = m[np.abs(m["lat_deg"]) < 65.5]
    dd = md["irradiance_kwh_m2_day"].to_numpy() - np.array([mown[x] for x in md["lat_deg"]])
    u["moon_irradiance_table_minus_own_flat_max_abs_kwh"] = float(np.abs(dd).max())
    u["moon_irradiance_note"] = "own integration includes the 1/r^2 eccentricity factor; the table's builder may not (difference shows it)"
    # Earth ground irradiance range (WorldClim srad, kWh/m2/day)
    land = e["mask_fraction"] > 0
    u["earth_ground_irradiance_range_land"] = [float(e.loc[land, "irradiance_kwh_m2_day"].min()),
                                              float(e.loc[land, "irradiance_kwh_m2_day"].max())]
    u["earth_ground_over_toa_max"] = float(np.nanmax(b.col("earth_base.bin", "v.irradiance_kwh_m2_day") / toa_b))
    # relative elevation: own body means
    wE = np.cos(np.radians(e["lat_deg"]))
    okE = e["elevation_m"].notna()
    meanE = float((e.loc[okE, "elevation_m"] * wE[okE]).sum() / wE[okE].sum())
    wM = np.cos(np.radians(m["lat_deg"]))
    meanM = float((m["elevation_m"] * wM).sum() / wM.sum())
    u["body_mean_elevation_own"] = {"EARTH_land_cells": meanE, "EARTH_cells_in_mean": int(okE.sum()), "MOON": meanM}
    er = b.col("earth_rover_pairs.bin", "elevation_rel_m.earth")
    mr = b.col("earth_rover_pairs.bin", "elevation_rel_m.moon")
    lir = b.col("earth_rover.bin", "land_index").astype(int)
    twr = b.col("earth_rover.bin", "twin")
    elev_b = b.col("earth_base.bin", "v.elevation_m")
    if len(er) == len(lir):
        ok = np.isfinite(er)
        u["rover_elev_rel_earth_minus_own_max_abs_m"] = float(np.nanmax(np.abs(er[ok] - (elev_b[lir[ok]] - meanE))))
        ok2 = np.isfinite(mr) & np.isfinite(twr)
        u["rover_elev_rel_moon_minus_own_max_abs_m"] = float(np.nanmax(np.abs(
            mr[ok2] - (m["elevation_m"].to_numpy()[twr[ok2].astype(int)] - meanM))))
    res["units"] = u

    # ---------------------------------------------------------------- 3. ocean, ice, missing
    ids = b.col("earth_base.bin", "id").astype(int)
    tab = e.set_index(np.arange(len(e)))
    miss = {}
    sim_cols = {"rover": ["slope_iso_deg", "roughness_m", "elevation_m"],
                "solar": ["slope_iso_deg", "roughness_m"],
                "lunar_base": ["tmin_c", "lst_diurnal_amp_k", "slope_iso_deg", "roughness_m"]}
    for mi in MISSIONS:
        li = b.col(f"earth_{mi}.bin", "land_index").astype(int)
        rk = b.col(f"earth_{mi}.bin", "rank")
        ranked = ids[li[np.isfinite(rk)]]
        t = tab.iloc[ranked]
        miss[mi] = {
            "ranked": int(len(ranked)),
            "mask_fraction_lt_0.3": int((t["mask_fraction"] < 0.3).sum()),
            "mask_fraction_eq_0": int((t["mask_fraction"] == 0).sum()),
            "elevation_missing": int(t["elevation_m"].isna().sum()),
            "thermal_class_agua": int((t["thermal_inertia_class"] == "agua").sum()),
            "thermal_class_hielo": int((t["thermal_inertia_class"] == "hielo").sum()),
            "snow_ice_frac_ge_0.5": int((t["snow_ice_frac"] >= 0.5).sum()),
            "lc_dominant_220_snow_ice": int((t["lc_dominant_cci_code"] == 220).sum()),
            "lat_le_-60_antarctic": int((t["lat_deg"] <= -60).sum()),
            "missing_similarity_input": {c: int(t[c].isna().sum()) for c in sim_cols[mi]},
            "mask_fraction_min": float(t["mask_fraction"].min()),
        }
        if mi == "rover":
            ice = t[(t["snow_ice_frac"] >= 0.5) | (t["thermal_inertia_class"] == "hielo")]
            rk_r = rk[np.isfinite(rk)]
            miss[mi]["ice_cells_best_rank"] = int(rk_r[np.isin(ranked, ice.index.to_numpy())].min()) if len(ice) else None
            miss[mi]["ice_cells_in_top_100"] = int(((rk_r <= 100) & np.isin(ranked, ice.index.to_numpy())).sum())
            miss[mi]["greenland_box_ice"] = int(((ice["lat_deg"] > 59) & (ice["lon_deg"] > -75) & (ice["lon_deg"] < -10)).sum())
    res["ranked_integrity"] = miss
    # land cells removed by each common gate
    landc = e[e["mask_fraction"] > 0]
    res["land_cells"] = {"mask_fraction_gt_0": int(len(landc)),
                         "fail_mask_lt_0.3": int((landc["mask_fraction"] < 0.3).sum()),
                         "elevation_missing": int(landc["elevation_m"].isna().sum()),
                         "elevation_lt_1": int((landc["elevation_m"] < 1).sum()),
                         "pass_both_common_gates": int(((landc["mask_fraction"] >= 0.3) & (landc["elevation_m"] >= 1)).sum()),
                         "lst_missing": int(landc["lst_diurnal_amp_k"].isna().sum()),
                         "tmin_missing": int(landc["tmin_c"].isna().sum()),
                         "slope_iso_missing": int(landc["slope_iso_deg"].isna().sum()),
                         "roughness_missing": int(landc["roughness_m"].isna().sum())}
    res["moon"] = {"permafrost_class_values": m["permafrost_class"].value_counts(dropna=False).to_dict(),
                   "thermal_inertia_class_values": m["thermal_inertia_class"].value_counts(dropna=False).to_dict(),
                   "rain_non_null": int(m["rain_mm_day"].notna().sum()), "wind_non_null": int(m["wind_max_ms"].notna().sum())}
    C.write_json("p1_inputs.json", res)
    print(json.dumps(res, indent=1, default=C._default))


if __name__ == "__main__":
    main()
