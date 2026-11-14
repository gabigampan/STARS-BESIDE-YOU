# A2 - Where every number comes from, and data quality

Scope: `tierra luna/` at branch `final-integration` (`d4a11e4`, identical to main), plus `mission_scoring.py/.json` from the zip. Repo files are cited as `file:line` (paths are relative to `/home/user/stars-beside-you/tierra luna/`). Every command ran in the scratch copy `.../stars/run-A2`. Check scripts are in `.../stars/a2scripts/` (`npzcheck.py`, `moon2.py`, `moon3.py`, `geo.py`, `prof.py`, `h.py`, `dict.py`). The per-variable table is in `A2_data_dictionary.csv`: 65 rows, one per variable and body, plus downstream columns.

Not available in this session: the PR #1 zip ("files 2.zip") and the team's local zip said to hold `rover_preset.py` v3 and `rover_integration.py`. Nothing below describes their content.

## 0. Baseline and how the committed outputs were made

| Check | Command | Result |
|---|---|---|
| new filter selftest | `python mission_scoring.py selftest` | `selftest OK (5 comprobaciones)`, confirmed |
| rover selftest | `python rover_preset.py --selftest` | `11/11 checks passed`, confirmed |
| tests | `python -m pytest -q tests` | `15 passed`, confirmed |
| committed `output_py/` = which run? | `python main.py --pds --out-dir out_pds`, then compared with pandas (`../cmp_a2.py`) | earth, moon and harmonized CSVs, audit CSV and `optimal_mission_zones.csv` have **identical values**. `analog_ranking.csv` has the same 100 cells and the same values; only the order of 13 tied rows differs (`h.py` check). |
| default run | `python main.py --out-dir out_default` | Earth CSV is identical to the committed one. The Moon is entirely different: it is the synthetic generator. |

**The committed outputs come from `python main.py --pds`.** Earth was built without `--use-gee`.

## 1. Data lineage (what actually runs)

```
main.py:133-141  --pds -> lola_dem = data/cache/ldem_4.img (config.py:23-27); source labels set from CLI flags only
 MOON  extract_lunar_data -> extract_lunar_from_files (lunar_extractor.py:61-84)
       if moon_global_pds.npz exists: return its 7 arrays (zoom only if the shape differs). ldem_4.img is NOT read.
       else (lines 86-101): ldem_4 elevation + formula temp/rock/sar (_global_diviner_temp_and_rock, lines 25-48) = MODELLED
       no --pds: synthetic crater field, seed 42 (lines 168-225) with injected artefacts
 EARTH extract_earth_data (earth_extractor.py:257-273) -> _build_global_earth_grid (130-158)
       if earth_global_real.npz exists: return its 7 arrays. The seed-101 Gaussian model (160-254) is NOT run.
       --use-gee: GEE first (84-119); falls back silently on any exception
 CLEAN clean_planetary_dataset (harmonizer_cleaner.py:28-131): sentinels, config ranges, IQR on sar only (line 84), nearest-neighbour fill
 TABLE dataset_to_dataframe (harmonizer_cleaner.py:188-315): coordinates + 12 formula columns
 WEB   export_web_bundle (analog_finder.py:575-691): land-only (elev>0) ranking, old mission gates, scores, JSON
 earth_mission_filtered.csv: written by `mission_filters.py apply` (mission_filters.py:233-261), not by main.py
```

## 2. Hypotheses checked

### (a) "Earth comes by default from a local synthetic model (global_model, seed 101); GEE only with --use-gee": PARTLY REFUTED

- GEE runs only with `--use-gee` (main.py:159; earth_extractor.py:263-266): **confirmed**.
- The seed-101 model is **not** what runs by default. `earth_extractor.py:137-158` loads `data/cache/earth_global_real.npz` whenever the file exists, and the file is committed. Proof: the default run's Earth CSV has the same values as the npz (audit min/mean/max match the npz arrays exactly: elevation -250 / 224.6803 / 5274.3125). The seed-101 code is reached only if the npz is deleted.
- The label is wrong in the other direction: every Earth row says `source = global_model` (main.py:141), but the values come from a file named `..._real`.
- If `--use-gee` worked, it would not fetch the globe. The region is a 90 km square around (0 N, 0 E): `half_width_m = 180*500/2 = 45 km` around `earth_center_lat/lon = 0,0` (earth_extractor.py:11-13; config.py:79-80). That is open ocean, and `_resize_2d` would stretch it onto the 90 x 180 globe (lines 111-112). `gee_earth_grid_export.js:2-4` exports a 30 km buffer near Valencia, not a global grid.
- With a grid other than 90 x 180, the npz branch injects fake artefacts into the loaded data (earth_extractor.py:154-157). The cleaner then "scale-corrects" the 14850 into 297 K (harmonizer_cleaner.py:64-68), turning an artefact into a plausible temperature. This does not occur at the default 90 x 180.

**`earth_global_real.npz`** (149,897 bytes, committed in `ca72d0b` "Add files via upload" by gabigampan, 2026-11-14; no script in the repo or the zip creates it, checked with grep):

| array | shape | min | max | mean | ocean cells (10,273) |
|---|---|---|---|---|---|
| elevation_m | 90x180 f32 | -250 | 5274.31 | 224.68 | constant -250 |
| elevation_rel_m | " | -1045.72 | 4226.89 | -634.14 | constant -1000 (land = elev - 1047.422) |
| slope_deg | " | 0.01 | 37.17 | 1.57 | constant 0.01 |
| roughness_m | " | 0.1 | 1969.87 | 71.59 | constant 0.1 |
| temp_k | " | 217.36 | 327.52 | 280.25 | constant 285 |
| rock_or_bare_frac | " | 0 | 0.98 | 0.153 | constant 0 |
| sar_sigma0_db | " | -24 | 0.585 | -19.98 | constant -24 |
| land_mask | bool | 5,927 True (36.6 %) | | | |

Is it real data? **Not determined, but the land pattern matches real geography** (`geo.py`): Tibet (33 N 86 E) is 5042 m, Amazon 47 m, Sahara bare fraction 0.87, Atlantic and Pacific are ocean, Greenland is 2848 m and the Antarctic plateau 2545 m. Of the 3,272 cells holding at least one GeoNames place (the `reverse_geocoder` cities1000 list), 2,772 are land in the npz. It is not the seed-101 model. The product, date, aggregation and author are not documented anywhere. Polar elevations exist, so it is not SRTM alone (SRTM is cited at README.md:39). The web page claims "NOAA ETOPO1/SRTM30 + NCEP Global" (web/index.html:372), and nothing backs that claim. Earth `sar_sigma0_db` on land fits `-18.29 + 7.97*rock + 0.452*slope` with R² = 0.9905 (`moon3.py`), which is behaviour expected of a formula, not of Sentinel-1. `slope_deg` cannot be reproduced from its elevation with the repo formula (corr 0.60). The default run uses this file.

**`moon_global_pds.npz`** (382,852 bytes, same commit, no generator in the repo). It holds 7 arrays, 90x180 f32, no NaN. Tests (`npzcheck.py`, `moon2.py`, `moon3.py`):

| array | finding | level |
|---|---|---|
| elevation_m | exactly the 8x8 block mean of `ldem_4.img` (LOLA GDR, 4 ppd, 720x1440, `LRO-L-LOLA-4-GDR-V1.0`), rolled to -180..180: max abs diff 0.0 | MEASURED |
| elevation_rel_m | elevation_m - global mean, exact | DERIVED |
| roughness_m | standard deviation of the 64 ldem_4 pixels (7.58 km each) in each 2 deg cell (max diff 2e-4). This is not the "local 3x3 std" written on the label (harmonizer_cleaner.py:166) | DERIVED |
| slope_deg | method not determined: corr 0.31 with the repo formula, 0.63 with the mean 4-ppd gradient. The web page says "LOLA LDSM_16" (web/index.html:619), which was not downloaded | NOT DETERMINED |
| temp_k | 43.45-110.43 K. Strongly latitude-driven (std within a latitude row 2.28 K, overall 11.18 K). The Tycho cell is 109.8 K against a row mean of 92.8 K, which looks like real Diviner night-time data. But the cited products `dgdr_st_clc_cyl_0030_032` and `dgdr_st_avg_cyl_032` cover only 60 S-60 N (labels: `MAXIMUM_LATITUDE = 60`, `MINIMUM_LATITUDE = -60`), and the npz has values up to +-89 deg. Source not determined | NOT DETERMINED |
| rock_or_bare_frac | 0.0015-0.0463. The Tycho cell is the global maximum (consistent with Diviner rock abundance), but the cited RA product also covers only +-60 deg and the npz has values poleward | NOT DETERMINED |
| sar_sigma0_db | **= -19.2 + 45*rock + 0.22*slope exactly** (least-squares residual 2e-6). This formula appears nowhere in the code | MODELLED |

**Cached PDS files** (`data/cache/`, from the labels and `pds_reader.py:291-304`; rows map to latitude as `lat = MAXIMUM_LATITUDE - (row+0.5)/ppd`):

| file | product | coverage | used by the committed run? |
|---|---|---|---|
| `ldem_4.img` + `.lbl` (2,073,600 B, full) | LOLA LDEM_4, 4 ppd, height = DN*0.5 m above 1737.4 km | global | no: bypassed by the npz (lunar_extractor.py:66-84). It matches the npz elevation exactly |
| `ldac_4.lbl` (label only) | LOLA LDAC_4 data-count map | - | never referenced in code |
| `ldem_64.img.8894cdd5.rows_8466_8596.bin` (5,990,400 B = 130 rows x 23,040 x 2) | LOLA LDEM_64, 64 ppd | rows 8466-8595, lat -42.28 to -44.30, all 360 deg of longitude (Tycho band) | no: only with `--pds --local-window` (main.py:136-139) |
| `dgdr_ra_avg_cyl_032_img.img...rows_3272_3339.bin` (1,543,680 B = 67 rows x 11,520 x 2) | Diviner rock abundance, 32 ppd, DN*0.001 | rows 3272-3338, lat -42.27 to -44.34, all longitudes | no (local window only) |
| `dgdr_st_clc_cyl_0030_032_img...rows_3272_3339.bin` | Diviner rock-free regolith temperature, 00:30 local time, DN*0.02 K | same band | no (local window only) |
| `dgdr_st_avg_cyl_032_img...rows_3272_3339.bin` | Diviner regolith temperature deviation from the global average | same band | no (local window gap-fill only, lunar_extractor.py:110-122) |

Default run without `--pds`: the Moon is the synthetic generator (seed 42, lunar_extractor.py:168-225), labelled `synthetic`. The committed outputs are the `--pds` variant.

### (b) "90 x 180 grid of ~2 deg cells, while resolution says 500 m; 16,200 Earth cells": CONFIRMED

- grid_shape (90,180) (config.py:75; main.py:22-33); lat = 90-(row+0.5)*2 and lon = -180+(col+0.5)*2 (harmonizer_cleaner.py:202-203). There are 16,200 Earth rows and 16,200 Moon rows (32,400 in the harmonized CSV).
- `resolution_m` = 500 on every row (harmonizer_cleaner.py:225). The real cell height is 2 deg = 222.4 km on Earth and 60.6 km on the Moon (2·π·R/180).
- `x_m` = (col-89.5)*500 and `y_m` = (44.5-row)*500 (lines 198-199): range +-44,750 m and +-22,250 m. They describe a 90 x 45 km sheet, not the globe.
- Both GeoTIFFs (`rasterio`): EPSG:3857, transform origin (-45000, 22500), 500 m pixels, bounds -45000..45000 x -22500..22500 m, which is **lon +-0.404 deg, lat +-0.202 deg at 0 N 0 E**. The tag `RESOLUTION_METERS = 500.0` (harmonizer_cleaner.py:144-177). A global Earth grid and a lunar grid are both georeferenced as a 90 km patch in the Gulf of Guinea. The README admits EPSG:3857 is not lunar (README.md:79) but still claims 500 m/px (README.md:71).
- `analog_web_data.json` grid says `resolution_m: 500.0`, dlat 4.0, dlon 4.0 (stride 2).

### (c) Formula columns cite NASA POWER / MODIS, and nothing was downloaded: CONFIRMED

No downloader for POWER, NCEP, MODIS or IPA exists. The only network code is `pds_reader.py` (PDS) and the GEE path. All 12 columns come from `dataset_to_dataframe`. Here `cos_lat = clip(cos(lat), 0.05, 1)` (line 249), `bare` is rock_or_bare_frac with NaN replaced by 0.1, and `temp` is temp_k with NaN replaced by 250 (lines 235-236).

| column | formula (harmonizer_cleaner.py) | claimed source |
|---|---|---|
| irradiance_kwh_m2_day | `clip((1.6+4.8*cos_lat^0.75)*(0.78+0.32*bare+0.04*clip(max(elev,0)/3000,0,1.5)), 0.8, 8.2)` :250-255. The same formula is used for the Moon | "NASA POWER / NOAA NCEP" (mission_filters.json:59) |
| sun_elev_max_deg | `clip(90-|lat| + (1.54 Moon / 11.7 Earth), 1.5, 90)` :256. Earth uses 11.7, but the obliquity is 23.44 deg (standard value, not from the repo): at 51 N the code gives 50.7 against 62.4 | "solar array elevation envelope" (:64) |
| sun_low_frac_0_5deg | `clip(0.028+0.26*(|lat|/90)^2.2, 0.025, 0.35)` :257, identical for both bodies | "Artemis low-horizon regime" (:69) |
| lst_diurnal_amp_k | Moon `clip(180*cos_lat^0.35, 25, 210)` :260; Earth land `clip(8+22*bare+0.0022*max(elev,0), 6, 48)`, ocean 2.5 :262-266 | "MODIS/NCEP" (:94) |
| thermal_inertia_class | bare >= 0.22 arena, >= 0.42 regolito, >= 0.55 and (rough >= 110 or slope >= 4) roca; Earth: hielo if elev > 0 and T < 261, agua if elev <= 0 :268-274 | "Diviner Bandfield et al. (2011)" (:103) |
| permafrost_class | Earth land: T <= 274.15 (or elev >= 3400 and T <= 278) esporadico, <= 270.15 discontinuo, <= 265.15 continuo; Moon: abs(lat) >= 75 and T <= 75 continuo, abs(lat) >= 65 and 75 < T <= 90 discontinuo :276-284 | "IPA Brown et al." (:129) |
| rain_mm_day | Earth `clip(4.2*clip(1-bare,0,1)^1.8*clip(cos_lat+0.15,0.2,1.1), 0.01, 12)` :290-294; Moon 0 | none in code |
| wind_max_ms | Earth `clip(4.5+0.0012*max(elev,0)+3.8*(|lat|/90)^1.4, 2.5, 15.5)` :295-299; Moon 0 | none |
| tmin_c | `(temp-273.15) - 0.35*lst_diurnal_amp_k` :300 | none (author notes call it "estimaciones del modelo") |
| mask_fraction | Earth `elev>0 ? clip(0.35+0.65*min(elev/150,1), 0.35, 1) : 0`; Moon 1 :241-247 | "celda con dato suficiente" (mission_scoring.json:7) |
| slope_300m_deg, rough_300m_m | copies of slope_deg and roughness_m (:303-304), verified equal | "300 m" in the name; VIPER limit cited for the gate |

The same formulas are duplicated in analog_finder.py:479-492 for when rain_mm_day is missing (not triggered: the column exists).

### (d) Lunar radar column is synthetic: CONFIRMED

In the committed run, Moon `sar_sigma0_db` is exactly `-19.2 + 45*rock_or_bare_frac + 0.22*slope_deg` (npz arrays, residual 2e-6). The fallback branch would also be a formula (`-19 + 14.5*rock + 0.14*slope`, lunar_extractor.py:47), and so would the no-`--pds` branch (`-19.5+14*rock+0.12*slope+noise`, :201-203). The non-global PDS branch sets it to NaN (:131). No lunar radar product is read anywhere. Earth sar also behaves as a formula (R² 0.9905, see (a)).

### (e) Earth thermal amplitude at most 39 K; Moon 63-180 K: CONFIRMED

Earth land is 8.89-38.75 K and ocean is a constant 2.5 K (formula cap 48, never reached). Moon is 63.08-179.99 K. The Moon value is a function of latitude only: the minimum 63.08 = 180·0.05^0.35 at the clipped cos(89 deg), and the maximum is at the equator. Effect: in the old system, the thermal gate `lst_diurnal_amp_k >= 16` (mission_filters.json:91-95) and the new one `>= 15` (mission_scoring.json:58) select on a quantity that is itself `8+22*bare+0.0022*elev`. That gate is in practice a bare-fraction and elevation gate.

## 3. Data quality (counts on the committed files, `prof.py`, `h.py`)

| check | earth CSV | moon CSV | harmonized | filtered | ranking | zones | web JSON |
|---|---|---|---|---|---|---|---|
| rows | 16,200 | 16,200 | 32,400 (= moon+earth; amp/tmin differ by <= 4e-6 from float rounding) | 16,200 | 100 | 30 (6 x 5) | 1,477 earth (land, stride 2), 4,050 moon |
| lat/lon out of range | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| lat/lon swapped | 0 (abs(lat) <= 89, abs(lon) <= 179; geography checks in 2a; Moon elevation matches only with the correct roll: unrolled corr -0.26) | | | | | | |
| lon convention | -180..180 everywhere. PDS sources are 0..360 and are converted with `np.roll(..., samples//2)` (pds_reader.py:326) | | | | | | |
| duplicate cells (row,col) | 0 | 0 | 0 per body | 0 | 0 | - | 0 |
| NaN / missing | 0 in every CSV and in the JSON | | | | | | |
| imputed by the cleaner | Earth 0; Moon sar 17 cells (IQR, audit CSV) | | | | | | |
| negative irradiance, slope > 90, fraction outside [0,1], T <= 0 K, tmin < -273.15 | 0 each | 0 each | | | | | |
| constant columns | body, resolution_m, source | body, resolution_m, source, mask_fraction (1), thermal_inertia_class ('suelo' x 16,200), rain_mm_day (0), wind_max_ms (0) | | | | | |
| exact functions of latitude | sun_elev_max_deg, sun_low_frac_0_5deg | mask_fraction, sun_elev_max_deg, sun_low_frac_0_5deg, lst_diurnal_amp_k, TI class, rain, wind | | | | | |
| ocean cells | 10,273 / 16,200 (63.4 %), all 7 bands at constant fill; there irradiance, rain and wind vary with latitude only | - | | ocean fails mask_min (mask_fraction 0) | excluded (elev > 0 filter, analog_finder.py:430) | | excluded |

Unit and label problems:
- `resolution_m`, `x_m`, `y_m` and the GeoTIFF transform claim 500 m; the cells are 222 km (Earth) and 61 km (Moon). See 2b.
- `slope_300m_deg` and `rough_300m_m` claim a 300 m baseline; they are 2-deg cell values. R1 (`docs/integration/R1_viper_rover_spec_sources.md:112`) notes that no official LOLA product uses a 300 m baseline.
- `roughness_m` is labelled "local 3x3 std" (harmonizer_cleaner.py:166); on the Moon it is the standard deviation within a 2-deg cell of 7.58 km pixels.
- No kelvin/Celsius mix-up in the values: temp_k is in K (217-328 Earth, 43-110 Moon) and tmin_c in degC. But Moon `tmin_c` (-251.8 to -219.8 degC) subtracts up to 63 K (0.35 x amp) from a temp_k described as night-time Diviner (README.md:7). It is not a minimum computed from data.
- Moon temp_k is a night-time value (43-110 K), while Earth temp_k is described as a MODIS daytime LST median (README.md:43; earth_extractor.py:41). The similarity z-scores compare them only after per-body normalisation (analog_finder.py:143-181), so absolute units never meet. The permafrost and TI thresholds are absolute, though.
- `irradiance_kwh_m2_day` applies an Earth-style atmospheric formula to the airless Moon.
- Moon `thermal_inertia_class` is all 'suelo' because Moon rock never reaches 0.22.

"source" says real where values are modelled:
- All 16,200 Moon rows say `real_PDS` (main.py:140, set by the `--pds` flag). In those rows the sar column and 11 formula columns are modelled, and temp, rock and slope come from an undocumented array.
- Earth rows say `global_model` although the bands are loaded from `earth_global_real.npz`.
- `analog_web_data.json` and the web page badge say "Real LRO LOLA + Diviner vs. NOAA ETOPO1/SRTM30 + NCEP Global" (web/index.html:372). Nothing in the code reads ETOPO1, SRTM30 or NCEP.

README discrepancies with the code:
- IQR is applied to sar only (harmonizer_cleaner.py:84), not to temp and rock as README.md:52 says.
- Slope, roughness and relative elevation are recomputed only in local-window mode (harmonizer_cleaner.py:120-128), not always as README.md:53 says.

Downstream extras:
- `earth_mission_filtered.csv` lacks rain_mm_day, wind_max_ms and tmin_c. It was made by the `mission_filters.py apply` CLI from an older Earth CSV. Its shared columns equal the current CSV exactly. Pass counts: rover 5,297, solar 5,198, thermal 3,337, ice 3,023, all 2,114 (equal to `mission_stats` in the JSON).
- `workable_rover`: 581 of 5,927 land cells meet rain <= 1, wind <= 12 and tmin >= -10. All 100 ranked cells are 0. It is exported only; neither system uses it in a pass or score. `mission_scoring.json:27` keeps `workable_days`, but `mission_scoring.py` never reads it (grep "workable" finds nothing).
- `earth_region` is the nearest of 48 hard-coded landmarks within 18 deg (analog_finder.py:129-140). For example, zone (67 N, 175 E) is labelled "Kamchatka Volcanic Belt".
- New system (`mission_scoring.py run` on the harmonized CSV, keeps EARTH rows only, mission_scoring.py:266-267): rover 5,297, solar 5,192, thermal 2,613, ice 3,023, all four 1,728; solar and thermal 1,986. This matches the author's notes.

## 4. Share of variables by level (19 physical variables per body: 7 bands + 12 table columns; metadata excluded)

| level | EARTH (committed / default run) | MOON (committed `--pds` run) |
|---|---|---|
| MEASURED (verified against a product in the repo) | 0 (0 %) | 1: elevation_m (5 %) |
| DERIVED (stated formula on a measured value) | 1: elevation_rel_m (5 %), and its ocean value is a fixed -1000 | 4: elevation_rel_m, roughness_m, rough_300m_m (copy), sun_elev_max_deg (21 %) |
| MODELLED | 11: sar (probable), mask_fraction, irradiance, sun_elev_max, sun_low_frac, amp, TI class, permafrost, rain, wind, tmin_c (58 %) | 10: sar, mask_fraction, irradiance, sun_low_frac, amp, TI class, permafrost, rain (0), wind (0), tmin_c (53 %) |
| NOT DETERMINED (undocumented cached array) | 7: elevation, slope, roughness, temp, rock, slope_300m, rough_300m (37 %). The land pattern matches real Earth; the ocean (63 % of cells) is constant fill, which is MODELLED | 4: slope_deg, slope_300m_deg, temp_k, rock_or_bare_frac (21 %) |

Every gate and soft criterion of the old and new systems reads only MODELLED or NOT DETERMINED columns. The one exception is `elevation_m` in the new common gate (elev >= 1), whose land values are NOT DETERMINED. If both npz files were deleted, Earth would become 100 % MODELLED (seed-101 model). The Moon would keep a MEASURED elevation (ldem_4) and have MODELLED temp, rock and sar (lunar_extractor.py:25-48).
