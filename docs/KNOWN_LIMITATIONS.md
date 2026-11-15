# Known limitations

Team "Stars Beside You", NASA Space Apps Challenge 2026. State of branch `final-integration`, engine 3.4.0,
data contract revision 8, 15 November 2026. Every statement below is taken from `ASSUMPTIONS.md`,
`docs/REAL_DATA.md`, `docs/DECISIONS.md`, the statistical audit in `docs/stats_audit/` (parts 1 to 9 and the
re-audit JSON files) and the texts the bundle ships (`app/public/data/v2/similarity.json` `texts`). Where a
figure is quoted, the source named next to it holds the computation.

## 1. What is measured, derived or modelled

Each column has one of three levels in the provenance files (`tierra luna/real_data/provenance_*.csv`,
summarised in `docs/REAL_DATA.md` section 4). The app shows the level next to every value.

**Earth.**

| level | columns |
|---|---|
| MEASURED | elevation (ETOPO 2022); land share and bare-ground share (ESA CCI land cover 2020, a classification: the bare share is a land-cover share, not rock abundance); clear-sky fraction (ISCCP-H, supplement) |
| DERIVED | slope and roughness (from ETOPO); land surface temperature and its day-night amplitude (MODIS LST climatology: clear-sky, two overpasses, not air temperature, and the amplitude understates the daily range); sun elevation columns and sunlight above the atmosphere (formulas of latitude, never measured) |
| MODELLED | **coldest-month minimum temperature and ground irradiance (WorldClim 2.1: interpolated 1970-2000 climate normals; the temperature is 2 m air temperature)**; **permafrost class (Obu et al. probability maps, with assumed IPA thresholds; empty, not "none", where the maps have no pixel, south of about 18-25 N)**; thermal-inertia class (an assumed mapping from land-cover classes); rain and wind (WorldClim, not stored in the bundle) |

**Moon.**

| level | columns |
|---|---|
| MEASURED | elevation (LOLA LDEM_16, height above the 1737.4 km sphere); maximum and minimum surface temperature (Diviner GCP); rock abundance (Diviner, 60 S to 60 N only) |
| DERIVED | slope, roughness; mean temperature and diurnal amplitude; polar lit fraction (a ray-traced simulation over LOLA topography at latitudes of 65.5 deg or more, flat-ground geometry elsewhere); irradiance (solar constant and exact geometry, no atmosphere) |
| MODELLED | land share and bare-ground share (1 everywhere by definition); thermal-inertia class ("regolito" everywhere, an assumption); permafrost class ("ninguno" in every cell, a label set by a team decision, not a measurement) |

Comparisons across bodies therefore often set a modelled Earth value against a measured lunar one. The clearest
case is Lunar base: the Earth coldest temperature is a MODELLED WorldClim air temperature, the lunar one a
MEASURED Diviner surface temperature (ASSUMPTIONS.md 0.13).

## 2. Resolution

- A cell is 1 degree: about 111 km north-south on Earth (110.6-111.7 km) and about 30 km on the Moon (30.3 km).
  East-west a cell is that size times cos(latitude): next to the lunar pole a cell is a strip 0.26 km wide,
  and poleward of about 80 deg lunar cells are only a few km wide. A polar cell averages lit ridges with
  shadowed craters; the best-lit points of the lunar south pole do not appear (ASSUMPTIONS.md 10.5).
- Every value is a cell aggregate. Nothing here describes a landing site or a rover traverse.
- Slopes are measured over 3.7-3.8 km and roughness at a 1.85-1.9 km lag. The team's rover thresholds were
  written for a 300 m baseline and are applied unchanged; km-baseline slopes are gentler and km-lag roughness
  larger, so the gates do not mean exactly what their authors intended (ASSUMPTIONS.md 10.5).
- Cells with less than half land are coarse; Earth latitudes are geodetic (at most 0.19 deg from
  planetocentric).

## 3. What each mission's list can and cannot claim

The app lists five sites per mission with the words "five of the highest-scoring analogs in our model, not a
proven best" (Rover: "five of the 254 sites tied at the top"). The full ranking is ordered by the final score
(50 % similarity, 50 % the team's suitability).

### Rover

- **254 sites are tied** at the top final score of 100.00 (241 after leaving out cells half or more ice or less
  than half land). Differences within the measurement error of the elevation models (slope 0.27 deg, roughness
  17.4 m; ETOPO 2022 RMSE 7.17 m and LOLA ~10 m radial) are scored as equal, so the data cannot tell these sites
  apart. Among tied points the order is by Earth cell id; the five are chosen to be spread across the world.
- **The order is the team's suitability.** The similarity is saturated (10,335 of 10,337 pairs score 100), so the
  final ranking equals the suitability ranking (Spearman 1.000; `docs/stats_audit/9_reauditoria_rover.md`).
  The suitability is saturated too: 250 of the 254 tied sites score the maximum on all three team criteria.
  Slope and roughness utilities correlate at 0.97, so they act as nearly one criterion.
- Recognised analogs pay for the bare-ground criterion at 1 degree: Bardenas ranks in the top 68.2 % and Tabernas
  in the top 71.5 %, losing 24.4 and 19.8 suitability points on the bare-ground share alone; Ramon (3.6 %),
  Haughton (4.2 %), Qaidam (4.0 %) and Yungay (8.1 %) stay in the top 10 %.
- **The five are not stable as individuals:** in 200 simulations under the documented data uncertainty each stays
  among the five in 43-87.5 % of runs and the exact list repeats in 10.5 %; the tied group is stable (89 % of its
  members kept, median). The twins change in most runs.
- Ice sheets and water-dominated cells are not excluded from the ranking (1,506 and 1,145 ranked points); they are
  only skipped when the five are chosen.
- The minimum slope of 0.5 deg is a team criterion with no official source, kept for its measured effect.
- Slope and roughness at km baselines say nothing about rover-scale hazards (rocks, boulders, soil strength).

### Solar panels

- **The similarity is saturated.** Sunlight above the atmosphere depends on latitude only, so a twin is the best of
  a median of about 1,840 candidate maria cells; 78 % of the 6,360 pairs score 99 or more and 514 show 100.00.
  Among the 100 best-ranked points the similarity only goes from 99.00 to 100.00, so their order follows
  suitability.
- **Matched on sunlight above the atmosphere, not at the ground.** At the Earth site part of that sunlight is lost
  in the atmosphere: 35 % for the number 1 pair ("6.2 of 9.6" kWh/m2/day), 45.3 % at the median of all pairs. The
  ground value is MODELLED (WorldClim). The Moon has no atmosphere and its day lasts 29.5 Earth days, about half
  of them in darkness. No text says or implies that panels charge the same in both places.
- Only Earth points at about 33.5 deg of latitude or less can find a twin among the equatorial maria: 12,417 of
  the 18,777 passing points have no twin and are listed after the paired points.
- The three latitude-driven or modelled criteria weigh 0 in the suitability; 35 % of it is the ISCCP clear-sky
  fraction.
- No independent re-audit of Solar panels (a part 9 like those of Rover and Lunar base) is in
  `docs/stats_audit/`; the stability sentence of the five reads "Stability figures pending the independent
  re-audit." in the shipped bundle.

### Lunar base

- **A likeness of thermal position, not of temperature.** The coldest temperature and the daily swing are compared
  as percentiles of each body's own population. In real values the two places are far apart: median difference
  207.9 K in coldest temperature (about 200 K) and 153.8 K in daily swing over the 450 pairs (ASSUMPTIONS.md
  0.13). Every pair sentence in the app says so with the real difference.
- **The five are fragile:** in 200 simulations the same five come back together in 0 runs, and no one of them
  stays among the five in more than 23 % (`docs/stats_audit/9_reauditoria_base.md`). The number 2 site (E17538)
  is 0.6 K above the swing gate and leaves the funnel in 36.5 % of the simulations; the fifth is in a practical
  tie (10 of 16 weight changes keep it).
- **Recognised polar stations are excluded by the swing gate** (daily swing at least 15 K, the team's gate):
  Haughton crater 2.5 K, Svalbard (Bockfjorden) 1.2 K, Kangerlussuaq 6.6 K; McMurdo and Concordia have no land
  surface temperature (the MODIS product has none for Antarctica). Without the gate, Ellesmere Island cells with
  a swing of about 1 K would match at a similarity of about 99. These stations are analogs of cold and
  isolation, not of thermal cycling.
- Only 450 of the 2,419 passing points have a twin; 103 distinct twins, the most shared one (Mons Mouton Plateau)
  by 25 points (5.6 %). The zone includes every cell touching one of NASA's nine candidate regions (280 cells):
  69 of the 103 twins have less than half of their cell inside a region and are labelled "at the edge of".
- The four suitability weights sum to 0.95 and are renormalised (effective 36.8 / 26.3 / 26.3 / 10.5 %).

## 4. External validation as it stands

There is no ground truth that says which Earth place "really is" the analog of a lunar place, so no accuracy
percentage is given (`docs/VALIDATION.md`). What was checked is where known sites fall in each ranking:

- **Rover:** the team's mobility analog sites with verified coordinates: positive-negative separation 0.906,
  5 of 8 positives in the top quartile; the full list (including sites whose coordinates were written from
  memory) is worse, 0.855 (`9_reauditoria_rover.md` section 7).
- **Solar panels:** 13 sunny BSRN radiation stations and 6 cloudy stations as a contrast: 11 sunny stations pass
  the funnel and 9 have a twin, ranked from number 36 (Gandhinagar) to number 2,858 (De Aar) of 6,360
  (`similarity.json` `texts.external_validation_solar`).
- **Lunar base:** 13 cold or harsh research and analog sites and 7 warm humid stations: 3 of the 13 pass the funnel
  and 2 have a twin (MDRS number 335, Craters of the Moon number 179 of 450); separation 0.615
  (`9_reauditoria_base.md` section 7). No polar analog passes (section 3).

## 5. Criteria of the team without an official source

- The solar and thermal (Lunar base) thresholds in `tierra luna/mission_scoring.json` are, in the file's own note,
  "valores de diseno NO validados con fuente externa" (design values not validated with an external source);
  the rover thresholds are provisional, and the rover tolerances of `rover_preset.py` version 3 are marked
  "ILUSTRATIVO".
- The Rover minimum slope of 0.5 deg has no official source (section 3).
- The permafrost thresholds and the thermal-inertia class mapping are assumptions (`real_data/class_mappings.json`).
- Several tolerances (Solar panels sunlight 0.6 kWh/m2/day, Lunar base 10 percentile points) were set by the
  team lead's delegate on 2026-11-15 (`docs/DECISIONS.md`, ASSUMPTIONS.md 0.12 and 0.13), not taken from a
  published source.
- Where the engine departs from the team's scoring file (7 criteria) is listed in the bundle text
  `deviations_from_team` and in `docs/DECISIONS.md` (decisions of 11:28 and 11:36).
- Some numbers of the team's file have no effect at this resolution or are read by no code (`similarity.json`
  `texts.numbers_without_effect`); the common gate "elevation at least 1 m" removes 177 real land cells below sea
  level, not the ocean.

## 6. Licences

WorldClim 2.1 is free for academic and other non-commercial use only; redistribution or commercial use needs
prior permission. The bundle ships 1-degree aggregates of two WorldClim columns (coldest temperature, ground
irradiance). Whether a public app may redistribute them, or whether permission must be asked or the columns
dropped, is a **pending team decision** (ASSUMPTIONS.md 10.5). The MODIS LST climatology is CC BY-SA 4.0, so data
derived from it must be shared under the same licence.

## 7. Software and presentation

- Frame rate has not been measured on real hardware. The app's tests and the video renders run in headless
  Chromium in a container without a GPU (WebGL in SwiftShader, `app/video-sim/README.md`).
- There is no cloud layer on the Earth globe (the NASA Visible Earth host could not be reached from the build
  container); the star background in the Moon view is oriented with Earth-frame logic (cosmetic).
- The mission videos are simulations, not footage; the Solar panels and Lunar base videos are driven by table
  values of one pair.
- The region label of an Earth cell comes from the nearest GeoNames place or a Natural Earth polygon and can be
  wrong near borders.

## 8. Open items listed by the audit

- The re-audits of Rover and Lunar base (`docs/stats_audit/9_reauditoria_*.md`) found no implementation fault and
  returned "NOT YET" on texts only (an outdated scoring formula text and missing stability figures for Rover; the
  external-validation and stability sentences for Lunar base, plus two minor wording points). The shipped bundle
  now carries the corrected Lunar base external-validation and stability texts; the Rover and Solar panels
  stability sentences still read "pending" in `similarity.json`.
- Solar panels has no independent re-audit yet (section 3).
- The WorldClim licence decision (section 6).
- The water skip for the five (mask_fraction below 0.5) is marked "to be confirmed" (ASSUMPTIONS.md 0).
- No lunar cold-trap variable exists; ice prospecting has no lunar side and is shown only as information.
