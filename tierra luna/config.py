import os
from dataclasses import dataclass, field
from typing import Dict, Tuple

LOCAL_LDEM4_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "cache", "ldem_4.img"
)

DATA_SOURCES_URLS = {
    "spaceapps_2026": "https://www.spaceappschallenge.org/2026/",
    "nasa_earthdata_cryosphere": (
        "https://search.earthdata.nasa.gov/search?fst0=Cryosphere"
        "&lat=39.13960498298632&long=-0.2651955352828237&zoom=5.705411016960538"
    ),
    "nasa_worldview": (
        "https://worldview.earthdata.nasa.gov/index.html"
        "?v=29.579326379038207,-23.321994475603763,218.99146031191327,66.69809521905691"
        "&t=2026-11-14-T05%3A01%3A28Z"
    ),
    "nasa_pds_main": "https://pds.nasa.gov/",
    "pds_lro_main": "https://pds-geosciences.wustl.edu/missions/lro/",
    "pds_lro_diviner": "https://pds-geosciences.wustl.edu/missions/lro/diviner.htm",
    "lola_dem_global_pds_url": (
        LOCAL_LDEM4_PATH
        if os.path.exists(LOCAL_LDEM4_PATH)
        else "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_4.img"
    ),
    "lola_dem_pds_url": (
        "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/"
        "lola_gdr/cylindrical/img/ldem_64.img"
    ),
    "diviner_rock_pds_url": (
        "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
        "data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_032_img.img"
    ),
    "diviner_temp_pds_url": (
        "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
        "data_derived_gdr_l3/cylindrical/img/dgdr_st_clc_cyl_0030_032_img.img"
    ),
    "diviner_temp_avg_pds_url": (
        "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/"
        "data_derived_gdr_l3/cylindrical/img/dgdr_st_avg_cyl_032_img.img"
    ),
    "csa_rcm": "https://donnees-data.asc-csa.gc.ca/en/dataset/rcm",
    "csa_radarsat1": "https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1",
    "csa_sar_tutorial": "https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial",
    "copernicus_dataspace": "https://dataspace.copernicus.eu/",
    "esa_openscience": "https://opensciencedata.esa.int/",
    "jaxa_gportal": "https://www.gportal.jaxa.jp/?lang=en",
}

GEE_COLLECTIONS = {
    "SRTM": "USGS/SRTMGL1_003",
    "ASTER_GED": "NASA/ASTER_GED/AG100_003",
    "MODIS_LST": "MODIS/061/MOD11A1",
    "MODIS_SNOW": "MODIS/061/MOD10A1",
    "SENTINEL1_SAR": "COPERNICUS/S1_GRD",
    "ALOS_PALSAR": "JAXA/ALOS/PALSAR/YEARLY/SAR",
}

HARMONIZED_BANDS = [
    "elevation_m",
    "elevation_rel_m",
    "slope_deg",
    "roughness_m",
    "temp_k",
    "rock_or_bare_frac",
    "sar_sigma0_db",
]


@dataclass
class GridConfig:
    target_resolution_m: float = 500.0
    grid_shape: Tuple[int, int] = (90, 180)
    nodata_value: float = -9999.0
    global_mode: bool = True

    earth_center_lat: float = 0.0
    earth_center_lon: float = 0.0
    earth_date_start: str = "2026-01-01"
    earth_date_end: str = "2026-11-14"

    moon_center_lat: float = 0.0
    moon_center_lon: float = 0.0

    valid_ranges_earth: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "elevation_m": (-500.0, 9000.0),
        "elevation_rel_m": (-6000.0, 6000.0),
        "slope_deg": (0.0, 90.0),
        "roughness_m": (0.0, 2500.0),
        "temp_k": (180.0, 360.0),
        "rock_or_bare_frac": (0.0, 1.0),
        "sar_sigma0_db": (-35.0, 15.0),
    })

    valid_ranges_moon: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "elevation_m": (-9200.0, 10800.0),
        "elevation_rel_m": (-9000.0, 9000.0),
        "slope_deg": (0.0, 90.0),
        "roughness_m": (0.0, 3500.0),
        "temp_k": (20.0, 420.0),
        "rock_or_bare_frac": (0.0, 1.0),
        "sar_sigma0_db": (-35.0, 15.0),
    })
