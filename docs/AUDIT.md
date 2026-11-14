# Phase 0 audit: what the pipeline in `tierra luna/` really does

Stars Beside You, NASA Space Apps Challenge 2026, challenge "Earth analogs for Permanent Moon Base and Mars" (Earth and Moon only in this pipeline). Written 2026-11-14.

**What was audited, and how:**

- **State audited.** Branch `final-integration`, commit 618bc45. That commit is `main` plus `mission_scoring.py` and `mission_scoring.json` copied unchanged from the root zip, plus a `.gitignore`.
- **No repository file was changed.** Every run used scratch copies.
- **Uncommitted changes that appeared during the writing.** These were not made by this audit and are not audited: `tierra luna/analog_finder.py` (the x0.35 penalty replaced by NaN), `tierra luna/mission_scoring.json` (`on_missing_gate` "keep" changed to "drop"), and a new folder `tierra luna/engine/`.

**Companion documents:**

- [DATA_DICTIONARY.md](DATA_DICTIONARY.md) and [data_dictionary.csv](data_dictionary.csv): every variable, its level, observed range and use.
- [FILTERS.md](FILTERS.md): both filter systems copied exactly, the differences between them, the reproduced counts, and the verdict of official sources on every threshold.

**Evidence:**

- [audit_evidence/](audit_evidence/) holds the four auditor reports (A1 inventory and tests, A2 data, A3 filters and scoring, A4 points), A2's per-variable table and `A4_lunar_points.csv`.
- [sources/](sources/) holds the official-source notes R1 (VIPER), R2 (lunar reference), R3 (thresholds) and R4 (front end and data access). Every fact in them carries a URL and a quote.
- A4's Earth point table (`A4_earth_points.csv`) is not copied because of its size (1,607 rows, 600 KB). It lists every Earth point that the outputs name or rank (the 30 optimal zones, the top-100 ranking and the 1,477 web cells), with country (Natural Earth 1:110m), first-level region (GeoNames), land fraction, distance to the label's anchor and a label check. It lives in the session scratchpad (`stars/parts/A4_earth_points.csv`).
- The auditors' scripts are under the session scratchpad (`stars/a2scripts`, `a3scripts`, `a4scripts`, `docscripts`) and are referenced by name. Those paths do not exist outside this session.

**Not available in this session, so pending:**

- the comparison with the zip of pull request #1 ("files 2.zip");
- the comparison with the team's local zip said to contain `rover_preset.py` version 3 and `rover_integration.py`.

Nothing in these documents describes the content of either zip.

---

## Summary for the team lead

1. **No Earth number is measured, and the default Earth data is not the seed-101 model either.** Every Earth band is loaded from `data/cache/earth_global_real.npz` (`earth_extractor.py:134-158`). No code in the repository produces that file. Its land pattern matches real geography, but its product, date and processing are undocumented. Every Earth row is still labelled `source = global_model` (`main.py:141`), and the web badge says "NOAA ETOPO1/SRTM30 + NCEP Global" (`web/index.html:372`). The twelve mission columns, including irradiance, sun angles, thermal amplitude, thermal-inertia class, permafrost and `tmin_c`, are closed-form formulas (`harmonizer_cleaner.py:241-313`). **Effect:** the product cannot claim that its Earth results rest on NASA or other measured data. Every pass count and score is a model output until the npz origin is documented and the formula columns are replaced or labelled.

2. **The grid is 2 degrees, not 500 m.** It is 90 x 180 cells, 222 km north-south on Earth and 61 km on the Moon. Yet `resolution_m`, `x_m`, `y_m`, the README and both GeoTIFFs say 500 m. The GeoTIFFs are georeferenced as a 90 km x 45 km patch at 0 N, 0 E. The `slope_300m_deg` and `rough_300m_m` columns are copies of the 2-degree values (`harmonizer_cleaner.py:303-304`). **Effect:** the rover gate is a rover-scale VIPER figure (15 deg, which NASA does publish) applied to 2-degree terrain. A test site of a few km can never be represented. 6 of the 44 benchmark analog sites (Teide, both Lanzarote sites, Mauna Kea, Kilauea, HI-SEAS) fall in cells coded as ocean and can never appear.

3. **The solar mission selects the opposite of the lit-ridge concept, in both systems.**
   - The live (old) system scores Earth cells by their similarity to a lunar profile labelled "South Pole PSR & Shackleton Rim". That profile is simply every cell south of -75 deg, and the system rewards a higher grazing-sun fraction. So it picks Earth's coldest cells (Antarctica, Verkhoyansk).
   - The new system's gates (`sun_elev_max_deg >= 10`, `sun_low_frac_0_5deg <= 0.25`, `irradiance_kwh_m2_day >= 2.5`) would remove every lunar cell poleward of about 77 deg. That is exactly where NASA's sources place the near-continuously lit rims.
   - **Effect:** the solar mission cannot be presented as a south-pole power analog. No illumination variable exists in the data.

4. **The thermal comparison is not physical.** Similarity uses z-scores normalised separately on each body (`analog_finder.py:143-181`). Earth land at 217-328 K therefore scores up to 100 % "similar" to a Moon at 43-110 K. The lunar diurnal amplitude is a latitude formula giving 63-180 K, while Diviner data show 250-300 K at low and mid latitudes (R2 section 3). **Effect:** the thermal similarity percentages and every lunar thermal value must not be presented as comparisons with real lunar conditions.

5. **Two filter systems exist, and only the old one is live.**
   - `analog_finder.py` and the web page use `mission_filters.json`. `mission_scoring.py` is imported by nothing, tested by nothing, and its CLI scores only EARTH rows.
   - The author's counts reproduce exactly (solar 5,192, thermal 2,613, both 1,986). The web page shows the old counts instead (solar 5,198, thermal 3,337).
   - `mission_scoring.json` already has a provisional rover block (contrary to the brief) and sets `on_missing_gate` to "keep", contrary to the author's own note.
   - **Effect:** until the integration is done, the counts in the author's note are not what users see.

6. **Scoring faults change the rankings.**
   - A gate-failed cell keeps 35 % of its score in the CSV and JSON outputs, while the browser sets it to 0.
   - The domain mapping gives `temp_k` more weight than slope in the rover mission (0.1825 against 0.1725).
   - The new rover "soft" score reverses the old rover formula instead of approximating it.
   - **Effect:** the outputs disagree with each other, and the "light" weight slider cannot express light.

7. **Place names in the outputs are not locations.**
   - Earth region names are the nearest of 48 hard-coded anchors, up to about 2,000 km away. In the top 100, 4 cells are in another country than their label and 15 are mostly sea or ice shelf.
   - Two of the seven lunar zone labels describe places that their masks do not select: "Mare Tranquillitatis" and "Farside Highlands (> +2000 m)".
   - **Effect:** names on the map and in the CSVs must be replaced by computed country and region, or shown as "nearest landmark".

8. **Source strings overstate their evidence.**
   - The JSON files cite "NASA VIPER operational slope limit", "NASA POWER / NOAA NCEP", "MODIS/NCEP", "Bandfield et al." and "IPA Brown et al." for values that are formulas, or that `rover_preset.py` marks ESTIMADO or ILUSTRATIVO.
   - The README claims 12 tests (there are 15), IQR filtering on three bands (only SAR is filtered) and a 500 m grid.
   - **Effect:** every source text and README claim must be corrected before submission, or the submission misstates its data.

---

## (a) Inventory

### What is in the repository (tracked at 618bc45)

| Path | What it is |
|---|---|
| `STARS-BESIDE-YOU-main (2).zip` (14,031,467 B) | a copy of the whole tree (see the comparison below) |
| `Instruciones filtros solar y temp` (no extension) | the author's note for the new filter system (Spanish) |
| `.gitignore` | added in 618bc45 |
| `tierra luna/*.py` | `main.py`, `config.py`, `lunar_extractor.py`, `earth_extractor.py`, `pds_reader.py`, `harmonizer_cleaner.py`, `analog_finder.py`, `mission_filters.py`, `rover_preset.py`, `mission_scoring.py` (3,304 lines in all) |
| `tierra luna/*.json` | `mission_filters.json` (old system), `mission_scoring.json` (new system) |
| `tierra luna/data/cache/` | `ldem_4.img`/`.lbl` (full LOLA 4 ppd), `ldac_4.lbl` (label only), one 130-row band of `ldem_64`, one 67-row band of three Diviner products, and the two npz caches `earth_global_real.npz` and `moon_global_pds.npz` |
| `tierra luna/data/presets/presets.json` | rover preset, rewritten by every run |
| `tierra luna/output_py/` | 10 generated outputs (CSV, GeoTIFF, JSON) |
| `tierra luna/web/` | `index.html` and `analog_data.js` (2.5 MB payload) |
| `tierra luna/tests/test_pipeline.py` | 14 test functions |
| `tierra luna/gee_earth_grid_export.js` | Earth Engine script for a 30 km window near Valencia |
| `tierra luna/__pycache__/`, `tests/__pycache__/` | 9 committed `.pyc` files (cpython-312) |

The working tree also holds an untracked `app/` folder with `.env.example` and `.env.local`. The latter is ignored by `.gitignore`; this audit did not read it.

### What is missing

| Missing item | Evidence | Effect |
|---|---|---|
| Producer of `earth_global_real.npz` and `moon_global_pds.npz` | no `np.savez` anywhere; only the loaders `earth_extractor.py:135` and `lunar_extractor.py:64` (A1 section 5.3) | the data behind every committed result cannot be regenerated or traced |
| `docs/AI_USE.md` | `rover_preset.py:1` "Declared in docs/AI_USE.md"; no such file | dangling declaration |
| Data README or sidecar per data file | the integration contract requires it (`/home/user/NASA/docs/plan/09b_team_inputs_and_contract.md` section 3) | sources cannot be cited |
| Tests for `mission_scoring` and for any gate count | section (b) | the new system is unverified in the suite |
| Illumination, permafrost, thermal-inertia and LST products | no downloader exists except PDS and the GEE path (A2 section 2c) | the mission columns are formulas |

### Duplicated or superfluous

| Item | Evidence | Effect |
|---|---|---|
| The root zip | identical copy of 50 tracked files (comparison below); pack size 25.93 MiB (A1 section 1.2) | removing it in a new commit does not shrink history; rewriting history is the owner's decision |
| Committed `.pyc` | 9 files, including `mission_filters.cpython-312.pyc` | machine-specific and stale |
| `web/analog_data.js` and `output_py/analog_web_data.json` | the same payload, verified equal (A1) | double maintenance |
| `output_py/earth_mission_filtered.csv` | not written by `main.py`; lacks `rain_mm_day`, `wind_max_ms` and `tmin_c`, so it was made from an older Earth CSV (A1 section 5.2) | stale output |
| The same formulas in two places | `analog_finder.py:479-492` repeats `harmonizer_cleaner.py:290-300`; `web/index.html:669-691` repeats `map_domain_weights_to_features` | any fix must be made twice |
| CRLF line endings in the committed CSVs | `git ls-files --eol` gives `i/crlf`; regenerated files are LF (A1) | byte diffs appear even when the content is equal |

### Root zip against `tierra luna/`, file by file

The tracked files were compared by sha256 with the zip entries (script `docscripts/zipcmp.py`, re-run for this document at 618bc45). The zip's internal prefix is `STARS-BESIDE-YOU-main (1)/STARS-BESIDE-YOU-main/`.

| Result | Files |
|---|---|
| Identical | **all 50 files in the zip**: `Instruciones filtros solar y temp`, all 49 files of `tierra luna/` in the zip (sources, data cache, outputs, web, tests, `.pyc`), including `mission_scoring.py` and `mission_scoring.json`, which 618bc45 copied byte for byte |
| Only in the repository | `tierra luna/mission_filters.py`, `tierra luna/mission_filters.json`, `.gitignore`, and the zip itself |
| Only in the zip | none |
| Different content | none |

**The zip tree does not run as shipped.** `analog_finder.py:10` imports `mission_filters`, which the zip does not contain. In A1's copy of the zip tree, `python -c "import analog_finder"` raised `ModuleNotFoundError` and pytest failed at collection (A1 section 1.1). The author's advice to "copy the two files" works only inside the repository tree.

### How to integrate the new filter files, and what stays unconnected

The copy has already been done (618bc45), and the standalone tool works:

- `python mission_scoring.py selftest` gives "selftest OK (5 comprobaciones)";
- the `run` command reproduces the author's counts (FILTERS.md section (d)).

Do not delete `mission_filters.py` or `mission_filters.json`: `analog_finder.py:10` and `tests/test_pipeline.py:263` import the module.

Still unconnected (A1 section 2.3, A3 section 1.2):

| Gap | Evidence |
|---|---|
| Pass flags in the pipeline come from `mission_filters.apply_missions` | `analog_finder.py:505-510` |
| Mission scores come from a third formula set, unrelated to both JSON files' soft criteria | `analog_finder.py:243-323` |
| The web reads `mission_filters` from the bundle and ignores `soft`; `to_web_cfg()` exists but is never called | `web/index.html:646`; `mission_scoring.py:190-204` |
| `GATE_PROP_MAP` has no entry for `slope_deg`, `tmin_c` or `elevation_m`. Exporting the new configuration as it stands would make every cell fail solar and thermal in the browser (read from code, not run) | `web/index.html:634-643` |
| `combine_with_similarity` needs `similarity_pct`, which only `analog_finder.py` produces | `mission_scoring.py:207-211` |
| `earth_mission_filtered.csv` lacks `tmin_c`, so the new thermal mission would raise `KeyError` on it | A1 section 2.2 |
| Not in pytest, not in the README | `tests/test_pipeline.py` |

### The two pending comparisons

| Comparison | Status | What it must answer |
|---|---|---|
| Pull request #1 zip ("files 2.zip") against the repository | **pending**: the file was not available | which files differ, and whether it contains a later `mission_scoring.*` or rover files |
| Team local zip (`rover_preset.py` v3, `rover_integration.py`) against the committed `rover_preset.py` | **pending**: the file was not available | the v3 gates, weights, site list and benchmark use. The committed file has no version string, no reference to `rover_integration.py` and no site coordinates (A1 section 6, A4 section 5), so it cannot be identified as v3 or as an earlier version |

---

## (b) Tests and self-tests

Each was run by A1 and A3 in scratch copies with Python 3.13.18. The committed `.pyc` files are cpython-312; 3.12 was not run.

| Command | Result |
|---|---|
| `python -m pytest tests -v -p no:cacheprovider` | **15 passed** (14 functions, one parametrised x2) in 2.44 s, offline. Side effect: rewrites `data/presets/presets.json` |
| `python mission_scoring.py selftest` | "selftest OK (5 comprobaciones)". It runs 7 asserts (lines 235-247) on an inline configuration with `on_missing_gate: "drop"`, never on the shipped JSON |
| `python rover_preset.py --selftest` | "11/11 checks passed" |
| `python mission_filters.py selftest` / `check mission_filters.json --strict` | "selftest OK" / "OK: sin problemas." |
| `python main.py` (default) | rc 0; the Moon is the synthetic generator, so it does **not** reproduce the committed outputs |
| `python main.py --pds` | rc 0; reproduces the committed outputs (only CRLF, ties in rank order and a timestamp differ) |

What each test really asserts (A1 section 3.1, read from `tests/test_pipeline.py`):

| Test (line) | Real assertion |
|---|---|
| `test_slope_flat_and_ramp` (35) | slope 0 on a flat DEM; 45 deg on a 1:1 ramp |
| `test_raw_has_all_bands_same_shape` (44) | the synthetic 60x60 local grids return 7 bands of the same shape |
| `test_raw_contains_injected_artifacts` (51) | the synthetic grids contain the injected artefacts |
| `test_clean_in_range_and_finite` [moon, earth] (56) | after cleaning, every band is finite and inside the configured range |
| `test_scale_fix_modis_dn` (65) | some Earth temperatures were rescaled; minimum > 180 K |
| `test_audit_counts_sentinels` (72) | at least 12 sentinel pixels counted on the Moon |
| `test_geotiff_7_bands_same_grid` (77) | 7 bands, 500 m pixels, the same grid on both bodies. It does **not** check that the georeference is correct |
| `test_csv_dataframe_columns_match` (93) | same columns, 3,600 rows, no NaN |
| `test_pds3_labels_parsed_correctly` (101) | the cached labels parse |
| `test_real_pds_tycho_window_and_cleaning` (118) | a 120x120 local window at Tycho from the cached rows has plausible ranges; SAR all NaN |
| `test_analog_finder_ranking_and_weights` (152) | 20 sorted rows in 0-100 %; different weights give a different similarity; web files are written |
| `test_global_moon_and_earth_coverage` (175) | the global grids reach beyond +-85 / +-175 deg; the Moon spans < -5000 and > 5000 m |
| `test_verified_real_landmarks_moon_and_earth` (194) | values at 15 fixed cells of the **npz caches** (for example Tibet > 4500 m); at least 3 zones per mission. It passes the Earth source label "real_NOAA" (line 249), a string that nothing asserts or checks against the data |
| `test_mission_filters_json_and_cli_integration` (262) | the old self-tests pass; `validate(..., strict=True)` is empty, which checks only form: non-empty sources, min <= max, complete weights summing to 1 with a `weights_note` (`mission_filters.py:122-144`) |

**What nothing tests:**

- `mission_scoring` at all.
- Any gate count or pass flag on real data.
- Any mission score value.
- The domain-to-feature mapping.
- Missing-data behaviour (the CSV test asserts there is no NaN at all).
- Which bands the IQR filter touches.
- Units beyond the "Kelvin" label.
- The cell-to-coordinate mapping and the GeoTIFF georeference.
- The longitude convention.
- The twelve formula columns.
- `read_pds_global`, the `main.py` CLI end to end, `--use-gee`, and the web page.

---

## (c) README claims against the code

From A1 section 4 (default run = `python main.py`, global 90x180 mode, `main.py:118-119`):

| # | Claim (README line) | What the code does | Verdict |
|---|---|---|---|
| 1 | Identical spatial resolution, 500 m/px by default (3, 71) | 2-deg cells (`harmonizer_cleaner.py:201-203`); `resolution_m` is just the `--res` value (225) | **False** in the default mode |
| 2 | `--pds` reads LOLA `ldem_64` and Diviner (7) | the global mode sets only `ldem_4` (`main.py:134-135`), then loads `moon_global_pds.npz` (`lunar_extractor.py:61-84`); Diviner only with `--local-window` | **False** for the global run |
| 3 | Without `--pds`, a synthetic generator with artefacts (7) | `lunar_extractor.py:168-215` | True |
| 4 | Earth uses the calibrated local model by default (8, 80) | loads `earth_global_real.npz` first (`earth_extractor.py:134-158`); the model runs only if the file is absent and does not reproduce it (max diff 9,749 m) | **Misleading** |
| 5 | Verified over Tycho with real LOLA/Diviner (14) | the test passes on cached rows | True (local window only) |
| 6 | 12 of 12 tests (16, 33) | 14 functions, 15 items | **False count** |
| 7 | 30 % maximum interpolation (28, 53) | `max_impute_frac=0.30` (`harmonizer_cleaner.py:33`) | True |
| 8 | SRTM gap-filled with ASTER (39) | GEE path only | True only with `--use-gee` |
| 9 | `elevation_rel_m` = DEM minus local mean (40) | recomputed only when not global (`harmonizer_cleaner.py:120`); in the Earth npz, `elevation_rel_m` = `elevation_m` - 1047.42 m on every land cell (a single global offset, not a local mean) and -1000 against -250 m on ocean fill cells | **False** for Earth by default |
| 10 | Slope = 2D gradient; roughness = 3x3 std (41-42) | the formula exists, but the default run uses npz values of undocumented method | **Not what runs** |
| 11 | Moon temperature from Diviner; Earth from MODIS LST (43) | local `--pds` / GEE paths only | True only for those paths |
| 12 | Moon rock from Diviner; Earth 1 - NDVI (44) | same | Partly |
| 13 | Moon SAR = radar backscatter (45) | no lunar radar product anywhere; the npz value is an exact formula | **False** |
| 14 | MODIS DN 7500-20000 x 0.02 (49) | `harmonizer_cleaner.py:64-68` | True |
| 15 | Sentinels (50) | also -3.4028235e38 | True |
| 16 | Physical ranges 20-420 K Moon, 180-360 K Earth (51) | `config.py:92,102` | True |
| 17 | 3.5 x IQR on temp, rock and SAR (52) | SAR only (`harmonizer_cleaner.py:84`) | **False** |
| 18 | Slope, roughness and relative elevation recomputed on the cleaned DEM (53) | only `if not config.global_mode` (120) | **False** by default |
| 19 | Audit report every run (55) | `main.py:167-169` | True |
| 20 | `python main.py --pds --res 500 --size 120` (61-62) | `--size` used only with `--local-window` | **Misleading** |
| 21 | GeoTIFFs EPSG:3857, 500 m/px (71, 79) | true as written; the georeference is wrong for a global grid | **Misleading** |
| 22 | CSVs hold coordinates + 7 variables (72) | plus 12 formula columns | Incomplete |
| 23 | Output list (69-75) | also `optimal_mission_zones.csv`, `analog_web_data.json`; `earth_mission_filtered.csv` not written | Incomplete |
| 24 | lat/lon are local spherical approximations (79) | exact cell centres in global mode | Partly |
| 25 | Web synced with `analog_finder.py` (17) | the payloads are equal | True |
| 26 | Structure table (22-33) | omits `mission_filters.*`, `rover_preset.py`, presets and the npz files | Incomplete |

---

## (d) The seven faults the team lead listed

The brief itself is not in the repository. The seven items below are the hypotheses handed to the auditors (A2 section 2 (a)-(e), A3 section 3 (a)-(b)), each checked against the code and data.

### 1. "Earth comes by default from a local synthetic model (seed 101); GEE only with `--use-gee`": CORRECTED

- **GEE runs only with `--use-gee`.** Confirmed (`main.py:159`; `earth_extractor.py:263-266`).
- **The default Earth data are not the seed-101 model but a cached array of undocumented origin.** `_build_global_earth_grid` returns `data/cache/earth_global_real.npz` whenever the file exists (`earth_extractor.py:134-158`), and the file is committed. It came in with commit ca72d0b ("Add files via upload"), and no script creates it. The seed-101 generator (`earth_extractor.py:160-254`) runs only if the file is deleted.
- **What the array looks like.** The land pattern matches real geography: Tibet 5,042 m, Sahara bare fraction 0.87 (A2 `geo.py`). The 10,273 ocean cells hold constant fill values. Earth SAR on land fits a linear formula with R2 0.990. The array is labelled `source = global_model`.
- **The GEE path itself is broken.** `--use-gee` would fetch a 90 km square around (0 N, 0 E), which is ocean, and stretch it over the globe (`earth_extractor.py:11-13, 111-112`). It falls back silently on any error (114-119).

### 2. "90 x 180 grid of about 2-degree cells while resolution says 500 m; 16,200 Earth cells": CONFIRMED

- **Grid.** `lat = 90-(row+0.5)*2` and `lon = -180+(col+0.5)*2` (`harmonizer_cleaner.py:202-203`), with 16,200 cells per body.
- **The 500 m labels.** `resolution_m` = 500 on every row (225), and `x_m` and `y_m` span +-44,750 m and +-22,250 m (198-199).
- **Real cell size.** 2 deg is 222.4 km on Earth and 60.6 km on the Moon (A2 section 2b).

### 3. "Formula columns cite NASA POWER / MODIS, and nothing was downloaded": CONFIRMED

- **No downloader exists** for POWER, NCEP, MODIS or IPA. The only network code is PDS (`pds_reader.py`) and the GEE path.
- **All twelve columns are formulas** (`harmonizer_cleaner.py:241-313`). FILTERS.md section (b) and DATA_DICTIONARY.md give each one.
- **Precise version of the fact:** the source strings cite products that are never read (`mission_filters.json:59, 94, 103, 129`).

### 4. "The lunar radar column is synthetic": CONFIRMED

In `moon_global_pds.npz`, which the committed run loads, Moon `sar_sigma0_db` = `-19.2 + 45*rock_or_bare_frac + 0.22*slope_deg` exactly (maximum residual 2e-6, re-run for this document; zero at float32 precision in the verification). In the committed CSV, 17 of these cells were then replaced by the IQR step (`harmonizer_cleaner.py:84`; `data_cleaning_audit_report.csv`), so the CSV matches the formula everywhere else, up to rounding. That formula appears nowhere in the code. The fallback branches are also formulas (`lunar_extractor.py:47`, `:201-203`), and the local PDS branch sets the column to NaN (`:131`). No lunar radar product is read anywhere.

### 5. "Earth thermal amplitude at most 39 K; Moon 63-180 K": CONFIRMED, and the lunar values are wrong

- **Earth.** Land is 8.89-38.75 K and ocean a constant 2.5 K, from `clip(8+22*bare+0.0022*elev, 6, 48)` (`harmonizer_cleaner.py:262-266`).
- **Moon.** The range is 63.08-179.99 K, a function of latitude only: `clip(180*cos_lat^0.35, 25, 210)` (`:260`).
- **Precise version of the fact:** both are formulas, not data. Diviner shows 250-300 K amplitude at low and mid latitudes. The 63-180 K range is plausible only poleward of about 80 deg (R2 section 3, from 96 sampled Diviner GCP strips).

### 6. "Rover: `temp_k` weighs more than slope after the domain mapping": CONFIRMED

The effective rover weights are `temp_k` 0.1825 and `slope_deg` 0.1725 (FILTERS.md section (e), re-computed with the module). Three domains feed `temp_k`: termico x 0.80, luz x 0.35 and agua x 0.45. Relief is spread over slope, roughness and relative elevation: those three features total 0.49, of which only 0.35 comes from `relieve`; the rest comes from `material`, `luz` and `agua`.

### 7. "A cell that fails a hard filter keeps 35 % of its score": CONFIRMED, with a precision

- `score = where(pass, combined, combined*0.35)` (`analog_finder.py:315-316`), and the same rule applies to `score_all` (322).
- Failed cells stay in `analog_ranking.csv` and in the web JSON with that score.
- **Precision:** `build_optimal_mission_zones` keeps only passing cells (339), and the browser sets failed missions to 0 (`web/index.html:1113-1118`). The outputs therefore disagree with each other.
- An uncommitted change now in the working tree replaces the penalty with NaN. It is not audited here.

---

## (e) Further faults, most serious first

| # | Fault | Evidence | Effect on results |
|---|---|---|---|
| 1 | The committed outputs need `--pds`, and the Moon then comes from `moon_global_pds.npz`, which has no producer. In that npz, elevation is an exact 2-deg block mean of LDEM_4; `slope_deg`, `temp_k` and `rock_or_bare_frac` are of undocumented origin; SAR is a formula | A1 section 5.2, A2 section 2a, A4 F1-F4 | `python main.py` as documented gives a different Moon (elevation up to 9,287 m different, 87 region labels different) |
| 2 | `source` labels are wrong: Moon `real_PDS` on modelled columns, Earth `global_model` on npz data, and the web badge "Real LRO LOLA + Diviner vs. NOAA ETOPO1/SRTM30 + NCEP Global" | `main.py:140-141`; `web/index.html:372` | users are told modelled values are real |
| 3 | The JSON source strings call illustrative values NASA limits (see summary item 8), and `validate()` accepts any non-empty string | `mission_filters.json:12, 24, 29, 36, 49`; `mission_filters.py:130` | provenance misstated |
| 4 | Every run and every pytest run rewrites the tracked `data/presets/presets.json` with `allow_unverified=True`, bypassing the preset's freeze guard | `analog_finder.py:35-56` | the repository changes on each run, and an unverified preset is marked frozen |
| 5 | The new common gate `elevation_m >= 1` would remove 11,041 of 16,200 lunar cells; its `why` ("descarta oceano") has no meaning on the Moon | FILTERS.md section (d) | the new gates cannot be reused for lunar cells as written |
| 6 | Earth `sun_elev_max_deg` uses +11.7 deg where Earth's obliquity is 23.44 deg (R3 F3) | `harmonizer_cleaner.py:256` | Earth maximum sun elevation is under-stated by 11.74 deg at abs(lat) >= 23.44 |
| 7 | An Earth irradiance formula is applied to the airless Moon; `sun_low_frac_0_5deg` is identical on both bodies | `harmonizer_cleaner.py:249-257` | lunar solar values carry no physics |
| 8 | Moon `tmin_c` subtracts 0.35 x amplitude (up to 63 K) from a night-time `temp_k` | `harmonizer_cleaner.py:300` | lunar minimum temperature invented |
| 9 | `pack_cells` fills missing values with fixed numbers (irr 4.0, smax 45.0, slow 0.05, damp 20.0, tic "roca", pfc "ninguno", tmin -5.0) | `analog_finder.py:617-625` (A3 section 3c) | missing data would appear as data in the web layer (no missing values today) |
| 10 | Web `GATE_PROP_MAP` lacks `slope_deg`, `tmin_c` and `elevation_m` | `web/index.html:634-643` | exporting the new configuration would fail every cell for solar and thermal in the browser |
| 11 | The new rover soft score reverses the old formula, although its `provisional` text says it approximates it | FILTERS.md section (c) | rover rankings change direction when switching systems |
| 12 | `on_missing_gate: "keep"` contradicts the author's note and the code default "drop" | `mission_scoring.json:4`; note line 9; `mission_scoring.py:147` | no effect today (no missing values); a missing elevation or mask, or a missing `thermal_inertia_class` in the solar mission (not in solar `require_present`, `mission_scoring.json:34`), would keep a cell |
| 13 | `rover_preset.py` mass 440 kg ("OK", arXiv) against NASA's 447 kg roving and 490 kg launch; ground clearance "MISSING" though NASA publishes 7-43 cm; wheelbase, track and CG height have no official source | `rover_preset.py:73-85`; R1 section 1 | tip-over and Froude figures rest on estimates |
| 14 | The lunar fallback path resamples with `zoom(order=1)`, which places output row 0 at lat 89.875 for a cell labelled 89 | `pds_reader.py:109-111`; A4 F2 | latitude errors up to 0.875 deg (about 26 km) if the npz is removed |
| 15 | With a grid other than 90 x 180, the Earth npz branch injects fake artefacts, and the cleaner then "rescales" 14850 into 297 K | `earth_extractor.py:154-157`; `harmonizer_cleaner.py:64-68` (A2 section 2a) | silent plausible-looking corruption for non-default grids |
| 16 | `earth_mission_filtered.csv` is stale; the zip tree does not import; the self-test count is wrong (5 printed, 7 run); 13.4 MiB zip and `.pyc` committed; README and `rover_preset.py:1` reference missing files | A1 sections 1-3 | maintenance and reproducibility |

---

## (f) Data incoherences

From A2 section 3 and A4, on the committed files.

| Check | Result |
|---|---|
| Units | No kelvin/Celsius mix-up in values: `temp_k` is in K (Earth 217-328, Moon 43-110) and `tmin_c` in degC. But the Moon `temp_k` is a night-time value while the Earth `temp_k` is described as MODIS LST (README:43) and the GEE path reads the daytime band `LST_Day_1km` (`earth_extractor.py:41`, `gee_earth_grid_export.js:31`), and the absolute permafrost and thermal-inertia thresholds apply to both. `irradiance_kwh_m2_day` uses an Earth atmospheric formula on the Moon. Roughness is labelled "local 3x3 std" (`harmonizer_cleaner.py:166`); on the Moon it is the standard deviation within a 2-degree cell. |
| Coordinates out of range | 0 in every CSV and in the web JSON |
| Impossible values | 0 negative irradiance, 0 slopes above 90, 0 fractions outside [0, 1], 0 T <= 0 K, 0 `tmin_c` below -273.15 |
| Repeated points | 0 duplicate (row, col) per body. Distinct benchmark sites share cells and so get identical values: Meteor Crater, Cinder Lake and Black Point (r27 c34); Askja and Holuhraun; Yungay and Salar de Pajonales (A4 section 5) |
| Swapped latitude and longitude | 0: abs(lat) <= 89, abs(lon) <= 179, the geography checks pass, and the lunar elevation matches LDEM_4 only with the correct roll |
| Longitude convention | -180..180 east-positive in every output. PDS products (0-360 E) are rolled at `pds_reader.py:101`. The IAU gazetteer data are 0-360 E although its metadata header says -180..180 (R2 section 2). R1 notes that one NASA presentation writes the VIPER site as "84.6°S, 31.0°W" against the USGS centre at 31.00 E (an apparent sign error, R1 section 1) |
| Constant columns | per body: `body`, `resolution_m`, `source`. Moon also: `mask_fraction` (1), `thermal_inertia_class` ('suelo'), `rain_mm_day` (0), `wind_max_ms` (0) |
| Exact functions of latitude | `sun_elev_max_deg`, `sun_low_frac_0_5deg` on both bodies; on the Moon also `lst_diurnal_amp_k` and the TI class |
| The 500 m label on a 2-degree grid | `resolution_m` = 500, `x_m` and `y_m` in 500 m steps, the GeoTIFF tag `RESOLUTION_METERS = 500.0`, `analog_web_data.json` `resolution_m: 500.0`. A real cell is 222.4 km (Earth) and 60.6 km (Moon) north-south |
| GeoTIFF georeferencing | both TIFFs: EPSG:3857, origin (-45000, 22500), 500 m pixels, bounds +-45 km x +-22.5 km, i.e. lon +-0.404 deg and lat +-0.202 deg at 0 N, 0 E. **The global Earth grid and the lunar grid are both placed as a 90 km patch in the Gulf of Guinea**, and EPSG:3857 is an Earth projection |
| Ocean | 10,273 of 16,200 Earth cells (63.4 %) hold constant fill values in all 7 bands; they are excluded from the ranking by `elevation_m > 0` (`analog_finder.py:430`). A4 also found 156 of the 1,477 web cells with their centre off Natural Earth land although elevation > 0 |

---

## (g) Cross-check of points

### Lunar zones against the IAU Gazetteer

Gazetteer: `MOON_nomenclature_center_pts.shp` (9,087 features, sphere R = 1,737.4 km, data 0-360 E). Distances are great-circle. Full rows: [audit_evidence/A4_lunar_points.csv](audit_evidence/A4_lunar_points.csv).

| Zone label (`analog_finder.py:187-205`) | Code definition | Nearest IAU feature | Verdict |
|---|---|---|---|
| South Pole-Aitken Basin (-53°S, 169°W) | lat -75..-30 and abs(lon) >= 135 (1,058 cells, 100 % farside) | Bose crater, 29.6 km from the label point | PARTLY: the point is plausible, but SPA is not an IAU gazetteer feature, so the outline could not be checked; the code zone is a box, and "-53°S" mixes a minus sign with "S" |
| Tycho & Southern Rocky Craters (35°S–55°S, 30°W–0°) | lat -55..-35, lon -30..+5 (198 cells) | Tycho, 58.8 km from the box centre | YES; the code box reaches lon +5, while the label says 0 |
| South Pole PSR & Shackleton Rim (75°S–90°S) | every cell with lat <= -75 (1,440 cells) | Shackleton, 10.0 km from the pole | YES for location; the 21 km rim is not resolved by 60.6 km cells, and no PSR map is used |
| Mare Tranquillitatis & Equatorial Maria | abs(lat) <= 30 and elevation <= -1200 m (1,626 cells) | - | **NO**: only 92 cells lie within Mare Tranquillitatis; 13.9 % are farside |
| Lunar Farside Highlands (> +2000 m) | elevation >= 80th percentile = 979.58 m (3,240 cells) | - | **NO**: 15.4 % nearside; 40.4 % below +2000 m |
| Steep Crater Walls & Massifs (Top 20% Slope) | slope >= 11.32 deg (3,240 cells) | - | the definition matches the code; it is not a place, and the slope origin is undocumented |
| Global Lunar Surface Mean | all 16,200 cells | - | consistent |

### Lunar values against the LRO products cached in the repository

| Column | Against the cached products | Level |
|---|---|---|
| `elevation_m` | equal to the 8x8 block mean of `ldem_4.img` in all 16,200 cells (MAE 0.00 m) | DERIVED |
| `elevation_rel_m` | elevation minus the global mean (-518.97 m) | DERIVED |
| `roughness_m` (= `rough_300m_m`) | standard deviation of the 64 LDEM_4 pixels (7.58 km) in the cell, exact | DERIVED |
| `slope_deg` (= `slope_300m_deg`) | not the code formula (r 0.31), not LDEM_4 pixel-slope statistics (best r 0.63); row 66 against the LDEM_64 block slope: r 0.764 | UNDOCUMENTED ORIGIN |
| `temp_k` | row 66 (lat -42..-44) matches the Diviner `DGDR_ST_CLC_0030` night temperature block mean (MAE 0.80 K); values poleward of 60 deg cannot come from the cached product (label `MAXIMUM_LATITUDE = 60`) | UNDOCUMENTED ORIGIN |
| `rock_or_bare_frac` | row 66 matches Diviner RA (r 0.972) | UNDOCUMENTED ORIGIN |
| `sar_sigma0_db` | exact formula, no radar product | MODELLED |

**Where A2 and A4 disagree** (checked for this document):

- **Lunar elevation level.** A2 says MEASURED and A4 says DERIVED. DERIVED is used, for the reason given in DATA_DICTIONARY.md section 1.
- **Lunar temperature and rock.** A4 says DERIVED within +-60 deg on one verified row; A2 says not determined. UNDOCUMENTED ORIGIN is used.
- **Lunar SAR.** A2's exact formula is right (residual 2e-6, re-run); A4's is the code fallback plus an offset.
- **Line numbers.** A4 cites `lunar_extractor.py:166-189` for the npz loader and `130-153` for the formulas; the correct lines are `61-84` and `25-48` (`grep`, 225-line file). A2 cites `pds_reader.py:326` for the longitude roll; the file has 163 lines and the roll is at line 101.

### Earth points: country, region, and why the labels fail

A4 checked every named or ranked Earth point:

- **Country:** Natural Earth 1:110m.
- **Region:** GeoNames via `reverse_geocoder`.
- **Label check:** OFF_LAND if the centre is off land and the cell is less than 50 % land; OFF_COUNTRY if the country is not the one the label names; LOOSE if the cell is more than 500 km from the label's anchor (A4's threshold).

| Output | n | OK | LOOSE (> 500 km) | OFF_COUNTRY | OFF_LAND | coastal |
|---|---|---|---|---|---|---|
| `optimal_mission_zones.csv` (= JSON) | 30 | 9 | 15 | 1 | 5 | 0 |
| `analog_ranking.csv` | 100 | 27 | 51 | 4 | 15 | 3 (LOOSE_COASTAL) |
| web `earth_cells` | 1,477 | 256 | 708 | 357 | 131 | 25 |

**How the labels are made, and why they fail.** `assign_earth_region_names` (`analog_finder.py:129-140`) takes the nearest of 48 hard-coded anchors by `hypot(dlat, dlon*cos(lat))` in degrees. Below 18 "degrees" (up to about 2,000 km) it writes the bare anchor name. Near the poles `cos(lat)` shrinks the longitude term. Examples:

- Ranks 2 and 11, "Devon Island Haughton Crater", are in Greenland (83N, 25W and 27W), 1,401 km from the anchor.
- Ranks 47 and 62, "Brooks Range & North Slope (Alaska)", are in Chukotka, Russia.
- Rover zone 5, "Kamchatka Volcanic Belt", is in Chukotka (67N, 175E).
- Rover zone 3, "Gobi Desert & Altai Range (Mongolia)", is in Hebei, China.

The top-100 ranking lies entirely north of 55N or south of 65S, and its median distance to the label's anchor is 672 km.

### Benchmark analog sites and the cells they fall in

`rover_preset.py` as committed names no sites. The closest committed equivalent, the 48 `EARTH_LANDMARKS` anchors (`analog_finder.py:77-126`), was compared with the 44 verified sites in `/home/user/NASA/docs/research/02_analog_benchmark.csv`. Cell = floor((90-lat)/2), floor((lon+180)/2).

| Landmark | Benchmark site | km apart | Cell | elev m | slope deg | In outputs |
|---|---|---|---|---|---|---|
| McMurdo Dry Valleys | MA07 | 13.0 | r83 c171 | 590 | 9.71 | no |
| Craters of the Moon (Idaho) | MO07 | 0.7 | r23 c33 | 1635 | 7.52 | no |
| Meteor Crater (Arizona) | MO02 | 3.4 | r27 c34 | 1750 | 6.70 | no |
| Mauna Kea | MO05 | 4.1 | r35 c12 | **-250 (ocean-coded)** | 0.01 | no |
| Teide & Lanzarote | ES05 / ES02 | 3.9 / 284.5 | r30 c81 / r30 c83 | **-250 (ocean-coded)** | 0.01 | no |
| Devon Island Haughton | MA06 | 221.8 | r7 c49 (site r7 c45) | 807 | 9.61 | the site's own cell is ranking #64 |
| Atacama, Askja, Etna, Afar, Pilbara | MA01, MA10, MO11, MA13, MA18 | 6-314 | see A4 section 5 | | | Pilbara in the web layer only |

**Cell-level effects** (A4 section 5):

- The median distance from a site to its cell centre is 57 km, and the maximum is 144 km.
- Six sites (ES02, ES03, ES05, MO05, MO06, OP02) are in ocean-coded cells and are excluded.
- Only one site cell is in the top 100, and only two (ES01, ES04) are among the 1,477 web cells, because the web layer keeps even rows and columns only.

**Conclusion:** a 2-degree cell cannot represent any of these sites.

---

## (h) The solar-mission concept fault

### What the code selects today

- **Old (live) system.** The solar mission ranks Earth cells by similarity to the lunar zone "South Pole PSR & Shackleton Rim (75°S–90°S)" (`analog_finder.py:258-263`). That zone is every lunar cell with lat <= -75, with no illumination input. Its mean `temp_k` z-score is -2.85, the most extreme in the profile, so the target pulls toward Earth's coldest cells. The solar `gate_q` rewards a **higher** grazing fraction: `low_q = (slow-0.025)/0.18` (`analog_finder.py:291`). Result: all six committed solar zones are polar cold cells (East and West Antarctica, the McMurdo label, Verkhoyansk), with irradiance 2.84-3.92 and sun_elev_max 20.7-34.7 deg (A3 section 6).
- **New system.** The gates and the soft score favour high sun and little grazing sun. The top cells are in tropical Africa, in the Sahel and beyond it (Senegal, Chad, Somalia, Burkina Faso, Central African Republic, Benin, DR Congo; scores 95.08-95.62). Applied to the Moon, the gates remove every cell poleward of about 77 deg (FILTERS.md section (d)). The `why` of the sun-elevation gate is "sol siempre rasante = sombras permanentes".
- **Neither system has an illumination variable.** `sun_elev_max_deg` is `90 - |lat| + constant`, and `sun_low_frac_0_5deg` and `irradiance_kwh_m2_day` are latitude formulas (`harmonizer_cleaner.py:249-257`). The code cannot tell a lit rim from a PSR.

### Why this is the opposite of the lit-ridge concept, per R2 and R3

| Fact | Quote and source |
|---|---|
| A PSR receives no direct sunlight | "permanently shadowed regions (PSRs, defined as areas that never receive direct solar illumination)" (Mazarico et al. 2011, https://ntrs.nasa.gov/api/citations/20120010094; R2 section 1) |
| The Moon's axial tilt | "The spin axis of the Moon is tilted by only 1.54°." (PIA13720, https://science.nasa.gov/photojournal/south-pole-illumination-map); Earth obliquity "23.44" (https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html; R3 F3) |
| The Sun at the poles | "At the Moon's North and South Poles, the Sun is never more than 1.5° above or below the horizon." (https://svs.gsfc.nasa.gov/4893) |
| Lit and shadowed areas are neighbours | "leaving some areas near the poles in permanent shadow" / "other nearby regions remain sunlit for the majority of the year" (PIA13720) |
| Illumination fractions | "We identified locations receiving sunlight for 92.27% of the time at 2 m above ground" / "95.65% of the time at 10 m above ground" (Gläser et al. 2014, https://elib.dlr.de/94240; MODELLED); Shackleton rim points "remain collectively sunlit for more than 90% of the year" (https://science.nasa.gov/resource/shackleton-craters-illuminated-rim-shadowed-interior/); best-lit sites 69.5-82.9 % at the surface (R3 F8) |
| Away from the poles | about 50 % of the time on flat ground, DERIVED from 14-day day and night (R2); no official per-latitude table found |
| Consequences for the gates | `sun_elev_max >= 10` fails every lunar cell above about 81.5 deg (R3 D1); horizontal irradiance at a lunar pole is at most 0.88 kWh/m2/day, below both the 1.8 and 2.5 gates (R3 D3) |

So the concept the team lead describes (lit polar ridges for power) is supported by the sources. The old system targets the PSR band, which is the dark half of that pair. The new system excludes the polar band altogether.

### What data would be needed to fix it

- **Moon:** a measured illumination fraction. Candidates: LOLA polar illumination (Mazarico 2011; PGDA product 69, for example `AVGVISIB_85S_060M_201608.TIF`, 34 MB, 60 m, HTTP 200) and the LROC WAC illumination percentage (`WAC_POLE_ILL_PCT_SOUTH_100M.IMG`, 100 m, 88-90 S). Both URLs were tested by R2 section 2. A PSR mask from the same sources would let the ice mission target real PSRs.
- **Earth:** an analog metric for long periods of low sun, computed with the correct 23.44 deg obliquity; and a panel-normal or time-averaged irradiance from a named product. R3 records that NASA POWER was not accessed in this session.
- **Both:** a statement of whether irradiance is horizontal, panel-normal or lunation-averaged (R3 open question 1).

---

## (i) Open questions for the team

| # | Decision needed | Default the integration will use if no answer comes |
|---|---|---|
| 1 | Where do `earth_global_real.npz` and `moon_global_pds.npz` come from (product, date, processing, script)? | Keep using them, label every Earth band and Moon slope, temperature and rock as UNDOCUMENTED ORIGIN, and remove "real", "NOAA", "SRTM", "NCEP", "MODIS" and "Diviner" from badges and source strings |
| 2 | Which system is the single source of mission filters: `mission_filters.json` or `mission_scoring.json`? | `mission_scoring.json` (its note says it replaces the old file), with `mission_filters.*` kept until nothing imports them |
| 3 | Missing value in a hard filter: drop or keep? | **drop**, as the author's note says; `require_present` is unchanged |
| 4 | Rover: are the provisional gates in `mission_scoring.json` (slope 0.5-15, roughness 5-650) and soft weights 0.45/0.30/0.25 accepted, given that `rover_preset.py` sets no roughness gate and no minimum slope? | Keep the JSON values marked provisional; cite 15 deg as the NASA VIPER requirement (R1: M24 p.4) at rover scale; mark 0.5 deg and 5-650 m "no official source" |
| 5 | Which `rover_preset.py` is current: the committed one or v3 in the local zip, and what does `rover_integration.py` do? | The committed one; the comparison stays pending |
| 6 | Solar: should the solar mission target lit polar ridges (R2), and should the solar gates be re-expressed as an illumination fraction? | Do not apply the solar gates to lunar cells. State on the solar card that no illumination data exist. Do not change thresholds until the team decides |
| 7 | Which lunar zone is the solar target, and which is the ice target? | Ice keeps the polar band, labelled "south polar band (lat <= -75), not a PSR map"; solar gets no lunar target until question 6 is answered |
| 8 | Thermal: compare amplitude rather than absolute temperature (the director's ruling in `/home/user/NASA/docs/plan/09b_team_inputs_and_contract.md` section 2.3), and with which lunar amplitude source? | Show `temp_k` similarity with an "each body normalised separately" warning; do not present lunar amplitudes 63-180 K as data |
| 9 | Should the common gate `elevation_m >= 1` apply to lunar cells? | No: apply the common gates to Earth only |
| 10 | Grid: stay at 2 degrees, or move to the 0.25-degree grid of the integration contract? | Stay at 2 degrees, label cells "2-degree cell, about 222 km", and drop every "500 m" and "300 m" label |
| 11 | Earth region names: replace the 48-anchor labels with computed country and region? | Show the country (Natural Earth) and "nearest landmark: <name>, <distance> km" |
| 12 | Failed cells: zero, NaN or x0.35? | NaN (removed), as in `mission_scoring.py`; the browser already shows 0 |
| 13 | May the 13.4 MiB root zip and the committed `.pyc` files be removed (a new commit; a history rewrite is a separate decision)? | Remove them in a new commit only after the pending zip comparisons, and leave history unchanged |
| 14 | Rover physical figures: use NASA's 447 kg roving mass and 7-43 cm ground clearance (R1)? | Use them with their R1 citations; leave wheelbase, track and CG height marked ESTIMADO |
| 15 | Thresholds marked "diseno" (all solar and thermal values): who validates them? | Keep them unchanged, shown as "design value, no official source" with the verdicts of FILTERS.md section (g) |

---

## Verification

An independent verifier re-checked the three documents (AUDIT.md, DATA_DICTIONARY.md with data_dictionary.csv, FILTERS.md) on 2026-11-14. The verifier did not write them.

**Method.**

- State: commit 618bc45. The verifier's scratch copy (`scratchpad/stars/run-verify`, copied from `scratchpad/stars/work`) is byte-identical to `git show HEAD:` for `mission_scoring.json`, `mission_scoring.py`, `mission_filters.json`, `analog_finder.py` and `harmonizer_cleaner.py`. The uncommitted working-tree changes listed at the top of this document (`on_missing_gate` "drop", NaN instead of x0.35, `tierra luna/engine/`) were confirmed with `git diff` and were not used for any check.
- Commands, all run with `scratchpad/stars/venv/bin/python` (Python 3.13.18): `pytest tests` (15 passed, 14 functions); the four self-tests; `mission_scoring.py run` for `solar,thermal` and for all four missions; `main.py --pds` in a second copy (`run-verify-pds`), whose `earth_moon_harmonized_clean.csv` equals the committed one exactly; and two scripts, `scratchpad/stars/vscripts/v1.py` (old and new pass counts on both bodies, overlaps, land failure counts, lunar latitude cut-offs) and `v2.py` (ranges, classes, fills, formulas, lunar zones). Further one-off checks covered the effective weights (the module's own `map_domain_weights_to_features`), the LDEM_4 8x8 block mean and standard deviation against `moon_global_pds.npz` (elevation: zero difference; roughness: 2e-4 m), the zip sha256 comparison, the GeoTIFF georeference, the benchmark sites, and the top-ranked solar and thermal cells (reverse geocoded).
- Every threshold, weight, `why`, `source`, map and default in FILTERS.md sections (a), (b), (f), (g) and (h) was compared with `mission_filters.json` and `mission_scoring.json` field by field.
- Every quotation attributed to R1, R2 and R3 was found in those notes, with its URL, and each verdict was compared with the note's own verdict.

**Claims re-derived: about 320**, counting one table row or one sentence as one claim. Approximate breakdown: JSON thresholds, weights and texts 49; mission_scoring.py and mission_filters.py behaviour and line references 15; pass counts on both bodies, overlaps and failure counts 21; effective feature weights 6; the x0.35 lines and the browser rule 4; thermal amplitude and temperature ranges on both bodies 4; grid, cell size, `x_m`/`y_m`, `resolution_m` and GeoTIFF 5; ocean and land counts and fill values 3; test and self-test results and test line numbers 6; the level of every variable against the code that produces it 44; observed ranges and class counts 38; README table rows 26; other file:line references 50 (in config.py, earth_extractor.py, lunar_extractor.py, pds_reader.py, main.py, analog_finder.py, web/index.html, rover_preset.py, mission_filters.py, tests, the author's note); zip and inventory 7; lunar zones, benchmark sites and the top-100 ranking 14; R-note quotations and verdicts 30.

**The four facts set by the director were confirmed:** solar 5,192, thermal 2,613 and both 1,986 on the 16,200 Earth cells; the provisional rover block (`mission_scoring.json:10-31`, gates 0.5-15 and 5-650, soft weights 0.45/0.30/0.25) and ice block (lines 74-88) exist; `on_missing_gate` is "keep" at line 4 of the committed file; the CLI keeps only EARTH rows (`mission_scoring.py:266-267`).

**Errors found and corrected (16):**

1. DATA_DICTIONARY.md section 4 and data_dictionary.csv cited the valid ranges at `config.py:80,90`, `81,91`, `83,93`, `84,94` and `85,95`. The lines are `88,98`, `89,99`, `91,101`, `92,102` and `94,104`.
2. DATA_DICTIONARY.md spoke of "four derived outputs" at the end of the CSV; there are six.
3. Moon `sun_elev_max_deg` was labelled DERIVED. Its only input is the cell-centre latitude, not a measured value, so under this project's definition it is MODELLED (with correct geometry and the official 1.54 deg tilt). The level counts (Moon: DERIVED 4 = 21 %, MODELLED 11 = 58 %) and the "three DERIVED values touched by gates" statement (now two) were corrected.
4. data_dictionary.csv labelled `similarity_pct`, `feature_distance` and `score_rover` as DERIVED, against DATA_DICTIONARY.md's own weakest-level rule. Now `similarity_pct` and `feature_distance` are UNDOCUMENTED ORIGIN, `score_rover` is "MODELLED at best", `matched_lunar_zone` is UNDOCUMENTED ORIGIN, and `earth_region` is METADATA, a label from coordinates and hard-coded anchors.
5. FILTERS.md said every mission gate column is also in `require_present`. The solar gate `thermal_inertia_class` is not (`mission_scoring.json:34`), so with "keep" a missing class would keep a solar cell. FILTERS.md section (b) and AUDIT.md section (e) row 12 were corrected.
6. `validate()` was described as checking "only two things". It also checks min <= max and complete weights (`mission_filters.py:122-144`). FILTERS.md section (a) and the test table in AUDIT.md section (b) were corrected.
7. The Tycho zone mean roughness was 719.3235 m in FILTERS.md section (c); the module gives 719.3236 m.
8. FILTERS.md section (g) gave the rover tolerance source as "Robotics 1 rover_preset.py tolerance scale" in a column headed "exact". The exact strings end in "(5.0 deg)" and "(10.0 m)".
9. FILTERS.md section (g) gave the verdict "contradicted" for the solar soft criteria `sun_elev_max_deg` and `sun_low_frac_0_5deg` as if it were a source verdict. R3 calls all weights pure design choices (summary 7). The rows now say "n.s.f. for the weight", and they label the conflict with the polar facts as an inference.
10. FILTERS.md section (d) and AUDIT.md section (h) equated the solar top cells with the note's "Sahel y Sahara". Several top-10 cells are in Somalia (1 S), DR Congo (3 S) and the Central African Republic (5 N), outside both regions.
11. AUDIT.md section (c), README row 9, said the "Earth npz offset varies 750-1047 m". On land the offset is a single constant, 1047.42 m. The 750 m comes only from the ocean fill values (-250 and -1000).
12. The AUDIT.md test table said the landmark test "asserts" the label "real_NOAA". Line 249 only passes the label; nothing asserts it.
13. AUDIT.md section (f) cited README:43 for a "daytime" Earth LST. README:43 says only "MODIS LST x 0.02". The daytime band is `LST_Day_1km`, read only on the GEE path (`earth_extractor.py:41`, `gee_earth_grid_export.js:31`).
14. The Earth label table in AUDIT.md section (g) left out A4's "coastal" column, so the rows did not add up to n (97 of 100; 1,452 of 1,477). The column was restored (0, 3, 25).
15. AUDIT.md section (d) item 4 said the Moon SAR formula is exact "in the committed run". It is exact in `moon_global_pds.npz`. In the committed CSV, 17 cells were replaced by the IQR step.
16. AUDIT.md section (d) item 6 gave 0.49 as relief's total. 0.49 is the total weight of the three relief features, of which only 0.35 comes from `relieve`.

**Checked and found correct (examples a decision rests on):**

- the old and new pass counts (rover 5,297/5,297; solar 5,198/5,192; thermal 3,337/2,613; ice 3,023/3,023; solar and thermal 3,162/1,986; all four 2,114/1,728);
- the Moon counts (old/new rover 9,062/1,910, solar 14,400/4,712, thermal 0/5,159, ice 4,680/801, all four 0/203; 11,041 cells failing `elevation_m >= 1`);
- the effective weights (rover `temp_k` 0.1825 against `slope_deg` 0.1725);
- the x0.35 lines (`analog_finder.py:315-316, 322`) and the browser zeroing (`web/index.html:1113-1118`);
- thermal amplitude (Earth land 8.89-38.75 K, ocean 2.5 K, Moon 63.08-179.99 K);
- 90 x 180 cells of 222.4 km (Earth) and 60.6 km (Moon); 10,273 ocean and 5,927 land Earth cells;
- the six benchmark sites in ocean cells;
- the zip: 50 files identical, none different.

**Not verified, and why:**

- The zip of pull request #1 ("files 2.zip") and the team's local zip with `rover_preset.py` version 3 and `rover_integration.py`. Neither file is available in this session, so both comparisons stay pending. The documents do not describe their content.
- The web sources behind R1-R4 were not re-opened, as instructed. Only the faithfulness of the documents to the notes was checked.
- Browser behaviour: that exporting the new configuration would fail every solar and thermal cell (`GATE_PROP_MAP`) and that the rover input overrides the slope maximum. Both were read from code; the page was not run.
- A4's geocoding of all 1,607 Earth points, the IAU gazetteer distances, "92 cells within Mare Tranquillitatis" and the median of 672 km to the label anchor. These were not re-run; only the top-10 solar and top-4 thermal cells were re-geocoded.
- The origin of `earth_global_real.npz` and of the Moon slope, temperature and rock arrays. Nothing in the repository documents it, so it cannot be verified.
- Python 3.12, the version of the committed `.pyc` files, is not installed here. `--use-gee` was not run (no credentials).

---

## Differences between the team lead's description of the data and the committed files

Added 2026-11-14 for the similarity proposal ([SIMILARITY_PROPOSAL.md](SIMILARITY_PROPOSAL.md)). Each fact was re-counted on the committed legacy table `tierra luna/output_py/earth_moon_harmonized_clean.csv` (unchanged since commit ca72d0b; 16,200 EARTH and 16,200 MOON rows, no missing values) with `scratchpad/stars/venv/bin/python`. Nothing in the repository was changed.

| Item | The description said | The committed table (re-counted) |
|---|---|---|
| Lunar `elevation_m` | -3,626 to -677 m, so the land mask `elevation_m >= 1` would remove every lunar cell | **-7,609.7 to +8,301.9 m**; **5,159** lunar cells are at or above 1 m (the land mask would remove 11,041, not all) |
| Lunar `permafrost_class` | `ninguno` everywhere | `ninguno` **11,520**, `discontinuo` **2,922**, `continuo` **1,758** (a latitude formula) |
| Lunar `thermal_inertia_class` | `suelo` 15,306 and `arena` 894 | `suelo` in **all 16,200** cells |
| Lunar `tmin_c` | -161 to -45 C | **-251.78 to -219.83 C** |
| Rover target in the old optimality score | the south-pole zone | the **Tycho zone**: `compute_mission_optimality_scores` maps `"rover": rocky_target`, and `rocky_target` is "Tycho & Southern Rocky Craters (35°S–55°S, 30°W–0°)" (`git show main:"tierra luna/analog_finder.py"`, lines 254-263). Solar and ice use the south-pole zone, thermal the global mean. |

**Probable cause (an inference, then checked).** The audit found that `main.py` without `--pds` builds a different, synthetic Moon (`moon_source = "synthetic"` when no LOLA file is given, `main.py:140`), and that the committed table comes from a `--pds` run (the Verification section above reproduced it exactly with `main.py --pds`). The described values therefore probably came from a run without `--pds`. To test this, the default pipeline was run in a scratch copy (`scratchpad/stars/proposal/run_default`, `python main.py --out-dir out_default`, never inside the repository). Its lunar rows (`source = synthetic`) give exactly the described values: `elevation_m` -3,625.53 to -676.73 m with **0** cells at or above 1 m; `permafrost_class` `ninguno` in all 16,200 cells; `thermal_inertia_class` `suelo` 15,306 and `arena` 894; `tmin_c` -161.33 to -45.08 C. Its Earth rows are identical to the committed ones (checked on `elevation_m`, `slope_deg`, `temp_k`, `rock_or_bare_frac`). So the four data facts in the description match the default (synthetic-Moon) run and not the committed table. That the team lead's numbers were taken from such a run remains an inference; the match is exact. The fifth item (rover target) is code, not data, and is the same in both runs.

**Possible labelling fault, left unchanged.** In the committed table every lunar cell has `thermal_inertia_class = suelo` ("soil"). The lunar surface is regolith, and the class list used by the missions has a `regolito` class (`mission_scoring.json`, thermal soft map). The real 1-degree lunar table (`output_real/moon_real_1deg.csv`) uses `regolito` everywhere. The legacy label is probably wrong; it was not changed. It matters for any similarity that compares this class across bodies: with `suelo` on the Moon, Earth cells labelled `suelo` match and Earth cells labelled `regolito` do not.
