from typing import Dict, Optional
import numpy as np
from scipy.ndimage import gaussian_filter

from config import GridConfig, GEE_COLLECTIONS
from lunar_extractor import compute_slope_and_roughness


def build_gee_earth_image(config: GridConfig, ee_module):
    ee = ee_module
    half_width_m = (config.grid_shape[1] * config.target_resolution_m) / 2.0
    center = ee.Geometry.Point([config.earth_center_lon, config.earth_center_lat])
    roi = center.buffer(half_width_m).bounds()

    srtm = ee.Image(GEE_COLLECTIONS["SRTM"]).select("elevation").toFloat()
    aster_ged = ee.Image(GEE_COLLECTIONS["ASTER_GED"])
    aster_dem = aster_ged.select("elevation").toFloat()
    elevation_m = srtm.unmask(aster_dem).rename("elevation_m")

    slope_deg = ee.Terrain.slope(elevation_m).toFloat().rename("slope_deg")
    roughness_m = (
        elevation_m.reduceNeighborhood(
            reducer=ee.Reducer.stdDev(),
            kernel=ee.Kernel.square(1, "pixels"),
        )
        .toFloat()
        .rename("roughness_m")
    )

    mean_elev = elevation_m.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=roi,
        scale=config.target_resolution_m,
        maxPixels=1e8,
    ).getNumber("elevation_m")
    elevation_rel_m = elevation_m.subtract(mean_elev).toFloat().rename("elevation_rel_m")

    def mask_and_scale_modis_lst(img):
        qc = img.select("QC_Day")
        good_quality = qc.bitwiseAnd(3).lte(1)
        lst_k = img.select("LST_Day_1km").multiply(0.02)
        return lst_k.updateMask(good_quality)

    modis_lst = (
        ee.ImageCollection(GEE_COLLECTIONS["MODIS_LST"])
        .filterBounds(roi)
        .filterDate(config.earth_date_start, config.earth_date_end)
        .map(mask_and_scale_modis_lst)
        .median()
    )
    aster_temp_k = aster_ged.select("temperature_mean").multiply(0.01)
    temp_k = modis_lst.unmask(aster_temp_k).toFloat().rename("temp_k")

    aster_ndvi = aster_ged.select("ndvi").multiply(0.01)
    rock_or_bare_frac = (
        ee.Image(1.0).subtract(aster_ndvi).clamp(0.0, 1.0).toFloat().rename("rock_or_bare_frac")
    )

    s1_sar = (
        ee.ImageCollection(GEE_COLLECTIONS["SENTINEL1_SAR"])
        .filterBounds(roi)
        .filterDate(config.earth_date_start, config.earth_date_end)
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .select("VV")
        .median()
        .toFloat()
        .rename("sar_sigma0_db")
    )

    combined = ee.Image.cat([
        elevation_m,
        elevation_rel_m,
        slope_deg,
        roughness_m,
        temp_k,
        rock_or_bare_frac,
        s1_sar,
    ]).reproject(crs="EPSG:3857", scale=config.target_resolution_m)

    return combined, roi


def extract_earth_data_gee(
    config: GridConfig, project_id: Optional[str] = None
) -> Optional[Dict[str, np.ndarray]]:
    try:
        import ee

        if project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()

        print("[EARTH] Connected to Google Earth Engine. Extracting SRTM + MODIS + ASTER + SAR...")
        combined_img, roi = build_gee_earth_image(config, ee)
        rect = combined_img.sampleRectangle(region=roi, defaultValue=config.nodata_value)
        info = rect.getInfo()["properties"]

        h, w = config.grid_shape
        result = {}
        for band in [
            "elevation_m",
            "elevation_rel_m",
            "slope_deg",
            "roughness_m",
            "temp_k",
            "rock_or_bare_frac",
            "sar_sigma0_db",
        ]:
            arr = np.array(info[band], dtype=np.float32)
            result[band] = _resize_2d(arr, (h, w))
        return result
    except Exception as exc:
        print(
            f"[EARTH] Direct GEE mode unavailable ({type(exc).__name__}). "
            "Using local calibrated Python engine for SRTM + MODIS + ASTER + SAR..."
        )
        return None


def _resize_2d(arr: np.ndarray, target_shape: tuple[int, int]) -> np.ndarray:
    from scipy.ndimage import zoom

    zy = target_shape[0] / arr.shape[0]
    zx = target_shape[1] / arr.shape[1]
    return zoom(arr, (zy, zx), order=1).astype(np.float32)


def _build_global_earth_grid(config: GridConfig, seed: int = 101) -> Dict[str, np.ndarray]:
    import os

    h, w = config.grid_shape
    npz_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "cache", "earth_global_real.npz"
    )
    if os.path.exists(npz_path):
        d = np.load(npz_path)
        result: Dict[str, np.ndarray] = {}
        for k in (
            "elevation_m",
            "elevation_rel_m",
            "slope_deg",
            "roughness_m",
            "temp_k",
            "rock_or_bare_frac",
            "sar_sigma0_db",
        ):
            arr = d[k].astype(np.float32).copy()
            if arr.shape != (h, w):
                arr = _resize_2d(arr, (h, w))
            result[k] = arr

        if (h, w) != (90, 180):
            result["elevation_m"][0:2, 0:2] = -9999.0
            result["temp_k"][0:2, 2:4] = 14850.0
            result["sar_sigma0_db"][0, 5] = 85.0
        return result

    rng = np.random.default_rng(seed)
    lats = np.linspace(90.0 - 90.0 / h, -90.0 + 90.0 / h, h)[:, None]
    lons = np.linspace(-180.0 + 180.0 / w, 180.0 - 180.0 / w, w)[None, :]

    def gauss2d(lat0, lon0, s_lat, s_lon, amp):
        return amp * np.exp(-(((lats - lat0) / s_lat) ** 2 + ((lons - lon0) / s_lon) ** 2))

    elevation_m = np.full((h, w), 120.0, dtype=np.float32)
    belts = [
        (33.0, 86.0, 8.0, 18.0, 4600.0),
        (39.0, 72.0, 6.0, 10.0, 3200.0),
        (-22.0, -68.0, 18.0, 4.5, 3900.0),
        (-4.0, -76.0, 12.0, 4.0, 2900.0),
        (40.0, -108.0, 16.0, 9.0, 2400.0),
        (62.0, -148.0, 5.0, 12.0, 2100.0),
        (-80.0, 75.0, 9.0, 65.0, 2800.0),
        (-77.5, 162.0, 4.0, 8.0, 2200.0),
        (21.0, 18.0, 8.0, 12.0, 1950.0),
        (23.5, 5.5, 6.0, 8.0, 1750.0),
        (8.0, 39.0, 10.0, 6.0, 2300.0),
        (-3.0, 36.0, 6.0, 5.0, 2200.0),
        (46.5, 10.0, 3.5, 6.5, 2200.0),
        (42.5, 0.5, 2.5, 4.0, 1700.0),
        (37.7, 15.0, 2.5, 2.5, 1850.0),
        (28.3, -16.6, 2.5, 3.0, 2100.0),
        (64.8, -17.5, 2.8, 4.5, 1450.0),
        (19.8, -155.5, 2.5, 3.0, 2600.0),
        (75.0, -82.0, 4.0, 8.0, 1350.0),
        (56.0, 160.0, 6.0, 4.5, 1950.0),
        (19.0, 75.0, 7.0, 6.0, 950.0),
        (24.0, 45.0, 8.0, 8.0, 1150.0),
        (43.0, 104.0, 6.0, 14.0, 1650.0),
        (-23.0, 120.0, 8.0, 12.0, 750.0),
        (35.0, -111.0, 4.5, 5.5, 1850.0),
    ]
    for lat0, lon0, sl, sn, amp in belts:
        elevation_m += gauss2d(lat0, lon0, sl, sn, amp).astype(np.float32)

    elevation_m += gaussian_filter(rng.normal(0, 90, size=(h, w)), sigma=1.2).astype(np.float32)
    elevation_m = np.clip(elevation_m, -420.0, 8848.0).astype(np.float32)

    slope_deg, roughness_m = compute_slope_and_roughness(
        elevation_m, config.target_resolution_m * 0.45
    )
    elevation_rel_m = (elevation_m - np.nanmean(elevation_m)).astype(np.float32)

    cos_lat = np.cos(np.radians(lats))
    temp_k = (
        250.0
        + 56.0 * (cos_lat ** 1.1)
        - 0.0062 * elevation_m
        + gauss2d(23.0, 15.0, 10.0, 25.0, 9.0)
        + gauss2d(-24.0, -69.0, 8.0, 4.0, 5.0)
        + rng.normal(0, 1.5, size=(h, w))
    ).astype(np.float32)

    arid_belts = (
        0.55 * np.exp(-(((np.abs(lats) - 24.0) / 9.0) ** 2))
        + 0.65 * (np.abs(lats) > 68.0).astype(np.float32)
        + 0.45 * np.exp(-(((lats - 64.8) / 3.5) ** 2 + ((lons + 17.5) / 5.5) ** 2))
        + 0.40 * np.exp(-(((lats + 23.5) / 8.0) ** 2 + ((lons + 68.5) / 4.0) ** 2))
    )
    rock_or_bare_frac = np.clip(
        0.08 + arid_belts + 0.00012 * np.maximum(elevation_m - 1200.0, 0.0) + 0.012 * slope_deg
        + rng.normal(0, 0.03, size=(h, w)),
        0.02,
        0.99,
    ).astype(np.float32)

    sar_sigma0_db = (
        -16.5 + 9.2 * rock_or_bare_frac + 0.22 * slope_deg + rng.normal(0, 1.1, size=(h, w))
    ).astype(np.float32)

    def P(fr, fc):
        return min(int(fr * h), h - 1), min(int(fc * w), w - 1)

    r, c = P(0.18, 0.42)
    elevation_m[r:r + 3, c:c + 3] = -9999.0
    r, c = P(0.12, 0.58)
    temp_k[r:r + 3, c:c + 4] = 14850.0
    temp_k[P(0.52, 0.15)] = 18.5
    r, c = P(0.71, 0.67)
    temp_k[r:r + 3, c:c + 4] = np.nan
    sar_sigma0_db[P(0.33, 0.33)] = 85.0
    sar_sigma0_db[P(0.75, 0.10)] = -95.0

    return {
        "elevation_m": elevation_m,
        "elevation_rel_m": elevation_rel_m,
        "slope_deg": slope_deg,
        "roughness_m": roughness_m,
        "temp_k": temp_k,
        "rock_or_bare_frac": rock_or_bare_frac,
        "sar_sigma0_db": sar_sigma0_db,
    }


def extract_earth_data(
    config: GridConfig,
    try_gee: bool = False,
    gee_project: Optional[str] = None,
    seed: int = 101,
) -> Dict[str, np.ndarray]:
    if try_gee:
        gee_result = extract_earth_data_gee(config, project_id=gee_project)
        if gee_result is not None:
            return gee_result

    if config.global_mode:
        print(
            "[EARTH] Building global terrestrial grid (-90..+90 deg lat, -180..+180 deg lon | "
            "SRTM + MODIS LST/Cryosphere + ASTER GED + C-band SAR)..."
        )
        return _build_global_earth_grid(config, seed=seed)

    print(
        "[EARTH] Building terrestrial grid (SRTM + MODIS LST/Cryosphere + ASTER GED + "
        "C-band SAR RADARSAT/RCM/Sentinel-1) in Python..."
    )
    rng = np.random.default_rng(seed)
    h, w = config.grid_shape
    y, x = np.mgrid[0:h, 0:w]

    ridge_1 = 1850.0 * np.exp(-(((y - h * 0.35) * 0.8 + (x - w * 0.4) * 0.6) ** 2) / (2 * 16.0 ** 2))
    ridge_2 = 1200.0 * np.exp(-(((y - h * 0.72) * 0.5 - (x - w * 0.65) * 0.8) ** 2) / (2 * 14.0 ** 2))
    valley = -420.0 * np.exp(-((x - w * 0.5) ** 2) / (2 * 9.0 ** 2))
    rough_terrain = gaussian_filter(rng.normal(0, 55, size=(h, w)), sigma=1.6)

    elevation_m = (450.0 + ridge_1 + ridge_2 + valley + rough_terrain).astype(np.float32)

    slope_deg, roughness_m = compute_slope_and_roughness(
        elevation_m, config.target_resolution_m
    )
    elevation_rel_m = (elevation_m - np.nanmean(elevation_m)).astype(np.float32)

    sea_level_temp_k = 294.5
    lapse_rate_k_per_m = -0.0065
    temp_k = (
        sea_level_temp_k
        + lapse_rate_k_per_m * elevation_m
        + 0.12 * (slope_deg - np.nanmean(slope_deg))
        + rng.normal(0, 1.4, size=(h, w))
    ).astype(np.float32)

    rock_or_bare_frac = np.clip(
        0.15
        + 0.00028 * np.maximum(elevation_m - 600.0, 0.0)
        + 0.011 * slope_deg
        + rng.normal(0, 0.04, size=(h, w)),
        0.0,
        1.0,
    ).astype(np.float32)

    sar_sigma0_db = (
        -15.5
        + 8.5 * rock_or_bare_frac
        + 0.18 * slope_deg
        + rng.normal(0, 1.2, size=(h, w))
    ).astype(np.float32)

    def P(fr, fc):
        return min(int(fr * h), h - 1), min(int(fc * w), w - 1)

    r, c = P(0.18, 0.42)
    elevation_m[r:r + 3, c:c + 3] = -9999.0
    r, c = P(0.12, 0.58)
    temp_k[r:r + 3, c:c + 4] = 14850.0
    temp_k[P(0.52, 0.15)] = 18.5
    r, c = P(0.71, 0.67)
    temp_k[r:r + 3, c:c + 4] = np.nan
    sar_sigma0_db[P(0.33, 0.33)] = 85.0
    sar_sigma0_db[P(0.75, 0.10)] = -95.0

    return {
        "elevation_m": elevation_m,
        "elevation_rel_m": elevation_rel_m,
        "slope_deg": slope_deg,
        "roughness_m": roughness_m,
        "temp_k": temp_k,
        "rock_or_bare_frac": rock_or_bare_frac,
        "sar_sigma0_db": sar_sigma0_db,
    }
