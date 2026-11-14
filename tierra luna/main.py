import argparse
import os
import pandas as pd

from config import GridConfig, DATA_SOURCES_URLS
from lunar_extractor import extract_lunar_data
from earth_extractor import extract_earth_data
from harmonizer_cleaner import (
    clean_planetary_dataset,
    export_to_geotiff,
    dataset_to_dataframe,
)
from analog_finder import export_web_bundle


def parse_args():
    parser = argparse.ArgumentParser(
        description="Global Moon (LOLA, Diviner) and Earth (SRTM, MODIS, ASTER, SAR) Data Extractor, Harmonizer, Cleaner, and Analog Finder."
    )
    parser.add_argument(
        "--res",
        type=float,
        default=500.0,
        help="Common spatial resolution in meters per pixel (default: 500.0 m)",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=90,
        help="Global latitude grid rows covering -90 to +90 deg (default: 90)",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=180,
        help="Global longitude grid cols covering -180 to +180 deg (default: 180)",
    )
    parser.add_argument(
        "--local-window",
        action="store_true",
        help="Run on a local square window instead of the full -90..+90 / -180..+180 planetary globe",
    )
    parser.add_argument(
        "--size",
        type=int,
        default=120,
        help="Square grid size when --local-window is used (default: 120)",
    )
    parser.add_argument(
        "--earth-lat",
        type=float,
        default=0.0,
        help="Terrestrial center latitude (default: 0.0 global)",
    )
    parser.add_argument(
        "--earth-lon",
        type=float,
        default=0.0,
        help="Terrestrial center longitude (default: 0.0 global)",
    )
    parser.add_argument(
        "--moon-lat",
        type=float,
        default=0.0,
        help="Lunar center latitude (default: 0.0 global)",
    )
    parser.add_argument(
        "--moon-lon",
        type=float,
        default=0.0,
        help="Lunar center longitude (default: 0.0 global)",
    )
    parser.add_argument(
        "--pds",
        action="store_true",
        help="Use real LOLA and Diviner data from NASA PDS (global ldem_4 map by default)",
    )
    parser.add_argument(
        "--lola-dem",
        type=str,
        default=None,
        help="Optional path or URL to a PDS LOLA DEM file (.img/.lbl)",
    )
    parser.add_argument(
        "--diviner-temp",
        type=str,
        default=None,
        help="Optional path or URL to a PDS Diviner Temperature file (.img/.lbl)",
    )
    parser.add_argument(
        "--diviner-rock",
        type=str,
        default=None,
        help="Optional path or URL to a PDS Diviner Rock Abundance file (.img/.lbl)",
    )
    parser.add_argument(
        "--use-gee",
        action="store_true",
        help="Attempt live query to Google Earth Engine (requires prior ee.Authenticate)",
    )
    parser.add_argument(
        "--gee-project",
        type=str,
        default=None,
        help="Google Cloud project ID for Earth Engine (optional)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output_py",
        help="Output directory for CSV and GeoTIFF files (default: output_py)",
    )
    return parser.parse_args()


def run_pipeline():
    args = parse_args()
    global_mode = not args.local_window
    grid_shape = (args.rows, args.cols) if global_mode else (args.size, args.size)

    config = GridConfig(
        target_resolution_m=args.res,
        grid_shape=grid_shape,
        global_mode=global_mode,
        earth_center_lat=args.earth_lat,
        earth_center_lon=args.earth_lon,
        moon_center_lat=args.moon_lat,
        moon_center_lon=args.moon_lon,
    )

    os.makedirs(args.out_dir, exist_ok=True)

    if args.pds:
        if global_mode:
            args.lola_dem = args.lola_dem or DATA_SOURCES_URLS["lola_dem_global_pds_url"]
        else:
            args.lola_dem = args.lola_dem or DATA_SOURCES_URLS["lola_dem_pds_url"]
            args.diviner_rock = args.diviner_rock or DATA_SOURCES_URLS["diviner_rock_pds_url"]
            args.diviner_temp = args.diviner_temp or DATA_SOURCES_URLS["diviner_temp_pds_url"]
    moon_source = "real_PDS" if args.lola_dem else "synthetic"
    earth_source = "synthetic_or_gee" if args.use_gee else "global_model"

    print("=" * 78)
    print(" GLOBAL EARTH-MOON HARMONIZATION & ANALOG PIPELINE (NASA SPACE APPS 2026)")
    print("=" * 78)
    print(f" * Coverage Mode             : {'FULL PLANETARY GLOBE (-90..+90 Lat, -180..+180 Lon)' if global_mode else 'LOCAL WINDOW'}")
    print(f" * Grid dimensions           : {config.grid_shape[0]}x{config.grid_shape[1]} cells")
    print("-" * 78)

    raw_moon = extract_lunar_data(
        config,
        lola_dem_path=args.lola_dem,
        diviner_temp_path=args.diviner_temp,
        diviner_rock_path=args.diviner_rock,
    )

    raw_earth = extract_earth_data(
        config,
        try_gee=args.use_gee,
        gee_project=args.gee_project,
    )

    print("\n[CLEANING] Running QA/QC audit, physical range filtering, IQR, and interpolation...")
    clean_moon, audit_moon = clean_planetary_dataset(raw_moon, body="moon", config=config)
    clean_earth, audit_earth = clean_planetary_dataset(raw_earth, body="earth", config=config)

    audit_all = pd.concat([audit_moon, audit_earth], ignore_index=True)
    audit_csv_path = os.path.join(args.out_dir, "data_cleaning_audit_report.csv")
    audit_all.to_csv(audit_csv_path, index=False)

    print("\nData Cleaning Summary (Moon and Earth):")
    print(
        audit_all[
            [
                "body",
                "variable",
                "scale_corrected_px",
                "nodata_sentinel_px",
                "out_of_physical_range_px",
                "statistical_outliers_px",
                "total_imputed_px",
                "clean_min",
                "clean_mean",
                "clean_max",
            ]
        ].to_string(index=False)
    )

    moon_tif_path = os.path.join(args.out_dir, "moon_lola_diviner_clean.tif")
    earth_tif_path = os.path.join(args.out_dir, "earth_srtm_modis_aster_clean.tif")

    export_to_geotiff(clean_moon, moon_tif_path, body="moon", config=config)
    export_to_geotiff(clean_earth, earth_tif_path, body="earth", config=config)

    df_moon = dataset_to_dataframe(clean_moon, body="moon", config=config, source=moon_source)
    df_earth = dataset_to_dataframe(clean_earth, body="earth", config=config, source=earth_source)
    df_combined = pd.concat([df_moon, df_earth], ignore_index=True)

    moon_csv_path = os.path.join(args.out_dir, "moon_lola_diviner_clean.csv")
    earth_csv_path = os.path.join(args.out_dir, "earth_srtm_modis_aster_clean.csv")
    combined_csv_path = os.path.join(args.out_dir, "earth_moon_harmonized_clean.csv")

    df_moon.to_csv(moon_csv_path, index=False)
    df_earth.to_csv(earth_csv_path, index=False)
    df_combined.to_csv(combined_csv_path, index=False)

    analog_paths = export_web_bundle(df_moon, df_earth, out_dir=args.out_dir, web_dir="web", stride=2)

    print("\n" + "=" * 78)
    print(" EXPORTED FILES (GeoTIFF, CSV, AND ANALOG RANKING WITH IDENTICAL UNITS)")
    print("=" * 78)
    print(f" 1. Moon GeoTIFF (7 bands)   : {os.path.abspath(moon_tif_path)}")
    print(f" 2. Earth GeoTIFF (7 bands)  : {os.path.abspath(earth_tif_path)}")
    print(f" 3. Clean Moon CSV           : {os.path.abspath(moon_csv_path)}")
    print(f" 4. Clean Earth CSV          : {os.path.abspath(earth_csv_path)}")
    print(f" 5. Combined Earth-Moon CSV  : {os.path.abspath(combined_csv_path)}")
    print(f" 6. QA/QC Cleaning Report    : {os.path.abspath(audit_csv_path)}")
    print(f" 7. Analog Ranking CSV       : {os.path.abspath(analog_paths['ranking_csv'])}")
    print(f" 8. Interactive Web Data     : {os.path.abspath(analog_paths['web_js'])}")
    print("=" * 78)


if __name__ == "__main__":
    run_pipeline()
