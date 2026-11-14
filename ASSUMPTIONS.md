# Assumptions, engine settings and open decisions

Scope: the analog engine in `tierra luna/engine/` and the bundles it writes. Since engine 2.0.0 the engine is dataset-aware (`tierra luna/engine/datasets.json`):

- `real_1deg` (default): the real 1-degree tables in `tierra luna/output_real/`, exported as the v2 bundle in `app/public/data/v2/` that the app ships. Sections 10 and 11.
- `legacy_2deg`: the committed 2-degree table, exported as the v1 JSON bundle to `tierra luna/build/legacy_2deg/` (not shipped) for before-and-after comparison: `python -m engine build --dataset legacy_2deg`. Sections 1 to 9 describe this table; their numbers are unchanged, because a fresh legacy build reproduces the v1 bundle byte for byte except its manifest. `app/public/data/v1/` is that last v1 bundle; the app code does not read it.

The file structures are in `docs/DATA_CONTRACT.md` (v2, with v1 as an appendix). The audit evidence behind sections 1 to 9 is in the Phase-0 audit (A1 to A4) and in `docs/integration/R1..R4`; the evidence behind section 10 is in `tierra luna/real_data/` (READMEs, provenance files, column aliases).

The engine reads mission thresholds, weights, utility bounds, category tables and tolerances **only** from `tierra luna/mission_scoring.json`. Settings that belong to the engine alone are in `tierra luna/engine/engine_config.json`; settings that depend on the input table are in `tierra luna/engine/datasets.json`, one descriptor per dataset. Each setting carries a `why`, and `load_engine_config` refuses a dataset setting placed in `engine_config.json`. Every entry below says what was assumed, why, what it does to the results, and where to change it.

Entries marked **pending team confirmation** are defaults the engine took on open team questions.

## 1. Data levels

Every variable has a level for each body. The levels live in `engine/provenance.json`, which was built from the audit data dictionary by `engine/build_provenance.py`. They are never inferred from column names. A DERIVED level is capped at the level of its input: a formula applied to an UNDOCUMENTED or MODELLED value takes that weaker level, and the entry says so in `level_note`.

| level | meaning | variables (EARTH / MOON) |
|---|---|---|
| MEASURED | Verified against a named data product in the repository | Moon `elevation_m` only. It is the exact 8x8 block mean of LOLA LDEM_4. |
| DERIVED | A stated formula applied to a measured value, or a copy of such a value | Moon only: `elevation_rel_m`, `roughness_m`, `rough_300m_m`, `sun_elev_max_deg`. |
| MODELLED | A formula or constant invented in code; not data | Both bodies: `sar_sigma0_db`, `mask_fraction`, `irradiance_kwh_m2_day`, `sun_low_frac_0_5deg`, `lst_diurnal_amp_k`, `thermal_inertia_class`, `permafrost_class`, `rain_mm_day`, `wind_max_ms`, `tmin_c`. Earth only: `sun_elev_max_deg`. |
| UNDOCUMENTED | Extra label for the audit's "NOT DETERMINED": a cached array (`earth_global_real.npz`, `moon_global_pds.npz`) whose product, date and method are not documented. It may be real data, but it cannot be presented as measured. | Earth: `elevation_m` (ocean is a -250 m fill), `elevation_rel_m` (the audit says DERIVED, but it is `elevation_m` minus a mean, and `elevation_m` is UNDOCUMENTED), `slope_deg`, `roughness_m`, `temp_k`, `rock_or_bare_frac`, `slope_300m_deg`, `rough_300m_m`. Moon: `slope_deg`, `temp_k`, `rock_or_bare_frac`, `slope_300m_deg`. |

What this means for the results:

- Every gate and every weighted variable of the four missions is MODELLED or UNDOCUMENTED on at least one body.
- The one MEASURED variable, lunar elevation, is not weighted by any mission.
- Every Earth cell sits in a 2-degree cell: about 222 km on Earth and about 61 km on the Moon. The `resolution_m = 500` column is wrong.
- On the 10,273 Earth ocean cells, the cached bands are constant fills (A2 section 2a). The bundle exports them as `null`, never as numbers (section 4, `earth_ocean_fill`).

The rankings therefore show how the team's criteria rank the cells of the current table. They are not evidence measured at site scale.

### Comparable across bodies

Each variable also carries `comparable_across_bodies` and a `comparability_note` in `provenance.json` (exported in `variables.json`). A variable marked `false` is not the same physical quantity on Earth and on the Moon. It is left out of the Earth-Moon similarity and the twin search, but it still counts fully in suitability (section 5).

| variable | comparable | reason |
|---|---|---|
| `rock_or_bare_frac` | no | Bare-ground fraction on Earth (0-0.98), rock abundance on the Moon (0.0015-0.046). |
| `irradiance_kwh_m2_day` | no | The lunar value is the Earth atmospheric formula fed with rock abundance where Earth uses bare-ground fraction (A2 sections 2c and 3). |
| `thermal_inertia_class` | no | Thresholds on `rock_or_bare_frac`; every lunar cell is `suelo`. |
| `permafrost_class` | no | Permafrost has no lunar equivalent by definition (R3, ice row and F17). |
| `temp_k` | yes, with caveat | Earth is described as daytime, the Moon as night-time-like (A2 section 3). Kept because ice and thermal have no other temperature. |
| `lst_diurnal_amp_k`, `tmin_c` | yes, with caveat | Both MODELLED; the lunar amplitude is contradicted by Diviner (section 9). |
| `slope_*`, `rough*` | yes, with caveat | Same quantity over different areas (222 km against 61 km cells), methods undocumented. |

## 2. Changes to existing team files

| file | change | why | effect |
|---|---|---|---|
| `tierra luna/mission_scoring.json` | `"on_missing_gate": "keep"` became `"drop"`. Nothing else changed. | The author's note says a missing value in a hard filter discards the cell, and the team lead set the same rule. | No effect on today's data, which has no missing values: Earth counts stay 5,192 solar, 2,613 thermal and 1,986 for both. With missing data, a cell missing `elevation_m` or `mask_fraction` would now be eliminated; before, it was kept. |
| `tierra luna/analog_finder.py` (1) | Removed the x0.35 multiplier in `compute_mission_optimality_scores`. A cell that fails a mission's gates now gets `score_<mission> = NaN`, and a cell that fails any mission gets `score_all = NaN`. `export_web_bundle` writes such scores as `null` (a new `_score_or_none` helper) instead of a number, so the JSON stays valid. | The team lead asked for exactly this: a cell that fails a hard filter has no score for that mission and cannot be ranked for it. | `analog_ranking.csv` and the old web JSON carry NaN/null for failed missions instead of 35 % of the score. `build_optimal_mission_zones` already used passing cells only. Test: `test_no_gate_failed_cell_ranked_in_old_analog_finder`. |
| `tierra luna/analog_finder.py` (2) | `compute_analog_ranking` takes its pass flags from `mission_scoring.json` through the engine's gate module (new helper `_apply_mission_scoring_gates`), instead of `mission_filters.apply_missions` on `mission_filters.json`. The similarity ranking now ranks only cells that pass every mission (`pass_all = 1`), with a stable sort. | Review finding: the old gates let 693 solar and 850 thermal Earth cells pass that `mission_scoring.json` eliminates, and the ranking gave a rank to all 5,927 land cells, 3,813 of which fail. `mission_scoring.json` says it replaces `mission_filters.json`. | analog_finder's pass flags and `mission_stats` now equal the engine's (rover 5,297, solar 5,192, thermal 2,613, ice 3,023, all four 1,728). `analog_ranking.csv` lists only cells passing all four missions. Its scores still use the old formulas of `mission_filters.json` (weights, tolerances): that path is legacy and the app reads the engine bundle. The old `web/index.html` still recomputes passes in the browser from `mission_filters.json`, so it can disagree with these flags. Test: `test_old_analog_finder_uses_the_engine_gates`. |
| `tierra luna/mission_scoring.py` | none | Behaviour must stay the same. | The engine wraps it: `engine/gates.py` and `engine/suitability.py` call `apply_gates`, `evaluate`, `utility` and `combine_with_similarity` unchanged. |
| `tierra luna/tests/conftest.py` (new) | A session fixture restores `data/presets/presets.json` byte for byte after the tests. | `analog_finder.get_rover_preset_bundle()` rewrites that tracked file, with a new `frozen_at`, every time the old pipeline runs, and the existing tests run it. | Running the tests no longer changes the working tree. No test result changes. |

## 3. Decisions on open team questions (all pending team confirmation)

1. **Rover gates kept exactly as in `mission_scoring.json`**: `slope_300m_deg` 0.5-15 and `rough_300m_m` 5-650.
   - `rover_preset.py` sets only a slope maximum (15, marked ESTIMADO) and no roughness gate.
   - The 5-650 m envelope has no source in the research notes (A3 section 4).
   - Effect: on Earth land, 591 cells fail on slope and 290 on roughness. On the Moon, 7,006 cells fail `rough_300m_m > 650`, the main lunar rover failure.
   - The rover block is exported with `provisional: true`.
   - Change: `mission_scoring.json` → `missions.rover.gates`.
2. **Ice kept as a provisional fourth mission**, exactly as written.
   - `permafrost_class` is a temperature threshold, not an IPA map.
   - Effect: 3,023 Earth and 4,680 lunar cells pass.
   - Change: `engine_config.json` → `missions`.
3. **The land mask applies to Earth only.**
   - The common gate `elevation_m >= 1` exists to discard ocean, whose elevation the model fixes at -250 m.
   - Lunar `elevation_m` is height relative to the 1737.4 km sphere, so the gate would remove 11,041 lunar cells for no physical reason.
   - Effect on lunar pass counts, without and with the gate on the Moon:

     | mission | without the gate (engine default) | with the gate (audit A3) |
     |---|---|---|
     | rover | 9,062 | 1,910 |
     | solar | 13,331 | 4,712 |
     | thermal | 16,200 | 5,159 |
     | ice | 4,680 | 801 |

   - `mask_fraction >= 0.3` still applies to both bodies; it is the constant 1.0 on the Moon.
   - Change: `engine_config.json` → `gate_body_applicability`.
4. **A missing value in a gated variable eliminates the cell.** This is `on_missing_gate = "drop"`, from section 2.
   - The reason code `<variable>:missing` is recorded.
5. **Non-comparable variables are left out of the similarity** (`similarity_comparability.exclude_non_comparable = true`).
   - Variables: `rock_or_bare_frac` (rover, thermal), `irradiance_kwh_m2_day` (solar, thermal), `thermal_inertia_class` (thermal), `permafrost_class` (thermal, ice). Reasons in section 1.
   - Why: with them, "Moon-likeness" measured how vegetated an Earth cell is. Before the change, corr(rover similarity, Earth bare fraction) was -0.982, and solar ranked the Amazon first (top 10: 8 Brazilian cells and French Guiana) although its suitability prefers the Sahel. After the change the rover correlation is 0.014.
   - Effect on each top 10 (engine 1.0.0 against 1.1.0, cell ids):

     | mission | before | after | overlap |
     |---|---|---|---|
     | rover | GL 971, AU 10590, AU 10411, AU 10410, BW 10182, SD 6943, MR 6202, ML 6745, AU 10239, GL 974 | GL 1330, GL 1689, AQ 15610, SA 5692, AQ 15383, AQ 15388, AQ 15744, AQ 15820, AQ 16097, OM 6416 | 0 |
     | solar | BR 8346, IN 7329, BR 8521, BR 8525, GF 7803, BR 8700, BR 8340, BR 8345, BR 8344, BR 8528 | KE 8210, CF 7661, CD 8561, GH 7289, CD 7841, BJ 7111, CF 7482, SO 8031, SS 7483, BF 7109 | 0 |
     | thermal | 10 Antarctic cells at -81/-83 deg, 69-81 E | 10 Antarctic cells at -81 deg, 65-83 E | 6 |
     | ice | 10 Antarctic cells (15092 first) | the same 10 | 10 |

   - Set the switch to `false` to restore the old comparison. If the team keeps the comparison, the app must say plainly that solar then ranks the Amazon first because forest cells resemble the formula's lunar values, not because they suit solar panels.
   - Change: `engine_config.json` → `similarity_comparability`; per variable: `engine/build_provenance.py` → `COMPARABILITY`.
6. **Mix factor 0.5** (`mix_factor`). It is `combine_with_similarity`'s own default, but choosing between lunar likeness and mission fitness is an open team question.
   - Effect on each top 10 compared with 0.5 (overlap out of 10): alpha 0.3 (more suitability): rover 0, solar 7, thermal 8, ice 9. Alpha 0.7 (more similarity): rover 8, solar 5, thermal 10, ice 10. Rover is the most sensitive: at 0.3 its top 10 is nine Antarctic cells and one Greenland cell.
7. **Similarity scale: 5th-95th percentile, pooled over the passing cells of both bodies** (`similarity_scale`).
   - The population is dominated by the body with more passing cells (thermal: 16,200 lunar against 2,613 Earth cells), so that body sets the scale. Weighting the two bodies equally would be a different rule; it is not implemented.
8. **Many-to-one twins.** Each Earth cell takes its single best lunar cell, so many Earth cells share a twin: distinct twins are rover 321, solar 941, thermal 2, ice 1. A one-to-one assignment would be a different rule and is not implemented.
9. **Confidence numbers** (`confidence`): level scores 1.0 / 0.7 / 0.3 / 0.2, thresholds 0.8 and 0.5, and the 1 km cell limit for "high" are engine choices.
10. **Antarctic labels** (`antarctic_label_lat_max = -60`): the Antarctic Treaty boundary; 1,689 land cells are labelled AQ.
11. **Similarity weights.** The team note in `mission_scoring.json` says its domain `weights` (relieve/material/termico/luz/agua) are used "only by the web 'Use Weights' button of the similarity". The engine instead weights the similarity with each mission's soft weights, because no mapping from those five domains to the new variables exists (the old `map_domain_weights_to_features` maps them to 6 old features and is the dilution the audit criticised). The domain weights are exported under `not_used_by_engine` with this reason.
12. **Solar gates exclude the lunar polar ridges.** Kept as written. The gates on irradiance, maximum sun elevation and low-sun fraction remove every lunar cell poleward of 77 deg (`missions.json` → `solar.facts.moon_pass_abs_lat_max`), which leaves 13,331 passing lunar cells, all at or equatorward of 77 deg. R2 section 1 and R3 section 4 say a lunar solar test should target the lit polar ridges; R3 asks whether this exclusion is intended (open question 3). Solar twins therefore lie between 1 and 77 deg of latitude.
13. **Thermal amplitude.** The lunar `lst_diurnal_amp_k` is a latitude formula (63-180 K) that Diviner contradicts at low and mid latitudes (about 250-300 K, R2 section 3; 95-390 K at the equator and about 220 K near-constant at polar rims, R3 F10 and F12; R2 open question 3, R3 open question 5). Thermal twins are therefore cells near the lunar poles (section 9).

## 4. Engine settings (`tierra luna/engine/engine_config.json`)

| setting | value | reason | effect on results |
|---|---|---|---|
| `engine_version` | 2.0.0 | Traces a bundle to the code; `engine.__version__` is read from it. 2.0.0 adds dataset descriptors, the real tables and the v2 bundle. | Written into `manifest.json`. No effect on scores. |
| `bundle_version`, `input_csv`, `output_dir`, `earth_ocean_fill`, `region_max_place_km`, `mission_notes`, `credits` | moved to `datasets.json` | They depend on the input table. The `legacy_2deg` descriptor keeps the values listed in this table (v1, the legacy CSV, ocean fills, 222.4 km, the legacy notes and credits); its output folder is now `build/legacy_2deg` (not shipped). | None on legacy results (byte-identical). |
| `mission_config` | `mission_scoring.json` | The team's filter system: the only source of thresholds, weights and bounds. | Every gate and soft criterion. Its sha256 is in `manifest.json`. |
| `missions` | rover, solar, thermal, ice | All four missions in the JSON. | Order of the missions in the bundle. |
| `gate_body_applicability` | `elevation_m`: EARTH; `mask_fraction`: EARTH, MOON | See section 3, item 3. | Lunar pass counts (table in section 3). |
| `on_invalid_value` | `report` | A value is never fixed silently. | Invalid values stay as they are, are listed in `validity.json` and are flagged in `invalid_fields`. Today 0 records fail. |
| `similarity_scale` | pooled 5th-95th percentile range over the cells of both bodies that pass the mission, concatenated | See section 5 and section 3, item 7. | Sets how fast similarity falls with a physical difference. Scales are written to `missions.json` (`similarity_scales`). |
| `similarity_zero_scale` | `exact_match` | Avoids a division by zero when every passing cell has the same value. | No variable has a zero scale today. |
| `similarity_comparability` | `exclude_non_comparable: true` | Section 3, item 5. | Similarity variables per mission: rover 2 of 3, solar 5 of 6, thermal 2 of 6, ice 1 of 2. |
| `mix_factor` | 0.5 | `combine_with_similarity`'s own default; pending (section 3, item 6). | final = 0.5 x similarity + 0.5 x suitability. |
| `pairing_chunk_rows` | 128 (was 512) | Memory and speed only: 128 Earth rows x 64,800 lunar cells x 8 bytes = 66 MB per temporary array on the 1-degree grid. | None on results (the legacy bundle is byte-identical). A legacy build takes about 8 s, a real build about 55 s. |
| `missing_data_reason` | code suffix `missing`, label `no data` | A missing gated or required value eliminates the cell (`on_missing_gate = drop`); the interface must be able to say so and count it. | Reason code `<variable>:missing`, label `no data: <variable>` in `missions.json` `reason_codes`; per-mission counts in `missing_data`. |
| `binary_encoding` | little-endian; Float32 with NaN for cell values; Int32 with -2147483648 as the missing sentinel; quantised decimals: utility 6, similarity 6, score 2, confidence score 3 | v2 binary columns. Quantised Int32 (value = q / 10^d) stores exactly the published value, so the browser reproduces the engine's scores; a Float32 utility would not. | Bundle layout only; scores unchanged. |
| `first_view_budget_bytes` | first view 2,500,000; total 14,000,000 | Size targets for a phone (decimal MB, so they hold under either reading of "MB"). | Checked by the tests; nothing is cut silently. Today: first view 2,282,069 bytes, total 9,696,959. |
| `confidence` | level scores MEASURED 1.0, DERIVED 0.7, UNDOCUMENTED 0.3, MODELLED 0.2; high_min 0.8; medium_min 0.5; high_max_cell_km 1.0; pair score = min(Earth, Moon) x coverage. Since 2.0.0 each body's score uses the variables with data on that body's cell (the Earth cell or its twin) and coverage is the weight with data on both; identical to before when nothing is missing | Section 6; pending (section 3, item 9). | **Every ranked cell is "low"**, and the score is one constant per mission: rover 0.30, solar 0.225, thermal 0.21, ice 0.255. Levels are per variable and body and no value is missing, so the score cannot vary between cells; `missions.json` → `facts.confidence_constant = true` tells the app to show it once per mission. With no weighted variable with data, confidence is `null`, never 0. |
| `explain_top_n` | 25 | Size of the "why" panel. | Only the size of `explain.json`, and the `top_n_country_counts` fact. |
| `explain_helps_n`, `explain_hurts_n` | 2, 2 | One line of "helps most" and "hurts most" per cell. | Only `explain.json`. |
| `top_failure_reasons_n` | 5 | Summary length. | Only `missions.json`. |
| `body_radius_km` | Earth 6371.0, Moon 1737.4 | The IUGG mean Earth radius, and the LOLA and IAU sphere. | True cell sizes (222.4 km and 60.6 km) and place distances. |
| `coordinate_tolerance_deg` | 1e-6 | Largest accepted gap between a CSV lat/lon and the centre computed from row/col. | Schema only; 0 failures today. |
| `lunar_gazetteer_csv` | `engine/data/iau_moon_nomenclature.csv` | An offline extract of the IAU/USGS gazetteer: 9,087 features, zip sha256 recorded in `engine/data/iau_source.json`. | Lunar feature names. |
| `lunar_feature_exclude_types` | `Satellite Feature` | Lettered satellite craters (7,064 entries) are not what a map reader recognises. A4 used the same rule. | Each lunar cell is labelled with the nearest of 2,023 primary features. |
| `antarctic_label_lat_max` | -60.0 | GeoNames has no populated places in Antarctica, and nearest-place labels there came out as "TF Kerguelen" (A3). Pending (section 3, item 10). | Land cells at or south of 60 S are labelled Antarctica (AQ) with no region. |
| `earth_country_polygons` | `engine/data/ne_110m_admin_0_countries.geojson` | Country by point-in-polygon instead of nearest place (section 7). | Country of 3,855 land cells from a polygon, 383 from the nearest place (outside all 110m polygons). |
| `region_max_place_km` | 222.4 | A first-level region is shown only when the nearest place is within one cell and in the same country. | 962 non-Antarctic land cells have a `null` region instead of a distant one. |
| `earth_ocean_fill` | the 7 cached bands and their 2 copies, on Earth cells with `land = 0` | A2 section 2a: constant fills, not values. | Those 9 variables are `null` on the 10,273 ocean cells of `earth_cells.json`; the fill constants are recorded in `ocean_fill`. Gates still read the fill (the team's land gate is written for it), so no pass flag changes. |
| `export_decimals` | see file; utilities and similarities 6, scores 2 | The engine computes the published scores from the published 6-decimal utilities and similarities, so the browser reproduces them exactly; the rank is computed on the published 2-decimal final. | Browser recomputation with the default weights gives the stored suitability, similarity, final and rank. Bundle 8.9 MB. |
| `mission_titles` | short English titles | For display. The team's descriptions are exported verbatim. | None on scores. |
| `not_used_by_engine_why` | text | Why tolerances, workable_days and domain weights have no effect; quotes the team note accurately. | Only `missions.json`. |
| `mission_notes` | one note per mission | The known limitations of section 9, exported as `known_limitations` next to computed `facts`. | Only `missions.json`. Nothing is tuned. |
| `credits` | attribution texts | For the app's about box. | None on scores. |

## 5. Similarity

- **Formula.** For each variable, `sim = max(0, 1 - |earth - moon| / scale)` in physical units. A categorical variable scores 1 when equal and 0 otherwise. A missing value gives a null sim, the variable drops out, and the weights renormalise.
- **Which variables.** The mission's weighted (soft) variables that exist on both bodies **and** are the same physical quantity on both (section 1, "Comparable across bodies"). Today: rover `slope_300m_deg`, `rough_300m_m`; solar `sun_elev_max_deg`, `sun_low_frac_0_5deg`, `slope_deg`, `lst_diurnal_amp_k`, `roughness_m`; thermal `lst_diurnal_amp_k`, `tmin_c`; ice `temp_k`. Weights are the mission's soft weights applied directly to these variables and renormalised over them. The old domain matrix (`map_domain_weights_to_features`) is not used (section 3, item 11).
- **Why a pooled physical range, not per-body z-scores or percentile ranks.**
  - A rank or z-score says where a cell stands within its own planet. It hides real physical differences.
  - Example with MODELLED values: Earth's largest formula amplitude is 38.75 K, while the lunar formula gives 63-180 K. Both are formula output (A2: Earth `8 + 22*bare + 0.0022*elev`, Moon `180*cos(lat)^0.35`), and the lunar range is contradicted by Diviner (section 3, item 13).
  - With per-body z-scores the old code scored `temp_k` as a 100 % match between 220-330 K Earth cells and 43-110 K lunar cells (A3 section 7).
  - With a pooled physical scale those differences stay visible. For example, the best thermal pair has amplitude similarity 0.81 and `tmin_c` similarity 0.26.
- **Why 5th-95th percentile, pooled over passing cells.** It is robust to outliers and covers the range relevant to the mission. The body with more passing cells has more say (section 3, item 7).
- **Why the rover `tolerances` are not used as scales yet.**
  - `mission_scoring.json` gives slope 5 deg and roughness 10 m, but these are defined for 300 m baselines.
  - The `*_300m_*` columns are copies of 2-degree-cell values (A2), so applying 300 m tolerances to 2-degree values would be a unit mismatch.
  - The tolerances are exported under `not_used_by_engine`.
  - Change: `engine_config.json` → `similarity_scale` (a per-variable override can be added there when 300 m data exists).

## 6. Twins, final score, confidence

- **Twin.**
  - Each passing Earth cell gets the lunar cell, among those passing the same mission, with the highest weighted similarity under the JSON weights over the similarity variables. Ties go to the lowest lunar id.
  - The twin is **fixed at build time**. Browser sliders re-score against the same twin (`docs/DATA_CONTRACT.md`).
  - Effect: the best-matching lunar cells are shared by many Earth cells (section 3, item 8; section 9).
- **Final score.** `mission_scoring.combine_with_similarity(alpha = mix_factor)` is applied to the engine's `similarity_pct` and to an **unrounded** suitability. Gate-failed cells stay null. (Engine 1.0.0 used `mission_scoring.evaluate`'s score, which that module rounds to 2 decimals; up to 0.0074 points of error moved 2,364 rover ranks.)
- **Precision.** The engine takes the unrounded utilities from `mission_scoring.utility`, rounds them once to 6 decimals, and computes the published suitability from exactly those values with the renormalised formula. Per-variable similarities are rounded once to 6 decimals and the published similarity is computed from them. The final score is computed from these two unrounded values. The team module's own 2-decimal score is checked against the published suitability (difference at most 0.0051 points), so the engine and `mission_scoring` cannot drift apart.
- **Ranking.** By the published final score (2 decimals) descending, ties by Earth cell id ascending. So the stored rank is exactly the contract rule applied to the stored `final`. Only passing cells with a twin are ranked; today every passing cell has one. A passing cell without a comparable variable has no twin, no final score and no rank.
- **Confidence.**
  - Per body, the engine takes the weighted mean of the level scores of the mission's weighted variables. The pair takes the weaker body's value and multiplies it by the share of weight with data.
  - The label is "high" only at 0.8 or above **and** with cells of at most 1 km, which no 2-degree cell meets. "Medium" needs 0.5 or above.
  - Why: the criteria act at rover and site scale, and the inputs are mostly MODELLED or UNDOCUMENTED.
  - Effect: everything is "low" today, with one constant score per mission (section 4). Confidence rises only when measured inputs at finer resolution replace the modelled columns.

## 7. Place names

- **Earth country.** Point-in-polygon of the cell centre on Natural Earth 1:110m admin-0 countries (public domain; `engine/data/ne_110m_admin_0_countries.geojson`, origin and sha256 in `engine/data/ne_source.json`). The file is the copy shipped in the `three-globe` npm package's examples; it was not downloaded from naturalearthdata.com in this session.
  - `label_rule = "natural_earth_polygon"`: 3,813 cells.
  - `"natural_earth_polygon_geonames_code"`: 42 cells in polygons without an ISO code in that file (France, Norway, Northern Cyprus, Somaliland); the code comes from the nearest GeoNames place and the name from the polygon.
  - `"nearest_geonames_place"`: 383 cells whose centre lies outside every 110m polygon (coasts, small islands).
  - `"antarctic_treaty_area"`: 1,689 cells at or south of 60 S.
  - Before (engine 1.0.0), the country was that of the nearest GeoNames place, which was wrong for 229 land cells (e.g. 33 Greenland cells labelled Iceland).
- **Earth region.** The nearest GeoNames place's first-level region, only when that place is in the same country and within `region_max_place_km` (222.4 km); otherwise `null` (e.g. Tibetan cells were labelled "Hebei").
- **Nearest place.** `reverse_geocoder` 1.5.1, offline GeoNames cities1000 (CC BY 4.0), single-process mode for determinism. `nearest_place_km` is exported so the app can show how far away the named place is.
- Country names come from the IANA tz `iso3166.tab` (public domain, `tzdata` package), or from the polygon's own name when the table has no entry (e.g. Kosovo).
- Only land cells (those passing the `elevation_m` land gate) are labelled. The 48 hand-made landmark labels of `analog_finder.py` are not used.
- **Moon.** The nearest primary IAU-named feature, with its name, type, diameter, and great-circle distance on the 1737.4 km sphere.
  - Gazetteer longitudes are 0-360 positive east and are converted with `lon - 360` when `lon > 180`.
  - Credit: Gazetteer of Planetary Nomenclature, IAU WGPSN and USGS Astrogeology Science Center.

## 8. Validation

- The schema is built with pydantic, one model per body, and generated from `provenance.json`. It checks:
  - latitude in -90..90 and longitude in -180..180;
  - that the grid position matches the coordinates (tolerance `coordinate_tolerance_deg`) and therefore the id;
  - the physically valid range of each variable, from the data dictionary (several ranges are the `config.py` ranges, which have no cited source);
  - the category vocabularies.
- Missing values are valid at this stage. They are handled by the gates, which eliminate the cell, and by suitability, which renormalises and flags it. In the bundle a missing value is `null` (tested with a table that has missing values, because today's input has none).
- `engine/contract.py` also checks the stored rank against the contract rule, that every twin passes, that an ocean fill is never exported as a value, and that no excluded variable has a similarity.
- Result today: 0 failing records on either body.

## 9. Known limitations of the results

These come from the data or from the team's configuration, not from engine bugs. Nothing was tuned to hide them. Each mission's notes are exported in `missions.json` → `known_limitations`, next to computed `facts` (twins, latitude reach, countries of the top 25), so the app can show them beside the ranking.

- **Rover: ice sheets rank at the top.** Ranks 1 and 2 are interior Greenland (75 N, 39 W and 71 N, 41 W), and 35 of the top 50 are Antarctic. 172 Greenland cells pass the rover gates; Greenland holds ranks 1, 2, 22, 28, 42 and 46. Cause: the provisional soft criteria have no surface-type term, ice counts as bare ground in `rock_or_bare_frac` (0.77 at rank 1), and 2-degree slope and roughness are smooth on an ice sheet (rank 1: slope 1.689 deg against 1.691 on its twin). An ice sheet is not a regolith trafficability analog. Whether `hielo` cells should be gated out is a question for Robotics 1.
- **Rover twins are mare cells.** The commonest twins are Seleucus (867 Earth cells), Mare Frigoris (505) and Sinus Roris (241): smooth lunar cells match smooth Earth cells. The 2-degree slope and roughness say nothing about rover-scale hazards.
- **Solar: no lunar polar site can be a twin.** Section 3, item 12. Top solar cells are now equatorial Africa (Kenya, Central African Republic, DR Congo, Ghana, Benin, Somalia, South Sudan, Burkina Faso); twins lie at 1-77 deg latitude. The solar similarity rests on latitude formulas (`sun_elev_max_deg`, `sun_low_frac_0_5deg`), slope, roughness and amplitude, so a near-equatorial Earth cell matches a near-equatorial lunar cell.
- **Thermal: twins are two lunar polar cells.** Every Earth cell's twin is Erlanger (87 N, 27 E; 2,353 cells) or Whipple (89 N, 179 W; 260 cells). The lunar amplitude formula is lowest at the clipped pole (63-64 K) and Earth's largest formula amplitude is 39 K, so the poles are always closest. The top 25 are all Antarctic. Rank 1 (81 S, 75 E): amplitude 34.88 K against 64.1 K, similarity 0.81 with a pooled scale of 155.5 K; `tmin_c` -64.8 against -224.3 C, similarity 0.26.
- **Ice: one twin for every Earth cell.** With `permafrost_class` out of the similarity, only `temp_k` remains, and every Earth cell's twin is W. Bond (65 N, 7 E), temp_k 88.11 K, class `discontinuo`: the warmest lunar cell that passes the ice gate, at the warm edge of the MODELLED lunar class thresholds, because it is the closest to the temperatures of the passing Earth cells (217-278 K). Ice similarity is therefore a temperature distance to one cell. Until a lunar cold-trap variable exists (R3 F13: PSRs as low as 25 K), the ice twin says little. Engine 1.0.0 described ice twins as "the coldest lunar cells with continuo permafrost"; that was wrong: its two twins were the warmest cells of each class (74.99 K continuo, 88.11 K discontinuo), and its similarity was dominated by a match on the permafrost label.
- **Temperature mixes times of day.** Earth `temp_k` is described as daytime and lunar `temp_k` as night-time-like (A2 section 3). The ice and thermal comparisons keep it, with that caveat in `variables.json`.
- **Confidence is "low" everywhere** and constant per mission (section 4).

## 10. The real 1-degree dataset (`real_1deg`, default since engine 2.0.0)

Inputs: `tierra luna/output_real/earth_real_1deg.csv` and `moon_real_1deg.csv` (64,800 cells each), built by `tierra luna/real_data/build_earth.py` and `build_moon.py` from open products. The engine reads them, their provenance files and `column_aliases.json` at build time and never copies a value into code. An independent verifier may still correct the tables or provenance rows: rebuild the bundle after any change (`python -m engine build`; the test `test_published_v2_matches_a_fresh_build` fails while the shipped bundle is stale).

### 10.1 Dataset settings (`tierra luna/engine/datasets.json` → `real_1deg`)

| setting | value | reason | effect on results |
|---|---|---|---|
| `inputs` | the two per-body CSVs | The builders' primary products; `earth_moon_real_1deg.csv` is their concatenation. | Every number. Their sha256 are in `manifest.json` `inputs`. |
| `grid` | 180 x 360, 1 degree | The tables' grid. | `id = row * 360 + col`; cells 111.2 km (Earth) and 30.3 km (Moon) north-south. |
| `provenance` | `real_data/provenance_earth.csv`, `provenance_moon.csv` | Levels, products, licences, resolutions and caveats from the builders, row of the real column actually read. `no data` becomes level `NO_DATA`; `DERIVED (...)` becomes DERIVED with the text kept as `level_note`; any other text is refused. | Levels in `variables.json` and in confidence. |
| `column_aliases` | `real_data/column_aliases.json` | Mission variable name to real column, with true baseline and caveat per body. | `slope_300m_deg` and `rough_300m_m` are read from km-baseline columns (below). |
| `column_overrides` | `slope_deg` → `slope_iso_deg`, `slope_p90_deg` → `slope_iso_p90_deg` | Every slope variable the missions name (rover `slope_300m_deg`, solar `slope_deg`) is read from the isotropic-baseline column on both bodies. The literal `slope_deg` uses a one-pixel east-west spacing that shrinks as cos(latitude), so near the poles the east-west baseline falls to tens of metres and inflates the slope; both builders documented this. The isotropic column keeps 3.706 km (Earth) and 3.79 km (Moon) in both directions; these baselines are read from the provenance rows, not typed. | Equal to the literal slope at low latitudes; changes polar cells only. No mission uses a p90 slope today. |
| `variables` | label, unit, kind, short definition per mission variable | Display text; definitions summarise the provenance files. | None on scores. Categories are taken from the data. |
| `comparability` | one row per variable (10.3) | Decided from the definitions; **pending team confirmation**. | Which variables enter the similarity and the twin search. |
| `bundle_format`, `bundle_version`, `output_dir` | v2, v2, `../app/public/data/v2` | Compact bundle for a phone (section 11). | Layout only. |
| `earth_land_cells` | `mask_fraction > 0` | The Earth files hold every cell with any land (25,497), so the app can show why a coastal or lake cell fails. | Pure-ocean cells (no land pixel) are absent from the Earth files; they fail every mission. |
| `earth_ocean_fill` | none | The real tables have no fills: a value without land is empty. | - |
| `region_max_place_km` | 111.2 | One 1-degree Earth cell, same rule as the legacy 222.4 km for 2 degrees. | Regions farther than one cell are null. |
| `export_columns` | variables used by any gate, `require_present` or soft criterion | `rain_mm_day` and `wind_max_ms` are named only by rover `workable_days`, which `mission_scoring.py` does not read. | They are described in `variables.json` but not stored (about 0.2 MB saved). |
| `lunar_named_sites` | `real_data/lunar_named_sites.csv` | The lunar sites that matter to the missions. | `lunar_named_sites.json` with each site's cell and per-mission outcome. |
| `credits` | place-name credits | Data credits are added at build time from the provenance files' `licence_credit` text, one entry per product used. | `manifest.json` `credits`. |
| `mission_notes` | per mission | Known limitations of each mission on these tables (10.6). Written after seeing the results; nothing was tuned. | `missions.json` `known_limitations`. |

### 10.2 Levels (from the provenance files)

| variable (column read) | Earth | Moon |
|---|---|---|
| `elevation_m` | MEASURED (ETOPO 2022) | MEASURED (LOLA LDEM_16) |
| `mask_fraction` | MEASURED (ESA CCI land cover) | MODELLED (1 by definition) |
| `slope_300m_deg`, `slope_deg` (`slope_iso_deg`) | DERIVED | DERIVED |
| `rough_300m_m`, `roughness_m` (`roughness_m`) | DERIVED | DERIVED |
| `rock_or_bare_frac` | MEASURED (land-cover share) | MODELLED (1 by definition) |
| `temp_k`, `lst_diurnal_amp_k` | DERIVED (MODIS LST climatology) | DERIVED (Diviner) |
| `tmin_c` | MODELLED (WorldClim, interpolated air) | DERIVED (Diviner surface) |
| `irradiance_kwh_m2_day` | MODELLED (WorldClim srad) | DERIVED (geometry, LOLA lit fraction near the poles) |
| `sun_elev_max_deg`, `sun_low_frac_0_5deg` | DERIVED (formula) | DERIVED (formula) |
| `thermal_inertia_class` | MODELLED (assumed land-cover mapping) | MODELLED ('regolito' everywhere) |
| `permafrost_class` | MODELLED (Obu permafrost probability) | NO_DATA |
| `rain_mm_day`, `wind_max_ms` | MODELLED (WorldClim) | NO_DATA |

Confidence uses these levels with the unchanged rule (section 4) and the 1 km limit for "high", which no 1-degree cell meets. Result: rover "medium" for every ranked cell (0.575); solar 12,717 "medium" (0.525) and 6,060 "low" (0.455: cells with no land surface temperature, whose `lst_diurnal_amp_k` weight is missing); thermal "low" everywhere (0.432-0.445); ice none (no ranked cell). The rover score is limited by the Moon, where `rock_or_bare_frac` is 1 by definition (MODELLED).

### 10.3 Comparability (pending team confirmation)

| variable | status | reason |
|---|---|---|
| `slope_300m_deg`, `slope_deg` | comparable | Same definition (central differences, isotropic baseline, cos-lat weighted mean) and near-equal baselines: 3.706 km (Earth), 3.79 km (Moon). Both are km-baseline slopes. |
| `rough_300m_m`, `roughness_m` | comparable | Same deviogram definition at near-equal lags: 1.853 km (Earth), 1.895 km (Moon). |
| `sun_elev_max_deg`, `sun_low_frac_0_5deg` | comparable | Same formula on both bodies, each with its own obliquity, flat horizon. |
| `irradiance_kwh_m2_day` | comparable with caveat | Daily energy on a horizontal surface on both, but Earth is under the atmosphere and clouds (interpolated climatology) and the Moon has none. |
| `temp_k` | comparable with caveat | Both are mean surface temperatures, but Earth is the mean of two clear-sky overpasses (~10:30, ~22:30) and the Moon a full diurnal mean; no Antarctic Earth values. |
| `lst_diurnal_amp_k` | comparable with caveat | Both describe the daily swing of the surface temperature, but Earth is ~10:30 minus ~22:30, which understates the true daily range, while the Moon is maximum minus minimum. |
| `tmin_c` | not comparable | Earth is an interpolated air temperature; the Moon a surface brightness temperature (there is no air). |
| `rock_or_bare_frac` | not comparable | Earth bare-ground share against a lunar 1 by definition. |
| `thermal_inertia_class` | not comparable | Earth assumed land-cover mapping against 'regolito' everywhere by assumption. |
| `permafrost_class`, `rain_mm_day`, `wind_max_ms` | not comparable | No lunar data. |
| `elevation_m`, `mask_fraction` | not comparable | Geoid against sphere; land share against 1 by definition (gates only). |

Effect: similarity variables are rover `slope_300m_deg`, `rough_300m_m`; solar all six weighted variables; thermal `lst_diurnal_amp_k`, `irradiance_kwh_m2_day` (`tmin_c`, `thermal_inertia_class`, `rock_or_bare_frac`, `permafrost_class` left out); ice `temp_k` (but no lunar cell passes ice). The caveat of every "comparable with caveat" variable is exported with it (`variables.json` `comparability`, `missions.json` `weighted_variables[].comparability_note`). Change: `datasets.json` → `real_1deg` → `comparability`.

### 10.4 Hard filters on the real tables

- The common land gate `elevation_m >= 1` stays Earth-only (`gate_body_applicability`): lunar heights are above a sphere and 43,502 of 64,800 lunar cells are below 1 m. On Earth it now also removes land below sea level (177 land cells for ice, for example) and cells with no land DEM pixel (252 land cells have no `elevation_m`: "no data").
- `mask_fraction >= 0.3` now means "at least 30 % of the cell is land" (ESA CCI; inland water counts as water). 3,275 land cells fail it, including small islands (the Lanzarote and Tenerife benchmark sites).
- **Missing data eliminates the cell** (`on_missing_gate = drop`) with the reason `no data: <variable>`. Cells lost per mission:

| mission | Earth land cells with a missing gated value | of which only because of missing data | main variable | Moon |
|---|---|---|---|---|
| rover | 714 | 0 | `slope_300m_deg` (714), `rough_300m_m` (376) | 0 |
| solar | 720 | 0 | `slope_deg` (714), `elevation_m` (252), `irradiance_kwh_m2_day` (49) | 0 |
| thermal | 6,870 | 6,060 | `lst_diurnal_amp_k` (6,761; 6,581 of them at or south of 60 S: no land surface temperature in Antarctica) | 0 |
| ice | 13,052 | 11,338 | `permafrost_class` (13,013: the Obu maps stop at about 18-25 N and on ice sheets) | **64,800 (all)**: `permafrost_class` has no lunar data |

### 10.5 Known limitations of the real dataset

- **Licences.** WorldClim 2.1 (`tmin_c`, `irradiance_kwh_m2_day`, and the unstored `rain_mm_day`, `wind_max_ms`): "freely available for academic use and other non-commercial use. Redistribution or commercial use is not allowed without prior permission." The v2 bundle ships cell aggregates of `tmin_c` and `irradiance_kwh_m2_day` in `earth_base.bin`; whether a public hackathon app may redistribute them, or whether permission must be asked or the columns dropped, is a **team decision (pending)**. The MODIS LST climatology (`temp_k`, `lst_diurnal_amp_k`; Hengl 2018) is CC BY-SA 4.0: derived data shared from it must carry the same licence. Obu permafrost: CC BY 3.0 (NH) and CC BY 4.0 (Antarctic). ESA CCI land cover: free use with attribution. ETOPO 2022 and the NASA PDS products: no restrictions. Every licence text is exported verbatim (`variables.json` `licence_credit`, `manifest.json` `credits`).
- **Land surface temperature is clear-sky** (cloudy days are missing, biasing warm in cloudy climates) and the mean of two overpasses, not a 24 h mean; the amplitude is a day-minus-night difference that understates the daily range.
- **No land surface temperature in Antarctica** (the product ends near 62 S): 6,581 Antarctic land cells have no `temp_k` or `lst_diurnal_amp_k` and fail thermal with "no data"; in solar the amplitude weight drops out (lower confidence).
- **Cell size.** A cell is 1 degree: 111 km north-south on Earth and 30 km on the Moon. Every value is a cell aggregate (mean, share or percentile of finer pixels). Nothing here describes a landing site or a rover traverse.
- **Thresholds written for 300 m applied at kilometre baselines.** The rover gates and utilities (slope 0.5-15 deg, roughness 5-650 m) were written for a 300 m baseline and are applied **unchanged** to slopes over 3.7-3.8 km and roughness at a 1.85-1.9 km lag. km-baseline slopes are much gentler and km-lag roughness larger than at 300 m, so the gates do not mean what their authors intended. Nothing was adjusted; the true baseline is exported for every relief variable so the interface never says "300 m".
- **Polar strips.** East-west a cell is 111 x cos(lat) km on Earth and 30.3 x cos(lat) km on the Moon: 0.26 km wide next to the lunar pole. A polar cell is a strip that crosses rims, slopes and floors and averages lit ridges with shadowed craters; the best-lit points of the lunar south pole do not appear (real_data/README.md).
- **Earth irradiance is under the atmosphere** (WorldClim surface radiation, at most 6.4 kWh/m2/day) while lunar irradiance is airless (up to 10.4 at the equator): sunny Earth deserts are closest to lunar cells at 51.5-74.5 deg latitude.
- **Ice has no lunar side.** No lunar cell passes the ice mission (no lunar permafrost data), so no Earth cell gets a twin, a similarity, a final score or a rank; only Earth suitability is computed (5,750 passing Earth cells). A lunar cold-trap criterion would be a new team rule.
- **Earth permafrost is empty, not 'ninguno', where the Obu maps have no pixel** (south of about 18-25 N except Antarctic outcrops, ice sheets).
- **`thermal_inertia_class`** on Earth is an assumed mapping from land-cover classes (MODELLED); the dominant class of a coastal cell can be `agua` although at least 30 % of it is land (4,421 land cells fail solar and thermal on `agua`).
- **Earth latitudes are geodetic** (WGS84), not planetocentric: at most 0.19 deg (21 km) apart, a fifth of a cell.
- **No physically-valid ranges** are given by the provenance files, so `validity.json` checks only the grid, coordinates and category vocabularies on these tables.

### 10.6 Results on the real tables (engine 2.0.0; inputs sha256 3eb11d43... and 906de058...)

| mission | Earth pass (of 25,497 land cells) | Moon pass (of 64,800) | ranked | distinct twins | top of the ranking | physically sensible? |
|---|---|---|---|---|---|---|
| rover | 10,337 | 60,988 | 10,337 | 7,215 | Canadian Arctic Archipelago (78.5 N), Russian Arctic, Gobi (Mongolia); top 25: CA 8, DZ 5, MN 4, CN 3, RU 3 | Partly. Bare, km-smooth polar deserts and stony deserts are reasonable trafficability analogs at the km scale (Devon Island's Haughton crater ranks 436), but the ranking is driven by suitability alone: similarity is 97.5-100 for every cell (median 99.95), because two relief variables and 61,000 candidate lunar cells always give a near-exact match. 26 cells tie at final 100.0 and are ordered by cell id (north to south), so the top 25 order carries no information. Rover-scale hazards are not seen at all (10.5). |
| solar | 18,777 | 52,400 | 18,777 | 1,980 | Kimberley (north-western Australia), Somalia, Borkou (Chad), Madagascar; top 25: AU 15, SO 5 | Suitability yes: sunny, flat, low-latitude deserts. Twins no: Earth irradiance under the atmosphere matches airless lunar irradiance only at 51.5-74.5 deg lunar latitude (Manzinus alone is the twin of 2,412 Earth cells), and the lunar polar ridges fail the solar gates (most poleward passing lunar cell 74.5 deg). |
| thermal | 2,419 | 64,800 | 2,419 | 8 | Altiplano and Puna (Bolivia, Chile, Argentina; Atacama ranks 12), Qaidam Basin and Tibetan Plateau (Qinghai); top 25: CL 9, CN 9, BO 4, AR 3 | Earth side yes: high, dry, bare plateaus with cold nights are classic thermal-cycling analogs. Twins no: Earth amplitudes (tens of kelvin, understated) are far below lunar ones (median 266 K), so every Earth cell's twin is one of 8 cells at 87.5 S near Haworth, the lunar cells with the smallest amplitude. |
| ice | 5,750 | 0 | 0 | 0 | none (suitability only: continuous permafrost cells score 100) | No ranking can exist: the lunar side has no permafrost data (10.5). |

Before and after (legacy 2-degree table, section 9): the top solar analog was equatorial Africa and, before engine 1.1.0, the Amazon; the top rover analogs were the Greenland ice sheet and Antarctica. On the real tables the rover top cells are ice-free bare polar deserts and stony deserts (345 of Greenland's 749 land cells, the flat ice-sheet interior, now fail `slope_300m_deg:below_min`, flatter than 0.5 deg at a 3.7 km baseline; 353 Greenland cells still pass and none is in the top 25), and solar moves to arid north-western Australia, Somalia and the Sahara's edge. Thermal moves from Antarctica (formula amplitudes) to the Altiplano and Tibet (MODIS amplitudes; Antarctica has no data).

Analog benchmark (`/home/user/NASA/docs/research/02_analog_benchmark.csv`, 44 sites, `python -m engine report --benchmark ...`): rover 35 of 44 sites pass, best ranks Makhtesh Ramon 368, Merzouga 395, Qaidam 418, Haughton 436 (of 10,337); solar 32 pass, best Pilbara 29 (of 18,777); thermal 14 pass, best Atacama Yungay 12, Qaidam 22, Salar de Pajonales 33 (of 2,419); ice 9 pass (Arctic and subarctic sites) but none can be ranked. Island sites (Lanzarote, Tenerife) fail `mask_fraction` (< 30 % land in their 1-degree cell) and Aquarius Reef Base is under the sea.

## 11. The v2 bundle (choices)

- **Binary, split, on demand.** Per-cell numbers are little-endian Float32 / Int32 arrays indexed in `manifest.json`; the first view (manifest, missions, variables, places, Earth base, the default mission) is 2,282,069 bytes and the whole bundle 9,696,959 bytes. Lunar data, other missions, explanations, nearest places and the IAU table load on demand.
- **Exact recompute.** Utilities and per-variable similarities are stored as Int32 q (value = q / 10^6), scores as q / 100, so the browser decodes the exact published numbers and reproduces suitability, similarity, final and rank (tested on all 37,283 passing cells).
- **Coordinates as grid axes.** `lat` (180 values) and `lon` (360 values) per base file instead of two arrays per cell: exact (cell centres are multiples of 0.5 deg) and 0.2 MB smaller.
- **Per-grid-row columns.** A value column that is constant along every grid row on the whole body (detected from the data: the sun-geometry formulas, and the lunar values set by definition) is stored once per row. Saves 0.2 MB on Earth and 1.3 MB on the Moon; values are unchanged.
- **Moved off the first view.** The country `label_rule` and the nearest populated place (name and distance) are in `earth_place_detail.bin` and `place_detail.json` (on demand); the top 25 cells of `explain.json` carry the nearest place too.
- **Not stored.** `rain_mm_day`, `wind_max_ms` (not used by the engine) and columns with no data on a body (lunar `permafrost_class`); `variables.json` says why.
- **Deterministic.** No clock is read; arrays are in id order; two builds are byte-identical (`test_bundle_is_deterministic` in tests/test_real_data.py).
