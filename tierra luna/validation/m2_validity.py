"""Metric 2: validity against a stated schema (units, physical ranges, coordinates in
range, cell centres on the grid, no duplicate ids), per table, every failure counted by
kind and listed in validation/out/m2_validity_failures.csv.

The schema below is this document's own (docs/VALIDATION.md section 2), written from
the units in real_data/provenance_*.csv. Bounds are physical plausibility limits, wide
on purpose: a failure means "impossible or inconsistent", not "unusual". A missing
value is not a failure (missing stays missing); it is counted under metric 1.
"""
from __future__ import annotations

import math
import os
from typing import Dict, List

import numpy as np
import pandas as pd

from common import BUNDLE, MISSIONS, REAL_DIR, bundle, context, load_json, write_csv

S0 = 1361.0  # W/m2, the solar constant cited in real_data/provenance_moon.csv (NASA NSSDC Moon fact sheet)
MOON_IRR_MAX = S0 * 24.0 / math.pi / 1000.0   # annual-mean daily insolation at the lunar equator, kWh/m2/day

THERMAL_CLASSES = {"roca", "regolito", "arena", "suelo", "hielo", "agua"}
PERMAFROST_CLASSES = {"continuo", "discontinuo", "esporadico", "ninguno"}

# column: (unit, min, max, why)
EARTH_RANGES = {
    "cell_km": ("km", 110.0, 112.0, "WGS84 meridian arc of 1 degree (110.57-111.69 km, provenance_earth.csv)"),
    "elevation_m": ("m", -430.0, 8849.0, "land surface: no dry land lies below about -430 m (Dead Sea shore) or above 8,849 m"),
    "elevation_all_m": ("m", -11000.0, 8849.0, "land and sea floor"),
    "mask_fraction": ("1", 0.0, 1.0, "fraction"),
    "slope_deg": ("deg", 0.0, 90.0, "angle"), "slope_p90_deg": ("deg", 0.0, 90.0, "angle"),
    "slope_iso_deg": ("deg", 0.0, 90.0, "angle"), "slope_iso_p90_deg": ("deg", 0.0, 90.0, "angle"),
    "roughness_m": ("m", 0.0, 5000.0, "RMS height difference is non-negative"),
    "rock_or_bare_frac": ("1", 0.0, 1.0, "fraction"), "bare_frac": ("1", 0.0, 1.0, "fraction"),
    "snow_ice_frac": ("1", 0.0, 1.0, "fraction"), "permafrost_area_frac": ("1", 0.0, 1.0, "fraction"),
    "temp_k": ("K", 180.0, 340.0, "annual-mean land surface temperature"),
    "lst_diurnal_amp_k": ("K", 0.0, 60.0, "an amplitude (day minus night) of a land surface is expected to be >= 0"),
    "lst_diurnal_amp_max_k": ("K", 0.0, 80.0, "largest monthly amplitude, >= 0"),
    "lst_diurnal_amp_max_month": ("month", 1.0, 12.0, "calendar month"),
    "tmin_c": ("degC", -90.0, 35.0, "coldest-month minimum air temperature"),
    "irradiance_kwh_m2_day": ("kWh/m2/day", 0.0, 12.0, "ground irradiance; also checked against the top of the atmosphere"),
    "sun_elev_max_deg": ("deg", 0.0, 90.0, "angle"), "sun_low_frac_0_5deg": ("1", 0.0, 1.0, "fraction"),
    "rain_mm_day": ("mm/day", 0.0, 40.0, "annual mean precipitation"),
    "wind_max_ms": ("m/s", 0.0, 60.0, "monthly mean wind speed"),
    "lc_dominant_cci_code": ("code", 10.0, 220.0, "ESA CCI LCCS legend codes 10-220"),
    "n_dem_land_px": ("count", 0.0, 1e9, ">= 0"), "n_dem_slope_px": ("count", 0.0, 1e9, ">= 0"),
    "n_lst_px": ("count", 0.0, 1e9, ">= 0"), "n_worldclim_px": ("count", 0.0, 1e9, ">= 0"),
    "n_permafrost_px": ("count", 0.0, 1e9, ">= 0"),
}
MOON_RANGES = {
    "cell_km": ("km", 30.0, 31.0, "1 degree on a 1737.4 km sphere = 30.32 km"),
    "elevation_m": ("m", -9500.0, 11000.0, "LOLA heights above the 1737.4 km sphere"),
    "slope_deg": ("deg", 0.0, 90.0, "angle"), "slope_p90_deg": ("deg", 0.0, 90.0, "angle"),
    "slope_iso_deg": ("deg", 0.0, 90.0, "angle"), "slope_iso_p90_deg": ("deg", 0.0, 90.0, "angle"),
    "roughness_m": ("m", 0.0, 5000.0, ">= 0"),
    "mask_fraction": ("1", 0.0, 1.0, "fraction"), "rock_or_bare_frac": ("1", 0.0, 1.0, "fraction"),
    "rock_abundance_frac": ("1", 0.0, 1.0, "fraction"), "illum_frac": ("1", 0.0, 1.0, "fraction"),
    "temp_k": ("K", 0.0, 420.0, "lunar surface"), "tmax_k": ("K", 0.0, 420.0, "lunar surface"),
    "tmin_k": ("K", 0.0, 420.0, "lunar surface"), "lst_diurnal_amp_k": ("K", 0.0, 420.0, ">= 0"),
    "tmin_c": ("degC", -273.15, 147.0, "above absolute zero"),
    "irradiance_kwh_m2_day": ("kWh/m2/day", 0.0, MOON_IRR_MAX + 1e-3,
                              f"cannot exceed the equatorial annual mean S0*24/pi/1000 = {MOON_IRR_MAX:.4f}"),
    "sun_elev_max_deg": ("deg", 0.0, 90.0, "angle"), "sun_low_frac_0_5deg": ("1", 0.0, 1.0, "fraction"),
    "temp_n_subcells": ("count", 1.0, 1e9, ">= 1"),
}


def _num(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s, errors="coerce").to_numpy(dtype=np.float64)


def check_table(df: pd.DataFrame, table: str, body: str, ranges: Dict, prefix: str) -> List[Dict]:
    """Failures [{table, record, kind, column, value}] of one cell table."""
    fails: List[Dict] = []

    def add(mask, kind, column, values=None):
        for i in np.flatnonzero(mask):
            fails.append({"table": table, "record": str(df["cell_id"].iat[i]), "kind": kind, "column": column,
                          "value": None if values is None else values[i]})

    row, col = _num(df["row"]), _num(df["col"])
    lat, lon = _num(df["lat_deg"]), _num(df["lon_deg"])
    add(~np.isfinite(row) | (row < 0) | (row > 179) | (row != np.floor(row)), "row_out_of_grid", "row", row)
    add(~np.isfinite(col) | (col < 0) | (col > 359) | (col != np.floor(col)), "col_out_of_grid", "col", col)
    add(~np.isfinite(lat) | (lat < -90) | (lat > 90), "lat_out_of_range", "lat_deg", lat)
    add(~np.isfinite(lon) | (lon < -180) | (lon > 180), "lon_out_of_range", "lon_deg", lon)
    add(np.abs(lat - (89.5 - row)) > 1e-9, "lat_not_cell_centre", "lat_deg", lat)
    add(np.abs(lon - (-179.5 + col)) > 1e-9, "lon_not_cell_centre", "lon_deg", lon)
    expect = np.array([f"{prefix}{int(r) * 360 + int(c)}" if np.isfinite(r) and np.isfinite(c) else ""
                       for r, c in zip(row, col)])
    add(df["cell_id"].astype(str).to_numpy() != expect, "id_not_row_col", "cell_id")
    add(df["cell_id"].duplicated(keep=False).to_numpy(), "duplicate_id", "cell_id")
    add(df.duplicated(["row", "col"], keep=False).to_numpy(), "duplicate_row_col", "row,col")
    add(df["body"].astype(str).to_numpy() != body, "wrong_body", "body")
    for c, (unit, lo, hi, _why) in ranges.items():
        if c not in df.columns:
            fails.append({"table": table, "record": "*", "kind": "column_missing", "column": c, "value": None})
            continue
        v = _num(df[c])
        ok = np.isfinite(v)
        add(ok & (v < lo), "below_physical_min", c, v)
        add(ok & (v > hi), "above_physical_max", c, v)
    for c, allowed in (("thermal_inertia_class", THERMAL_CLASSES), ("permafrost_class", PERMAFROST_CLASSES)):
        s = df[c]
        present = s.notna() & ~s.astype(str).str.strip().str.lower().isin(["", "nan", "none"])
        add((present & ~s.astype(str).isin(allowed)).to_numpy(), "unknown_category", c)
    return fails


def consistency_earth(df: pd.DataFrame, c: Dict) -> List[Dict]:
    """Earth ground irradiance cannot exceed the sunlight above the atmosphere at the
    same latitude (the engine's DERIVED top-of-atmosphere value, docs/ASSUMPTIONS 0.12)."""
    dv = c["results"]["solar"].extra["real"]["derived"].values["irradiance_toa_kwh_m2_day"]["EARTH"]
    ids = (df["row"].to_numpy() * 360 + df["col"].to_numpy())
    toa = np.asarray(dv)[np.searchsorted(c["cells"]["EARTH"]["id"].to_numpy(), ids)]
    g = _num(df["irradiance_kwh_m2_day"])
    bad = np.isfinite(g) & np.isfinite(toa) & (g > toa)
    return [{"table": "earth_real_1deg.csv", "record": str(df["cell_id"].iat[i]), "kind": "ground_above_toa",
             "column": "irradiance_kwh_m2_day", "value": g[i]} for i in np.flatnonzero(bad)]


def consistency_moon(df: pd.DataFrame) -> List[Dict]:
    out = []
    tk, tc = _num(df["tmin_k"]), _num(df["tmin_c"])
    for i in np.flatnonzero(np.abs((tk - 273.15) - tc) > 0.011):
        out.append({"table": "moon_real_1deg.csv", "record": str(df["cell_id"].iat[i]), "kind": "tmin_c_not_tmin_k_minus_273.15",
                    "column": "tmin_c", "value": tc[i]})
    lo, mid, hi = _num(df["tmin_k"]), _num(df["temp_k"]), _num(df["tmax_k"])
    for i in np.flatnonzero((lo > mid + 1e-6) | (mid > hi + 1e-6)):
        out.append({"table": "moon_real_1deg.csv", "record": str(df["cell_id"].iat[i]), "kind": "not_tmin<=temp<=tmax",
                    "column": "temp_k", "value": mid[i]})
    for col in ("rain_mm_day", "wind_max_ms"):
        v = _num(df[col])
        for i in np.flatnonzero(np.isfinite(v)):
            out.append({"table": "moon_real_1deg.csv", "record": str(df["cell_id"].iat[i]), "kind": "value_where_no_data_declared",
                        "column": col, "value": v[i]})
    return out


def check_combined(comb: pd.DataFrame, earth: pd.DataFrame, moon: pd.DataFrame) -> List[Dict]:
    """The combined table must equal the two body tables on every shared column."""
    out = []
    for body, df in (("EARTH", earth), ("MOON", moon)):
        part = comb[comb["body"] == body].set_index("cell_id")
        ref = df.set_index("cell_id")
        if len(part) != len(ref) or set(part.index) != set(ref.index):
            out.append({"table": "earth_moon_real_1deg.csv", "record": "*", "kind": f"{body}_ids_differ", "column": "cell_id", "value": None})
            continue
        part = part.loc[ref.index]
        for col in ref.columns:
            if col not in part.columns:
                continue
            a, b = ref[col], part[col]
            if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
                x, y = a.to_numpy(float), b.to_numpy(float)
                bad = ~((np.isnan(x) & np.isnan(y)) | (np.abs(x - y) <= 1e-9 * np.maximum(1, np.abs(x))))
            else:
                bad = ~(a.isna().to_numpy() & b.isna().to_numpy()) & (a.astype(str).to_numpy() != b.astype(str).to_numpy())
            for i in np.flatnonzero(bad):
                out.append({"table": "earth_moon_real_1deg.csv", "record": str(ref.index[i]), "kind": "differs_from_body_table",
                            "column": col, "value": None})
    return out


def check_bundle() -> (List[Dict], Dict[str, int]):
    """Shipped bundle: Earth ids and centres, mission files (rank, final, twin in zone), Moon labels."""
    b = bundle()
    fails: List[Dict] = []
    records: Dict[str, int] = {}
    ids = b.int_column("earth_base.bin", "id")
    lat_r, lon_c = b.column("earth_base.bin", "lat"), b.column("earth_base.bin", "lon")
    records["earth_base.bin"] = len(ids)
    rows, cols = ids // 360, ids % 360
    for i in np.flatnonzero(np.diff(ids) <= 0):
        fails.append({"table": "earth_base.bin", "record": int(ids[i + 1]), "kind": "id_not_ascending_unique", "column": "id", "value": None})
    for i in np.flatnonzero((ids < 0) | (ids >= 64800)):
        fails.append({"table": "earth_base.bin", "record": int(ids[i]), "kind": "id_out_of_grid", "column": "id", "value": None})
    lat, lon = lat_r[rows], lon_c[cols]
    bad = (np.abs(lat - (89.5 - rows)) > 1e-4) | (np.abs(lon - (-179.5 + cols)) > 1e-4)
    for i in np.flatnonzero(bad):
        fails.append({"table": "earth_base.bin", "record": int(ids[i]), "kind": "centre_not_on_grid", "column": "lat,lon", "value": None})
    places = b.json("places.json")
    miss = b.manifest["encoding"]["int32_missing"]
    for col, n in (("country", len(places["countries"])), ("region", len(places["regions"]))):
        v = b.int_column("earth_base.bin", col)
        for i in np.flatnonzero((v != miss) & ((v < 0) | (v >= n))):
            fails.append({"table": "earth_base.bin", "record": int(ids[i]), "kind": f"{col}_index_invalid", "column": col, "value": int(v[i])})
    moon_lat = 89.5 - np.arange(64800) // 360
    moon_elev = b.column("moon_base.bin", "v.elevation_m")
    region = b.int_column("moon_base.bin", "region")
    zones = b.json("mission_zones.json")
    codes = [r["code"] for r in zones["regions"]]
    a_idx = codes.index("A")
    zone = {"rover": moon_lat <= -75.0,
            "solar": (np.abs(moon_lat) <= 30.0) & (moon_elev <= -1200.0),
            "lunar_base": region == a_idx}
    zone_note = {"rover": "lat <= -75 (engine_config real_value_similarity.missions.rover.zone)",
                 "solar": "|lat| <= 30 and elevation_m <= -1200",
                 "lunar_base": "region A of mission_zones.json (the 280 Artemis cells)"}
    for m in MISSIONS:
        f = f"earth_{m}.bin"
        li = b.int_column(f, "land_index")
        rank = b.int_column(f, "rank")
        suit, sim, fin = b.column(f, "suitability"), b.column(f, "similarity"), b.column(f, "final")
        twin = b.int_column(f, "twin")
        records[f] = len(li)
        pid = ids[li]
        r_ok = rank != miss
        n_ranked = int(r_ok.sum())
        if sorted(rank[r_ok].tolist()) != list(range(1, n_ranked + 1)):
            fails.append({"table": f, "record": "*", "kind": "rank_not_permutation", "column": "rank", "value": None})
        for i in np.flatnonzero(r_ok != (twin != miss)):
            fails.append({"table": f, "record": int(pid[i]), "kind": "rank_without_twin_or_twin_without_rank", "column": "rank,twin", "value": None})
        exp = 0.5 * sim + 0.5 * suit
        for i in np.flatnonzero(r_ok & (np.abs(fin - exp) > 0.0051)):
            fails.append({"table": f, "record": int(pid[i]), "kind": "final_not_half_sim_half_suit", "column": "final", "value": fin[i]})
        for name, v in (("suitability", suit), ("similarity", sim), ("final", fin)):
            for i in np.flatnonzero(np.isfinite(v) & ((v < 0) | (v > 100))):
                fails.append({"table": f, "record": int(pid[i]), "kind": f"{name}_out_of_0_100", "column": name, "value": v[i]})
        tw = twin[r_ok]
        inz = zone[m][tw]
        for i, t in zip(np.flatnonzero(r_ok)[~inz], tw[~inz]):
            fails.append({"table": f, "record": int(pid[i]), "kind": "twin_outside_zone", "column": "twin", "value": int(t)})
        # order of ranks agrees with the rule: final descending, ties by id ascending
        o = np.flatnonzero(r_ok)
        o = o[np.argsort(rank[o])]
        for a, c2 in zip(o[:-1], o[1:]):
            if fin[a] < fin[c2] or (fin[a] == fin[c2] and pid[a] > pid[c2]):
                fails.append({"table": f, "record": int(pid[c2]), "kind": "rank_order_wrong", "column": "rank", "value": None})
    feat = b.int_column("moon_base.bin", "feature")
    fkm = b.column("moon_base.bin", "feature_km")
    nfeat = len(b.json("iau_moon_features.json")["name"])
    records["moon_base.bin"] = 64800
    for i in np.flatnonzero((feat < 0) | (feat >= nfeat)):
        fails.append({"table": "moon_base.bin", "record": int(i), "kind": "feature_index_invalid", "column": "feature", "value": int(feat[i])})
    for i in np.flatnonzero(~np.isfinite(fkm) | (fkm < 0)):
        fails.append({"table": "moon_base.bin", "record": int(i), "kind": "feature_km_invalid", "column": "feature_km", "value": fkm[i]})
    return fails, records, zone_note


def run() -> Dict:
    c = context()
    earth = pd.read_csv(os.path.join(REAL_DIR, "earth_real_1deg.csv"), low_memory=False)
    moon = pd.read_csv(os.path.join(REAL_DIR, "moon_real_1deg.csv"), low_memory=False)
    comb = pd.read_csv(os.path.join(REAL_DIR, "earth_moon_real_1deg.csv"), low_memory=False)
    fails = []
    fails += check_table(earth, "earth_real_1deg.csv", "EARTH", EARTH_RANGES, "E")
    fails += consistency_earth(earth, c)
    fails += check_table(moon, "moon_real_1deg.csv", "MOON", MOON_RANGES, "M")
    fails += consistency_moon(moon)
    comb_fails = check_combined(comb, earth, moon)
    fails += comb_fails
    bf, brec, zone_note = check_bundle()
    fails += bf
    records = {"earth_real_1deg.csv": len(earth), "moon_real_1deg.csv": len(moon),
               "earth_moon_real_1deg.csv": len(comb), **brec}
    fdf = pd.DataFrame(fails, columns=["table", "record", "kind", "column", "value"])
    fdf["record"] = fdf["record"].astype(str)
    fdf = fdf.sort_values(["table", "kind", "column", "record"], kind="mergesort")
    write_csv(fdf, "m2_validity_failures.csv")
    summ = []
    for t, n in records.items():
        g = fdf[(fdf["table"] == t) & (fdf["record"] != "*")]
        bad = g["record"].nunique()
        star = int(((fdf["table"] == t) & (fdf["record"] == "*")).sum())
        summ.append({"table": t, "records": n, "failing_records": int(bad), "table_level_failures": star,
                     "pass_pct": round(100.0 * (n - bad) / n, 4) if n else None})
    kinds = fdf.groupby(["table", "kind", "column"]).size().reset_index(name="count")
    write_csv(pd.DataFrame(summ), "m2_validity_by_table.csv")
    write_csv(kinds, "m2_validity_by_kind.csv")
    schema = [{"body": "EARTH", "column": k, "unit": v[0], "min": v[1], "max": v[2], "why": v[3]} for k, v in EARTH_RANGES.items()] + \
             [{"body": "MOON", "column": k, "unit": v[0], "min": v[1], "max": v[2], "why": v[3]} for k, v in MOON_RANGES.items()]
    write_csv(pd.DataFrame(schema), "m2_schema.csv")
    return {"by_table": summ, "by_kind": kinds.to_dict("records"), "zone_rules": zone_note}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=1, default=str))
