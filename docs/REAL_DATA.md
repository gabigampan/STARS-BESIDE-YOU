# Real-data tables for Earth and Moon (1-degree grid)

Team "Stars Beside You", NASA Space Apps Challenge 2026. Built and independently verified on 2026-11-14.
No Google Earth Engine, no NASA POWER API, no accounts, logins or keys.

## 1. What there is

| file | content |
|---|---|
| `tierra luna/output_real/earth_real_1deg.csv` | 64,800 Earth cells, 37 columns (25,497 cells contain land) |
| `tierra luna/output_real/moon_real_1deg.csv` | 64,800 Moon cells, 31 columns |
| `tierra luna/output_real/earth_moon_real_1deg.csv` | both tables, 129,600 rows, 43 columns, the team's column order first where names coincide |
| `tierra luna/real_data/provenance_earth.csv`, `provenance_moon.csv` | one row per column: level, product, version, URL, licence and credit, native resolution, aggregation, formula, caveats |
| `tierra luna/real_data/manifest_earth.csv`, `manifest_moon.csv` | every downloaded file: URL, size, sha256, date, still on disk or not |
| `tierra luna/real_data/manifest_verification.csv` | the 4 files downloaded again for this verification (same sha256 as the builders' manifests; deleted afterwards) |
| `tierra luna/real_data/column_aliases.json` | mission variable name -> real column, per body, with the true baseline and a caveat |
| `tierra luna/real_data/class_mappings.json` | assumed land-cover -> `thermal_inertia_class` mapping and permafrost thresholds (Earth) |
| `tierra luna/real_data/mission_readiness.json` | per mission and body: cells with every needed variable present |
| `tierra luna/real_data/lunar_named_sites.csv` | IAU lunar features, their gazetteer coordinates and the cell they fall in |
| `tierra luna/real_data/verification/` | the independent check scripts and their outputs (section 6) |
| `tierra luna/real_data/README.md`, `README_EARTH.md` | builder notes |

Rebuild (raw files and caches live in the scratchpad `stars/realdata/`, never in the repository):

    PY=<scratchpad>/stars/venv/bin/python
    $PY -I "tierra luna/real_data/build_earth.py"        # downloads what is missing; --no-download uses the disk
    $PY -I "tierra luna/real_data/build_moon.py"         # downloads what is missing, reuses reduced caches
    $PY -I "tierra luna/real_data/build_combined.py"     # concatenation + mission_readiness.json
    $PY -I "tierra luna/real_data/check_earth.py"        # Earth self-check -> checks_earth.txt

Current sha256: Earth `3eb11d43c6d316c7166f937c0a52354327340c5e1f44f7df7ec580a7bb40f599`,
Moon `906de058b977c5aba81901531edae624df659662eea2de8806d58df7b93d4c82`,
combined `f6ac7250bfbebe0fadbaff235944716d0e474580cb64cf2b8f0acfbef0a30b4c`.

## 2. Common definitions (both bodies)

- **Grid.** 1-degree cells, 180 rows x 360 columns. Row 0 is the north (centre latitude 89.5), column 0 is the
  west (centre longitude -179.5), longitudes -180..180 east-positive. `cell_id` = body initial + `row*360+col`
  (E0..E64799, M0..M64799). `cell_km` is the true north-south size: 110.574-111.694 km on Earth (WGS84 meridian
  arc), 30.323 km on the Moon (R = 1737.4 km). East-west size is `cell_km * cos(lat)`.
- **Latitude type.** The Moon uses planetocentric latitude (LOLA, Diviner and the gazetteer are on a 1737.4 km
  sphere, where planetocentric = planetographic). **Earth does not:** its cells are boxes in the products' WGS84
  geodetic latitude. The two differ by at most 0.19 deg (21 km, at 45 deg), a fifth of a cell. Converting would mean
  re-binning every source pixel by pixel, and the monthly LST rasters are no longer on disk; not done.
- **Missing** is an empty field, never 0 and never a fill value. No fill value survives in any table (checked:
  -9999, -32768, -32767, 32767, 65535, -99999, |x| > 1e20, "nan" strings).
- **Relief** from the DEM pixels at native spacing on a sphere (Earth R = 6371.0088 km, ETOPO 2022 60" pixels of
  1.853 km; Moon R = 1737.4 km, LOLA LDEM_16 pixels of 1.895 km), true metric spacing (east-west spacing =
  dy cos(lat)):
  - `elevation_m` = area-weighted (cos lat) mean of the pixels (Earth: land pixels only).
  - `slope_deg` = area-weighted mean of pixel slopes from central differences, `atan(hypot(dz/dx, dz/dy))`;
    baseline 2 pixels = 3.706 km (Earth) / 3.790 km (Moon) north-south, times cos(lat) east-west.
  - `slope_p90_deg` = 90th percentile of the same pixel slopes (unweighted).
  - `slope_iso_deg`, `slope_iso_p90_deg` = same, east-west baseline never shorter than north-south
    (lag max(1, 1/cos lat) pixels). Use these poleward of about 85 deg, where the literal east-west spacing
    falls to tens of metres and `slope_deg` becomes noisy (Moon `slope_p90_deg` reaches 84 deg at 89.5).
  - `roughness_m` = sqrt(mean squared height difference) of pixel pairs one DEM pixel apart in metric distance
    (1.853 km Earth, 1.895 km Moon), north-south and east-west pairs pooled; the deviogram of Rosenburg et al.
    2011 (JGR 116, E02001) at that lag.
  - **No 300 m baseline exists here.** `slope_300m_deg` and `rough_300m_m` are not written; `column_aliases.json`
    maps them to `slope_deg` and `roughness_m` with the real baselines. Kilometre-baseline slopes are much gentler
    than 300 m slopes and kilometre-lag roughness is larger, so the mission thresholds (15 deg, 5-650 m) do not
    transfer directly. (For the Moon, LOLA LDSM/LDRM products with 30-120 m baselines exist; no keyless global
    Earth equivalent is used, so they were not mixed in.)
- **Sun geometry** (DERIVED, exact formula, cell-centre latitude, Sun centre, flat horizon, no refraction,
  circular orbit): `sun_elev_max_deg = 90 - max(0, |lat| - eps)`; `sun_low_frac_0_5deg` = time with
  0 < h <= 5 deg divided by time with h > 0 over a year, with `sin(dec) = sin(eps) sin(L)` and
  `sin(h) = sin(lat) sin(dec) + cos(lat) cos(dec) cos(H)`, L and H uniform in time. Earth eps = 84381.406" =
  23.4392794 deg (IAU 2006, IERS Conventions 2010 ch. 5, https://iers-conventions.obspm.fr/content/chapter5/icc5.pdf);
  Moon eps = 1.54 deg (NASA PIA13720, https://science.nasa.gov/photojournal/south-pole-illumination-map/).
- **Levels.** MEASURED = read from a downloaded official product (spatial averaging only). DERIVED = computed by a
  stated formula from measured values. MODELLED = estimated, interpolated, simulated by a model, or assumed.
  "no data" = left empty, not estimated.

## 3. Sources, credits and licences

| product | used for | URL | licence / credit |
|---|---|---|---|
| NOAA NCEI ETOPO 2022 v1, 60" surface (ice surface, EGM2008 heights) | Earth relief | https://www.ngdc.noaa.gov/thredds/fileServer/global/ETOPO2022/60s/60s_surface_elev_netcdf/ETOPO_2022_v1_60s_N90W180_surface.nc | US Government work, no restrictions. Credit NOAA NCEI (2022), doi:10.25921/fd45-gt74 |
| ESA CCI / C3S Land Cover 2020 v2.1.1, 300 m (anonymous Microsoft Planetary Computer COG copy) | land share, bare share, thermal class | https://planetarycomputer.microsoft.com/dataset/esa-cci-lc (blob needs a keyless SAS token from planetarycomputer.microsoft.com/api/sas/v1/token) | free use with attribution: "ESA Climate Change Initiative - Land Cover led by UCLouvain (2017)" and Copernicus C3S |
| OpenLandMap MODIS MOD11A2 LST climatology 2000-2017 v1.0 (Hengl 2018), 1 km | Earth LST, diurnal amplitude | doi:10.5281/zenodo.1420115 | CC BY-SA 4.0 (checked on the Zenodo record). Source NASA MOD11A2 v006, doi:10.5067/MODIS/MOD11A2.006 |
| WorldClim 2.1, 10', 1970-2000 (Fick & Hijmans 2017) | Earth tmin, rain, wind, insolation | https://geodata.ucdavis.edu/climate/worldclim/2_1/base/ | **Not CC BY** (the builder said CC BY 4.0; corrected). worldclim.org: "freely available for academic use and other non-commercial use. Redistribution or commercial use is not allowed without prior permission." Publishing these columns outside a non-commercial academic context may need permission |
| Obu et al. permafrost probability PERPROB v5.0: NH 2000-2016 (PANGAEA 888600), Antarctic 2000-2017 (PANGAEA 902576) | Earth permafrost | https://store.pangaea.de/Publications/ObuJ-etal_2018/ , .../ObuJ-etal_2019/ | NH CC BY 3.0, ANT CC BY 4.0 (checked on PANGAEA) |
| LOLA LDEM_16 V3.1 (PDS) | Moon relief | https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_16.img | NASA PDS, public. Credit LOLA team, Smith et al. 2010 |
| Diviner Global Cumulative Products, tbol, files *_002 (Williams et al. 2017) | Moon temperatures | https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/ | NASA PDS, public. Credit Diviner team (UCLA), Williams et al. 2017, Icarus 283:300 |
| Diviner rock abundance DGDR_RA_AVG_CYL_032 (Bandfield et al. 2011) | Moon rock abundance | .../data_derived_gdr_l3/cylindrical/img/dgdr_ra_avg_cyl_032_img.img | NASA PDS, public. Credit Bandfield et al. 2011, JGR 116, E00H02 |
| LOLA average illumination AVGVISIB_65S/65N_240M_201608 (Mazarico et al. 2011) | Moon polar lit fraction | https://pgda.gsfc.nasa.gov/data/MoonIllumination/ | NASA GSFC PGDA, public. Credit Mazarico et al. 2011, Icarus 211:1066 |
| IAU/USGS Gazetteer of Planetary Nomenclature, Moon centre points | named-site cells | https://asc-planetarynames-data.s3.us-west-2.amazonaws.com/MOON_nomenclature_center_pts.zip | IAU WGPSN / USGS |
| NSSDC Moon fact sheet (S0 = 1361 W/m2, R = 1737.4 km); science.nasa.gov/moon/facts (regolith) | Moon constants and the regolith assumption | https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html | NASA |

Checked and not used: NASA Earth Observations (neo.gsfc.nasa.gov now redirects to science.nasa.gov and serves no
files); CERES, GPM IMERG, MCD12C1 and MOD11C3 at NASA DAACs (need an Earthdata Login: skipped by rule).

## 4. Provenance (final)

Full text, URLs and caveats per row are in the two provenance CSVs. Coverage = share of cells with a value
(Earth: of the 25,497 land cells; Moon: of 64,800).

### Earth

| column | level | product (native resolution) | aggregation / formula | coverage |
|---|---|---|---|---|
| elevation_m | MEASURED | ETOPO 2022 60" (1.853 km) | area-weighted mean of land pixels (pixel = land if >= 18 of its 36 CCI pixels are not water) | 0.990 |
| mask_fraction | MEASURED | ESA CCI LC 2020 (300 m) | non-water pixels / valid pixels (inland water counts as water) | 1.000 (0 over ocean) |
| slope_deg, slope_p90_deg | DERIVED | ETOPO 2022 | common definition (sec. 2), 3.706 km baseline | 0.977 |
| slope_iso_deg, slope_iso_p90_deg | DERIVED | ETOPO 2022 | isotropic 3.706 km baseline | 0.972 |
| roughness_m | DERIVED | ETOPO 2022 | deviogram at 1.853 km, both directions | 0.985 |
| rock_or_bare_frac | MEASURED (classification) | ESA CCI LC 2020 | share of land pixels in bare (200-202) or sparse vegetation < 15 % (150-153). A land-cover share, **not** rock abundance | 1.000 |
| thermal_inertia_class | MODELLED (assumed mapping) | ESA CCI LC 2020 | each CCI class -> roca/regolito/arena/suelo/hielo/agua (class_mappings.json), plurality | 1.000 |
| temp_k | DERIVED | OpenLandMap MOD11A2 LST (1 km) | per pixel (annual day + annual night)/2, cell mean. Clear-sky **land surface** temperature at ~10:30/~22:30, **not air** | 0.735 (no Antarctica) |
| lst_diurnal_amp_k | DERIVED | same | annual day - annual night LST (two overpasses, so it understates the true daily range) | 0.735 |
| lst_diurnal_amp_max_k (+ _month) | DERIVED | same, 12 monthly day-night layers | largest monthly cell mean | 0.735 |
| tmin_c | MODELLED | WorldClim 2.1 (10') | coldest-month mean daily minimum **air** temperature (2 m), interpolated 1970-2000 | 0.998 |
| irradiance_kwh_m2_day | MODELLED | WorldClim 2.1 srad | sum(srad_m days_m)/365.25/3600, global horizontal at the surface | 0.998 |
| rain_mm_day | MODELLED | WorldClim 2.1 prec | annual total / 365.25 | 0.998 |
| wind_max_ms | MODELLED | WorldClim 2.1 wind | windiest-month **mean** 10 m speed; not a gust or daily maximum | 0.998 |
| permafrost_class (+ permafrost_area_frac) | MODELLED | Obu et al. PERPROB (926.6 m) | mean probability: continuo >= 0.9, discontinuo 0.5-0.9, esporadico 0.01-0.5, ninguno < 0.01 (assumed IPA thresholds) | 0.490 |
| sun_elev_max_deg, sun_low_frac_0_5deg | DERIVED | formula, IAU 2006 obliquity | sec. 2 | 1.000 |
| slope_300m_deg, rough_300m_m | no data | none | not written; see column_aliases.json | - |
| supporting | | | `cell_km`, `elevation_all_m` (with bathymetry), `bare_frac`, `snow_ice_frac`, `lc_dominant_cci_code`, pixel counts `n_*` | |

### Moon

| column | level | product (native resolution) | aggregation / formula | coverage |
|---|---|---|---|---|
| elevation_m | MEASURED | LOLA LDEM_16 V3.1 (1.895 km) | area-weighted mean of 256 pixels; height above the **1737.4 km sphere** (not a sea level) | 1.000 |
| slope_deg, slope_p90_deg, slope_iso_deg, slope_iso_p90_deg | DERIVED | LDEM_16 | common definition, 3.790 km baseline | 1.000 |
| roughness_m | DERIVED | LDEM_16 | deviogram at 1.895 km, both directions | 1.000 |
| rock_abundance_frac | MEASURED (retrieval) | Diviner RA (948 m), 60S-60N | area-weighted mean; empty if < 50 % valid | 0.667 |
| tmax_k, tmin_k | MEASURED | Diviner GCP tbol (0.5 deg x 0.25 h, 2009-2015, all seasons averaged) | max / min of the diurnal curve per 0.5 deg bin, area-weighted mean of 4 bins | 1.000 |
| temp_k | DERIVED | same | diurnal mean after circular linear interpolation of empty local-time bins (<= 3 h gaps); bolometric **surface** temperature | 1.000 |
| lst_diurnal_amp_k, tmin_c | DERIVED | same | tmax_k - tmin_k; tmin_k - 273.15 (surface, there is no air) | 1.000 |
| illum_frac | DERIVED | at abs(lat) >= 65.5: LOLA AVGVISIB (240 m), a **ray-traced simulation** over LOLA topography; elsewhere flat-ground geometry | `illum_frac_level` = DERIVED_LOLA_TOPOGRAPHY / DERIVED_FLAT_GEOMETRY | 1.000 |
| irradiance_kwh_m2_day | DERIVED | S0 = 1361 W/m2 + exact geometry (+ topographic illum_frac at the poles) | horizontal surface, per 24 h, no atmosphere | 1.000 |
| sun_elev_max_deg, sun_low_frac_0_5deg | DERIVED | formula, eps = 1.54 deg | sec. 2 | 1.000 |
| mask_fraction, rock_or_bare_frac | MODELLED | definition | 1 everywhere (no ocean, no vegetation). rock_or_bare_frac is **not** rock abundance | 1.000 |
| thermal_inertia_class | MODELLED | assumption | "regolito" everywhere | 1.000 |
| permafrost_class | MODELLED | label set by definition (team lead decision 2026-11-14; real_data/provenance_moon.csv) | 'ninguno' in all 64,800 cells (a label, not a measurement; corrected 2026-11-15 after the statistical audit, docs/stats_audit/1_datos_rejilla_nombres.md 1.6.2: it was listed here as empty) | 0 |
| rain_mm_day, wind_max_ms | no data | not applicable (no liquid water, no atmosphere) | empty, not 0 | 0 |
| slope_300m_deg, rough_300m_m | no data | none | not written | - |

## 5. Corrections made during verification

All were fixed in the code, rebuilt and re-checked.

| # | problem found | fix |
|---|---|---|
| 1 | Earth `roughness_m` used east-west pairs one pixel apart (1.853 cos(lat) km) while the Moon used the same metric lag in both directions: the two bodies did not share a definition, and Earth roughness was too low away from the equator (new/old median ratio 1.005 at abs(lat) < 30, 1.075 at 30-60, 1.26 at 60-75, 1.44 poleward of 75; e.g. Svalbard 144 -> 203 m, Dry Valleys 200 -> 251 m) | Earth east-west pairs now at 1/cos(lat) pixels (linear interpolation), as on the Moon |
| 2 | Earth `elevation_m` and `slope_deg` were unweighted cell means, the Moon's area-weighted | Earth now area-weighted (elevation changes: median 0.2 m, 99th percentile 22 m, maximum 57 m at 85.5 S) |
| 3 | Earth lacked the isotropic slope columns the Moon has | `slope_iso_deg`, `slope_iso_p90_deg` added with the Moon's definition |
| 4 | Earth `permafrost_class` was set on 18 cells with no CCI land pixel | now empty there (land cells only, like every other land variable) |
| 5 | Earth `thermal_inertia_class` labelled DERIVED although it is an assumed class mapping | MODELLED (provenance and class_mappings.json); permafrost thresholds likewise MODELLED |
| 6 | Moon `illum_frac` at the poles labelled MEASURED; AVGVISIB is the LOLA team's simulation over measured topography, not a light measurement | DERIVED; `illum_frac_level` values renamed DERIVED_LOLA_TOPOGRAPHY / DERIVED_FLAT_GEOMETRY |
| 7 | Moon `temp_k` labelled MEASURED although it fills local-time gaps by interpolation | DERIVED (tmax_k and tmin_k stay MEASURED: linear interpolation cannot exceed the measured extremes) |
| 8 | WorldClim licence written as CC BY 4.0 | corrected: non-commercial, no redistribution without permission |
| 9 | "permafrost empty south of 25 N" was inaccurate (the NH map reaches about 18 N; Mauna Kea, 19.5 N, is mapped) | caveats corrected |
| 10 | Earth provenance had no rows for slope_300m_deg / rough_300m_m | "no data" rows added |

No numeric value in the Moon table changed; only two labels. In the Earth table only elevation_m, elevation_all_m, slope_deg,
roughness_m (plus the two new slope_iso columns) and 18 permafrost cells changed; every other column is identical to before.

## 6. Checks run (with numbers)

Scripts in `real_data/verification/` (they read the raw files directly and import nothing from the builders).

**6.1 Independent re-computation from raw files.** Every difference is at the CSV's rounding (half the last
written digit).

| body | cells | variables | maximum absolute difference |
|---|---|---|---|
| Earth | 57 (20 named places + 36 random land cells, 3 per 15-degree band + 1 ocean cell) | elevation_m, slope_deg, slope_p90_deg, slope_iso_deg, slope_iso_p90_deg, roughness_m | 0.047 m, 0.0005 deg, 0.0005 deg, 0.0005 deg, 0.0005 deg, 0.005 m |
| Earth | 57 | mask_fraction, rock_or_bare_frac, thermal_inertia_class | 5e-5, 5e-5, 0 class mismatches |
| Earth | 48 with LST | temp_k, lst_diurnal_amp_k | 0.005 K, 0.005 K |
| Earth | 56 land | tmin_c, rain_mm_day, wind_max_ms, irradiance_kwh_m2_day | 0.005 C, 0.0005 mm/d, 0.005 m/s, 0.0005 kWh/m2/d |
| Earth | 26 with a permafrost value | permafrost_area_frac, permafrost_class | 4e-5, 0 class mismatches |
| Earth | 48 | lst_diurnal_amp_max_k (July layer downloaded again) | July cell mean <= table maximum in all 48; equal (0.004 K) in the 3 cells whose maximum month is July |
| Moon | 54 (18 IAU features + 36 random cells, 2 per 10-degree band) | elevation_m, slope_deg, slope_p90_deg, slope_iso_deg, slope_iso_p90_deg, roughness_m | 0.05 m, 0.0005 deg, 0.0005, 0.0005, 0.0005, 0.005 m |
| Moon | 37 within 60S-60N | rock_abundance_frac | 5e-5 |
| Moon | 45 in 3 bands downloaded again (0-10N, 30-40S whose label has swapped latitudes, 80-90S) | temp_k, tmax_k, tmin_k, lst_diurnal_amp_k, tmin_c | 0.005 K each |
| Moon | 16 polar cells | illum_frac, irradiance | <= 0.006 and <= 0.006 kWh/m2/d at 66.5-87.5 deg. At 88.5-89.5 deg the cell is a 0.26-0.8 km wide strip and the value depends on how 240 m pixels are assigned (pixel centre in the cell vs pixels touched by the cell): Shackleton 0.147 (table) vs 0.122, Peary 0.132 vs 0.138. Both are defensible; the table's rule is stated |
| both | all 180 rows | sun_elev_max_deg, sun_low_frac_0_5deg (closed-form day length per declination, a different method), Moon geometric irradiance | <= 0.0003, <= 0.0002, <= 0.0005 kWh/m2/d |

**6.2 Grid, units and longitude.** Both tables: 64,800 unique ids, `lat = 89.5 - row`, `lon = -179.5 + col`,
`cell_id` matches. LOLA and Diviner RA are 0..360 east in the PDS labels (WESTERNMOST_LONGITUDE 0,
CENTER_LONGITUDE 180) and are rolled correctly; Diviner GCP is already -180..180. Placement tests: Tycho
(gazetteer -43.30, -11.22) falls in cell (-43.5, -11.5), whose rock abundance is 0.065 against 0.003 in the cell
at +11.5 E; Aristarchus 0.037 vs 0.003; Copernicus pre-dawn temperature 102 K vs 94 K at the mirrored longitude
(rocky ejecta stay warm); the LDEM_16 maximum near Mons Huygens lies at (19.53, -2.91) against the gazetteer
(19.92, -2.86). Earth: the ETOPO maximum near Everest is 8157 m at (27.992, 86.925) against the summit
(27.988, 86.925), Kilimanjaro 5727 m at (-3.075, 37.358), Denali 5770 m at (63.075, -151.008), Mont Blanc 4169 m
at (45.842, 6.858): each inside its table cell. Units: ETOPO and LOLA metres; LST stored as K x 50 (scale 0.02,
verified: Sahara annual day pixel 313 K); WorldClim srad kJ m-2 day-1; RA = DN x 0.001; AVGVISIB DN x 4e-5.

**6.3 Provenance against code and the web.** Every level was compared with what the code computes (corrections in
section 5). URLs answered on 2026-11-14 (one request per host, at least 2 s apart): ETOPO file, NCEI page, WorldClim
zip and page, Zenodo LST file, PANGAEA zip, PDS LDEM_16, Diviner RA, PGDA illumination TIF, MIT label, IERS PDF,
NSSDC fact sheet, science.nasa.gov pages: 200 (PIA13720 after a 301 to its trailing-slash URL, which quotes the
1.54 deg tilt; doi.org for MOD11A2: 302 to the DAAC). The CCI blob gives 409 without the keyless SAS token, as
expected. Licences checked on the source pages: Zenodo record 1420115 CC BY-SA 4.0; PANGAEA 888600 CC BY 3.0 and
902576 CC BY 4.0; WorldClim non-commercial (section 3). No column without a source carries a value: Moon
rain and wind are empty in all 64,800 cells, and Moon permafrost_class is the MODELLED label 'ninguno' in all 64,800
(set by definition, real_data/provenance_moon.csv; corrected 2026-11-15 after the statistical audit, docs/stats_audit/1_datos_rejilla_nombres.md 1.6.2); Earth LST is empty in Antarctica rather than filled.

**6.4 Physical sanity.** Earth land (mask_fraction >= 0.5): LST vs abs(lat) Spearman -0.92; LST anomaly vs
elevation anomaly within each latitude row r = -0.71, slope -4.4 K/km (a surface lapse rate); tmin_c vs temp_k
r = 0.94; bare share vs rain (abs(lat) < 60) Spearman -0.76; diurnal amplitude vs rain -0.31; largest LST
309.7 K (13.5 N, 40.5 E, Danakil); largest amplitude 35.7 K (Atacama). Moon: temp_k vs abs(lat) Spearman -0.99;
zonal medians of max/min/amplitude 391.4/94.4/297.3 K at 0-10 N, 353.7/87.9/265.7 K at 40-50 N, 231.9/54.9/176.9 K
at 80-90 S, matching R2 (391.8/94.4/297.7 K at 0-10 N) and the NSSDC 95-390 K; coldest cell 26.8 K (86.5 S),
23 cells never above 110 K (cold traps). Measurement, not formula: within one latitude row the median standard
deviation is 3.7 K for Earth LST, 2.3 K for lunar temp_k and 3.3 K for lunar tmax_k, and lunar rock abundance
correlates with the pre-dawn temperature anomaly (Spearman 0.58, abs(lat) < 30), as rocks stay warm at night. The
variables that are formulas (sun geometry, lunar irradiance outside the poles) have zero spread within a row and
are labelled DERIVED. Earth-Moon contrast: median diurnal amplitude 9.7 K (Earth land, maximum 35.7 K) vs
265.6 K (Moon; only 11 polar cells are at or below 35.7 K); median slope_deg 0.49 vs 5.30 deg; median roughness
15.3 vs 159.7 m (99th percentiles 268 vs 374 m). Elevation ranges: Earth -2570..5420 m (cell means), Moon
-8176..9102 m.

**6.5 Reproducibility.** All files on disk match their manifest sha256 and size (Earth 41 of 53 listed, the 12
monthly LST files were deleted by design after reduction; Moon 30 of 48, the 18 GCP tables deleted after
reduction). The 4 files downloaded again for this check (3 GCP bands, the July LST layer) have exactly the
sha256 in the builders' manifests. Earth: with every stage cache removed except the 12 reduced monthly LST arrays,
`build_earth.py --no-download` rebuilt from the raw files in 6.4 minutes and gave a byte-identical CSV. Moon:
with the LOLA, rock and illumination caches removed, `build_moon.py` rebuilt from the raw files in 19 s and gave a
byte-identical CSV (the GCP reduction was reused; its raw tables are 2.8 GB and were not all downloaded again, but
3 of 18 bands were re-reduced independently, 6.1). A full clean build was not run: it would transfer about
5.7 GB (Earth) and 3.1 GB (Moon), above the download budget.

## 7. Mission readiness

From `mission_readiness.json` (`build_combined.py`): cells where every variable the mission reads is present,
using `column_aliases.json` (slope_300m_deg -> slope_deg, rough_300m_m -> roughness_m). "Needed" = common gates
(elevation_m, mask_fraction) + require_present + gates + weighted soft criteria. Earth counts are over the 25,497
land cells, Moon over 64,800 cells.

| mission | Earth: all needed present | Moon: all needed present | note |
|---|---|---|---|
| rover | 24,918 (24,909 also with rain/wind/tmin for workable_days) | 64,800 (0 with workable_days: no rain or wind on the Moon) | |
| solar | 18,362 | 64,800 | Earth limited by LST (lst_diurnal_amp_k soft criterion; none in Antarctica) |
| thermal | 11,520 strictly; 18,627 if the permafrost soft criterion uses its declared default | 0 strictly; 64,800 with the default | permafrost_class is a soft criterion with "default": 0.5 |
| ice | 11,521 | 0 | permafrost_class is required; it does not apply to the Moon |

Literal gate pass counts (information only, the engine decides): rover 11,141 Earth / 21,135 Moon; solar 12,717 /
19,152; thermal 2,419 / 21,298; ice 4,964 / 0. **The common gate `elevation_m >= 1` keeps only 21,298 lunar
cells (33 %)**: lunar elevation is relative to a 1737.4 km sphere, not to a sea level, so for the Moon this gate
should use `mask_fraction` instead. The solar gates `sun_elev_max_deg >= 10` and `irradiance >= 2.5` remove every
lunar cell poleward of about 81.5 deg by geometry (R3).

## 8. Variables that remain without data

- `slope_300m_deg`, `rough_300m_m`: not written for either body (no keyless global product at 300 m).
- Moon `rain_mm_day`, `wind_max_ms`: not applicable, empty in every cell. Moon `permafrost_class`: the MODELLED label
  'ninguno' in every cell, not empty (corrected 2026-11-15 after the statistical audit, docs/stats_audit/1_datos_rejilla_nombres.md 1.6.2).
- Moon `rock_abundance_frac`: empty poleward of 60 deg (21,608 cells); the 128 px/deg product (80S-80N, 1.9 GB)
  was not used.
- Earth `temp_k`, `lst_diurnal_amp_k`, `lst_diurnal_amp_max_k`: empty for Antarctica (the LST layers stop at 62 S),
  about 6,760 land cells.
- Earth `permafrost_class`: empty on 13,013 land cells: south of about 18-25 N outside Antarctica (Andes, East
  Africa and other tropical mountain permafrost are missing, not "ninguno"), on Greenland and other ice sheets,
  and on the Antarctic ice sheet (only ice-free outcrops are mapped).
- Earth `wind_max_ms`: no keyless gust or daily-maximum product; the column holds the windiest-month mean.
- Earth irradiance from CERES and precipitation from GPM IMERG: need an Earthdata Login, not used.

## 9. Limits a user must know

- **A cell is large.** Earth cells are about 111 x 111 cos(lat) km; lunar cells 30.3 x 30.3 cos(lat) km. A value is
  an average over that area: the Everest cell's mean elevation is 2,563 m, the Dead Sea cell 473 m, the Mauna Kea
  cell 1,345 m. Near the lunar poles a cell is a 30 km by 0.26-2.6 km strip that averages lit rims with shadowed
  floors: the best-lit points (about 90 % of the time) and permanently shadowed floors cannot appear.
- **Surface vs air temperature.** Earth `temp_k` and `lst_diurnal_amp_k` are clear-sky land *surface*
  temperatures at two overpass times (they understate the true daily range); Earth `tmin_c` is *air* temperature
  at 2 m; lunar temperatures are *surface* bolometric temperatures. Comparing Earth `tmin_c` with lunar `tmin_c`
  compares air with surface.
- **Baselines.** Slopes use a 3.7-3.8 km baseline, roughness a 1.85-1.90 km lag on both bodies; 300 m values would
  be steeper (slope) and smaller (roughness). Use `slope_iso_deg` poleward of 85 deg.
- **Modelled Earth climate.** WorldClim is interpolated: at Dome C `tmin_c` is -49 C against about -70 C measured;
  at Greenland Summit precipitation is about 4 times the measured value. Its licence is non-commercial.
- **Classifications are not measurements of the property.** `rock_or_bare_frac` (Earth) is a land-cover share;
  ESA CCI maps many deserts as shrubland (Death Valley 0.05, Hanksville 0.21, Tabernas 0.15) and the McMurdo Dry
  Valleys cell as ice (0.0). `thermal_inertia_class` is an assumed mapping (Earth) or a blanket assumption
  "regolito" (Moon); "roca" is almost absent on Earth (2 cells).
- **Elevation references differ**: Earth above the EGM2008 geoid, Moon above a 1737.4 km sphere.
- **Earth latitude is geodetic** (section 2), up to 0.19 deg from planetocentric.
- **Lunar irradiance** is for a horizontal surface, per 24-hour Earth day, at the top of a non-existent atmosphere;
  Earth irradiance is MODELLED surface radiation after clouds (WorldClim 2.1 srad, an interpolated climatology;
  corrected 2026-11-15 after the statistical audit, 1.6.3: it was called measured-climatology here). A vertical tracking panel at a lunar
  pole would receive about 32.7 kWh/m2 per lit day.
- **Small islands and coasts**: a few cells hold one or two land pixels and odd means (for example -2,570 m at
  17.5 S, 177.5 W). Filter with `mask_fraction >= 0.3` or the `n_*` pixel counts.

## Supplementary table: ISCCP clear-sky fraction (2026-11-15)

`tierra luna/real_data/supplement/earth_cloud_isccp_1deg.csv` (64,800 Earth cells, key `cell_id` = `E<id>`; columns `cloud_frac_isccp`, `clear_frac_isccp`, `n_months_isccp`), written by `tierra luna/research/r2_build_cloud.py`. Provenance beside it (`provenance_earth_cloud_isccp.csv`): ISCCP H-series Basic HGM (gridded monthly mean) v01r00, variable `cldamt`, NOAA NCEI Climate Data Record, 60 monthly files 2012-01 to 2016-12, native 1-degree equal-angle grid identical to ours; per cell the mean of the monthly means, kept with at least 48 valid months (22 cells empty); clear = 1 - cloud; level DERIVED; licence "No constraints on data access or use"; cite Rossow and Schiffer 1999, BAMS 80:2261-2287, and the NCEI ISCCP-H CDR. Caveats: cloud detection least reliable over snow, ice and polar night; coastal cells mix land and ocean clouds; cloud amount is not irradiance. The engine joins it by cell id at build (`engine/datasets.json` `supplements`, `engine/dataset.py` `load_supplements`) without rebuilding the big tables; only `clear_frac_isccp` is read (Solar panels suitability, weight 0.35).
