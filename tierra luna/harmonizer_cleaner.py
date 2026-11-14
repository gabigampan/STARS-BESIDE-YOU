import os
from typing import Dict, Tuple, Any
import numpy as np
import pandas as pd
from scipy.ndimage import distance_transform_edt
import rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS

from config import GridConfig, HARMONIZED_BANDS
from lunar_extractor import compute_slope_and_roughness

SENTINEL_VALUES = (-32768.0, -9999.0, -3.4028235e38, 1e32)


def _interpolate_nan_holes(arr: np.ndarray) -> np.ndarray:
    mask = np.isnan(arr)
    if not np.any(mask):
        return arr.copy()
    if np.all(mask):
        return np.zeros_like(arr)

    indices = distance_transform_edt(mask, return_distances=False, return_indices=True)
    filled = arr[tuple(indices)]
    return filled.astype(np.float32)


def clean_planetary_dataset(
    raw_data: Dict[str, np.ndarray],
    body: str,
    config: GridConfig,
    iqr_multiplier: float = 3.5,
    max_impute_frac: float = 0.30,
) -> Tuple[Dict[str, np.ndarray], pd.DataFrame]:
    valid_ranges = (
        config.valid_ranges_moon if body.lower() == "moon" else config.valid_ranges_earth
    )
    cleaned: Dict[str, np.ndarray] = {}
    audit_rows = []

    for band in HARMONIZED_BANDS:
        arr = raw_data[band].astype(np.float32).copy()
        total_px = arr.size

        if not np.isfinite(arr).any():
            cleaned[band] = np.full_like(arr, np.nan)
            audit_rows.append({
                "body": body.upper(),
                "variable": band,
                "total_pixels": total_px,
                "scale_corrected_px": 0,
                "nodata_sentinel_px": total_px,
                "out_of_physical_range_px": 0,
                "statistical_outliers_px": 0,
                "total_imputed_px": 0,
                "clean_min": np.nan,
                "clean_mean": np.nan,
                "clean_std": np.nan,
                "clean_max": np.nan,
            })
            continue

        scale_fixed_count = 0
        if body.lower() == "earth" and band == "temp_k":
            dn_mask = (arr > 7500.0) & (arr < 20000.0)
            scale_fixed_count = int(np.sum(dn_mask))
            if scale_fixed_count > 0:
                arr[dn_mask] = arr[dn_mask] * 0.02

        nan_or_inf = ~np.isfinite(arr)
        sentinel_mask = np.zeros_like(arr, dtype=bool)
        for sv in SENTINEL_VALUES:
            sentinel_mask |= np.isclose(arr, sv, atol=1e-3)
        nodata_count = int(np.sum(nan_or_inf | sentinel_mask))
        arr[nan_or_inf | sentinel_mask] = np.nan

        vmin, vmax = valid_ranges[band]
        out_of_range_mask = (arr < vmin) | (arr > vmax)
        out_of_range_count = int(np.sum(out_of_range_mask))
        arr[out_of_range_mask] = np.nan

        valid_vals = arr[np.isfinite(arr)]
        iqr_outlier_count = 0
        if valid_vals.size > 10 and band == "sar_sigma0_db":
            q25, q75 = np.percentile(valid_vals, [25.0, 75.0])
            iqr = max(float(q75 - q25), 1e-6)
            lower_fence = max(vmin, q25 - iqr_multiplier * iqr)
            upper_fence = min(vmax, q75 + iqr_multiplier * iqr)
            iqr_mask = (arr < lower_fence) | (arr > upper_fence)
            iqr_outlier_count = int(np.sum(iqr_mask))
            arr[iqr_mask] = np.nan

        total_interpolated = int(np.sum(np.isnan(arr)))
        if total_interpolated / total_px > max_impute_frac:
            print(
                f"[CLEANING] {body}/{band}: {100 * total_interpolated / total_px:.0f}% missing "
                f"(> {100 * max_impute_frac:.0f}% threshold); skipping interpolation, keeping nodata."
            )
            arr_filled = arr
            total_interpolated = 0
        else:
            arr_filled = np.clip(_interpolate_nan_holes(arr), vmin, vmax)
        cleaned[band] = arr_filled

        audit_rows.append({
            "body": body.upper(),
            "variable": band,
            "total_pixels": total_px,
            "scale_corrected_px": scale_fixed_count,
            "nodata_sentinel_px": nodata_count,
            "out_of_physical_range_px": out_of_range_count,
            "statistical_outliers_px": iqr_outlier_count,
            "total_imputed_px": total_interpolated,
            "clean_min": round(float(np.nanmin(arr_filled)), 4),
            "clean_mean": round(float(np.nanmean(arr_filled)), 4),
            "clean_std": round(float(np.nanstd(arr_filled)), 4),
            "clean_max": round(float(np.nanmax(arr_filled)), 4),
        })

    if not config.global_mode:
        slope_clean, rough_clean = compute_slope_and_roughness(
            cleaned["elevation_m"], config.target_resolution_m
        )
        cleaned["slope_deg"] = np.clip(slope_clean, 0.0, 90.0)
        cleaned["roughness_m"] = np.clip(rough_clean, 0.0, valid_ranges["roughness_m"][1])
        cleaned["elevation_rel_m"] = (
            cleaned["elevation_m"] - np.mean(cleaned["elevation_m"])
        ).astype(np.float32)

    audit_df = pd.DataFrame(audit_rows)
    return cleaned, audit_df


def export_to_geotiff(
    data: Dict[str, np.ndarray],
    output_path: str,
    body: str,
    config: GridConfig,
) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    h, w = config.grid_shape
    res = config.target_resolution_m

    west = -(w * res) / 2.0
    north = (h * res) / 2.0
    transform = from_origin(west, north, res, res)

    crs = CRS.from_epsg(3857)

    profile = {
        "driver": "GTiff",
        "height": h,
        "width": w,
        "count": len(HARMONIZED_BANDS),
        "dtype": rasterio.float32,
        "crs": crs,
        "transform": transform,
        "nodata": config.nodata_value,
        "compress": "lzw",
    }

    unit_labels = {
        "elevation_m": "meters (m)",
        "elevation_rel_m": "meters (m, zero-centered)",
        "slope_deg": "degrees (deg, 0-90)",
        "roughness_m": "meters (m, local 3x3 std)",
        "temp_k": "Kelvin (K)",
        "rock_or_bare_frac": "fraction [0-1]",
        "sar_sigma0_db": "decibels (dB)",
    }

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.update_tags(
            PLANETARY_BODY=body.upper(),
            RESOLUTION_METERS=str(res),
            UNITS_STANDARD="SI_HARMONIZED_KELVIN_METERS_DEGREES",
        )
        for idx, band_name in enumerate(HARMONIZED_BANDS, start=1):
            dst.write(
                np.nan_to_num(data[band_name].astype(np.float32), nan=config.nodata_value),
                idx,
            )
            dst.set_band_description(idx, f"{band_name} [{unit_labels[band_name]}]")

    return output_path


def dataset_to_dataframe(
    data: Dict[str, np.ndarray],
    body: str,
    config: GridConfig,
    source: str = "synthetic",
) -> pd.DataFrame:
    h, w = config.grid_shape
    res = config.target_resolution_m
    rows, cols = np.mgrid[0:h, 0:w]

    x_m = (cols - w / 2.0 + 0.5) * res
    y_m = ((h / 2.0 - 0.5) - rows) * res

    if config.global_mode:
        lat = 90.0 - (rows + 0.5) * (180.0 / h)
        lon = -180.0 + (cols + 0.5) * (360.0 / w)
    else:
        if body.lower() == "moon":
            radius_m = 1737400.0
            c_lat, c_lon = config.moon_center_lat, config.moon_center_lon
        else:
            radius_m = 6371000.0
            c_lat, c_lon = config.earth_center_lat, config.earth_center_lon

        meters_per_deg_lat = (np.pi / 180.0) * radius_m
        lat = c_lat + (y_m / meters_per_deg_lat)
        cos_lat = max(float(np.cos(np.radians(np.clip(abs(c_lat), 0.0, 85.0)))), 0.08)
        lon = c_lon + (x_m / (meters_per_deg_lat * cos_lat))

    df_dict: Dict[str, Any] = {
        "body": body.upper(),
        "row": rows.ravel(),
        "col": cols.ravel(),
        "x_m": np.round(x_m.ravel(), 2),
        "y_m": np.round(y_m.ravel(), 2),
        "lat_deg": np.round(lat.ravel(), 6),
        "lon_deg": np.round(lon.ravel(), 6),
        "resolution_m": res,
        "source": source,
    }

    for band in HARMONIZED_BANDS:
        df_dict[band] = np.round(data[band].ravel(), 4)

    elev_flat = data["elevation_m"].ravel()
    slope_flat = data["slope_deg"].ravel()
    rough_flat = data["roughness_m"].ravel()
    temp_flat = np.nan_to_num(data["temp_k"].ravel(), nan=250.0)
    bare_flat = np.nan_to_num(data["rock_or_bare_frac"].ravel(), nan=0.1)
    lat_flat = lat.ravel()

    is_moon = body.lower() == "moon"
    if is_moon:
        mask_frac = np.ones_like(elev_flat, dtype=np.float32)
    else:
        mask_frac = np.where(
            elev_flat > 0.0,
            np.clip(0.35 + 0.65 * np.minimum(elev_flat / 150.0, 1.0), 0.35, 1.0),
            0.0,
        ).astype(np.float32)

    cos_lat = np.clip(np.cos(np.radians(lat_flat)), 0.05, 1.0)
    irr = np.clip(
        (1.6 + 4.8 * np.power(cos_lat, 0.75))
        * (0.78 + 0.32 * bare_flat + 0.04 * np.clip(np.maximum(elev_flat, 0.0) / 3000.0, 0.0, 1.5)),
        0.8,
        8.2,
    )
    sun_max = np.clip(90.0 - np.abs(lat_flat) + (1.54 if is_moon else 11.7), 1.5, 90.0)
    sun_low = np.clip(0.028 + 0.26 * np.power(np.abs(lat_flat) / 90.0, 2.2), 0.025, 0.35)

    if is_moon:
        diurnal_amp = np.clip(180.0 * np.power(cos_lat, 0.35), 25.0, 210.0)
    else:
        diurnal_amp = np.where(
            elev_flat > 0.0,
            np.clip(8.0 + 22.0 * bare_flat + 0.0022 * np.maximum(elev_flat, 0.0), 6.0, 48.0),
            2.5,
        )

    ti_class = np.full(elev_flat.shape, "suelo", dtype=object)
    ti_class[bare_flat >= 0.22] = "arena"
    ti_class[bare_flat >= 0.42] = "regolito"
    ti_class[(bare_flat >= 0.55) & ((rough_flat >= 110.0) | (slope_flat >= 4.0))] = "roca"
    if not is_moon:
        ti_class[(elev_flat > 0.0) & (temp_flat < 261.0)] = "hielo"
        ti_class[elev_flat <= 0.0] = "agua"

    pf_class = np.full(elev_flat.shape, "ninguno", dtype=object)
    if is_moon:
        pf_class[(np.abs(lat_flat) >= 75.0) & (temp_flat <= 75.0)] = "continuo"
        pf_class[(np.abs(lat_flat) >= 65.0) & (temp_flat > 75.0) & (temp_flat <= 90.0)] = "discontinuo"
    else:
        land_ok = elev_flat > 0.0
        pf_class[land_ok & ((temp_flat <= 274.15) | ((elev_flat >= 3400.0) & (temp_flat <= 278.0)))] = "esporadico"
        pf_class[land_ok & (temp_flat <= 270.15)] = "discontinuo"
        pf_class[land_ok & (temp_flat <= 265.15)] = "continuo"

    if is_moon:
        rain_mm = np.zeros_like(elev_flat, dtype=np.float32)
        wind_ms = np.zeros_like(elev_flat, dtype=np.float32)
    else:
        rain_mm = np.clip(
            4.2 * np.power(np.clip(1.0 - bare_flat, 0.0, 1.0), 1.8) * np.clip(cos_lat + 0.15, 0.2, 1.1),
            0.01,
            12.0,
        )
        wind_ms = np.clip(
            4.5 + 0.0012 * np.maximum(elev_flat, 0.0) + 3.8 * np.power(np.abs(lat_flat) / 90.0, 1.4),
            2.5,
            15.5,
        )
    tmin_c = (temp_flat - 273.15) - 0.35 * diurnal_amp

    df_dict["mask_fraction"] = np.round(mask_frac, 3)
    df_dict["slope_300m_deg"] = np.round(slope_flat, 3)
    df_dict["rough_300m_m"] = np.round(rough_flat, 2)
    df_dict["irradiance_kwh_m2_day"] = np.round(irr, 3)
    df_dict["sun_elev_max_deg"] = np.round(sun_max, 2)
    df_dict["sun_low_frac_0_5deg"] = np.round(sun_low, 4)
    df_dict["lst_diurnal_amp_k"] = np.round(diurnal_amp, 2)
    df_dict["thermal_inertia_class"] = ti_class
    df_dict["permafrost_class"] = pf_class
    df_dict["rain_mm_day"] = np.round(rain_mm, 2)
    df_dict["wind_max_ms"] = np.round(wind_ms, 2)
    df_dict["tmin_c"] = np.round(tmin_c, 2)

    return pd.DataFrame(df_dict)
