# R3: Do official sources support the filter thresholds?

Team "Stars Beside You", NASA Space Apps Challenge 2026. Prepared 2026-11-14 for the audit and the build.
All threshold values below are **as reported** by the team lead; none were changed. They must be re-read from the team's JSON once the repository is reachable.
All URLs were accessed on **2026-11-14**. Levels: **MEASURED** (official product or published figure), **DERIVED** (computed here from a measured figure by the formula shown), **MODELLED** (simulation or estimate).

## 1. Summary

| # | Finding | Level |
|---|---|---|
| 1 | A gate "maximum solar elevation >= 10 deg" applied to lunar cells removes **every lunar site poleward of about 81.5 deg latitude**, which includes the lunar poles where the Sun never rises more than about 1.5 deg. This is the suspected concept error and the sources confirm it. | MEASURED tilt, DERIVED cut-off |
| 2 | An irradiance gate ">= 2.5 kWh/m2/day" on a **horizontal** surface also removes the lunar poles: even with permanent light, horizontal irradiance at a pole is at most about 0.88 kWh/m2 per Earth day. The older 1.8 value fails them too. | DERIVED |
| 3 | The unit kWh/m2/day is an **inference**, but it is the only one of the common units for which 2.5 is a sensible cut (US federal and NREL products state daily solar resource in kWh/m2/day). | MEASURED unit usage |
| 4 | Slope <= 15 deg for solar is **far looser** than federal and NREL solar siting practice on Earth (5 % = 2.9 deg). It is in line with Apollo rover experience (rover <= 15 deg is supported). | MEASURED |
| 5 | Permafrost has one official definition (ground at or below 0 deg C for at least two consecutive years). It is a ground-temperature criterion, not an ice criterion. | MEASURED |
| 6 | The lunar equatorial diurnal range is about 95 K to 390 K (about 295 K amplitude). Lunar polar crater rims stay "constant at around 220K" (very small amplitude), so a thermal-amplitude gate >= 15 K applied to lunar cells may also drop polar rim cells. | MEASURED |
| 7 | Mask fraction 0.3, grazing-sun share 25 %, minimum temperature 5 deg C, thermal "good" end 35 K, roughness 5 to 650 m, slope >= 0.5 deg, and all weights are **pure design choices**: no source can confirm or refute them. | n/a |

## 2. Reference facts (with quotes)

| ID | Fact | Value | Source (accessed 2026-11-14) | Exact quote | Level |
|---|---|---|---|---|---|
| F1 | Solar irradiance at the Moon | 1361.0 W/m2 | https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html | "Solar irradiance (W/m2) 1361.0 1361.0 1.000" | MEASURED |
| F2 | Solar irradiance at Earth | 1361.0 W/m2 | https://nssdc.gsfc.nasa.gov/planetary/factsheet/earthfact.html | "Solar irradiance (W/m2) 1361.0" | MEASURED |
| F3 | Earth obliquity | 23.44 deg | same Earth fact sheet | "Obliquity to orbit (deg) 23.44" | MEASURED |
| F4 | Moon spin-axis tilt relative to the ecliptic (governs Sun height) | 1.54 deg | Gläser et al., NASA-hosted preprint (submitted to Planetary and Space Science, 2017): https://ntrs.nasa.gov/api/citations/20170007365/downloads/20170007365.pdf | "As a consequence of the small 1.54° rotational obliquity, illumination in polar regions differs considerably" | MEASURED (published) |
| F5 | Maximum Sun elevation at the lunar poles | 1.54 deg | same, Fig. 2 caption | "Note: the maximum elevation of the Sun at the poles is 1.54°." | MEASURED (published) |
| F6 | Moon tilt, NASA SVS wording | about 1.5 deg | https://svs.gsfc.nasa.gov/5229/ | "while the Earth is tilted 23.5°, the tilt of the Moon is a mere 1.5°" | MEASURED |
| F7 | Moon obliquity **to its own orbit** (not the Sun-relevant value) | 6.68 deg | Moon fact sheet (F1) | "Obliquity to orbit (deg) 6.68" | MEASURED. Do not use for Sun elevation: see F4 |
| F8 | Best-lit lunar polar sites | 69.5 % to 82.9 % average illumination at surface; 77.1 % to 88.0 % at 2 m height | Gläser et al. (F4), abstract | "Their average illumination levels range from 69.5% to 82.9%" ; "Here average illumination levels range from 77.1% to 88.0%" | MODELLED (LOLA-based simulation) |
| F9 | Slopes at best-lit lunar polar sites | avg 8.4 deg (max 11.5) and avg 12.1 deg (max 17.1) at two ridge clusters | Gläser et al. (F4), Results | "the average slope is 8.4◦ and the maximum slope is 11.5◦" ; "with an average and maximum slope of 12.1◦ and 17.1◦" | MEASURED (from LOLA DTM) |
| F10 | Lunar diurnal range at the equator | 95 K to 390 K | Moon fact sheet (F1) | "Diurnal temperature range (equator): 95 K to 390 K" | MEASURED |
| F11 | Lunar equator, Diviner | almost 400 K noon, below 100 K night | https://www.diviner.ucla.edu/science (LRO Diviner team) | "mean surface temperatures reach almost 400K (260.6 ºF) at noon" ; "then drop to below 100K (-279.4 ºF) during the night." | MEASURED |
| F12 | Lunar polar crater rims | about 220 K, nearly constant | same Diviner page | "Diviner has observed that temperatures in these regions remain constant at around 220K." | MEASURED |
| F13 | Lunar PSRs | as low as 25 K | same Diviner page | "temperatures within these permanently-shadowed craters can fall as low as 25K" | MEASURED |
| F14 | Earth record land surface temperature (LST, not air) | 70.7 deg C, Lut Desert, 2005, MODIS | https://science.nasa.gov/earth/earth-observatory/the-hottest-spot-on-earth-77627/ | "when MODIS recorded a temperature of 70.7°C (159.3°F)" ; "As opposed to air temperatures, which are measured 1.5 to 2 meters above the ground" | MEASURED |
| F15 | Largest 24-h **air** temperature change, USA (frontal/chinook event, not a diurnal cycle) | 103 deg F (-54 to 49 deg F) = 57.2 K | NOAA/NCDC: https://www.ncei.noaa.gov/monitoring-content/extremes/ncec/reports/lomanwa.pdf | "recorded a 103F temperature change (-54F to 49F) within twenty-four hours" | MEASURED; K conversion DERIVED (x 5/9) |
| F16 | Typical desert day and night **air** temperatures (educational page, weak source) | average 38 deg C day, -3.9 deg C night | https://science.nasa.gov/kids/earth/mission-biomes/biodesert/ | "desert temperatures rise to an average of 38°C" ; "desert temperatures fall to an average of -3.9°C" | MEASURED as stated; quality low (children's page) |
| F17 | Permafrost, USGS | at or below 0 deg C for >= 2 consecutive years | USGS Prof. Paper 1386-A, Heginbottom et al.: https://pubs.usgs.gov/pp/p1386a/pdf/notes/6-8permafros_508.pdf | "Permafrost or perennially frozen ground is defined as Earth material that remains at or below 0 degree Celsius (°C) for at least 2 consecutive years." | Definition |
| F18 | Permafrost, NOAA | same | https://arctic.noaa.gov/report-card/report-card-2017/terrestrial-permafrost/ | "Permafrost is defined as earth materials that exist at or below 0° C continuously for at least two consecutive years." | Definition |
| F19 | US federal solar exclusion criteria (2012 Solar PEIS) | slope > 5 % excluded; insolation < 6.5 kWh/m2/day excluded | BLM Notice of Intent, Federal Register 87 (235), 8 Dec 2022, p. 75284 ff.: https://www.energy.gov/sites/default/files/2023-05/blm-noi-eval-utility-scale-solar-energy-planning-12-2022_0.pdf | "(excluding development in locations with slopes greater than 5 percent) and 2 (excluding development where insolation values are below 6.5 kWh/m2/day) were based on technological constraints present at the time the 2012 programmatic EIS was prepared which might no longer apply." | MEASURED (regulatory) |
| F20 | Global GHI product unit (World Bank / Solargis Global Solar Atlas) | kWh/m2 daily and yearly totals | https://datacatalog.worldbank.org/search/dataset/0038645 | "global horizontal irradiation (GHI) in kWh/m² covering the globe" ; "LTAy_YearlyTotals = LTAy_DailyTotals * 365.25" | MEASURED (unit only) |
| F21 | Apollo LRV design slope | 20 to 23 deg favourable, max 25 deg | NASA NTRS 20250011301 (Jacob et al.): https://ntrs.nasa.gov/citations/20250011301 | "The LRVs were designed to navigate a 20 – 23° slope in "favorable conditions" with a max of 25°." | MEASURED (design spec) |
| F22 | Apollo LRV as driven | up to 20 deg straight ahead (Apollo 17); roll instability near 15 deg cross-slope (Apollo 15) | NASA ALSJ compilation of Mission Reports: https://www.nasa.gov/wp-content/uploads/static/history/alsj/WOTM/WOTM-LRVPerformance.html | "Sloped of up to 20 degrees were easily negotiated in a straight-ahead mode." ; "roll instability would be approached on the 15-degree slopes if the vehicle were traveling a contour line" | MEASURED (crew report) |

### Derived values used below (formulas stated)

| ID | Quantity | Formula | Result | Level |
|---|---|---|---|---|
| D1 | Highest latitude on the Moon where the yearly maximum noon Sun reaches 10 deg (flat horizon, no refraction) | 90 - phi + 1.54 >= 10, so phi <= 81.54 deg | **81.5 deg** | DERIVED from F4 |
| D2 | Same for Earth | 90 - phi + 23.44 >= 10 holds for every phi up to 90 (pole: 23.44 deg) | gate never removes an Earth cell if it uses the yearly maximum | DERIVED from F3 |
| D3 | Max horizontal irradiance at a lunar pole, Sun at 1.54 deg, lit 24 h a day | 1361 x sin(1.54 deg) x 24 h / 1000 | **0.88 kWh/m2/day** | DERIVED from F1, F5 |
| D4 | Mean horizontal irradiance at the lunar equator over a lunation (no albedo, flat) | 1361 / pi x 24 / 1000 | about **10.4 kWh/m2 per Earth day** | DERIVED from F1 |
| D5 | Slope percent to degrees | atan(p) | 3 % = 1.7 deg; 5 % = 2.9 deg; 10 % = 5.7 deg; 15 deg = 26.8 % | DERIVED |
| D6 | Lunar equatorial diurnal amplitude | 390 - 95 | **295 K** | DERIVED from F10 |

## 3. Threshold-by-threshold verdicts

| Mission / gate | Value as reported | What official sources say | Verdict | Consequence for results |
|---|---|---|---|---|
| Common: land only | elevation >= 1 m | No source defines land by an elevation of 1 m; land masks are normally a separate product. Lowland land below sea level exists on Earth (no quote collected this session). | No official source found (design choice) | Below-sea-level land (e.g. depressions) would be dropped; lunar cells have no sea level, so the rule must not be applied to lunar elevations relative to a datum without checking sign conventions. |
| Common: mask fraction | >= 0.3 | None | Design choice | Cannot be confirmed; affects coastal and mixed cells only. |
| Solar: irradiance | >= 2.5 (unit not stated) | Unit inference: kWh/m2/day is the unit of US federal and global GHI products (F19, F20); BLM's former high-resource cut was 6.5 kWh/m2/day (F19). In W/m2 a value of 2.5 would be meaningless; in MJ/m2/day it equals 0.69 kWh/m2/day and passes almost everything. Moon: 1361 W/m2 (F1). | Unit: **inference**, consistent. Value: design choice; no official global minimum found. | Applied to **lunar polar cells** on a horizontal surface the gate removes them all (D3 = 0.88 < 2.5). Equatorial lunar cells pass easily (D4). Must state whether lunar irradiance is horizontal, panel-normal, or time-averaged. |
| Solar: irradiance (old) | >= 1.8 | as above | Design choice | Also removes lunar poles (0.88 < 1.8). |
| Solar: slope | <= 15 deg | Federal 2012 exclusion: slope > 5 % (2.9 deg) (F19). Best-lit lunar polar sites have slopes 8.4 to 17.1 deg (F9). | **Contradicted** as an Earth solar-siting value (15 deg is about 5x the federal limit); plausible for a small lunar array on rim terrain. | Admits many Earth cells that no utility planner would accept; consistent with lunar rim terrain. Label it a mission choice, not an engineering standard. |
| Solar: max solar elevation | >= 10 deg | Lunar max Sun elevation at the poles is 1.54 deg (F5); tilt 1.54 deg (F4) or about 1.5 deg (F6). | **Contradicted for lunar poles**: physics makes the gate fail every lunar cell above about 81.5 deg (D1). On Earth it removes nothing if computed as a yearly maximum (D2). | **Every lunar polar site, including the Artemis III candidate regions "near the lunar South Pole" (NASA, 28 Oct 2024: https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/, quote: "identified an updated set of nine potential landing regions near the lunar South Pole"), is removed by this gate.** This is the suspected concept error. The polar advantage is near-continuous light at low Sun angle (F8), which this gate punishes. |
| Solar: max solar elevation (old) | >= 5 deg | same | Contradicted for lunar poles (cut-off phi <= 86.5 deg) | Still removes the pole cells within 3.5 deg of each pole. |
| Solar: grazing-sun share | <= 25 % | No definition of "grazing" found. At the lunar poles the Sun is always grazing (F5). | Design choice; contradicts polar physics | Removes all lunar polar cells for any grazing definition above 1.54 deg. |
| Solar: not water | n/a | Definition only | Design choice | none |
| Thermal: daily amplitude | >= 15 K | Earth air: largest 24-h change on record in the US 57.2 K, frontal not diurnal (F15); desert average day 38 deg C vs night -3.9 deg C (F16, weak). Earth LST: no official source found for the global maximum diurnal LST range. Moon: about 295 K at the equator (D6); polar rims nearly constant near 220 K (F12). | Value: design choice. Team's Earth max of 39 K is plausible but **unverified** (no official global maximum of diurnal LST found). | If lunar polar rim cells have amplitude below 15 K they fail this gate. Team says lunar amplitude is 63 to 180 K: the upper value is below the 295 K equatorial figure (D6) and the lower value is above the polar-rim behaviour (F12), so the team's lunar layer is probably smoothed, averaged or latitude-limited. Check. |
| Thermal: "good" end | 35 K | Team: Earth max 39 K vs Moon 63 to 180 K (as reported). | Design choice, defensible | No Earth cell can reach lunar values; scoring is relative, so state this on the globe legend. |
| Thermal: minimum temperature | <= 5 deg C | Air vs LST must be stated: NASA notes air is measured "1.5 to 2 meters above the ground" (F14). | Design choice | Behaviour depends on whether the layer is air or LST; mixing them invalidates comparison with lunar surface temperatures (which are surface, F10 to F13). |
| Rover: slope | <= 15 deg | LRV designed for 20 to 23 deg, max 25 deg (F21); driven up to 20 deg; cross-slope roll instability near 15 deg (F22). | **Supported** (conservative relative to the LRV) | Reasonable; note it is below the LRV design maximum. |
| Rover: roughness (old) | 5 to 650 m | None found; unit "m" of roughness needs a definition (std of elevation? over which window?). | Design choice | Cannot be confirmed. |
| Rover: slope (old) | >= 0.5 deg | None | Design choice | Removes flat terrain, which is unusual for a rover gate; ask why. |
| Ice: permafrost present | presence | Permafrost = ground at or below 0 deg C for at least 2 consecutive years (F17, F18). Temperature-based, not ice-based. | Supported as a concept | The layer must use this definition (e.g. a permafrost zonation product), not "ground ice" or "snow". On the Moon the analogous quantity is cold-trap temperature (PSRs as low as 25 K, F13); permafrost has no lunar equivalent by definition. |
| Weights (all missions) | as listed in the brief | None | Pure design choices | Should be shown as adjustable, with a sensitivity check. |

## 4. Consequence in one paragraph

If the same hard filters run on lunar cells, the solar-panel mission will contain **no lunar polar sites at all**, for three independent reasons: maximum solar elevation >= 10 deg (D1), grazing share <= 25 % (F5), and, if irradiance is horizontal, irradiance >= 2.5 (D3). The lunar south pole is where NASA plans to land (Artemis III regions) and where the best illumination exists (F8). Unless the team intends this, the solar gates must be re-expressed for the Moon (illumination fraction and panel-normal irradiance rather than Sun height and horizontal irradiance).

## Verification log

| Opened | Result |
|---|---|
| power.larc.nasa.gov/docs/faqs/solar/ and /llms.txt (WebFetch) | Read; no unit or range statements. Then read robots.txt: it disallows `anthropic-ai` and `Claude-Web`. **Stopped using this host** to respect robots.txt. No API call made. |
| power.larc.nasa.gov/docs/methodology/energy-fluxes/ and /parameters/ | 404 and JavaScript-only respectively |
| gis.earthdata.nasa.gov POWER ImageServer metadata | 404 |
| docs.nrel.gov, www.nrel.gov, developer.nrel.gov | Hosts not reachable from this session (network allowlist). NREL slope criteria (3 %, 5 %, 10 %) seen only in search snippets, **not used** |
| blmsolar.anl.gov exclusion page | 403. Used the Federal Register notice on energy.gov instead (F19) |
| nssdc.gsfc.nasa.gov Moon and Earth fact sheets | OK (F1 to F3, F7, F10) |
| ntrs.nasa.gov Gläser et al. PDF | OK via pdftotext (F4, F5, F8, F9); saved under scratchpad/stars/r3_ntrs/ |
| ntrs.nasa.gov 20170003782 (Fisher et al. 2017) | OK; no diurnal-amplitude statement usable here |
| svs.gsfc.nasa.gov/5229, diviner.ucla.edu/science | OK (F6, F11 to F13) |
| science.nasa.gov hottest-spot article; NASA kids desert page | OK (F14, F16) |
| repository.library.noaa.gov/view/noaa/27287 (MODIS LST diurnal cycle) | Abstract has no regional magnitudes |
| ncei.noaa.gov Loma record PDF | OK (F15) |
| pubs.usgs.gov permafrost PDF | WebFetch 403; curl OK (F17) |
| arctic.noaa.gov permafrost | OK (F18) |
| datacatalog.worldbank.org GHI | OK, unit only (F20) |
| ntrs.nasa.gov 20250011301; nasa.gov ALSJ LRV page | OK (F21, F22) |
| nasa.gov Artemis III regions release; NTRS 20250011660 | OK; neither gives a numeric latitude bound |
| Not found | Official global range of daily surface irradiance on Earth; official maximum diurnal LST range on Earth; any source for mask 0.3, grazing 25 %, 5 deg C, roughness 5 to 650 m |

## Open questions for the team

1. What is the unit of the irradiance layer, and for lunar cells is it horizontal, panel-normal, or averaged over the lunation?
2. Is "maximum solar elevation" a yearly maximum or a single-date value? On the Moon, is it computed with the 1.54 deg tilt (not 6.68 deg, F7)?
3. Is excluding all lunar polar sites from the solar mission intended? If not, which gates should be replaced by an illumination-fraction gate?
4. Is the thermal layer on Earth air temperature or land surface temperature, and which product?
5. How was the lunar amplitude range 63 to 180 K obtained, given 95 to 390 K at the equator and near-constant 220 K at polar rims?
6. How is "grazing sun" defined (angle threshold)?
7. Which permafrost product is used, and does it follow the 0 deg C / two-year definition?
8. What does roughness 5 to 650 m measure, and why the old minimum slope of 0.5 deg?
9. Can the NREL hosts be allowed in the session network so the NREL slope criteria can be quoted directly?
