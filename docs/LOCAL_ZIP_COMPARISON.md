# Team local zip vs main: comparison, rover v3 integration and rover ranking check

Stars Beside You, NASA Space Apps Challenge 2026. Written 2026-11-14 on branch `final-integration`.

- Zip: `STARS-BESIDE-YOU-main/tierra luna` as supplied by the team lead (unpacked outside the repository).
- Main: a copy of the repository's `main` branch, `tierra luna/` folder.
- Branch: `/home/user/stars-beside-you/tierra luna` (working tree).

Nothing in this report changes a variable, threshold or weight of `mission_scoring.json` or `mission_filters.json`.

---

## 1. File-by-file comparison (sha256)

Paths are relative to `tierra luna/`. "Zip" and "Main" columns are the full sha256 of each copy.

| File | Status | Zip sha256 | Main sha256 |
|---|---|---|---|
| `README.md` | identical | `37ebaed0a67905ad561ba1c9cdabd8ef87c49d3b07b7e7c097aeabbb3580d819` | `37ebaed0a67905ad561ba1c9cdabd8ef87c49d3b07b7e7c097aeabbb3580d819` |
| `analog_finder.py` | changed | `cdd2494356340d6afa967fea6a32a1823d1b2d861600fbf46cf693e257be3819` | `617926d29edfa9fd1eae81cf79fbc757138d420a554ccfe066e7c1b0ede2f326` |
| `config.py` | identical | `6d54c58bee5d3737983798202516d38f0da1db6c4bb985229371d0892934dc44` | same |
| `data/cache/dgdr_ra_avg_cyl_032_img.img.f9b0cef3.rows_3272_3339.bin` | identical | `fab2c182bb176656fe29fd2b2fcd7c1afb6271645510fb88c79dc6f2bdb84e7d` | same |
| `data/cache/dgdr_ra_avg_cyl_032_img.lbl` | identical | `2c84b7d76764f503baf415ec780abfc5da55d9724030cf7587a09b868c5a0206` | same |
| `data/cache/dgdr_st_avg_cyl_032_img.img.9b0e1eff.rows_3272_3339.bin` | identical | `7d1f4e3c9d020d693fc6b8613aaa7ec087857c3f3e914fa705ca5dfc78d5321b` | same |
| `data/cache/dgdr_st_avg_cyl_032_img.lbl` | identical | `364b41712088ddd9be0c1724e984a22423dd5356a7c98a6a47e42275644d5e1a` | same |
| `data/cache/dgdr_st_clc_cyl_0030_032_img.img.42660e4d.rows_3272_3339.bin` | identical | `bca600942d847c170c2a342251aa2dc4f4f058783823b416dc4b80476fbfc001` | same |
| `data/cache/dgdr_st_clc_cyl_0030_032_img.lbl` | identical | `731641bb485e9e0076cb2cd57c68246c35225d2cc423ff17391cb0e9476f3311` | same |
| `data/cache/earth_global_real.npz` | identical | `2896d687fc8c7639284e26cbb9401ff9e2d1f85fd934fdedf97cde3123dc2e68` | same |
| `data/cache/ldac_4.lbl` | identical | `f073a1967b38bc7b2620e173be841f4f7724769038d4c097b68ffc2c6213000d` | same |
| `data/cache/ldem_4.img` | identical | `c04632eba6449af49e3108ed7c25b3b1c450600abd3690df4fc815853a1af476` | same |
| `data/cache/ldem_4.lbl` | identical | `b5a197b4d417e3b5e0e84f8fe15f9a1d2203b8eb5d7213236c0ffbc86e940cc6` | same |
| `data/cache/ldem_64.img.8894cdd5.rows_8466_8596.bin` | identical | `204bf8e05c13a38f8c170a789a18ac0d1fb96a282e81f6c83cffc7bebbd2d892` | same |
| `data/cache/ldem_64.lbl` | identical | `4e7a94c76c716a147b21ccf07669d004246b0d1b017b7d63d50befaa1a34142d` | same |
| `data/cache/moon_global_pds.npz` | identical | `4143fce1673a3edef4548c7d22c732a37b6bf4f6b88ff5cd090ca7bedecb742f` | same |
| `data/presets/presets.json` | **missing from zip** | - | `87a52b48b6c25d1b24aaff0f1499fb3c5862e7f95acd9e04e8cf27f8980b6b55` |
| `earth_extractor.py` | identical | `c2931962a13e6b50ece67a6e60bcc387c6c9814a1f2848a1664e5c57a39f9011` | same |
| `gee_earth_grid_export.js` | identical | `1458dca16722f9d2d73c5b15a60a42289837b10c42fe00fe04f3daf503752723` | same |
| `harmonizer_cleaner.py` | changed | `e04a6cf6e698d97140066c78a334f6bfe7b8b60fad9d3213aee4492d65dfb46f` | `078c065e48db8533bf8d11083a7780f772ab7503eaddc89279ec1ce6beafc554` |
| `lunar_extractor.py` | identical | `4d2ef959b63d74e671e23cf1180880f6eea6310c1017b923cf6d2ce85a51f491` | same |
| `main.py` | identical | `177cc22758ae303fa8a51b2b3696a8127c3081e24c930f5eb5b58ffa57c68aa2` | same |
| `mission_filters.json` | changed | `b337b39c008ed1b5a5764605425617b864c4a5a97f115d3d6e86c1473970568d` | `635de033ff0a6d6f1b229a6082063354e88c8f4eb18674e014930df5c7235e75` |
| `mission_filters.py` | identical | `9f3af96d77b46d9f37d85ee661b23c580bcde2dab2605d5da9fd15d1d1ab8dc4` | same |
| `output_py/analog_ranking.csv` | changed | `45b9883f5f836c57011f34e908ea93548b98b1607e3a84922b7f62c269dd25ce` | `a63bceb1fb802c9948c1d5483be4b079b0a0dc07f977bff68eef2042073b7a01` |
| `output_py/analog_web_data.json` | changed | `734b8a75895092322a28f8039ca345be03d0cdb344872cb975621a41e247ff50` | `404fb91c2db77f8ac2730e568e50e1ed11266a0a04aee1dbeed4de7e839a90f1` |
| `output_py/data_cleaning_audit_report.csv` | changed | `2323e1dc7f4893076de28d68e72d4edb843ef91af8eb1519b047f44d42d0c96a` | `7cf25882f1786c045759f82d3f04cad8ad8ae1f2689b556adea2979df5ed0849` |
| `output_py/earth_mission_filtered.csv` | identical | `0fe9f90d0b4f6958e178402f9b7e451bbcc10303c69d793aa69362a4f63cd40b` | same |
| `output_py/earth_moon_harmonized_clean.csv` | changed | `45e6faccec1ba7ebeea402ff5a9feb9bd167584e9814cf36f31a4766d9771c58` | `572b6ca64950ada9c90a291232dd34f33ec4d85b4a8136c030232badb5124064` |
| `output_py/earth_srtm_modis_aster_clean.csv` | changed | `f69d93b1c155382faf1f22b8bec978cd0631300c4ff0f88a46bb9024462a74d7` | `01202c8f9a27fb4d54e388c29085f87df15fae511c587496a0ee56bd7fe46c0b` |
| `output_py/earth_srtm_modis_aster_clean.tif` | changed | `19e04aebf81d53403b5f7389965694d7bc42db254f64b5aabc27bbbce4304f4c` | `25ef7c72e64517cbca967c501bb59c019fc2a5901943213e83bd5dc4ad4c4841` |
| `output_py/moon_lola_diviner_clean.csv` | changed | `30149154ef211510dff0d7c40b0fbe7102f1d7646e2db26da40b65065cda0ce2` | `c3046b29b125c58b1da28df88e5c2fb7b94c2f6da6fa6a5e58c0173bb48b487a` |
| `output_py/moon_lola_diviner_clean.tif` | changed | `ec376edc0da9125d088dc0f2798f60c0d08414f20a1fe749139a5dfa42cd784f` | `ad7b834a24aab574f9d7ed7fc837eab004f5cc430c6fad354eab88067e6ce44f` |
| `output_py/optimal_mission_zones.csv` | changed | `ed8bc53920cd31901a0cb773455f34b47f5f10c4d8ba8afd12d54feabe9c50cb` | `14c18e35c16a5ef7adc1283c32e78435917b3a33407c71a12cd4b1b30f46dd28` |
| `pds_reader.py` | identical | `57fad7c67918b0495d9e82f43b2be6a6332b4f0c1eef94a2212b89c402a1482a` | same |
| `requirements.txt` | identical | `8546602f0ddd80beb715989dd3d8e77a84784868c5f81968830a02be3ca28aa6` | same |
| `rover_integration.py` | **new in zip** | `afcd1666035d0118d23199bd224d3e11eccc3b26d2091a5cb04afb3909c10cdc` | - |
| `rover_preset.py` | changed (version 3) | `e1a89a9265fdc113cefe1f7e87dc7718ee71bb6153192ed49ddd45f43759f4eb` | `9c8a1c7dca3a0dcfe1963344849c6e4dd61889b8aa46bda6016f153ba1e28a91` |
| `tests/test_pipeline.py` | identical | `bdb2a248a46cb7a14ee28a13cc6c2d54b25bcc8995e1e5a38dd5f36af0f1e500` | same |
| `web/analog_data.js` | changed | `7693de324f8a3459926a4cb2cc4e14805b667b671b0531f653f56974a27add94` | `e8e66a5d00a4e273d0f1217c43c3bf967e4169323303028f8d508c9f50c9e037` |
| `web/index.html` | changed | `581c8fd787db50bbad276894249ab5cd501a0b18ab20d58d0db2aaa320e4f551` | `2f8accf1955e6d34edc16b7957cf4c9d2e93f773ce605e508c9aee6821600bb2` |

Not listed: 23 cache files (`__pycache__/*.pyc`, `.pytest_cache/*`). The 7 `cpython-312` `.pyc` files are identical; the zip adds `cpython-313` `.pyc` files and a `.pytest_cache/`, i.e. the zip was run locally with Python 3.13. None of them is source.

`mission_scoring.py` and `mission_scoring.json` are not in the zip, but they are not in `main` either: they exist only on this branch, so the zip cannot conflict with them.

`output_py/earth_mission_filtered.csv` is identical, but no script in either tree writes it (`grep earth_mission_filtered *.py` finds nothing), so it is a stale file left over from an earlier version.

---

## 2. Changed code and configuration files

### 2.1 `analog_finder.py` (zip vs main: three changes)

**(a) Rover preset is no longer refrozen on every run.** Main lines 35-56 build the preset with `freeze=True` and call `merge_into_presets(..., refreeze=True)` every time, which rewrites `data/presets/presets.json` with a new `frozen_at`. The zip (lines 35-67) instead reads `data/presets/presets.json` and uses a stored `rover` preset only if it has `frozen_at`; otherwise it builds with `freeze=False` and adds `"preset_frozen": bool(frozen)` to the bundle. Its comment:

```
    # [AI-assisted] Freezing is no longer redone on every run (the plan asks
    # to freeze BEFORE looking at results). If data/presets/presets.json holds
    # a frozen `rover` preset, it is used as is. Otherwise an unfrozen preset
    # is built. Freeze explicitly with:
    #   python rover_preset.py --presets data/presets/presets.json --author "..." --freeze
```

and it removes:

```
-    try:
-        merge_into_presets(Path(PRESETS_JSON_PATH), preset, name="rover", refreeze=True)
-    except Exception:
-        pass
```

Branch: does **not** have it (branch lines 35-56 are as main). Needed by `rover_integration`? No: `rebuild_rover_bundle` only checks `previous_bundle.get("preset_frozen")`; with the branch bundle that key is absent, so it rebuilds an unfrozen preset and runs normally. **Not ported** (see section 8). Consequence to know: on the branch a pipeline run still writes a "frozen" v3 preset into `presets.json` while the web bundle's `rover_preset.preset` is the unfrozen rebuild from `rover_integration` (`frozen_at: null`). The tests are not affected (`tests/conftest.py` restores `presets.json` after the session).

**(b) Rover lunar target: Shackleton region instead of Tycho (PORTED, team lead's decision).** In `compute_mission_optimality_scores`:

Main, line 259:
```
259        "rover": rocky_target,
```
Zip, lines 270-272:
```
270        # [AI-assisted] Plan decision 2: the lunar target is the Shackleton
271        # region (the only Moon Base site NASA has named), not Tycho.
272        "rover": polar_target,
```
Branch now, lines 259-261 (identical text to the zip):
```
259        # [AI-assisted] Plan decision 2: the lunar target is the Shackleton
260        # region (the only Moon Base site NASA has named), not Tycho.
261        "rover": polar_target,
```
`polar_target` is the lunar zone `"South Pole PSR & Shackleton Rim (75°S–90°S)"` (branch lines 251-253); `rocky_target` (`"Tycho & Southern Rocky Craters (35°S–55°S, 30°W–0°)"`) is now unused, as in the zip. Effect: the rover similarity part (`analog_sim`, 0.65 of the legacy `score_rover`) and the rover `t_slope`/`t_rough` targets are now taken from the polar zone. In a scratch run of the branch export on the committed tables, the six optimal rover zones became (-85,-141), (-81,155), (-81,-37), (-73,67), (81,-85), (-69,117), i.e. polar Earth cells. The hard filters are not touched by this change.

**(c) Hook (PORTED).** Zip lines 599-600, branch lines 619-620, inside `export_web_bundle`, right after `compute_analog_ranking`:
```
    from rover_integration import apply_rover_extras
    meta = apply_rover_extras(earth_scored, meta)
```
The branch's own changes (hard filters from `mission_scoring.json`, NaN score for a failed gate, `_apply_mission_scoring_gates`) are kept.

### 2.2 `harmonizer_cleaner.py` (zip vs main: +48 lines)

The zip adds `BODY_RADIUS_M`, `global_cell_size_m(h, w, body)` and `compute_slope_and_roughness_global(dem_m, body)`, and in global mode:

```
    if config.global_mode:
        # [AI-assisted] Global grid: recompute slope with the true cell size
        # (the extractors use a fixed pixel size that inflates slopes).
        slope_g, rough_g = compute_slope_and_roughness_global(cleaned["elevation_m"], body)
        cleaned["slope_deg"] = np.clip(slope_g, 0.0, 90.0)
        cleaned["roughness_m"] = np.clip(rough_g, 0.0, valid_ranges["roughness_m"][1])
```
and new output columns `relief_cell_km`, `relief_cell_ew_km`, `slope_cell_deg`, `rough_cell_m` (comment: "In global mode the columns named *_300m_* hold cell-scale values (kept for compatibility)").

What it does: on the 2-degree global grid, slope is recomputed with the real size of a cell (about 222 km north-south on Earth, about 61 km on the Moon) instead of the fixed 500 m pixel. This makes slopes far smaller: in the zip's table Earth `slope_300m_deg` ranges 0.0 to 1.529 deg, against 0.01 to 37.168 deg in main/branch. Roughness keeps the 3x3 standard deviation definition.

Branch: does not have it. Needed by `rover_integration`? No. **Not ported.** It conflicts in effect with the branch filters: with zip slopes (max 1.53 deg) almost every Earth cell would pass the 15 deg maximum, and most would fail the 0.5 deg minimum of `mission_scoring.json`.

### 2.3 `mission_filters.json`

The 294 changed lines are mostly line endings: the zip file uses CRLF (146 of 146 lines end in `\r\n`), main uses LF, so every line differs textually. Parsed as JSON, exactly six values differ, all in `missions.rover`:

| Key | Main (= branch) | Zip |
|---|---|---|
| `gates.slope_300m_deg.min` | `0.5` | `null` |
| `gates.slope_300m_deg.source` | `rover.max_operational_slope_deg: NASA VIPER operational slope limit (15 deg < 47.29 deg static tip-over, rover_preset.py)` | `ESTIMADO: VIPER approximation in rover_preset.py (max_operational_slope_deg), pending verification. At the 2-degree grid this gate is applied to cell-scale slope (~220 km), not 300 m.` |
| `gates.rough_300m_m.min` | `5.0` | `null` |
| `gates.rough_300m_m.source` | `LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)` | `PENDIENTE: confirm the source of the 650 m upper limit (Robotics 1). Applied to cell-scale roughness (3x3 std of elevation), not 300 m RMS.` |
| `frozen_at` | `2026-11-14T16:30:00+00:00` | `2026-11-14T19:41:16+00:00` |
| `author` | `Robotics 1 - Mobility Team` | `Robótica 1` |

All other values (slope max 15.0, roughness max 650.0, tolerances 5.0 / 10.0, weights, solar/thermal/ice blocks, `mask_min`) are equal. Branch: unchanged and stays unchanged (team lead's rule). **Not ported.**

### 2.4 `web/index.html` (zip vs main: +15 / 2 changed lines)

The zip adds two helpers, `cellKm()` (`Math.round((Math.PI * 6371.0) / rows)`, the real north-south size of a cell) and `gateRange(col, unit)` (reads the rover gate min/max from `ANALOG_DATA.mission_filters` instead of hard-coding them), and changes two labels: main line 1407 `[0.5–18°] | rough_300m = ... [5–650 m]` becomes `cell slope (~${cellKm()} km) ... [${gateRange("slope_300m_deg", "°")}] | cell roughness ... [${gateRange("rough_300m_m", " m")}]`, and main line 1615 `Relief & Rover Gate:` becomes `Relief & Rover Gate (cell scale ~${cellKm()} km):`. Note that main's label says `0.5–18°` while every filter file says 15: the zip's version removes that hard-coded mismatch. Branch: not present; not needed by `rover_integration`. **Not ported** (listed in section 8).

### 2.5 `rover_preset.py` and `rover_integration.py`

Described in full in sections 4 and 5. Branch now holds `rover_integration.py` byte for byte from the zip (sha256 `afcd1666...10cdc`) and `rover_preset.py` v3 with exactly two lines changed after copying (lines 167-168, VIPER sources, section 6); its sha256 is `191fd46f0c387e6bb5935ac4026b9331faf05cfe7a8b6235ee89c1262408dc21`.

### 2.6 `data/presets/presets.json` (missing from the zip)

Kept as committed (sha256 `87a52b48...6b55`): v3 does not need it regenerated. It is the version 1 output (no `excluded_features`, no `wear_test_flags`; slope gate source `rover.max_operational_slope_deg: ESTIMADO - replace from project DB`). Because the branch still has main's `get_rover_preset_bundle` (2.1 a), the next real pipeline run will rewrite it with the v3 preset (new keys `excluded_features`, `wear_test_flags`, `baseline`, version 3 transfer card rows and notes, the new slope and speed sources, a shorter `unverified` list). That happens at run time; it was not done here.

---

## 3. Data: which command produced which outputs

`main.py` (identical in zip and main) sets the Moon source label from its arguments, line 140:
```
    moon_source = "real_PDS" if args.lola_dem else "synthetic"
```
`--pds` fills `args.lola_dem` with the global LOLA `ldem_4` URL in global mode; without `--pds` (and without `--lola-dem`) the Moon is the synthetic generator in `lunar_extractor.py` ("Generating synthetic LRO LOLA + Diviner grid ..."). The Earth label is `global_model` unless `--use-gee`.

Measured on `output_py/earth_moon_harmonized_clean.csv` (32,400 rows each):

| Fact (Moon rows, 16,200) | Zip | Repository (main = branch, committed) |
|---|---|---|
| `source` column | `synthetic` | `real_PDS` |
| `elevation_m` range | -3,625.5 to -676.7 m | -7,609.7 to 8,301.9 m |
| `permafrost_class` | `ninguno` in all 16,200 | `ninguno` 11,520, `discontinuo` 2,922, `continuo` 1,758 |
| `thermal_inertia_class` | `suelo` 15,306, `arena` 894 | `suelo` 16,200 |
| `tmin_c` range | -161.33 to -45.08 C | -251.78 to -219.83 C |
| Earth `source` | `global_model` | `global_model` |
| Earth `slope_300m_deg` range | 0.0 to 1.529 deg | 0.01 to 37.168 deg |

Conclusion: the zip's outputs come from `python main.py` with no `--pds` (synthetic Moon, Earth global model), run with the zip's own `harmonizer_cleaner.py` (true-cell-size slopes); the repository's committed outputs come from `python main.py --pds` (real LOLA Moon) with main's harmonizer (fixed-pixel slopes). The zip's web bundle was also produced with the hook active: its `rover_preset` has `preset_frozen: false` and a `ranking_check` with `coordinates_from: "APPROX_SITE_COORDS (replace with the benchmark CSV)"`, `ok: false`, problems "Concordia ... scores as high as the mobility analogs" and "Rio Tinto ... scores as high as the mobility analogs".

What this means for anyone comparing numbers: **no number in the zip's `output_py/` or `web/analog_data.js` can be compared with the repository's.** The Moon is a different (synthetic) Moon, the Earth slopes and roughness use a different definition, and the mission filters differ (2.3). Similarity scores, pass counts (zip rover pass 5,354; failures only on roughness), optimal zones and rankings all differ for those reasons, not because of any change in the scoring logic. The repository's data outputs were not replaced.

---

## 4. `rover_preset.py` version 3

Self-contained, standard library only. Version 3 header: "nothing from versions 1 and 2 was removed".

### 4.1 Rover specification (`ROVER_SPEC`, name "VIPER (approximation)", locomotion "wheels")

As in the zip, then the branch value where it was changed (section 6).

| Field | Value | Unit | Source (zip) | Status (zip) | Branch |
|---|---|---|---|---|---|
| `mass_kg` | 440 | kg | Phase-1 plan (VIPER, arXiv 2405.11001) | OK | unchanged |
| `cg_height_m` | 0.60 | m | ESTIMADO - replace from project DB | VERIFICAR | unchanged (no official source) |
| `cg_x_m` | 0.0 | m | assumed centred | VERIFICAR | unchanged (no official source) |
| `cg_y_m` | 0.0 | m | assumed centred | VERIFICAR | unchanged (no official source) |
| `wheelbase_m` | 1.30 | m | ESTIMADO from ~1.5 m body length - replace from project DB | VERIFICAR | unchanged (no official source) |
| `track_m` | 1.30 | m | ESTIMADO from ~1.5 m body width - replace from project DB | VERIFICAR | unchanged (no official source) |
| `n_contacts` | 4 | - | four wheels | OK | unchanged |
| `contact_patch_length_m` | 0.10 | m | ESTIMADO - replace from project DB | VERIFICAR | unchanged (no official source) |
| `contact_patch_width_m` | 0.20 | m | ESTIMADO wheel width - replace from project DB | VERIFICAR | unchanged (official wheel width proposed, section 6) |
| `ground_clearance_m` | None | m | "" | MISSING | unchanged (official range proposed, section 6) |
| `max_speed_mps` | 0.20 | m/s | ESTIMADO (~0.8 km/h) - replace from project DB | VERIFICAR | **source and status replaced** (value unchanged) |
| `max_operational_slope_deg` | 15 | deg | ESTIMADO - replace from project DB | VERIFICAR | **source and status replaced** (value unchanged) |

Gravity (`DEFAULT_GRAVITY`, "NASA Planetary Fact Sheet values used in the phase-1 plan"): earth 9.81, moon 1.62, mars 3.73 m/s^2.

### 4.2 Preset configuration (`PRESET_CONFIG`)

- **Weights by sector** (all marked illustrative): relief 0.35 ("ILUSTRATIVO - plan sec. 3 order only (relief and material weigh more)"), surface_material 0.30 ("ILUSTRATIVO - plan sec. 3 order only"), thermal_regime 0.10, light_and_sky 0.10, water_ice_aridity 0.15 ("ILUSTRATIVO"). Normalised to sum 1 by the builder. Same numbers as `mission_scoring.json` `weights` (relieve 0.35, material 0.3, termico 0.1, luz 0.1, agua 0.15).
- **Baseline**: `"auto"` (300m if `slope_300m_deg` is in the Earth columns, else 5km if `slope_5km_deg` is, else 300m with a warning); can be forced with `--baseline`.
- **Common tolerance**: `thermal_inertia_class`, type class, classes `dust, sand, coarse_or_crust, rock`, same 1.0, neighbour 0.5, far 0 ("ILUSTRATIVO - matrix values proposed in plan sec. 3; set by Robotics 1"). TES thresholds 150 / 350 / 600.
- **Tolerances by baseline**: 300m: `slope_300m_deg` scale 5.0 deg, `rough_300m_m` scale 10.0 m (both "ILUSTRATIVO - set by Robotics 1"); 5km: `slope_5km_deg` scale 2.0 deg ("5 km slopes are much gentler"), `rough_5km_m` scale 30.0 m ("check EarthEnv roughness definition, contract asks RMS"). The version 1 key `tolerances` (300 m values) is kept because `analog_finder.py` reads it.
- **Hard filters (gates by baseline)**: 300m: `slope_300m_deg` min None, max from `max_operational_slope_deg` (15); `rough_300m_m` min None, max None, "no gate until Robotics 1 sets one". 5km: `slope_5km_deg` min None, max from `max_operational_slope_deg`, note "a 5 km mean hides local slopes even more; weak gate"; `rough_5km_m` no gate.
- **p90 rule** (`gate_prefer_p90: True`): if a column named like `slope_300m_p90_deg` / `slope_5km_p90_deg` exists, the slope gate is moved onto it ("p90 of the cell (steepest stretches)"); otherwise it stays on the median and the builder records "gate uses the median slope (permissive)". Neither the committed legacy table nor the real 1-degree table has a column with that exact name (the real table has `slope_p90_deg` / `slope_iso_p90_deg`), so in both cases v3 falls back to the median.
- A slope gate whose max is not below the static tip-over angle raises `PresetError`.
- **Roughness**: only a tolerance (scale 10 m at 300 m, 30 m at 5 km); no roughness gate in v3.
- **Workable days**: rain_mm_max 1, wind_max_ms_max 12, tmin_c_min -10 ("ILUSTRATIVO - phase-1 plan, model 1 defaults").
- Freezing is refused while any item is unverified unless `--allow-unverified`; a frozen preset in `presets.json` is replaced only with `--refreeze` (recorded as `refrozen_from`).

### 4.3 Deliberately left out of the score (`EXCLUDED_FEATURES`)

- `rock_abundance`: "Diviner rock abundance only reaches 60 S; the Shackleton region (84-90 S) has no comparable rock data, so rock density cannot be compared at the lunar target." Source: "Phase-1 plan, section 4 (limits found in testing)".
- `abrasivity`: "Abrasiveness depends on grain shape and hardness; no global orbital layer measures it at 300 m or 5 km. Handled as a level C row of the Test Transfer Card and as a site flag (wear_test_hint), never as a score." Source: "No dataset in the phase-1 data inventory".

### 4.4 Test Transfer Card (values from the current spec)

| Level | Item | Value | Note in code |
|---|---|---|---|
| A | Static tip-over angle (min) | 47.29 deg (all four edges) | independent of gravity |
| A | Weight on tool, Moon / Mars / Earth | 712.8 / 1641.2 / 4316.4 N | m * g; an Earth test pushes harder than on the target |
| A | Earth twin mass for equal ground load, Moon / Mars | 72.7 / 167.3 kg | m * g_target / g_earth |
| A | Earth test speed (Froude), Moon / Mars | 0.492 / 0.324 m/s | v_target * sqrt(g_earth / g_target) |
| A | Ground clearance | no data | rover property; "Rock density is not scored: no rock data at the lunar south pole (Diviner stops at 60 S)" |
| B | Energy per km | - | range only, about +/-30 % (Apollo 15 LRV, Costes et al. 1972) |
| B | Slip | - | granular scaling, cohesionless sand only; a lightened rover at 1 g is optimistic (arXiv 2405.11001) |
| C | Traction and sinkage on target, thermal control, dust adhesion, radiation on electronics | - | declared limit, no prediction |
| C | Getting stuck or sinking in loose soil | - | tested on Earth, never predicted; "VIPER twin slipped 42 % at 30 deg on Earth vs 85 % simulated on the Moon (arXiv 2405.11001). Every Earth result is optimistic." |
| C | Abrasive wear of wheels, seals and bearings | - | tested on Earth, never predicted; rounded Earth sand underestimates wear; young volcanic or pyroclastic ground is closer |

Ground pressure (rigid patch): Earth 53,955 Pa, Moon 8,910 Pa, Mars 20,515 Pa (depends on the unverified patch size).

### 4.5 Wear hint by lithology (`wear_test_hint`, flag only, no score)

GLiM classes `py` pyroclastics, `vb` basic volcanic, `vi` intermediate volcanic, `va` acid volcanic -> `candidate_for_wear_tests` ("may keep angular grains, closer to lunar regolith for wear tests (check in the field)"). `su` unconsolidated sediments, `ss` siliciclastic sedimentary, `sm` mixed sedimentary, `sc` carbonate sedimentary, `ev` evaporites -> `optimistic_for_wear` ("grains usually rounded, wear tests here underestimate lunar abrasion"). Anything else -> `no_data`. Neither Earth table in the repository has a `lithology_class` column, so every rover zone gets `no_data`.

### 4.6 Ranking validation (`validate_rover_ranking`)

- Expected high (`MOBILITY_POSITIVES`): Bardenas, Tabernas, Dumont Dunes, MDRS, Yungay, Erfoud, Dhofar, Ramon, Haughton, Death Valley, Qaidam.
- Expected low (`MOBILITY_MISMATCHES`): Concordia, NEEMO, HI-SEAS, Rio Tinto, El Soplao.
- Reference: "BASEPROD rover dataset at Bardenas Reales, Gerdes et al., Scientific Data 11:1054 (2024), doi:10.1038/s41597-024-03881-1".
- Rule: a problem is raised if Bardenas has no score, if Bardenas is below the median of the scored positives, or if any expected-low site scores at or above that median. Sites with no score are ignored except Bardenas. It reports only and never changes weights. The "percentile" it prints is computed among the named sites only, not among all cells.

### 4.7 Self-test

29 checks (11 version 1, 12 version 2, 6 version 3). Result on the branch: **29/29 passed**.

---

## 5. `rover_integration.py`

Purpose (docstring): connects v3 to `analog_finder.py` "without changing how the ranking is computed. It only ADDS information to the metadata that export_web_bundle() already writes"; "Scores, gates and weights are never modified here."

Functions:

- `rebuild_rover_bundle(earth_df, previous_bundle=None, author=...)`: if `previous_bundle["preset_frozen"]` is true, returns the old bundle unchanged; otherwise builds the v3 preset with `available_columns=list(earth_df.columns)` (so baseline and p90 rule follow the real columns), `freeze=False, allow_unverified=True`, and stores `rover_spec`, `preset_config`, `gravity`, `preset`.
- `_pick(row, *names)`: case-insensitive column lookup in a CSV row.
- `load_site_coords(path=BENCHMARK_CSV)`: reads the benchmark CSV if it exists; name column `name` / `site` / `site_name`, latitude `lat` / `latitude` / `lat_deg`, longitude `lon` / `longitude` / `lon_deg`. A check name matches a row when it is a case-insensitive substring of the row name (with `í` -> `i`); the first matching row wins. Any check site not found falls back to `APPROX_SITE_COORDS`.
- `_grid_step_deg(earth_df)`: median latitude step of the grid.
- `site_scores(earth_scored, coords, score_col="score_rover")`: nearest grid cell to each site (longitude wrapped, scaled by cos(lat)); score is `None` if the nearest cell is farther than 1.5 grid steps or its score is NaN. Returns score, cell lat/lon and distance in degrees.
- `rover_ranking_check(earth_scored, benchmark_csv)`: runs `validate_rover_ranking` on those cell scores; adds `cells`, `coordinates_from` and a note that a site score is the score of its nearest cell.
- `add_wear_hints(zones, earth_scored)`: adds `wear_test_hint` / `wear_test_text` to each rover zone from `lithology_class` if that column exists.
- `apply_rover_extras(earth_scored, meta)`: the single entry point; sets `meta["rover_preset"]`, `meta["rover_preset"]["ranking_check"]`, and the wear hints on `meta["optimal_mission_zones"]["rover"]`; any exception is caught and stored as `meta["rover_preset"]["integration_error"]`.
- `selftest()`: 10 checks on a synthetic 2-degree grid. Result on the branch: **10/10 passed**.

Benchmark path expected: `tierra luna/data/benchmark/analog_benchmark.csv` (built from `os.path.dirname(__file__)`).

Approximate fallback coordinates carried in the code (`APPROX_SITE_COORDS`, decimal degrees): Bardenas (42.20, -1.50); Tabernas (37.05, -2.40); Dumont Dunes (35.68, -116.23); MDRS (38.41, -110.79); Yungay (-24.08, -69.93); Erfoud (31.43, -4.23); Dhofar (18.60, 54.00); Ramon (30.60, 34.80); Haughton (75.38, -89.67); Death Valley (36.50, -117.00); Qaidam (37.00, 95.00); Concordia (-75.10, 123.33); NEEMO (24.95, -80.45); HI-SEAS (19.60, -155.48); Rio Tinto (37.70, -6.60); El Soplao (43.30, -4.42).

Hook: two lines in `analog_finder.export_web_bundle` right after `compute_analog_ranking` (section 2.1 c). The `score_rover` it reads there is `analog_finder`'s own rover score (0.65 lunar similarity + 0.35 rover quality, NaN where a `mission_scoring.json` gate fails), not the soft score of `mission_scoring.py`.

End-to-end check of the hook (scratch copy of the branch, committed legacy tables, never in the repository): export ran with no `integration_error`; baseline `300m`; slope gate max 15 on the median ("applies_to": "median of the cell"); `coordinates_from` = the benchmark CSV; ranking check `ok: false`, problem "Bardenas scores below the median of mobility analogs" (Bardenas 43.67, median of positives 45.64; Rio Tinto 36.36, El Soplao 43.28 below the median; Yungay, Qaidam, Concordia, NEEMO with no score; HI-SEAS has no land cell within 1.5 grid steps). This is the in-pipeline score, given for information; the check the team lead asked for is in section 7.

---

## 6. VIPER figures (rule 5)

Only fields marked to verify, missing or estimated were examined. Source notes: `docs/sources/R1_viper_rover_spec_sources.md` (keys B25, F26, M24 as defined there).

| Field (before) | Official value in R1 | Meaning matches exactly? | Applied? |
|---|---|---|---|
| `max_operational_slope_deg` = 15, "ESTIMADO", VERIFICAR | 15 deg, requirement: M24 p.4 "Slopes up to 15 deg (reqt)" (https://ntrs.nasa.gov/api/citations/20240013903/downloads/LSIC_2024-Tech%20Infusion_Panel-VIPER_Mob-HW.pdf); also B25 p.17 "Slopes up to 15 deg and obstacles to 15 cm", F26 p.22 "15 deg slopes + 20 cm step obstacles (design limit)" | Yes (rover operational slope). Caveat recorded in the source text: rover-scale, not a DEM-baseline slope | **Yes.** Value stays 15 (team decision). New source: `NASA requirement: 'Slopes up to 15 deg (reqt)', Bluethmann, VIPER Rover Overview and Mobility and Hardware, NTRS 20240013903, p.4 (rover-scale requirement, not a DEM-baseline slope; docs/sources/R1_viper_rover_spec_sources.md)`; status OK |
| `max_speed_mps` = 0.20, "ESTIMADO (~0.8 km/h)", VERIFICAR | 20 cm/s: B25 p.17 and p.47 "Top Speed: 20cm/s (0.5MPH)" (https://assets.science.nasa.gov/content/dam/science/psd/lunar-science/documents/2025-02-13_VIPER_Updated_Technical_Briefing_Presentation-Shared.pdf) | Yes (maximum speed = top speed) | **Yes.** Value stays 0.20. New source: `NASA VIPER Industry Day Technical Briefing, 13 Feb 2025, p.17 and p.47: 'Top Speed: 20cm/s (0.5MPH)' (docs/sources/R1_viper_rover_spec_sources.md)`; status OK |
| `contact_patch_width_m` = 0.20, "ESTIMADO wheel width", VERIFICAR | wheel 20 cm wide: F26 p.10 "50 cm diameter, 20 cm wide" (https://ntrs.nasa.gov/api/citations/20260002876/downloads/viper-2026-04-29_v2.pdf) | Not exactly: the official figure is the wheel width; the field is the contact-patch width (equal only under the code's rigid flat-ground assumption) | **No, proposed.** Same number (0.20); team to decide whether wheel width may stand for patch width |
| `ground_clearance_m` = None, MISSING | 7 to 43 cm, adjustable: B25 p.47 / M24 p.4 "Adjustable ground clearance from 7- 43cm" | The field is one number; the official figure is a range | **No, proposed.** Choosing 0.07, 0.43 or a nominal value is a team decision (or store both ends) |
| `contact_patch_length_m` = 0.10, VERIFICAR | none (wheel diameter 50 cm is not a patch length) | - | No; stays, no official source |
| `cg_height_m` = 0.60, VERIFICAR | "**no official source found**" (R1) | - | No; stays, no official source |
| `cg_x_m`, `cg_y_m` = 0.0, "assumed centred", VERIFICAR | none | - | No; stay, no official source |
| `wheelbase_m` = 1.30, VERIFICAR | "**no official source found** ... Only overall footprint (1.7 x 1.7 m) is published." | - | No; stays, no official source |
| `track_m` = 1.30, VERIFICAR | "**no official source found**" | - | No; stays, no official source |

Not flagged but worth the team's attention: `mass_kg` = 440 (status OK, source "Phase-1 plan (VIPER, arXiv 2405.11001)"). The official roving mass is 447 kg (B25 p.46 "Mass: launch = 490kg, roving = 447kg"). Left unchanged because it is not marked to verify.

Effect of the two applied changes: no value, hard filter, weight or tolerance changes; the slope gate's `source` string in the built preset now carries the NASA requirement; the preset's `unverified` list no longer contains `max_speed_mps` or the slope-gate item. All self-test expectations unchanged (29/29, 10/10). Freezing is still refused without `--allow-unverified` because weights and tolerances remain illustrative and five rover fields stay unverified.

---

## 7. Contradiction (stated, not resolved)

`mission_scoring.json`, `missions.rover.gates` (the filters the pipeline applies, unchanged):
```
"slope_300m_deg": {"min": 0.5, "max": 15.0, "max_from": "max_operational_slope_deg", ...}
"rough_300m_m":   {"min": 5.0, "max": 650.0, "source": "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)"}
```
`rover_preset.py` v3, `PRESET_CONFIG["gates_by_baseline"]["300m"]`:
```
"slope_300m_deg": {"min": None, "max_from": "max_operational_slope_deg"},
"rough_300m_m":   {"min": None, "max": None, "source": "no gate until Robotics 1 sets one"},
```
and with `gate_prefer_p90: True` v3 puts the slope gate on the p90 column when one exists, while `mission_scoring.json` applies it to the median column `slope_300m_deg`.

So, for the same rover: (1) slope minimum 0.5 deg in the JSON vs none in v3; (2) slope maximum 15 deg in both, but on the median in the JSON and on p90 (when available) in v3; (3) roughness 5 to 650 m in the JSON vs no roughness gate at all in v3 (only a tolerance of 10 m at 300 m). v3 also defines 5 km gates (slope max 15, no roughness gate) that the JSON does not have. Tolerances (5 deg, 10 m) and sector weights agree. The zip's own `mission_filters.json` sided with v3 on the minimums (`null`) and marked the 650 m maximum `PENDIENTE`. The JSON stays as it is; the pipeline's pass/fail comes from the JSON, the v3 gates only appear in the web bundle's `rover_preset.preset.gates`.

---

## 8. Integration done on the branch, and what was not ported

Done:
1. `tierra luna/rover_preset.py`: v3 from the zip, plus the two source/status lines of section 6 (lines 167-168). Nothing else differs from the zip.
2. `tierra luna/rover_integration.py`: byte for byte from the zip.
3. `tierra luna/analog_finder.py`: the hook (lines 619-620) and the Shackleton target (lines 259-261), both with the zip's exact text. Nothing else.
4. `tierra luna/data/benchmark/analog_benchmark.csv`: section 9.
5. `tierra luna/tests/test_rover_integration.py` (new, 7 tests): both self-tests, the benchmark columns and that every check site resolves from the file (not the fallback), the hook and the polar target present, and that `apply_rover_extras` never raises.

Note: the director's checkpoint commits (`ff6f1ae`) already contain items 1-4 as they stood; the test file is uncommitted.

Not ported (team lead to decide), none needed for `rover_integration` to run:
- `analog_finder.py` (2.1 a): `get_rover_preset_bundle` reading a frozen preset from `presets.json` instead of refreezing on every run, and the `preset_frozen` flag. Without it the frozen flag that `rover_integration` honours is never set on the branch.
- `harmonizer_cleaner.py` (2.2): true-cell-size slopes in global mode and the four new columns `relief_cell_km`, `relief_cell_ew_km`, `slope_cell_deg`, `rough_cell_m`.
- `mission_filters.json` (2.3): rover slope and roughness minimums set to null, new source texts, `frozen_at`, `author`, CRLF line endings. Forbidden by the team lead's rule.
- `web/index.html` (2.4): `cellKm()`, `gateRange()` and the two label changes (removes the hard-coded `0.5–18°` / `5–650 m`).
- All of `output_py/` and `web/analog_data.js`: zip data from a different (synthetic Moon) run; not replaced.

---

## 9. Benchmark file

Created at `tierra luna/data/benchmark/analog_benchmark.csv` from `/home/user/NASA/docs/research/02_analog_benchmark.csv` (44 sites). Same 16 columns in the same order: `id, name, lat, lon, coord_quality, country, target_body, orientation_group, analog_type, analog_property_for, not_analog_for, tested_there, benchmark_role, in_spain, source_url, source_status`. All values equal except one: MA05 `name` "Mars Desert Research Station (Hanksville, Utah)" became "Mars Desert Research Station (MDRS) (Hanksville, Utah)", because the code matches by substring and "MDRS" is not otherwise in the name (without it MDRS silently falls back to the approximate point). Quoting differs from the source file only where the CSV writer needs no quotes.

Grid conventions: legacy table, 2-degree cells centred on odd degrees (cell (43, -1) covers 42-44 N, 2-0 W); real table, 1-degree cells centred on half degrees with an id `E<n>`. Cells below are the nearest cell centre to the benchmark point (the same rule `rover_integration` uses).

| Site | Code approx (lat, lon) | Benchmark (lat, lon), id | Coordinate quality / source status / source URL (from benchmark) | Distance | Legacy 2-deg cell | Real 1-deg cell |
|---|---|---|---|---|---|---|
| Bardenas | 42.20, -1.50 | 42.1612, -1.4663, ES06 | OSM centroid of Bardenas Reales / VERIFIED LIVE / https://www.nature.com/articles/s41597-024-03881-1 | 5.1 km | (43, -1) | (42.5, -1.5) E17098 |
| Tabernas | 37.05, -2.40 | 37.0676, -2.5295, ES04 | OSM centroid of Paraje Natural; exact ExoFiT trial point not published here / VERIFIED LIVE / https://www.esa.int/ESA_Multimedia/Images/2018/11/ExoFitness | 11.7 km | (37, -3) | (37.5, -2.5) E18897 |
| Dumont Dunes | 35.68, -116.23 | 35.6811, -116.2248, MA04 | OSM point / FROM MEMORY / https://www.nasa.gov/analogs | 0.5 km | (35, -117) | (35.5, -116.5) E19503 |
| MDRS | 38.41, -110.79 | 38.4065, -110.7919, MA05 | Wikipedia and OSM agree / VERIFIED LIVE / https://mdrs.marssociety.org/ | 0.4 km | (39, -111) | (38.5, -110.5) E18429 |
| Yungay | -24.08, -69.93 | -24.0800, -70.0000, MA01 | approx +-0.1 deg; McKay et al. 2003 station at -24.0825, -69.9852 / VERIFIED LIVE / McKay et al. 2003 PDF (webarchive.library.unt.edu) | 7.1 km | (-25, -71) (lon -70.0 is exactly on the -71/-69 boundary; approx point gives (-25, -69)) | (-24.5, -70.5) E41149 (approx point: (-24.5, -69.5)) |
| Erfoud | 31.43, -4.23 | 31.4350, -4.2328, MA15 | OSM point for Erfoud town / VERIFIED LIVE (Morocco and dates; Erfoud location FROM MEMORY) / https://oewf.org/en/mars2013/ | 0.6 km | (31, -5) | (31.5, -4.5) E21055 |
| Dhofar | 18.60, 54.00 | 18.1395, 55.1754, MA17 | OSM point for Marmul airport; field base nearby (+-0.2 deg) / VERIFIED LIVE / https://oewf.org/en/amadee-18 | **134.2 km** | (19, 55) (approx: (19, 53)) | (18.5, 55.5) E25795 (approx: (18.5, 53.5)) |
| Ramon | 30.60, 34.80 | 30.6120, 34.8012, MA16 | OSM point for Mitzpe Ramon / VERIFIED LIVE / https://oewf.org/en/amadee-20/ | 1.3 km | (31, 35) | (30.5, 34.5) E21454 |
| Haughton | 75.38, -89.67 | 75.3833, -89.6667, MA06 | Wikipedia and OSM agree / VERIFIED LIVE / https://www.marsinstitute.no/hmp | 0.4 km | (75, -89) | (75.5, -89.5) E5130 |
| Death Valley | 36.50, -117.00 | 36.2309, -116.7847, MA03 | OSM point (Wikipedia gives 36.2503,-116.8258) / FROM MEMORY (site-specific test record not fetched) / https://www.nasa.gov/analogs | **35.6 km** | (37, -117) | (36.5, -116.5) E19143 (approx: (36.5, -117.5)) |
| Qaidam | 37.00, 95.00 | 38.7367, 93.3335, MA14 | OSM point for Lenghu town (regional; Dalangtan playa further W) / VERIFIED LIVE / https://arxiv.org/abs/2501.08584 | **242.3 km** | (39, 93) (approx: (37, 95)) | (38.5, 93.5) E18633 (approx: (37.5, 94.5)) |
| Concordia | -75.10, 123.33 | -75.1000, 123.3333, OP01 | OSM point / VERIFIED LIVE / https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/Concordia | 0.1 km | (-75, 123) | (-75.5, 123.5) E59703 |
| NEEMO | 24.95, -80.45 | 24.9500, -80.4536, OP03 | Wikipedia point / FROM MEMORY / https://www.nasa.gov/analogs | 0.4 km | (25, -81) | (24.5, -80.5) E23499 |
| HI-SEAS | 19.60, -155.48 | 19.6024, -155.4872, OP02 | Wikipedia point / FROM MEMORY (hi-seas.org returned HTTP 401) / https://www.nasa.gov/analogs | 0.8 km | (19, -155) | (19.5, -155.5) E25224 |
| Rio Tinto | 37.70, -6.60 | 37.7200, -6.5600, ES01 | approx +-0.03 deg (from memory; Nerva town geocoded 37.6951,-6.5505 by OSM) / VERIFIED LIVE / https://astrobiology.nasa.gov/news/drilling-for-weird-life/ | 4.2 km | (37, -7) | (37.5, -6.5) E18893 |
| El Soplao | 43.30, -4.42 | 43.2965, -4.4101, ES08 | OSM point (re-checked 2026-11-14) / VERIFIED LIVE / https://www.frontiersin.org/articles/10.3389/feart.2021.642667/pdf | 0.9 km | (43, -5) | (43.5, -4.5) E16735 |

Distances are great-circle (haversine, R = 6371 km). With the benchmark file present the code no longer uses the approximate points; where the approximate point is more than a few km off (Dhofar, Death Valley, Qaidam, and Yungay at the cell boundary), it falls in a different cell. Four benchmark coordinates are themselves marked FROM MEMORY in the benchmark (Dumont Dunes, Death Valley, NEEMO, HI-SEAS); they are kept as recorded.

---

## 10. Runs and the rover ranking check

### 10.1 Self-tests and suite

- `python rover_preset.py --selftest`: 29/29 checks passed.
- `python rover_integration.py --selftest`: 10/10 checks passed.
- `python -m pytest -q` in `tierra luna/`: before the new test file, with `engine/` unchanged, **83 passed, 1 skipped** (skip: `test_engine.py:376` "app/public/data/v1 was removed"). Later runs, while another agent was editing `engine/config.py`, `engine/gates.py`, `engine/pipeline.py`, `engine/*.json` and `mission_scoring.json` (adding `lunar_base` and `offered_missions`; the rover block is unchanged), gave 4 failures and 30 setup errors, all in `tests/test_engine.py` and `tests/test_real_data.py`, all inside the engine (`KeyError` on `elevation_r...`, missing `app/public/data/v2/*.bin`); they persisted on a re-run and none involves `rover_preset.py`, `rover_integration.py` or `analog_finder.py`. `tests/test_pipeline.py` + `tests/test_rover_integration.py`: **22 passed** (15 + 7). The full suite should be re-run once the engine work lands.

### 10.2 Method

Rover block of `mission_scoring.json` through `mission_scoring.evaluate(df, ["rover"])` (common gates `elevation_m >= 1`, `mask_fraction >= 0.3`; `require_present` slope and roughness; gates slope 0.5-15 deg, roughness 5-650 m; soft score: slope 0.45 (bad 15, good 1), roughness 0.30 (bad 650, good 30), `rock_or_bare_frac` 0.25 (bad 0, good 0.7)). Site cells by `rover_integration.site_scores` with the benchmark coordinates; check by `rover_preset.validate_rover_ranking`. Rank = position among all cells that have a score (1 = best). Nothing was tuned.

- Input A: committed legacy table, EARTH rows of `output_py/earth_moon_harmonized_clean.csv` (16,200 cells, 2 degrees). 5,297 cells pass and are scored.
- Input B: `output_real/earth_real_1deg.csv` (64,800 cells, 1 degree), mapped through `real_data/column_aliases.json`: `slope_300m_deg` <- `slope_iso_deg` (as instructed; 3.706 km baseline), `rough_300m_m` <- `roughness_m` (1.853 km lag), other variables identity. 10,337 cells pass and are scored.

### 10.3 Input A, legacy 2-degree table

| Site | Expected | Cell | Passes? (why not) | Score | Rank / 5297 |
|---|---|---|---|---|---|
| Bardenas | high | (43, -1) | yes (slope 10.12, rough 463.2, rock 0.23) | 32.83 | 5063 |
| Tabernas | high | (37, -3) | yes (slope 10.78, rough 492.7) | 27.89 | 5157 |
| Dumont Dunes | high | (35, -117) | yes | 44.71 | 4740 |
| MDRS | high | (39, -111) | yes | 35.82 | 4997 |
| Yungay | high | (-25, -71) | **no**: ocean-coded cell (elevation -250, mask 0): fails elevation, mask, slope min, roughness min | - | - |
| Erfoud | high | (31, -5) | yes | 40.22 | 4871 |
| Dhofar | high | (19, 55) | yes (slope 1.21, rough 54.8, rock 0.81) | 98.13 | 437 |
| Ramon | high | (31, 35) | yes | 53.65 | 4374 |
| Haughton | high | (75, -89) | yes | 86.54 | 1526 |
| Death Valley | high | (37, -117) | yes | 35.43 | 5004 |
| Qaidam | high | (39, 93) | **no**: slope 17.35 > 15 and roughness 811.4 > 650 | - | - |
| Concordia | low | (-75, 123) | **no**: slope 0.397 < 0.5 | - | - |
| NEEMO | low | (25, -81) | **no**: slope 0.085 < 0.5 and roughness 3.14 < 5 | - | - |
| HI-SEAS | low | (19, -155) | **no**: ocean-coded cell (elevation -250, mask 0) | - | - |
| Rio Tinto | low | (37, -7) | yes (slope 2.96, rough 134.0) | 71.19 | 3132 |
| El Soplao | low | (43, -5) | yes | 38.90 | 4908 |

Median of scored positives 40.22. **Check FAILS**: "Bardenas scores below the median of mobility analogs" and "Rio Tinto (operations or mineralogy analog) scores as high as the mobility analogs". Why: the legacy slopes are fixed-pixel slopes on a 2-degree grid (the zip's harmonizer comment calls them inflated); most named mobility sites sit in cells with 8-12 deg "300 m" slope and 360-545 m roughness, near the bad end of the soft scale, so they rank in the bottom tenth of 5,297 cells, while flatter cells (Dhofar, Rio Tinto) score high. Two sites (Yungay, HI-SEAS) fall in ocean-coded cells at this resolution.

### 10.4 Input B, real 1-degree table (slope from `slope_iso_deg`)

| Site | Expected | Cell | Passes? (why not) | Score | Rank / 10337 |
|---|---|---|---|---|---|
| Bardenas | high | (42.5, -1.5) E17098 | yes (slope 1.91, rough 77.0, rock 0.018) | 70.43 | 7042 |
| Tabernas | high | (37.5, -2.5) E18897 | yes | 69.36 | 7385 |
| Dumont Dunes | high | (35.5, -116.5) E19503 | yes | 70.17 | 7128 |
| MDRS | high | (38.5, -110.5) E18429 | yes | 77.38 | 2120 |
| Yungay | high | (-24.5, -70.5) E41149 | yes | 84.34 | 1410 |
| Erfoud | high | (31.5, -4.5) E21055 | yes | 99.29 | 387 |
| Dhofar | high | (18.5, 55.5) E25795 | **no**: slope 0.143 < 0.5 and roughness 4.85 < 5 | - | - |
| Ramon | high | (30.5, 34.5) E21454 | yes | 99.43 | 369 |
| Haughton | high | (75.5, -89.5) E5130 | yes | 98.89 | 430 |
| Death Valley | high | (36.5, -116.5) E19143 | yes | 66.21 | 8281 |
| Qaidam | high | (38.5, 93.5) E18633 | yes | 99.02 | 418 |
| Concordia | low | (-75.5, 123.5) E59703 | **no**: slope 0.043 < 0.5 and roughness 1.09 < 5 | - | - |
| NEEMO | low | (24.5, -80.5) E23499 | **no**: sea cell (mask 0.002, no slope or roughness data) | - | - |
| HI-SEAS | low | (19.5, -155.5) E25224 | yes | 64.52 | 8647 |
| Rio Tinto | low | (37.5, -6.5) E18893 | yes | 74.87 | 4399 |
| El Soplao | low | (43.5, -4.5) E16735 | yes | 53.97 | 9865 |

Median of scored positives 84.34. **Check FAILS** on one item: "Bardenas scores below the median of mobility analogs". All three scored expected-low sites are below the median (HI-SEAS 64.52, Rio Tinto 74.87, El Soplao 53.97). Why Bardenas is low: its 1-degree cell has gentle slope and roughness (utilities 0.93 and 0.92) but `rock_or_bare_frac` 0.018 (the whole cell, 42-43 N, 2-1 W, has almost no bare or sparse-vegetation land cover in ESA CCI; the badlands are a small part of a 1-degree cell), and that variable carries 25 % of the soft score; Tabernas, Dumont Dunes and Death Valley are low for the same reason. Dhofar is removed by the 0.5 deg slope and 5 m roughness minimums: these thresholds were written for a 300 m baseline and are applied here to a 3.7 km slope and a 1.85 km roughness, which are much gentler (`column_aliases.json` states this caveat); the same minimums remove Concordia.

### 10.5 Overall

The rover ranking check fails on both inputs, for data and baseline reasons stated above, not because of a code fault. No threshold, weight or coordinate was changed to make it pass.
