# Similarity proposal: Earth analog points and their lunar twins

Status: **proposal for the team lead's approval; nothing is implemented.** Written 2026-11-14 on branch `final-integration`. All numbers come from scripts run read-only on the repository (`scratchpad/stars/proposal2/scripts_v3/`: `artemis_regions.py`, `analysis_v3.py`, `tables_v3.py`, `compose_v3.py`; outputs in `scratchpad/stars/proposal2/out_v3/`). The repository's code and configuration were not changed. Inputs as of branch checkpoint 3b6c949 (that checkpoint added the `lunar_base` block to `mission_scoring.json`, an exact copy of `thermal`, identical to the copy used here, and filled the lunar `permafrost_class` with `ninguno`; neither changes any number below).

## 1. One page

**The rule in five lines.**

1. An Earth cell is ranked only if it passes the mission funnel unchanged (common gates, required variables, hard filters, suitability 0-100 from `mission_scoring.json`; Lunar base = the `thermal` block). Lunar cells are not filtered.
2. Each body is normalised on its own, exactly as `analog_finder.normalize_planetary_features` does: robust z-score `clip((v - median) / (IQR/1.349), -4, 4)`.
3. The **twin** of an Earth cell is the single lunar cell inside the mission's target zone with the smallest weighted z-distance (ties to the lowest cell id): south-pole zone (75S-90S) for Rover and Solar panels; the nine NASA candidate landing regions for Lunar base.
4. Similarity = `100 x exp(-0.45 x sqrt(sum w_i (z_earth,i - z_twin,i)^2))` with the repository's `DEFAULT_WEIGHTS`, renormalised over the variables in the similarity; on the real data that is relative elevation, slope, roughness and temperature (no radar column; bare fraction removed by decision).
5. Final = 0.5 x similarity + 0.5 x suitability (`combine_with_similarity`, alpha 0.5). The twin is named after the nearest IAU feature, with its distance in km and the gazetteer link.

**What "similar" means here.** Because each body is normalised separately, a similarity of 98 means "the Earth cell holds the same relative position on Earth as the twin holds on the Moon", not "the values are equal". Worked pair (Rover, real data, rank 1): Earth cell E5128 (75.5N 91.5W, Canadian Arctic Archipelago, two cells west of the cell of Haughton crater) and lunar cell M60952 (79.5S 67.5W, nearest named feature Drygalski, 108 km).

| variable | Earth E5128 | z on Earth | Moon M60952 | z on Moon |
|---|---|---|---|---|
| slope (deg, ~3.7 km baseline) | 0.88 | +0.38 | 6.19 | +0.39 |
| roughness (m, ~1.9 km lag) | 34.5 | +0.39 | 198.7 | +0.42 |
| relative elevation (m) | -513 | -0.29 | -1,091 | -0.32 |
| surface temperature (K) | 253.5 | -1.43 | 149.5 | -1.49 |
| bare fraction (informative) | 0.998 | | 1 (definition) | |

The slope differs by a factor of 7, the roughness by 6, the temperature by 104 K, yet the similarity is 98.4 (suitability 99.8, final 99.1): both cells are slightly steeper and rougher than their body's median and about 1.4-1.5 robust standard deviations colder than their body's median. Every table below therefore shows the absolute values of both points beside the similarity.

**Lunar base zone.** The official outlines were found: USGS Astrogeology, McClernan (2024), *Down Selected Artemis III Candidate Landing Site Navigational Grids*, doi [10.5066/P1MEQ6UK](https://doi.org/10.5066/P1MEQ6UK), CC0. What is public is a 1 km navigational grid per region (polar stereographic, sphere 1,737.4 km); the separate file of exact region outlines (`A3_9regions-lonlat-simplified.zip`) is listed on the item but not published (HTTP 403). The union of each grid's 1 km squares was used as the region footprint, so it can be slightly larger than the region: the cell counts are an upper bound. The nine footprints touch **280** one-degree cells of the real table and **114** two-degree cells of the legacy table. The whole south-pole zone was also computed (A1sp) for comparison. NASA's naming: since 2026-02-27 Artemis III is a 2027 test flight in low Earth orbit and the first landing is Artemis IV (early 2028); NASA has published no new region list for Artemis IV (section 1.1).

**Three numbers per mission (real 1-degree data, rule A1).**

| mission | Earth points ranked | distinct lunar twins | largest share of one twin | Spearman of the final score vs the global-mean baseline A0 |
|---|---|---|---|---|
| Rover | 10,337 | 305 | 9.2 % (M59479, Boltzmann) | 0.334 |
| Solar panels | 18,777 | 186 | 16.8 % (M59734, Schrodinger) | 0.567 |
| Lunar base (NASA regions) | 2,419 | 48 | 27.7 % (M62515, Nobile Rim 2) | -0.159 |
| Lunar base (whole 75S-90S zone, for comparison) | 2,419 | 74 | 15.7 % | -0.011 |

None of the A0 top 10 stays in the A1 top 10 for any mission. Half of the ranked points share at most 10 twins (Rover), 6 (Solar panels) and 3 (Lunar base).

**What remains to be decided** (details in section 5):

1. **Weights**: `DEFAULT_WEIGHTS` (A1), the diluted "Use Weights" matrix (A2) or the undiluted mapping (A3a). On the real data A1 and A3a give nearly the same Rover ranking (Spearman 1.000), but A2/A3 move Solar panels and Lunar base to temperature-dominated similarities (47-75 % temperature).
2. **The rock variable on the real data**: removed from the similarity as decided (it is 1 in every lunar cell); this document confirms the reason in code and numbers (section 2.2). Please confirm the removal is final.
3. **Twin versus zone mean**: recommend the **twin** (section 2.3), with the twin-sharing figures shown to users.
4. Two issues found during the work that need a decision: Antarctic Earth cells with no temperature get z = 0 (the Earth median, 284 K) in the repository's normalisation (1,156 Rover and 6,060 Solar panels points); and the twin concentrates on a few lunar cells at the edge of the zone's range.

### 1.1 Naming and dates (verified on nasa.gov, 2026-11-14)

- NASA news release 24-136, **Oct 28, 2024**, "NASA Provides Update on Artemis III Moon Landing Regions" (https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/): "The refined candidate Artemis III lunar landing regions are, in no priority order: Peak near Cabeus B, Haworth, Malapert Massif, Mons Mouton Plateau, Mons Mouton, Nobile Rim 1, Nobile Rim 2, de Gerlache Rim 2, Slater Plain".
- NASA news release 26-022, **Feb 27, 2026**, "NASA Adds Mission to Artemis Lunar Program, Updates Architecture" (https://www.nasa.gov/news-release/nasa-adds-mission-to-artemis-lunar-program-updates-architecture/): "the Artemis III mission, now in 2027, will be designed to test out systems and operational capabilities in low Earth orbit to prepare for an Artemis IV landing in 2028."
- Artemis III mission page (https://www.nasa.gov/mission/artemis-iii/, page metadata modified 2026-10-19): "Artemis III will carry out a series of objectives in low Earth orbit designed to demonstrate critical systems needed for future lunar landings, beginning with Artemis IV." Mission type "Crewed Demonstration", launch 2027.
- Artemis IV mission page (https://www.nasa.gov/mission/artemis-iv/, modified 2026-03-16): "Mission Type Crewed Surface Landing LAUNCH Early 2028"; astronauts "spend approximately a week near the South Pole of the Moon". Its "Lunar Site Selection" panel still says "the agency has identified nine candidate landing regions near the lunar South Pole" and links to the October 2024 release.
- NASA blog, **October 23, 2026** (https://www.nasa.gov/blogs/missions/2026/10/23/nasa-shares-artemis-acceleration-plans-for-moon-missions/): Artemis III "will send four astronauts to low Earth orbit in 2027 to test critical systems needed for future lunar landings"; "Artemis IV, the first Artemis mission on the lunar surface".
- **New regions for Artemis IV: none found.** No NASA release lists candidate regions for Artemis IV; the Artemis IV page reuses the nine regions of October 2024. The team lead's description (Artemis III became an Earth-orbit test flight in 2027 on 2026-02-27; first landing Artemis IV in 2028 at the south pole) is **confirmed**; NASA's current wording is "early 2028".

**Wording for the web app (Lunar base zone):** "Lunar twin searched inside the nine candidate landing regions near the lunar south pole that NASA announced on 28 October 2024 for the first crewed landing of Artemis (named Artemis III at the time; since 27 February 2026 NASA plans that landing as Artemis IV, early 2028, and Artemis III as a 2027 test flight in Earth orbit). Region footprints: USGS navigational grids (McClernan 2024, doi:10.5066/P1MEQ6UK, CC0), drawn on 1-degree cells."

## 2. The rule as computed, and the checks behind it

### 2.1 Code it reproduces (quoted lines)

Read at git ref `main` (`git show main:"tierra luna/analog_finder.py"`, commit d4a11e4) and in the team's newer local copy (`scratchpad/stars/ziplocal/STARS-BESIDE-YOU-main/tierra luna/analog_finder.py`). `normalize_planetary_features`, `build_lunar_reference_zones`, `map_domain_weights_to_features` and `compute_analog_ranking` are identical in both (diff of main 143-250 against local 154-261 and of main 419-470 against local 432-483: no difference).

- `DEFAULT_WEIGHTS` (main 68-75, local 79-86): elevation_rel_m 0.15, slope_deg 0.25, roughness_m 0.20, temp_k 0.15, rock_or_bare_frac 0.15, sar_sigma0_db 0.10.
- Scale (main 162, local 173): `scale = iqr_scale if iqr_scale > 1e-6 else (std if std > 1e-6 else 1.0)`.
- Missing values (main 166, local 177): `z = np.where(np.isfinite(vals), (vals - med) / scale, 0.0)`, then `np.clip(z, -4.0, 4.0)`; the variable is marked `"valid": True` (main 178, local 189) whenever it has at least one finite value.
- Earth population (main 430, local 443): `land_filter = earth_df["elevation_m"] > 0.0`.
- Active variables (main 443, local 456): `if w.get(f, 0.0) > 0 and moon_stats[f]["valid"] and earth_stats[f]["valid"]`, weights renormalised over them.
- Similarity (main 456, local 469): `similarity_pct = 100.0 * np.exp(-0.45 * rms_dist)`.
- South-pole zone (main 189, local 200): `"South Pole PSR & Shackleton Rim (75°S–90°S)": lat <= -75.0`.
- Rover target, main 259: `"rover": rocky_target,` (the Tycho box, main 193: "Tycho & Southern Rocky Craters (35°S–55°S, 30°W–0°)"). Local copy 270-272: `# [AI-assisted] Plan decision 2: the lunar target is the Shackleton` / `# region (the only Moon Base site NASA has named), not Tycho.` / `"rover": polar_target,`. **The local copy is the team's latest decision and is used here.** (The branch's own checkpoint 49b4de2 now carries the same change at lines 259-261.)

The baseline A0 computed here reproduces the repository: on the legacy table its similarity differs from `compute_analog_ranking`'s `similarity_pct` by at most 0.0063 points (the rounding of z to 4 decimals and of the output to 2), checked by `scratchpad/stars/proposal/check_s0.py`.

### 2.2 Variables with no variation (both bodies, both datasets)

| dataset | body (population) | variable | n | missing (z set to 0) | median | IQR/1.349 | std | scale used | share of the most repeated value | distinct values |
|---|---|---|---|---|---|---|---|---|---|---|
| real 1 deg | Earth (land, elevation_m > 0: 25095 cells) | elevation_rel_m | 25,095 | 0 | -225.3 | 1007 | 1108 | 1007 | 0.0 % | 14,304 |
| real 1 deg | Earth (land, elevation_m > 0: 25095 cells) | slope_deg | 24,714 | 381 | 0.482 | 1.041 | 1.641 | 1.041 | 0.3 % | 4,981 |
| real 1 deg | Earth (land, elevation_m > 0: 25095 cells) | roughness_m | 25,009 | 86 | 18.14 | 42.28 | 60.1 | 42.28 | 0.1 % | 10,096 |
| real 1 deg | Earth (land, elevation_m > 0: 25095 cells) | temp_k | 18,517 | 6,578 | 284.3 | 21.49 | 16.4 | 21.49 | 0.1 % | 5,494 |
| real 1 deg | Earth (land, elevation_m > 0: 25095 cells) | rock_or_bare_frac | 25,095 | 0 | 0.001 | 0.09144 | 0.3024 | 0.09144 | 41.2 % | 4,972 |
| real 1 deg | Earth (land, elevation_m > 0: 25095 cells) | sar_sigma0_db | 0 | all | | | | invalid (no data) | | |
| real 1 deg | Moon (all 64800 cells) | elevation_rel_m | 64,800 | 0 | -527.9 | 1769 | 2131 | 1769 | 0.0 % | 42,617 |
| real 1 deg | Moon (all 64800 cells) | slope_deg | 64,800 | 0 | 4.91 | 3.248 | 3.048 | 3.248 | 0.0 % | 12,189 |
| real 1 deg | Moon (all 64800 cells) | roughness_m | 64,800 | 0 | 159.7 | 92.01 | 88.63 | 92.01 | 0.0 % | 28,309 |
| real 1 deg | Moon (all 64800 cells) | temp_k | 64,800 | 0 | 197.7 | 32.29 | 33.43 | 32.29 | 0.1 % | 12,333 |
| real 1 deg | Moon (all 64800 cells) | rock_or_bare_frac | 64,800 | 0 | 1 | 0 | 0 | 1 | 100.0 % | 1 |
| real 1 deg | Moon (all 64800 cells) | sar_sigma0_db | 0 | all | | | | invalid (no data) | | |
| legacy 2 deg | Earth (land, elevation_m > 0: 5927 cells) | elevation_rel_m | 5,927 | 0 | -506.2 | 1042 | 1095 | 1042 | 0.0 % | 5,848 |
| legacy 2 deg | Earth (land, elevation_m > 0: 5927 cells) | slope_deg | 5,927 | 0 | 2.546 | 3.538 | 4.549 | 3.538 | 0.1 % | 5,698 |
| legacy 2 deg | Earth (land, elevation_m > 0: 5927 cells) | roughness_m | 5,927 | 0 | 115.1 | 160.7 | 214.7 | 160.7 | 0.0 % | 5,917 |
| legacy 2 deg | Earth (land, elevation_m > 0: 5927 cells) | temp_k | 5,927 | 0 | 273.7 | 33.28 | 27.03 | 33.28 | 0.1 % | 4,379 |
| legacy 2 deg | Earth (land, elevation_m > 0: 5927 cells) | rock_or_bare_frac | 5,927 | 0 | 0.4017 | 0.4804 | 0.3003 | 0.4804 | 0.2 % | 3,517 |
| legacy 2 deg | Earth (land, elevation_m > 0: 5927 cells) | sar_sigma0_db | 5,927 | 0 | -12.6 | 3.416 | 3.17 | 3.416 | 0.1 % | 5,751 |
| legacy 2 deg | Moon (all 16200 cells) | elevation_rel_m | 16,200 | 0 | -246.7 | 1663 | 2064 | 1663 | 0.0 % | 16,047 |
| legacy 2 deg | Moon (all 16200 cells) | slope_deg | 16,200 | 0 | 8.467 | 3.357 | 3.488 | 3.357 | 0.0 % | 15,116 |
| legacy 2 deg | Moon (all 16200 cells) | roughness_m | 16,200 | 0 | 576.8 | 424.3 | 425.9 | 424.3 | 0.0 % | 16,187 |
| legacy 2 deg | Moon (all 16200 cells) | temp_k | 16,200 | 0 | 92.14 | 8.761 | 11.18 | 8.761 | 0.0 % | 15,349 |
| legacy 2 deg | Moon (all 16200 cells) | rock_or_bare_frac | 16,200 | 0 | 0.004 | 0.002298 | 0.002603 | 0.002298 | 3.9 % | 176 |
| legacy 2 deg | Moon (all 16200 cells) | sar_sigma0_db | 16,200 | 0 | -17.14 | 0.7586 | 0.7954 | 0.7586 | 0.0 % | 12,266 |

Findings:

- **Lunar `rock_or_bare_frac` on the real table is 1 in all 64,800 cells**: IQR 0 and standard deviation 0, so the code falls through to `scale = 1.0` and every lunar cell gets z = (1 - 1)/1 = 0, while the variable stays `valid` and keeps its weight (16.7 % in A0 after radar drops out). The similarity then rewards Earth cells that sit at the **Earth median bare fraction (0.001, i.e. vegetated)**. Numerically, among the 10,337 Rover-ranked cells, the median A0 similarity is 74.6 for bare fraction < 0.01 (5,332 cells), 61.5 for 0.01-0.1 (1,766), 41.3 for 0.1-0.5 (1,793) and 43.5 for >= 0.5 (1,446): the baseline prefers vegetated ground, the opposite of the intent. 18.1 % of the Rover-ranked cells are clipped at z = +4. The team lead's description is **confirmed** in code and data; the variable is **removed** from A1-A3 on the real data and shown as an informative value. The Diviner rock abundance (`rock_abundance_frac`, fraction of the surface covered by blocks of about 1 m or more, Bandfield et al. 2011, PDS `DGDR_RA_AVG_CYL_032`, 60S-60N) is not substituted; it is listed among the lunar informative values, and it has no data in either target zone (all twins lie south of 75S).
- **Earth `rock_or_bare_frac` (real)**: 41.2 % of Earth land cells repeat one value (the median is 0.001); it varies, but half of the land is pinned at zero.
- **Radar (`sar_sigma0_db`)**: absent on both bodies of the real data (`valid` False), removed by the code itself; weight renormalised away. On the legacy table it exists but the lunar column is synthetic (AUDIT.md, fault 4).
- **Earth `temp_k` (real)**: 6,578 of 25,095 land cells have no value (6,558 of them at or south of 60S, where the MODIS climatology is empty, and 20 in the high Arctic). The code sets their z to 0, the Earth median (284.3 K). This touches 1,156 Rover and 6,060 Solar-panels ranked points (none for Lunar base, whose gates need the diurnal amplitude, also empty there). Those Antarctic points are compared with the Moon as if they were temperate. This is a decision item.
- **Legacy lunar `rock_or_bare_frac`** varies only between 0.002 and 0.046 (176 distinct values); its z-scores are large relative to its physical meaning.
- **Sun variables (A3b only)**: on the Moon `sun_elev_max_deg` and `sun_low_frac_0_5deg` are flat-horizon formulas of latitude (89 and 84 distinct values); on Earth 68 and 89. Inside a polar zone they carry latitude only.
- Inside the target zones (real data) the four similarity variables all vary (south-pole zone IQR: relative elevation 2,400 m, slope 4.5 deg, roughness 123 m, temperature 33.5 K; NASA-region cells: 2,540 m, 5.9 deg, 150 m, 33.2 K).

### 2.3 Twin or zone mean

The old optimality code compares every Earth cell with the **mean z-profile** of a zone (`build_lunar_reference_zones`, local 223 / main 212: `prof[f"{feat}_z"] = round(float(sub[f"{feat}_z"].mean()), 4)`). That variant (A1mean) was computed beside the twin:

| mission (real data) | similarity, twin (min / median / max) | similarity, zone mean | Spearman of final, twin vs mean | top-10 overlap | top-50 overlap |
|---|---|---|---|---|---|
| Rover | 62.3 / 79.1 / 99.3 | 21.8 / 54.8 / 84.5 | 0.798 | 4/10 | 27/50 |
| Solar panels | 61.9 / 76.8 / 99.3 | 21.8 / 52.4 / 83.3 | 0.864 | 0/10 | 10/50 |
| Lunar base | 55.9 / 67.5 / 94.3 | 30.1 / 49.3 / 70.4 | 0.760 | 0/10 | 12/50 |

**Recommendation: the twin.** The zone mean is a profile that no place on the Moon has (it averages crater floors and massifs), so it cannot be shown as "the lunar place this resembles", which is the product's promise; the twin is a real cell with a name and coordinates. The cost is visible in the tables: the twin similarity is compressed upwards (no point falls below 56) because every Earth point finds some close cell among hundreds, and twins concentrate on a few lunar cells at the edge of the zone's range (an Earth point warmer than any polar cell maps to the warmest polar cell). The rankings agree moderately (Spearman 0.76-0.86) but the top 10 change almost completely, so the choice matters for what users see first.

## 3. Results per mission

Each block gives, on the **real 1-degree data**: the A0 baseline top 10; the A1 top 10 with twins; the absolute values of both points; the informative values (not part of the similarity); the variants A2, A3a and A3b (and for Lunar base A1 on the whole south-pole zone); the twin-sharing table; the change against the baseline. The **legacy 2-degree** version follows for comparison (A1 top 10, twin sharing, change). Variant definitions: A0 = similarity to the global lunar mean with `DEFAULT_WEIGHTS` (the repository today); A1 = approved rule; A2 = A1 with `map_domain_weights_to_features` of the mission's domain weights (the web page's "Use Weights"), renormalised over the variables present; A3a = undiluted mapping, each domain's weight spent only on its own variables (relieve: slope, roughness, relative elevation; material: bare fraction and radar; termico: temperature; split inside a domain in proportion to `DEFAULT_WEIGHTS`), "luz" and "agua" dropped and the rest renormalised; A3b = A3a plus "luz" spent equally on irradiance, maximum sun elevation and low-sun fraction. "agua" cannot be added in A3b: its only variable, `permafrost_class`, is categorical (the z-score machinery reads it as missing) and is `ninguno` in every lunar cell of the real table, so its weight is dropped in A3b too. Earth places follow `engine/places.py` (Natural Earth country polygon, GeoNames first-level region within one cell, Antarctica south of 60S). Lunar names: nearest non-satellite IAU feature (`engine/data/iau_moon_nomenclature.csv`, USGS/IAU Gazetteer of Planetary Nomenclature); for Lunar base the NASA region(s) the twin cell touches are in brackets.

### 3.1 Rover

**Reading.** A1 puts the Canadian Arctic Archipelago at the top (all ten cells between 70.5N and 78.5N, suitability 99.6-100) with south-polar twins: gentle terrain slightly above the Earth median and among the coldest on Earth, paired with lunar cells slightly above the lunar median and among the coldest on the Moon. Haughton crater (Devon Island), a real lunar-analog site, rises from rank 4,224 (A0) to 80. The A0 top 10 (prairies of Canada, Montana and Kazakhstan, bare fraction 0.001-0.008) is driven by the bare-fraction artefact of section 2.2. A2 and A3a barely change the Rover ranking (Spearman 0.997 and 1.000 with A1); A3b (adds sun variables) changes the top 10 (3/10 kept) because sun geometry pulls towards the latitude of the polar zone.

Ranked Earth points (pass every gate): **10,337**. Target zone: south_pole (5400 lunar cells).


#### A0 baseline (global mean): top 10

| # | Earth cell | lat, lon | country / region | suitability | similarity | final |
|---|---|---|---|---|---|---|
| 1 | E12303 | 55.5N 116.5W | Canada / Alberta | 75.0 | 98.3 | 86.6 |
| 2 | E14294 | 50.5N 74.5E | Kazakhstan / Qaraghandy | 75.0 | 97.8 | 86.4 |
| 3 | E12306 | 55.5N 113.5W | Canada / Alberta | 75.0 | 97.7 | 86.4 |
| 4 | E11945 | 56.5N 114.5W | Canada | 75.0 | 97.6 | 86.3 |
| 5 | E14654 | 49.5N 74.5E | Kazakhstan / Qaraghandy | 75.0 | 97.2 | 86.1 |
| 6 | E14653 | 49.5N 73.5E | Kazakhstan / Qaraghandy | 75.1 | 97.1 | 86.1 |
| 7 | E14112 | 50.5N 107.5W | Canada / Saskatchewan | 75.2 | 96.8 | 86.0 |
| 8 | E14835 | 48.5N 104.5W | United States / Montana | 75.0 | 96.7 | 85.9 |
| 9 | E14474 | 49.5N 105.5W | Canada / Saskatchewan | 75.3 | 96.3 | 85.8 |
| 10 | E13759 | 51.5N 100.5W | Canada / Manitoba | 75.0 | 96.6 | 85.8 |

#### A1 approved rule: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E5128 | 75.5N 91.5W | Canada | 99.8 | 98.4 | 99.1 | M60952 | 79.5S 67.5W | [Drygalski](http://planetarynames.wr.usgs.gov/Feature/1645) (107.9) |
| 2 | E6903 | 70.5N 116.5W | Canada | 100.0 | 98.1 | 99.0 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 3 | E5485 | 74.5N 94.5W | Canada | 99.8 | 97.9 | 98.9 | M60536 | 78.5S 123.5W | [Ashbrook](http://planetarynames.wr.usgs.gov/Feature/422) (104.7) |
| 4 | E6904 | 70.5N 115.5W | Canada | 100.0 | 97.6 | 98.8 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 5 | E5845 | 73.5N 94.5W | Canada | 99.8 | 97.7 | 98.8 | M59507 | 75.5S 72.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (46.4) |
| 6 | E4036 | 78.5N 103.5W | Canada | 100.0 | 97.5 | 98.8 | M59545 | 75.5S 34.5W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (90.5) |
| 7 | E5129 | 75.5N 90.5W | Canada | 99.8 | 97.7 | 98.7 | M60536 | 78.5S 123.5W | [Ashbrook](http://planetarynames.wr.usgs.gov/Feature/422) (104.7) |
| 8 | E5118 | 75.5N 101.5W | Canada | 99.6 | 97.9 | 98.7 | M61164 | 79.5S 144.5E | [Nefed ev](http://planetarynames.wr.usgs.gov/Feature/14538) (65.2) |
| 9 | E4037 | 78.5N 102.5W | Canada | 100.0 | 97.3 | 98.6 | M59545 | 75.5S 34.5W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (90.5) |
| 10 | E6538 | 71.5N 121.5W | Canada | 100.0 | 97.3 | 98.6 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |

Absolute values, A1 top 10 (Earth / lunar twin). Variables in the similarity: elevation_rel_m, slope_deg, roughness_m, temp_k.

| # | elev_rel m | slope deg | rough m | temp K | bare frac | radar dB |
|---|---|---|---|---|---|---|
| 1 | -513 / -1,091 | 0.9 / 6.2 | 35 / 199 | 253.5 / 149.5 | 0.998 / 1.000 * | no data / no data * |
| 2 | -424 / -857 | 1.0 / 6.3 | 30 / 180 | 259.1 / 158.2 | 0.824 / 1.000 * | no data / no data * |
| 3 | -528 / -1,064 | 0.8 / 5.9 | 34 / 194 | 254.1 / 149.4 | 1.000 / 1.000 * | no data / no data * |
| 4 | -441 / -857 | 0.8 / 6.3 | 27 / 180 | 258.8 / 158.2 | 0.897 / 1.000 * | no data / no data * |
| 5 | -419 / -724 | 0.9 / 6.3 | 33 / 188 | 254.2 / 150.6 | 0.716 / 1.000 * | no data / no data * |
| 6 | -635 / -1,241 | 0.8 / 5.9 | 31 / 186 | 253.2 / 147.1 | 0.910 / 1.000 * | no data / no data * |
| 7 | -428 / -1,064 | 0.8 / 5.9 | 35 / 194 | 253.0 / 149.4 | 1.000 / 1.000 * | no data / no data * |
| 8 | -588 / -1,168 | 1.0 / 6.7 | 37 / 204 | 254.3 / 150.2 | 0.716 / 1.000 * | no data / no data * |
| 9 | -604 / -1,241 | 0.8 / 5.9 | 29 / 186 | 253.4 / 147.1 | 0.868 / 1.000 * | no data / no data * |
| 10 | -498 / -857 | 1.0 / 6.3 | 31 / 180 | 258.4 / 158.2 | 0.760 / 1.000 * | no data / no data * |

\* not part of the similarity on this dataset.

Not part of the similarity (informative only), A1 top 10 (Earth / lunar twin):

| # | irradiance kWh/m2/day | diurnal amplitude K | minimum temp C | surface class | permafrost | lunar rock abundance (Diviner) |
|---|---|---|---|---|---|---|
| 1 | 2.40 / 1.49 | 2.7 / 213.2 | -38.4 / -206.6 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 2 | 2.42 / 2.05 | 3.6 / 203.9 | -33.0 / -200.3 | agua / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 3 | 2.37 / 1.66 | 2.4 / 201.1 | -37.5 / -208.3 | agua / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 4 | 2.43 / 2.05 | 3.6 / 203.9 | -34.0 / -200.3 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 5 | 2.40 / 2.00 | 2.7 / 208.5 | -38.2 / -200.4 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 6 | 2.17 / 1.90 | 1.6 / 200.2 | -40.0 / -203.3 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 7 | 2.41 / 1.66 | 2.5 / 201.1 | -38.5 / -208.3 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 8 | 2.27 / 1.44 | 2.2 / 204.3 | -38.7 / -207.2 | agua / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 9 | 2.19 / 1.90 | 1.7 / 200.2 | -40.2 / -203.3 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 10 | 2.35 / 2.05 | 3.3 / 203.9 | -32.7 / -200.3 | agua / regolito | continuo / ninguno | no data (product covers 60S-60N) |

#### A2 Use Weights (diluted matrix): top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E5128 | 75.5N 91.5W | Canada | 99.8 | 98.3 | 99.0 | M60952 | 79.5S 67.5W | [Drygalski](http://planetarynames.wr.usgs.gov/Feature/1645) (107.9) |
| 2 | E6903 | 70.5N 116.5W | Canada | 100.0 | 98.0 | 99.0 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 3 | E6904 | 70.5N 115.5W | Canada | 100.0 | 97.8 | 98.9 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 4 | E5485 | 74.5N 94.5W | Canada | 99.8 | 97.7 | 98.8 | M60536 | 78.5S 123.5W | [Ashbrook](http://planetarynames.wr.usgs.gov/Feature/422) (104.7) |
| 5 | E5129 | 75.5N 90.5W | Canada | 99.8 | 97.7 | 98.7 | M60536 | 78.5S 123.5W | [Ashbrook](http://planetarynames.wr.usgs.gov/Feature/422) (104.7) |
| 6 | E5845 | 73.5N 94.5W | Canada | 99.8 | 97.6 | 98.7 | M59507 | 75.5S 72.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (46.4) |
| 7 | E5118 | 75.5N 101.5W | Canada | 99.6 | 97.7 | 98.7 | M61164 | 79.5S 144.5E | [Nefed ev](http://planetarynames.wr.usgs.gov/Feature/14538) (65.2) |
| 8 | E5486 | 74.5N 93.5W | Canada | 99.3 | 98.0 | 98.6 | M61165 | 79.5S 145.5E | [Nefed ev](http://planetarynames.wr.usgs.gov/Feature/14538) (68.8) |
| 9 | E6538 | 71.5N 121.5W | Canada | 100.0 | 97.3 | 98.6 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 10 | E5110 | 75.5N 109.5W | Canada | 100.0 | 97.1 | 98.6 | M59907 | 76.5S 32.5W | [Newton](http://planetarynames.wr.usgs.gov/Feature/4235) (106.2) |

#### A3a undiluted, luz/agua dropped: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E5128 | 75.5N 91.5W | Canada | 99.8 | 98.4 | 99.1 | M60952 | 79.5S 67.5W | [Drygalski](http://planetarynames.wr.usgs.gov/Feature/1645) (107.9) |
| 2 | E6903 | 70.5N 116.5W | Canada | 100.0 | 98.0 | 99.0 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 3 | E5485 | 74.5N 94.5W | Canada | 99.8 | 97.8 | 98.8 | M60536 | 78.5S 123.5W | [Ashbrook](http://planetarynames.wr.usgs.gov/Feature/422) (104.7) |
| 4 | E6904 | 70.5N 115.5W | Canada | 100.0 | 97.6 | 98.8 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 5 | E5845 | 73.5N 94.5W | Canada | 99.8 | 97.7 | 98.8 | M59507 | 75.5S 72.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (46.4) |
| 6 | E5129 | 75.5N 90.5W | Canada | 99.8 | 97.7 | 98.8 | M60536 | 78.5S 123.5W | [Ashbrook](http://planetarynames.wr.usgs.gov/Feature/422) (104.7) |
| 7 | E5118 | 75.5N 101.5W | Canada | 99.6 | 97.8 | 98.7 | M61164 | 79.5S 144.5E | [Nefed ev](http://planetarynames.wr.usgs.gov/Feature/14538) (65.2) |
| 8 | E4036 | 78.5N 103.5W | Canada | 100.0 | 97.4 | 98.7 | M59545 | 75.5S 34.5W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (90.5) |
| 9 | E6538 | 71.5N 121.5W | Canada | 100.0 | 97.3 | 98.6 | M60093 | 76.5S 153.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (163.0) |
| 10 | E4037 | 78.5N 102.5W | Canada | 100.0 | 97.1 | 98.6 | M59545 | 75.5S 34.5W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (90.5) |

#### A3b undiluted, luz variables added: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E6923 | 70.5N 96.5W | Canada | 100.0 | 87.6 | 93.8 | M59504 | 75.5S 75.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (37.4) |
| 2 | E6903 | 70.5N 116.5W | Canada | 100.0 | 87.5 | 93.7 | M59507 | 75.5S 72.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (46.4) |
| 3 | E6907 | 70.5N 112.5W | Canada | 100.0 | 87.4 | 93.7 | M59735 | 75.5S 155.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (176.3) |
| 4 | E7259 | 69.5N 120.5W | Canada | 99.3 | 88.0 | 93.7 | M59500 | 75.5S 79.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (46.2) |
| 5 | E6904 | 70.5N 115.5W | Canada | 100.0 | 87.2 | 93.6 | M59507 | 75.5S 72.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (46.4) |
| 6 | E6905 | 70.5N 114.5W | Canada | 100.0 | 87.0 | 93.5 | M59507 | 75.5S 72.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (46.4) |
| 7 | E6906 | 70.5N 113.5W | Canada | 100.0 | 86.9 | 93.5 | M59504 | 75.5S 75.5W | [Le Gentil](http://planetarynames.wr.usgs.gov/Feature/3311) (37.4) |
| 8 | E7263 | 69.5N 116.5W | Canada | 100.0 | 86.9 | 93.4 | M59736 | 75.5S 156.5E | [Schrodinger](http://planetarynames.wr.usgs.gov/Feature/5381) (183.8) |
| 9 | E6549 | 71.5N 110.5W | Canada | 100.0 | 86.8 | 93.4 | M59484 | 75.5S 95.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (44.5) |
| 10 | E6538 | 71.5N 121.5W | Canada | 100.0 | 86.3 | 93.1 | M59574 | 75.5S 5.5W | [Short](http://planetarynames.wr.usgs.gov/Feature/5499) (33.8) |

#### Twin sharing (Rover)

| variant | distinct twins | largest share | top 3 twins | top 10 twins | twins covering half the points | most shared twins (cell, nearest feature, points, %) |
|---|---|---|---|---|---|---|
| A1 | 305 | 9.2 % | 24.1 % | 52.4 % | 10 | M59479 Boltzmann 954 (9.2 %); M60093 Schrodinger 901 (8.7 %); M59634 Demonax 641 (6.2 %) |
| A2 | 289 | 13.3 % | 27.1 % | 59.6 % | 8 | M59479 Boltzmann 1,370 (13.3 %); M59634 Demonax 717 (6.9 %); M59635 Demonax 714 (6.9 %) |
| A3a | 301 | 10.3 % | 24.7 % | 54.1 % | 9 | M59479 Boltzmann 1,063 (10.3 %); M60093 Schrodinger 832 (8.0 %); M59634 Demonax 654 (6.3 %) |
| A3b | 136 | 11.5 % | 28.2 % | 61.2 % | 8 | M59479 Boltzmann 1,186 (11.5 %); M59634 Demonax 967 (9.4 %); M59478 Boltzmann 762 (7.4 %) |

#### Change against the baseline and similarity distribution (Rover)

| variant | Spearman final vs A0 | Spearman similarity vs A0 | top-10 overlap | top-50 overlap | similarity min / median / max | Spearman(similarity, suitability) |
|---|---|---|---|---|---|---|
| A0 | 1 | 1 | 10/10 | 50/50 | 19.6 / 58.1 / 98.3 | 0.320 |
| A1 | 0.334 | -0.085 | 0/10 | 0/50 | 62.3 / 79.1 / 99.3 | 0.071 |
| A1mean | 0.717 | 0.699 | 0/10 | 0/50 | 21.8 / 54.8 / 84.5 | 0.553 |
| A2 | 0.297 | -0.109 | 0/10 | 0/50 | 58.4 / 76.9 / 99.2 | 0.058 |
| A3a | 0.320 | -0.096 | 0/10 | 0/50 | 60.8 / 78.4 / 99.2 | 0.065 |
| A3b | 0.372 | 0.037 | 0/10 | 0/50 | 50.0 / 67.3 / 88.9 | 0.109 |

Largest rises from A0 to A1 (rank A0 -> A1): E7476 69.5N 96.5E Russia 8,050 -> 504; E4052 78.5N 87.5W Canada 7,938 -> 537; E7352 69.5N 27.5W Greenland 8,016 -> 649

Largest falls from A0 to A1: E29002 9.5N 22.5E Central African Rep. / Vakaga 1,879 -> 8,613; E26896 15.5N 76.5E India / Karnataka 2,129 -> 8,816; E25454 19.5N 74.5E India / Maharashtra 2,039 -> 8,705

A1 against its variants: A1mean: Spearman 0.798, top-10 4/10, top-50 27/50; A2: Spearman 0.997, top-10 8/10, top-50 48/50, same twin for 80 % of points; A3a: Spearman 1.000, top-10 10/10, top-50 49/50, same twin for 94 % of points; A3b: Spearman 0.950, top-10 3/10, top-50 16/50, same twin for 57 % of points

#### Legacy 2-degree data (Rover), for comparison

Ranked Earth points (pass every gate): **5,297**. Target zone: south_pole (1440 lunar cells).

##### A1 approved rule: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E15462 | 81.0S 145.0E | Antarctica | 99.6 | 92.6 | 96.1 | M15223 | 79.0S 27.0E | [Schomberger](http://planetarynames.wr.usgs.gov/Feature/5378) (73.1) |
| 2 | E15461 | 81.0S 143.0E | Antarctica | 100.0 | 92.0 | 96.0 | M15223 | 79.0S 27.0E | [Schomberger](http://planetarynames.wr.usgs.gov/Feature/5378) (73.1) |
| 3 | E15458 | 81.0S 137.0E | Antarctica | 100.0 | 91.3 | 95.7 | M15223 | 79.0S 27.0E | [Schomberger](http://planetarynames.wr.usgs.gov/Feature/5378) (73.1) |
| 4 | E15492 | 83.0S 155.0W | Antarctica | 100.0 | 91.2 | 95.6 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 5 | E16131 | 89.0S 43.0E | Antarctica | 99.3 | 91.9 | 95.6 | M15010 | 77.0S 39.0W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (145.7) |
| 6 | E15945 | 87.0S 31.0E | Antarctica | 99.0 | 92.1 | 95.5 | M15010 | 77.0S 39.0W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (145.7) |
| 7 | E16048 | 89.0S 123.0W | Antarctica | 99.3 | 91.8 | 95.5 | M15010 | 77.0S 39.0W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (145.7) |
| 8 | E16047 | 89.0S 125.0W | Antarctica | 99.2 | 91.8 | 95.5 | M15010 | 77.0S 39.0W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (145.7) |
| 9 | E15944 | 87.0S 29.0E | Antarctica | 99.6 | 91.4 | 95.5 | M15010 | 77.0S 39.0W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (145.7) |
| 10 | E15452 | 81.0S 125.0E | Antarctica | 99.4 | 91.6 | 95.5 | M15010 | 77.0S 39.0W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (145.7) |

Absolute values, A1 top 10 (Earth / lunar twin). Variables in the similarity: elevation_rel_m, slope_deg, roughness_m, temp_k, rock_or_bare_frac, sar_sigma0_db.

| # | elev_rel m | slope deg | rough m | temp K | bare frac | radar dB |
|---|---|---|---|---|---|---|
| 1 | 1,120 / 2,353 | 0.9 / 7.4 | 39 / 371 | 230.0 / 78.5 | 0.727 / 0.006 | -12.2 / -17.3 |
| 2 | 1,189 / 2,353 | 0.6 / 7.4 | 25 / 371 | 228.7 / 78.5 | 0.726 / 0.006 | -12.4 / -17.3 |
| 3 | 1,385 / 2,353 | 0.6 / 7.4 | 26 / 371 | 227.2 / 78.5 | 0.736 / 0.006 | -12.3 / -17.3 |
| 4 | -997 / -1,375 | 0.7 / 7.1 | 30 / 335 | 243.3 / 81.4 | 0.725 / 0.006 | -12.4 / -17.4 |
| 5 | 1,816 / 3,340 | 1.0 / 8.0 | 45 / 354 | 228.4 / 80.1 | 0.761 / 0.006 | -11.9 / -17.2 |
| 6 | 1,781 / 3,340 | 1.1 / 8.0 | 47 / 354 | 228.8 / 80.1 | 0.760 / 0.006 | -11.9 / -17.2 |
| 7 | 1,768 / 3,340 | 1.0 / 8.0 | 44 / 354 | 231.3 / 80.1 | 0.759 / 0.006 | -11.9 / -17.2 |
| 8 | 1,773 / 3,340 | 1.0 / 8.0 | 46 / 354 | 231.3 / 80.1 | 0.759 / 0.006 | -11.9 / -17.2 |
| 9 | 1,753 / 3,340 | 0.8 / 8.0 | 37 / 354 | 228.7 / 80.1 | 0.757 / 0.006 | -12.0 / -17.2 |
| 10 | 1,785 / 3,340 | 0.9 / 8.0 | 43 / 354 | 225.1 / 80.1 | 0.759 / 0.006 | -11.9 / -17.2 |

\* not part of the similarity on this dataset.


##### Twin sharing (Rover)

| variant | distinct twins | largest share | top 3 twins | top 10 twins | twins covering half the points | most shared twins (cell, nearest feature, points, %) |
|---|---|---|---|---|---|---|
| A1 | 82 | 12.4 % | 32.3 % | 64.0 % | 7 | M14928 Schrodinger 655 (12.4 %); M14890 Hale 574 (10.8 %); M15010 Casatus 482 (9.1 %) |
| A2 | 77 | 10.8 % | 30.0 % | 63.5 % | 7 | M15010 Casatus 573 (10.8 %); M14928 Schrodinger 544 (10.3 %); M14891 Hale 471 (8.9 %) |
| A3a | 77 | 12.8 % | 34.3 % | 71.1 % | 5 | M14792 Zeeman 679 (12.8 %); M15010 Casatus 617 (11.6 %); M14890 Hale 523 (9.9 %) |
| A3b | 66 | 13.6 % | 36.6 % | 73.1 % | 5 | M14792 Zeeman 721 (13.6 %); M15010 Casatus 654 (12.3 %); M14928 Schrodinger 564 (10.6 %) |

##### Change against the baseline and similarity distribution (Rover)

| variant | Spearman final vs A0 | Spearman similarity vs A0 | top-10 overlap | top-50 overlap | similarity min / median / max | Spearman(similarity, suitability) |
|---|---|---|---|---|---|---|
| A0 | 1 | 1 | 10/10 | 50/50 | 32.4 / 70.2 / 94.0 | 0.298 |
| A1 | 0.916 | 0.347 | 0/10 | 0/50 | 41.8 / 67.9 / 92.6 | 0.781 |
| A1mean | 0.931 | 0.465 | 2/10 | 36/50 | 29.1 / 48.6 / 67.5 | 0.416 |
| A2 | 0.914 | 0.339 | 0/10 | 0/50 | 40.2 / 66.0 / 92.5 | 0.762 |
| A3a | 0.919 | 0.358 | 0/10 | 0/50 | 39.8 / 67.0 / 92.1 | 0.835 |
| A3b | 0.910 | 0.321 | 0/10 | 0/50 | 39.6 / 64.8 / 92.5 | 0.722 |

Largest rises from A0 to A1 (rank A0 -> A1): E15244 79.0S 69.0E Antarctica 3,652 -> 1,319; E15250 79.0S 81.0E Antarctica 3,795 -> 1,484; E15245 79.0S 71.0E Antarctica 3,767 -> 1,459

Largest falls from A0 to A1: E4284 43.0N 109.0E Mongolia / East Gobi Aymag 334 -> 1,816; E14952 77.0S 155.0W Antarctica 233 -> 1,714; E4104 45.0N 109.0E Mongolia / East Gobi Aymag 283 -> 1,739

A1 against its variants: A1mean: Spearman 0.987, top-10 1/10, top-50 1/50; A2: Spearman 1.000, top-10 4/10, top-50 36/50, same twin for 45 % of points; A3a: Spearman 0.999, top-10 5/10, top-50 37/50, same twin for 31 % of points; A3b: Spearman 0.998, top-10 3/10, top-50 23/50, same twin for 31 % of points

### 3.2 Solar panels

**Reading.** The south-pole zone is the coldest part of the Moon, but solar suitability favours sunny, warm places, so in A1 the similarity and the suitability pull against each other (Spearman -0.68 between them). The top 10 are high-suitability cells in southern Africa, Madagascar, India and Nicaragua whose twins are the warmest polar cells (Boltzmann, Demonax, Casatus): their temperatures differ by about 120-135 K and the pairing rests on relief alone. Twins concentrate: 6 lunar cells take half of the 18,777 points. The A2/A3 variants raise temperature to 47-57 % of the weight and change the top 10 completely. This mission's pairs are the least defensible of the three (section 4.3).

Ranked Earth points (pass every gate): **18,777**. Target zone: south_pole (5400 lunar cells).


#### A0 baseline (global mean): top 10

| # | Earth cell | lat, lon | country / region | suitability | similarity | final |
|---|---|---|---|---|---|---|
| 1 | E30079 | 6.5N 19.5E | Central African Rep. / Nana-Grebizi | 92.9 | 83.5 | 88.2 |
| 2 | E30078 | 6.5N 18.5E | Central African Rep. / Ouham | 93.2 | 83.2 | 88.2 |
| 3 | E38385 | 16.5S 45.5E | Madagascar / Melaky | 96.5 | 79.9 | 88.2 |
| 4 | E39563 | 19.5S 143.5E | Australia | 94.9 | 81.4 | 88.1 |
| 5 | E30077 | 6.5N 17.5E | Central African Rep. / Ouham | 93.3 | 83.0 | 88.1 |
| 6 | E42681 | 28.5S 21.5E | South Africa / Northern Cape | 93.5 | 82.5 | 88.0 |
| 7 | E38106 | 15.5S 126.5E | Australia | 95.9 | 80.0 | 88.0 |
| 8 | E44216 | 32.5S 116.5E | Australia / Western Australia | 90.2 | 85.7 | 88.0 |
| 9 | E38744 | 17.5S 44.5E | Madagascar / Melaky | 96.8 | 79.1 | 87.9 |
| 10 | E30080 | 6.5N 20.5E | Central African Rep. / Ouaka | 92.5 | 83.4 | 87.9 |

#### A1 approved rule: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E44120 | 32.5S 20.5E | South Africa / Western Cape | 86.8 | 78.0 | 82.4 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 2 | E40517 | 22.5S 17.5E | Namibia / Khomas | 93.3 | 71.4 | 82.4 | M60006 | 76.5S 66.5E | [Demonax](http://planetarynames.wr.usgs.gov/Feature/1484) (67.6) |
| 3 | E37308 | 13.5S 48.5E | Madagascar / Diana | 92.1 | 72.7 | 82.4 | M59478 | 75.5S 101.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (88.4) |
| 4 | E27615 | 13.5N 75.5E | India / Karnataka | 90.9 | 73.6 | 82.3 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 5 | E42682 | 28.5S 22.5E | South Africa / Northern Cape | 93.0 | 71.4 | 82.2 | M59636 | 75.5S 56.5E | [Demonax](http://planetarynames.wr.usgs.gov/Feature/1484) (80.9) |
| 6 | E42323 | 27.5S 23.5E | South Africa / Northern Cape | 92.9 | 71.3 | 82.1 | M59539 | 75.5S 40.5W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (117.2) |
| 7 | E42683 | 28.5S 23.5E | South Africa / Northern Cape | 92.4 | 71.9 | 82.1 | M59539 | 75.5S 40.5W | [Casatus](http://planetarynames.wr.usgs.gov/Feature/1040) (117.2) |
| 8 | E27814 | 12.5N 85.5W | Nicaragua / Boaco | 91.2 | 73.1 | 82.1 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 9 | E41606 | 25.5S 26.5E | South Africa / North-West | 91.6 | 72.6 | 82.1 | M59636 | 75.5S 56.5E | [Demonax](http://planetarynames.wr.usgs.gov/Feature/1484) (80.9) |
| 10 | E43042 | 29.5S 22.5E | South Africa / Northern Cape | 93.0 | 71.2 | 82.1 | M59636 | 75.5S 56.5E | [Demonax](http://planetarynames.wr.usgs.gov/Feature/1484) (80.9) |

Absolute values, A1 top 10 (Earth / lunar twin). Variables in the similarity: elevation_rel_m, slope_deg, roughness_m, temp_k.

| # | elev_rel m | slope deg | rough m | temp K | bare frac | radar dB |
|---|---|---|---|---|---|---|
| 1 | 431 / 371 | 2.0 / 10.3 | 76 / 276 | 293.1 / 172.2 | 0.153 / 1.000 * | no data / no data * |
| 2 | 996 / 1,563 | 0.9 / 6.9 | 37 / 196 | 296.4 / 162.9 | 0.000 / 1.000 * | no data / no data * |
| 3 | -372 / -593 | 2.9 / 13.1 | 115 / 348 | 297.2 / 167.6 | 0.000 / 1.000 * | no data / no data * |
| 4 | 39 / 371 | 1.8 / 10.3 | 83 / 276 | 296.8 / 172.2 | 0.000 / 1.000 * | no data / no data * |
| 5 | 449 / 1,094 | 0.8 / 6.2 | 33 / 178 | 296.0 / 162.4 | 0.002 / 1.000 * | no data / no data * |
| 6 | 653 / 1,407 | 0.5 / 5.4 | 18 / 166 | 295.5 / 161.2 | 0.004 / 1.000 * | no data / no data * |
| 7 | 680 / 1,407 | 0.6 / 5.4 | 21 / 166 | 294.9 / 161.2 | 0.004 / 1.000 * | no data / no data * |
| 8 | -314 / 371 | 2.1 / 10.3 | 80 / 276 | 297.8 / 172.2 | 0.000 / 1.000 * | no data / no data * |
| 9 | 561 / 1,094 | 0.8 / 6.2 | 31 / 178 | 294.6 / 162.4 | 0.002 / 1.000 * | no data / no data * |
| 10 | 383 / 1,094 | 0.8 / 6.2 | 31 / 178 | 296.2 / 162.4 | 0.046 / 1.000 * | no data / no data * |

\* not part of the similarity on this dataset.

Not part of the similarity (informative only), A1 top 10 (Earth / lunar twin):

| # | irradiance kWh/m2/day | diurnal amplitude K | minimum temp C | surface class | permafrost | lunar rock abundance (Diviner) |
|---|---|---|---|---|---|---|
| 1 | 5.52 / 2.37 | 17.5 / 224.0 | 0.7 / -197.9 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 2 | 6.09 / 2.02 | 20.6 / 210.7 | 3.4 / -198.5 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 3 | 5.90 / 2.20 | 8.6 / 224.9 | 17.3 / -198.7 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 4 | 5.54 / 2.37 | 9.8 / 224.0 | 15.6 / -197.9 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 5 | 5.94 / 2.28 | 19.5 / 213.8 | 1.3 / -196.8 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 6 | 5.93 / 2.24 | 19.8 / 214.1 | 0.8 / -198.8 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 7 | 5.86 / 2.24 | 19.2 / 214.1 | -0.4 / -198.8 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 8 | 5.60 / 2.37 | 8.7 / 224.0 | 19.0 / -197.9 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 9 | 5.68 / 2.28 | 17.0 / 213.8 | 2.2 / -196.8 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 10 | 5.88 / 2.28 | 18.1 / 213.8 | 1.5 / -196.8 | suelo / regolito | no data / ninguno | no data (product covers 60S-60N) |

#### A2 Use Weights (diluted matrix): top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E15420 | 47.5N 120.5E | China / Inner Mongolia | 70.1 | 91.5 | 80.8 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 2 | E17537 | 41.5N 77.5E | Kyrgyzstan / Ysyk-Koel | 63.6 | 95.5 | 79.6 | M63218 | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 3 | E15061 | 48.5N 121.5E | China / Inner Mongolia | 69.6 | 89.3 | 79.5 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 4 | E13255 | 53.5N 115.5E | Russia / Transbaikal Territory | 62.4 | 96.5 | 79.4 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 5 | E13981 | 51.5N 121.5E | China / Inner Mongolia | 65.2 | 93.1 | 79.2 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 6 | E13980 | 51.5N 120.5E | China / Inner Mongolia | 65.6 | 92.7 | 79.2 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 7 | E12897 | 54.5N 117.5E | Russia | 60.9 | 97.4 | 79.2 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 8 | E12895 | 54.5N 115.5E | Russia | 61.1 | 97.1 | 79.1 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 9 | E13256 | 53.5N 116.5E | Russia / Transbaikal Territory | 62.2 | 95.9 | 79.0 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 10 | E13983 | 51.5N 123.5E | China / Heilongjiang Sheng | 64.7 | 93.4 | 79.0 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |

#### A3a undiluted, luz/agua dropped: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E15420 | 47.5N 120.5E | China / Inner Mongolia | 70.1 | 91.5 | 80.8 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 2 | E13980 | 51.5N 120.5E | China / Inner Mongolia | 65.6 | 93.2 | 79.4 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 3 | E17537 | 41.5N 77.5E | Kyrgyzstan / Ysyk-Koel | 63.6 | 95.2 | 79.4 | M63218 | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 4 | E13255 | 53.5N 115.5E | Russia / Transbaikal Territory | 62.4 | 96.3 | 79.4 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 5 | E12895 | 54.5N 115.5E | Russia | 61.1 | 97.3 | 79.2 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 6 | E15061 | 48.5N 121.5E | China / Inner Mongolia | 69.6 | 88.7 | 79.2 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 7 | E13981 | 51.5N 121.5E | China / Inner Mongolia | 65.2 | 93.0 | 79.1 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 8 | E12899 | 54.5N 119.5E | Russia / Transbaikal Territory | 60.9 | 97.1 | 79.0 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 9 | E13983 | 51.5N 123.5E | China / Heilongjiang Sheng | 64.7 | 93.2 | 79.0 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 10 | E12897 | 54.5N 117.5E | Russia | 60.9 | 96.9 | 78.9 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |

#### A3b undiluted, luz variables added: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E38744 | 17.5S 44.5E | Madagascar / Melaky | 96.8 | 36.5 | 66.6 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 2 | E38105 | 15.5S 125.5E | Australia | 96.9 | 36.3 | 66.6 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 3 | E39104 | 18.5S 44.5E | Madagascar / Melaky | 95.9 | 37.0 | 66.5 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 4 | E39464 | 19.5S 44.5E | Madagascar / Menabe | 95.9 | 37.0 | 66.4 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 5 | E38385 | 16.5S 45.5E | Madagascar / Melaky | 96.5 | 36.4 | 66.4 | M59416 | 75.5S 163.5W | [De Forest](http://planetarynames.wr.usgs.gov/Feature/1437) (43.5) |
| 6 | E37750 | 14.5S 130.5E | Australia | 96.4 | 36.3 | 66.4 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 7 | E38027 | 15.5S 47.5E | Madagascar / Sofia | 96.3 | 36.4 | 66.4 | M59416 | 75.5S 163.5W | [De Forest](http://planetarynames.wr.usgs.gov/Feature/1437) (43.5) |
| 8 | E38464 | 16.5S 124.5E | Australia | 96.9 | 35.8 | 66.4 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 9 | E37746 | 14.5S 126.5E | Australia | 96.6 | 35.9 | 66.2 | M59479 | 75.5S 100.5W | [Boltzmann](http://planetarynames.wr.usgs.gov/Feature/805) (80.9) |
| 10 | E37390 | 13.5S 130.5E | Australia | 96.1 | 36.4 | 66.2 | M59416 | 75.5S 163.5W | [De Forest](http://planetarynames.wr.usgs.gov/Feature/1437) (43.5) |

#### Twin sharing (Solar panels)

| variant | distinct twins | largest share | top 3 twins | top 10 twins | twins covering half the points | most shared twins (cell, nearest feature, points, %) |
|---|---|---|---|---|---|---|
| A1 | 186 | 16.8 % | 37.8 % | 67.9 % | 6 | M59734 Schrodinger 3,161 (16.8 %); M59522 Le Gentil 2,315 (12.3 %); M59736 Schrodinger 1,631 (8.7 %) |
| A2 | 124 | 19.0 % | 47.3 % | 80.8 % | 4 | M59734 Schrodinger 3,567 (19.0 %); M59479 Boltzmann 2,895 (15.4 %); M59522 Le Gentil 2,415 (12.9 %) |
| A3a | 122 | 20.0 % | 53.2 % | 86.4 % | 3 | M59736 Schrodinger 3,748 (20.0 %); M59479 Boltzmann 3,243 (17.3 %); M59522 Le Gentil 2,989 (15.9 %) |
| A3b | 68 | 19.3 % | 53.9 % | 89.4 % | 3 | M59479 Boltzmann 3,618 (19.3 %); M59734 Schrodinger 3,436 (18.3 %); M59522 Le Gentil 3,073 (16.4 %) |

#### Change against the baseline and similarity distribution (Solar panels)

| variant | Spearman final vs A0 | Spearman similarity vs A0 | top-10 overlap | top-50 overlap | similarity min / median / max | Spearman(similarity, suitability) |
|---|---|---|---|---|---|---|
| A0 | 1 | 1 | 10/10 | 50/50 | 19.6 / 68.2 / 98.3 | -0.132 |
| A1 | 0.567 | 0.197 | 0/10 | 8/50 | 61.9 / 76.8 / 99.3 | -0.681 |
| A1mean | 0.799 | 0.679 | 2/10 | 12/50 | 21.8 / 52.4 / 83.3 | -0.061 |
| A2 | 0.428 | 0.159 | 0/10 | 0/50 | 48.8 / 68.4 / 99.2 | -0.696 |
| A3a | 0.377 | 0.162 | 0/10 | 0/50 | 45.3 / 66.1 / 99.1 | -0.693 |
| A3b | 0.612 | 0.236 | 2/10 | 15/50 | 34.3 / 54.9 / 81.5 | -0.940 |

Largest rises from A0 to A1 (rank A0 -> A1): E17537 41.5N 77.5E Kyrgyzstan / Ysyk-Koel 18,306 -> 923; E42590 28.5S 69.5W Argentina 17,577 -> 331; E42950 29.5S 69.5W Argentina / San Juan 17,672 -> 1,349

Largest falls from A0 to A1: E60508 78.5S 151.5W Antarctica 6,350 -> 18,272; E56817 67.5S 117.5E Antarctica 6,421 -> 18,273; E60507 78.5S 152.5W Antarctica 6,422 -> 18,256

A1 against its variants: A1mean: Spearman 0.864, top-10 0/10, top-50 10/50; A2: Spearman 0.933, top-10 0/10, top-50 2/50, same twin for 59 % of points; A3a: Spearman 0.887, top-10 0/10, top-50 0/50, same twin for 42 % of points; A3b: Spearman 0.862, top-10 0/10, top-50 12/50, same twin for 43 % of points

#### Legacy 2-degree data (Solar panels), for comparison

Ranked Earth points (pass every gate): **5,192**. Target zone: south_pole (1440 lunar cells).

##### A1 approved rule: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E10058 | 21.0S 137.0E | Australia | 94.3 | 70.5 | 82.4 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 2 | E10598 | 27.0S 137.0E | Australia / South Australia | 93.2 | 71.1 | 82.1 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 3 | E10419 | 25.0S 139.0E | Australia | 93.8 | 70.5 | 82.1 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 4 | E10418 | 25.0S 137.0E | Australia | 93.5 | 70.8 | 82.1 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 5 | E10599 | 27.0S 139.0E | Australia / South Australia | 93.2 | 70.9 | 82.0 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 6 | E10239 | 23.0S 139.0E | Australia | 93.7 | 70.1 | 81.9 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 7 | E10242 | 23.0S 145.0E | Australia | 93.5 | 70.1 | 81.8 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 8 | E10238 | 23.0S 137.0E | Australia | 93.0 | 70.5 | 81.8 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 9 | E10591 | 27.0S 123.0E | Australia | 93.2 | 70.3 | 81.7 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |
| 10 | E10770 | 29.0S 121.0E | Australia / Western Australia | 91.9 | 71.6 | 81.7 | M14890 | 75.0S 81.0E | [Hale](http://planetarynames.wr.usgs.gov/Feature/2321) (90.3) |

Absolute values, A1 top 10 (Earth / lunar twin). Variables in the similarity: elevation_rel_m, slope_deg, roughness_m, temp_k, rock_or_bare_frac, sar_sigma0_db.

| # | elev_rel m | slope deg | rough m | temp K | bare frac | radar dB |
|---|---|---|---|---|---|---|
| 1 | -793 / -1,375 | 0.7 / 7.1 | 34 / 335 | 297.3 / 81.4 | 0.633 / 0.006 | -13.1 / -17.4 |
| 2 | -998 / -1,375 | 0.7 / 7.1 | 31 / 335 | 296.7 / 81.4 | 0.650 / 0.006 | -12.9 / -17.4 |
| 3 | -971 / -1,375 | 0.5 / 7.1 | 22 / 335 | 298.2 / 81.4 | 0.682 / 0.006 | -12.8 / -17.4 |
| 4 | -915 / -1,375 | 1.0 / 7.1 | 47 / 335 | 297.0 / 81.4 | 0.662 / 0.006 | -12.7 / -17.4 |
| 5 | -1,016 / -1,375 | 0.3 / 7.1 | 13 / 335 | 296.8 / 81.4 | 0.644 / 0.006 | -13.2 / -17.4 |
| 6 | -872 / -1,375 | 1.0 / 7.1 | 45 / 335 | 298.8 / 81.4 | 0.664 / 0.006 | -12.7 / -17.4 |
| 7 | -787 / -1,375 | 1.0 / 7.1 | 47 / 335 | 297.9 / 81.4 | 0.583 / 0.006 | -13.3 / -17.4 |
| 8 | -793 / -1,375 | 1.3 / 7.1 | 60 / 335 | 296.5 / 81.4 | 0.632 / 0.006 | -12.8 / -17.4 |
| 9 | -560 / -1,375 | 0.8 / 7.1 | 36 / 335 | 295.8 / 81.4 | 0.672 / 0.006 | -12.7 / -17.4 |
| 10 | -617 / -1,375 | 0.9 / 7.1 | 42 / 335 | 292.7 / 81.4 | 0.630 / 0.006 | -13.0 / -17.4 |

\* not part of the similarity on this dataset.


##### Twin sharing (Solar panels)

| variant | distinct twins | largest share | top 3 twins | top 10 twins | twins covering half the points | most shared twins (cell, nearest feature, points, %) |
|---|---|---|---|---|---|---|
| A1 | 84 | 13.9 % | 34.1 % | 64.0 % | 7 | M14928 Schrodinger 724 (13.9 %); M14890 Hale 672 (12.9 %); M14847 Short 374 (7.2 %) |
| A2 | 61 | 19.7 % | 42.7 % | 78.6 % | 4 | M14890 Hale 1,025 (19.7 %); M14893 Hale 649 (12.5 %); M14927 Schrodinger 542 (10.4 %) |
| A3a | 50 | 15.5 % | 39.4 % | 77.4 % | 5 | M14890 Hale 807 (15.5 %); M14792 Zeeman 634 (12.2 %); M14928 Schrodinger 603 (11.6 %) |
| A3b | 45 | 15.6 % | 39.2 % | 75.3 % | 5 | M14890 Hale 812 (15.6 %); M14792 Zeeman 628 (12.1 %); M14928 Schrodinger 597 (11.5 %) |

##### Change against the baseline and similarity distribution (Solar panels)

| variant | Spearman final vs A0 | Spearman similarity vs A0 | top-10 overlap | top-50 overlap | similarity min / median / max | Spearman(similarity, suitability) |
|---|---|---|---|---|---|---|
| A0 | 1 | 1 | 10/10 | 50/50 | 30.1 / 70.5 / 94.0 | 0.018 |
| A1 | 0.899 | 0.485 | 0/10 | 30/50 | 39.3 / 67.1 / 92.6 | -0.474 |
| A1mean | 0.972 | 0.578 | 0/10 | 39/50 | 27.7 / 47.7 / 67.5 | -0.662 |
| A2 | 0.851 | 0.346 | 0/10 | 30/50 | 40.3 / 61.3 / 93.8 | -0.750 |
| A3a | 0.815 | 0.311 | 0/10 | 30/50 | 38.3 / 60.0 / 93.4 | -0.770 |
| A3b | 0.842 | 0.239 | 0/10 | 20/50 | 36.5 / 58.4 / 91.1 | -0.883 |

Largest rises from A0 to A1 (rank A0 -> A1): E14732 73.0S 125.0E Antarctica 4,052 -> 1,688; E14733 73.0S 127.0E Antarctica 4,068 -> 1,732; E14734 73.0S 129.0E Antarctica 4,074 -> 1,746

Largest falls from A0 to A1: E14952 77.0S 155.0W Antarctica 2,735 -> 4,204; E2118 67.0N 97.0E Russia 2,229 -> 3,631; E1943 69.0N 107.0E Russia 2,357 -> 3,752

A1 against its variants: A1mean: Spearman 0.902, top-10 5/10, top-50 38/50; A2: Spearman 0.985, top-10 8/10, top-50 47/50, same twin for 39 % of points; A3a: Spearman 0.971, top-10 6/10, top-50 46/50, same twin for 46 % of points; A3b: Spearman 0.960, top-10 7/10, top-50 39/50, same twin for 40 % of points

### 3.3 Lunar base

**Reading.** With the NASA regions as target, the A1 top 10 is the western Kunlun / Aksai Chin plateau (about 3,200-4,700 m above Earth's mean land height, suitability 60-72) paired with cells of the Mons Mouton Plateau and Nobile Rim 1 regions (about 5,500-6,300 m above the lunar mean), i.e. high plateaus on both bodies; one Puna cell (Argentina) also enters. Using the whole south-pole zone instead (A1sp) keeps 7 of the top 10 and moves a few twins outside the NASA regions (Short, Rittenhouse). The ranking is anti-correlated with the global-mean baseline (Spearman -0.16): the baseline favoured low, vegetated cells (bare fraction 0.001-0.08 in its top 10). A2/A3 make temperature 62-75 % of the weight and collapse the twins: 12 or fewer distinct twins and 64-66 % of all points on one de Gerlache Rim 2 cell (M64190).

Cells touched by each NASA region (footprint = union of the USGS 1 km grid squares):

| region | 1 km grid squares | footprint km2 | real 1-degree cells touched | legacy 2-degree cells touched |
|---|---|---|---|---|
| Peak near Cabeus B | 441 | 441 | 12 | 7 |
| Haworth | 930 | 930 | 45 | 13 |
| Malapert Massif | 462 | 462 | 23 | 12 |
| Mons Mouton Plateau | 4,524 | 4,524 | 87 | 33 |
| Mons Mouton | 289 | 289 | 11 | 6 |
| Nobile Rim 1 | 441 | 441 | 15 | 7 |
| Nobile Rim 2 | 420 | 420 | 19 | 10 |
| de Gerlache Rim 2 | 441 | 441 | 53 | 28 |
| Slater Plain | 441 | 441 | 36 | 11 |
| **union** (cells shared by neighbouring regions counted once) | | | **280** | **114** |

Near the pole a one-degree cell is only a few km wide east-west (about 0.5 km at 89S), which is why de Gerlache Rim 2 (88.2S) touches 53 cells.

Ranked Earth points (pass every gate): **2,419**. Target zone: artemis (280 lunar cells).


#### A0 baseline (global mean): top 10

| # | Earth cell | lat, lon | country / region | suitability | similarity | final |
|---|---|---|---|---|---|---|
| 1 | E15778 | 46.5N 118.5E | China / Inner Mongolia | 36.5 | 87.6 | 62.0 |
| 2 | E18287 | 39.5N 107.5E | China / Inner Mongolia | 38.7 | 85.3 | 62.0 |
| 3 | E18288 | 39.5N 108.5E | China / Inner Mongolia | 38.5 | 85.0 | 61.8 |
| 4 | E15418 | 47.5N 118.5E | Mongolia / East Aimak | 37.6 | 84.6 | 61.1 |
| 5 | E14109 | 50.5N 110.5W | Canada / Alberta | 26.1 | 96.0 | 61.1 |
| 6 | E18289 | 39.5N 109.5E | China / Inner Mongolia | 36.1 | 85.8 | 60.9 |
| 7 | E18649 | 38.5N 109.5E | China / Shaanxi | 35.0 | 86.8 | 60.9 |
| 8 | E14835 | 48.5N 104.5W | United States / Montana | 24.8 | 96.7 | 60.7 |
| 9 | E14654 | 49.5N 74.5E | Kazakhstan / Qaraghandy | 24.3 | 97.2 | 60.7 |
| 10 | E14699 | 49.5N 119.5E | China / Inner Mongolia | 35.2 | 86.1 | 60.7 |

#### A1 approved rule: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E19345 | 36.5N 85.5E | China / Xinjiang Uygur Zizhiqu | 69.6 | 83.8 | 76.7 | M62859 [Mons_Mouton_Plateau] | 84.5S 39.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (10.6) |
| 2 | E19704 | 35.5N 84.5E | China | 71.6 | 80.8 | 76.2 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 3 | E19699 | 35.5N 79.5E | China | 67.4 | 84.2 | 75.8 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 4 | E19703 | 35.5N 83.5E | China | 69.6 | 81.9 | 75.7 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 5 | E18986 | 37.5N 86.5E | China / Xinjiang Uygur Zizhiqu | 60.3 | 89.5 | 74.9 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 6 | E19346 | 36.5N 86.5E | China | 66.4 | 83.2 | 74.8 | M62859 [Mons_Mouton_Plateau] | 84.5S 39.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (10.6) |
| 7 | E19705 | 35.5N 85.5E | China | 66.0 | 83.1 | 74.6 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 8 | E19698 | 35.5N 78.5E | China | 62.3 | 86.0 | 74.1 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 9 | E41871 | 26.5S 68.5W | Argentina | 69.6 | 78.7 | 74.1 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 10 | E19702 | 35.5N 82.5E | China | 64.4 | 83.3 | 73.9 | M63217 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 37.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (13.1) |

Absolute values, A1 top 10 (Earth / lunar twin). Variables in the similarity: elevation_rel_m, slope_deg, roughness_m, temp_k.

| # | elev_rel m | slope deg | rough m | temp K | bare frac | radar dB |
|---|---|---|---|---|---|---|
| 1 | 4,230 / 6,304 | 1.9 / 8.8 | 75 / 300 | 271.6 / 152.4 | 0.781 / 1.000 * | no data / no data * |
| 2 | 4,270 / 6,345 | 1.0 / 6.6 | 34 / 231 | 272.8 / 150.1 | 0.933 / 1.000 * | no data / no data * |
| 3 | 4,500 / 5,469 | 4.4 / 19.0 | 175 / 569 | 271.8 / 167.5 | 0.578 / 1.000 * | no data / no data * |
| 4 | 4,343 / 6,345 | 1.2 / 6.6 | 39 / 231 | 272.3 / 150.1 | 0.892 / 1.000 * | no data / no data * |
| 5 | 3,188 / 5,469 | 5.1 / 19.0 | 186 / 569 | 275.9 / 167.5 | 0.682 / 1.000 * | no data / no data * |
| 6 | 4,313 / 6,304 | 1.8 / 8.8 | 66 / 300 | 270.7 / 152.4 | 0.789 / 1.000 * | no data / no data * |
| 7 | 4,389 / 6,345 | 1.1 / 6.6 | 41 / 231 | 271.3 / 150.1 | 0.815 / 1.000 * | no data / no data * |
| 8 | 4,657 / 5,469 | 4.6 / 19.0 | 175 / 569 | 269.5 / 167.5 | 0.495 / 1.000 * | no data / no data * |
| 9 | 3,862 / 5,469 | 5.0 / 19.0 | 162 / 569 | 280.6 / 167.5 | 0.528 / 1.000 * | no data / no data * |
| 10 | 4,502 / 5,803 | 2.8 / 11.5 | 112 / 390 | 270.5 / 154.7 | 0.761 / 1.000 * | no data / no data * |

\* not part of the similarity on this dataset.

Not part of the similarity (informative only), A1 top 10 (Earth / lunar twin):

| # | irradiance kWh/m2/day | diurnal amplitude K | minimum temp C | surface class | permafrost | lunar rock abundance (Diviner) |
|---|---|---|---|---|---|---|
| 1 | 4.38 / 0.85 | 27.1 / 187.1 | -28.7 / -204.7 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 2 | 4.43 / 0.78 | 27.5 / 182.8 | -27.7 / -205.7 | regolito / regolito | discontinuo / ninguno | no data (product covers 60S-60N) |
| 3 | 4.31 / 0.63 | 26.5 / 199.9 | -27.9 / -203.4 | regolito / regolito | discontinuo / ninguno | no data (product covers 60S-60N) |
| 4 | 4.40 / 0.78 | 27.2 / 182.8 | -28.0 / -205.7 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 5 | 4.46 / 0.63 | 22.2 / 199.9 | -23.8 / -203.4 | regolito / regolito | discontinuo / ninguno | no data (product covers 60S-60N) |
| 6 | 4.39 / 0.85 | 25.3 / 187.1 | -28.8 / -204.7 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 7 | 4.41 / 0.78 | 25.2 / 182.8 | -28.1 / -205.7 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |
| 8 | 4.24 / 0.63 | 24.2 / 199.9 | -28.8 / -203.4 | regolito / regolito | discontinuo / ninguno | no data (product covers 60S-60N) |
| 9 | 5.75 / 0.63 | 31.6 / 199.9 | -7.5 / -203.4 | regolito / regolito | no data / ninguno | no data (product covers 60S-60N) |
| 10 | 4.36 / 0.60 | 24.2 / 178.5 | -28.4 / -210.2 | regolito / regolito | continuo / ninguno | no data (product covers 60S-60N) |

#### A2 Use Weights (diluted matrix): top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E19699 | 35.5N 79.5E | China | 67.4 | 84.5 | 75.9 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 2 | E19698 | 35.5N 78.5E | China | 62.3 | 87.1 | 74.7 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 3 | E19700 | 35.5N 80.5E | China / Xinjiang Uygur Zizhiqu | 57.6 | 89.4 | 73.5 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 4 | E19701 | 35.5N 81.5E | China / Xinjiang Uygur Zizhiqu | 57.9 | 88.0 | 72.9 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 5 | E18987 | 37.5N 87.5E | China | 61.6 | 83.1 | 72.4 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 6 | E19345 | 36.5N 85.5E | China / Xinjiang Uygur Zizhiqu | 69.6 | 74.7 | 72.2 | M62859 [Mons_Mouton_Plateau] | 84.5S 39.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (10.6) |
| 7 | E19344 | 36.5N 84.5E | China | 66.1 | 77.5 | 71.8 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 8 | E41871 | 26.5S 68.5W | Argentina | 69.6 | 73.8 | 71.7 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 9 | E19704 | 35.5N 84.5E | China | 71.6 | 71.2 | 71.4 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 10 | E40432 | 22.5S 67.5W | Bolivia | 77.0 | 65.7 | 71.4 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |

#### A3a undiluted, luz/agua dropped: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E19699 | 35.5N 79.5E | China | 67.4 | 84.9 | 76.1 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 2 | E19698 | 35.5N 78.5E | China | 62.3 | 88.2 | 75.2 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 3 | E19700 | 35.5N 80.5E | China / Xinjiang Uygur Zizhiqu | 57.6 | 90.6 | 74.1 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 4 | E19701 | 35.5N 81.5E | China / Xinjiang Uygur Zizhiqu | 57.9 | 89.7 | 73.8 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 5 | E19344 | 36.5N 84.5E | China | 66.1 | 79.5 | 72.8 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 6 | E18987 | 37.5N 87.5E | China | 61.6 | 83.3 | 72.5 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 7 | E40432 | 22.5S 67.5W | Bolivia | 77.0 | 66.7 | 71.9 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 8 | E41871 | 26.5S 68.5W | Argentina | 69.6 | 72.9 | 71.2 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 9 | E19345 | 36.5N 85.5E | China / Xinjiang Uygur Zizhiqu | 69.6 | 72.7 | 71.1 | M62859 [Mons_Mouton_Plateau] | 84.5S 39.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (10.6) |
| 10 | E19697 | 35.5N 77.5E | Pakistan | 48.0 | 93.4 | 70.7 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |

#### A3b undiluted, luz variables added: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E40432 | 22.5S 67.5W | Bolivia | 77.0 | 49.4 | 63.2 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 2 | E19699 | 35.5N 79.5E | China | 67.4 | 57.7 | 62.6 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 3 | E19704 | 35.5N 84.5E | China | 71.6 | 53.2 | 62.4 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 4 | E19345 | 36.5N 85.5E | China / Xinjiang Uygur Zizhiqu | 69.6 | 54.7 | 62.2 | M62859 [Mons_Mouton_Plateau] | 84.5S 39.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (10.6) |
| 5 | E19703 | 35.5N 83.5E | China | 69.6 | 53.5 | 61.5 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 6 | E19344 | 36.5N 84.5E | China | 66.1 | 56.6 | 61.3 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 7 | E18634 | 38.5N 94.5E | China / Qinghai Sheng | 72.1 | 50.4 | 61.3 | M64190 [de_Gerlache_Rim_2] | 88.5S 69.5W | [de Gerlache](http://planetarynames.wr.usgs.gov/Feature/1439) (15.0) |
| 8 | E41151 | 24.5S 68.5W | Chile | 74.1 | 47.9 | 61.0 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 9 | E40792 | 23.5S 67.5W | Chile / Antofagasta | 73.5 | 48.3 | 60.9 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 10 | E40071 | 21.5S 68.5W | Chile | 73.7 | 48.1 | 60.9 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |

#### A1 with the whole south-pole zone: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E19345 | 36.5N 85.5E | China / Xinjiang Uygur Zizhiqu | 69.6 | 83.8 | 76.7 | M62859 [Mons_Mouton_Plateau] | 84.5S 39.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (10.6) |
| 2 | E19704 | 35.5N 84.5E | China | 71.6 | 80.8 | 76.2 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 3 | E19699 | 35.5N 79.5E | China | 67.4 | 84.2 | 75.8 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 4 | E18634 | 38.5N 94.5E | China / Qinghai Sheng | 72.1 | 79.5 | 75.8 | M59931 | 76.5S 8.5W | [Short](http://planetarynames.wr.usgs.gov/Feature/5499) (59.8) |
| 5 | E19703 | 35.5N 83.5E | China | 69.6 | 81.9 | 75.7 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |
| 6 | E18992 | 37.5N 92.5E | China / Qinghai Sheng | 72.9 | 78.1 | 75.5 | M59682 | 75.5S 102.5E | [Rittenhouse](http://planetarynames.wr.usgs.gov/Feature/5157) (52.4) |
| 7 | E15758 | 46.5N 98.5E | Mongolia / Bayanhongor | 62.0 | 88.5 | 75.3 | M59680 | 75.5S 100.5E | [Rittenhouse](http://planetarynames.wr.usgs.gov/Feature/5157) (64.3) |
| 8 | E18986 | 37.5N 86.5E | China / Xinjiang Uygur Zizhiqu | 60.3 | 89.5 | 74.9 | M63218 [Mons_Mouton_Plateau, Nobile_Rim_1] | 85.5S 38.5E | [Masina](http://planetarynames.wr.usgs.gov/Feature/16269) (15.4) |
| 9 | E19346 | 36.5N 86.5E | China | 66.4 | 83.2 | 74.8 | M62859 [Mons_Mouton_Plateau] | 84.5S 39.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (10.6) |
| 10 | E19705 | 35.5N 85.5E | China | 66.0 | 83.1 | 74.6 | M62858 [Mons_Mouton_Plateau, Nobile_Rim_1] | 84.5S 38.5E | [Floss](http://planetarynames.wr.usgs.gov/Feature/16251) (13.0) |

#### Twin sharing (Lunar base)

| variant | distinct twins | largest share | top 3 twins | top 10 twins | twins covering half the points | most shared twins (cell, nearest feature, points, %) |
|---|---|---|---|---|---|---|
| A1 | 48 | 27.7 % | 54.1 % | 76.5 % | 3 | M62515 Wapowski 671 (27.7 %); M63665 Slater 332 (13.7 %); M64191 de Gerlache 305 (12.6 %) |
| A2 | 12 | 66.1 % | 86.2 % | 99.6 % | 1 | M64190 de Gerlache 1,600 (66.1 %); M64189 de Gerlache 321 (13.3 %); M63218 Masina 163 (6.7 %) |
| A3a | 10 | 63.9 % | 92.5 % | 100.0 % | 1 | M64190 de Gerlache 1,546 (63.9 %); M64189 de Gerlache 437 (18.1 %); M63218 Masina 255 (10.5 %) |
| A3b | 10 | 63.9 % | 90.0 % | 100.0 % | 1 | M64190 de Gerlache 1,546 (63.9 %); M64189 de Gerlache 382 (15.8 %); M63218 Masina 250 (10.3 %) |
| A1sp | 74 | 15.7 % | 33.9 % | 65.9 % | 6 | M59734 Schrodinger 379 (15.7 %); M59482 Boltzmann 256 (10.6 %); M59479 Boltzmann 186 (7.7 %) |

#### Change against the baseline and similarity distribution (Lunar base)

| variant | Spearman final vs A0 | Spearman similarity vs A0 | top-10 overlap | top-50 overlap | similarity min / median / max | Spearman(similarity, suitability) |
|---|---|---|---|---|---|---|
| A0 | 1 | 1 | 10/10 | 50/50 | 19.6 / 46.9 / 97.2 | -0.573 |
| A1 | -0.159 | -0.354 | 0/10 | 0/50 | 55.9 / 67.5 / 94.3 | 0.040 |
| A1mean | 0.208 | 0.341 | 0/10 | 0/50 | 30.1 / 49.3 / 70.4 | -0.075 |
| A2 | -0.149 | -0.301 | 0/10 | 0/50 | 43.9 / 57.2 / 91.3 | 0.045 |
| A3a | -0.136 | -0.268 | 0/10 | 0/50 | 41.9 / 56.2 / 93.4 | 0.041 |
| A3b | -0.047 | -0.208 | 0/10 | 0/50 | 36.9 / 46.9 / 60.8 | 0.030 |
| A1sp | -0.011 | -0.070 | 0/10 | 0/50 | 64.6 / 75.4 / 94.3 | -0.031 |

Largest rises from A0 to A1 (rank A0 -> A1): E18253 39.5N 73.5E Kyrgyzstan / Osh 2,352 -> 157; E17538 41.5N 78.5E China / Xinjiang Uygur Zizhiqu 2,205 -> 67; E19697 35.5N 77.5E Pakistan 2,220 -> 90

Largest falls from A0 to A1: E16640 43.5N 99.5W United States / South Dakota 83 -> 2,138; E19520 35.5N 99.5W United States / Oklahoma 203 -> 2,241; E19160 36.5N 99.5W United States / Oklahoma 177 -> 2,207

A1 against its variants: A1mean: Spearman 0.760, top-10 0/10, top-50 12/50; A2: Spearman 0.987, top-10 5/10, top-50 42/50, same twin for 16 % of points; A3a: Spearman 0.980, top-10 4/10, top-50 40/50, same twin for 12 % of points; A3b: Spearman 0.970, top-10 4/10, top-50 40/50, same twin for 13 % of points; A1sp: Spearman 0.961, top-10 7/10, top-50 34/50, same twin for 13 % of points

#### Legacy 2-degree data (Lunar base), for comparison

Ranked Earth points (pass every gate): **2,613**. Target zone: artemis (114 lunar cells).

##### A1 approved rule: top 10

| # | Earth cell | lat, lon | country / region | suit. | sim. | final | lunar twin | twin lat, lon | nearest IAU feature (km) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | E15427 | 81.0S 75.0E | Antarctica | 79.5 | 76.3 | 77.9 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 2 | E15426 | 81.0S 73.0E | Antarctica | 79.4 | 76.4 | 77.9 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 3 | E15429 | 81.0S 79.0E | Antarctica | 79.4 | 76.4 | 77.9 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 4 | E15425 | 81.0S 71.0E | Antarctica | 79.1 | 76.6 | 77.9 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 5 | E15428 | 81.0S 77.0E | Antarctica | 79.5 | 76.2 | 77.8 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 6 | E15430 | 81.0S 81.0E | Antarctica | 79.2 | 76.4 | 77.8 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 7 | E15424 | 81.0S 69.0E | Antarctica | 78.9 | 76.5 | 77.7 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 8 | E15431 | 81.0S 83.0E | Antarctica | 78.9 | 76.5 | 77.7 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 9 | E15423 | 81.0S 67.0E | Antarctica | 78.8 | 76.6 | 77.7 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |
| 10 | E15422 | 81.0S 65.0E | Antarctica | 78.6 | 76.7 | 77.7 | M15762 [Mons_Mouton_Plateau] | 85.0S 25.0E | [Jaci](http://planetarynames.wr.usgs.gov/Feature/16268) (20.3) |

Absolute values, A1 top 10 (Earth / lunar twin). Variables in the similarity: elevation_rel_m, slope_deg, roughness_m, temp_k, rock_or_bare_frac, sar_sigma0_db.

| # | elev_rel m | slope deg | rough m | temp K | bare frac | radar dB |
|---|---|---|---|---|---|---|
| 1 | 2,984 / 4,967 | 0.9 / 5.6 | 40 / 717 | 220.5 / 71.7 | 0.819 / 0.006 | -11.5 / -17.7 |
| 2 | 2,952 / 4,967 | 1.1 / 5.6 | 49 / 717 | 220.3 / 71.7 | 0.819 / 0.006 | -11.4 / -17.7 |
| 3 | 2,970 / 4,967 | 0.8 / 5.6 | 34 / 717 | 220.5 / 71.7 | 0.817 / 0.006 | -11.6 / -17.7 |
| 4 | 2,913 / 4,967 | 1.0 / 5.6 | 46 / 717 | 220.0 / 71.7 | 0.816 / 0.006 | -11.5 / -17.7 |
| 5 | 2,999 / 4,967 | 0.7 / 5.6 | 30 / 717 | 220.9 / 71.7 | 0.818 / 0.006 | -11.6 / -17.7 |
| 6 | 2,933 / 4,967 | 0.9 / 5.6 | 39 / 717 | 220.6 / 71.7 | 0.816 / 0.006 | -11.5 / -17.7 |
| 7 | 2,883 / 4,967 | 1.0 / 5.6 | 47 / 717 | 220.5 / 71.7 | 0.815 / 0.006 | -11.4 / -17.7 |
| 8 | 2,888 / 4,967 | 0.9 / 5.6 | 42 / 717 | 220.9 / 71.7 | 0.814 / 0.006 | -11.5 / -17.7 |
| 9 | 2,857 / 4,967 | 1.1 / 5.6 | 50 / 717 | 220.3 / 71.7 | 0.814 / 0.006 | -11.4 / -17.7 |
| 10 | 2,831 / 4,967 | 1.1 / 5.6 | 49 / 717 | 220.1 / 71.7 | 0.812 / 0.006 | -11.4 / -17.7 |

\* not part of the similarity on this dataset.


##### Twin sharing (Lunar base)

| variant | distinct twins | largest share | top 3 twins | top 10 twins | twins covering half the points | most shared twins (cell, nearest feature, points, %) |
|---|---|---|---|---|---|---|
| A1 | 23 | 18.7 % | 48.1 % | 94.0 % | 4 | M15580 Mons Mouton 488 (18.7 %); M15599 Wapowski 397 (15.2 %); M15762 Jaci 372 (14.2 %) |
| A2 | 10 | 51.6 % | 79.7 % | 100.0 % | 1 | M15600 Wapowski 1,349 (51.6 %); M15599 Wapowski 369 (14.1 %); M15580 Mons Mouton 365 (14.0 %) |
| A3a | 7 | 60.1 % | 82.9 % | 100.0 % | 1 | M15600 Wapowski 1,570 (60.1 %); M15599 Wapowski 305 (11.7 %); M15580 Mons Mouton 291 (11.1 %) |
| A3b | 7 | 59.2 % | 83.0 % | 100.0 % | 1 | M15600 Wapowski 1,547 (59.2 %); M15580 Mons Mouton 318 (12.2 %); M15599 Wapowski 303 (11.6 %) |
| A1sp | 81 | 18.9 % | 32.4 % | 58.7 % | 7 | M15010 Casatus 493 (18.9 %); M14890 Hale 202 (7.7 %); M14827 Casatus 151 (5.8 %) |

##### Change against the baseline and similarity distribution (Lunar base)

| variant | Spearman final vs A0 | Spearman similarity vs A0 | top-10 overlap | top-50 overlap | similarity min / median / max | Spearman(similarity, suitability) |
|---|---|---|---|---|---|---|
| A0 | 1 | 1 | 10/10 | 50/50 | 25.0 / 67.2 / 94.0 | -0.423 |
| A1 | 0.791 | 0.308 | 0/10 | 0/50 | 37.1 / 71.6 / 81.1 | 0.624 |
| A1mean | 0.741 | 0.308 | 0/10 | 0/50 | 27.3 / 53.6 / 66.7 | 0.215 |
| A2 | 0.754 | 0.071 | 0/10 | 0/50 | 33.5 / 66.3 / 76.7 | 0.773 |
| A3a | 0.734 | -0.005 | 0/10 | 0/50 | 35.2 / 65.3 / 79.3 | 0.812 |
| A3b | 0.729 | 0.003 | 0/10 | 0/50 | 35.0 / 65.2 / 77.7 | 0.794 |
| A1sp | 0.804 | 0.276 | 0/10 | 0/50 | 37.9 / 82.2 / 92.6 | 0.589 |

Largest rises from A0 to A1 (rank A0 -> A1): E15428 81.0S 77.0E Antarctica 1,337 -> 5; E15429 81.0S 79.0E Antarctica 1,333 -> 3; E15427 81.0S 75.0E Antarctica 1,324 -> 1

Largest falls from A0 to A1: E2136 67.0N 133.0E Russia / Sakha 216 -> 1,536; E15186 79.0S 47.0W Antarctica 24 -> 1,333; E14801 75.0S 97.0W Antarctica 4 -> 1,269

A1 against its variants: A1mean: Spearman 0.943, top-10 0/10, top-50 9/50; A2: Spearman 0.984, top-10 9/10, top-50 33/50, same twin for 33 % of points; A3a: Spearman 0.978, top-10 0/10, top-50 22/50, same twin for 31 % of points; A3b: Spearman 0.972, top-10 0/10, top-50 22/50, same twin for 31 % of points; A1sp: Spearman 0.952, top-10 0/10, top-50 0/50, same twin for 0 % of points

## 4. Effective weights, known analog sites, limitations

### 4.1 Effective weights of each variant

Today's diluted percentages (`map_domain_weights_to_features`, six variables, recomputed with the module's own function): Rover slope 17.25 %, roughness 18.25 %, relative elevation 13.5 %, temperature 18.25 %, rock 20.0 %, radar 12.75 %; Solar panels temperature 36.25 %, relative elevation 20.75 %, rock 16.25 %, slope 13.5 %, roughness 7.25 %, radar 6.0 %; Lunar base (= thermal) temperature 41.75 %, rock 24.25 %, roughness 10.25 %, slope 8.25 %, radar 8.0 %, relative elevation 7.5 %. These **confirm** the team lead's figures (which were rounded down to one decimal: 17.2, 18.2, 18.3, 12.8 ... are 17.25, 18.25, 18.25, 12.75). They are the A2 row of the legacy table below; on the real data the same matrix is renormalised over the four variables present.

**Real 1-degree data** (percent of the similarity weight; blank = not in the similarity)

| mission | variant | slope | roughness | relative elevation | temperature | bare fraction | radar | irradiance | sun elevation max | low-sun fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| Rover | A0 | 27.78 | 22.22 | 16.67 | 16.67 | 16.67 |  |  |  |  |
| Rover | A1 | 33.33 | 26.67 | 20.00 | 20.00 |  |  |  |  |  |
| Rover | A2 | 25.65 | 27.14 | 20.07 | 27.14 |  |  |  |  |  |
| Rover | A3a | 32.41 | 25.93 | 19.44 | 22.22 |  |  |  |  |  |
| Rover | A3b | 26.52 | 21.21 | 15.91 | 18.18 |  |  | 6.06 | 6.06 | 6.06 |
| Solar panels | A0 | 27.78 | 22.22 | 16.67 | 16.67 | 16.67 |  |  |  |  |
| Solar panels | A1 | 33.33 | 26.67 | 20.00 | 20.00 |  |  |  |  |  |
| Solar panels | A2 | 17.36 | 9.32 | 26.69 | 46.62 |  |  |  |  |  |
| Solar panels | A3a | 17.86 | 14.29 | 10.71 | 57.14 |  |  |  |  |  |
| Solar panels | A3b | 7.81 | 6.25 | 4.69 | 25.00 |  |  | 18.75 | 18.75 | 18.75 |
| Lunar base | A0 | 27.78 | 22.22 | 16.67 | 16.67 | 16.67 |  |  |  |  |
| Lunar base | A1 | 33.33 | 26.67 | 20.00 | 20.00 |  |  |  |  |  |
| Lunar base | A2 | 12.18 | 15.13 | 11.07 | 61.62 |  |  |  |  |  |
| Lunar base | A3a | 10.42 | 8.33 | 6.25 | 75.00 |  |  |  |  |  |
| Lunar base | A3b | 8.93 | 7.14 | 5.36 | 64.29 |  |  | 4.76 | 4.76 | 4.76 |

**Legacy 2-degree data** (percent of the similarity weight; blank = not in the similarity)

| mission | variant | slope | roughness | relative elevation | temperature | bare fraction | radar | irradiance | sun elevation max | low-sun fraction |
|---|---|---|---|---|---|---|---|---|---|---|
| Rover | A0 | 25.00 | 20.00 | 15.00 | 15.00 | 15.00 | 10.00 |  |  |  |
| Rover | A1 | 25.00 | 20.00 | 15.00 | 15.00 | 15.00 | 10.00 |  |  |  |
| Rover | A2 | 17.25 | 18.25 | 13.50 | 18.25 | 20.00 | 12.75 |  |  |  |
| Rover | A3a | 19.44 | 15.56 | 11.67 | 13.33 | 24.00 | 16.00 |  |  |  |
| Rover | A3b | 17.16 | 13.73 | 10.29 | 11.76 | 21.18 | 14.12 | 3.92 | 3.92 | 3.92 |
| Solar panels | A0 | 25.00 | 20.00 | 15.00 | 15.00 | 15.00 | 10.00 |  |  |  |
| Solar panels | A1 | 25.00 | 20.00 | 15.00 | 15.00 | 15.00 | 10.00 |  |  |  |
| Solar panels | A2 | 13.50 | 7.25 | 20.75 | 36.25 | 16.25 | 6.00 |  |  |  |
| Solar panels | A3a | 13.89 | 11.11 | 8.33 | 44.44 | 13.33 | 8.89 |  |  |  |
| Solar panels | A3b | 6.94 | 5.56 | 4.17 | 22.22 | 6.67 | 4.44 | 16.67 | 16.67 | 16.67 |
| Lunar base | A0 | 25.00 | 20.00 | 15.00 | 15.00 | 15.00 | 10.00 |  |  |  |
| Lunar base | A1 | 25.00 | 20.00 | 15.00 | 15.00 | 15.00 | 10.00 |  |  |  |
| Lunar base | A2 | 8.25 | 10.25 | 7.50 | 41.75 | 24.25 | 8.00 |  |  |  |
| Lunar base | A3a | 7.35 | 5.88 | 4.41 | 52.94 | 17.65 | 11.76 |  |  |  |
| Lunar base | A3b | 6.58 | 5.26 | 3.95 | 47.37 | 15.79 | 10.53 | 3.51 | 3.51 | 3.51 |

### 4.2 Known analog sites

Sites from `NASA/docs/research/02_analog_benchmark.csv`, located in the cell that contains the listed coordinates. "Reason if eliminated" is the funnel's own message (`mission_scoring.score_mission`). Mauna Kea and HI-SEAS fall in the same real cell (E25224).

##### Real data, known analog sites (Rover)

| site | cell | passes? | rank A0 | rank A1 | rank A2 | rank A3a | A1 twin (feature) | reason if eliminated |
|---|---|---|---|---|---|---|---|---|
| Rio Tinto - Pena de Hierro headwaters (Huelva) | E18893 | yes | 1,899/10,337 | 6,541/10,337 | 6,705/10,337 | 6,575/10,337 | M59416 (De Forest) | |
| Tabernas Desert (Almeria) | E18897 | yes | 7,825/10,337 | 6,966/10,337 | 6,992/10,337 | 6,954/10,337 | M59478 (Boltzmann) | |
| Bardenas Reales (Navarra) | E17098 | yes | 5,707/10,337 | 5,811/10,337 | 5,788/10,337 | 5,801/10,337 | M59479 (Boltzmann) | |
| El Soplao cave (Cantabria) | E16735 | yes | 9,803/10,337 | 9,993/10,337 | 9,963/10,337 | 9,984/10,337 | M59634 (Demonax) | |
| Atacama Desert - Yungay core | E41150 | yes | 6,079/10,337 | 2,529/10,337 | 2,860/10,337 | 2,664/10,337 | M60256 (Casatus) | |
| Mojave - Dumont Dunes | E19503 | yes | 7,199/10,337 | 8,535/10,337 | 8,399/10,337 | 8,556/10,337 | M59478 (Boltzmann) | |
| Mars Desert Research Station (Hanksville, Utah) | E18429 | yes | 6,144/10,337 | 4,169/10,337 | 4,277/10,337 | 4,225/10,337 | M59679 (Rittenhouse) | |
| Haughton impact crater (Devon Island, Nunavut) | E5130 | yes | 4,224/10,337 | 80/10,337 | 81/10,337 | 78/10,337 | M59910 (Newton) | |
| Black Point Lava Flow and SP Mountain (San Francisco Volcanic Field) | E19508 | yes | 4,797/10,337 | 6,081/10,337 | 6,213/10,337 | 6,136/10,337 | M59680 (Rittenhouse) | |
| Mauna Kea - Pu'u Hiwahine (PISCES site) | E25224 | yes | 9,120/10,337 | 9,572/10,337 | 9,596/10,337 | 9,580/10,337 | M59634 (Demonax) | |
| Concordia Station (Dome C) | E59703 | no | | | | | | slope_300m_deg fuera de [0.5, 15.0]; rough_300m_m fuera de [5.0, 650.0] |
| HI-SEAS habitat (Mauna Loa) | E25224 | yes | 9,120/10,337 | 9,572/10,337 | 9,596/10,337 | 9,580/10,337 | M59634 (Demonax) | |

##### Real data, known analog sites (Solar panels)

| site | cell | passes? | rank A0 | rank A1 | rank A2 | rank A3a | A1 twin (feature) | reason if eliminated |
|---|---|---|---|---|---|---|---|---|
| Rio Tinto - Pena de Hierro headwaters (Huelva) | E18893 | yes | 1,720/18,777 | 3,269/18,777 | 4,408/18,777 | 3,633/18,777 | M59416 (De Forest) | |
| Tabernas Desert (Almeria) | E18897 | yes | 13,084/18,777 | 5,922/18,777 | 6,272/18,777 | 6,405/18,777 | M59478 (Boltzmann) | |
| Bardenas Reales (Navarra) | E17098 | yes | 8,247/18,777 | 5,792/18,777 | 4,202/18,777 | 3,665/18,777 | M59479 (Boltzmann) | |
| El Soplao cave (Cantabria) | E16735 | no | | | | | | thermal_inertia_class no permitido |
| Atacama Desert - Yungay core | E41150 | yes | 12,201/18,777 | 3,535/18,777 | 4,028/18,777 | 2,891/18,777 | M60256 (Casatus) | |
| Mojave - Dumont Dunes | E19503 | yes | 9,342/18,777 | 4,691/18,777 | 4,495/18,777 | 5,360/18,777 | M59478 (Boltzmann) | |
| Mars Desert Research Station (Hanksville, Utah) | E18429 | yes | 9,526/18,777 | 2,471/18,777 | 1,167/18,777 | 806/18,777 | M59679 (Rittenhouse) | |
| Haughton impact crater (Devon Island, Nunavut) | E5130 | no | | | | | | irradiance_kwh_m2_day fuera de [2.5, inf] |
| Black Point Lava Flow and SP Mountain (San Francisco Volcanic Field) | E19508 | yes | 4,729/18,777 | 1,280/18,777 | 483/18,777 | 576/18,777 | M59680 (Rittenhouse) | |
| Mauna Kea - Pu'u Hiwahine (PISCES site) | E25224 | yes | 17,012/18,777 | 10,028/18,777 | 11,061/18,777 | 11,273/18,777 | M59634 (Demonax) | |
| Concordia Station (Dome C) | E59703 | yes | 15,064/18,777 | 14,587/18,777 | 15,064/18,777 | 13,930/18,777 | M59522 (Le Gentil) | |
| HI-SEAS habitat (Mauna Loa) | E25224 | yes | 17,012/18,777 | 10,028/18,777 | 11,061/18,777 | 11,273/18,777 | M59634 (Demonax) | |

##### Real data, known analog sites (Lunar base)

| site | cell | passes? | rank A0 | rank A1 | rank A2 | rank A3a | A1 twin (feature) | reason if eliminated |
|---|---|---|---|---|---|---|---|---|
| Rio Tinto - Pena de Hierro headwaters (Huelva) | E18893 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf]; tmin_c fuera de [-inf, 5.0] |
| Tabernas Desert (Almeria) | E18897 | yes | 2,269/2,419 | 1,908/2,419 | 2,018/2,419 | 2,038/2,419 | M62504 (Floss) | |
| Bardenas Reales (Navarra) | E17098 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf] |
| El Soplao cave (Cantabria) | E16735 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf]; thermal_inertia_class no permitido |
| Atacama Desert - Yungay core | E41150 | yes | 171/2,419 | 41/2,419 | 96/2,419 | 116/2,419 | M62486 (Mons Mouton) | |
| Mojave - Dumont Dunes | E19503 | yes | 1,895/2,419 | 1,647/2,419 | 1,890/2,419 | 1,940/2,419 | M64189 (de Gerlache) | |
| Mars Desert Research Station (Hanksville, Utah) | E18429 | yes | 1,629/2,419 | 1,084/2,419 | 1,165/2,419 | 1,216/2,419 | M64191 (de Gerlache) | |
| Haughton impact crater (Devon Island, Nunavut) | E5130 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf] |
| Black Point Lava Flow and SP Mountain (San Francisco Volcanic Field) | E19508 | yes | 500/2,419 | 1,199/2,419 | 1,161/2,419 | 1,214/2,419 | M62484 (Mons Mouton) | |
| Mauna Kea - Pu'u Hiwahine (PISCES site) | E25224 | no | | | | | | tmin_c fuera de [-inf, 5.0] |
| Concordia Station (Dome C) | E59703 | no | | | | | | lst_diurnal_amp_k sin dato |
| HI-SEAS habitat (Mauna Loa) | E25224 | no | | | | | | tmin_c fuera de [-inf, 5.0] |

##### Legacy data, known analog sites (Rover)

| site | cell | passes? | rank A0 | rank A1 | rank A2 | rank A3a | A1 twin (feature) | reason if eliminated |
|---|---|---|---|---|---|---|---|---|
| Rio Tinto - Pena de Hierro headwaters (Huelva) | E4766 | yes | 2,580/5,297 | 3,391/5,297 | 3,413/5,297 | 3,331/5,297 | M14847 (Short) | |
| Tabernas Desert (Almeria) | E4768 | yes | 5,121/5,297 | 5,170/5,297 | 5,171/5,297 | 5,168/5,297 | M14838 (Newton) | |
| Bardenas Reales (Navarra) | E4229 | yes | 5,026/5,297 | 5,092/5,297 | 5,090/5,297 | 5,091/5,297 | M14906 (Rittenhouse) | |
| El Soplao cave (Cantabria) | E4227 | yes | 4,824/5,297 | 4,939/5,297 | 4,947/5,297 | 4,933/5,297 | M14831 (Casatus) | |
| Atacama Desert - Yungay core | E10315 | no | | | | | | slope_300m_deg fuera de [0.5, 15.0]; rough_300m_m fuera de [5.0, 650.0] |
| Mojave - Dumont Dunes | E4891 | yes | 4,710/5,297 | 4,728/5,297 | 4,740/5,297 | 4,739/5,297 | M14831 (Casatus) | |
| Mars Desert Research Station (Hanksville, Utah) | E4534 | yes | 5,000/5,297 | 4,968/5,297 | 4,971/5,297 | 4,976/5,297 | M14862 (Schomberger) | |
| Haughton impact crater (Devon Island, Nunavut) | E1305 | yes | 140/5,297 | 1,130/5,297 | 1,114/5,297 | 1,116/5,297 | M14847 (Short) | |
| Black Point Lava Flow and SP Mountain (San Francisco Volcanic Field) | E4894 | yes | 4,211/5,297 | 4,186/5,297 | 4,172/5,297 | 4,169/5,297 | M14852 (Short) | |
| Mauna Kea - Pu'u Hiwahine (PISCES site) | E6312 | no | | | | | | elevation_m fuera de [1.0, inf]; mask_fraction fuera de [0.3, inf]; slope_300m_deg fuera de [0.5, 15.0]; rough_300m_m fuera de [5.0, 650.0] |
| Concordia Station (Dome C) | E14911 | no | | | | | | slope_300m_deg fuera de [0.5, 15.0] |
| HI-SEAS habitat (Mauna Loa) | E6312 | no | | | | | | elevation_m fuera de [1.0, inf]; mask_fraction fuera de [0.3, inf]; slope_300m_deg fuera de [0.5, 15.0]; rough_300m_m fuera de [5.0, 650.0] |

##### Legacy data, known analog sites (Solar panels)

| site | cell | passes? | rank A0 | rank A1 | rank A2 | rank A3a | A1 twin (feature) | reason if eliminated |
|---|---|---|---|---|---|---|---|---|
| Rio Tinto - Pena de Hierro headwaters (Huelva) | E4766 | yes | 1,200/5,192 | 1,387/5,192 | 1,619/5,192 | 1,775/5,192 | M14847 (Short) | |
| Tabernas Desert (Almeria) | E4768 | yes | 4,163/5,192 | 4,542/5,192 | 4,638/5,192 | 4,665/5,192 | M14838 (Newton) | |
| Bardenas Reales (Navarra) | E4229 | yes | 4,174/5,192 | 4,580/5,192 | 4,652/5,192 | 4,697/5,192 | M14906 (Rittenhouse) | |
| El Soplao cave (Cantabria) | E4227 | yes | 3,592/5,192 | 4,408/5,192 | 4,524/5,192 | 4,575/5,192 | M14831 (Casatus) | |
| Atacama Desert - Yungay core | E10315 | no | | | | | | slope_deg fuera de [-inf, 15.0] |
| Mojave - Dumont Dunes | E4891 | yes | 3,111/5,192 | 3,452/5,192 | 3,295/5,192 | 3,432/5,192 | M14831 (Casatus) | |
| Mars Desert Research Station (Hanksville, Utah) | E4534 | yes | 3,952/5,192 | 4,210/5,192 | 4,047/5,192 | 4,076/5,192 | M14862 (Schomberger) | |
| Haughton impact crater (Devon Island, Nunavut) | E1305 | yes | 2,631/5,192 | 3,285/5,192 | 3,433/5,192 | 3,403/5,192 | M14847 (Short) | |
| Black Point Lava Flow and SP Mountain (San Francisco Volcanic Field) | E4894 | yes | 1,993/5,192 | 2,108/5,192 | 1,878/5,192 | 2,001/5,192 | M14852 (Short) | |
| Mauna Kea - Pu'u Hiwahine (PISCES site) | E6312 | no | | | | | | elevation_m fuera de [1.0, inf]; mask_fraction fuera de [0.3, inf]; thermal_inertia_class no permitido |
| Concordia Station (Dome C) | E14911 | yes | 4,353/5,192 | 2,225/5,192 | 1,518/5,192 | 1,364/5,192 | M15404 (Scott) | |
| HI-SEAS habitat (Mauna Loa) | E6312 | no | | | | | | elevation_m fuera de [1.0, inf]; mask_fraction fuera de [0.3, inf]; thermal_inertia_class no permitido |

##### Legacy data, known analog sites (Lunar base)

| site | cell | passes? | rank A0 | rank A1 | rank A2 | rank A3a | A1 twin (feature) | reason if eliminated |
|---|---|---|---|---|---|---|---|---|
| Rio Tinto - Pena de Hierro headwaters (Huelva) | E4766 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf]; tmin_c fuera de [-inf, 5.0] |
| Tabernas Desert (Almeria) | E4768 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf]; tmin_c fuera de [-inf, 5.0] |
| Bardenas Reales (Navarra) | E4229 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf]; tmin_c fuera de [-inf, 5.0] |
| El Soplao cave (Cantabria) | E4227 | no | | | | | | lst_diurnal_amp_k fuera de [15.0, inf]; tmin_c fuera de [-inf, 5.0] |
| Atacama Desert - Yungay core | E10315 | no | | | | | | tmin_c fuera de [-inf, 5.0] |
| Mojave - Dumont Dunes | E4891 | yes | 2,450/2,613 | 2,534/2,613 | 2,546/2,613 | 2,555/2,613 | M15601 (Oberbeck) | |
| Mars Desert Research Station (Hanksville, Utah) | E4534 | yes | 2,485/2,613 | 2,504/2,613 | 2,493/2,613 | 2,503/2,613 | M15578 (Malapert) | |
| Haughton impact crater (Devon Island, Nunavut) | E1305 | yes | 1,546/2,613 | 1,866/2,613 | 1,930/2,613 | 1,961/2,613 | M15599 (Wapowski) | |
| Black Point Lava Flow and SP Mountain (San Francisco Volcanic Field) | E4894 | yes | 2,206/2,613 | 2,348/2,613 | 2,441/2,613 | 2,465/2,613 | M15580 (Mons Mouton) | |
| Mauna Kea - Pu'u Hiwahine (PISCES site) | E6312 | no | | | | | | elevation_m fuera de [1.0, inf]; mask_fraction fuera de [0.3, inf]; lst_diurnal_amp_k fuera de [15.0, inf]; tmin_c fuera de [-inf, 5.0]; thermal_inertia_class no permitido |
| Concordia Station (Dome C) | E14911 | yes | 1,074/2,613 | 192/2,613 | 105/2,613 | 78/2,613 | M15762 (Jaci) | |
| HI-SEAS habitat (Mauna Loa) | E6312 | no | | | | | | elevation_m fuera de [1.0, inf]; mask_fraction fuera de [0.3, inf]; lst_diurnal_amp_k fuera de [15.0, inf]; tmin_c fuera de [-inf, 5.0]; thermal_inertia_class no permitido |

### 4.3 Verdict: are the pairs defensible to a planetary scientist?

- **Rover: partly.** The pairs are defensible as a statement of *relative* terrain position (gentle, slightly rough, cold for its body), and the top places (Canadian Arctic, near Haughton) are recognised polar analog terrain. They are not defensible as physical likeness: slope and roughness differ by factors of 5-7 at the same baseline, temperature by about 100 K. The cause is the per-body normalisation, which the document must state next to every pair.
- **Solar panels: no, not as pairs.** The suitability selects sunny, warm places; the twin must come from the coldest, most grazing-sun part of the Moon; the two pull in opposite directions (Spearman -0.68), and the twins are the warmest polar cells matched on relief alone. Six lunar cells take half of the points. Cause: a target zone whose defining property (polar illumination) is not among the similarity variables; adding the sun variables (A3b) adds latitude, not illumination physics.
- **Lunar base: partly.** High Earth plateaus paired with the high Mons Mouton Plateau and Nobile rims is a coherent relative statement, and the target regions are official. Weak points: 48 twins for 2,419 points (three cover half), the Earth's thermal gates (diurnal amplitude, cold minimum) never meet the lunar values (top-10 Earth diurnal amplitude 22-32 K against 178-200 K for the twins), and only four topographic/thermal variables enter.
- **Common causes when not defensible:** (1) z-scores per body hide absolute differences; (2) the target zone covers a narrow part of the lunar range, so Earth points outside it collapse onto the zone's edge cells; (3) no material variable remains on the real data; (4) Antarctic Earth cells without temperature are treated as temperate (z = 0).

### 4.4 Limitations, stated plainly

- **Cell size.** Real cells are 1 degree (111 km north-south on Earth, 30 km on the Moon); legacy 2 degrees. A pair says "a 100 km Earth cell resembles a 30 km lunar cell in relative terms", never "this outcrop resembles this crater". Slopes are ~3.7 km-baseline slopes and roughness a ~1.9 km lag, not rover-scale values.
- **Polar strips.** Near the south pole a one-degree lunar cell is a few km wide east-west and covers almost no area; the 75S-90S zone holds 5,400 cells of very unequal area, and the twin search weights them all equally. The NASA-region footprints are the USGS navigational grids (an upper bound of the exact outlines, which are not public).
- **What z-scores per body hide.** A similarity of 98 can join 0.9 deg with 6.2 deg, 253 K with 150 K. A user who reads "98 % similar" as physical likeness is misled unless the absolute values are shown (they are, in every table here).
- **Variables with no data.** Radar: none on the real data. Bare fraction: constant on the Moon (removed). Earth temperature: none in Antarctica (z = 0, decision item). Lunar permafrost: `ninguno` in every cell of the real table, a MODELLED label set by definition (the column was empty until checkpoint 3b6c949, which also updated `column_aliases.json`); it enters no similarity. Diviner rock abundance: 60S-60N only, so none for any twin. Earth diurnal amplitude: minimum -4.6 K in the real table (a negative day-minus-night value), informative only.
- **Twin concentration.** Largest shares 9-28 % with `DEFAULT_WEIGHTS`, 13-66 % with the mission weights.

## 5. Decisions pending

1. Weights for the similarity: A1 (`DEFAULT_WEIGHTS`), A2 (today's diluted matrix) or A3a (undiluted). Recommendation: A1 until the mission teams state weights per variable; if domain weights must be used, A3a, because A2 lets "luz" and "agua" (which have no variable among the six) leak into temperature and relative elevation.
2. Rock variable on the real data: removal confirmed by the numbers (section 2.2); Diviner rock abundance kept as a separate informative lunar value only.
3. Twin versus zone mean: twin recommended (section 2.3).
4. Antarctic Earth cells with no temperature: keep the repository's z = 0 (as computed here) or drop the variable for those cells and renormalise. Affects 1,156 Rover and 6,060 Solar-panels points.
5. Twin concentration: accept and show the share, or add a rule (for example report the top three twins per Earth point).
6. Lunar base footprint: accept the USGS grid footprints (280 cells) or wait for exact outlines; and whether the product shows the NASA regions (A1) or the whole south-pole zone (A1sp).
7. Solar panels: whether the south-pole zone remains its target given section 4.3.

## 6. New data looked up

Every external item used here, with its source, access date and the checks run. No missing value was filled or estimated; nothing was added to the repository's tables.

| item | source (accessed 2026-11-14) | level | checks and results |
|---|---|---|---|
| Artemis candidate-region footprints | USGS ScienceBase item 671a6fa8d34efed5620f89f8, doi 10.5066/P1MEQ6UK (resolves there): title "Down Selected Artemis III Candidate Landing Site Navigational Grids", originator Mark T. McClernan, publication date 2024-12-05, citation "McClernan, M.T., 2024 ... U.S. Geological Survey data release", rights "Creative Commons Zero v1.0 Universal". Contents: nine region zips with 1 km, 100 m and 10 m LGRS-ACC grids; text: "Down selected Artemis III Candidate Landing Regions were sourced from LROC QuickMap". The 1 km grid shapefiles of all nine regions were extracted to `scratchpad/stars/artemis/usgs_grids/` (eight zips downloaded in full and deleted after extraction, SHA-256 in `artemis/usgs_dl/sha256.txt`; Mons Mouton Plateau read by HTTP range from the published S3 object). The listed outline file `A3_9regions-lonlat-simplified.zip` returned HTTP 403 (unpublished). | MEASURED (official outlines as grids) | **Units and projection:** `.prj` of all nine identical: "Moon_2015_-_Sphere_Ocentric_South_Polar", stereographic, latitude of origin -90, central meridian 0, scale 0.994, false easting/northing 500,000 m, sphere 1,737,400 m, metres; grid squares 1.000 km2 each. The XML metadata says straight-vertical longitude -90, which contradicts the `.prj`; with -90 the region centres would fall 55-338 km from their features, with the `.prj` 3-67 km, so the `.prj` is right. Converted with pyproj to IAU_2015:30100 ("Moon (2015) - Sphere / Ocentric"). **Latitude/longitude not swapped:** all latitudes -82.8 to -88.7, longitudes -78.5 to +135.5. **Longitude convention:** output -180..180; the gazetteer's 0..360 east longitudes converted (lon - 360 when > 180) before comparison. **Every region within a few degrees of the pole:** yes (82.8S-88.7S). **Centres against the IAU gazetteer** (great-circle km, 1,737.4 km sphere; feature diameter in brackets): Malapert Massif - Mons Malapert 3.1 (67 km); Mons Mouton Plateau - Mons Mouton 8.0 (130 km); de Gerlache Rim 2 - de Gerlache 21.5 (33 km); Mons Mouton - Mons Mouton 25.0; Slater Plain - Slater 32.6 (25 km); Haworth - Haworth 33.6 (51 km); Nobile Rim 1 - Nobile 39.3 (79 km); Nobile Rim 2 - Nobile 43.0; Peak near Cabeus B - Cabeus B 67.1 (60 km). Rim and "peak near" regions sit on or beside their parent feature, as their names say. |
| Artemis programme statements | nasa.gov pages listed in section 1.1 (releases 24-136 and 26-022, Artemis III and IV mission pages, blog of 2026-10-23); NASA web search for Artemis IV candidate regions | official statements | Quotes copied from the fetched HTML; release dates read from the page header ("Oct 28, 2024", "Feb 27, 2026") and page metadata. No Artemis IV region list found. |
| Wueller et al. (2026) | Crossref record of doi 10.1029/2025JE009434 | not used | Exists: "Assessing Potential Landing Sites With Favorable Illumination and Accessible, Potentially Volatile-Rich Permanently Shadowed Regions Within Artemis Candidate Landing Regions", JGR Planets, issued 2026-02-27. Not needed (the USGS grids were readable); Table A1 was not opened. |
| IAU feature names and centres | `engine/data/iau_moon_nomenclature.csv` (already in the repository; source and SHA-256 in `iau_source.json`) | MEASURED | Used as is; satellite features excluded for naming as `engine_config.json` says (Cabeus B, a satellite feature, was used only for the region check). |

No other value was fetched. The Diviner rock abundance and all Earth and Moon variables come from the repository's own real tables and their provenance files.
