# Validation of the shipped analog pairs (corrected model)

Team "Stars Beside You", NASA Space Apps Challenge 2026. Written 2026-11-15 for the **corrected model**: engine 3.4.0, contract revision 8, criteria set `corrected` for all three missions (`engine_config.json` `criteria_sets`), dataset `real_1deg`, bundle `app/public/data/v2/`. It replaces this morning's version, which described contract revision 6.

**Where the numbers come from.** Each number carries its source:

- **[V-mN]**: recomputed for this document by `tierra luna/validation/mN_*.py`, output table in `tierra luna/validation/out/`. These scripts call the engine's own `engine.build.compute` (the same call as `python -m engine build`, so the corrected criteria sets are applied). Every variant used for a sensitivity is built in memory as a deep copy. Nothing in the engine, the configuration, the data or the bundle was changed.
- **[A-file]**: taken from an independent audit or re-audit made today on the same corrected model (commit d24ebb3), in `docs/stats_audit/`. Those reviewers wrote their own code (`tierra luna/audit/`), which does not import the engine. `9_reauditoria_rover.md` and `9_reauditoria_base.md` are on this branch; `9_reauditoria_solar.md` (final verdict, commit 89a5c52) is on branch `audit-solar` (`git fetch origin audit-solar`).

**Read this first.** There is no ground truth that says which Earth place "really is" the analog of a lunar place. So this document gives **no accuracy percentage**. Each metric says what it measures, on which set, and what it does not show. Section 7 combines the checks into one figure per mission. That figure is a **summary of checks, not a probability that a pair is right**.

## Summary (one page)

Funnel survivors and pairs in the shipped bundle: Rover 10,337 survivors, all 10,337 paired; Solar panels 18,777 survivors, 6,360 paired; Lunar base 2,419 survivors, 450 paired. Only paired points have a rank with a lunar twin.

| # | check (what it measures) | Rover | Solar panels | Lunar base |
|---|---|---|---|---|
| 1 | **Coverage**: share of the values behind each ranked point that are MEASURED / DERIVED / MODELLED / missing [V-m1] | 33.3 / 66.7 / 0 / 0 % | 12.5 / 75.0 / 12.5 / 0.002 % | 26.7 / 46.7 / 26.7 / 0 % |
| 2 | **Validity**: records passing the schema (units, ranges, grid, consistency, bundle rules) [V-m2] | 251,420 of 251,430 records (99.996 %) over the two tables and the bundle; the 10 failures are Earth cells that pass no funnel | same | same |
| 3 | **External agreement**: documented analog sites in the top 25 % of the ranking (recall; precision over the listed sites) [V-m3, V-m9] | `rover_preset.py` list: recall **6 of 11 (54.5 %)**, precision 100 %; team benchmark: 4 of 10 (40 %), 66.7 %. `validate_rover_ranking` **fails** (Bardenas below the median) | BSRN stations: recall **6 of 13 (46.2 %)**, precision 100 %; but no better than latitude within a latitude row | recognised habitat and polar analogs: **0 of 13**; only 3 of 13 pass the funnel (amplitude gate >= 15 K) |
| 4 | **Sensitivity**: weights +-20 %, hard thresholds +-10 % [V-m4] | top 50 keeps >= 42 of 50; number 1 never changes; at most 604 cells enter, 483 leave | top 50 >= 45; number 1 never changes; irradiance gate moves 1,312 cells but no pair | weights: number 1 never changes, top 50 >= 47; **thermal gates +-10 %: number 1 changes in 4 of 4, top 50 keeps 29-40, 100-306 twins change** |
| 5 | **Reproduction** of the declared counts (solar 5,192, thermal 2,613, both 1,986) [V-m5] | **reproduced exactly** on the legacy 2-degree table they come from, by the team module and by independent code. The shipped real 1-degree table gives solar (= Solar panels) 18,777 / thermal (= Lunar base) 2,419 / both 2,419 (Rover, 10,337, is not one of these three counts): different data, not an error | | |
| 6 | **Coordinates**: every ranked point checked [V-m6] | centre in its cell 100 %; country confirmed 99.52 % (50 small Arctic or coastal cells not); twin's nearest IAU feature recomputed equal 1,144 of 1,144 | 100 %; 100 %; 1,704 of 1,704 | 100 %; 100 %; 103 of 103 |
| 7 | **Global figure** (weighted summary of 1-6; **not a probability**) [V-m7] | **86.5** | **83.7** | **68.1** |

What a jury member should take away:

- The data and the bundle are **internally sound**: grid, ranges, ranks, finals, twin zones, countries and lunar feature names check out, with 10 listed invalid records that no mission uses.
- **Agreement with the outside world is the binding limit.** About half the documented Rover and solar test sites rank in the top quarter, with no listed negative there; the Lunar base funnel keeps out 10 of 13 recognised habitat and polar analogs by design (its thermal-cycling gate).
- **The Rover order is the team's suitability** (almost every pair is within the measurement uncertainty), and the Solar panels order is no better than latitude for the reference stations. Rover and Solar panels are stable to the stated changes; Lunar base is fragile to its two thermal gates.
- Six corrections were applied today after the audit (section 8), each with its before and after; five proposals that would change a team criterion are listed and not applied.

---

## 1. Data coverage by provenance level [V-m1]

**How.** The levels come from the team's provenance files `tierra luna/real_data/provenance_earth.csv` and `provenance_moon.csv`. For mission variables they come through the engine's registry, which reads the same files (plus the provenance of the supplementary column `clear_frac_isccp`). A level is never inferred from a column name. A missing value is counted as missing, never as a level. Script `validation/m1_coverage.py`; tables `out/m1_coverage_*.csv`.

**Per body.** The population is the 25,497 Earth land cells and all 64,800 lunar cells, over the value columns of each table (bookkeeping columns such as pixel counts are left out).

| body | columns | MEASURED | DERIVED | MODELLED | missing |
|---|---|---|---|---|---|
| Earth | 24 | 29.13 % | 37.87 % | 24.88 % | 8.13 % |
| Moon | 22 | 16.67 % | 54.55 % | 18.18 % | 10.61 % |

Per variable (`out/m1_coverage_by_body_variable.csv`):

- **Earth.** MEASURED: elevation, land fraction, bare and rock fraction, snow and ice fraction, land-cover code (ESA CCI, ETOPO 2022). DERIVED: slopes, roughness, MODIS surface temperature and its 10:30-22:30 amplitude, the sun-geometry formulas. MODELLED: WorldClim minimum air temperature, irradiance, rain and wind; the thermal-inertia class (an assumed land-cover mapping); permafrost. Largest missing shares: permafrost 51.0 % (cells outside the map), MODIS temperature and amplitude 26.5 % (Antarctica and other cells without MODIS LST), slope 2.8 %, elevation 1.0 %.
- **Moon.** MEASURED: LOLA elevation, Diviner `tmax_k`, `tmin_k` and rock abundance (rock abundance missing on 33.4 % of cells). Rain and wind are declared "no data" on the Moon and count as missing: 9.1 of the 10.6 points missing.

**Per mission.** The values each ranked point actually uses: the Earth value of every funnel variable (common gates, required variables, hard filters, weighted variables) and both sides of every pairing variable (the Earth cell and its twin).

| mission | ranked points | values per point | MEASURED | DERIVED | MODELLED | missing |
|---|---|---|---|---|---|---|
| Rover | 10,337 | 9 | 33.33 % | 66.67 % | 0 % | 0 % |
| Solar panels | 6,360 | 16 | 12.50 % | 75.00 % | 12.50 % | 0.002 % (2 points lack `clear_frac_isccp`) |
| Lunar base | 450 | 15 | 26.67 % | 46.67 % | 26.67 % | 0 % |

Per ranked point (`out/m1_coverage_per_ranked_point.csv`): levels are per column, so the shares are the same on every ranked point, except the 2 Solar panels points without a cloud value (6.25 % missing on those two).

**Before and after.** This morning Rover used 11 values per point (relative elevation included), Solar panels 15 and Lunar base 16 with 30.4 % MODELLED and 0.8 % missing (59 points without permafrost). The corrections removed the MODELLED WorldClim irradiance and the permafrost class from the suitability sums; Lunar base now has **no missing value** and 26.7 % MODELLED (minimum air temperature and thermal-inertia class, plus irradiance as a gate).

**What it does not show.** A MEASURED value can still be coarse: every value is a 1-degree aggregate.

## 2. Validity against a stated schema [V-m2]

**Schema** (`validation/m2_validity.py`, written out as `out/m2_schema.csv`):

- **Every cell table:** `row` integer 0-179, `col` 0-359; `lat_deg` = 89.5 - row and `lon_deg` = -179.5 + col to 1e-9 (the centre is on the grid); `cell_id` = prefix + row x 360 + col, unique; `body` constant.
- **Physical ranges, with units:** fractions in [0, 1]; angles in [0, 90] deg; roughness >= 0; Earth land elevation in [-430, 8,849] m; Earth surface temperature in [180, 340] K; land-surface thermal amplitude >= 0; Earth minimum air temperature in [-90, 35] degC; lunar temperatures in [0, 420] K; lunar irradiance <= 10.397 kWh/m2/day (S0 = 1,361 W/m2, equatorial annual mean).
- **Categories** belong to the classes used in `mission_scoring.json`.
- **Consistency:** Earth ground irradiance <= sunlight above the atmosphere at that latitude; lunar `tmin_c` = `tmin_k` - 273.15 to 0.011; lunar `tmin_k` <= `temp_k` <= `tmax_k`; no value in a lunar column declared "no data".
- **Bundle files:** ids ascending and unique, centres on the grid, valid country and region indices (`earth_base.bin`); ranks form 1..N, a rank exists exactly when a twin exists, final = 0.5 x similarity + 0.5 x suitability to 0.0051, every score in 0-100, rank order = final descending with ties by id, every twin inside its mission's zone recomputed independently (`earth_<mission>.bin`); valid feature indices and distances (`moon_base.bin`).

A missing value is not a failure (it is counted in section 1).

| table | records | failing | pass |
|---|---|---|---|
| `earth_real_1deg.csv` | 64,800 | 10 | 99.985 % |
| `moon_real_1deg.csv` | 64,800 | 0 | 100 % |
| `earth_base.bin` | 25,497 | 0 | 100 % |
| `earth_rover.bin` / `earth_solar.bin` / `earth_lunar_base.bin` | 10,337 / 18,777 / 2,419 | 0 | 100 % |
| `moon_base.bin` | 64,800 | 0 | 100 % |
| **all records** | **251,430** | **10** | **99.996 %** |

The 10 failures (`out/m2_validity_failures.csv`): 9 Earth cells with a negative MODIS amplitude (minimum -4.6 K at E54133; the variable is 10:30 minus 22:30, so a negative value is possible arithmetically but meaningless as a thermal cycle) and E38522 with an elevation of -2,569.9 m on a land fraction of 0.0002. **None of the 10 passes any funnel**, so no ranked point is affected.

**Change since this morning.** The combined table `earth_moon_real_1deg.csv`, which failed on all its 64,800 lunar rows (stale permafrost label), has been removed from the repository; the engine never read it. The check skips it when it is absent.

**What it does not show.** A value inside its physical range can still be wrong. This metric catches the impossible and the inconsistent only.

## 3. External agreement with documented analog sites [V-m3, V-m9]

There is no list of "correct" pairs. What exists is a short list of places that NASA, ESA and others have documented as analogs for a purpose. The question is: does the ranking put those places high, for the mission they were used for?

**Definitions (stated once, used for every list).**

- A site is located by the 1-degree cell that contains its published coordinate.
- **Predicted positive at threshold T**: the cell passes the mission funnel, has a lunar twin, and its published rank is within the best T % of the mission's ranked (paired) list. T = 25 % is the main definition; 10 %, 50 % and "paired at any rank" are also reported.
- **Recall** = positives predicted positive / all positives on the list.
- **Precision** = positives predicted positive / all sites of the list predicted positive (positives plus negatives). The thousands of unlabelled cells of the ranking are not counted: precision says only whether the listed negatives are kept out of the top.
- Sites whose coordinate the benchmark file marks as written from memory are reported separately ("verified only").

**The lists.**

1. **Rover, `rover_preset.py`** (the positive and negative names used by `validate_rover_ranking`): 11 mobility analogs (Bardenas, Tabernas, Dumont Dunes, MDRS, Yungay, Erfoud, Dhofar, Ramon, Haughton, Death Valley, Qaidam) and 5 operations or mineralogy analogs as negatives (Concordia, NEEMO, HI-SEAS, Rio Tinto, El Soplao). Located through the team benchmark `data/benchmark/analog_benchmark.csv`.
2. **Rover and Lunar base, team benchmark** `analog_benchmark.csv` (44 sites with source URLs; labels from keywords in its own columns, rule in `m3_external.py`): Haughton, Black Point Lava Flow (D-RATS), Mauna Kea (PISCES), Atacama, Holuhraun, Etna and others.
3. **Solar panels, `validation_sites_solar.csv`** (research r4): 13 BSRN reference radiation stations in arid climates or on mountain tops as positives, 6 low-sunshine Met Office stations as negatives.
4. **Lunar base, `validation_sites_lunar_base.csv`** (research r4): 13 recognised habitat, cold and polar analogs (Concordia, Haughton, McMurdo, Svalbard, Kangerlussuaq, Mauna Kea, Teide, MDRS, Askja, Black Point, Craters of the Moon, Timanfaya, Neumayer/EDEN ISS) as positives, 7 humid tropical stations as negatives.

**Result** (`out/m9_precision_recall.csv`, `out/m3_precision_recall.csv`; per-site table `out/m9_external_sites.csv`, `out/m3_benchmark_sites.csv`):

| mission | list | positives / negatives | pass the funnel (pos / neg) | recall at top 25 % | precision at top 25 % | recall at top 10 / 50 % / paired |
|---|---|---|---|---|---|---|
| Rover | `rover_preset.py`, all | 11 / 5 | 10 / 3 | **6 of 11 (54.5 %)** | **100 %** (0 negatives in the top quarter) | 45.5 / 54.5 / 90.9 % |
| Rover | `rover_preset.py`, verified coordinates only | 8 / 2 | 7 / 1 | 5 of 8 (62.5 %) | 100 % | 50 / 62.5 / 87.5 % |
| Rover | team benchmark (keyword labels) | 10 / 5 | 8 / 4 | 4 of 10 (40 %) | 66.7 % (Tirez, Dallol in the top quarter) | 20 / 40 / 80 % |
| Solar panels | BSRN list | 13 / 6 | 11 / 0 | **6 of 13 (46.2 %)** | **100 %** | 23.1 / 69.2 / 69.2 % |
| Lunar base | r4 list | 13 / 7 | 3 / 0 | **0 of 13 (0 %)** | undefined (nothing predicted) | 0 / 7.7 / 15.4 % |
| Lunar base | team benchmark (`cold` labels) | 5 / 11 | 0 / 5 | 0 of 5 (0 %) | undefined | 0 / 0 / 0 % |

Ranks of the named sites (percentile of the published rank in the ranked list, lower is better):

- **Rover** ([V-m9] = [A-9_reauditoria_rover] §7, identical): Ramon 3.6, Erfoud 3.7 (unverified), Qaidam 4.1, Haughton 4.2, Yungay 8.1, MDRS 20.5, Bardenas 68.2, Dumont Dunes 68.9 (unverified), Tabernas 71.5, Death Valley 80.1 (unverified); Dhofar does not pass (roughness < 5 m at 1°). Negatives: Rio Tinto 42.4, HI-SEAS 83.7, El Soplao 95.4; Concordia and NEEMO do not pass.
- **Solar panels:** Gandhinagar, Solar Village, Gobabeb, Tamanrasset, Gurgaon and Alice Springs in the top quarter of the paired list; Desert Rock and Boulder pass the funnel but have no twin; Izaña and Lampedusa fail the land gate (their cell is mostly sea); all six negatives fail the irradiance gate (>= 2.5 kWh/m2/day). In the full ranking of the 18,777 survivors (paired first) the positives' median percentile is 8.3 % (this morning 14.9 %). **Within the same 1° latitude row** it is 28.8 % (this morning 27.9 %): the correction did not make the ranking say more than latitude about these stations ([A-9_reauditoria_solar] §7).
- **Lunar base** ([A-9_reauditoria_base] §7): only 3 of the 13 positives pass the funnel: Craters of the Moon (rank 179, 7.4 %), MDRS (335, 13.8 %), Black Point (passes, no twin). The other 10 are removed by the diurnal-amplitude gate (>= 15 K; Haughton 2.5 K, Svalbard 1.2 K, Kangerlussuaq 6.6 K, Askja 7.4 K), by missing amplitude (Concordia, McMurdo: MODIS does not cover Antarctica), by the land gate or by `tmin_c` <= 5 degC. The same gate removes all 7 negatives.

**`rover_preset.validate_rover_ranking`** on the shipped Rover finals ([V-m3], `out/m3_rover_preset_check.csv`): **fails**, with every scope and score. Bardenas (final 85.21) is below the median of the mobility analogs (96.6). The re-audit explains why: with similarity 100 for 10,335 of 10,337 pairs, the Rover order is the team's suitability, and at 1° the bare-ground criterion gives Bardenas 0.018 and Tabernas 0.146 of bare or sparse cover, which costs them 24.4 and 19.8 points ([A-9_reauditoria_rover] §7). It is a weakness of a criterion of the team, not of the implementation.

**What it does not show.** The lists are small (11 to 13 positives), the negatives are few and easy (they fail a gate), and a 1-degree cell is not a field site: a site 10 km wide sits in a cell of about 111 x 111 km.

## 4. Sensitivity per mission [V-m4]

**How** (`validation/m4_sensitivity.py`). Every variant is a deep copy of the corrected configuration (after the criteria-set deviations), run through the engine's own `run_mission` in memory:

- **(a) Weights +-20 %:** each suitability weight x1.2 and x0.8, the weights then renormalised to their original sum. Rover 3 weights, Solar panels 4, Lunar base 4: 22 variants. Pairing does not depend on these weights.
- **(b) Hard thresholds +-10 %:** each numeric hard threshold x0.9 and x1.1 (common gates and the mission's gates, min or max); the whole mission is rerun (funnel, pairing, rank): 32 variants. The category gate (`thermal_inertia_class` excludes water) has no number and was not varied.
- **(c) Pairing tolerances +-20 %** (extra): each tolerance x0.8 and x1.2, its filter bound following: 18 variants.

Measures: overlap of the top 5 and the top 50 of the full ranking with the shipped one, Spearman on the points ranked in both, whether the number 1 pair changes, cells entering or leaving the funnel, pairs gained or lost. **Note:** "top 5" here is ranks 1-5 of the full ranking, not the five shown (which skip ice and water and keep 2° apart; for the shown five see the re-audits at the end of this section). Number 1 of the full ranking: Rover E3872 with M61299 (a water-dominated coastal cell, skipped in the five shown), Solar panels E40184 with M23206, Lunar base E21054 with M62517.

**(a) Weights +-20 %** (`out/m4_sensitivity_weights.csv`):

| mission | variants | worst top-5 overlap | worst top-50 overlap | lowest Spearman | number 1 changes |
|---|---|---|---|---|---|
| Rover | 6 | 5 / 5 | 50 / 50 | 0.987 | 0 |
| Solar panels | 8 | 4 / 5 | 45 / 50 (amplitude weight x0.8) | 0.998 | 0 |
| Lunar base | 8 | 3 / 5 (`tmin_c` x1.2) | 47 / 50 | 0.995 | 0 |

The Rover top is untouched because the top 254 points have every utility at or near 1: no weight can separate them (saturation, not robustness of the order, [A-9_reauditoria_rover] §5).

**(b) Hard thresholds +-10 %** (`out/m4_sensitivity_thresholds.csv`; only changes that move something):

| mission | threshold | x0.9: cells enter / leave; pairs | x1.1: cells enter / leave; pairs | top 50 kept | number 1 |
|---|---|---|---|---|---|
| Rover | land fraction >= 0.3 (common) | +118 / 0; +118 | 0 / -112; -112 | 49 / 47 | same |
| Rover | slope >= 0.5° | +604 / 0; +604 | 0 / -483; -483 | 42 / 47 | same |
| Rover | slope <= 15° | 0 / -1 | no change | 50 | same |
| Rover | roughness 5-650 m, elevation >= 1 m | no change | no change | 50 | same |
| Solar panels | ground irradiance >= 2.5 kWh/m2/day | +1,312 / 0; **pairs unchanged** | 0 / -1,316; **pairs unchanged** | 50 | same |
| Solar panels | slope <= 15° | 0 / -1 | no change | 50 | same |
| Solar panels | sun elevation, low-sun share, land, elevation | no change | no change | 50 | same |
| Lunar base | amplitude >= 15 K | +407 / 0; pairs 450 -> 529 (+137 / -58); 306 kept pairs change twin | 0 / -421; pairs 450 -> 347 (+73 / -176); 230 change twin | **33 / 29** | **changes** |
| Lunar base | `tmin_c` <= 5 degC | 0 / -164; pairs 450 -> 441; 127 change twin | +151 / 0; pairs 450 -> 451; 100 change twin | 40 / 40 | **changes** |
| Lunar base | land fraction, elevation (common) | no change | no change | 50 | same |

**(c) Pairing tolerances +-20 %** (`out/m4_sensitivity_tolerances.csv`): Rover none of 4 variants changes anything (every pair is far inside the 2° / 30 m filter). Solar panels: the key tolerance (0.6 kWh/m2/day) moves pairs 6,360 -> 5,956 / 6,546, top 50 keeps 48-49, number 1 same. Lunar base: pairs 392-530, top 50 keeps 47-49, number 1 same in all 8.

**The five shown** ([A] figures, weights +-10 % and Monte Carlo of input uncertainty, 200 runs): Rover 5 of 5 keep place and twin in 10/10 weight variants; exact five repeat in 10.5 % of runs ([A-9_reauditoria_rover] §5-6). Solar panels 14/14; exact five 0 of 200 ([A-9_reauditoria_solar] §5-6). Lunar base 10-16 of 16; exact five 0 of 200 ([A-9_reauditoria_base] §5-6).

**What it means.**

- **Rover and Solar panels: the top of the ranking is stable** under every stated change (number 1 never moves; top 50 keeps >= 42 and >= 45). Rover counts move only with the land and slope-minimum gates; Solar panels counts with the irradiance gate, which removes cells that have no twin anyway.
- **Lunar base is fragile** to its two thermal gates: +-10 % changes 100-306 twins and its number 1, because the pairing compares percentiles inside the population that passes the funnel. It is robust to its weights and tolerances (number 1 same in all 16 variants; this morning it changed in 6 of 12 weight variants).
- **What this does not show:** whether the shipped values are right; only how much the result depends on them.

## 5. Reproduction of the declared counts [V-m5]

**What was declared.** Solar 5,192, thermal 2,613, both 1,986: the author's note on `mission_scoring.py`. `docs/AUDIT.md` (Summary item 5) explains their origin: they were computed by `mission_scoring.py` on the **legacy 2-degree table** `output_py/earth_moon_harmonized_clean.csv` (16,200 Earth rows), with `mission_scoring.json` as committed at 618bc45 (`on_missing_gate` "keep").

**How** (`validation/m5_reproduction.py`): recomputed with the team module `mission_scoring.evaluate`, unchanged, and with the script's own gate code (independent of both the team module and the engine), on the legacy table and on the shipped real 1-degree table, under the committed configuration and the current one (`on_missing_gate` "drop"; `lunar_base` = an exact copy of thermal before the deviations).

| table | configuration | method | solar | thermal / Lunar base | both |
|---|---|---|---|---|---|
| legacy 2-degree | committed 618bc45 (keep) | team module | **5,192** | **2,613** | **1,986** |
| legacy 2-degree | committed 618bc45 (keep) | own code | 5,192 | 2,613 | 1,986 |
| legacy 2-degree | current (drop) | team module and own code | 5,192 | 2,613 | 1,986 |
| real 1-degree (shipped) | current | engine and own code | 18,777 | 2,419 | 2,419 |
| real 1-degree (shipped) | committed 618bc45 (keep) | own code | 18,777 | 2,419 | 2,419 |

**Result.**

- **The declared counts are reproduced exactly** on the table they were computed on, by both methods and under both configurations (no cell of that table passes only because a gated value is missing, so "keep" and "drop" agree).
- **The shipped counts differ because the table differs**, not because of an error: real 1-degree data, 25,497 land cells instead of 5,927 legacy ones.
  - Solar: the largest removals are the water class (4,421 land cells), irradiance < 2.5 kWh/m2/day (3,462) and land < 30 % (3,275) (`out/m5_shipped_failure_reasons.csv`).
  - Thermal / Lunar base: 9.5 % of the land cells pass, against 44.1 % of the legacy ones. The amplitude gate (>= 15 K) holds on 59.8 % of the legacy land cells, where the amplitude was a latitude formula of 8.9-38.8 K, and on only 17.8 % of the real ones, where it is MODIS 10:30-22:30 (-4.6 to 35.7 K) and is missing on 26.5 % (`out/m5_gate_shares.csv`).
  - "Both" equals the Lunar base count on the shipped table: every Lunar base survivor also passes the solar gates.
- The corrections of today changed no gate, so these counts are the same as this morning. The weights changed by the corrections do not enter a count.

## 6. Coordinates: every point falls where it says [V-m6]

**How** (`validation/m6_coordinates.py`). **Every** ranked point was checked, not a sample: 10,337 + 6,360 + 450 = 17,147.

- **(a) Cell:** the stored centre lies inside the cell its id names.
- **(b) Land:** the centre against the Natural Earth 1:110m admin-0 polygons in `engine/data`, with the script's own shapely point-in-polygon (the engine's labelling code is not used); for a centre outside every polygon, whether any polygon touches the 1-degree square.
- **(c) Country:** the country the bundle names equals the polygon containing the centre (same ISO code, or same name where Natural Earth has no ISO code); for a centre outside every polygon, the named country's polygon must touch the cell. Cells labelled Antarctica are checked for latitude.
- **(d) Lunar features:** each twin's nearest IAU named feature and its distance, recomputed with the script's own great-circle code (1,737.4 km sphere) from `engine/data/iau_moon_nomenclature.csv`.
- Region (admin-1) labels were **not** checked against polygons: the repository has none.

| check | Rover | Solar panels | Lunar base |
|---|---|---|---|
| points checked | 10,337 | 6,360 | 450 |
| centre inside its cell | 10,337 (100 %) | 6,360 (100 %) | 450 (100 %) |
| centre on Natural Earth land | 9,753 (94.4 %) | 6,339 (99.7 %) | 450 (100 %) |
| centre off land, land polygon touches the cell | 544 | 21 | 0 |
| no land polygon in the cell (islands missing at 1:110m) | 40 | 0 | 0 |
| country confirmed (centre polygon / touching polygon / Antarctica latitude) | 8,758 / 373 / 1,156 = **10,287 (99.52 %)** | 6,339 / 21 / 0 = **6,360 (100 %)** | **450 (100 %)** |
| country not confirmed | 50 (0.48 %) | 0 | 0 |
| distinct twins: nearest IAU feature and distance recomputed and equal (to 0.1 km) | **1,144 of 1,144**; median 51.4 km, max 194.3 km | **1,704 of 1,704**; median 53.5 km, max 186.3 km | **103 of 103**; median 26.5 km, max 60.0 km |

**The 50 unconfirmed Rover points** (`out/m6_coordinate_failures.csv`), all labelled from the nearest GeoNames place:

- 17 cells that no 1:110m polygon touches (small Arctic and ocean islands: 5 Svalbard, 3 United States, 3 Russia, 3 Canada, 1 Indonesia, 1 South Georgia, 1 Ecuador): probably right, not confirmable at that scale;
- 10 "Svalbard & Jan Mayen" cells touching the Norway polygon: consistent (Natural Earth puts Svalbard in Norway);
- 23 cells labelled with a country other than the polygon touching the cell: 9 "Greenland" touching Canada, 5 "Svalbard" and 4 "Iceland" touching Greenland (probably wrong labels on Arctic sea cells), 2 "Argentina" touching Chile, 1 "St Pierre & Miquelon" touching Canada, 1 "Ukraine" on the Crimea polygon that the 1:110m file assigns to Russia, 1 "Somalia" touching Somaliland.

None of the 15 shown analogs is among them: their names were checked against the nearest GeoNames place by great circle in all three re-audits ([A-9_reauditoria_*] point 8).

**What it does not show.** The 1:110m polygons are coarse; "centre off land" mostly means a coastal cell. And a correct coordinate of a 1-degree cell says nothing about a field site inside it.

## 7. One global figure per mission [V-m7]

**Read this first: it is a summary of checks, not a probability of being right.**

Each component is a 0-100 score read from the tables above (`validation/m7_global.py`, `out/m7_global.csv`):

| component | weight | definition | why this weight |
|---|---|---|---|
| external agreement | 0.25 | mean recall at the top 25 % over the site lists of the mission (section 3: Rover `rover_preset.py` 54.5 and team benchmark 40.0; Solar panels BSRN 46.2; Lunar base r4 list 0 and team benchmark 0) | the only check against knowledge from outside the team's tables and code; not a majority, because the lists are tiny |
| coverage | 0.20 | share of the values behind the ranked points that are MEASURED or DERIVED (section 1) | how much of what is ranked rests on data rather than models |
| stability | 0.20 | mean top-50 overlap over every variant of section 4, as % of 50 | a top that flips under +-10-20 % changes cannot be presented with confidence |
| validity | 0.15 | record-weighted pass share of the tables the mission reads (section 2) | necessary, near 100 % by construction, so weighted lower |
| coordinates | 0.15 | share of ranked points whose country is confirmed x share of twins whose nearest feature agrees (section 6) | same reason |
| reproduction | 0.05 | declared counts reproduced on their table (section 5) | about the team's earlier claims, not the shipped result |

| mission | external | coverage | stability | validity | coordinates | reproduction | **global** | without external |
|---|---|---|---|---|---|---|---|---|
| Rover | 47.3 | 100.0 | 98.6 | 100.0 | 99.5 | 100 | **86.5** | 99.5 |
| Solar panels | 46.2 | 87.5 | 98.5 | 100.0 | 100.0 | 100 | **83.7** | 96.3 |
| Lunar base | 0.0 | 73.3 | 92.1 | 100.0 | 100.0 | 100 | **68.1** | 90.8 |

**How to read it.** The internal components are high for every mission; **external agreement decides the figure** and is the lowest component in all three. This morning the figures were 84.3 / 96.1 / 67.2, but Solar panels' 96.1 was an upper bound with no external check at all; its 83.7 now includes one.

## 8. Improvements made today, before and after

These are the corrections the team lead ordered after the statistical audit (`docs/DECISIONS.md`, "Decisiones de las 11:28 y 11:36" and "Decisiones tomadas (11:23 CET)"). The team's file `mission_scoring.json` was **not edited**. Each change is a named deviation in `engine_config.json` `criteria_sets` (set `corrected`), stating the team's value, ours, the reason and the source. The set `audited_morning` rebuilds this morning's bundle exactly; three independent re-audits confirmed this ([A-9_reauditoria_*], point 3, "GO").

| # | change (decision) | before (this morning) | after (shipped) | source of the figures |
|---|---|---|---|---|
| C1 | **Rover pairing**: relative elevation out of similarity and of the pair filter (no physical meaning for a rover); slope and roughness 50 % + 50 % (11:23) | weights 40/40/20; largest twin share 19.9 % (M61116, 2,033 points); 10,192 of 10,337 paired | weights 50/50; largest twin share 2.6 %; 10,337 of 10,337 paired | DECISIONS 11:23 table; [A-9_reauditoria_rover] §2 |
| C2 | **Rover scale**: the score treats a difference within the measurement uncertainty as a match, `s = exp(-0.5 max(0, d/σ - 1)^2)`, σ slope 0.265°, σ roughness 17.4 m from ETOPO 2022 (7.17 m RMSE) and LOLA (~10 m) (11:51) | pair differences median 0.41° / 5.3 m | median 0.016° / 1.09 m; 10,335 of 10,337 pairs within σ, so similarity 100. **Consequence: the Rover order is the team's suitability** (Spearman final-suitability 1.000) | [A-9_reauditoria_rover] §2, §7 |
| C3 | **Solar panels suitability** (option E2): latitude geometry (sun elevation, low-sun share, 0.15 + 0.15) and modelled WorldClim irradiance (0.35, duplicates the pairing) out; measured-by-satellite clear-sky fraction ISCCP-H in, weight 0.35 (11:51) | Spearman suitability vs \|latitude\| -0.857 (the ranking was latitude) | +0.337; 7 of the top 50 unchanged; gates unchanged; 18,777 / 6,360 / 1,704 unchanged | DECISIONS 11:28 §2; [A-9_reauditoria_solar] verdict |
| C4 | **Lunar base suitability** (option R): `thermal_inertia_class` 0.15 -> 0 (still required, still excludes water), `rock_or_bare_frac` 0.10 -> 0.25, `permafrost_class` 0.05 -> 0 (607 of 2,419 had no value) (11:51) | five E17538, E16830, E15751, E21054, E17187 | five E21054, E17538, E21833, E18627, E19672; 2,419 / 450 / 103 unchanged; 38 of the top 50 unchanged | DECISIONS 11:28 §3; [A-9_reauditoria_base] §2 |
| C5 | **Choice of the five** (all missions): skip ice (`snow_ice_frac` >= 0.5) and water (`mask_fraction` < 0.5), 2° minimum separation; Rover picks within its tied group (`spread_within_top_tie`) (11:23, 11:28/11:36) | Rover five all with twin M59895 and neighbours; a water cell (E3872, 33.8 % land) would be number 1 | no ice or water in any five; land share >= 0.66 in all 15; minimum separation 2.97-60° | [A-9_reauditoria_*] point 8 |
| C6 | **Confidence per pair removed** (it was uniform: "medium" / "low"), replaced by the top-5 stability figures of the re-audits (11:28 §6) | one label for every pair | stability per analog in `top5_stability_<mission>` | DECISIONS 11:28 §6 |

**Effect on the checks of this document** (this morning's version of `docs/VALIDATION.md`, contract revision 6, against this one):

| check | before (morning, contract rev. 6) | after (corrected, rev. 8) | source |
|---|---|---|---|
| Rover: paired points; distinct twins | 10,192; 401 | 10,337; 1,144 | old `docs/VALIDATION.md` §6; [V-m6] |
| Rover: team benchmark recall / precision at top 25 % | 40 % / 57.1 % | 40 % / 66.7 % (false alarms: Tirez and Dallol; this morning Barranco del Jaroso, Pajonales and Dallol) | [V-m3] |
| Rover: `rover_preset.py` verified list, median percentile of positives | 9.2 | 8.1 | [A-9_reauditoria_rover] §7 |
| Rover: Bardenas / Tabernas percentile | 44.5 / 24.7 | 68.2 / 71.5 (worse: the order is now the team's suitability) | [A-9_reauditoria_rover] §7 |
| Solar panels: external check | not measurable (no list) | BSRN list: recall 46.2 %, precision 100 %; median percentile 14.9 % -> 8.3 % overall, 27.9 % -> 28.8 % within latitude row | [V-m9]; [A-9_reauditoria_solar] §7 |
| Solar panels: suitability vs \|latitude\| (Spearman) | -0.857 | +0.337 | [A-9_reauditoria_solar] verdict |
| Solar panels: shown analogs among the five in 200 Monte Carlo runs | 0-2 % | 0.5-13 % | [A-9_reauditoria_solar] §6 |
| Lunar base: values MODELLED / missing | 30.4 % / 0.8 % | 26.7 % / 0 % | old §1; [V-m1] |
| Lunar base: number 1 changes under +-20 % weights | 6 of 12 variants | 0 of 8 | old §4; [V-m4] |
| Lunar base: shown analogs among the five (Monte Carlo, mean) | 0.145 | 0.201 | [A-9_reauditoria_base] §6 |
| Lunar base: recognised analogs passing the funnel | 3 of 13 | 3 of 13 (same) | [A-9_reauditoria_base] §7 |
| Global figure Rover / Solar panels / Lunar base | 84.3 / 96.1 (upper bound, no external check) / 67.2 | 86.5 / 83.7 / 68.1 | old §7; [V-m7] |

**Proposed and not applied**, because each would change a criterion of the team (proposals for the team lead, effect measured where stated):

| id | proposal (would change a team criterion) | measured effect (in memory, [V-m8] `out/m8_improvements.csv` unless stated) |
|---|---|---|
| P1 | Rover: drop the minimums slope >= 0.5° and roughness >= 5 m (written for a 300 m baseline; the table is at 3.7 km and 1.85 km) | funnel and pairs 10,337 -> 22,185; benchmark recall unchanged (40 %); `validate_rover_ranking` still fails. The team lead decided at 11:23 to **keep** the slope minimum: without it 28 flat cells enter the top 50 and the four mobility analogs lose rank (DECISIONS 11:23, "Pendiente mínima") |
| P2 | Rover: weight of `rock_or_bare_frac` 0.25 -> 0 (a 1° land-cover share is near 0 at Bardenas, Tabernas, Death Valley) | top 50 keeps only 13 of 50; benchmark recall 40 -> 0 %; `validate_rover_ranking` still fails. **Not advised** |
| P3 | Lunar base: amplitude gate 15 K -> 13.5 K, or -> 0 K (MODIS 10:30-22:30 understates the daily range) | 13.5 K: funnel 2,419 -> 2,826, pairs 450 -> 529, number 1 changes, cold sites recovered still 0. 0 K: funnel 9,981, pairs 2,109, benchmark recall 0 -> 40 % (Haughton, Kangerlussuaq) at 100 % precision; but then five Ellesmere cells with ~1 K amplitude lead the ranking ([A-9_reauditoria_base] verdict, point 3) |
| P4 | Lunar base: compute the percentiles over a population that does not depend on the funnel (e.g. all Earth land with a value) | not computed; suggested by section 4 (a 10 % change of a thermal gate reshuffles 100-306 twins) |
| P5 | Tolerances x1.2: Lunar base `tmin_k` and amplitude 10 -> 12 percentile points; Solar panels sunlight above the atmosphere 0.6 -> 0.72 kWh/m2/day | pairs 450 -> 469 / 483; 6,360 -> 6,546; number 1 same in all three |

Not a team criterion, also not applied (this document writes no data file): mark Earth amplitudes < 0 and elevations < -430 m as invalid (no effect today: none of those 10 cells passes a funnel); verify the 15 benchmark coordinates written from memory (upper bound: Rover benchmark recall stays 40 %, precision 66.7 -> 60 %); state in the web text that the Solar panels weights sum to 0.70 and Lunar base to 0.95, so the effective weights are higher than written ([A-9_reauditoria_solar] F1, [A-9_reauditoria_base] §1).

## 9. Limits, said plainly

- **A 1-degree cell is not a field site.** Every value is the aggregate of a cell about 111 km wide on Earth (about 30 km on the Moon). A documented site that is a few kilometres across is represented by the whole cell around it; Bardenas, for example, is mostly farmland and scrub at 1°.
- **Few benchmark sites.** 11 to 13 positives per list, and negatives that a gate removes anyway. A recall of 54.5 % is 6 of 11 sites: one site more or less moves it by 9 points.
- **The Rover order is the team's suitability.** 10,335 of 10,337 pairs are within the measurement uncertainty of both terrain variables (similarity 100), so the final score is 50 + suitability / 2 (Spearman 1.000) and 254 points tie at the top; the five shown are a spread sample of that tied group, chosen by a stated rule, not five "best" places ([A-9_reauditoria_rover] §2, §6).
- **Solar panels: no gain within the same latitude.** Against the BSRN stations the corrected ranking is better overall (median percentile 8.3 % against 14.9 %) but the same within a latitude row (28.8 % against 27.9 %); with 11 stations that difference is not interpretable ([A-9_reauditoria_solar] §7).
- **Lunar base: only 3 of 13 recognised habitat and polar analogs pass its funnel**, because of the team's diurnal-amplitude gate (>= 15 K) and because MODIS has no amplitude over Antarctica. The gate is kept on purpose: without it five Ellesmere cells with 0.9-1.9 K of amplitude lead the ranking with similarity 97.7-99.8 ([A-9_reauditoria_base] §1-3).
- **The five shown are fragile under input uncertainty** in all three missions (Monte Carlo of 200 runs with documented or illustrative uncertainties): the exact five repeat in 10.5 % (Rover), 0 % (Solar panels) and 0 % (Lunar base) of the runs; each shown analog stays among the five in 43-87.5 %, 0.5-13 % and 18-23 % of the runs ([A-9_reauditoria_rover] §6, [A-9_reauditoria_solar] §6, [A-9_reauditoria_base] §6). The web says "five of the highest-scoring analogs in our model".
- **Not checked:** region (admin-1) labels (no polygons in the repository); category gates (no number to change); pairing weights (only suitability weights were varied by +-20 %; the re-audits varied pairing weights by +-10 %).

## 10. How to re-run everything (one command)

    cd "tierra luna" && python validation/run_all.py && python validation/report_tables.py

Use a Python 3.13 with numpy, pandas, scipy, pyproj, shapely, geopandas, rasterio, pydantic, reverse_geocoder and pytest (`tierra luna/requirements.txt`, `tierra luna/engine/requirements.txt`). The run reads only; it writes only `tierra luna/validation/out/` (all tables quoted here and `out/summary.json`). It is deterministic (no random numbers, no clock in any output) and takes about 15 minutes on 4 shared CPUs, most of it the in-memory engine reruns of section 4. `m5_reproduction.py` needs the full git history (it reads `mission_scoring.json` at commit 618bc45 with `git show`): in a shallow clone run `git fetch --unshallow` first. Each script also runs alone, for example `python validation/m9_external_lists.py`.

The audit figures quoted as [A-...] are re-run with the scripts named in each file (`tierra luna/audit/ra_rover_*.py`, `ra_base_*.py`, `ra_solar_*.py` on branch `audit-solar`, `p*.py`), and the r4 site ranks with `python -I "tierra luna/research/r4_rank_sites.py" app/public/data/v2`.

## Files

| file | content |
|---|---|
| `tierra luna/validation/run_all.py` | runs metrics m1-m9 (a failing metric is reported, the others still run) and writes `out/summary.json` |
| `validation/common.py` | paths, the engine call (`engine.build.compute`, corrected criteria sets applied), the in-memory variant runner |
| `validation/m1_coverage.py` | section 1 |
| `validation/m2_validity.py` | section 2 |
| `validation/m3_external.py`, `validation/m9_external_lists.py` | section 3 (team benchmark; `rover_preset.py`, BSRN and Lunar base lists with precision and recall) |
| `validation/m4_sensitivity.py` | section 4 |
| `validation/m5_reproduction.py` | section 5 |
| `validation/m6_coordinates.py` | section 6 |
| `validation/m7_global.py` | section 7 |
| `validation/m8_improvements.py` | in-memory effect of the proposals of section 8 |
| `validation/report_tables.py` | Markdown tables from the outputs (`out/tables.md`) |
| `validation/out/*.csv`, `out/r4/out/r4_rank_sites_shipped.*` | every table quoted above, with every failure listed |
