# A1 - Inventory, zip comparison, tests, README vs code, end-to-end reproducibility

Scope: repository `/home/user/stars-beside-you` (branch final-integration = main, 3 commits), read only; nothing was run inside it (`git status --short` is empty after the audit). All runs used copies:
`$S=/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars`
- `$S/run-A1` (work copy: tests, self-tests, mission_scoring runs; helper files in `$S/run-A1/_a1/`)
- `$S/run-A1-default` (`python main.py`), `$S/run-A1-pds` (`python main.py --pds`), `$S/run-A1-nonpz` (cache npz files renamed), `$S/run-A1-zip` (zip tree as shipped).
Python used: `$S/venv/bin/python` = Python 3.13.18 (the committed `.pyc` files are cpython-312).

Not available in this session, so not compared: the zip of pull request #1 ("files 2.zip") and the team's local zip with `rover_preset.py` v3 and `rover_integration.py`. Nothing below describes their content.

---

## 1. Repository vs zip, superfluous/risky content, secret scan

### 1.1 File-by-file sha256 ("tierra luna/" in repo vs "tierra luna/" in `STARS-BESIDE-YOU-main (2).zip`)
Command: `find . -type f | sort | xargs sha256sum` in both trees, then `diff` of names and `join` on path (lists in `$S/run-A1/_a1/run_a1_{repo,zip}.sha`).

| Result | Files |
|---|---|
| Identical (same sha256) | 47 of 49 files on each side, **including all 9 `__pycache__/*.pyc`** (also `__pycache__/mission_filters.cpython-312.pyc` is in the zip) |
| Only in repo | `mission_filters.py`, `mission_filters.json` |
| Only in zip | `mission_scoring.py` (sha256 b10d1bcf...), `mission_scoring.json` (d4faf620...) |
| Changed | none |
| Root file `Instruciones filtros solar y temp` | identical in repo root and zip root (b14e782c...) |

Correction to the baseline: the zip does not differ in `__pycache__` either; the trees differ only in the 4 files above.

**The zip tree does not run as shipped.** `analog_finder.py:10` does `from mission_filters import ...`; the zip has no `mission_filters.py`. In `$S/run-A1-zip`: `python -c "import analog_finder"` -> `ModuleNotFoundError: No module named 'mission_filters'`; `pytest tests -q` -> `1 error during collection`. (The stale `__pycache__/mission_filters.cpython-312.pyc` cannot rescue this: a pyc inside `__pycache__` is only used when the source exists. Verified on 3.13; 3.12 not run.) So the author's advice "copy the two files, do not touch mission_filters.py" only works in the repo tree, not by replacing the tree with the zip.

### 1.2 Superfluous or risky content (`git ls-files`, `find -size +1M`, `git count-objects -vH`)

| Item | Evidence | Effect |
|---|---|---|
| 13.4 MiB zip committed at root | `STARS-BESIDE-YOU-main (2).zip` 14,031,467 B, commit d4a11e4 | Duplicates the whole tree; pack is already 25.93 MiB. Deleting it in a new commit does not shrink history (needs history rewrite, which is the owner's decision). |
| Compiled bytecode committed | 9 files: `tierra luna/__pycache__/*.cpython-312.pyc` (8) + `tests/__pycache__/test_pipeline.cpython-312-pytest-9.2.0.pyc` | Machine/version specific, stale risk (a pyc for `mission_filters` travels in the zip without its source). |
| No `.gitignore`, no `.gitattributes` | `ls -a` of repo root shows only `.git`, the zip, the notes file and `tierra luna` | Nothing stops pycache, outputs, caches being re-committed. No LFS. |
| Generated outputs committed | `output_py/` 10 files (largest `earth_moon_harmonized_clean.csv` 6.1 MB), `web/analog_data.js` 2.5 MB, `output_py/analog_web_data.json` 2.5 MB (same payload, verified equal) | Every run rewrites them; diffs are noisy. Committed CSVs are CRLF (`git ls-files --eol`: `i/crlf`), regenerated ones LF, so a byte diff appears even when content is equal. |
| Downloaded/cached data committed without LFS | `data/cache/`: `ldem_64...rows_8466_8596.bin` 5.99 MB, `ldem_4.img` 2.07 MB, three Diviner `rows_3272_3339.bin` 1.54 MB each, `earth_global_real.npz` 150 KB, `moon_global_pds.npz` 383 KB | The two `.npz` files have no producer in the repo (see 5.3); the pipeline silently prefers them over the code paths. |
| Folder names with spaces / odd names | `tierra luna/`, `STARS-BESIDE-YOU-main (2).zip`, `Instruciones filtros solar y temp` (no extension, misspelt) | Needs quoting in every shell/CI command. |
| Side-effect write into a tracked file | `analog_finder.py:53` `merge_into_presets(Path(PRESETS_JSON_PATH), preset, name="rover", refreeze=True)` | Every pipeline run and every `pytest` run rewrites `data/presets/presets.json` (`frozen_at`, `refrozen_from` timestamps). Observed: work copy sha 692a9290 -> eef63e9b after `pytest`; the director's baseline run had already changed the work copy (repo sha 87a52b48, `frozen_at` 18:34:24 vs work copy 20:32:21). |
| Dangling reference | `rover_preset.py:1` "Declared in docs/AI_USE.md" | No `docs/` folder exists in the repo. |

### 1.3 Secret scan
Patterns: `AKIA[0-9A-Z]{16}`, `AIza...`, `ghp_`, `github_pat_`, `sk-...`, `xox[baprs]-`, `BEGIN ... PRIVATE KEY`, `"private_key"`, `client_secret`, `api[_-]?key`, `apikey`, `secret`, `token`, `passw`, `bearer`, `authorization` (case-insensitive).
- `git grep -I -i -E <pattern> <commit>` for each of ca72d0b, bfa0995, d4a11e4: **no match**.
- `grep -r -I` over the unpacked zip: **no match**.
- `grep -a` over all tracked binaries for `AKIA..|AIza|ghp_|PRIVATE KEY|client_secret`: **no match**.
- Only prose hits for "credentials" (`README.md:18`, `README.md:80`) and "ee.Authenticate" (`main.py:99`). Nothing that looks like a key, token or password.

---

## 2. Integrating `mission_scoring.py` / `mission_scoring.json`

### 2.1 What imports what (grep of `import`/`from` in all `.py`)

| Module | Imports (project modules) |
|---|---|
| `main.py:5-13` | config, lunar_extractor, earth_extractor, harmonizer_cleaner, analog_finder |
| `analog_finder.py:10-18` | **mission_filters** (TEMPLATE, apply_missions, load_cfg), rover_preset |
| `analog_finder.py:20-22` | reads `mission_filters.json` next to the module |
| `harmonizer_cleaner.py:10-11`, `earth_extractor.py:5-6`, `lunar_extractor.py:6-7` | config, lunar_extractor, pds_reader |
| `tests/test_pipeline.py:10-15, 263-264` | config, lunar_extractor, earth_extractor, harmonizer_cleaner, pds_reader, analog_finder, mission_filters, rover_preset |
| `web/index.html` | reads `window.ANALOG_DATA.mission_filters` (`index.html:646`), labels say "mission_filters.json" (`:373, :378, :395, :566`); no `soft` handling (grep for `soft` = 0 hits) |

**Nothing calls `mission_scoring`** (grep over repo `.py/.html/.js/.md`: 0 files; in the work copy only the module itself).

### 2.2 What `mission_scoring.py` expects
- Config path: `CONFIG_PATH = <dir of mission_scoring.py>/mission_scoring.json` (`mission_scoring.py:37`); `--config` overrides (`:257`).
- Input: a CSV via `run --cells` (filters `body == EARTH` if the column exists, `:266-267`) or a DataFrame via `evaluate(df, missions)` (`:160`).
- Every gate/soft/require_present column must exist or it raises `KeyError` (`:50, :83, :127`). Columns used by the shipped JSON: `elevation_m, mask_fraction, slope_300m_deg, rough_300m_m, rock_or_bare_frac, irradiance_kwh_m2_day, sun_elev_max_deg, sun_low_frac_0_5deg, slope_deg, thermal_inertia_class, lst_diurnal_amp_k, roughness_m, tmin_c, permafrost_class, temp_k`. All are present in `earth_moon_harmonized_clean.csv` and `earth_srtm_modis_aster_clean.csv`; **`earth_mission_filtered.csv` lacks `tmin_c`** (and rain/wind), so `thermal` would raise on it.
- Only numpy/pandas; no project imports.

### 2.3 Is copying the two files enough?
Copying makes the standalone tool work and changes nothing else. Verified in `$S/run-A1` (which has both files):

```
python mission_scoring.py selftest                -> selftest OK (5 comprobaciones)
python mission_scoring.py run --cells output_py/earth_moon_harmonized_clean.csv --missions solar,thermal --out .../ms_scores.csv
  solar: 5192/16200 ... score medio 60.2 ; thermal: 2613/16200 ... score medio 57.6 ; pasan todas: 1986
python mission_scoring.py run ... --missions rover,solar,thermal,ice
  rover 5297, solar 5192, thermal 2613, ice 3023, all four 1728
```
The author's figures (5,192 / 2,613 / 1,986, notes lines 21-23) reproduce exactly.

Steps (exact):
1. `cp mission_scoring.py mission_scoring.json "tierra luna/"` (from the zip). Do not delete `mission_filters.py/.json` (imported by `analog_finder.py:10` and `tests/test_pipeline.py:263`).
2. Run `python mission_scoring.py selftest` and the `run` command above from inside `tierra luna/`.

Still unconnected after copying:

| Gap | Evidence |
|---|---|
| Pipeline pass flags still come from `mission_filters.apply_missions` with `on_missing="keep"` | `analog_finder.py:505-510` |
| Pipeline mission scores come from a third, hard-coded formula set (65 % similarity + 35 % `gate_q`, failing cells x0.35), unrelated to both JSONs' soft criteria | `analog_finder.py:243-323` |
| Web reads `mission_filters` from the bundle; `to_web_cfg()` exists (`mission_scoring.py:190-204`) but nobody calls it; web ignores `soft` | `analog_finder.py:567, 668`; `index.html:646` |
| `combine_with_similarity` uses `similarity_pct`, which only exists after `compute_analog_ranking` | `mission_scoring.py:207-211`, `analog_finder.py:457` |
| Not in pytest; README does not mention it | `tests/test_pipeline.py` (no reference) |
| Two different gate sets live side by side: solar in `mission_filters.json:56-70` (irr 1.8-8.5, sun_elev 5-85, sun_low 0.025-0.4) vs `mission_scoring.json:35-41` (irr >= 2.5, slope_deg <= 15, sun_elev >= 10, sun_low <= 0.25, not water); thermal `mission_filters.json:91-104` (amp 16-60, class in roca/regolito/arena/hielo) vs `mission_scoring.json:57-61` (amp >= 15, tmin_c <= 5, not water) | Same data, different counts: solar 5198 (mission_filters CLI) vs 5192; thermal 3337 vs 2613. Rover and ice gate sets are identical in both (5297 / 3023). |

Inconsistencies inside the new system (state of the zip files, not opinions):
- `mission_scoring.json:4` sets `"on_missing_gate": "keep"`, so a missing value in a hard gate **keeps** the cell; the author's note (`Instruciones...:9`) and the module docstring (`mission_scoring.py:18-19`) say a missing hard-filter value discards it. The code default is `"drop"` (`:147`), overridden by the JSON. Today it changes nothing: the Earth rows have 0 NaN in every column (checked with `e.isna().sum()`), and `require_present` columns are always dropped when missing (`:81-89`).
- Self-test prints "5 comprobaciones" but contains 7 `assert` statements (`:235-247`); it uses an inline config (`:216-228`) with `on_missing_gate: "drop"`, so it never exercises the shipped JSON.
- `mission_scoring.json:3` says it "sustituye a mission_filters.json", contradicting the author's "sin tocar mission_filters.py".
- All solar/thermal thresholds are labelled "diseno" and "NO validados con fuente externa" (`mission_scoring.json:3`, `:36-40`, `:58-60`; notes `:34`).
- Ocean handling: common gate `elevation_m >= 1` (`:6`). In the data 10,273 Earth cells have `elevation_m == -250.0` exactly; these are also the 10,273 cells with `mask_fraction < 0.3` and the 10,273 `agua` cells.

---

## 3. Self-tests and pytest (in `$S/run-A1`)

| Command | Result |
|---|---|
| `python mission_scoring.py selftest` | `selftest OK (5 comprobaciones)` (confirms baseline; 7 asserts actually run) |
| `python rover_preset.py --selftest` | `11/11 checks passed` (confirms baseline) |
| `python mission_filters.py selftest` / `check mission_filters.json --strict` | `selftest OK` / `OK: sin problemas.` |
| `python -m pytest tests -v -p no:cacheprovider` | **15 passed in 2.44 s**; 14 test functions, one parametrized x2 (confirms baseline). Runs offline because the PDS rows are cached. Side effect: rewrites `data/presets/presets.json` (1.2). |

### 3.1 What each test really asserts (`tests/test_pipeline.py`)

| Test (line) | What it actually checks |
|---|---|
| `test_slope_flat_and_ramp` (35) | slope 0 and roughness 0 on a flat DEM; slope 45 deg on a 1:1 ramp |
| `test_raw_has_all_bands_same_shape` (44) | synthetic local Moon/Earth (60x60) return the 7 band keys in order, all 60x60 |
| `test_raw_contains_injected_artifacts` (51) | synthetic Moon has a -32768 pixel; synthetic Earth temp has a value > 10000 |
| `test_clean_in_range_and_finite` [moon, earth] (56) | after cleaning, every band finite and inside the config valid range |
| `test_scale_fix_modis_dn` (65) | audit shows > 0 Earth temp pixels rescaled; cleaned Earth temp min > 180 K |
| `test_audit_counts_sentinels` (72) | Moon elevation `nodata_sentinel_px >= 12` |
| `test_geotiff_7_bands_same_grid` (77) | both TIFFs have 7 bands, res 500x500, "Kelvin" in temp band name, same width/height/res/CRS (not that the georeference is right) |
| `test_csv_dataframe_columns_match` (93) | Moon and Earth DataFrames same columns, 3600 rows, no NaN anywhere |
| `test_pds3_labels_parsed_correctly` (101) | cached `.lbl` files parse to the expected lines/samples/scale/ppd |
| `test_real_pds_tycho_window_and_cleaning` (118) | local 120x120 window at -43.3/-11.4 from cached LOLA/Diviner rows: elevation range -4000..-3000 / 1000..2000 m, rock in [0,1], temp in (46,160) K, SAR band all NaN / nodata |
| `test_analog_finder_ranking_and_weights` (152) | 20 rows, sorted, 0..100 %, `matched_lunar_zone` column exists; temp-only weights give different similarities; web bundle files written |
| `test_global_moon_and_earth_coverage` (175) | global 90x180 lat/lon extents reach beyond +-85 / +-175; Moon elevation spans < -5000 and > 5000 m |
| `test_verified_real_landmarks_moon_and_earth` (194) | values at 15 fixed cells of the two cached `.npz` grids (e.g. SPA < -5000 m, Tibet > 4500 m and < 282 K, oceans < 0); ranking keeps only land; mission keys exist and each mission has >= 3 optimal zones; labels Earth source `"real_NOAA"` (249) which is only a string |
| `test_mission_filters_json_and_cli_integration` (262) | `mission_filters.selftest()` passes, `rover_preset.selftest() == 0`, `validate(mission_filters.json, strict=True) == []` (only that sources are non-empty strings and weights sum to 1) |

### 3.2 Not tested at all
- **mission_scoring**: nothing (not imported by any test).
- **Hard filters on real data**: no test checks which cells pass any gate or the counts; only "at least 3 zones per mission".
- **Mission scores** (`analog_finder.py:243-323`): no value is checked.
- **Weights**: only "different weights -> different similarity"; the domain-to-feature mapping (`analog_finder.py:225-240`) and mission weights are untested.
- **Missing data**: no test feeds NaN to gates, `require_present`, or `on_missing`; the CSV test asserts there is *no* NaN at all.
- **IQR filter**: no test on which bands it touches (README claim is wrong, see 4).
- **Units**: only the "Kelvin" label and the MODIS DN rescale; nothing on K vs degC (`tmin_c`), kWh/m2/day, degrees vs fractions.
- **Coordinates**: no check that lat/lon map to the right cell (landmark test uses its own `rc()` with a hard-coded 2 deg cell, `:203-204`), no check of GeoTIFF georeferencing, no lon convention test.
- **Derived/modelled mission columns** (`harmonizer_cleaner.py:241-313`), `pds_reader.read_pds_global`, `main.py` CLI end-to-end, `--use-gee`, web page.

---

## 4. README (`tierra luna/README.md`) vs code

Default run = `python main.py` -> global mode 90x180 (`main.py:118-119`, `config.py:75-77`).

| # | Claim | README line | What the code does | Verdict |
|---|---|---|---|---|
| 1 | Identical spatial resolution, 500 m/px by default | 3, 71 | Default grid is global 90x180 = 2 deg x 2 deg cells (`harmonizer_cleaner.py:201-203`); `resolution_m` column is just the `--res` value (`:225`). GeoTIFF transform uses 500 m pixels (`:141-146`), i.e. a 90 km x 45 km EPSG:3857 rectangle for a global grid | **False** in default (global) mode; true only with `--local-window` |
| 2 | `--pds` reads LOLA `ldem_64` + Diviner `dgdr_ra_avg` and `dgdr_st_clc_0030` | 7 | In global mode `--pds` sets only `lola_dem = ldem_4` (`main.py:134-135`, local path `config.py:5-7, 23-27`) and then loads `data/cache/moon_global_pds.npz` (`lunar_extractor.py:61-84`). Diviner files are only used with `--local-window` (`main.py:136-139`) | **False** for the default/global run; true for `--pds --local-window` |
| 3 | Without `--pds`, synthetic generator with injected artifacts | 7 | `lunar_extractor.py:168-215` | True (note: it is a local crater scene stretched over the globe in global mode) |
| 4 | Earth uses the calibrated local Python model by default | 8, 80 | Global mode first loads `data/cache/earth_global_real.npz` (`earth_extractor.py:134-158`); the model (`:160-254`) runs only if that file is absent. The npz is **not** reproduced by the model (max abs diff elevation 9749 m, temp 1.457e4 K, in `$S/run-A1-nonpz`) | **Misleading**: committed Earth data come from an npz of undetermined origin |
| 5 | Verified over Tycho with real LOLA/Diviner | 14 | `test_real_pds_tycho_window_and_cleaning` passes offline from cached rows | True (local window only) |
| 6 | 12 of 12 tests passed / 12 automated tests | 16, 33 | 14 test functions, 15 test items, all pass | **False count** |
| 7 | 30 % maximum interpolation threshold | 28, 53 | `max_impute_frac=0.30`, `harmonizer_cleaner.py:33, 94-102` | True |
| 8 | Elevation: SRTM gap-filled with ASTER | 39 | Only in the GEE path (`earth_extractor.py:15-18`) | True only for `--use-gee` |
| 9 | `elevation_rel_m` = DEM minus local mean | 40 | Recomputed only when not global (`harmonizer_cleaner.py:120-128`). In the cached Earth npz, `elevation_m - elevation_rel_m` ranges 750.0..1047.4 (not a constant), so it is not "DEM minus a mean"; Moon npz: constant -518.97 = global mean | **False** for Earth in default mode |
| 10 | Slope = 2D gradient of DEM; roughness = 3x3 std | 41-42 | `lunar_extractor.py:14-22`; but pixel size passed is arbitrary in global code paths: Moon `eff_res_m * 0.08` (`:87-88`), Earth model `target_resolution_m * 0.45` = 225 m for 2 deg cells (`earth_extractor.py:201-203`). Default run uses npz values (method not determined) | Formula true; physical scale **not** as stated |
| 11 | Moon temp = Diviner; Earth temp = MODIS LST x 0.02 with ASTER fallback | 43 | Diviner only in local `--pds`; MODIS/ASTER only in GEE path (`earth_extractor.py:38-52`). Global non-npz Moon path models temp from latitude/elevation (`lunar_extractor.py:32-37`) | True only for local PDS / GEE paths |
| 12 | Moon rock = Diviner rock abundance; Earth = 1 - NDVI | 44 | Same split: local `--pds` / GEE only; global non-npz Moon rock is a formula (`lunar_extractor.py:39-46`) | Partly |
| 13 | Moon SAR = radar backscatter | 45 | No lunar radar product is referenced anywhere in code/config; local PDS path sets SAR to NaN (`lunar_extractor.py:131`); other paths model it (`:47`, `:201-203`) | **False** (never measured) |
| 14 | MODIS DN 7500..20000 x 0.02 | 49 | `harmonizer_cleaner.py:64-68`, Earth `temp_k` only | True |
| 15 | Sentinels -32768, -9999, 1e32, NaN, Inf | 50 | Plus -3.4028235e38 (`harmonizer_cleaner.py:13, 70-75`) | True |
| 16 | Physical ranges [20,420] K Moon, [180,360] K Earth | 51 | `config.py:102, 92` | True |
| 17 | **3.5 x IQR applied only to `temp_k`, `rock_or_bare_frac`, `sar_sigma0_db`** | 52 | `if valid_vals.size > 10 and band == "sar_sigma0_db"` (`harmonizer_cleaner.py:84`): **only SAR** | **False** (temp and rock are never IQR-filtered) |
| 18 | Slope/roughness/relative elevation recomputed on cleaned DEM | 53 | Only `if not config.global_mode` (`harmonizer_cleaner.py:120`) | **False** in default mode |
| 19 | Audit report every run | 55 | `main.py:167-169` | True |
| 20 | Usage `python main.py --pds --res 500 --size 120` | 61-62 | `--size` is used only with `--local-window` (`main.py:119`); both commands run the global grid | **Misleading** |
| 21 | GeoTIFFs EPSG:3857, 500 m/px | 71, 79 | `harmonizer_cleaner.py:141-148` | True as written, georeference wrong for global grid (row 1) |
| 22 | CSVs: coordinates + 7 variables | 72 | Also 12 extra columns, all formula-generated (`harmonizer_cleaner.py:302-313`) | Incomplete |
| 23 | Output list | 69-75 | Also writes `optimal_mission_zones.csv` (`analog_finder.py:647-649`) and `analog_web_data.json` (`:676-678`); `earth_mission_filtered.csv` is not written by `main.py` | Incomplete |
| 24 | lat/lon are local spherical approximations | 79 | True only in local mode (`harmonizer_cleaner.py:204-215`); global mode gives exact cell centres (`:201-203`) | Partly |
| 25 | Web synced with `analog_finder.py` | 17 | Committed `web/analog_data.js` payload == `output_py/analog_web_data.json` (parsed and compared) | True |
| 26 | Structure table | 22-33 | Omits `mission_filters.py/.json`, `rover_preset.py`, `data/presets/presets.json`, `data/cache/*.npz` | Incomplete |

---

## 5. End to end

### 5.1 `main.py` options (`main.py:16-113`)
`--res` (500), `--rows` (90), `--cols` (180), `--local-window`, `--size` (120, local only), `--earth-lat/--earth-lon/--moon-lat/--moon-lon` (0, local only), `--pds`, `--lola-dem`, `--diviner-temp`, `--diviner-rock`, `--use-gee`, `--gee-project`, `--out-dir` (output_py). Web bundle always goes to `./web` relative to the working directory (`main.py:207`). Source labels: `moon_source = "real_PDS"` whenever a LOLA path is set, `earth_source = "synthetic_or_gee"` / `"global_model"` (`main.py:140-141`); they do not say whether the npz caches were used or whether GEE actually succeeded (GEE failure falls back silently, `earth_extractor.py:114-119`).

### 5.2 Runs (each about 2.8 s wall time)
- `$S/run-A1-default`: `python main.py` -> rc 0.
- `$S/run-A1-pds`: `python main.py --pds` -> rc 0. Both offline.
- Comparison script `$S/run-A1/_a1/cmp.py` (rows, column sets, max abs diff per numeric column, differing cells for text columns, per-band TIFF diff).

**Committed outputs are reproduced by `python main.py --pds`, not by the default `python main.py`.** The committed Moon CSV has `source = real_PDS` in all 16,200 rows.

| Output | `--pds` vs committed | default vs committed |
|---|---|---|
| `moon_lola_diviner_clean.csv` (16,200 rows, 28 cols) | equal content; bytes differ only by CRLF vs LF | Moon fully different: max abs diff elevation 9286.9 m, temp 202.0 K, slope 30.4 deg, roughness 3053 m; `source` 16,200 cells differ; `permafrost_class` 4,680, `thermal_inertia_class` 894 cells differ |
| `earth_srtm_modis_aster_clean.csv` | equal (CRLF only) | equal (CRLF only) |
| `earth_moon_harmonized_clean.csv` (32,400) | equal (CRLF only) | Moon half differs as above |
| `data_cleaning_audit_report.csv` (14) | equal (CRLF only) | differs (e.g. `nodata_sentinel_px` +20, `clean_max` up to 8978.6) |
| `moon_...tif`, `earth_...tif` | sha256 identical | Moon TIFF differs (band max diffs as CSV); Earth identical |
| `analog_ranking.csv` (100 rows) | same 100 cells, same values; only `rank` differs by <= 2 among tied `similarity_pct` | different: 87 `earth_region`, 31 `matched_lunar_zone` cells differ; similarity up to 3.05 |
| `optimal_mission_zones.csv` (30) | equal (CRLF only) | different (26 regions differ, mission_score up to 19.46) |
| `analog_web_data.json` / `web/analog_data.js` | only `/rover_preset/preset/frozen_at` differs (timestamp written at run time) | 6 top-level keys differ |
| `earth_mission_filtered.csv` | not written by `main.py` | not written by `main.py` |

`earth_mission_filtered.csv`: reproduced by `python mission_filters.py apply mission_filters.json output_py/earth_srtm_modis_aster_clean.csv --missions rover,solar,thermal,ice --out ...` (pass counts rover 5297, solar 5198, thermal 3337, ice 3023, all 2114; 0 differing cells), but the committed file has 30 columns without `rain_mm_day, wind_max_ms, tmin_c`, so it was made from an earlier version of the Earth CSV than the one committed. It is stale relative to the code.

### 5.3 What the committed results actually rest on (data levels)
With the npz caches present, the committed outputs depend entirely on two files that **no code in the repository produces** (grep for the file names: only the loaders `earth_extractor.py:135`, `lunar_extractor.py:64`; no `np.savez` anywhere):

| Data | Code path | Level (by what the code does) |
|---|---|---|
| Moon 7 bands (`--pds`, global) | `moon_global_pds.npz` | **Not determined.** Elevation correlates r = 0.940 with the `ldem_4` code path (`read_pds_global`) at zero shift, but max abs diff 5224 m, median 313 m, so it is not that code's output. Temp (43.5..110.4 K), rock (0.0015..0.046) and SAR cannot be traced to any product read by the code; SAR cannot be MEASURED (no lunar radar source anywhere). |
| Moon 7 bands (no npz) | `ldem_4.img` resampled + formulas | elevation MEASURED (LOLA, bilinear zoom), slope/roughness DERIVED with an arbitrary 0.08 pixel factor, temp/rock/SAR MODELLED (`lunar_extractor.py:25-48`) |
| Moon, default `python main.py` | synthetic | MODELLED |
| Earth 7 bands (default and `--pds`) | `earth_global_real.npz` (has an extra `land_mask`, 5927 land cells; 10,273 cells exactly -250.0 m) | **Not determined** (no producer; name says "real" but nothing shows which product). |
| Earth 7 bands (no npz) | `_build_global_earth_grid` | MODELLED (Gaussian "belts" + noise, `earth_extractor.py:160-254`) |
| `mask_fraction`, `irradiance_kwh_m2_day`, `sun_elev_max_deg`, `sun_low_frac_0_5deg`, `lst_diurnal_amp_k`, `thermal_inertia_class`, `permafrost_class`, `rain_mm_day`, `wind_max_ms`, `tmin_c` | `harmonizer_cleaner.py:241-313` | **MODELLED** (closed-form functions of latitude, elevation, temp, rock fraction) on both bodies |
| `slope_300m_deg`, `rough_300m_m` | `harmonizer_cleaner.py:303-304` | Copies of `slope_deg` / `roughness_m` of the 2 deg grid; the "300m" baseline in the name is not computed anywhere |

Consequence: every mission gate and mission score (old and new system) runs on MODELLED columns, and the similarity ranking runs on two npz grids of undetermined origin. The author already flags `tmin_c` and the derived variables as model estimates (`Instruciones...:36`).

### 5.4 `--use-gee` (not run; no credentials)
Would need: `earthengine-api` (in `requirements.txt`), prior `ee.Authenticate()`, a Google Cloud project with Earth Engine enabled passed as `--gee-project` (`earth_extractor.py:88-93`), network access to Earth Engine. Code-level problem regardless of credentials: the ROI is `Point(earth_center_lon, earth_center_lat).buffer(cols * res / 2).bounds()` (`earth_extractor.py:11-13`); in the default global mode that is a 45 km buffer around 0 deg, 0 deg (Gulf of Guinea, ocean), which is then resized to 90x180 (`:112`) and treated as the global Earth grid. Also the run label stays `synthetic_or_gee` whether GEE worked or not (`main.py:141`). `gee_earth_grid_export.js:1-4` targets a separate 30 km window at 39.139605, -0.265196 (near Valencia), not the global grid.

---

## 6. `rover_preset.py` as committed

| Question | Answer (evidence) |
|---|---|
| Version string | **None.** `grep -n "version\|VERSION" rover_preset.py` returns nothing. Cannot be told apart from "v3" without the local zip, which is not available here. |
| References `rover_integration.py`? | **No** (grep: 0 hits). |
| References a benchmark CSV? | **No** (grep for `benchmark` and `.csv`: 0 hits). Only file I/O is `presets.json` (`:464-479`) and optional JSON inputs (`:482-483`). |
| Self-test (`:489-559`, 11 checks) | Earth-twin mass 440 kg x 1.62/9.81 = 72.66 kg; Froude factors Moon 2.46, Mars 1.62; tip-over of a 1.30 m square at CG 0.6 m = atan(0.65/0.6) (= 47.29 deg); CG outside footprint unstable; tip-over independent of g; mass-budget CG; freeze blocked while sources illustrative; slope gate above tip-over rejected; other presets kept; frozen preset not overwritten without refreeze. It tests arithmetic and guards, not any rover value. |
| Status of the rover numbers | `ROVER_SPEC` (`:71-86`): only `mass_kg` (440, "arXiv 2405.11001") and `n_contacts` are `OK`; `cg_height_m`, `wheelbase_m`, `track_m`, contact patch, `max_speed_mps`, `max_operational_slope_deg` (15) are `ESTIMADO`/`VERIFICAR`; `ground_clearance_m` is `MISSING`. `PRESET_CONFIG` weights, tolerances and workable-day limits are `ILUSTRATIVO` (`:93-111`). |
| How the pipeline uses it | `analog_finder.py:35-43` builds the preset with `freeze=True, allow_unverified=True`, i.e. bypasses the module's own freeze guard on every run, and writes it to `presets.json` (`:53`). |
| Mis-sourcing downstream | `mission_filters.json:12` cites the 15 deg slope as "NASA VIPER operational slope limit", and `:24, :29, :36, :49` cite tolerances/weights/workable days as "Robotics 1 rover_preset.py" values; in `rover_preset.py` the same numbers are `ESTIMADO`/`ILUSTRATIVO`. `mission_scoring.json:15-16, 24-27` copies these sources unchanged. `validate(..., strict=True)` passes because it only checks that `source` is non-empty (`mission_filters.py:130`). |
