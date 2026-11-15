# Real-data input tables (1-degree grid, Earth and Moon)

Both tables use the same grid: 180 rows x 360 columns, row 0 at the north (centre latitude 89.5), column 0 at
the west (centre longitude -179.5), longitudes -180..180 east-positive, planetocentric latitude. Missing values are
empty, never 0 and never a fill value. No Google Earth Engine, no NASA POWER API, no accounts or keys.

- Earth: see `README_EARTH.md`.
- Both, verified and concatenated: see `../../docs/REAL_DATA.md` (independent re-computation, fixes, provenance, mission readiness). `build_combined.py` writes `output_real/earth_moon_real_1deg.csv` and `mission_readiness.json`.
- Moon: see below.

<!-- MOON START -->
## Moon: `output_real/moon_real_1deg.csv`

64,800 cells. Built by `build_moon.py` from LOLA, Diviner and LOLA polar-illumination products (PDS / NASA GSFC),
plus exact Sun geometry. Every column has a row in `provenance_moon.csv` with its level (MEASURED, DERIVED,
MODELLED or no data), product, version, URL, credit, resolution, aggregation, formula and caveats.

### Rebuild (one command)

    /tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/venv/bin/python -I "real_data/build_moon.py" --raw-dir <scratch>/stars/realdata/moon

Raw files go to `--raw-dir` (default: the scratchpad `stars/realdata/moon/`), never into the repository. Files
already listed in `<raw-dir>/manifest_moon_raw.json` with the right size are not downloaded again, and reduced
caches in `<raw-dir>/reduced/` are reused. The 18 Diviner GCP tables (156 MB each, 2.8 GB) are downloaded one
at a time, reduced to 0.5-degree diurnal statistics and deleted (`--keep-raw` keeps them). Peak disk use is
about 450 MB; about 3.1 GB are transferred in a clean build (about 6 minutes here). Each request is preceded by
a HEAD, and requests to one host are at least 1 s apart. The client identifies as `Claude-User`, which the
pds-geosciences.wustl.edu robots.txt explicitly allows (its generic `*` rules disallow `/lro/`). The build is
deterministic (no random numbers, fixed quadrature grids).

### Files

| file | content |
|---|---|
| `build_moon.py` | download, reduce, assemble, self-check |
| `provenance_moon.csv` | one row per column |
| `manifest_moon.csv` | every file downloaded: URL, bytes, sha256, UTC date, HEAD status, use, still on disk? |
| `lunar_named_sites.csv` | IAU features that matter to the missions, their gazetteer coordinates, the cell they fall in and that cell's values |
| `checks_moon.json` | self-checks (below) |
| `column_aliases.json` (`MOON` key) | mission variable name -> real column, true baseline, caveat |

### Columns and levels

| column | level | source |
|---|---|---|
| elevation_m | MEASURED | LOLA LDEM_16 V3.1 (1.895 km pixels), cos-lat weighted cell mean; height above the 1737.4 km sphere |
| slope_deg, slope_p90_deg | DERIVED | LDEM_16, common Earth/Moon definition (central differences, 1-pixel east-west spacing) |
| slope_iso_deg, slope_iso_p90_deg | DERIVED | same, with a 3.79 km baseline in both directions (use these poleward of ~85 deg) |
| roughness_m | DERIVED | RMS height difference at a 1.895 km lag (Rosenburg et al. 2011 deviogram) |
| rock_abundance_frac | MEASURED | Diviner rock abundance (Bandfield et al. 2011), 60S-60N only, empty elsewhere |
| tmax_k, tmin_k | MEASURED | Diviner GCP (Williams et al. 2017), bolometric brightness temperature, diurnal max / min of the measured local-time bins |
| temp_k | DERIVED | same, diurnal mean after circular linear interpolation of empty local-time bins (gaps up to 3 h); relabelled from MEASURED during verification |
| lst_diurnal_amp_k, tmin_c | DERIVED | tmax_k - tmin_k; tmin_k - 273.15 |
| illum_frac | DERIVED everywhere: at abs(lat) >= 65.5 from the LOLA AVGVISIB 240 m product (Mazarico et al. 2011), which is the LOLA team's ray-traced SIMULATION over measured LOLA topography, not a light measurement (`illum_frac_level` = DERIVED_LOLA_TOPOGRAPHY); elsewhere flat-ground geometry (DERIVED_FLAT_GEOMETRY). Relabelled from MEASURED during verification | see `illum_frac_level` |
| irradiance_kwh_m2_day | DERIVED | S0 = 1361 W/m2 x horizontal-surface geometry, with the LOLA topographic illum_frac where it exists |
| sun_elev_max_deg, sun_low_frac_0_5deg | DERIVED | exact geometry, obliquity 1.54 deg (PIA13720) |
| mask_fraction, rock_or_bare_frac | MODELLED | 1 by definition (no ocean, no vegetation) |
| thermal_inertia_class | MODELLED | "regolito" everywhere (NASA: "Nearly the entire Moon is covered by ... lunar regolith") |
| permafrost_class | MODELLED | the label 'ninguno' in every cell, set by definition (team lead decision 2026-11-14; provenance_moon.csv), not empty (corrected 2026-11-15 after the statistical audit, docs/stats_audit/1_datos_rejilla_nombres.md 1.6.2) |
| rain_mm_day, wind_max_ms | no data | not applicable on the Moon: empty, not 0 |

`slope_300m_deg` and `rough_300m_m` are not written: no global product has a 300 m baseline. `column_aliases.json`
maps them to `slope_deg` and `roughness_m` with the true baselines.

Irradiance (horizontal, per 24 h): 10.40 kWh/m2/day at the equator, 7.29 at 45.5 deg, 0.84 at 85.5 deg
(geometric), 0.42 at 85.5 deg with the LOLA topographic lit fraction.

### Self-checks (checks_moon.json)

- Elevation vs the committed 2-degree table: correlation 0.9995, median difference 10 m. The committed table is
  an unweighted block mean of LDEM_4 (reproduced to 0.001 m); its lack of area weights gives differences of
  100-1100 m poleward of ~73 deg. Area-weighted LDEM_4 vs this table: median 8 m, maximum 144 m.
- Temperatures vs the R2 latitude profile: zonal medians of max, min and amplitude agree within 0-3.5 K in every
  band (e.g. 0-10N max 391.4 / min 94.4 K vs R2 391.8 / 94.4 K; published 95-390 K, NSSDC Moon fact sheet).
- Empty values: rock_abundance_frac 21,608 (60 rows outside 60S-60N plus 8 cells with < 50 % valid pixels);
  rain_mm_day, wind_max_ms 64,800 (not applicable). permafrost_class is not empty: the MODELLED label 'ninguno' in all
  64,800 cells (corrected 2026-11-15 after the statistical audit, docs/stats_audit/1_datos_rejilla_nombres.md 1.6.2). All other columns are complete.
- One Diviner label (40s30s) has its MINIMUM and MAXIMUM_LATITUDE swapped; the build uses the data's own latitudes.

### What a 1-degree cell can and cannot show

A cell is 30.3 km north-south but only 30.3 x cos(lat) km east-west: 1.3 km at 87.5 deg and 0.26 km next to the
pole. Near the poles it is a strip that crosses rims, slopes and crater floors, so it averages lit ridges with
shadowed craters. The best-lit points (about 90 % of the time) and the Shackleton-de Gerlache ridge do not appear;
cell illum_frac near Shackleton is about 0.15. `lunar_named_sites.csv` lists, for each site, what the cell can
resolve.

### Notes for the engine

- `elevation_m` is relative to a sphere. About 62 % of the Moon's area (67 % of the cells) is below 1 m, so the
  common gate `elevation_m >= 1` (meant to drop Earth oceans) would drop most of the Moon. Use `mask_fraction`
  instead.
- Temperatures are surface brightness temperatures, not air temperatures.
- `rain_mm_day` and `wind_max_ms` are empty on the Moon. A rule that needs them must treat them as not applicable.
<!-- MOON END -->
