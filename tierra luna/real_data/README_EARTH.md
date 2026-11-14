# Earth real-data table (1-degree grid)

`output_real/earth_real_1deg.csv` holds 64,800 Earth cells (180 x 360, row 0 at the north, col 0 at -180).
Every value comes from an open product that needs no account or key, or from a stated formula.
Google Earth Engine, NASA POWER and logins were not used.

## Rebuild (one command)

    /tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python "real_data/build_earth.py"
    /tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python "real_data/check_earth.py"

The venv needs numpy, pandas, rasterio, pyproj and netCDF4. Raw files go to `EARTH_RAW_DIR`, which defaults to the
scratchpad `stars/realdata/earth_raw/`, never the repository. The 12 monthly LST files (about 3 GB in total) are
downloaded one at a time, reduced to 1 degree and deleted. A clean build transfers about 5.7 GB in total and needs about 1.8 GB of disk (1.57 GB of raw files kept for rebuilding plus 0.23 GB of cache). The full build took about 35 minutes here. After the verification fixes (2026-11-14) a rebuild with `--no-download` from the raw files (all stage caches removed except the 12 reduced monthly LST arrays, whose raw files were deleted) took 6.4 minutes and gave a byte-identical CSV (sha256 3eb11d43...). Downloads wait between requests as each host's
robots.txt asks (NCEI 60 s, Zenodo 10 s, others at least 1 s). The build is deterministic.

## Files

| file | content |
|---|---|
| `build_earth.py` | downloads (when missing) and aggregates everything to the grid |
| `earth_sources.py` | URLs, polite downloader, manifest writer |
| `check_earth.py` | ranges, coverage, completeness and checks at known places (output saved in `checks_earth.txt`) |
| `manifest_earth.csv` | every downloaded file: URL, size, sha256, date, whether it is still on disk |
| `provenance_earth.csv` | one row per variable: level (MEASURED / DERIVED / MODELLED), product, version, URL, licence and credit, resolution, aggregation, formula, caveats |
| `column_aliases.json` (`EARTH` key) | mission variable name -> real column, with the true baseline. `slope_300m_deg` -> `slope_deg` (3.7 km baseline); `rough_300m_m` -> `roughness_m` (1.853 km lag in both directions) |
| `class_mappings.json` (`EARTH` key) | assumed land-cover -> `thermal_inertia_class` mapping with a reason for each class; permafrost thresholds |

## Sources

- **Relief:** ETOPO 2022 60" surface (NOAA NCEI).
- **Land share and land cover:** ESA CCI/C3S Land Cover 2020 v2.1.1, 300 m (anonymous Planetary Computer copy).
- **Land surface temperature:** OpenLandMap MODIS MOD11A2 LST climatology 2000-2017, 1 km (Zenodo 1420115).
- **Air tmin, wind, precipitation, insolation:** WorldClim 2.1, 10' (interpolated, 1970-2000).
- **Permafrost:** Obu et al. permafrost probability, NH and Antarctic (PANGAEA).
- **Sun geometry:** formula with the IAU 2006 obliquity.

NASA Earth Observations (NEO) no longer serves files: it redirects to science.nasa.gov. CERES, GPM IMERG and
MCD12C1/MOD11C3 at NASA DAACs need Earthdata Login, so they were skipped.

## Things to keep in mind

- `temp_k` is land **surface** temperature (clear sky, mean of the ~10:30 and ~22:30 overpasses), not air temperature.
- `lst_diurnal_amp_k` is the day overpass minus the night overpass, so it underestimates the true daily amplitude.
- `tmin_c` is air temperature: the coldest month's mean daily minimum.
- `wind_max_ms` is the windiest month's **mean** wind speed, not a gust.
- `rock_or_bare_frac` is a land-cover share (bare plus sparse vegetation), not rock abundance.
- The Antarctic interior has no LST, and `permafrost_class` is empty south of about 18-25 N except on Antarctic rock outcrops.

## Changes made during verification (2026-11-14)

- `roughness_m`: east-west pairs are now taken at the same metric lag as north-south pairs (1.853 km, i.e.
  1/cos(lat) pixels, linear interpolation), exactly as in the Moon table. The first build used a 1-pixel east
  lag (1.853 cos(lat) km), which lowered roughness (new/old median ratio 1.005 at |lat| < 30, 1.075 at 30-60, 1.26 at 60-75 and 1.44 poleward of 75 deg) and did not match the Moon.
- `elevation_m`, `elevation_all_m`, `slope_deg`: cos(lat) area-weighted cell means, as in the Moon table
  (elevation changes: median 0.2 m, 99th percentile 22 m, maximum 57 m at 85.5 S).
- New `slope_iso_deg`, `slope_iso_p90_deg`: same definition as the Moon's (3.706 km baseline in both directions).
- `permafrost_class` / `permafrost_area_frac`: empty on cells with no CCI land pixel (18 coastal/ocean cells had a class before).
- `thermal_inertia_class` is MODELLED (an assumed mapping), not DERIVED.
- WorldClim licence corrected: non-commercial use, no redistribution without permission (it is not CC BY).
- The NH permafrost map reaches about 18-25 N, not 25 N everywhere (Mauna Kea, 19.5 N, is mapped).
- Cell latitudes are WGS84 geodetic, not planetocentric (at most 0.19 deg apart); not converted.
