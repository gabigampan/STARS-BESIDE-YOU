# Data contract: static bundle v2 (contract revision 8, engine 3.4.0)

The engine (`tierra luna/engine`) writes a static, versioned bundle that the browser app reads with plain `fetch()`; no server is needed.

| command (run from `tierra luna/`) | dataset | output | shipped |
|---|---|---|---|
| `python -m engine build` (same as `--dataset real_1deg`) | real 1-degree tables (`output_real/*.csv`) | `app/public/data/v2/` (this contract) | yes |
| `python -m engine build --dataset legacy_2deg` | legacy 2-degree table | `build/legacy_2deg/` (same v2 format) | no |
| `python -m engine build --similarity-rule repo_global_mean --out DIR` | any | `DIR` (the earlier rule for every mission, no twins, same contract revision) | no |
| `python -m engine build --similarity-rule zone_twin --out DIR` | any | `DIR` (last night's z-score twin rule for every mission) | no |

Datasets are described in `tierra luna/engine/datasets.json`, engine settings in `engine_config.json`. The machine check of this contract is `engine/bundle_v2.py` (`validate_bundle_v2`), run by the tests; it also shows, in Python, every decoding and recompute step below.

**What changed in revision 8** (decisions of 2026-11-15 11:28, 11:36 and 11:51 CET; engine 3.4.0; `manifest.contract_revision` = 8). For the web developer:

1. **New variable** `clear_frac_isccp` (variables.json: label "Clear-sky fraction (ISCCP satellite clouds)", unit fraction 0-1, Earth level DERIVED, product ISCCP-H HGM v01r00 NOAA NCEI 2012-2016, licence "no constraints", cite Rossow and Schiffer 1999; Moon NO_DATA). It is a Solar panels soft criterion (weight 0.35, bad 0.308, good 0.671): `earth_solar.bin` carries `u.clear_frac_isccp`; `u.irradiance_kwh_m2_day`, `u.sun_elev_max_deg`, `u.sun_low_frac_0_5deg` are gone (weight 0). Lunar base: `u.thermal_inertia_class` and `u.permafrost_class` are gone, `rock_or_bare_frac` weighs 0.25. The browser suitability formula is unchanged (weights from `missions.json`).
2. **Supplementary data**: `manifest.json` config hashes list `earth_cloud_isccp_1deg.csv` and its provenance file (joined by cell id at build; `datasets.json` `supplements`).
3. **Criteria set per mission**: `missions.json missions[].criteria_set` = {"set": "corrected" or "audited_morning", "title", "deviations": [{criterion, team, ours, reason, source}]}.
4. **Rover similarity scores**: per variable `s = exp(-0.5 * max(0, |d| / sigma - 1)^2)` with `sigma` = `similarity.variables[].uncertainty_scale.sigma` (slope 0.265093 deg, roughness 17.401661 m); the pair filter (`bound`) is unchanged (2 deg, 30 m). A web build that recomputes Rover scores from the differences with the old Gaussian must use this formula; the published `s.<variable>` are authoritative.
5. **Top-5 fields** (`missions.json missions[].top5`): new `rule_id` (`rank_with_skips` | `spread_within_top_tie` | `by_rank` | `min_separation`), `skips` ({ice: {enabled, column "snow_ice_frac", op ">=", value 0.5}, water: {enabled, column "mask_fraction", op "<", value 0.5}}), `top_tie_n`, `top_tie_n_after_skips`, `alternative_rule` and, for Rover, `alternative` = {rule_id, ids, overall_ranks, rule} (the other list; the team lead is choosing between the two). `ids`, `overall_ranks`, `rule`, `min_separation_deg`, `min_separation_km` keep their meaning.
6. **Per-pair confidence removed**: `earth_<mission>.bin` columns `confidence` and `confidence_score` are still present (so older builds read the file) but every value is missing; `explain.json` pairs no longer have `confidence` / `confidence_score`; `missions.json` has no `confidence_counts` and no `distributions.confidence_score`. **The web must not show a confidence label.**
7. **New and changed limits texts** (`missions.json` honest-limits texts, each with `show`): `solar_suitability_clouds` [mission_card, data_and_limits]; `lunar_base_swing_gate` [mission_card, data_and_limits]; `lunar_base_criteria` [mission_card, data_and_limits]; `rover_no_new_variable` [mission_card, data_and_limits]; `rover_tie` [mission_card, top5, data_and_limits]; `rover_suitability_one_criterion` [mission_card, data_and_limits]; `deviations_from_team` [data_and_limits] (rows separated by " || ", columns by " | "); `constants_two_values` [data_and_limits]; `top5_stability_<mission>` now [mission_card, data_and_limits] and pending for the three missions.

**What changed in revision 7** (decisions of 2026-11-15 11:23 CET, taken by the delegate on the team lead's behalf; engine 3.3.0; `manifest.contract_revision` = 7). Solar panels and Lunar base pairing unchanged: `earth_solar.bin`, `earth_solar_pairs.bin`, `moon_solar.bin`, `earth_lunar_base.bin`, `earth_lunar_base_pairs.bin`, `moon_lunar_base.bin` and every other `.bin` except the three Rover files are byte-identical to revision 6. For the web developer:

1. **Rover variables.** `missions.json` `missions[rover].similarity.variables` is now `slope_deg` (key, weight 0.5, tolerance 2 deg, bound 2) and `roughness_m` (key, weight 0.5, tolerance 30 m, bound 30); each row has a new `weight_set_by`. Relative elevation is out of the similarity **and** of the pair filter. `earth_rover.bin` loses `s.elevation_rel_m`; `earth_rover_pairs.bin` loses `elevation_rel_m.earth/.moon/.diff` and gains **`info.elevation_rel_m.earth`, `info.elevation_rel_m.moon`, `info.elevation_rel_m.diff`** (float32, m, "not part of the similarity", shown as a difference like the Lunar base information rows). `missions[rover|solar].similarity` gain `info_columns` (the `info.*` columns of the pairs file: Rover `elevation_rel_m`, Solar none) and `info_in_explain_only` (the information rows that stay in `explain.json` only). Every passing Rover point now has a twin (10,337 of 10,337); `twins.json` Rover lists 1,166 twins, each with `not_part_of_similarity.elevation_rel_m`. Similarity recompute for Rover: `100 * (0.5 * s.slope_deg + 0.5 * s.roughness_m)`.
2. **`missions.json` `missions[].top5`** (every mission): `{"rule": "<plain English sentence for the user>", "min_separation_deg": 2.0 | null, "min_separation_km": 222.4 | null, "ids": [five Earth cell ids in the order shown], "overall_ranks": [their ranks in the full ranking]}`. Rover and Solar panels: greedy by rank with a 2-degree great-circle separation between cell centres (Rover ranks 1, 2, 4, 6, 8; Solar panels 1, 3, 4, 7, 9); Lunar base: ranks 1 to 5, separation null. Show these five as "the five"; the full ranking (`rank`, `list_order`) is unchanged and stays ordered by final score. `explain.json` holds the full explanation of each of the five (new key `top_n_rule`: the first `top_n` ranks, then any of the five beyond them).
3. **`show` field on texts.** `similarity.json` `texts` entries may carry `"show": [...]` among `"mission_card"`, `"top5"`, `"pair_panel"`, `"data_and_limits"`, plus `missions` (absent = every mission), `decision` and `source` (the audit file or "computed at build"). Render a text where its `show` says; texts without `show` keep their revision 6 behaviour. Texts whose `show` contains `mission_card` are also appended to `missions[].known_limitations`.
4. **New text keys** (all computed or filled at build; figures are never typed): `list_order_<mission>` (top5, mission_card: ordered by final score, "five of the highest-scoring analogs in our model"); `top5_stability_<mission>` (top5, data_and_limits; `status` "pending" with the sentence "Stability figures pending the independent re-audit." for Rover and Solar panels until the re-auditor fills `engine_config.json` `top5_stability`, "audited" with figures and `source` for Lunar base); `ties_at_top_rover` (top5, data_and_limits: 74 points share the published final 100.00, ordered among themselves by cell id); `surface_classes_rover` (mission_card, data_and_limits: ice-sheet and snow cells and water-dominated cells in the Rover ranking, with `figures`); `external_validation_<mission>` (data_and_limits: Rover rank percentiles of the known mobility analogs, recomputed every build; Solar panels and Lunar base: none, and why; also `missions[].external_validation` with the per-site rows for Rover); `gate_elevation_land` (data_and_limits, every mission: the common gate elevation >= 1 m removes 177 land cells, 37 with at least 30 % land); `numbers_without_effect` (data_and_limits, every mission: gate limits that remove no cell on their own, and values of `mission_scoring.json` no code reads); `zone_edge_lunar_base` (pair_panel, data_and_limits). The existing `solar_similarity_saturation` gains `show` (mission_card, pair_panel, data_and_limits); its text and figures are unchanged.
5. **Per-twin region phrase (Lunar base).** `twins.json` `missions.lunar_base.twins[].nasa_region` = `{"region": "<NASA region name>", "share_of_cell": 0-1 (4 decimals), "phrase": "in" | "at the edge of", "text": "in NASA's Haworth candidate region" | "at the edge of NASA's Haworth candidate region"}`: the region the twin's cell shares most area with; "in" at 50 % or more of the cell, "at the edge of" below. Print `text` beside the twin.
6. **Gate override: none.** The Rover slope minimum (0.5 deg, `mission_scoring.json`) is kept as the team wrote it (no source was found; the data show it keeps featureless flats, water and ice out of the head of the ranking: `docs/DECISIONS.md`, section of 11:23 CET). `missions[rover].gates` is unchanged.
7. **Mission notes.** `missions[rover].known_limitations`: the similarity note now describes slope and roughness only; the ice note with typed figures is replaced by `texts.surface_classes_rover`.

**Wording and display rounding, 2026-11-15** (contract revision stays **6**; no pairing, weight, tolerance, threshold, zone, score, rank or twin changed: every `.bin` file is byte-identical to the revision 6 build before this note). For the web developer, the fields whose text changed:

- **`similarity.json` `texts.solar_limitation.placeholders.loss_pct`: new rule.** The share lost must agree with the two numbers printed beside it. Before, `{loss_pct}` was 100 x `atm.lost_share` (from the unrounded values) with 0 decimals, so the number 1 pair read "6.2 of 9.6" with "36 %", where 6.2 / 9.6 gives 35.4 %. Now the placeholder has no `column` / `multiply`; it has `rule: "share_lost_of_displayed_tenths"`, `columns: {"above": "atm.toa_kwh_m2_day", "ground": "atm.ground_kwh_m2_day"}` and a `formula`. The rule, in integers so that Python and JavaScript cannot disagree on a half:
  1. **Displayed value** of a stored float32 `raw` (this rule also applies to `{toa_earth}`, `{toa_moon}` and `{ground_earth}`, which is what the browser already shows): the shortest decimal that rounds back to the float32 (the browser's `f32Decimal(raw)`; Python `np.format_float_positional(np.float32(raw), unique=True)`), written with 1 decimal, **half up** (`Intl.NumberFormat` rounds that decimal half up; Python `Decimal(...).quantize(Decimal("0.1"), ROUND_HALF_UP)`).
  2. **Integers of tenths**: `A` = `{toa_earth}` as displayed, `G` = `{ground_earth}` as displayed, times 10 (6.2 -> 62). JavaScript, for `raw >= 0`: `const s = f32Decimal(raw).toFixed(12), i = s.indexOf('.'); const T = Number(s.slice(0, i)) * 10 + Number(s[i + 1]) + (Number(s[i + 2]) >= 5 ? 1 : 0);` (exact: `T / 10` is what `Intl.NumberFormat` shows with 1 decimal; checked on all 6,360 Solar panels pairs).
  3. **`loss_pct` = 100 x (A - G) / A rounded half up** = `floor((200 x (A - G) + A) / (2 x A))`. Python: `(200 * (A - G) + A) // (2 * A)`. JavaScript: `Math.floor((200 * (A - G) + A) / (2 * A))` (exact: small integers, denominator under 2^20). Number 1: A = 96, G = 62, floor(6896 / 192) = **35**. The top 5 read 35, 36, 38, 37, 36 (`docs/AUDIO_TOP5.json`, the team's recorded audio). On 1,910 of the 6,360 Solar panels pairs the new percentage differs from the old 100 x `atm.lost_share` by one point.

  `atm.lost_share` is unchanged in `earth_solar_pairs.bin` (it is the unrounded share, not the displayed one). An app that still reads `loss_pct.column` finds none and must not show the sentence half-filled: apply the rule above. The engine's Python implementation is `tierra luna/engine/display.py` (`share_lost_percent`), used by `explain.json`, by `validate_bundle_v2` and by `tierra luna/tools/make_audio_top5.py`. `texts.solar_limitation` also has a new `display_rule` (the paragraph above, in one sentence).
- **`explain.json` `missions.solar[].similarity.pair_sentence` (new)**: `texts.solar_limitation` filled by the engine for each of the 25 published Solar panels pairs, with the rule above (as `missions.lunar_base[].similarity.pair_sentence` already was; the Lunar base sentences are unchanged). `validate_bundle_v2` checks that every per-pair sentence of `explain.json` is its template filled from the binary columns and that `{loss_pct}` can be computed on every Solar panels pair.
- **"Artemis III" no longer appears in user-facing text** (NASA's pages, consulted today and recorded in `docs/MISSION_ZONES.md`, give Artemis IV as the first crewed landing; the nine regions were announced in October 2024 for Artemis III). `lunar_named_sites.json` `sites[].why` of the seven NASA regions now reads "NASA candidate landing region '<name>' (announced October 2024)" (Nobile: "NASA candidate landing regions 'Nobile Rim 1' and 'Nobile Rim 2' (announced October 2024)"; before, e.g. "Artemis III candidate 'Slater Plain'"); Mons Malapert's `site_note` adds "'Malapert Massif' is an informal name" (it was in `why`). In builds that use the z-score zone (`--similarity-rule zone_twin`), the Lunar base zone `name` is "NASA's nine candidate landing regions near the lunar south pole" (was "NASA Artemis III candidate landing regions (9, announced 2024-10-28)") and the fallback `reason` names the nine regions the same way. Source citations keep their official titles (the USGS dataset "Down Selected Artemis III Candidate Landing Site Navigational Grids", NASA RELEASE24-136, the file `artemis_iii_regions.geojson`). A test checks that no user-facing text of the bundle says "Artemis III" outside a `source` / citation field.
- **`missions.json` `missions[solar].known_limitations[2]`**: its last sentence said "their confidence is lower" of the 6,060 passing Solar panels cells without land surface temperature; none of them has a twin (all at 64.5 S or further south), so they have no confidence at all. It now reads: "... with the remaining weights renormalised. None of them has a lunar twin (they lie at 64.5 S or further south, far from the latitudes whose sunlight matches the maria), so they have no similarity, no final score and no confidence." The other Rover and Solar panels limitations were checked against the shipped method and are unchanged.
- Sizes: `missions.json` 61,510, `similarity.json` 44,647, `explain.json` 176,653, `lunar_named_sites.json` 14,044 bytes; first view 2,356,210, total 13,780,175 bytes.

**What changed in revision 6** (team decision of 2026-11-15 08:55 CET, the team lead's delegate on his behalf: Lunar base design D4b of `docs/LUNAR_BASE_PROPOSAL.md` confirmed; Rover and Solar panels unchanged). For the web developer:

- **Rover and Solar panels: nothing changes.** `earth_rover.bin`, `earth_rover_pairs.bin`, `moon_rover.bin`, `earth_solar.bin`, `earth_solar_pairs.bin`, `moon_solar.bin`, `earth_base.bin` and the rover/solar parts of `missions.json`, `twins.json`, `explain.json` and `lunar_named_sites.json` are byte-identical to revision 5 (test `test_rover_and_solar_are_byte_identical_to_revision_5`).
- **Lunar base has a new rule, `percentile_and_real_tolerance`** (`manifest.similarity_rules.lunar_base`, `similarity.json` `rules`, `missions.json` `missions[lunar_base].similarity.rule`). It is the real-value machinery of revision 5 with a **scale per variable**: the two keys, coldest temperature (`tmin_k`) and daily thermal amplitude (`lst_diurnal_amp_k`), are compared as **mid-rank percentiles within their own population** (Earth: the 2,419 points passing the Lunar base funnel; Moon: the 280 cells of the zone); slope and roughness in **real values**. It is a likeness of thermal **position**, not of temperature: every pair must show the per-pair sentence `similarity.json` `texts.lunar_base_pair_sentence` (filled from `earth_lunar_base_pairs.bin`) and the real values.
- `earth_lunar_base.bin`: now like the rover/solar files: `similarity`, `final`, `rank` and `twin` are **missing on the 1,969 passing points without a twin**; new `s.tmin_k`, `s.lst_diurnal_amp_k`, `s.slope_deg`, `s.roughness_m` (per-variable scores, /1e6, for the exact recompute); `sim_vars_used` and `sim_missing_bits` are gone.
- **New file `earth_lunar_base_pairs.bin`** (rows `passing`; layout in "earth_lunar_base_pairs.bin" below): `list_order`; per similarity variable the real values `<v>.earth`, `<v>.moon`, `<v>.diff` (K for `tmin_k` and `lst_diurnal_amp_k`, deg, m) and, for the two percentile variables, `<v>.earth_pct`, `<v>.moon_pct`, `<v>.diff_pct` (percentile points: the compared values); not part of the similarity, `info.temp_k.*` (mean temperature, K), `info.elevation_rel_m.*` (m) and `info.irradiance_kwh_m2_day.*`; the no-twin reason `nopair_kind`, `nopair_var`, `nopair_gap` and, when both groups fail, `nopair_var2`, `nopair_gap2`.
- `missions.json` `missions[lunar_base].similarity` (rule `percentile_and_real_tolerance`): `variables` (each with `role`, `weight`, `scale`, `tolerance` in `unit`, `bound`, `real_unit`, `tolerance_set_by`, `why`, `sides`, `pairs_columns`, `compared_columns`, `score_column`, `population_size`), `populations` (`EARTH`/`MOON`: `rule`, `why`, `cells`, `cells_with_value`), `percentile` (formula), `zone` (`kind: "similarity_zone"`, `name`, `cells`: 280), `filter`, `nopair_kinds`, `nopair_groups`, `unpaired_by_kind`, `unpaired_reasons`, `info_columns`, `pair_sentence` (the key of the template in `similarity.json` `texts`), `pairs_file`, `paired_count`, `unpaired_count`, `distinct_twins`, `largest_share`.
- `similarity.json`: new `percentile_and_real` (rule, formula, meaning, per-mission variables, populations and zone). The z-score keys (`variables`, `active_variables`, `formula`, `target`, `z_rule_missions`, ...) are **absent** from the shipped bundle: no shipped mission uses z-scores (they remain in a `--similarity-rule zone_twin` or `repo_global_mean` build). The detail tiles no longer carry `z.<variable>`.
- `similarity.json` `texts`: new `similarity_meaning_lunar_base` (wherever a Lunar base similarity is shown), `lunar_base_pair_sentence` (per-pair template, every pair) and `no_twin_note_lunar_base` (one variant per `nopair_kind`). `similarity_meaning`, `missing_temperature_mark` and `missing_temperature_note` now have `missions: []` and a `status` "no longer applies": do not show them. `twin_sharing_note`: show the first sentence only, for every mission.
- `twins.json` `missions.lunar_base` rows: `values` (lunar real value of each similarity variable, K / deg / m), `percentiles` (the cell's percentile within the zone for `tmin_k` and `lst_diurnal_amp_k`), `not_part_of_similarity` (adds `temp_k`, `elevation_rel_m`); no `z`. `explain.json` `missions.lunar_base` items: `similarity.variables` (per variable `scale`, `unit`, `earth`/`moon`/`difference` in the compared unit, `earth_real`/`moon_real`/`difference_real` in `real_unit`, `score`), `similarity.not_part_of_similarity`, `similarity.twin`, `similarity.meaning` and `similarity.pair_sentence` (the template filled for that pair).
- **Lunar regions (new)**: `moon_base.bin` has a new int32 column **`region`** (all lunar cells; index into `mission_zones.json` `regions`), and the new file **`mission_zones.json`** (on demand): the six regions A-F of `docs/MISSION_ZONES.md` section 2 with `code`, `label`, `rule`, `cells`; `mission_zone_regions` (rover A + B, solar D, lunar_base A); `texts` (`general_note`, `zone_why.<mission>`, `outside.<mission>.<region>`) copied verbatim from `tierra luna/engine/mission_zone_texts.json`, or `null` when that file is absent or incomplete (`manifest.mission_zone_texts.status` says which).
- `manifest.contract_revision` is `6`, `engine_version` `3.2.0`; `manifest.counts.missions.lunar_base` now has `ranked_EARTH` 450 and `unpaired_EARTH` 1,969.

**What changed in revision 5** (team decision of 2026-11-15, morning; `docs/DECISIONS.md` "Decisiones tomadas (15-11-2026, mañana)"):

- **The similarity rule is per mission.** `manifest.similarity_rule` is `"per_mission"` (a single rule name only when every mission shares one, e.g. a `--similarity-rule` build) and the new `manifest.similarity_rules` (also `similarity.json` `rules`, `missions.json` `similarity_rules`) maps each mission to its rule: `rover` and `solar` use **`real_value_tolerance`** (similarity on real values within stated tolerances), `lunar_base` keeps `zone_twin` (z-scores), byte for byte as in revision 4. Always read the rule of the mission, never one global rule.
- **Real-value missions** (`missions.json` `missions[].similarity` with `rule = "real_value_tolerance"`): the block lists the similarity `variables` (role `key` or `secondary`, `weight`, `tolerance`, `bound`, `unit`, `tolerance_set_by`, `why`, how each side is made), the `zone`, `filter`, `paired_count`, `unpaired_count`, `unpaired_reasons`, `nopair_kinds` and `pairs_file`. `ranked_count` and `passing_without_similarity` keep their meaning: paired points and passing points without a twin.
- `earth_<mission>.bin` of a real-value mission: new quantised columns `s.<variable>` (per-variable score, /1e6) used for the exact recompute; `similarity`, `final`, `rank` and `twin` are **missing on passing points without a twin**; `sim_vars_used` and `sim_missing_bits` are no longer written for these missions (they stay in `earth_lunar_base.bin`).
- New on-demand file per real-value mission, **`earth_<mission>_pairs.bin`** (rows `passing`): `list_order`, the real values on both sides and the absolute difference of every similarity variable, the no-twin reason (`nopair_kind`, `nopair_var`, `nopair_gap`) and, for solar, the sunlight at the ground and above the atmosphere and the share lost (`atm.*`).
- `earth_base.bin`: new `d.irradiance_toa_kwh_m2_day` (per grid row, DERIVED): Earth's sunlight above the atmosphere.
- `similarity.json`: new `rules`, `real_value` (formula, filter, derived variables with the body means of the relative elevation and the sunlight formula, per-mission detail) and `z_rule_missions` (the missions the z-score keys describe: `lunar_base`); `target.zones` lists the `zone_twin` missions only. New texts `similarity_meaning_real_values`, `no_twin_note`; `solar_limitation` is now a per-pair template (it replaces decision 5's text and is no longer in `known_limitations`); `similarity_meaning` and the temperature texts carry `missions: ["lunar_base"]`.
- `twins.json` rows of a real-value mission: `values` holds the lunar real value of each similarity variable (no `z`); `not_part_of_similarity` adds `temp_k`. `explain.json` items of a real-value mission: `similarity.variables` (per variable role, weight, tolerance, bound, Earth, Moon, difference, score), `similarity.twin`, `similarity.not_part_of_similarity` (Earth, Moon, difference) and, for solar, `similarity.atmosphere`.
- `manifest.counts.missions.<m>` adds `unpaired_EARTH`.

**What changed in revision 4** (team decisions of 2026-11-15, answers to `docs/DECISIONS.md`):

- the shipped rule is `zone_twin` (`manifest.similarity_rule`, `similarity.json` `rule`): every ranked Earth cell has a lunar twin (`earth_<mission>.bin` `twin`, `moon_<mission>.bin` `twin_count`, `twins.json`); `repo_global_mean` stays available with `--similarity-rule repo_global_mean` and writes the same revision without twins;
- two new int32 columns in every `earth_<mission>.bin` (rows `passing`), so the ranking list can mark the pairs whose similarity used fewer variables without loading a detail tile: `sim_vars_used` (how many of `similarity.json` `active_variables` have a value on both sides of the pair) and `sim_missing_bits` (bit k set when `active_variables[k]` was left out; on the real tables only `temp_k`, bit 3, for Antarctic cells); `validate_bundle_v2` checks both against the z-scores on every passing cell;
- `similarity.json` `texts`: the approved English web texts (decisions 1 to 5), and the solar limitation as the first item of the solar mission's `missions.json` `known_limitations`.

**What changed in revision 3** (engine 3.0.0, team lead decisions of 2026-11-14):

- exactly three offered missions: `rover`, `solar`, `lunar_base` (an exact copy of the team's `thermal` block); the `ice` block is an information component of `lunar_base`; `thermal` and `ice` are no longer separate missions or files;
- the funnel is exported step by step (`missions.json` `funnel`, reason codes with their step and one-line text);
- the similarity is the repository's own (`analog_finder`), described in the new `similarity.json`; the active rule is `repo_global_mean` (no twin); `twin`, `twin_count` and `twins.json` exist only when the rule has twins (`zone_twin`);
- utilities, z-scores and the ice component moved to the tiled detail files `earth_detail_NN.bin`; the per-mission `earth_<mission>.bin` keep the map columns;
- per-variable similarities `s.<v>`, `missing_n` and the v1 appendix were removed.

## General rules

- **Files.** JSON (UTF-8, compact, keys in a fixed order) for metadata and small tables; little-endian binary typed arrays (`.bin`) for per-cell numbers. Two builds from the same inputs are byte-identical. The build removes `.json` / `.bin` files of an earlier bundle that are not in the new one.
- **Version.** `bundle_version` is `"v2"` in every JSON file and the folder name; `manifest.contract_revision` is `6`.
- **Missing values.** A missing value is never `0` and never a default:
  - JSON: `null`;
  - Float32 column: `NaN`;
  - Int32 column: the sentinel `-2147483648` (INT32_MIN; `manifest.encoding.int32_missing`), never a valid value in this bundle.
- **Grid.** 180 rows x 360 columns of 1-degree cells per body (`manifest.grid`).
  - `id = row * 360 + col` (0..64799); Earth and Moon ids are separate namespaces.
  - Row 0 is at the north, column 0 at the west. Cell centre: `lat = 90 - (row + 0.5)`, `lon = -180 + (col + 0.5)`, longitude positive east, -180..180.
  - Earth latitudes are the source products' WGS84 geodetic latitudes (at most 0.19 deg from geocentric).
- **True cell size.** Earth 111.2 km north-south (6371 km sphere); Moon 30.3 km (1737.4 km sphere). East-west the cell is that size x cos(latitude): a polar cell is a narrow strip.
- **What a value means.** Every per-cell value is an aggregate over a whole cell (`variables.json` `aggregation`). Nothing in this bundle describes a point or a rover-scale site.
- **Text from team files** (gate `source`, weight `why`, mission `description`, class names such as `roca`, `suelo`, `continuo`, `ninguno`, and the `team_text` of a reason) is copied verbatim, in Spanish where the team wrote Spanish.

## Files

Sizes from the build of 2026-11-15 (Lunar base decision; wording and display rounding pass), revision 6 (`manifest.files[].bytes` is authoritative); revision 7 changes only `earth_rover.bin`, `earth_rover_pairs.bin`, `moon_rover.bin` (same sizes or near) and the JSON files (see the sizes note below).

| file | format | loaded | rows | content | bytes |
|---|---|---|---|---|---|
| `manifest.json` | JSON | start | - | index of every file and binary column, grid, encoding, counts, detail tiles, credits, `mission_zone_texts` | 161,255 |
| `missions.json` | JSON | start | - | offered missions, funnel steps, gates, weights, reason codes, counts, components, alpha, the per-mission similarity block, notes | 61,510 |
| `similarity.json` | JSON | start | - | the rule of each mission; the real-value rule (rover, solar); the percentile rule (`percentile_and_real`, lunar_base); texts | 44,647 |
| `variables.json` | JSON | start | - | per variable and body: real column, level, source, licence, baseline, caveat, comparability; lunar information columns | 65,006 |
| `places.json` | JSON | start | - | Earth country and region tables | 34,824 |
| `earth_base.bin` | bin | start | Earth land cells (25,497) | id, coordinates, country, region, values, `d.irradiance_toa_kwh_m2_day` | 1,432,152 |
| `earth_rover.bin` | bin | start (default mission) | land / passing | fail bits; suitability, similarity, final, rank, twin, confidence, per-variable scores `s.<v>` | 556,816 |
| `earth_solar.bin`, `earth_lunar_base.bin` | bin | on demand | land / passing | same layout | 928,176 / 218,100 |
| `earth_rover_pairs.bin`, `earth_solar_pairs.bin` | bin | on demand (when a pair or a point without twin is shown) | passing | list order, real values both sides and difference, no-twin reason; solar `atm.*` | 537,524 / 1,201,728 |
| `earth_lunar_base_pairs.bin` | bin | on demand | passing | list order; percentiles and real values both sides and differences; mean temperature, relative elevation, irradiance; no-twin reason | 319,308 |
| `earth_detail_00.bin` .. `earth_detail_17.bin` | bin | on demand (one per selected cell) | land cells of 10 grid rows | utilities of every mission, the ice component (no z-scores since revision 6) | 6,160 - 276,800 each, 2,039,200 in all |
| `moon_base.bin` | bin | on demand | all 64,800 lunar cells | values, information column, nearest IAU feature, `region` | 2,857,680 |
| `moon_<mission>.bin` (3) | bin | on demand | all lunar cells | fail bits and twin counts | 518,400 each |
| `twins.json` | JSON | on demand | - | every distinct twin per mission | 1,038,364 |
| `earth_place_detail.bin` | bin | on demand | Earth land cells | label rule, nearest populated place and its distance | 305,964 |
| `place_detail.json` | JSON | on demand | - | label rules, nearest-place names | 113,249 |
| `explain.json` | JSON | on demand | - | top 25 ranked Earth cells per mission with the whole funnel | 176,653 |
| `iau_moon_features.json` | JSON | on demand | - | 2,023 primary IAU lunar features | 105,663 |
| `lunar_named_sites.json` | JSON | on demand | - | named lunar sites, their cell and per-mission outcome | 14,044 |
| `mission_zones.json` | JSON | on demand (Moon view) | - | the six lunar regions, each mission's zone as regions, the "why not here" texts | 12,301 |
| `validity.json` | JSON | on demand | - | schema validation report of the input tables | 251 |

- **Revision 7** (2026-11-15 11:23 CET): first view without the manifest **2,170,969 bytes** (2,332,028 with it), total without the manifest **13,959,831 bytes** (14,120,890 with it), under the 14,000,000-byte target that the tests check on the bundle without its manifest; `twins.json` grew to 1,407,221 bytes (1,166 Rover twins instead of 401). Revision 6 below.
- **First view** (`manifest.load.first_view` plus the manifest), revision 6: **2,356,210 bytes**, under the 2,500,000-byte target. **Total**: **13,780,175 bytes**, under 14,000,000 (before the wording and display rounding pass: 2,354,530 and 13,767,549). Revision 5: 2,340,377 and 13,484,232. Both targets are `engine_config.json` `first_view_budget_bytes`; the tests check them. Revision 4 (zone_twin for all three missions): 2,261,764 and 11,393,483. The comparison build with `--similarity-rule repo_global_mean` (no twins, no pairs files): first view 2,220,513, total 9,653,647.
- **Showing the funnel of one land cell** needs the first view (values, gates, reason tables, scores of the default mission), the mission file of each mission shown (fail bits and scores; 0.17-0.63 MB) and **one** detail tile (at most 332,160 bytes): never the whole set of tiles.
- Earth files hold only **land cells**: cells with any land (`mask_fraction > 0`, datasets.json `earth_land_cells`). Pure-ocean cells are absent; they fail every mission on the land gates.

## manifest.json

```json
{"bundle_version":"v2","contract_revision":6,"engine_version":"3.2.0",
 "dataset":{"id":"real_1deg","why":"..."},
 "build_time":"inputs-sha256:...","similarity_rule":"per_mission",
 "similarity_rules":{"rover":"real_value_tolerance","solar":"real_value_tolerance","lunar_base":"percentile_and_real_tolerance"},
 "mission_zone_texts":{"status":"texts copied verbatim from engine/mission_zone_texts.json","texts_present":true},
 "inputs":[{"key":"EARTH","file":"earth_real_1deg.csv","sha256":"...","rows":64800},{"key":"MOON",...}],
 "config_sha256":{"mission_scoring.json":"...","engine_config.json":"...","datasets.json":"...","provenance_earth.csv":"...",
                  "provenance_moon.csv":"...","column_aliases.json":"...","iau_moon_nomenclature.csv":"...",
                  "ne_110m_admin_0_countries.geojson":"...","artemis_iii_regions.geojson":"..."},
 "grid":{...},"encoding":{"byte_order":"little","float32_missing":"NaN","int32_missing":-2147483648,"column_rule":"...","quantised_rule":"..."},
 "counts":{"EARTH":{"cells":64800,"land_cells":25497,"invalid_records":0},"MOON":{"cells":64800,"invalid_records":0},
           "missions":{"rover":{"pass_EARTH":10337,"pass_MOON":60988,"ranked_EARTH":10192,"unpaired_EARTH":145,"distinct_twins":401},...},
           "lunar_features_for_labels":2023},
 "load":{"first_view":["missions.json","similarity.json","variables.json","places.json","earth_base.bin","earth_rover.bin"],
         "default_mission":"rover"},
 "detail_tiles":{"rows_per_tile":10,"lookup":"...",
                 "files":[{"name":"earth_detail_00.bin","row_start":0,"row_end":9,"land_cells":346}, ...]},
 "files":[{"name":"earth_rover.bin","bytes":391424,"sha256":"...","format":"bin","load":"start","description":"...",
           "body":"EARTH","mission":"rover","row_sets":{"land":25497,"passing":10337},
           "columns":[{"name":"fail_bits","type":"int32","rows":"land","length":25497,"offset":0,"missing":-2147483648,"scale":null,"description":"..."},
                      {"name":"suitability","type":"int32","rows":"passing","length":10337,"offset":...,"missing":-2147483648,
                       "scale":0.01,"divisor":100,"decode":"value = q / divisor"}, ...]}, ...],
 "sizes":{"first_view_bytes_without_manifest":1969737,"total_bytes_without_manifest":9233303,"detail_tile_max_bytes":332160,
          "budget":{"first_view_max":2500000,"total_max":14000000}},
 "credits":["...place-name credits...","...one entry per data product used, verbatim from the provenance files..."]}
```

- `build_time` is the `--build-time` text if one was passed, else `inputs-sha256:` and 16 hex digits of a hash of the input hashes. No clock is read.
- `similarity_rule` is `"per_mission"` when the missions use different rules (the shipped bundle), else the one rule (a `--similarity-rule` build); `similarity_rules` is always the rule of each mission.
- `files` lists every other file in load order with its size and sha256. The manifest does not list itself.

## Binary layout

Every `.bin` file is a plain concatenation of columns, without a header; the column index is in `manifest.files[]`.

| column key | meaning |
|---|---|
| `name` | column name (per-file tables below) |
| `type` | `float32` or `int32`, little-endian, 4 bytes per value |
| `length`, `offset` | number of values; byte offset of the first one (a multiple of 4; columns are contiguous, in index order) |
| `rows` | the row set the values follow (below) |
| `missing` | `"NaN"` (float32) or `-2147483648` (int32) |
| `scale`, `divisor`, `decode` | quantised columns only: Int32 `q`, `value = q / divisor` |
| `codes` | index columns: the JSON table the integer indexes |
| `unit`, `variables`, `per_grid_row`, `description` | value columns: unit, the mission variables read from this real column, stored once per grid row or not |

| `rows` | one value per | order |
|---|---|---|
| `land` | Earth land cell | `earth_base.bin` `id`, ascending |
| `passing` | Earth land cell passing the mission's hard filters | ascending id; `land_index` gives its position in `land` |
| `tile_land` | Earth land cell of one detail tile | ascending id; the tile's own `id` column |
| `all` | lunar cell | position = lunar cell id |
| `grid_rows`, `grid_cols` | grid row (180) / grid column (360) | a cell's row is `floor(id / 360)`, its column `id % 360` |

A value column constant along every grid row on the whole body (detected from the data: the sun-geometry formulas and the lunar values set by definition) is stored once per grid row (`per_grid_row = true`); the value of a cell is `column[floor(id / 360)]`.

Quantised columns store exactly the published value: `q / divisor` in double precision is the same double as the engine's number (utilities 6 decimals, z-scores 4, scores 2, confidence scores 3; `engine_config.json` `binary_encoding` and `repo_similarity`). Always divide; `q * scale` can differ in the last bit.

### Reading a column in TypeScript

```ts
type Column = { name: string; type: 'float32' | 'int32'; rows: string; length: number; offset: number;
                missing: 'NaN' | number; scale: number | null; divisor?: number; codes?: string };
type FileEntry = { name: string; bytes: number; format: 'json' | 'bin'; load: 'start' | 'on_demand';
                   row_sets?: Record<string, number>; columns?: Column[] };

const BASE = 'data/v2/';
const INT32_MISSING = -2147483648;   // manifest.encoding.int32_missing

async function loadBin(entry: FileEntry): Promise<Record<string, Float32Array | Int32Array>> {
  const buf = await (await fetch(BASE + entry.name)).arrayBuffer();
  const out: Record<string, Float32Array | Int32Array> = {};
  const littleEndianHost = new Uint8Array(new Uint32Array([1]).buffer)[0] === 1;
  for (const c of entry.columns!) {
    if (littleEndianHost) {          // every browser in practice: zero-copy views (offsets are 4-byte aligned)
      out[c.name] = c.type === 'float32' ? new Float32Array(buf, c.offset, c.length)
                                         : new Int32Array(buf, c.offset, c.length);
    } else {                         // big-endian host: decode with DataView
      const dv = new DataView(buf, c.offset, 4 * c.length);
      const a = c.type === 'float32' ? new Float32Array(c.length) : new Int32Array(c.length);
      for (let i = 0; i < c.length; i++) a[i] = c.type === 'float32' ? dv.getFloat32(4 * i, true) : dv.getInt32(4 * i, true);
      out[c.name] = a;
    }
  }
  return out;
}

const decodeQ = (q: number, c: Column) => (q === INT32_MISSING ? null : q / c.divisor!);
const rowValue = (col: Float32Array, id: number, cols = 360) => col[Math.floor(id / cols)];
const latOf = (lat: Float32Array, id: number) => lat[Math.floor(id / 360)];
const lonOf = (lon: Float32Array, id: number) => lon[id % 360];
// Reason codes of a cell from its fail bits (missions.json reason_codes[k].bit == k), in bit order.
const reasonsOf = (bits: number, codes: { bit: number; code: string; text: string; step: number }[]) =>
  codes.filter(r => (bits >>> r.bit) & 1);
// One-line elimination reason (missions.json elimination_line_rule).
const eliminationLine = (bits: number, codes: { bit: number; text: string }[]) =>
  codes.filter(r => (bits >>> r.bit) & 1).map(r => r.text).join('; ');
// Detail tile of a cell, and its position in that tile.
function tileOf(manifest: any, id: number) {
  const row = Math.floor(id / 360);
  return manifest.detail_tiles.files.find((t: any) => t.row_start <= row && row <= t.row_end);
}
function positionInTile(ids: Int32Array, id: number): number {   // binary search; -1 = not a land cell
  let lo = 0, hi = ids.length - 1;
  while (lo <= hi) { const m = (lo + hi) >> 1; if (ids[m] === id) return m; if (ids[m] < id) lo = m + 1; else hi = m - 1; }
  return -1;
}
```

## The funnel (team lead decision 2)

Identical for the three missions; `missions.json` `funnel` gives the text of each step, built from the configuration (common-gate limits from `mission_scoring.json`, their bodies from `engine_config.json` `gate_body_applicability`, the decay from `repo_similarity`).

| step | name | where in the bundle |
|---|---|---|
| 1 | common gates: land mask `elevation_m >= 1` (Earth only), `mask_fraction >= 0.3` (both bodies) | `missions[].gates[]` with `step: 1`; reason codes with `step: 1` |
| 2 | required variables: a missing one eliminates with `<variable> no data` | `missions[].require_present`; reason codes with `step: 2` |
| 3 | the mission's hard filters: failing one eliminates the cell for that mission (no score, no rank) | `gates[]` with `step: 3`; reason codes with `step: 3` |
| 4 | suitability 0-100, survivors only | `earth_<m>.bin` `suitability`; utilities in the detail tile |
| 5 | similarity: rover and solar on real values within tolerances; lunar_base on thermal position (percentiles within each population) and real terrain; a point with no lunar cell inside the filter has no twin and stops here, keeping its suitability | `earth_<m>.bin` `similarity`, `twin`, `s.<v>`; `earth_<m>_pairs.bin`; `missions.json` `similarity`; `similarity.json` |
| 6 | final = alpha x similarity + (1 - alpha) x suitability, paired points only; the list shows the paired points by rank, then the points without a twin by suitability | `earth_<m>.bin` `final`, `rank`; `earth_<m>_pairs.bin` `list_order`; `missions.json` `alpha` |

For every Earth land cell `id` and mission `m`, the panel shows:

1. **Gates.** For each `gates[g]` with `"EARTH"` in `applies_to`: the limit (`limit`, e.g. `"[2.5, inf]"`, or `min`, `max`, `allow`, `exclude`), the cell's value (`earth_base.bin` `v.<columns.EARTH>`; categories index `variables.json` `categories`) and pass or fail (fail when a reason code of that variable has its bit set in `earth_<m>.bin` `fail_bits[landPos]`). A gate value that is missing fails with the `missing` code.
2. **Elimination reason** in one line: the `text` of the set reason codes in bit order, joined with `"; "` (e.g. `"irradiance_kwh_m2_day outside [2.5, inf]; thermal_inertia_class not allowed"`); `team_text` is mission_scoring.py's own wording (`"... fuera de [2.5, inf]"`, `"... no permitido"`, `"... sin dato"`). An eliminated cell has no suitability, similarity, final or rank for that mission, whatever the weights, but may pass another mission.
3. **Suitability breakdown** (survivors): per weighted variable (`weighted_variables[]`): value (`earth_base.bin`), utility `u = tile "<m>.u.<v>"` (missing = the cell has no value: ignored, weights renormalised), weight `w`, contribution `w * u`; sort by contribution; points `= 100 * w * u / sum(w over variables with a utility)`; **coverage** `= sum(w with a utility) / sum(all w)`.
4. **Similarity, alpha, final**: `earth_<m>.bin` `similarity`, `final`, `rank`; `alpha` from `missions.json`. Real-value missions (rover, solar): per similarity variable its role, the Earth value, the twin's value, the difference, the tolerance and the bound (`earth_<m>_pairs.bin` and `missions.json` `similarity.variables`) and the score (`s.<v>`), with `texts.similarity_meaning_real_values`; solar also the per-pair text `texts.solar_limitation`; a point without a twin shows `texts.no_twin_note` instead. lunar_base (revision 6): per variable its role, scale, the percentile of both sides and their difference (the two thermal keys, `earth_lunar_base_pairs.bin` `<v>.earth_pct`, `.moon_pct`, `.diff_pct`, beside the tolerance in percentile points), the real values of both sides and their real difference for every variable (`<v>.earth`, `.moon`, `.diff`: coldest temperature and amplitude in K, slope, roughness; `info.temp_k.*` and `info.elevation_rel_m.*` marked "not part of the similarity"), the score `s.<v>`, with `texts.similarity_meaning_lunar_base` and, on **every** pair, the filled `texts.lunar_base_pair_sentence`; a point without a twin shows the variant of `texts.no_twin_note_lunar_base` for its `nopair_kind`. Label the Earth coldest temperature "modelled air temperature (WorldClim)" and the lunar one "measured surface temperature (Diviner)" (`missions.json` `similarity.variables[].sides`).
5. **Confidence**: `confidence` (index into `confidence_codes`) and `confidence_score`; the **level** of every value (`MEASURED`, `DERIVED`, `MODELLED`, `NO_DATA`; `variables.json` `levels` defines a fifth, `UNDOCUMENTED`, a cached array of undocumented origin, which no variable of the shipped real_1deg dataset has: its text says so, and it can appear only with the legacy 2-degree table) is in `variables.json` `variables[].bodies[EARTH|MOON].level` (per variable and body) and in `similarity.json` `variables[].levels`.
6. **lunar_base only, the ice component** (information, never changes the ranking): tile `lunar_base.ice.fail_bits` (bits index `missions[lunar_base].component_results.ice.reason_codes`), `lunar_base.ice.suitability` and `lunar_base.ice.u.<v>` (missing unless the cell passes ice).

## earth_base.bin (start)

| column | type | rows | content |
|---|---|---|---|
| `id` | int32 | land | Earth cell id |
| `lat`, `lon` | float32 | grid_rows, grid_cols | cell-centre coordinates |
| `country`, `region` | int32 | land | index into `places.json` `countries`, `regions` (sentinel: no label) |
| `v.<column>` | float32 / int32 | land or grid_rows | value of the real column `<column>`; categories are int32 indexes into `variables.json` `categories` |

Derived column (revision 5): `d.irradiance_toa_kwh_m2_day` (float32, `grid_rows`, `level: "DERIVED"`): Earth's annual-mean daily sunlight on a horizontal surface at the top of the atmosphere, from the latitude (`similarity.json` `real_value.irradiance_toa`); a formula, never shown as measured.

Stored columns (real column, mission variables read from it): `elevation_m`, `mask_fraction`, `slope_iso_deg` (slope_300m_deg, slope_deg), `roughness_m` (rough_300m_m, roughness_m), `rock_or_bare_frac`, `irradiance_kwh_m2_day`, `sun_elev_max_deg` (per grid row), `sun_low_frac_0_5deg` (per grid row), `thermal_inertia_class`, `lst_diurnal_amp_k`, `tmin_c`, `permafrost_class`, `temp_k`.

## earth_\<mission\>.bin (rover at start, the others on demand)

| column | type | rows | content |
|---|---|---|---|
| `fail_bits` | int32 | land | bit k set when `missions.json` `reason_codes[k]` failed; `0` = the cell passes |
| `land_index` | int32 | passing | position of the cell in `earth_base.bin` |
| `suitability` | int32 q, /100 | passing | 0-100 |
| `similarity` | int32 q, /100 | passing | 0-100, the mission's rule; missing when the cell has no twin (real-value missions) or no similarity variable with a value |
| `final` | int32 q, /100 | passing | 0-100 |
| `rank` | int32 | passing | 1 = best; sentinel when not ranked (no similarity: no twin) |
| `twin` | int32 | passing | **only when the rule has twins** (all three missions in the shipped bundle): lunar twin id (= `moon_base.bin` position); sentinel = **no lunar analog** (real-value missions: no zone cell passes the pair filter) |
| `confidence` | int32 | passing | index into `missions.json` `confidence_codes` (`low`, `medium`, `high`); sentinel = no confidence |
| `confidence_score` | int32 q, /1000 | passing | 0-1 |
| `s.<variable>` | int32 q, /1e6 | passing | revision 5, **real-value missions only** (revision 6: also lunar_base, scored on the compared values: percentile points for the two thermal keys): score of each similarity variable (`missions.json` `similarity.variables`, in that order), `exp(-0.5 * (difference / tolerance)^2)` rounded to 6 decimals; sentinel when there is no twin or the variable (a secondary) has no value on a side |
| `sim_vars_used` | int32 | passing | revision 4, **zone_twin / repo_global_mean missions only** (none in the shipped bundle since revision 6; a `--similarity-rule` build): number of `similarity.json` `active_variables` with a value on both sides of the pair (the set P of the recompute formulas); 4 on the real tables, 3 where temperature is missing, 0 when the cell has no similarity |
| `sim_missing_bits` | int32 | passing | revision 4: bit k set when `active_variables[k]` has no value on the Earth cell or on its lunar side and was left out of the distance (weights renormalised); `0` = every variable used. Show the mark `similarity.json` `texts.missing_temperature_mark` in the ranking and the panel when the `temp_k` bit is set |

## earth_\<mission\>_pairs.bin (on demand; real-value missions: rover, solar)

All columns follow `passing` (the same rows as `earth_<mission>.bin`).

| column | type | content |
|---|---|---|
| `list_order` | int32 | display order of the passing points: 1..P = the paired points by `rank`; P+1.. = the points without a twin by published `suitability` descending, ties by Earth cell id |
| `<v>.earth`, `<v>.moon`, `<v>.diff` | float32 | for every similarity variable `v` (`missions.json` `similarity.variables[].pairs_columns`): the real value of the Earth cell, of the twin, and `|Earth - twin|` computed in double precision; `.earth` is set on every passing point, with or without a twin (NaN only when the Earth cell has no value); `.moon` and `.diff` are NaN on a point without a twin (or with no value). Display values; the recompute uses `s.<v>` |
| `nopair_kind` | int32 | sentinel = paired; otherwise index into `missions.json` `similarity.nopair_kinds`: `key_value_missing_on_earth`, `no_zone_cell_within_bound` (no zone cell has that variable within its bound), `no_joint_match` (each variable alone can be matched, no single cell meets every bound) |
| `nopair_var` | int32 | sentinel = paired; otherwise the index of the blocking variable in `similarity.variables` |
| `nopair_gap` | float32 | the smallest gap found for that variable, in its unit (`no_zone_cell_within_bound`: distance to the closest zone value; `no_joint_match`: its difference at the zone cell nearest to meeting every bound); NaN = paired or no Earth value |
| `atm.ground_kwh_m2_day`, `atm.toa_kwh_m2_day`, `atm.lost_share` | float32 | **solar only**, every passing point: Earth irradiance at the ground (`v.irradiance_kwh_m2_day`), Earth sunlight above the atmosphere (DERIVED), `1 - ground / above` (0-1), from the unrounded values: the percentage printed in `texts.solar_limitation` is computed from the two displayed values instead (`{loss_pct}`, note of 2026-11-15 at the top) |

Variables in the shipped bundle: rover `slope_deg`, `roughness_m`, `elevation_rel_m`; solar `irradiance_toa_kwh_m2_day`, `slope_deg`, `roughness_m`. `elevation_rel_m` is `elevation_m` minus the area-weighted mean `elevation_m` of the body (`missions.json` `similarity.variables[].sides.<body>.body_mean`: Earth 695.9244 m, Moon -248.3894 m). `irradiance_toa_kwh_m2_day` is the DERIVED sunlight above the atmosphere on Earth and the lunar surface irradiance (`v.irradiance_kwh_m2_day`) on the Moon.

## earth_lunar_base_pairs.bin (on demand; revision 6, rule percentile_and_real_tolerance)

All columns follow `passing` (2,419 rows, the same rows as `earth_lunar_base.bin`). The Earth-side columns `<v>.earth` and `<v>.earth_pct` hold the point's own value and percentile on **every** passing point, with or without a twin (as in the rover and solar pairs files; NaN only when the point has no value); every other float32 column (`.moon`, `.diff`, `.moon_pct`, `.diff_pct`, `info.<v>.*`) is NaN on a point without a twin (or with no value).

| column | unit | content |
|---|---|---|
| `list_order` | - | as in the real-value pairs files: 1..450 the paired points by `rank`, then the points without a twin by published suitability descending, ties by id |
| `tmin_k.earth`, `tmin_k.moon`, `tmin_k.diff` | K | coldest temperature, real values: Earth = WorldClim **modelled air** temperature of the coldest month (`v.tmin_c` + 273.15), Moon = Diviner **measured surface** night minimum (`v.tmin_c` + 273.15); `diff` = \|Earth - twin\| in K (also in degrees C as absolute values: K - 273.15) |
| `tmin_k.earth_pct`, `tmin_k.moon_pct`, `tmin_k.diff_pct` | percentile points | the compared values: percentile of the Earth point among the 2,419 passing points, of the twin among the 280 zone cells, and their difference (key, tolerance 10, bound 10) |
| `lst_diurnal_amp_k.earth`, `.moon`, `.diff` | K | daily thermal amplitude, real values (Earth MODIS 10:30 - 22:30; Moon Diviner max - min) |
| `lst_diurnal_amp_k.earth_pct`, `.moon_pct`, `.diff_pct` | percentile points | compared values (key, tolerance 10, bound 10) |
| `slope_deg.earth`, `.moon`, `.diff` | deg | real values, compared as they are (secondary, tolerance 2, bound 4) |
| `roughness_m.earth`, `.moon`, `.diff` | m | real values, compared as they are (secondary, tolerance 30, bound 60) |
| `info.temp_k.earth`, `.moon`, `.diff` | K | mean temperature: **not part of the similarity**, shown as a difference |
| `info.elevation_rel_m.earth`, `.moon`, `.diff` | m | relative elevation (centred on each body's area-weighted mean, as for rover): not part of the similarity |
| `info.irradiance_kwh_m2_day.earth`, `.moon`, `.diff` | kWh/m2/day | ground irradiance: information only |
| `nopair_kind` | int32 | sentinel = paired; else index into `missions.json` `missions[lunar_base].similarity.nopair_kinds`: `key_value_missing_on_earth`, `no_cell_meets_thermal_position` (no zone cell has both keys within 10 points), `no_cell_meets_terrain` (no zone cell has slope within 4 deg and roughness within 60 m), `no_cell_meets_either`, `no_single_cell_meets_both` (each group is met by some cell, never by the same one) |
| `nopair_var`, `nopair_gap` | int32, float32 | the blocking variable (index into `similarity.variables`) and the smallest gap found, in its **compared** unit (percentile points for the thermal keys, deg, m): its difference at the zone cell nearest to meeting the failed group's bounds (for `no_single_cell_meets_both`: every bound); for `no_cell_meets_either` the thermal group |
| `nopair_var2`, `nopair_gap2` | int32, float32 | `no_cell_meets_either` only: the same for the terrain group; sentinel / NaN otherwise |

Today: 450 paired; without a twin 237 thermal position, 943 terrain, 196 both, 593 no single cell (`missions.json` `similarity.unpaired_by_kind`).

**Per-pair sentence** (`similarity.json` `texts.lunar_base_pair_sentence`, approved by the team on 2026-11-15 08:55 CET; show it on every pair): placeholders `{temp_diff_k}` = `info.temp_k.diff` (0 decimals), `{tmin_moon_c}` = `tmin_k.moon` - 273.15 (0 decimals), `{tmin_earth_c}` = `tmin_k.earth` - 273.15 (1 decimal), `{amp_diff_k}` = `lst_diurnal_amp_k.diff` (0 decimals), `{slope_diff}` = `slope_deg.diff` (1 decimal), `{rough_diff}` = `roughness_m.diff` (1 decimal); each placeholder's `file`, `column`, `subtract` and `decimals` are in the template. Fill it from the stored float32 values (value, minus `subtract`, shown with `decimals` digits: `toFixed(decimals)`; the engine fills `explain.json` with the same rule, `engine/display.py` `to_fixed_of_stored`, an exact implementation of `toFixed`, so `explain.json` is character for character what this rule prints; checked on all 450 pairs by `tests/test_audit_corrections_1.py`. Until the audit correction of 2026-11-15 the engine used Python's `f"{x:.{d}f}"`, which rounds an exact binary half to even where `toFixed` rounds it up: 8 values in 8 of the 450 pairs, e.g. a temperature difference of exactly 154.5 K, printed 154 instead of 155, none of them in the top 25 of `explain.json`), and show the values beside it from the same columns, so the sentence and the panel agree. Some source values sit on a decimal half (e.g. a lunar minimum of -232.50 °C, a roughness difference of 27.35 m): in 30 of the 450 pairs the last digit shown follows the stored float32 value rather than the CSV's double; both are correct roundings of the same number. The words "colder" and "larger" hold on every pair (the twin is colder and swings more; checked by a test). Number 1 (E17538 with M63528), as in `explain.json`: "... the twin is 195 K colder on average (minimum -232 °C at the surface against -24.5 °C air temperature here) and its day-night swing is 138 K larger; slope differs by 0.5° and roughness by 0.3 m."

## earth_detail_NN.bin (on demand, one tile per 10 grid rows)

`manifest.detail_tiles.files[k]` covers grid rows `row_start..row_end`; tiles are in row order, so concatenating every tile's rows gives the `land` order of `earth_base.bin`. All columns follow `tile_land`.

| column | content |
|---|---|
| `id` | Earth cell id (land cells of the tile, ascending) |
| `z.<variable>` | int32 q, /1e4: the per-body z-score of each active z-score similarity variable (`similarity.json` `active_variables`); **only in builds with a z-score mission** (`--similarity-rule zone_twin` or `repo_global_mean`), absent from the shipped bundle since revision 6; missing when the cell has no value or is outside the normalised population (`elevation_m > 0`) |
| `<mission>.u.<variable>` | int32 q, /1e6: utility 0-1 of each weighted variable of the mission; missing when the cell is eliminated for the mission or has no value |
| `lunar_base.ice.fail_bits` | bits of `missions[lunar_base].component_results.ice.reason_codes`; 0 = passes ice |
| `lunar_base.ice.u.<variable>`, `lunar_base.ice.suitability` | ice utilities (/1e6) and suitability (/100); missing unless the cell passes ice |

## moon_base.bin and moon_\<mission\>.bin (on demand)

`moon_base.bin`: `lat`, `lon`, the `v.<column>` value columns where the Moon has data (`rain_mm_day` and `wind_max_ms` have none; `mask_fraction`, `rock_or_bare_frac`, `thermal_inertia_class` and `permafrost_class` are constant by definition and stored per grid row), `info.rock_abundance_frac` (float32: Diviner rock abundance, information only, a different quantity from `rock_or_bare_frac`; its provenance is in `variables.json` `lunar_info_columns`), `feature` (index into `iau_moon_features.json`: the nearest primary IAU feature) and `feature_km` (great-circle km to its centre); revision 6: `region` (int32, all cells: index into `mission_zones.json` `regions`, the cell's lunar region A-F).

`moon_<mission>.bin`: `fail_bits` (all lunar cells, same bit table as Earth; information only: **lunar cells are not filtered for the similarity**) and, only when the rule has twins, `twin_count` (Earth cells whose twin is this cell; for real-value missions only paired points count).

Lunar z-scores are not stored per cell: `z = clip((value - median) / scale, -4, 4)` rounded to 4 decimals with the Moon's `median` and `scale` from `similarity.json`; a twin's z-scores are in `twins.json`.

## mission_zones.json (on demand; revision 6)

```json
{"consulted_on":"2026-11-15","source_document":"docs/MISSION_ZONES.md",
 "regions":[{"code":"A","label":"...","rule":"plain words","cells":280},{"code":"B",...,"cells":5120},{"code":"C",...,"cells":5400},
            {"code":"D",...,"cells":6686},{"code":"E",...,"cells":25971},{"code":"F",...,"cells":21343}],
 "mission_zone_regions":{"rover":["A","B"],"solar":["D"],"lunar_base":["A"]},
 "region_column":"moon_base.bin 'region' (index into 'regions')",
 "texts":{"general_note":"...","zone_why":{"rover":"...","solar":"...","lunar_base":"..."},
          "outside":{"rover":{"C":"...","D":"...","E":"...","F":"..."},"solar":{...},"lunar_base":{...}}},
 "texts_status":"...","figures":...,"approved_by":...,"label_source":"..."}
```

- A lunar cell's region: `regions[moon_base.bin region[id]]`. Regions are evaluated in order, first match wins (A the nine NASA regions = the Lunar base zone; B latitude <= -75 not A; C latitude >= 75; D |latitude| <= 30 and elevation <= -1,200 m = the Solar panels zone; E |longitude| > 90; F the rest); the thresholds are those of the mission zones (`engine_config.json` `lunar_regions`).
- For the mission on screen: a cell whose region is in `mission_zone_regions[mission]` is inside the zone (normal pair view); otherwise show `texts.outside[mission][code]`. Show `texts.general_note` once in the Moon view and `texts.zone_why[mission]` with the zone.
- `texts`, `region_labels` (as `regions[].label`), `consulted_on`, `figures` and `approved_by` come verbatim from `tierra luna/engine/mission_zone_texts.json`. When that file is absent, not valid JSON or lacks a required key, `texts` is `null`, `consulted_on` is `null`, the labels are the engine's fallback labels (`label_source`) and `manifest.mission_zone_texts.status` says why; when it is present the build fails if any mission lacks a text for a region outside its zone.

## missions.json

```json
{"bundle_version":"v2","dataset":"real_1deg","config_version":"v1-draft","config_note":"...",
 "offered_missions":["rover","solar","lunar_base"],"default_mission":"rover",
 "components_not_offered":{"thermal":"core of lunar_base (...)","ice":"information component of lunar_base, ..."},
 "alpha":0.5,"alpha_why":"...","similarity_rule":"per_mission",
 "similarity_rules":{"rover":"real_value_tolerance","solar":"real_value_tolerance","lunar_base":"percentile_and_real_tolerance"},
 "funnel":[{"step":1,"name":"common gates","text":"..."}, ... {"step":6,"name":"final","text":"..."}],
 "elimination_line_rule":"the cell's reason codes (fail_bits) in bit order, their 'text' joined with '; '",
 "confidence_codes":["low","medium","high"],
 "missions":[{
   "id":"solar","title":"Solar array placement","description":"Colocacion de placas solares","author":"...",
   "threshold_status":{"status":"team_design_values","text":"Team design values: ... no external source ..."},
   "provisional":false,"provisional_note":null,"frozen_at":null,"components":{"core":null,"info":[]},
   "on_missing_gate":"drop","require_present":["irradiance_kwh_m2_day","sun_elev_max_deg","sun_low_frac_0_5deg","slope_deg"],
   "files":{"EARTH":"earth_solar.bin","MOON":"moon_solar.bin"},
   "gates":[{"variable":"elevation_m","step":1,"columns":{"EARTH":"elevation_m","MOON":"elevation_m"},"origin":"common",
             "applies_to":["EARTH"],"min":1.0,"max":null,"max_from":null,"allow":null,"exclude":null,"limit":"[1.0, inf]",
             "source":"solo tierra firme (...)"}, ...],
   "weighted_variables":[{"variable":"irradiance_kwh_m2_day","kind":"numeric","label":"Solar irradiance","unit":"kWh/m2/day",
             "columns":{...},"levels":{"EARTH":"MODELLED","MOON":"DERIVED"},"weight":0.35,"bad":2.5,"good":6.0,"map":null,
             "default":null,"why":"energia disponible","also_in_similarity":false}, ...],
   "reason_codes":[{"bit":2,"code":"irradiance_kwh_m2_day:below_min","variable":"irradiance_kwh_m2_day","kind":"below_min",
                    "label":"below minimum: Solar irradiance","step":3,
                    "text":"irradiance_kwh_m2_day outside [2.5, inf]","team_text":"irradiance_kwh_m2_day fuera de [2.5, inf]"}, ...],
   "pass_counts":{"EARTH":18777,"EARTH_LAND_CELLS":25497,"MOON":52400,"MOON_CELLS":64800},
   "ranked_count":6360,"passing_without_similarity":12417,
   "top_failure_reasons":{"EARTH_LAND":[...],"MOON":[...]},
   "missing_data":{"EARTH_LAND":{"cells_with_missing_data":...,"cells_failing_only_on_missing_data":...,"by_variable":{...}},"MOON":{...}},
   "alpha":0.5,
   "similarity":{"rule":"real_value_tolerance",
     "variables":[{"variable":"irradiance_toa_kwh_m2_day","label":"Sunlight without atmosphere","unit":"kWh/m2/day","role":"key",
                   "weight":0.8,"tolerance":0.6,"bound":0.6,"tolerance_set_by":"the team lead's delegate on the team lead's behalf, 2026-11-15 (morning)",
                   "why":"...","sides":{"EARTH":{"kind":"toa_insolation","column":null,"level":"DERIVED","text":"..."},"MOON":{"kind":"column","column":"irradiance_kwh_m2_day","level":"DERIVED",...}},
                   "pairs_columns":{"earth":"irradiance_toa_kwh_m2_day.earth","moon":"...","diff":"..."},"score_column":"s.irradiance_toa_kwh_m2_day"},
                  {"variable":"slope_deg","role":"secondary","weight":0.1,"tolerance":2.0,"bound":4.0,...}, ...],
     "weights_why":"...","score":"s = exp(-0.5 * (|earth value - moon value| / tolerance)^2)","similarity_formula":"...",
     "filter":{"key":"|difference| <= 1 x tolerance","secondary":"|difference| <= 2 x tolerance","missing_key":"...","missing_secondary":"..."},
     "score_decimals":6,
     "zone":{"kind":"abs_lat_max_elevation_max","abs_lat_max":30.0,"elevation_max_m":-1200.0,"elevation_column":"elevation_m",
             "name":"Mare Tranquillitatis & Equatorial Maria","source":"analog_finder.build_lunar_reference_zones: ...","why":"...","cells":6686},
     "passing_count":18777,"paired_count":6360,"unpaired_count":12417,
     "nopair_kinds":["key_value_missing_on_earth","no_zone_cell_within_bound","no_joint_match"],
     "unpaired_reasons":[{"kind":"no_zone_cell_within_bound","variable":"irradiance_toa_kwh_m2_day","role":"key","bound":0.6,
                          "earth_cells":12416,"gap_min":0.6563,"gap_median":4.1466,"gap_max":4.9112}, ...],
     "pairs_file":"earth_solar_pairs.bin","list_rule":"...",
     "distinct_twins":1704,"earth_cells_with_twin":6360,"largest_share":{"twin_id":21795,"earth_cells":159,"share":0.025}},
   "confidence_counts":{"low":6060,"medium":12717,"high":0},
   "distributions":{"suitability":{"min":...,"p05":...,"p25":...,"median":...,"p75":...,"p95":...,"max":...,"mean":...,"n":...},
                    "similarity":{...},"final":{...},"confidence_score":{...}},
   "component_results":{},
   "known_limitations":["..."],
   "facts":{"moon_pass_abs_lat_max":...,"distinct_twins":0,"twins":[],"twin_abs_lat_range":null,"top_n":25,
            "top_n_country_counts":{...},"confidence_constant":false},
   "not_used_by_engine":{"tolerances":null,"workable_days":null,"domain_weights":{...},"why":"..."}}, ...]}
```

- **`threshold_status`**: `provisional` (rover: its JSON block says so; `provisional_note` is the block's text) or `team_design_values` (solar and lunar_base: the JSON note says the solar and thermal thresholds have no external source). Show it next to every number of the mission.
- **`reason_codes`**: the bit table of `fail_bits` (both bodies). `label` uses the variable's display label (`weighted_variables[].label`, `variables.json` `label`), so mission variable names such as `slope_300m_deg` never reach a label; `variable` and `text` keep the mission variable name, as the team lead's reason format requires. `kind` is `missing`, `below_min`, `above_max`, `not_allowed` or `excluded`; `step` is the funnel step; `text` the English line; `team_text` mission_scoring.py's own reason text (the engine checks, on every cell, that the join of the `team_text` of a cell's codes equals the reason string mission_scoring.apply_gates gives). At most 31 codes per mission.
- **`gates[].applies_to`**: the land gate `elevation_m` applies to EARTH only; `mask_fraction` to both bodies (it is 1 on the Moon by definition).
- **`weighted_variables[].also_in_similarity`**: true when the same variable is also one of the repository similarity variables (e.g. solar `slope_deg`, `roughness_m`).
- **`similarity`** of a real-value mission (rover, solar): shown in the example above; `zone.kind` is `lat_max` (rover: lunar latitude <= `lat_max`) or `abs_lat_max_elevation_max` (solar: |latitude| <= `abs_lat_max` and `v.<elevation_column>` <= `elevation_max_m`). `tolerance_set_by` must be shown next to each tolerance ("illustrative team values" for slope and roughness).
- **`ranked_count`** = points with a rank (paired); **`passing_without_similarity`** = passing points without a twin; their sum is `pass_counts.EARTH`.
- **`known_limitations`**: since revision 5 the solar card no longer starts with the decision 5 text (withdrawn); the solar per-pair text is `similarity.json` `texts.solar_limitation`.
- **`similarity`** of lunar_base (revision 6, rule `percentile_and_real_tolerance`): `variables` (per variable `variable`, `label`, `unit` = compared unit (`percentile points` for `tmin_k` and `lst_diurnal_amp_k`, `deg`, `m`), `real_unit` (K, K, deg, m), `role`, `weight` (0.4, 0.4, 0.1, 0.1), `scale` (`percentile_within_population` or `real`), `tolerance` (10, 10, 2, 30), `bound` (10, 10, 4, 60), `tolerance_set_by` (show it next to each tolerance: the delegate on the team lead's behalf, 2026-11-15 08:55 CET; terrain: illustrative team values of rover_preset.py), `why`, `sides` (how each side is made, with its level: Earth `tmin_c` MODELLED air temperature, Moon MEASURED surface temperature), `pairs_columns`, `compared_columns`, `score_column`, `population_size`), `populations`, `percentile`, `zone` (`name` "NASA's nine candidate landing regions near the lunar south pole", `cells` 280), `filter`, `nopair_kinds`, `nopair_groups`, `unpaired_by_kind`, `unpaired_reasons`, `info_columns`, `pair_sentence`, `pairs_file`, `list_rule`, counts and `distinct_twins`, `largest_share`.
- **`similarity`** of a z-score mission (none in the shipped bundle since revision 6): the rule; with `zone_twin` also `zone` (`name`, `kind`, `used`, `reason`, `cells`, `regions`), `distinct_twins`, `earth_cells_with_twin`, `largest_share` (`twin_id`, `earth_cells`, `share`).
- **`component_results`** (`lunar_base` only): `ice` with its gates, weighted variables, reason codes (the bit table of the tile's `lunar_base.ice.fail_bits`), pass counts (`EARTH`, `MOON`, `EARTH_passing_both`), top failure reasons and suitability distribution, and `role`: information only.
- **`distributions`**: of the passing Earth cells (suitability) and the ranked ones (the rest).

## similarity.json (start)

Revision 5 adds, before the z-score keys:

```json
{"bundle_version":"v2","dataset":"real_1deg","rule":"per_mission",
 "rules":{"rover":"real_value_tolerance","solar":"real_value_tolerance","lunar_base":"percentile_and_real_tolerance"},
 "rule_why":"...","rule_options":{"real_value_tolerance":"...","zone_twin":"...",...},"alpha":0.5,
 "real_value":{"rule":"real_value_tolerance","missions":["rover","solar"],"why":"...","score":"...","similarity":"...",
   "filter_bound_multiplier":{"key":1.0,"secondary":2.0},"missing_key":"...","missing_secondary":"...","score_decimals":6,
   "twin":"...","published":"...","meaning":"...",
   "derived_variables":{"elevation_rel_m":{"EARTH":{"kind":"relative_to_body_mean","column":"elevation_m","level":"DERIVED",
                                                    "body_mean":695.9244,"cells_in_mean":25245,"text":"..."},"MOON":{...,"body_mean":-248.3894}},
                        "irradiance_toa_kwh_m2_day":{"EARTH":{"kind":"toa_insolation","level":"DERIVED",...},"MOON":{"kind":"column","column":"irradiance_kwh_m2_day",...}}, ...},
   "irradiance_toa":{"formula":"...","settings":{"solar_constant_w_m2":1361.0,"obliquity_deg":23.44,"eccentricity":0.0167,...},
                     "settings_why":"...","computed_reference_kwh_m2_day":{"0":9.9743,"30":8.7651,"45":7.3667,"60":5.6717},"level":"DERIVED ..."},
   "lunar_day_earth_days":29.53,"reference_tolerances_not_used":{...},"info_differences":{...},
   "missions_detail":{"rover":{"variables":[...],"zone":{...},"weights_why":"..."},"solar":{...}}},
 "z_rule_missions":["lunar_base"],
 ... the z-score keys below (absent from the shipped bundle since revision 6: no z-score mission) ...,
 "texts":{...}}
```

Revision 6 adds `"percentile_and_real":{"rule":"percentile_and_real_tolerance","missions":["lunar_base"],"why","score","similarity","filter_bound_multiplier","missing_key","missing_secondary","score_decimals","twin","meaning","missions_detail":{"lunar_base":{"variables","percentile","populations","zone","weights_why","not_part_of_similarity"}}}`. The shipped bundle has no z-score mission, so the keys below are **absent** from it (present in a `--similarity-rule zone_twin` / `repo_global_mean` build).

The z-score keys (revision 4 layout; they apply to the missions in `z_rule_missions`):

```json
{"bundle_version":"v2","dataset":"real_1deg","rule":"repo_global_mean","rule_why":"...","rule_options":{...},"alpha":0.5,
 "function":"analog_finder.compute_analog_ranking + analog_finder.normalize_planetary_features",
 "features_and_weights":"analog_finder.ANALOG_FEATURES and analog_finder.DEFAULT_WEIGHTS, imported at build time (not copied)",
 "formula":{"z":"...","distance":"...","similarity":"...","decay":0.45,"final":"..."},
 "meaning":"Each body is normalised on its own, so 'similar' means the same RELATIVE position on each body ...",
 "earth_population":{"rule":"elevation_m > 0.0","cells":25095},"moon_population":{"rule":"every lunar cell","cells":64800},
 "variables":[{"variable":"elevation_rel_m","status":"active","status_reason":null,"weight":0.15,"norm_weight":0.2,
               "columns":{"EARTH":"elevation_m","MOON":"elevation_m"},"column_note":"...","levels":{"EARTH":"MEASURED","MOON":"MEASURED"},
               "stats":{"EARTH":{"valid":true,"n":25095,"median":470.6,"scale":1006.7828,"mean":...,"min":...,"max":...,
                                 "iqr":...,"std_dev":...,"distinct_values":...,"variation":"ok"},"MOON":{...}},
               "target_global_mean":{"z":0.1425,"value":-521.3786}},
              {"variable":"rock_or_bare_frac","status":"excluded","status_reason":"Team lead decision 3: ...","norm_weight":null,...},
              {"variable":"sar_sigma0_db","status":"inactive","status_reason":"no values on at least one body ...",...}, ...],
 "active_variables":["elevation_rel_m","slope_deg","roughness_m","temp_k"],
 "variation_threshold":1e-06,
 "variation_findings":[{"variable":"rock_or_bare_frac","body":"MOON","variation":"zero","action":"removed from the similarity (similarity_excluded)"}, ...],
 "not_part_of_similarity":["irradiance_kwh_m2_day","lst_diurnal_amp_k","tmin_c","thermal_inertia_class","permafrost_class","rock_or_bare_frac"],
 "not_part_of_similarity_note":"...","z_decimals":4,
 "target":{"kind":"global_mean","name":"Global Lunar Surface Mean (-90° to +90°)",
           "profile":{"elevation_rel_m":{"z":0.1425,"value":-521.3786}, ...},
           "info_not_in_similarity":{"irradiance_kwh_m2_day":{"mean":6.4848,"level":"DERIVED","part_of_similarity":false}, ...}},
 "twins":null,"no_twin_reason":"..."}
```

With `zone_twin`, `target` is `{"kind":"zone_twin","tie_rule":"lowest_lunar_id","lunar_cells_filtered":false,"zones":{...}}` with one entry per `zone_twin` mission (none in the shipped bundle since revision 6; the real-value zones are in `missions.json` `similarity.zone` and `real_value.missions_detail`) and `twins`/`no_twin_reason` are absent.

- **Meaning, real-value missions (rover, solar).** Similarity is computed on real values within stated tolerances: the twin's key variables are within their tolerance of the Earth point, its secondary variables within twice theirs; show both values, the difference and the tolerance, with `texts.similarity_meaning_real_values`.
- **Meaning, lunar_base (revision 6).** A likeness of thermal **position**, not of temperature: the two thermal keys are compared as percentiles within each population, terrain in real values; show `texts.similarity_meaning_lunar_base`, the percentiles, the real values and differences, and the per-pair sentence on every pair.
- **Meaning, z-score missions (none shipped since revision 6).** Each body is normalised on its own, so a high similarity means the same **relative** position on each body, not equal absolute values. Show both: the Earth cell's z (tile `z.<v>`) and value (`earth_base.bin` `v.<columns.EARTH>`), and the lunar side's z and value (`target.profile`, or the twin's in `twins.json`).
- **`columns`**: the real column each similarity variable is read from, after `column_overrides` (e.g. `slope_deg` is read from `slope_iso_deg`); it is always a stored `v.<column>` of `earth_base.bin` / `moon_base.bin` (`test_similarity_columns_are_stored_columns`).
- **`status`**: `active` (in the distance, `norm_weight` = weight / sum of active weights), `excluded` (a dataset decision; reason given), `inactive` (no values on a body: the repository's own rule drops it).
- **`variation`** per body: `ok`, `near_zero` (at least half the cells share one value), `zero` (every value equal: the repository would give every cell z = 0 and still count the variable), `no_data`.
- **`texts`, revision 6**: `similarity_meaning_lunar_base` (lunar_base, wherever its similarity is shown); `lunar_base_pair_sentence` (lunar_base, per-pair template on every pair; placeholders in section "earth_lunar_base_pairs.bin"); `no_twin_note_lunar_base` (`variants` keyed by `nopair_kind`; placeholders `{variable}`, `{unit}`, `{bound}`, `{gap}` from `nopair_var`/`nopair_gap` and, for `no_cell_meets_either`, `{variable2}`, `{unit2}`, `{gap2}` from `nopair_var2`/`nopair_gap2`; gaps with 2 decimals rounded up). `similarity_meaning`, `missing_temperature_mark` and `missing_temperature_note` carry `missions: []` and `status` "no longer applies" (they described the z-score rule): not shown. `twin_sharing_note`: first sentence only, every mission.
- **`texts`, revision 5**: every entry may carry `missions` (the missions it applies to). New: `similarity_meaning_real_values` (rover, solar; wherever a similarity is shown); `no_twin_note` (rover, solar; on every passing point without a twin; placeholders `{variable}` = `similarity.variables[nopair_var].label`, `{bound}`, `{unit}`, `{gap}` = `nopair_gap` with 2 decimals rounded **up** (ceil), so a gap just above its bound never displays as the bound (rover: 30.02 m against 30 m); use `variant_no_joint_match` when `nopair_kind` is `no_joint_match`); `solar_limitation` is now a **per-pair template** for solar pairs (`mission_card: false`, `replaces` the decision 5 text): placeholders `{toa_earth}` = `earth_solar_pairs.bin` `atm.toa_kwh_m2_day`, `{toa_moon}` = `irradiance_toa_kwh_m2_day.moon`, `{ground_earth}` = `atm.ground_kwh_m2_day` (1 decimal each), `{loss_pct}` = 100 x `atm.lost_share` (0 decimals); the lunar day (29.5) is filled at build time (number 1: 9.6, 9.6, 6.2, 36). *Since the wording and display rounding note of 2026-11-15 (top of this file), `{loss_pct}` is computed from the two displayed numbers: number 1 reads 9.6, 9.6, 6.2, 35.* `similarity_meaning`, `missing_temperature_mark` and `missing_temperature_note` apply to lunar_base only; `twin_sharing_note` to every mission (first sentence only for rover and solar).
- **`texts`** (revision 4): the English web texts approved by the team on 2026-11-15, verbatim from section 8 of each decision in `docs/DECISIONS.md` (`missing_temperature_mark` is the short mark of the team's answer 3). Each entry is `{decision, text, where}` (`twin_sharing_note` also `placeholders`; `solar_limitation` also `mission`): `similarity_meaning` (decision 1: wherever a similarity is shown, next to the absolute values of both sides), `rock_note` (decision 2), `missing_temperature_mark` and `missing_temperature_note` (decision 3: pairs with the `temp_k` bit of `sim_missing_bits`), `twin_sharing_note` (decision 4: N = `twins.json` `earth_cells`, X = 100 N / `ranked_count`; the second sentence is about lunar_base), `solar_limitation` (decision 5; also the first item of the solar mission's `known_limitations`). *Revision 5 replaces the decision 5 solar text with the per-pair template described in the previous bullet and removes it from `known_limitations`; the temperature texts apply to lunar_base only.*
- **Not part of the similarity**: the variables in `not_part_of_similarity` are shown for both points with the mark "not part of the similarity": Earth from `earth_base.bin`, the Moon from `target.info_not_in_similarity` (whole-Moon mean or commonest class) or from the twin (`twins.json` `not_part_of_similarity`).

## twins.json (on demand; only with a twin rule)

```json
{"bundle_version":"v2","dataset":"real_1deg","gazetteer":"...",
 "missions":{"rover":{"rule":"zone_twin","distinct_twins":744,"earth_cells_with_twin":10337,
   "largest_share":{"twin_id":59479,"earth_cells":895,"share":0.0866},
   "twins":[{"id":59479,"lat":-75.5,"lon":-100.5,"earth_cells":895,
             "z":{"elevation_rel_m":...,"slope_deg":...,"roughness_m":...,"temp_k":...},
             "values":{"elevation_rel_m":...,"slope_deg":...,"roughness_m":...,"temp_k":...},
             "not_part_of_similarity":{"irradiance_kwh_m2_day":...,"lst_diurnal_amp_k":...,"tmin_c":...,
                                       "thermal_inertia_class":"regolito","permafrost_class":"ninguno","rock_or_bare_frac":1.0},
             "feature":{"name":"Boltzmann","type":"Crater, craters","distance_km":80.9,
                        "url":"http://planetarynames.wr.usgs.gov/Feature/..."}}, ...]}, ...}}
```

lunar_base (revision 6): a row has `values` (lunar real values of `tmin_k`, `lst_diurnal_amp_k` in K, `slope_deg`, `roughness_m`), `percentiles` (the cell's percentile within the 280 zone cells of the two thermal keys), `not_part_of_similarity` (`temp_k`, `irradiance_kwh_m2_day`, classes, `rock_or_bare_frac`, `elevation_rel_m`), no `z`; `earth_cells` counts the paired points only.

Real-value missions (revision 5): a row has `values` = the lunar real value of each similarity variable (`elevation_rel_m` centred on the Moon's mean, `irradiance_toa_kwh_m2_day` = the lunar surface irradiance), no `z`, and `not_part_of_similarity` adds `temp_k`; `earth_cells` counts the paired points only. The lunar_base rows are unchanged from revision 4.

Twins are listed by Earth-cell count descending, then id. `earth_cells` is the number of Earth points sharing the twin; `feature` is the nearest primary feature of the USGS/IAU gazetteer with the great-circle distance and the gazetteer URL.

## variables.json

As before: per variable `name`, `label`, `unit`, `kind`, `description`, `categories`, `used_by`, `in_engine`, `comparability`, and per body `column`, `stored_as`, `level`, `level_text`, `level_note`, `product`, `version`, `url`, `licence_credit`, `native_resolution`, `aggregation`, `formula`, `true_baseline`, `true_baseline_km`, `cell_ns_km`, `caveat`, `provenance_caveat`. New: `lunar_info_columns` (`[{column, stored_as, label, unit, note, level, product, url, licence_credit, caveat, used_by_engine: false}]`).

- Show `level` and `caveat` next to every value, and the true baseline for relief variables (never "300 m").
- Only `MEASURED` may be presented as measured. Lunar `permafrost_class` is `MODELLED`: the label `ninguno` on every cell, set by definition (team lead decision 5), not a measurement.
- `comparability` describes the physical quantities; it no longer selects similarity variables (the repository similarity uses its own fixed list, `similarity.json`).

## places.json, place_detail.json, earth_place_detail.bin

Unchanged: `places.json` `countries` (`[{code, name}]`, indexed by `earth_base.bin` `country`), `regions`, `region_rule`; `earth_place_detail.bin` (land rows) `label_rule`, `nearest_place`, `nearest_place_km`; label rules `natural_earth_polygon`, `natural_earth_polygon_geonames_code`, `nearest_geonames_place`, `antarctic_treaty_area`.

## explain.json, iau_moon_features.json, lunar_named_sites.json, validity.json

- `explain.json`: `{"top_n":25,"missions":{"rover":[item, ...], ...}}`, the top 25 ranked Earth cells per mission. Item: `rank`, `id`, `lat`, `lon`, `place`, `suitability`, `coverage`, `breakdown` (per weighted variable `variable`, `value`, `utility`, `weight`, `contribution`, `points`, `level`; sorted by contribution), `similarity` (`value`, `rule`; z-score rules: `earth` and `moon` z and value per active variable, with `zone_twin` also `twin`; real-value rule: `twin`, `variables` = per similarity variable `{variable, role, weight, tolerance, bound, earth, moon, difference, score}`, `not_part_of_similarity` = `{temp_k, lst_diurnal_amp_k[, irradiance_kwh_m2_day]: {earth, moon, difference}}` and, for solar, `atmosphere` = `{ground_kwh_m2_day, toa_kwh_m2_day, lost_share}` and `pair_sentence` (`texts.solar_limitation` filled with the display rule of 2026-11-15; `lost_share` is the unrounded share, not the printed percentage); lunar_base (revision 6): `variables` = per variable `{variable, role, scale, weight, tolerance, bound, unit, earth, moon, difference, real_unit, earth_real, moon_real, difference_real, score}` (earth/moon/difference in the compared unit), `not_part_of_similarity` = `{temp_k, elevation_rel_m, irradiance_kwh_m2_day}`, `meaning`, `pair_sentence` (filled)), `alpha`, `final`, `confidence`, `confidence_score`; `lunar_base` items also carry `components.ice` (`pass`, `fail` texts, `suitability`).
- `iau_moon_features.json`: column-oriented `name`, `type`, `lat`, `lon`, `diameter_km`; `moon_base.bin` `feature` indexes these arrays.
- `lunar_named_sites.json`: per site `missions.<m>` = `{pass, fail, fail_text, twin_of_count}` (`twin_of_count` null without a twin rule).
- `validity.json`: `{"valid", "bodies": {...}}`.

## Recompute formulas (browser)

For mission `m` and a passing Earth cell (`land_index` gives `landPos`; the tile and its position from `manifest.detail_tiles`):

```
V      = weighted_variables (order matters), w_v = weight (or a slider weight)
u_v    = tile "<m>.u.<v>" / 1e6        (null = missing)
U      = { v in V : u_v != null }
suitability = 100 * sum_{v in U} w_v * u_v / sum_{v in U} w_v                 (sum in V order; null if empty)
coverage    = sum_{v in U} w_v / sum_{v in V} w_v

-- real-value missions (rover, solar: similarity.rule == "real_value_tolerance"; lunar_base: "percentile_and_real_tolerance",
-- same formula on its published scores s.<v>)
S      = missions.json similarity.variables (order matters), ws_v = weight (or a similarity slider weight)
s_v    = earth_<m>.bin "s.<v>" / 1e6     (null = missing)
paired = earth_<m>.bin twin != sentinel   (the twin is fixed at build time; a slider never changes it)
similarity = 100 * sum_{v in S, s_v != null} ws_v * s_v / sum_{v in S, s_v != null} ws_v    (sum in S order; null if not paired)

-- z-score missions (none shipped since revision 6; --similarity-rule zone_twin / repo_global_mean builds)
F      = similarity.json active_variables, nw_f = variables[f].norm_weight (sum in F order)
ze_f   = tile "z.<f>" / 1e4;  zm_f = target.profile[f].z (repo_global_mean) or the twin's twins.json z[f] (zone_twin)
P      = { f in F : ze_f != null and zm_f != null }
d2     = sum_{f in F} nw_f * (ze_f - zm_f)^2                 if P == F
       = sum_{f in P} nw_f * (ze_f - zm_f)^2 / sum_{f in P} nw_f   otherwise      (null if P is empty)
similarity = round2(100 * exp(-decay * sqrt(d2)))            decay = formula.decay; round2 = numpy.round(x, 2)

final  = alpha * similarity + (1 - alpha) * suitability       (alpha = missions.json alpha; unrounded suitability and similarity; null without a similarity)
rank   = order the cells with a final by round(final, 2) descending, ties by cell id ascending, from 1
list   = the ranked cells by rank, then the passing cells without a twin by round(suitability, 2) descending, ties by id
         (= earth_<m>_pairs.bin list_order with the published weights)
```

- With the published weights this reproduces every stored value exactly (`round(x, 2) == q / 100`) and the stored rank; `validate_bundle_v2` checks every passing cell of the three missions from the bundle alone, under both rules (`test_recompute_from_bundle_for_both_rules`).
- A suitability slider changes `w_v`; for rover, solar and lunar_base a similarity slider may change `ws_v` (the scores `s.<v>` and the twin stay fixed: the twin was chosen at build time with the published weights). `validate_bundle_v2` checks the exact recompute of all three missions (`test_slider_on_lunar_base_similarity_weights_recomputes_exactly`). Cells that fail the mission are never scored or ranked. `validate_bundle_v2(path, weights=..., sim_weights=...)` returns the recomputed values for replacement weights (`test_slider_on_similarity_weights_recomputes_exactly`).
- Real-value similarity: stored `similarity` = `round(similarity, 2)` (Python `round`), recomputed exactly from `s.<v>`; the browser must sum in the order of `similarity.variables`.
- **Rounding (one rule; corrected 2026-11-15 after the statistical audit, `docs/stats_audit/2_metodo_top5_unidades.md` 3.4.2).** Every stored 2-decimal score of the shipped rules (rover and solar `real_value_tolerance`, lunar_base `percentile_and_real_tolerance`): `suitability`, `similarity`, `final`, and the rank, which orders by the stored `final`, is **Python's `round(float(x), 2)`** on the unrounded double: correctly rounded from the exact binary value of `x`, and an exact binary half (e.g. 0.125) goes to the even digit. Implemented in `engine/suitability.py` `round_like_export` and `engine/export_v2.py` `_round_array` (both convert with `float()` first; checked by `tests/test_audit_corrections_1.py`). It is **not** `numpy.round(x, 2)`, and `round()` applied to a `numpy.float64` is `numpy.round`: the two differ next to a half, e.g. 2.675 (binary 2.67499...) is 2.67 with `round(float(x), 2)` and 2.68 with `numpy.round` or `round(np.float64(2.675), 2)`; a reimplementation in Python must convert to `float` first. `numpy.round(x, 2)` is used only by the z-score similarity of the rules that are not shipped (`zone_twin`, `repo_global_mean`, the `round2` above), as analog_finder does. In the browser, `Math.round(x * 100) / 100` can differ from the stored value next to a half; such a difference can only swap cells whose finals differ by less than 0.01, so the browser must use the stored values, not round its own.

Build-time quantities (display only):

```
numeric utility      u = clip((value - bad) / (good - bad), 0, 1)
categorical utility  u = map[class], or default for a class not in the map; null when the value is missing
z (per body)         z = clip((value - median) / scale, -4, 4), rounded to 4 decimals (analog_finder.normalize_planetary_features)
twin (zone_twin)     = the zone cell with the smallest d2; ties -> lowest lunar id; lunar cells are not filtered
confidence score     = min(Earth level score, Moon level score) * coverage (engine_config confidence); without a twin
                       a variable counts on the Moon when the lunar table has data for it
```

## Units

| variable (mission name) | unit | | variable | unit |
|---|---|---|---|---|
| elevation_m, rough_300m_m, roughness_m | m | | irradiance_kwh_m2_day | kWh/m2/day (per 24 h, horizontal surface) |
| slope_300m_deg, slope_deg, sun_elev_max_deg | deg | | temp_k, lst_diurnal_amp_k | K |
| tmin_c | degC | | mask_fraction, rock_or_bare_frac, sun_low_frac_0_5deg, rock_abundance_frac | fraction 0-1 |
| thermal_inertia_class, permafrost_class | category | | z-scores | dimensionless (robust spreads from the body's median) |

Scores are 0-100; utilities and confidence scores 0-1; distances km.

## Meaning of NaN, null and sentinels

| where | marker | meaning |
|---|---|---|
| `v.<column>` float32 | NaN | the input table has no value for that cell |
| `v.<column>` int32 (category) | sentinel | no class for that cell (e.g. Earth permafrost south of the map) |
| `<m>.u.<v>` | sentinel | eliminated for `m` (check `fail_bits`), or no value for `v` (the weight drops out) |
| `z.<f>` | sentinel | no value for `f`, or outside the normalised population; the variable drops out of the distance |
| `similarity`, `final`, `rank` | sentinel | no twin (real-value missions: no lunar analog, reason in `earth_<m>_pairs.bin`) or no similarity variable with a value |
| `twin` | sentinel | no lunar analog (real-value missions and lunar_base) |
| `<v>.moon_pct/.diff_pct`, `info.<v>.*`, `nopair_gap2` | NaN | no twin / no value; not set |
| `<v>.earth`, `<v>.earth_pct` (pairs files) | NaN | the Earth point has no value (set on every passing point, paired or not) |
| `s.<v>` | sentinel | no twin, or no value for that secondary variable on a side (dropped, weights renormalised) |
| `<v>.moon/.diff`, `nopair_gap` | NaN | no twin / no value; paired |
| `country`, `region`, `label_rule`, `nearest_place` | sentinel | no label |
| JSON | `null` | missing |

`0` is always a real value.

## Bundle v1 (retired)

Engine 3.0.0 no longer writes the v1 JSON bundle: the legacy table goes through the v2 exporter too (`build/legacy_2deg/`, not shipped). The v1 exporter (`engine/export.py`, `engine/contract.py`) remains in the code for reference; its format assumed a lunar twin for every ranked cell, which the default rule does not have.
