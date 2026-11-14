# Earth–Moon Planetary Data Extraction, Harmonization, and Cleaning Pipeline

Python pipeline (with an optional Google Earth Engine script) that builds a **Lunar** grid (LRO LOLA + Diviner) and a **Terrestrial** grid (SRTM, MODIS, ASTER, SAR) with **identical spatial resolution (500 m/px by default) and identical SI physical units**, applies a multi-stage QA/QC cleaning pipeline, and exports the results to **multiband GeoTIFF** and **CSV**.

> [!IMPORTANT]
> **Data Source Modes:**
> - **Moon (`--pds`)**: Downloads and processes **real NASA PDS data** from **LRO LOLA** (`ldem_64.img`, 64 px/deg = 473.8 m/px) and **LRO Diviner** (`dgdr_ra_avg_cyl_032_img.img` rock abundance and `dgdr_st_clc_cyl_0030_032_img.img` nighttime regolith temperature at ~00:30 LT, 32 px/deg = 947.6 m/px) via HTTP Range requests cached locally in `data/cache/`. Running without `--pds` uses the synthetic generator with injected artifacts to test all QA/QC cleaning branches.
> - **Earth**: Uses the calibrated local Python model (`earth_extractor.py`) by default. Passing `--use-gee` (requires a Google Earth Engine account) or running `gee_earth_grid_export.js` in the GEE Code Editor queries Google Earth Engine in the cloud.

## Verification Status

| Component | Status |
| :--- | :--- |
| Real PDS Lunar Pipeline (`python main.py --pds`) | Verified with LRO LOLA (`ldem_64`) and Diviner (`dgdr_ra_avg`, `dgdr_st_clc_0030`) over Tycho crater (`-43.3 deg`, `-11.4 deg`) |
| Synthetic Pipeline (`python main.py`) | Executed with Python 3.12; generates 7-band GeoTIFF and CSV files |
| Automated Test Suite (`tests/test_pipeline.py`) | **12 of 12 passed** (including real PDS `.lbl`/`.img` extraction, Diviner multi-LT temperature fusion, and analog ranking) |
| Interactive Web Map & Weight Sliders (`web/index.html`) | Generated and synced with `analog_finder.py` (`web/analog_data.js`) |
| Google Earth Engine Cloud Connection & `.js` Script | Untested locally (project runs locally without cloud credentials) |

## Repository Structure

| File | Description |
| :--- | :--- |
| `config.py` | Data source URLs, GEE collection IDs, target resolution, study center coordinates, and valid physical ranges |
| `pds_reader.py` | PDS3 label (`.lbl`) parser and local metric window resampler for binary `.img` files (local or via HTTP Range cached in `data/cache/`) |
| `lunar_extractor.py` | Lunar variable extraction (LOLA: elevation, slope, roughness; Diviner: fused multi-LT surface temperature and rock abundance) |
| `earth_extractor.py` | Terrestrial variable extraction (SRTM, ASTER, MODIS, SAR) via GEE or local calibrated engine |
| `harmonizer_cleaner.py` | QA/QC cleaning pipeline (with a 30% maximum interpolation threshold), audit report generator, and GeoTIFF/CSV exporter |
| `analog_finder.py` | Planetary Z-score normalization, customizable multi-variable similarity ranking, and web data bundle exporter |
| `main.py` | Command-line interface (`--pds` for real PDS lunar data) |
| `web/index.html` | Interactive web dashboard with Leaflet map, side-by-side planetary grid canvas, weight sliders, and live ranking table |
| `gee_earth_grid_export.js` | Standalone script for the Google Earth Engine Code Editor |
| `tests/test_pipeline.py` | 12 automated unit and integration tests with `pytest` |

## Harmonized Variables (7 Bands, Identical Across Moon and Earth)

| # | Variable | Physical Unit | Moon Source | Earth Source |
| :-: | :--- | :--- | :--- | :--- |
| 1 | `elevation_m` | `m` | LOLA GDR DEM | SRTM, gap-filled with ASTER GDEM |
| 2 | `elevation_rel_m` | `m` | DEM minus local mean | DEM minus local mean |
| 3 | `slope_deg` | `deg` (0–90) | 2D gradient of DEM | 2D gradient of DEM |
| 4 | `roughness_m` | `m` | Local 3×3 standard deviation | Local 3×3 standard deviation |
| 5 | `temp_k` | `K` | Diviner Lunar Radiometer | MODIS LST × 0.02, with ASTER fallback |
| 6 | `rock_or_bare_frac` | `[0–1]` | Diviner rock abundance | ASTER bare soil / rock fraction (`1 - NDVI`) |
| 7 | `sar_sigma0_db` | `dB` | Radar backscatter | C-band SAR backscatter (Sentinel-1 / RADARSAT analog) |

## Data Cleaning Pipeline (`harmonizer_cleaner.py`)

1. **Scale factor correction**: Unscaled MODIS LST digital numbers (`7500 < value < 20000`) are automatically multiplied by `0.02` to convert to Kelvin (`K`).
2. **Sentinel & NoData masking**: Sentinel values (`-32768`, `-9999`, `1e32`), `NaN`, and `Inf` are masked as missing.
3. **Planetary physical range filtering**: Values outside valid physical bounds for each planetary body are masked (e.g., `[20, 420] K` on the Moon; `[180, 360] K` on Earth).
4. **Statistical outlier filtering (3.5× IQR)**: Applied **only** to impulse-noise-prone bands (`temp_k`, `rock_or_bare_frac`, `sar_sigma0_db`). Topographic bands are not clipped by IQR so real crater floors and ridges are preserved.
5. **Spatial hole interpolation (void filling) & derivative recomputation**: Missing pixels are filled via nearest valid neighbor interpolation only if the missing fraction is at most `30%` (`max_impute_frac=0.30`); otherwise they are preserved as `nodata` to avoid fabricating data. Topographic slope, roughness, and relative elevation are then recomputed on the cleaned DEM.

Every run outputs `data_cleaning_audit_report.csv` with the exact pixel counts modified at each stage.

## Usage

```bash
pip install -r requirements.txt
python main.py --pds --res 500 --size 120 --out-dir output_py
python main.py --res 500 --size 120 --out-dir output_py
pip install pytest
python -m pytest tests -v
```

On Windows, if `python` opens the Microsoft Store stub, install Python with `winget install Python.Python.3.12`.

## Output Files (`output_py/` and `web/`)

- `moon_lola_diviner_clean.tif` and `earth_srtm_modis_aster_clean.tif`: 7-band GeoTIFFs, `EPSG:3857`, `500 m/px`.
- `moon_lola_diviner_clean.csv`, `earth_srtm_modis_aster_clean.csv`, and `earth_moon_harmonized_clean.csv`: Tabular datasets with coordinates (`x_m`, `y_m`, `lat_deg`, `lon_deg`) and all 7 harmonized variables.
- `analog_ranking.csv`: Top ranked terrestrial analog sites with overall similarity percentage, per-variable similarity scores, and matched lunar geomorphological zone.
- `data_cleaning_audit_report.csv`: QA/QC cleaning audit report.
- `web/index.html` & `web/analog_data.js`: Interactive web application with map and weight sliders (can be opened directly in any browser).

## Known Limitations

- Both GeoTIFFs use `EPSG:3857` so desktop GIS tools can overlay them on the same metric grid; `EPSG:3857` is not a native lunar CRS, and CSV `lat_deg`/`lon_deg` values are local spherical approximations.
- Without Google Earth Engine credentials (`--use-gee`), terrestrial bands are generated by the local calibrated model in `earth_extractor.py`.

## Reference Data Portals

- NASA Space Apps Challenge 2026: https://www.spaceappschallenge.org/2026/
- NASA PDS: https://pds.nasa.gov/ · LRO: https://pds-geosciences.wustl.edu/missions/lro/ · Diviner: https://pds-geosciences.wustl.edu/missions/lro/diviner.htm
- NASA Earthdata Search (Cryosphere) & NASA Worldview (configured in `config.py`)
- CSA RCM: https://donnees-data.asc-csa.gc.ca/en/dataset/rcm · RADARSAT-1: https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1 · SAR Tutorial: https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial
- Copernicus Data Space: https://dataspace.copernicus.eu/ · ESA Open Science Data: https://opensciencedata.esa.int/ · JAXA G-Portal: https://www.gportal.jaxa.jp/?lang=en
