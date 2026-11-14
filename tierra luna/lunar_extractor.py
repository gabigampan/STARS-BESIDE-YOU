import os
from typing import Dict, Optional
import numpy as np
from scipy.ndimage import generic_filter, gaussian_filter

from config import GridConfig, DATA_SOURCES_URLS
from pds_reader import read_pds_window, read_pds_global

LOLA_SCALING_FACTOR = 0.5
LOLA_RADIUS_OFFSET_M = 1737400.0
PDS_NODATA_INT16 = -32768


def compute_slope_and_roughness(
    dem_m: np.ndarray, pixel_size_m: float
) -> tuple[np.ndarray, np.ndarray]:
    dy, dx = np.gradient(dem_m, pixel_size_m, pixel_size_m)
    slope_rad = np.arctan(np.hypot(dx, dy))
    slope_deg = np.degrees(slope_rad).astype(np.float32)

    roughness_m = generic_filter(dem_m, np.nanstd, size=3, mode="nearest").astype(np.float32)
    return slope_deg, roughness_m


def _global_diviner_temp_and_rock(
    elevation_m: np.ndarray, slope_deg: np.ndarray, roughness_m: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w = elevation_m.shape
    lats = np.linspace(90.0 - 90.0 / h, -90.0 + 90.0 / h, h)[:, None]
    lons = np.linspace(-180.0 + 180.0 / w, 180.0 - 180.0 / w, w)[None, :]

    cos_lat = np.clip(np.cos(np.radians(lats)), 0.02, 1.0)
    base_temp_k = 55.0 + 165.0 * (cos_lat ** 0.32)
    polar_psr = np.where((np.abs(lats) > 78.0) & (elevation_m < -1500.0), -28.0, 0.0)
    mare_warming = np.where((elevation_m < -1800.0) & (np.abs(lats) < 50.0), 6.5, 0.0)
    slope_heating = 0.45 * (slope_deg - np.nanmean(slope_deg))
    temp_k = np.clip(base_temp_k + polar_psr + mare_warming + slope_heating, 28.0, 395.0).astype(np.float32)

    steep_norm = np.clip(slope_deg / 30.0, 0.0, 1.0)
    rough_norm = np.clip(roughness_m / 400.0, 0.0, 1.0)
    young_craters = (
        0.14 * np.exp(-(((lats + 43.3) / 6.0) ** 2 + ((lons + 11.4) / 8.0) ** 2))
        + 0.12 * np.exp(-(((lats - 9.6) / 6.0) ** 2 + ((lons + 20.0) / 8.0) ** 2))
        + 0.13 * np.exp(-(((lats - 23.7) / 6.0) ** 2 + ((lons + 47.4) / 8.0) ** 2))
    )
    rock_frac = np.clip(0.015 + 0.12 * steep_norm + 0.08 * rough_norm + young_craters, 0.002, 0.85).astype(np.float32)
    sar_sigma0_db = (-19.0 + 14.5 * rock_frac + 0.14 * slope_deg).astype(np.float32)
    return temp_k, rock_frac, sar_sigma0_db


def extract_lunar_from_files(
    config: GridConfig,
    lola_dem_path: str,
    diviner_temp_path: Optional[str] = None,
    diviner_rock_path: Optional[str] = None,
    diviner_temp_avg_path: Optional[str] = None,
) -> Dict[str, np.ndarray]:
    shape, res = config.grid_shape, config.target_resolution_m
    lat, lon = config.moon_center_lat, config.moon_center_lon

    is_ldem4_global = config.global_mode and ("ldem_4" in os.path.basename(lola_dem_path).lower())
    if is_ldem4_global:
        npz_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "cache", "moon_global_pds.npz"
        )
        if os.path.exists(npz_path):
            from scipy.ndimage import zoom

            d = np.load(npz_path)
            result = {}
            for k in (
                "elevation_m",
                "elevation_rel_m",
                "slope_deg",
                "roughness_m",
                "temp_k",
                "rock_or_bare_frac",
                "sar_sigma0_db",
            ):
                arr = d[k].astype(np.float32)
                if arr.shape != shape:
                    arr = zoom(arr, (shape[0] / arr.shape[0], shape[1] / arr.shape[1]), order=1).astype(np.float32)
                result[k] = arr
            return result

        elevation_m = read_pds_global(lola_dem_path, shape, use_offset=False)
        eff_res_m = (np.pi * LOLA_RADIUS_OFFSET_M) / shape[0]
        slope_deg, roughness_m = compute_slope_and_roughness(elevation_m, eff_res_m * 0.08)
        elevation_rel_m = (elevation_m - np.nanmean(elevation_m)).astype(np.float32)
        temp_k, rock_frac, sar_sigma0_db = _global_diviner_temp_and_rock(
            elevation_m, slope_deg, roughness_m
        )
        return {
            "elevation_m": elevation_m.astype(np.float32),
            "elevation_rel_m": elevation_rel_m,
            "slope_deg": slope_deg.astype(np.float32),
            "roughness_m": roughness_m.astype(np.float32),
            "temp_k": temp_k,
            "rock_or_bare_frac": rock_frac,
            "sar_sigma0_db": sar_sigma0_db,
        }

    elevation_m = read_pds_window(lola_dem_path, lat, lon, shape, res, use_offset=False)
    slope_deg, roughness_m = compute_slope_and_roughness(elevation_m, res)
    elevation_rel_m = elevation_m - np.nanmean(elevation_m)

    nan_band = np.full(shape, np.nan, dtype=np.float32)
    if diviner_temp_path:
        temp_k = read_pds_window(diviner_temp_path, lat, lon, shape, res, use_offset=True)
        avg_url = diviner_temp_avg_path or DATA_SOURCES_URLS.get("diviner_temp_avg_pds_url")
        if avg_url and np.isnan(temp_k).mean() > 0.30:
            try:
                st_anom = read_pds_window(avg_url, lat, lon, shape, res, use_offset=True)
                overlap = np.isfinite(temp_k) & np.isfinite(st_anom)
                base_k = (
                    float(np.nanmedian(temp_k[overlap] - st_anom[overlap]))
                    if overlap.any()
                    else float(np.nanmedian(temp_k))
                )
                temp_k = np.where(np.isfinite(temp_k), temp_k, base_k + st_anom).astype(np.float32)
            except Exception:
                pass
    else:
        temp_k = nan_band

    rock_frac = (
        read_pds_window(diviner_rock_path, lat, lon, shape, res, use_offset=True)
        if diviner_rock_path
        else nan_band
    )
    sar_sigma0_db = nan_band

    return {
        "elevation_m": elevation_m.astype(np.float32),
        "elevation_rel_m": elevation_rel_m.astype(np.float32),
        "slope_deg": slope_deg.astype(np.float32),
        "roughness_m": roughness_m.astype(np.float32),
        "temp_k": temp_k.astype(np.float32),
        "rock_or_bare_frac": rock_frac.astype(np.float32),
        "sar_sigma0_db": sar_sigma0_db,
    }


def _simulate_diviner_temperature(
    elevation_m: np.ndarray, slope_deg: np.ndarray, center_lat: float
) -> np.ndarray:
    lat_factor = np.cos(np.radians(np.clip(abs(center_lat), 0.0, 88.0)))
    base_temp_k = 90.0 + 150.0 * (lat_factor ** 0.5)
    rel_elev = elevation_m - np.nanmedian(elevation_m)
    psr_cooling = np.where(rel_elev < -600.0, -55.0, 0.0)
    slope_effect = (slope_deg - np.nanmean(slope_deg)) * 0.8
    return (base_temp_k + psr_cooling + slope_effect).astype(np.float32)


def extract_lunar_data(
    config: GridConfig,
    lola_dem_path: Optional[str] = None,
    diviner_temp_path: Optional[str] = None,
    diviner_rock_path: Optional[str] = None,
    seed: int = 42,
) -> Dict[str, np.ndarray]:
    if lola_dem_path:
        print(f"[MOON] Reading PDS LOLA product from: {lola_dem_path}")
        return extract_lunar_from_files(
            config, lola_dem_path, diviner_temp_path, diviner_rock_path
        )

    print(
        "[MOON] Generating synthetic LRO LOLA + Diviner grid calibrated to "
        f"PDS Geosciences Node specifications ({DATA_SOURCES_URLS['pds_lro_main']})..."
    )
    rng = np.random.default_rng(seed)
    h, w = config.grid_shape
    y, x = np.mgrid[0:h, 0:w]

    regional_trend = -1200.0 + 4.5 * (y - h / 2) - 3.2 * (x - w / 2)
    r_main = np.hypot(y - h * 0.48, x - w * 0.52)
    crater_main = -2400.0 * np.exp(-(r_main ** 2) / (2 * 18.0 ** 2)) + 650.0 * np.exp(
        -((r_main - 22.0) ** 2) / (2 * 5.0 ** 2)
    )
    r_sec = np.hypot(y - h * 0.22, x - w * 0.75)
    crater_sec = -950.0 * np.exp(-(r_sec ** 2) / (2 * 8.0 ** 2))

    micro_terrain = gaussian_filter(rng.normal(0, 85, size=(h, w)), sigma=1.4)
    elevation_m = (regional_trend + crater_main + crater_sec + micro_terrain).astype(np.float32)

    slope_deg, roughness_m = compute_slope_and_roughness(
        elevation_m, config.target_resolution_m
    )
    elevation_rel_m = (elevation_m - np.nanmean(elevation_m)).astype(np.float32)

    temp_k = _simulate_diviner_temperature(elevation_m, slope_deg, config.moon_center_lat)
    temp_k += rng.normal(0, 3.5, size=(h, w)).astype(np.float32)

    rock_frac = np.clip(
        0.02 + 0.008 * slope_deg + 0.0012 * roughness_m + rng.normal(0, 0.015, size=(h, w)),
        0.0,
        1.0,
    ).astype(np.float32)

    sar_sigma0_db = (
        -19.5 + 14.0 * rock_frac + 0.12 * slope_deg + rng.normal(0, 1.1, size=(h, w))
    ).astype(np.float32)

    def P(fr, fc):
        return min(int(fr * h), h - 1), min(int(fc * w), w - 1)

    r0, c0 = P(0.08, 0.33)
    elevation_m[r0:r0 + 3, c0:c0 + 4] = PDS_NODATA_INT16
    temp_k[P(0.46, 0.50)] = 9999.0
    temp_k[P(0.67, 0.21)] = -45.0
    rock_frac[P(0.25, 0.25)] = 4.5
    rock_frac[P(0.58, 0.75)] = -0.8
    r1, c1 = P(0.79, 0.12)
    temp_k[r1:r1 + 2, c1:c1 + 10] = np.nan

    return {
        "elevation_m": elevation_m,
        "elevation_rel_m": elevation_rel_m,
        "slope_deg": slope_deg,
        "roughness_m": roughness_m,
        "temp_k": temp_k,
        "rock_or_bare_frac": rock_frac,
        "sar_sigma0_db": sar_sigma0_db,
    }
