# Validation of the shipped analog pairs

Team "Stars Beside You", NASA Space Apps Challenge 2026. Written 2026-11-15 for engine 3.2.0, contract revision 6, dataset `real_1deg` (the bundle in `app/public/data/v2/`). Every number below was computed by the scripts in `tierra luna/validation/` and is in their output tables in `tierra luna/validation/out/`. Nothing in the engine, the configuration, the data or the bundle was changed. Every variant used to measure a sensitivity or an improvement was built in memory.

**Read this first.** There is no ground truth that says which Earth place "really is" the analog of a lunar place. So this document gives no accuracy percentage. Each metric says what it measures, how, on which set, and what it does not show. Section 7 combines the checks into one figure per mission. That figure is a summary of checks. It is **not** a probability that a pair is right.

**Rerun (one command, about 12 minutes on 4 shared CPUs; deterministic, no random numbers, no clock in any output):**

    cd "tierra luna" && python validation/run_all.py && python validation/report_tables.py

Use a Python with the engine's dependencies (`tierra luna/requirements.txt`, `tierra luna/engine/requirements.txt`, plus shapely). This document used `<scratchpad>/stars/venv/bin/python` (Python 3.13). `run_all.py` writes every table and `out/summary.json`. `report_tables.py` turns them into the Markdown tables in `out/tables.md`.

## Summary (one page)

Funnel survivors and paired points of the shipped bundle: Rover 10,337 survivors, 10,192 paired; Solar panels 18,777 survivors, 6,360 paired; Lunar base 2,419 survivors, 450 paired. Only paired points have a rank.

| # | check (what it measures) | Rover | Solar panels | Lunar base |
|---|---|---|---|---|
| 1 | **Coverage**: share of the values behind each ranked point (funnel on Earth, pairing on both sides) that are MEASURED / DERIVED / MODELLED / missing | 27.3 / 72.7 / 0 / 0 % | 13.3 / 73.3 / 13.3 / 0 % | 25.0 / 43.8 / 30.4 / 0.8 % |
| 2 | **Validity**: records passing the schema of section 2 | Earth table 99.985 % (10 of 64,800 fail: 9 negative thermal amplitudes, 1 elevation of -2,569.9 m); Moon table 100 %; bundle files 100 %. The combined CSV `earth_moon_real_1deg.csv` is stale: its 64,800 lunar rows lack the `ninguno` permafrost label (the engine does not read that file). | same | same |
| 3 | **External agreement**: documented analog sites recovered (passes the funnel, has a twin, ranks in the top 25 %) | recall 4 of 10 (40 %), precision 4 of 7 (57 %); 20-80 % recall depending on the definition. `rover_preset.validate_rover_ranking` **fails**: Bardenas scores 82.34 against a median of 91.15 for the mobility analogs | **not measurable**: no benchmark site is documented for solar power | recall 0 of 5 cold sites: all 5 are removed by the amplitude gate (>= 15 K) or have no amplitude value |
| 4 | **Sensitivity**: weights +-20 %, hard thresholds +-10 %, pairing tolerances +-20 % | top 5 keeps >= 4 of 5, top 50 >= 42 of 50; number 1 never changes; at most 604 cells enter and 525 pairs are lost | top 5 >= 4 of 5, top 50 >= 46; number 1 never changes; the irradiance gate moves 1,312 cells but no pair | **fragile**: number 1 changes in 14 of 28 variants; top 50 keeps 29-50 of 50; a +-10 % change of a thermal gate changes 100-306 twins, because the percentiles depend on who passes the funnel |
| 5 | **Reproduction** of the declared counts (solar 5,192, thermal 2,613, both 1,986) | reproduced exactly on the legacy 2-degree table, both by the team module and by an independent recount. The shipped table gives 18,777 / 2,419 / 2,419: it is a different table (1 degree, real data), not an error | | |
| 6 | **Coordinates**: every ranked point checked (not a sample) | centre inside its cell 100 %; centre on Natural Earth land 94.3 %, the cell touches land 99.6 %; country confirmed 99.6 % (40 points not confirmed, all small Arctic or ocean islands missing from the 1:110m polygons, or a neighbouring country's polygon); twin's nearest IAU feature recomputed and equal for 401 of 401 twins | 99.7 % / 100 % / 100 %; 1,704 of 1,704 twins | 100 % / 100 % / 100 %; 103 of 103 twins |
| 7 | **Global figure** (weighted summary of 1-6, section 7; not a probability) | **84.3** | **96.1**, without external agreement, which cannot be measured; read it as an upper bound | **67.2** |

What a jury member should take away:

- The data and the bundle are **internally sound**. Ids, cell centres, ranges, ranks, finals, twin zones and lunar feature labels all check out, with a handful of listed exceptions.
- **Agreement with the outside world is weak and is the binding limit.**
  - Rover recovers 4 of 10 documented mobility analogs in its top quarter, and three "wrong-purpose" sites rank as high.
  - Lunar base recovers none of the five documented cold-region analogs, because its amplitude gate removes them all.
  - Solar panels cannot be checked at all.
- Rover and Solar panels rankings are **stable** under the stated changes. Lunar base is not.
- Eight improvements are listed in section 8, each with its measured effect. Four of them would change a team setting and are proposals only.

---

## 1. Data coverage by provenance level

**How.** Levels come from the team's provenance files `tierra luna/real_data/provenance_earth.csv` and `provenance_moon.csv`. For mission variables they come through the engine's registry, which reads the same files with `column_aliases.json`. A level is never inferred from a column name. A missing value is counted as missing, never as a level. Script: `validation/m1_coverage.py`. Tables: `out/m1_coverage_*.csv`.

**Per body.** The populations are the 25,497 Earth land cells and all 64,800 lunar cells. The columns are the value columns of each table. Bookkeeping columns are left out (pixel counts, `cell_km`, `temp_n_subcells`, `illum_frac_level`, and `lst_diurnal_amp_max_month`, which has no provenance row).

| body | columns | MEASURED | DERIVED | MODELLED | missing |
|---|---|---|---|---|---|
| Earth | 24 | 29.13 % | 37.87 % | 24.88 % | 8.13 % |
| Moon | 22 | 16.67 % | 54.55 % | 18.18 % | 10.61 % |

**Per variable.** Full list in `out/m1_coverage_by_body_variable.csv`.

- **Earth.**
  - MEASURED: `elevation_m`, `mask_fraction`, `rock_or_bare_frac`, `bare_frac`, `snow_ice_frac`, `elevation_all_m` and the land-cover code.
  - DERIVED: slopes, roughness, `temp_k`, `lst_diurnal_amp_k` and the sun-geometry formulas.
  - MODELLED: `tmin_c`, `irradiance_kwh_m2_day`, `rain_mm_day`, `wind_max_ms` (WorldClim), `thermal_inertia_class` (an assumed land-cover mapping) and the permafrost columns.
  - Largest missing shares on land: `permafrost_class` 51.0 % (cells outside the permafrost map); `temp_k` and `lst_diurnal_amp_k` 26.5 % (Antarctica and other cells without MODIS LST); `slope_iso_deg` 2.8 %; `elevation_m` 1.0 %.
- **Moon.**
  - MEASURED: `elevation_m`, `tmax_k`, `tmin_k` and `rock_abundance_frac`. The last is missing on 33.4 % of cells.
  - `rain_mm_day` and `wind_max_ms` are declared "no data" and are empty. They count as missing: 9.1 points of the 10.6 % missing.
  - MODELLED by definition: `mask_fraction`, `rock_or_bare_frac`, `thermal_inertia_class` and `permafrost_class`.

**Per mission.** The set is the values each ranked point actually uses:

- the Earth values of every funnel variable (common gates, required variables, hard filters, weighted variables);
- both sides of every pairing variable, the Earth cell and its twin.

For pairing variables, the level is that of the quantity compared:

- **Lunar `tmin_k` is counted as MEASURED.** It is the Diviner value, which the engine reads back through `tmin_c` + 273.15. The provenance file calls `tmin_c` DERIVED; the engine configuration's text calls it MEASURED.
- **Earth top-of-atmosphere sunlight is DERIVED.** It is a formula of latitude.
- **Relative elevation is DERIVED on both bodies.**

| mission | ranked points | values per point | MEASURED | DERIVED | MODELLED | missing |
|---|---|---|---|---|---|---|
| Rover | 10,192 | 11 | 27.27 % | 72.73 % | 0 % | 0 % |
| Solar panels | 6,360 | 15 | 13.33 % | 73.33 % | 13.33 % | 0 % |
| Lunar base | 450 | 16 | 25.00 % | 43.75 % | 30.43 % | 0.82 % |

**Per ranked point.** The distribution is in `out/m1_coverage_per_ranked_point.csv`. Levels are per column, not per cell, so the shares are the same on every point of Rover and Solar panels. On Lunar base, 59 of the 450 points have no Earth `permafrost_class`. On those points the missing share is 6.25 % and the MODELLED share 25 %; on the others it is 0 % and 31.25 %.

**What it means and what it does not show.**

- Rover rests only on measured and derived values. Its MEASURED share comes from the land gates and the land-cover fraction.
- Lunar base has the most modelled input: the WorldClim air temperature, the assumed surface class and the permafrost labels.
- DERIVED is not "as good as measured". The Earth slope is derived at a 3.7 km baseline and the roughness at a 1.85 km lag, while the rover thresholds were written for 300 m. Coverage does not capture that mismatch; metric 3 shows its effect.

## 2. Validity against a stated schema

**Schema** (`validation/m2_validity.py`, written out as `out/m2_schema.csv`):

- **Every cell table.**
  - `row` is an integer in 0-179 and `col` an integer in 0-359.
  - `lat_deg` is in [-90, 90] and equals 89.5 - row; `lon_deg` is in [-180, 180] and equals -179.5 + col. Both checks are exact to 1e-9: the cell centre is on the grid.
  - `cell_id` equals the prefix (`E` or `M`) followed by row x 360 + col. No `cell_id` or (row, col) pair repeats, and `body` is constant.
- **Physical ranges**, per body and column, with the unit:
  - fractions in [0, 1]; angles in [0, 90] deg; roughness >= 0;
  - Earth land elevation in [-430, 8,849] m (no dry land lies lower or higher);
  - Earth surface temperature in [180, 340] K; a land-surface thermal amplitude >= 0;
  - Earth minimum air temperature in [-90, 35] degC;
  - lunar temperatures in [0, 420] K;
  - lunar irradiance at most S0 x 24 / pi / 1000 = 10.397 kWh/m2/day. That is the equatorial annual mean, with S0 = 1,361 W/m2 as cited in `provenance_moon.csv`.
- **Categories** must belong to the classes used in `mission_scoring.json`.
- **Consistency checks.**
  - Earth ground irradiance <= the sunlight above the atmosphere at the same latitude (the engine's DERIVED value).
  - Lunar `tmin_c` = `tmin_k` - 273.15 to within 0.011.
  - Lunar `tmin_k` <= `temp_k` <= `tmax_k`.
  - No value in the lunar columns declared "no data".
  - The combined table equals the two body tables.
- **Bundle files.**
  - `earth_base.bin`: ids ascending and unique; centres on the grid; country and region indices valid.
  - `earth_<mission>.bin`:
    - the ranks form 1..N;
    - a rank exists exactly when a twin exists;
    - final = 0.5 x similarity + 0.5 x suitability, to within 0.0051;
    - every score lies in 0-100;
    - the rank order is final descending, ties by id;
    - every twin lies in its mission's zone, recomputed independently: Rover lat <= -75; Solar panels |lat| <= 30 and elevation <= -1,200 m; Lunar base region A of `mission_zones.json`.
  - `moon_base.bin`: feature indices valid and distances >= 0.

A missing value is not a failure. Missing values are counted under metric 1.

**Result** (`out/m2_validity_by_table.csv`, every failure in `out/m2_validity_failures.csv`):

| table | records | failing | pass |
|---|---|---|---|
| `earth_real_1deg.csv` | 64,800 | 10 | 99.985 % |
| `moon_real_1deg.csv` | 64,800 | 0 | 100 % |
| `earth_moon_real_1deg.csv` | 129,600 | 64,800 | 50 % |
| `earth_base.bin` | 25,497 | 0 | 100 % |
| `earth_rover.bin` / `earth_solar.bin` / `earth_lunar_base.bin` | 10,337 / 18,777 / 2,419 | 0 | 100 % |
| `moon_base.bin` | 64,800 | 0 | 100 % |

Failures by kind:

- **Earth `lst_diurnal_amp_k` < 0 on 9 cells**, the minimum being -4.6 K at E54133. Three of them also have `lst_diurnal_amp_max_k` < 0. The variable is MODIS 10:30 minus 22:30, so a negative value is possible arithmetically. As a thermal-cycling amplitude it is not meaningful.
- **Earth `elevation_m` = -2,569.9 m on E38522** (17.5 S, 177.5 W), a cell with a land fraction of 0.0002.
- **The combined table differs on `permafrost_class`** in all 64,800 lunar rows. It has no value there, while `moon_real_1deg.csv` carries the label `ninguno` set on 2026-11-14. `ASSUMPTIONS.md` 0.6 already says `build_combined.py` was not rerun. The engine reads the two body tables, never the combined one, so no result is affected.

None of the 10 Earth failures passes any mission's funnel (section 8, P3 and P4).

**What it does not show.** Values inside their physical range can still be wrong. This metric only catches the impossible and the inconsistent.

## 3. External agreement with documented analog sites

**Set.** The 44 sites of `tierra luna/data/benchmark/analog_benchmark.csv`, each with the source URL recorded there.

**Excluded: 15 sites whose coordinates the file itself flags as unverified.** The rule: `coord_quality` contains "from memory", or `source_status` starts with "FROM MEMORY", or `source_status` says the location is from memory. The excluded sites are ES01 Rio Tinto, MA03 Death Valley, MA04 Dumont Dunes, MA09 Axel Heiberg, MA12 Lambahraun, MA15 Erfoud, MA18 Pilbara, BO01 Lonar, MO02 Meteor Crater, MO03 Cinder Lake, MO08 Sudbury, MO09 Mistastin, MO10 Pavilion Lake, OP02 HI-SEAS and OP03 NEEMO. **29 sites are usable.**

**Labels.** Labels come only from keywords in the file's own columns (`validation/m3_external.py`, function `labels`). Nothing is added from memory.

| mission | positive when | negative when | usable sites |
|---|---|---|---|
| Rover | "rover", "mobility" or "traverse" in `analog_type`, `analog_property_for` or `tested_there` | `benchmark_role` = `ops_only_exclude`, or "mobility" or "rover" in `not_analog_for` | 10 positive (ES02, ES04, ES05, ES06, MA01, MA05, MA06, MA11, MO04, MO11) and 5 negative (ES07, ES09, MA02, MA13, OP01) |
| Lunar base | "cold" in `analog_type` or `analog_property_for` | "cold" in `not_analog_for` | 5 positive (MA06, MA07, MA08, MA19, OP01) and 11 negative |
| Solar panels | "solar", "sun", "illumination", "irradiance" or "power" in any of those columns | | none |

**Per site.** A site's cell is the 1-degree cell containing its coordinate. The full table, with the exact funnel reasons and the cell values, is `out/m3_benchmark_sites.csv`. Notation:

- "out:" means eliminated by the funnel, followed by the reason(s);
- "suit" is suitability; "top x %" is the rank divided by the number of ranked points;
- a label in brackets is the site's label for that mission.

| site | cell | land fraction | Rover | Solar panels | Lunar base |
|---|---|---|---|---|---|
| ES02 Lanzarote, Timanfaya | E22126 | 0.10 | [positive] out: land < 30 % | out: land < 30 %, class agua | out: land < 30 %, tmin > 5 C, class agua |
| ES03 Lanzarote, La Corona lava tube | E21766 | 0.04 | out: land < 30 % | out: land < 30 %, class agua | out: land < 30 %, tmin > 5 C, class agua |
| ES04 Tabernas | E18897 | 1.00 | [positive] suit 69.4, final 84.55, top 24.7 % | suit 76.9, no twin (no zone cell within bound) | [negative] suit 20.6, no twin (thermal position) |
| ES05 Teide | E22123 | 0.18 | [positive] out: land < 30 % | out: land < 30 %, class agua | out: land < 30 %, amp < 15 K, tmin > 5 C, class agua |
| ES06 Bardenas Reales | E17098 | 1.00 | [positive] suit 70.4, final 82.34, top 44.5 % | suit 72.6, no twin (no zone cell within bound) | out: amp < 15 K |
| ES07 Barranco del Jaroso | E18898 | 0.61 | [negative] suit 74.4, final 86.37, top 18.5 % | suit 78.8, no twin | out: amp < 15 K |
| ES08 El Soplao | E16735 | 0.41 | suit 54.0, final 76.27, top 89.5 % | out: class agua | out: amp < 15 K, class agua |
| ES09 Laguna de Tirez | E18176 | 1.00 | [negative] suit 76.5, final 77.50, top 85.3 % | suit 79.2, no twin | [negative] suit 21.4, no twin (terrain) |
| MA01 Atacama, Yungay | E41150 | 1.00 | [positive] suit 93.2, final 91.15, top 9.2 % | suit 84.5, final 92.19, top 50.0 % | [negative] suit 73.7, no twin (no single cell meets both) |
| MA02 Salar de Pajonales | E41511 | 1.00 | [negative] suit 73.3, final 84.69, top 23.9 % | suit 77.8, final 88.76, top 75.3 % | [negative] suit 67.1, no twin (no single cell) |
| MA05 MDRS | E18429 | 1.00 | [positive] suit 77.4, final 83.92, top 28.9 % | suit 79.2, no twin | [negative] suit 33.4, final 55.10, top 79.1 % |
| MA06 Haughton, Devon Island | E5130 | 0.76 | [positive] suit 98.9, final 95.44, top 1.7 % | out: irr < 2.5 | [positive] out: amp < 15 K |
| MA07 McMurdo Dry Valleys | E60462 | 0.99 | suit 44.7, final 72.24, top 97.3 % | suit 37.0, no twin | [positive] out: amp missing |
| MA08 Svalbard, Bockfjorden | E3793 | 0.61 | suit 68.3, final 83.05, top 37.3 % | out: irr < 2.5, class agua | [positive] out: amp < 15 K, class agua |
| MA10 Askja | E8803 | 0.98 | suit 96.2, final 94.55, top 2.7 % | out: irr < 2.5 | [negative] out: amp < 15 K |
| MA11 Holuhraun | E9163 | 0.97 | [positive] suit 77.1, final 87.34, top 16.3 % | out: irr < 2.5 | [negative] out: amp < 15 K |
| MA13 Dallol | E27220 | 0.89 | [negative] suit 97.7, final 96.47, top 0.7 % | suit 93.3, final 96.64, top 14.3 % | [negative] out: tmin > 5 C |
| MA14 Qaidam, Lenghu | E18633 | 0.99 | suit 99.0, final 97.77, top 0.2 % | suit 75.7, no twin | suit 68.1, no twin (thermal position) |
| MA16 Makhtesh Ramon | E21454 | 1.00 | suit 99.4, final 92.59, top 6.2 % | suit 88.6, final 88.95, top 74.0 % | suit 41.7, no twin (no single cell) |
| MA17 Dhofar, Marmul | E25795 | 1.00 | out: slope < 0.5, rough < 5 | suit 92.4, final 96.18, top 19.6 % | [negative] out: tmin > 5 C |
| MA19 Kangerlussuaq | E8049 | 0.79 | suit 72.0, final 84.82, top 23.4 % | out: irr < 2.5 | [positive] out: amp < 15 K |
| MA20 Makgadikgadi | E39805 | 1.00 | out: slope < 0.5, rough < 5 | suit 92.8, final 96.39, top 17.5 % | [negative] out: tmin > 5 C |
| MO01 Nordlinger Ries | E14950 | 1.00 | suit 75.0, final 72.19, top 97.4 % | suit 65.2, no twin | out: amp < 15 K |
| MO04 Black Point, SP Mountain | E19508 | 1.00 | [positive] suit 72.6, final 82.45, top 43.2 % | suit 83.1, no twin | suit 35.6, no twin (no single cell) |
| MO05 Mauna Kea and MO06 Kilauea (same cell) | E25224 | 0.75 | suit 64.5, final 81.59, top 51.9 % | suit 76.3, final 88.01, top 79.5 % | [negative] out: tmin > 5 C |
| MO07 Craters of the Moon | E16626 | 1.00 | suit 71.9, final 84.58, top 24.5 % | suit 71.7, no twin | suit 28.1, final 61.64, top 37.8 % |
| MO11 Mount Etna | E18914 | 0.97 | [positive] suit 65.6, final 82.51, top 42.6 % | suit 76.2, no twin | out: amp < 15 K |
| OP01 Concordia, Dome C | E59703 | 1.00 | [negative] out: slope < 0.5, rough < 5 | suit 55.7, no twin | [positive] out: amp missing |

**Precision and recall.** A site is **recovered** under definition D1, the main one, when it passes the funnel, has a lunar twin and ranks in the top 25 % of the mission's ranked list.

- Recall = recovered positives / positives.
- Precision = recovered positives / (recovered positives + recovered negatives).
- "Negatives rejected" = negatives not recovered / negatives.

Both precision and recall are computed **on the benchmark set only**: nothing is known about the thousands of other cells. Sensitivity to the definition is in `out/m3_precision_recall.csv`.

| definition | Rover recall | Rover precision | Rover negatives rejected | Lunar base recall | Lunar base negatives rejected |
|---|---|---|---|---|---|
| D1 funnel + twin + top 25 % | **4 / 10 = 40 %** (ES04, MA01, MA06, MA11) | **57 %** (3 negatives also recovered: ES07, MA02, MA13) | 40 % | **0 / 5** | 100 % |
| D2 top 10 % | 20 % | 67 % | 80 % | 0 | 100 % |
| D3 top 50 % | 80 % | 73 % | 40 % | 0 | 100 % |
| D4 funnel + twin, any rank | 80 % | 67 % | 20 % | 0 | 91 % |
| D5 funnel only | 80 % | 67 % | 20 % | 0 | 55 % |
| D6 funnel + suitability in the top 25 % of survivors (pairing ignored) | 40 % | 67 % | 60 % | 0 | 82 % |

**What it means.**

- **Rover.** The ranking puts documented mobility analogs somewhat above the middle. It separates them poorly from sites documented for other purposes: Dallol (mineralogy and astrobiology) ranks in the top 1 %.
- **Lunar base.** Its funnel removes every documented cold-region analog. Haughton, Svalbard and Kangerlussuaq have a MODIS 10:30 - 22:30 amplitude below 15 K. McMurdo and Concordia have no amplitude at all (no MODIS LST in Antarctica). No definition recovers any of them.
- **Solar panels.** The benchmark documents no solar-power test site, so its external agreement is unknown, not good.

**Rover: `rover_preset.validate_rover_ranking`, reported as it is.** The function is run unchanged on the shipped rover result (`out/m3_rover_preset_check.csv`). Its positive sites are `MOBILITY_POSITIVES`: Bardenas, Tabernas, Dumont Dunes, MDRS, Yungay, Erfoud, Dhofar, Ramon, Haughton, Death Valley, Qaidam. Its negative sites are `MOBILITY_MISMATCHES`: Concordia, NEEMO, HI-SEAS, Rio Tinto, El Soplao. Each site takes the score of the benchmark cell. The check was run with the final score and with suitability, and on all named sites and on the verified coordinates only. **It fails in all four runs, with one problem: "Bardenas scores below the median of mobility analogs".**

- **Bardenas (ES06, cell E17098, 42.5 N 1.5 W).**
  - Values: slope 1.91 deg, roughness 77.0 m, `rock_or_bare_frac` 0.018.
  - Scores: suitability 70.43, final 82.34. The median of the scored positives is 91.15 for the final score (93.19 for suitability).
  - Cause: the 1-degree cell is almost entirely vegetated in ESA CCI land cover, so the bare-ground utility is near 0. That variable carries 25 % of the rover suitability, and the badlands are a small part of a 111 km cell.
- **Dhofar (E25795) and Concordia (E59703)** are removed by the 0.5 deg slope and 5 m roughness minimums. Dhofar has slope 0.143 and roughness 4.85; Concordia 0.043 and 1.09. Those minimums were written for a 300 m baseline. Here they are applied to a 3.7 km slope and a 1.85 km roughness.
- **NEEMO** is a sea cell, with a land fraction of 0.002 and no relief values.
- **The other negatives** all score below the positives' median: HI-SEAS 81.59, Rio Tinto 82.32, El Soplao 76.27.

**Limits, plainly.**

- A 1-degree cell is about 111 km north-south and up to 111 km east-west. It is not a field site: a test site of a few km is one small part of the cell. Three island sites (ES02, ES03, ES05) are in cells under 30 % land, and Mauna Kea and Kilauea share one cell.
- The sets are tiny: 15 labelled sites for Rover and 16 for Lunar base, so one site moves recall by 10-20 points.
- Most sites were chosen for reasons the tables do not hold: mineralogy, astrobiology, operations, crater geology, lava tubes.
- The labels come from keywords, not from an expert reading.

## 4. Sensitivity per mission

**How** (`validation/m4_sensitivity.py`). Every variant is a deep copy of the configuration, run through the engine's own `run_mission` in memory. Three families of changes:

- **(a) Weights.** Each suitability weight x1.2 and x0.8, all weights then renormalised to their original sum. Pairing does not depend on the weights.
- **(b) Thresholds.** Each numeric hard threshold x0.9 and x1.1: the common gates and the mission's gates, min or max. For Lunar base, its `thermal` core is changed with it, as the engine requires. The category gate (`thermal_inertia_class` excludes `agua`) has no number and was not varied.
- **(c) Tolerances.** Each pairing tolerance x0.8 and x1.2. Its filter bound follows (1x for a key variable, 2x for a secondary one).

Measures:

- overlap of the top 5 and the top 50 with the shipped ranking;
- Spearman correlation on the points ranked in both lists;
- whether the number 1 pair (Earth cell and twin) changes;
- cells entering or leaving the funnel;
- pairs gained or lost, and twins changed on kept pairs.

Number 1 of the shipped bundle: Rover E17566 with M59895 (41.5 N 106.5 E, Inner Mongolia); Solar panels E38464 with M24296; Lunar base E17538 with M63528.

**(a) Weights** (`out/m4_sensitivity_weights.csv`, 30 variants):

| mission | variants | worst top-5 overlap | worst top-50 overlap | lowest Spearman (all) | number 1 changes |
|---|---|---|---|---|---|
| Rover | 6 | 5 / 5 | 48 / 50 | 0.995 | 0 |
| Solar panels | 12 | 4 / 5 | 46 / 50 (irradiance x0.8) | 0.997 | 0 |
| Lunar base | 12 | 3 / 5 (`tmin_c` x0.8) | 44 / 50 | 0.996 | **6** |

**(b) Hard thresholds** (`out/m4_sensitivity_thresholds.csv`, 32 variants; only the changes that move something are listed):

| mission | threshold | x0.9: enter / leave, pairs +/- | x1.1: enter / leave, pairs +/- | number 1 |
|---|---|---|---|---|
| Rover | `mask_fraction` >= 0.3 (common) | +118 / 0, pairs +118 | 0 / -112, pairs -112 | same |
| Rover | slope >= 0.5 deg | +604 / 0, pairs +429 | 0 / -483, pairs -418 | same |
| Rover | slope <= 15 deg | 0 / -1, pairs -1 | no change | same |
| Rover | roughness 5-650 m, elevation >= 1 m | no change | no change | same |
| Solar panels | irradiance >= 2.5 kWh/m2/day | +1,312 / 0, **pairs unchanged** | 0 / -1,316, **pairs unchanged** | same |
| Solar panels | slope <= 15 deg | 0 / -1 | no change | same |
| Solar panels | sun elevation, low-sun share, mask, elevation | no change | no change | same |
| Lunar base | amplitude >= 15 K | +407 / 0; pairs 450 -> 529 (+137 / -58); 306 kept pairs change twin; top 50 keeps 31 | 0 / -421; pairs 450 -> 347 (+73 / -176); 230 change twin; top 50 keeps 29 | **changes** both ways |
| Lunar base | `tmin_c` <= 5 degC | 0 / -164; pairs 450 -> 441; 127 change twin | +151 / 0; pairs 450 -> 451; 100 change twin | **changes** both ways |
| Lunar base | `mask_fraction`, elevation (common) | no change | no change | same |

**(c) Pairing tolerances** (`out/m4_sensitivity_tolerances.csv`, 20 variants):

| mission | tolerance (role) | x0.8: pairs | x1.2: pairs | number 1 |
|---|---|---|---|---|
| Rover | slope 2 deg (key) | 10,192 -> 10,185 (-7) | unchanged | same |
| Rover | roughness 30 m (key) | -> 9,667 (-525) | -> 10,299 (+107) | same |
| Rover | relative elevation 500 m (secondary) | -> 9,863 (-329) | -> 10,299 (+107) | same |
| Solar panels | sunlight above the atmosphere 0.6 kWh/m2/day (key) | 6,360 -> 5,956 (-404) | -> 6,546 (+186) | same |
| Solar panels | slope 2 deg, roughness 30 m (secondary) | unchanged | +0 / +1 | same |
| Lunar base | `tmin_k` 10 percentile points (key) | 450 -> 425 (-25) | -> 469 (+19) | changes at x1.2 |
| Lunar base | amplitude 10 points (key) | -> 420 (-30) | -> 483 (+33) | changes at x0.8 |
| Lunar base | slope 2 deg (secondary) | -> 445 (-5) | -> 453 (+3) | changes at x1.2 |
| Lunar base | roughness 30 m (secondary) | -> 392 (-58) | -> 530 (+80) | changes at x1.2 |

Even when the pair count does not change, tolerances change which twin is chosen: 12-1,395 kept pairs per variant (column `twin_changed_on_kept_pairs`).

**What it means.**

- **Rover and Solar panels.** The top of the ranking is robust to every stated change: the number 1 pair never moves, and the top 50 keeps at least 42 of 50. The Rover counts move mostly with the slope minimum and the roughness tolerance. The Solar panels counts move with the irradiance tolerance.
- **Lunar base is fragile.** When the population passing the funnel changes, every Earth point's percentile changes, and the pairs are reshuffled. Small changes of the two thermal gates, of the weights or of the tolerances change its number 1 in 14 of 28 variants. Its top 50 then keeps as few as 29 of 50.
- **What this does not show:** whether the shipped values are the right ones. It only shows how much the result depends on them.

## 5. Reproduction of the declared counts

**How** (`validation/m5_reproduction.py`).

- The declared counts are solar 5,192, thermal 2,613 and both 1,986.
- They were recomputed on the legacy table, `output_py/earth_moon_harmonized_clean.csv`: 16,200 Earth rows on a 2-degree grid, 5,927 land cells with elevation >= 1.
- Two configurations: `mission_scoring.json` as committed at 618bc45 (`git show`; `on_missing_gate` "keep"), and the current file ("drop"; `lunar_base` = thermal).
- Two methods: the team module `mission_scoring.evaluate`, unchanged, and the script's own gate code.
- The same was done on the shipped table.

| table | configuration | method | solar | thermal / lunar_base | both |
|---|---|---|---|---|---|
| legacy 2-degree | committed (keep) | team module | 5,192 | 2,613 | 1,986 |
| legacy 2-degree | committed (keep) | own code | 5,192 | 2,613 | 1,986 |
| legacy 2-degree | current (drop) | team module and own code | 5,192 | 2,613 | 1,986 |
| real 1-degree (shipped) | current | engine and own code | 18,777 | 2,419 | 2,419 |
| real 1-degree (shipped) | committed (keep) | own code | 18,777 | 2,419 | 2,419 |

**Result.**

- **The declared counts are reproduced exactly on the legacy table**, by both methods and under both configurations. No cell of that table passes only because a gated value is missing, so "keep" and "drop" give the same counts. This agrees with the finding in `docs/AUDIT.md` (Summary item 5), recomputed here, not copied.
- **The shipped numbers differ because the table differs:** 1-degree real data, 25,497 land cells instead of 5,927. It is not a fault.
  - **Solar.** 73.6 % of the real land cells pass, against 87.6 % of the legacy ones. The largest removals are the `agua` class on 4,421 cells, irradiance < 2.5 on 3,462 and land < 30 % on 3,275 (`out/m5_shipped_failure_reasons.csv`).
  - **Thermal / Lunar base.** 9.5 % pass, against 44.1 %.
    - The amplitude gate (>= 15 K) holds on 59.8 % of the legacy land cells, where the amplitude is a latitude formula of 8.9-38.8 K. It holds on only 17.8 % of the real land cells, where it is MODIS 10:30 - 22:30 (-4.6 to 35.7 K) and is missing on 26.5 % of cells (`out/m5_gate_shares.csv`).
    - The gate removes 14,188 real land cells, and 6,761 more have no amplitude.
  - **"Both" equals the Lunar base count** on the shipped table: every Lunar base survivor also passes solar. On the legacy table, 76 % of the thermal survivors (1,986 of 2,613) also passed solar.

## 6. Coordinates: every ranked point falls where it says

**How** (`validation/m6_coordinates.py`). **Every** ranked point was checked, not a sample: 10,192 + 6,360 + 450.

- **(a) Cell.** The stored centre lies inside the cell its id names.
- **(b) Land.** The centre is tested against the Natural Earth 1:110m admin-0 polygons in `engine/data` (`ne_110m_admin_0_countries.geojson`), with the script's own shapely point-in-polygon. The engine's labelling code is not used. For a centre outside every polygon, the script checks whether any polygon touches the 1-degree square.
- **(c) Country.** The country the bundle names must equal the polygon containing the centre: same ISO code, or same `ADMIN` name where Natural Earth has no ISO code. For a centre outside every polygon, the named country's polygon must touch the cell. Cells labelled Antarctica (rule `antarctic_treaty_area`) are checked for latitude only.
- **(d) Region.** The repository holds no admin-1 polygons, so **the region was not checked against polygons**. The bundle's region is the GeoNames admin-1 of the nearest populated place. Only its presence and the distance to that place are reported.
- **(e) Lunar features.** Each twin's nearest named feature and its distance were recomputed with the script's own great-circle code from `engine/data/iau_moon_nomenclature.csv`. It uses the 1,737.4 km sphere and the `Satellite Feature` exclusion stated in `engine_config.json`.

| check | Rover | Solar panels | Lunar base |
|---|---|---|---|
| points checked | 10,192 | 6,360 | 450 |
| centre inside its cell | 10,192 (100 %) | 6,360 | 450 |
| centre on Natural Earth land | 9,610 (94.3 %) | 6,339 (99.7 %) | 450 |
| centre off land, but land polygon touches the cell | 542 | 21 | 0 |
| no land polygon in the cell | 40 | 0 | 0 |
| country = polygon at the centre | 8,668 | 6,339 | 450 |
| country = polygon touching the cell | 383 | 21 | 0 |
| labelled Antarctica, latitude correct | 1,101 of 1,101 | 0 | 0 |
| **country not confirmed** | **40 (0.4 %)** | 0 | 0 |
| region labelled; median / P90 km to the place it comes from | 6,108 (59.9 %); 61.5 / 1,338 km | 4,432 (69.7 %); 52.0 / 210 km | 428 (95.1 %); 25.2 / 65 km |
| distinct twins; nearest IAU feature and distance recomputed and equal (to within 0.1 km) | 401 / 401; median 59.4 km, max 189.3 km | 1,704 / 1,704; median 53.5 km, max 186.3 km | 103 / 103; median 26.5 km, max 60.0 km |

**The 40 unconfirmed Rover points** (`out/m6_coordinate_failures.csv`) all carry a label from the nearest GeoNames place:

- **17 cells that no 1:110m polygon touches.** They are small islands missing from that scale: 8 Russia, 3 Canada, 3 United States, 1 each for Ecuador, South Georgia and Indonesia.
- **7 cells labelled Svalbard & Jan Mayen next to the "Norway" polygon.** Natural Earth includes Svalbard in Norway, so these are consistent.
- **16 cells labelled with a country other than the polygon touching the cell.** **Probably wrong:** 8 "Iceland", 2 "Canada" and 1 "Svalbard" on cells that touch only Greenland. The others: 2 "Argentina" touching Chile; 1 "St Pierre & Miquelon" touching Canada; 1 "Ukraine" touching the polygon the 1:110m file assigns to Russia (Crimea); 1 "Somalia" touching Somaliland.

**What it means.** The ranked points are where their ids say, and their countries are confirmed except for small high-latitude islands and a few border or Arctic cells. The 1:110m polygons are coarse (a 1:110,000,000 map scale), so "centre off land" mostly means a coastal cell. The region label is unchecked.

## 7. One global figure per mission

**Read this first: it is a summary of checks, not a probability of being right.**

**Components.** Each component is a 0-100 score read from the tables above (`validation/m7_global.py`, `out/m7_global.csv`).

| component | weight | definition | why this weight |
|---|---|---|---|
| external agreement | 0.25 | recall under D1 (section 3) | the only check against knowledge from outside the team's own tables and code, so it weighs most. Not a majority, because the set is tiny and its labels come from keywords |
| coverage | 0.20 | share of the values behind the ranked points that are MEASURED or DERIVED (section 1) | how much of what is ranked rests on data rather than on models |
| stability | 0.20 | mean top-50 overlap over every variant of section 4, as % of 50 | a top that flips under +-10-20 % changes of design values cannot be presented with confidence |
| validity | 0.15 | record-weighted pass share of the tables the mission reads: the two body tables, `earth_base.bin`, `earth_<mission>.bin`, `moon_base.bin` (section 2) | a necessary condition, near 100 % by construction (the engine validates its inputs), so weighted lower so it does not inflate the figure |
| coordinates | 0.15 | share of ranked points whose country is confirmed x share of twins whose nearest feature agrees (section 6) | same reason as validity |
| reproduction | 0.05 | declared counts reproduced on the legacy table (section 5) | about the team's earlier claims, not the shipped result |

A component that cannot be measured is left out and the other weights are renormalised. That happens for Solar panels' external agreement.

| mission | external | coverage | stability | validity | coordinates | reproduction | **global** | global without external |
|---|---|---|---|---|---|---|---|---|
| Rover | 40.0 | 100.0 | 96.9 | 100.0 | 99.6 | 100 | **84.3** | 99.1 |
| Solar panels | not measurable | 86.7 | 98.6 | 100.0 | 100.0 | 100 | **96.1** (upper bound) | 96.1 |
| Lunar base | 0.0 | 68.8 | 92.4 | 100.0 | 100.0 | 100 | **67.2** | 89.6 |

**How to read it.**

- The internal components are high for every mission. **The external one decides the figure.** Without it every mission would look excellent, which is not what the evidence says.
- The Solar panels figure is high only because its external agreement could not be measured.
- For Rover, coverage counts DERIVED values as full. The baseline mismatch of the slope and roughness (section 1) lowers only the external component, through its effect on the documented sites.

## 8. Improvements the measurements suggest

Each improvement's effect was computed in memory (`validation/m8_improvements.py`, `out/m8_improvements.csv`). **TEAM SETTING** marks a change to a team threshold, weight or tolerance: it is a **proposal for the team lead only, not applied**. The others change no team setting.

| id | change | type | measured effect |
|---|---|---|---|
| P1 | Rover: drop the minimums slope >= 0.5 deg and roughness >= 5 m, keeping the maxima. They were written for a 300 m baseline, and the table's slope is at 3.7 km and its roughness at 1.85 km (`column_aliases.json` caveat) | **TEAM SETTING (threshold)** | funnel 10,337 -> 22,185; pairs 10,192 -> 15,132 (+4,940, none lost). Dhofar (AMADEE-18) enters and ranks 1,691 of 15,132 (top 11 %). Concordia enters but finds no twin. Benchmark D1 unchanged (recall 40 %, precision 57 %). `validate_rover_ranking` still fails on Bardenas |
| P2 | Rover: weight of `rock_or_bare_frac` 0.25 -> 0. A 1-degree land-cover share is near 0 at Bardenas (0.018), Tabernas and Death Valley | **TEAM SETTING (weight)** | `validate_rover_ranking` then **passes**, but D1 recall falls 40 -> 20 % (precision 50 %), and only 10 of the top 50 stay. The two external checks disagree, so tuning to about ten sites is not advised. Shown to make the trade-off visible |
| P3 | Mark Earth `lst_diurnal_amp_k` < 0 (9 cells) as invalid | no team setting (validity flag) | no effect on any ranking today: none of the 9 cells passes Solar panels or Lunar base. It guards future data |
| P4 | Mark Earth `elevation_m` < -430 m as invalid (E38522, -2,569.9 m, land fraction 0.0002) | no team setting (validity flag) | no effect today: the cell passes no funnel |
| P5 | Verify the 15 benchmark coordinates flagged as unverified | no team setting (benchmark) | an upper bound, counting them all as confirmed: Rover D1 recall 40 -> 46.7 %, precision 57.1 -> 63.6 %; Lunar base stays at 0 % |
| P6 | Lunar base: amplitude gate 15 K -> 13.5 K (x0.9), or -> 0 K. The Earth amplitude is MODIS 10:30 minus 22:30, which understates the daily range | **TEAM SETTING (threshold)** | at 13.5 K: funnel 2,419 -> 2,826, pairs 450 -> 529, number 1 changes, cold sites recovered still 0 of 5. At 0 K: funnel 9,981, pairs 2,109, 1 of 5 cold sites recovered (MA19 Kangerlussuaq), precision 100 % on that set |
| P7 | Lunar base: tolerance of the two thermal keys 10 -> 12 percentile points | **TEAM SETTING (tolerance)** | `tmin_k`: pairs 450 -> 469 (+19), number 1 changes. Amplitude: 450 -> 483 (+33), number 1 same. Only 18.6 % of the survivors have a twin today |
| P8 | Solar panels: tolerance of the sunlight above the atmosphere 0.6 -> 0.72 kWh/m2/day | **TEAM SETTING (tolerance)** | pairs 6,360 -> 6,546 (+186), number 1 same. Only 33.9 % of the survivors have a twin today |
| P9 | Rebuild `output_real/earth_moon_real_1deg.csv` with `real_data/build_combined.py`, so the lunar `permafrost_class` matches the body table | no team setting (data) | removes the 64,800 validity failures of section 2; no effect on the engine, which does not read that file. Not done here (file not owned) |
| P10 | Country label fallback for cells whose centre is off the 1:110m polygons: use the polygon that touches the cell before the nearest GeoNames place | no team setting (labels) | would relabel 16 Rover points, 11 of them on cells that touch only Greenland. Not computed against a finer polygon file, which is not in the repository |
| P11 | Lunar base: make the percentile population independent of the funnel, for example the whole Earth land with a value | **TEAM SETTING (pairing rule)** | not computed. It is suggested by section 4: today a 10 % change of a gate reshuffles 100-306 twins. Listed for the team lead without a measured effect |

## What was not done

- **Regions.** The region (admin-1) labels were not checked against polygons: the repository has no admin-1 polygons. Only their presence and the distance to their source place are reported.
- **Solar panels external agreement** cannot be measured: no benchmark site is documented for solar power. A solar test site list with sources would be needed.
- **Unverified benchmark sites.** 15 of the 44 sites were left out because the benchmark file flags their coordinates as unverified. P5 gives the most their verification could change.
- **Category gates** (`thermal_inertia_class` exclude `agua`) were not varied in section 4: they have no number to change by 10 %. The weights of the pairing variables were not varied either; the task asked for suitability weights.
- **Proposal P11** has no measured effect.
- **The combined CSV was not rebuilt (P9).** This document owns no data files.
- **The legacy bundle** (`build/legacy_2deg`) was not checked for coordinates. Only its counts were reproduced (section 5).
- **The old web counts quoted in `docs/AUDIT.md`** (solar 5,198, thermal 3,337, from `mission_filters.json`) were not recomputed.

## Files

| file | content |
|---|---|
| `tierra luna/validation/run_all.py` | runs metrics 1-8 and writes `out/summary.json` |
| `validation/common.py` | paths, the engine call, the in-memory variant runner |
| `validation/m1_coverage.py` ... `m8_improvements.py` | one script per section; each also runs alone (`python validation/m3_external.py`) |
| `validation/report_tables.py` | Markdown tables from the outputs (`out/tables.md`) |
| `validation/out/*.csv` | every table quoted above, with every failure listed |
