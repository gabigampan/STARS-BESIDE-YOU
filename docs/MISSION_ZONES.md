# Mission zones: real lunar missions by region, and why each test is searched where it is

Status: **section 4 approved on 2026-11-15 at 08:55 CET by the delegate, on the team lead's behalf, with corrections; the corrections are applied (section "Corrections of 2026-11-15 (after approval)" at the end).** The strings are in `tierra luna/engine/mission_zone_texts.json`. Written 2026-11-15 on branch `final-integration`. All pages below were opened on **2026-11-15** (access date for every row unless stated). Scripts and outputs (read-only on the repository): `scratchpad/stars/zones/scripts/regions.py`, `missions_in.json`; outputs `scratchpad/stars/zones/out/region_stats.json`, `missions_placed.json`, `region_by_cell.npy`. The full scratchpad path is `/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/zones/`.

The three zones are fixed by the team and are **not** changed here:

| Mission | Zone (as fixed by the team) | Rule on the 1-degree lunar table |
|---|---|---|
| Rover | South-pole zone | cell-centre latitude <= -75 |
| Solar panels | Equatorial maria | abs(latitude) <= 30 and `elevation_m` <= -1,200 m (relative to the 1,737.4 km sphere), as `engine/real_similarity.py` `zone_mask_real` (`abs_lat_max_elevation_max`) |
| Lunar base | The nine candidate landing regions NASA announced on 2024-10-28 | the 280 one-degree cells that the USGS navigational grids of the nine regions intersect (`proposal-verify/out/regions.json`, key `cells["1"]["intersects"]`; an upper bound of each region, see SIMILARITY_PROPOSAL sec. 1) |

## Sources (all opened 2026-11-15)

| Id | Page | Publisher, date shown on the page |
|---|---|---|
| S1 | https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_artifact_impacts.html "Table of Anthropogenic Impacts and Spacecraft on the Moon" | NASA NSSDCA (D. R. Williams), "Last Updated: 13 August 2025". Coordinates "based on DE 421 mean Earth/polar rotation axis reference frame"; columns "Latitude, Longitude (N, E Positive)" with longitude 0-360 E |
| S2 | https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html "Apollo Landing Site Coordinates" | NASA NSSDCA, "Last updated 06 March 2017"; "planetocentric Mean Earth/Polar Axis ... DE421" |
| S3 | https://nssdc.gsfc.nasa.gov/planetary/lunar/lunartimeline.html "Lunar Exploration Timeline" | NASA NSSDCA, "Last Updated: 10 July 2025" |
| S4 | https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=PRIME-1 (IM-2) | NASA NSSDCA Master Catalog |
| S5 | https://science.nasa.gov/lunar-discovery/deliveries/ "CLPS deliveries" | NASA Science, last updated Oct 23, 2026 |
| S6 | https://www.nasa.gov/news-release/nasa-provides-update-on-moon-base-rovers-landers-missions/ | NASA RELEASE26-046, May 26, 2026 (updated May 27); Spanish version https://www.nasa.gov/news-release/la-nasa-ofrece-informacion-actualizada-sobre-rovers-modulos-de-alunizaje-y-misiones-de-base-lunar/ |
| S7 | https://www.nasa.gov/moonbase-phases/ "Moon Base Phases" | NASA, last updated Nov 12, 2026 |
| S8 | https://www.nasa.gov/event/clps-flight-blue-origins-blue-moon-mark-1/ | NASA event page, last updated Oct 21, 2026 |
| S9 | https://www.nasa.gov/event/clps-flight-astrobotics-griffin-mission-one/ | NASA event page, last updated Oct 14, 2026 |
| S10 | https://www.nasa.gov/missions/moon-base/nasa-provides-updates-on-moon-base-cargo-landers-tech-demonstrations/ | NASA, Aug 04, 2026 (updated Aug 05) |
| S11 | https://www.nasa.gov/event/clps-flight-firefly-aerospaces-blue-ghost-mission-2/ (NASA, updated Oct 21, 2026) and https://fireflyspace.com/blue-ghost-mission-2 (operator) | |
| S12 | https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=IM-3-NOVA | NASA NSSDCA |
| S13 | https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=TO-CP-22 (IM-4) | NASA NSSDCA |
| S14 | https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=DRAPER (CP-12) and id=BLUEGHOS2 | NASA NSSDCA |
| S15 | https://science.nasa.gov/mission/viper/ (updated Sep 21, 2026) and https://www.nasa.gov/news-release/nasa-selects-blue-origin-to-deliver-viper-rover-to-moons-south-pole/ (RELEASE25-064, Sep 19, 2025) | NASA |
| S16 | https://www.nasa.gov/mission/artemis-iv/ (updated Mar 16, 2026); https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/ (RELEASE24-136, Oct 28, 2024) | NASA |
| S17 | https://www.cnsa.gov.cn/n6758823/n6758838/c10770822/content.html (CNSA, 2026-08-23); https://english.news.cn/20250204/e84da1b627ed46ebb9d0d81a88ce3ca1/c.html (Xinhua, 2025-02-04); https://english.www.gov.cn/news/202605/23/content_WS6a118ca1c6d00ca5f9a0b33c.html (gov.cn, 2026-05-23) | Chang'e 7 |
| S18 | https://www.cnsa.gov.cn/english/n6465652/n6465653/c10670293/content.html | CNSA (Xinhua), 2025-04-25: Chang'e 8 |
| S19 | https://www.cnsa.gov.cn/english/n6465652/n6465653/c10541840/content.html | CNSA (Xinhua), 2024-06-02: Chang'e 6 landing |
| S20 | https://www.pib.gov.in/PressReleasePage.aspx?PRID=2202454&reg=48&lang=2 (PIB, Department of Space, 11 Dec 2025); https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/jun/doc2026621898801.pdf (PIB, 21 June 2026); https://www.isro.gov.in/ISRO_JAXA_CH5_Technical_Interface_Meet.html (ISRO, May 15, 2025) | Chandrayaan-4, Chandrayaan-5/LUPEX |
| S21 | https://www.isro.gov.in/Chandrayaan3RAMBHALP_GroundTruth.html | ISRO, Dec 09, 2025 |
| S22 | https://www.isas.jaxa.jp/en/topics/files/SLIM-press-briefing-20241226.pdf | JAXA/ISAS, 2024-12-26 |
| S23 | https://www.nasa.gov/history/50-years-ago-lunar-landing-sites-selected/ | NASA History, Feb 08, 2018 (updated Aug 22, 2024) |
| S24 | https://www.nasa.gov/wp-content/uploads/2023/03/sp-4214.pdf (Compton, *Where No Man Has Gone Before*, NASA SP-4214; history.nasa.gov/SP-4214/ redirects here) | NASA |
| S25 | https://science.nasa.gov/photojournal/south-pole-illumination-map (PIA13720) | NASA |
| S26 | https://www.nasa.gov/missions/artemis/new-maps-help-developers-plan-lunar-road-trip-for-vipers-artemis-mission/ | NASA, Jul 15, 2021 |
| S27 | https://science.nasa.gov/wp-content/uploads/2024/01/lrolitho7temperaturevariation27may2014.pdf (LRO lithograph) | NASA |
| S28 | IAU/USGS Gazetteer, local extract `tierra luna/engine/data/iau_moon_nomenclature.csv` (source in `iau_source.json`, downloaded 2026-11-14) | used only for feature centres of planned targets |
| S29 | https://www.nasa.gov/moonbase/ "Moon Base" | NASA, last updated Nov 12, 2026 |
| S30 | https://www.nasa.gov/news-release/nasa-adds-mission-to-artemis-lunar-program-updates-architecture/ | NASA RELEASE26-022, Feb 27, 2026 (added by the fact check) |
| S31 | https://www.nasa.gov/blogs/missions/2026/10/23/nasa-shares-artemis-acceleration-plans-for-moon-missions/ | NASA blog, Oct 23, 2026 (added by the fact check) |
| S32 | https://www.nasa.gov/news-release/nasa-awards-moon-base-transportation-technology-science-projects/ | NASA RELEASE26-095, Nov 7, 2026 (added by the fact check) |
| S33 | https://www.ispace-inc.com/2026/03/27/ispace-announces-new-ultra-lunar-lander-integrating-japanese-and-u-s-lander-models/ (Mar 27, 2026) and https://www.ispace-inc.com/2026/11/13/ispace-completes-preliminary-design-review-pdrfor-the-mission-3-ultra-lander/ (Nov 13, 2026) | ispace (operator) (added by the fact check) |
| S34 | https://iki.cosmos.ru/research/missions/luna-27 | IKI RAS (lead scientific organisation; lead agency Roscosmos), no page date (latest news item 29 Oct 2024) (added by the fact check) |
| S35 | https://www.nasa.gov/mission/artemis-iii/ "Artemis III" | NASA, last updated Oct 19, 2026: "Mission Type: Crewed Demonstration", launch "2027", "will carry out a series of objectives in low Earth orbit", "before Americans return to the Moon on Artemis IV" (added 2026-11-15 after approval) |
| S36 | https://www.ispace-inc.com/mission-2/ (no page date; "Success 9 Completion of lunar landing: NOT COMPLETED") and https://www.ispace-inc.com/2025/06/24/ispace-releases-technical-cause-analysis-for-hakuto-r-mission-2/ (06.24.2025: "the technical cause of the hard landing was an anomaly in the LRF hardware"; attempt "on June 6, 2025" JST) | ispace (operator) (added 2026-11-15 after approval) |
| S37 | https://www.nasa.gov/news-release/nasa-receives-some-data-before-intuitive-machines-ends-lunar-mission/ (RELEASE25-025, Mar 07, 2025: "an early end of mission"; lander "on its side"; the "Nova-C Hopper" "only able to complete some objectives") and https://www.lunaroutpost.com/post/lunar-voyage-1-update (Lunar Outpost, operator of the MAPP rover, Mar 7, 2025: garage wedged under the lander, "preventing MAPP's deployment to the lunar surface") | NASA; Lunar Outpost (added 2026-11-15 after approval) |
| S38 | https://www.cnsa.gov.cn/n6758823/n6758838/index.html (CNSA news list, newest item 2026-11-09, no Chang'e or lunar-landing headline from 2026-10-09 to 2026-11-09) | CNSA (added 2026-11-15 after approval) |
| S39 | https://www.esa.int/Science_Exploration/Human_and_Robotic_Exploration/Exploration/Argonaut_Europe_s_lunar_lander_programme | ESA, cards dated 12 Oct 2026: "Argonaut Mission 1 will launch on a four-booster Ariane 6 rocket by the end of 2030"; aim "to transport cargo to and safely land on the Moon's south polar region" (added 2026-11-15 after approval) |
| S40 | https://www.kasa.go.kr/prog/bbsArticle/BBSMSTR_000000000041/view.do?bbsId=BBSMSTR_000000000041&nttId=B000000001474Ho4eE5 | KASA (Korea AeroSpace Administration), 2025-01-22: "a lunar lander for an independent lunar landing mission by 2032"; no site (added 2026-11-15 after approval) |
| S41 | https://dymon.co.jp/news/20260727_bs11-next-company/ | Dymon (operator of the Yaoki rover carried by IM-2), 2026-07-27: "月面探査車「YAOKI」が月面で撮影した世界初のクレーター内部画像" (the world's first image of a crater interior, taken by the lunar rover YAOKI on the lunar surface); nothing about driving (added by the second fact check, 2026-11-15) |

Coordinate handling: S1 gives each site twice, as "7.13 N, 64.37 W" and as "7.13, 295.63" (N, E positive, 0-360). The tables below give planetocentric latitude and east-positive longitude in -180..180, converted from S1's 0-360 column by subtracting 360 when the value exceeds 180 (e.g. Luna 9: 295.63 - 360 = -64.37, which matches S1's "64.37 W"). The IAU extract is 0-360 E and is converted the same way. Zone and region membership is computed for the 1-degree cell that contains the point (row = floor(90 - lat), col = floor(lon + 180), cell = row x 360 + col); the elevation quoted is that cell's `elevation_m` in `tierra luna/output_real/moon_real_1deg.csv`.

## 2. Regions the web can refer to

Six regions, applied in this order, so that each of the 64,800 one-degree cells falls in exactly one (checked by script: no cell unassigned, no overlap):

| Code | Region (web label) | Rule (cell centre) | Cells | Share of lunar area | Zone(s) it belongs to |
|---|---|---|---|---|---|
| A | The nine NASA candidate regions | cell in the 280-cell footprint of the nine regions (all lie at or below -75) | 280 | 0.05 % | Rover, Lunar base |
| B | South-polar region outside the nine NASA regions | lat <= -75, not A | 5,120 | 1.66 % | Rover |
| C | North-polar region | lat >= 75 | 5,400 | 1.70 % | none |
| D | Low equatorial plains (the maria) | abs(lat) <= 30 and elevation <= -1,200 m. This is exactly the Solar panels zone; 1,029 of its cells are on the far side (abs(lon) > 90) | 6,686 | 15.41 % | Solar panels |
| E | Far side | abs(lon) > 90 and -75 < lat < 75, not D | 25,971 | 45.98 % | none |
| F | Near-side highlands and mid-latitudes (includes the northern maria beyond 30 degrees) | abs(lon) <= 90 and -75 < lat < 75, not D | 21,343 | 35.21 % | none |

"Near side" and "far side" are split at 90 degrees of longitude; libration makes the real visible edge a few degrees wider, so cells near the limb are a simplification.

### Regional figures from the project's lunar table (computed today)

Area-weighted (cos latitude) medians over each region's cells; `tierra luna/output_real/moon_real_1deg.csv`. Levels from `docs/REAL_DATA.md`: `irradiance_kwh_m2_day` DERIVED (S0 1,361 W/m2, horizontal surface, per 24 h, with LOLA topographic illumination at the poles); `illum_frac` DERIVED (LOLA AVGVISIB ray-traced simulation at abs(lat) >= 65.5, flat-ground geometry elsewhere), a **cell average**, not the best ridge in the cell; `tmax_k`, `tmin_k` MEASURED (Diviner); `slope_deg` DERIVED (LDEM_16, 3.79 km baseline).

| Region | Irradiance, kWh/m2/day (median; p10-p90) | Illuminated fraction (median) | Day max T, K (median) | Night min T, K (median) | Slope, deg (median) |
|---|---|---|---|---|---|
| A nine NASA regions | 0.53 (0.17-0.89) | 0.31 | 243 | 62 | 10.6 |
| B south-polar, other | 1.32 (0.39-2.04) | 0.36 | 259 | 64 | 6.8 |
| C north-polar | 1.38 (0.39-2.06) | 0.36 | 256 | 65 | 5.7 |
| D low equatorial plains | 10.02 (9.22-10.38) | 0.50 | 388 | 94 | 1.1 |
| E far side | 8.96 (5.12-10.35) | 0.50 | 374 | 91 | 6.2 |
| F near-side highlands, mid-lat | 8.25 (4.64-10.28) | 0.50 | 364 | 90 | 3.9 |

Reading: at 1-degree scale the polar cells get **less** sunlight on level ground than the equator (horizontal irradiance about one tenth). NASA's "sunlit most of the year" statements (S25, S26) are about specific peaks and rims, a few hundred metres across, that a 1-degree cell average does not show. The web text must not say the polar regions are "sunnier" in general.

## 1. Landed, failed and planned missions

Outcome words are the source's own ("Soft Landing", "Lander", "Crewed Landing", "Rover", "Impact"). Columns "Region" and "Zone" are computed as above. All S1 rows: quote = the row as printed ("date | lat, lon (N, E positive)"), access 2026-11-15.

### 1a. Successful soft and crewed landings (28 sites; S1 type "Soft Landing", "Lander" or "Crewed Landing")

| Mission | Agency / operator | Country | Type | Date (UTC) | Site (where the source names it) | Lat, lon (E, -180..180) | Cell, elevation | Region | Zone | Source and quote |
|---|---|---|---|---|---|---|---|---|---|---|
| Luna 9 | USSR | USSR | robotic lander | 1966-02-03 | Oceanus Procellarum area (not named in S1) | 7.13, -64.37 | M29635, -1,566 m | D | Solar | S1 "3 February 1966 / 7.13, 295.63"; S1 note f: lander "probably at least 10 km away" from these coordinates (see Disagreements) |
| Surveyor 1 | NASA | USA | robotic lander | 1966-06-02 | - | -2.4745, -43.3398 | M33256, -1,887 m | D | Solar | S1 "2 June 1966 / -2.4745, 316.6602" |
| Luna 13 | USSR | USSR | robotic lander | 1966-12-24 | - | 18.87, -62.05 | M25677, -2,142 m | D | Solar | S1 "24 December 1966 / 18.87, 297.95" |
| Surveyor 3 | NASA | USA | robotic lander | 1967-04-20 | - | -3.0162, -23.4180 | M33636, -1,494 m | D | Solar | S1 "20 April 1967 / -3.0162, 336.5820" |
| Surveyor 5 | NASA | USA | robotic lander | 1967-09-11 | - | 1.4551, 23.1943 | M31883, -2,065 m | D | Solar | S1 "11 September 1967 / 1.4551, 23.1943" |
| Surveyor 6 | NASA | USA | robotic lander | 1967-11-10 | - | 0.4742, -1.4275 | M32218, -817 m | F | none | S1 "10 November 1967 / 0.4742, 358.5725" |
| Surveyor 7 | NASA | USA | robotic lander | 1968-01-10 | - | -40.9812, -11.5127 | M46968, +129 m | F | none | S1 "10 January 1968 / -40.9812, 348.4873" |
| Apollo 11 | NASA | USA | crewed landing | 1969-07-20 | - | 0.67416, 23.47314 | M32243, -1,879 m | D | Solar | S1 "20 July 1969 / 0.67416, 23.47314"; S2 LM "0.67416 / 23.47314" |
| Apollo 12 | NASA | USA | crewed landing | 1969-11-19 | - | -3.0128, -23.4219 | M33636, -1,494 m | D | Solar | S1 "19 November 1969 / -3.0128, 336.5781"; S2 LM "-3.0128 / -23.4219" |
| Luna 16 | USSR | USSR | sample return | 1970-09-20 | - | -0.5137, 56.3638 | M32636, -2,414 m | D | Solar | S1 "20 September 1970 / -0.5137, 56.3638" |
| Luna 17 / Lunokhod 1 | USSR | USSR | rover | 1970-11-17 | - | lander 38.23764, -35.00163; rover 38.3150, -35.0081 | M18504, -2,473 m | F | none | S1 "17 November 1970 / 38.23764, 324.99837"; Lunokhod 1 "38.3150, 324.9919" (same cell) |
| Apollo 14 | NASA | USA | crewed landing | 1971-02-05 | - | -3.64589, -17.47194 | M33642, -1,056 m | F | none | S1 "5 February 1971 / -3.64589, 342.52806"; S2 LM "-3.64589 / -17.47194" |
| Apollo 15 | NASA | USA | crewed landing | 1971-07-30 | - | 26.13239, 3.63330 | M22863, -1,724 m | D | Solar | S1 "30 July 1971 / 26.13239, 3.63330" |
| Luna 20 | USSR | USSR | sample return | 1972-02-21 | - | 3.7863, 56.6242 | M31196, -1,835 m | D | Solar | S1 "21 February 1972 / 3.7863, 56.6242" |
| Apollo 16 | NASA | USA | crewed landing | 1972-04-21 | - | -8.9734, 15.5011 | M35475, +225 m | F | none | S1 "21 April 1972 / -8.9734, 15.5011" |
| Apollo 17 | NASA | USA | crewed landing | 1972-12-11 | - | 20.1911, 30.7723 | M25050, -1,958 m | D | Solar | S1 "11 December 1972 / 20.1911, 30.7723" |
| Luna 21 / Lunokhod 2 | USSR | USSR | rover | 1973-01-15 | - | lander 25.9994, 30.4076; rover 25.8323, 30.9222 | M23250, -2,078 m | D | Solar | S1 "15 January 1973 / 25.9994, 30.4076"; Lunokhod 2 "25.8323, 30.9222" (same cell) |
| Luna 23 | USSR | USSR | robotic lander | 1974-11-06 | - | 12.6667, 62.1511 | M27962, -3,526 m | D | Solar | S1 "Soft Landing / 6 November 1974 / 12.6667, 62.1511" (S1 gives no outcome beyond "Soft Landing") |
| Luna 24 | USSR | USSR | sample return | 1976-08-18 | - | 12.7142, 62.2129 | M27962, -3,526 m | D | Solar | S1 "18 August 1976 / 12.7142, 62.2129" |
| Chang'e 3 / Yutu | CNSA | China | lander + rover | 2013-12-14 | - | 44.1214, -19.5117 | M16360, -2,683 m | F | none | S1 "14 December 2013 / 44.1214, 340.4883" |
| Chang'e 4 / Yutu 2 | CNSA | China | far-side lander + rover | 2019-01-03 | - | -45.4561, 177.5885 | M48957, -5,925 m | E | none | S1 "3 January 2019 / -45.4561, 177.5885"; note z: Yutu 2 "still mobile as of January 2023" |
| Chang'e 5 | CNSA | China | sample return | 2020-12-01 | - | 43.0576, -51.9161 | M16688, -2,561 m | F | none | S1 "1 December 2020 / 43.0576, 308.0839" |
| Chandrayaan-3 (Vikram + Pragyan) | ISRO | India | lander + rover | 2023-08-23 | Shiv Shakti point | -69.3741, 32.32 | M57452, +575 m | F | none | S1 "23 August 2023 / -69.3741, 32.32"; S21 "named as Shiv Shakti point (69.3° S, 32.3° E)" (same cell) |
| SLIM | JAXA | Japan | robotic lander | 2024-01-19 | - | -13.3160, 25.2510 | M37285, -213 m | F | none | S1 "19 January 2024 / -13.3160, 25.2510"; S22 "Landing site estimated by NASA LRO team: (13.3160°S, 25.2510°E) (ME coordinates)" |
| IM-1 Odysseus | Intuitive Machines (NASA CLPS TO2-IM) | USA | robotic lander | 2024-02-22 | Malapert A | -80.13, 1.44 | M61381, +2,563 m | B | Rover | S1 "22 February 2024 / -80.13, 1.44"; S5 "Malapert A", "It landed on February 22, 2024." |
| Chang'e 6 | CNSA | China | far-side sample return | 2024-06-01 UTC (2 June, 6:23 Beijing time) | Apollo Basin (in South Pole-Aitken Basin) | -41.6385, -153.9852 | M47186, -5,218 m | E | none | S1 "1 June 2024 / -41.6385, 206.0148"; S19 "successfully landed at the designated landing area at 6:23 a.m. (Beijing Time)", "an impact crater known as the Apollo Basin" |
| Blue Ghost 1 | Firefly (NASA CLPS TO19D) | USA | robotic lander | 2025-03-02 | Mare Crisium | 18.562, 61.810 | M25801, -3,616 m | D | Solar | S1 "2 March 2025 / 18.562, 61.810"; S5 "Mare Crisium", "delivered 10 NASA CLPS science payloads" |
| IM-2 Athena | Intuitive Machines (NASA CLPS PRIME-1) | USA | robotic lander (came to rest on its side) | 2025-03-06 | Mons Mouton plateau | -84.7906, 29.1957 | M62849, +5,032 m | A (Mons Mouton Plateau footprint) | Rover, Lunar base | S1 "6 March 2025 / -84.7906, 29.1957"; S4 "touched down on March 6 ... at the Mons Mouton plateau close to the south pole. Landing coordinates were 84.7906 S, 29.1957 E", "the lander was resting on its side" |

### 1b. Failed landing attempts (S1 type "Impact" for a lander)

| Mission | Agency / operator | Country | Date | Lat, lon | Cell, elevation | Region | Zone | Source and quote |
|---|---|---|---|---|---|---|---|---|
| Luna 5 | USSR | USSR | 1965-05-12 | -1.35, -25.48 | M32914, -1,092 m | F | none | S1 "12 May 1965 / -1.35, 334.52"; note e lists other sites (see Disagreements) |
| Luna 7 | USSR | USSR | 1965-10-07 | 9, -49 | M29291, -1,389 m | D | Solar | S1 "7 October 1965 / 9., 311." |
| Luna 8 | USSR | USSR | 1965-12-06 | 9.1, -63.3 | M28916, -1,732 m | D | Solar | S1 "6 December 1965 / 9.1, 296.7" |
| Surveyor 2 | NASA | USA | 1966-09-22 | 5.5, -12.0 | M30408, -1,124 m | F | none | S1 "22 September 1966 / 5.5, 348.0" |
| Surveyor 4 | NASA | USA | 1967-07-17 | about 0.5, -1.5 | M32218, -817 m | F | none | S1 "Impact (?) / Unknown (0.5, 358.5)"; "contact lost 2.5 minutes before landing" |
| Luna 15 | USSR | USSR | 1969-07-21 | 17, 60 | M26520, -3,580 m | D | Solar | S1 "21 July 1969 / 17., 60."; note c1 "also given as 12 N, 59 E or 17 N, 49 E" |
| Luna 18 | USSR | USSR | 1971-09-11 | 3.76, 56.66 | M31196, -1,835 m | D | Solar | S1 "11 September 1971 / 3.76, 56.66"; note n "Unconfirmed, contact lost ... during landing phase" |
| Beresheet | SpaceIL / IAI | Israel | 2019-04-11 | 32.5956, 19.3496 | M20719, -2,577 m | F | none | S1 "11 April 2019 / 32.5956, 19.3496" |
| Chandrayaan-2 Vikram | ISRO | India | 2019-09-06 | -70.8810, 22.7840 | M57802, +860 m | F | none | S1 "Vikram / Impact / 6 September 2019 / -70.8810, 22.7840" |
| Hakuto-R Mission 1 | ispace | Japan | 2023-04-25 | 47.581, 44.094 | M15344, -2,848 m | F | none | S1 "25 April 2023 / 47.581, 44.094" |
| Luna 25 | Roscosmos | Russia | 2023-08-19 | -57.865, 61.360 | M53161, -715 m | F | none | S1 "19 August 2023 / -57.865, 61.360" |
| Hakuto-R Mission 2 (Resilience) | ispace | Japan | 2025-06-05 UTC (6 June JST) | 60.4445, -4.588 (Mare Frigoris) | M10615, -2,480 m | F | none | S1 "5 June 2025 / 60.4445, 355.412"; S36 (re-checked 2026-11-15): landing milestone "NOT COMPLETED", "the technical cause of the hard landing was an anomaly in the LRF hardware" |
| Peregrine Mission 1 | Astrobotic (NASA CLPS TO2-AB) | USA | launched 2024-01-08 | target Sinus Viscositatis; no lunar arrival | - | - | - | S5 "launched on January 8, 2024", "It did not land." |

### 1c. Deliberate impacts and end-of-mission impacts (S1 type "Impact", orbiters and impactors)

Only these matter for the polar regions: Lunar Prospector, the Chandrayaan-1 Moon Impact Probe and LCROSS in B, and GRAIL A/B in C. The others are listed for completeness. S1 also lists Apollo S-IVB and LM ascent-stage impacts (all on the near side, within about 27 degrees of the equator) and objects of unknown impact site; they are not repeated here. The fact check added three S1 rows with coordinates that the draft had left out (Apollo 16 subsatellite, Chang'e 5-T1 booster, Chang'e 5 ascent craft).

| Object | Date | Lat, lon | Region | Zone | S1 quote / note |
|---|---|---|---|---|---|
| Luna 2 | 1959-09-13 | 30, 0 | D | Solar | "30., 0."; note a: "typically given as within the range of 29 - 31 N, 1 W to 1 E" |
| Ranger 4 | 1962-04-26 | -15.5, -130.7 | E | none | "-15.5, 229.3" |
| Ranger 6 / 7 / 8 / 9 | 1964-1965 | 9.3864, 21.4806 / -10.6340, -20.6770 / 2.6376, 24.7881 / -12.8281, -2.3884 | D (all four) | Solar | "9.3864, 21.4806"; "-10.6340, 339.3230"; "2.6376, 24.7881"; "-12.8281, 357.6116" |
| Lunar Orbiter 1 / 2 / 3 / 5 | 1966-1968 | 6.35, 160.71 / 3.0, 119.1 / 14.3, -92.7 / -2.79, -83.04 | E / E / E / F | none | "6.35, 160.71"; "3.0, 119.1"; "14.3, 267.3"; "-2.79, 276.96" |
| Hiten (JAXA/ISAS) | 1993-04-10 | -34.0, 55.3 | F | none | "-34.0, 55.3" |
| Lunar Prospector (NASA) | 1999-07-31 | -87.7, 42.0 | B | Rover | "31 July 1999 / -87.7, 42.0" |
| SMART-1 (ESA) | 2006-09-03 | -34.4, -46.2 | F | none | "-34.4, 313.8" |
| Chandrayaan-1 Moon Impact Probe (ISRO) | 2008-11-14 | about -89, -30 | B | Rover | "-89., 330."; note t: "Impacted in Shackleton crater near south pole, exact coordinates unknown" |
| Okina (JAXA Kaguya subsatellite) | 2009-02-12 | 28.213, -159.033 | E | none | "28.213, 200.967" |
| Chang'e 1 (CNSA) | 2009-03-01 | -1.50, 52.36 | D | Solar | "-1.50, 52.36" |
| Kaguya / SELENE (JAXA) | 2009-06-10 | -65.5, 80.4 | F | none | "-65.5, 80.4" |
| LCROSS Centaur and shepherding spacecraft (NASA) | 2009-10-09 | -84.6796, -48.7093 and -84.719, -49.61 | B | Rover | "-84.6796, 311.2907"; "-84.719, 310.39"; note y "impacted in permanently shadowed Cabeus crater" |
| GRAIL A and B (NASA) | 2012-12-17 | 75.6088, -26.5940 and 75.6508, -26.8341 | C | none | "75.6088, 333.4060"; "75.6508, 333.1659" |
| LADEE (NASA) | 2014-04-18 | 11.8494, -93.2494 | E | none | "11.8494, 266.7506" |
| Longjiang 2 (China) | 2019-07-31 | 16.6956, 159.5170 | D (a far-side low-plains cell) | Solar | "16.6956, 159.5170" |
| Apollo 16 subsatellite (NASA) | 1972-05-29 | 10.16, 111.9 | E | none | "29 May 1972 / 10.16, 111.9" (added by the fact check) |
| Chang'e 5 ascent craft (CNSA) | 2020-12-07 | -30, 0 (note aa: most probable site Regiomontanus, -0.21, -29.84 as printed) | F (cell M43380, +843 m) | none | "7 December 2020 / -30., 0."; note aa "intentionally crashed after returning samples to orbiter" (added by the fact check) |
| Chang'e 5-T1 booster (probable) | 2022-03-04 | 5.226, -125.514 | E | none | "5.226, 234.486"; note bb "considered most likely to be the booster stage of the Chang'e 5-T1" (added by the fact check) |

### 1d. Planned missions (status as of 2026-11-15)

Planned sites are given by feature name only on the official pages; none gives landing coordinates. Where a feature centre is used to place it in a region, it is the IAU gazetteer centre (S28), **not a landing point**, and the region is marked "(centre)".

| Mission | Agency / operator | Country | Type | Target date (as stated) | Site (as stated) | Feature centre used (IAU, converted) | Region | Zone | Source and quote |
|---|---|---|---|---|---|---|---|---|---|
| Artemis IV | NASA | USA | crewed landing | "Early 2028" | "near the South Pole of the Moon"; "nine candidate landing regions near the lunar South Pole" | - | A | Rover, Lunar base | S16 Artemis IV page: "Mission Type Crewed Surface Landing", "Early 2028" |
| Moon Base I (Blue Moon Mark 1 "Endurance") | Blue Origin for NASA | USA | robotic lander | S6: "Targeted for launch no earlier than fall 2026"; S8 (updated Oct 21, 2026) "When: 2027"; S7 (Nov 12, 2026) future tense, "will attempt a landing on the Shackleton Connecting Ridge" | "Shackleton Connecting Ridge" | Shackleton crater -89.67, 129.78 (the ridge is not an IAU name) | B (centre); site not placed | Rover | S6 "The mission will land on the Shackleton Connecting Ridge"; S8 "2027" |
| Moon Base II (Griffin-1, Astrolab FLIP rover) | Astrobotic / Voyager for NASA | USA | lander + rover | S9 (Oct 14, 2026) "Late 2026"; S10 "plans to launch in late 2026"; S7 (Nov 12, 2026) "ahead of its planned launch to the Moon in late 2026" (not launched) | S9 "the Nobile Crater at the lunar South Pole" | Nobile -85.2752, 53.2725 | B (centre); the Nobile Rim 1 and 2 NASA regions are nearby, so the real site may fall in A | Rover | S9; S5 still lists TO20A Griffin at "Mons Mouton" "in 2025" (see Disagreements) |
| Moon Base III (IM-3, Nova-C "Trinity") | Intuitive Machines for NASA | USA | lander + rovers | S6 "Also targeted for this year" (2026); S10 no date; S7 (Nov 12, 2026) "will become the first mission to land at Reiner Gamma" (future tense); S12 "Launch is currently planned for late 2025 or early 2026" (out of date) | Reiner Gamma | Reiner Gamma 7.3853, -58.9583 | D (centre) | Solar | S7 "Intuitive Machines' IM-3 mission will become the first mission to land at Reiner Gamma"; S12 |
| VIPER | NASA, delivered by Blue Origin (CS-7) | USA | rover | S15 "deliver VIPER to the lunar surface in late 2027"; delivery is a contract option | "Mons Mouton" | Mons Mouton -84.60, 31.00 | A (centre in Mons Mouton Plateau footprint) | Rover, Lunar base | S15 "Mons Mouton, Earth's Moon"; RELEASE25-064 "There is an option on the contract to deliver and safely deploy the rover" |
| IM-4 (CP-22) | Intuitive Machines for NASA | USA | robotic lander | S13 "NET 2027" | "Mons Mouton region" | Mons Mouton -84.60, 31.00 | A (centre) | Rover, Lunar base | S13 "a lander mission to the south pole region of the Moon, currently planned for the Mons Mouton region"; S5 "CP-22 ... Mons Mouton" |
| Blue Ghost Mission 2 (+ LuSEE-Night) | Firefly for NASA | USA | far-side lander | S11 NASA "2027"; Firefly (re-checked 2026-11-15) "Upcoming Mission", "no earlier than 2027" | Firefly: "Moon's Far Side, Nassau Crater" | Nassau -24.9137, 177.3370 | D (centre; a far-side low-plains cell) | Solar | S11; S7 "Planned to be the first American landing on the Moon's far side" |
| Blue Ghost Mission 3 (CP-21) | Firefly for NASA | USA | robotic lander | no date on S5 | "the Gruithuisen Domes" | Mons Gruithuisen Gamma 36.5585, -40.7213 | F (centre) | none | S5 |
| CS-11 (Schrödinger Basin; NSSDCA: Draper CP-12 on ispace APEX 1.0) | NASA CLPS | USA | robotic lander | S14 "touch down ... in 2026"; S5 no date, "Lander to be determined" | "Schrödinger Basin" | Schrödinger -74.7326, 132.9252 | E (centre at -74.7, just outside -75) | none | S5; S14 "Schrödinger basin on the lunar far side" |
| Other CLPS south-pole deliveries: CT-3 (Blue Moon Mark 1), CS-6 (Blue Ghost Mission 4), CT-4 (Nova-D) | NASA CLPS | USA | landers | no dates on S5 | "the lunar South Pole" / "the lunar south pole" | - | A or B (not placed) | Rover | S5 |
| CS-8 (Moon Base payloads) and CX-2 (Lunar Terrain Vehicle delivery) | NASA CLPS | USA | landers | no dates on S5 | "Lunar surface" (no site) | - | not placed | - | S5 (added by the fact check) |
| ispace Mission 3 (ULTRA lander) | ispace | Japan | robotic lander | "scheduled for launch in 2028" (S33, Nov 13, 2026) | no site named | - | not placed | - | S33 (added by the fact check) |
| Luna 27 (Luna-27.1, Luna-27.2) | Roscosmos / NPO Lavochkin / IKI RAS | Russia | robotic landers | "2029 и 2030" "(предполагаемые)" (tentative) | "в районе полюсов Луны", "приполярный район" (near-polar; which pole not stated) | - | not placed | - | S34 (added by the fact check; Luna 26 is an orbiter and is not listed) |
| PROMISE (nuclear-powered rover), MoonFall, Lunar Terrain Vehicles | NASA (Blue Origin delivery for PROMISE and LTVs) | USA | rovers / landers | MoonFall "targeted to arrive at the lunar South Pole in 2028"; LTVs "to the Moon in 2028"; PROMISE: "NASA is targeting late 2028 to launch PROMISE" (S32) | lunar South Pole region; PROMISE "will land at the Moon's South Pole" (S32) | - | A or B (not placed) | Rover | S7; S29 "NASA's PROMISE rover will bring proven Mars rover technology to the lunar South Pole"; S32 |
| Chang'e 7 (orbiter, lander, rover, hopper) | CNSA | China | lander + rover | Launch window missed: "嫦娥七号任务不满足发射条件，不能在今年预定窗口实施" (does not meet launch conditions, cannot be carried out in this year's scheduled window), CNSA 2026-08-23, re-opened 2026-11-15; no new date; no Chang'e headline in the CNSA news list up to 2026-11-09 (S38) | "the moon's south pole"; aims "to confirm the presence and distribution of water ice in permanently shadowed craters" (Xinhua 2025-02-04) | - (no official site) | A or B (not placed) | Rover | S17 |
| Chang'e 8 | CNSA | China | lander + rover + robot | "around 2029" (CNSA 2025); S3 says 2028 | "the Leibnitz-Beta Plateau near the lunar south pole region" | not in the IAU extract; not placed | not placed | - | S18 "scheduled for launch around 2029", "will target the Leibnitz-Beta Plateau near the lunar south pole region" |
| Chandrayaan-4 | ISRO | India | sample return | "2027" | "southern polar region of Moon (~84˚ to 86˚ south latitudes)" | - | A or B | Rover | S20 PIB 11 Dec 2025: "The planned timeline for Chandrayaan-4 mission is 2027. The targeted landing site ... is in the southern polar region of Moon (~84˚ to 86˚ south latitudes)" |
| Chandrayaan-5 / LUPEX | ISRO + JAXA | India, Japan | lander + rover | "Scheduled for launch in 2027–28" (PIB, June 2026) | "in the vicinity of a Permanently Shadowed Region (PSR) in the lunar South pole" | - | A or B (not placed) | Rover | S20 |
| Argonaut Mission 1 | ESA | Europe | cargo lander | "by the end of 2030" | "the Moon's south polar region" (no site) | - | A or B (not placed) | Rover | S39 (added 2026-11-15 after approval) |
| Korean lunar lander | KASA / KARI | South Korea | robotic lander | "by 2032" | not named | - | not placed | - | S40 (added 2026-11-15 after approval) |

No lunar landing or landing attempt after Hakuto-R Mission 2 (5 June 2025 UTC) was found on any official page opened on 2026-11-15: S1 (updated 13 Aug 2025) and S3 (10 Jul 2025) end there; S5 (Oct 23, 2026), S7 (Nov 12, 2026), S8, S9, S11 and S35 describe IM-3, Griffin-1, Blue Moon Mark 1 and Blue Ghost Mission 2 in the future tense; CNSA postponed Chang'e 7 (2026-08-23) and lists no lunar launch up to 2026-11-09 (S38); ESA's Argonaut (2030) and Korea's lander (2032) are later. This is "not found", not a proof of absence. None of the five missions the team lead named (ispace Resilience, Chang'e 7, IM-3, Blue Ghost Mission 2, Griffin-1) adds a landing to our zones: Resilience's hard landing (1b) is in region F, outside every zone, and the other four have not flown.

### Not confirmed on an official page (excluded from the web text)

- **Luna 26 / Luna 27 (Roscosmos)**: the fact check found the IKI RAS mission page (S34): Luna 27 landers "2029 и 2030" (tentative), near-polar, pole not stated; added to 1d as not placed. Luna 26 is an orbiter. TASS (press, not official) gives other dates for Luna 26; not used.
- **Chang'e 7 exact landing site** (press reports name a ridge near Shackleton): not on any CNSA/Xinhua/gov.cn page opened.
- **Chang'e 8 coordinates**: "Leibnitz-Beta Plateau" is not in the IAU extract; no coordinates on CNSA pages.
- **Exact sites and dates** of CT-3, CS-6, CT-4, PROMISE, MoonFall and the LTVs; launch dates of IM-3 and Griffin-1 beyond "2026"/"late 2026".
- **IM-1's final attitude** (widely reported as tipped): no official page opened today states it; only "It landed" (S5).
- **Rovers carried by IM-2** (checked 2026-11-15): the operator of MAPP says it was not deployed (S37, Lunar Outpost); NSSDCA (S4) says IM-2 "carries the Yaoki rover and a small \"hopper\"" but not what became of them, and NASA (S37) says only that the hopper completed "some objectives". Yaoki's operator says Yaoki took an image of a crater interior "on the lunar surface" (S41), without saying whether it moved. So whether any rover has driven beyond 75° S is **not established** on an official page, and a rover was on the surface there; the web text makes no claim either way.
- **ispace Mission 3**: found by the fact check (S33), launch 2028, no site; added to 1d. **ESA Argonaut and the Korean lander**: found on 2026-11-15 (S39, S40), added to 1d, not placed (no site). Other commercial landers: only those on the NASA, operator and agency pages above were checked; none is named in the web text.
- **Apollo communications as a site criterion**: S23 lists free-return, smoothness, slope, lighting; no page opened today states Earth communication as an Apollo criterion, so the web text does not claim it.

### Counts per region (from the tables above)

| Region | Successful soft or crewed landings | of which crewed | Failed landings | Impacts (1c) | Planned (placed by centre or stated region) |
|---|---|---|---|---|---|
| A nine NASA regions | 1 (IM-2) | 0 | 0 | 0 | Artemis IV; VIPER and IM-4 (Mons Mouton centre) |
| B south-polar, other | 1 (IM-1) | 0 | 0 | 4 objects (Lunar Prospector, Chandrayaan-1 MIP, LCROSS x2) | Moon Base I and Griffin-1 by centre; Chang'e 7, Chandrayaan-4, LUPEX, CT-3, CS-6, CT-4, PROMISE, MoonFall, LTVs, Argonaut Mission 1 in A or B |
| C north-polar | 0 | 0 | 0 | 2 (GRAIL A, B) | none found |
| D low equatorial plains | 15 (Luna 9, 13, 16, 20, 21, 23, 24; Surveyor 1, 3, 5; Apollo 11, 12, 15, 17; Blue Ghost 1) | 4 | 4 (Luna 7, 8, 15, 18) | 7 (Luna 2, Ranger 6-9, Chang'e 1, Longjiang 2) | IM-3 (Reiner Gamma), Blue Ghost 2 (Nassau centre) |
| E far side | 2 (Chang'e 4, Chang'e 6) | 0 | 0 | 8 (Ranger 4, Lunar Orbiter 1-3, Okina, LADEE, Apollo 16 subsatellite, Chang'e 5-T1 booster) | CS-11 Schrödinger (centre) |
| F near-side highlands, mid-lat | 9 (Surveyor 6, 7; Apollo 14, 16; Luna 17; Chang'e 3, 5; Chandrayaan-3; SLIM) | 2 | 8 (the last: Hakuto-R Mission 2, 2025) | 5 (Lunar Orbiter 5, Hiten, SMART-1, Kaguya, Chang'e 5 ascent craft) | Blue Ghost 3 (Gruithuisen) |
| Total | 28 | 6 | 12 (+ Peregrine, no arrival) | | |

## Disagreements between sources

| Item | Source 1 | Source 2 | Handling |
|---|---|---|---|
| Luna 9 site | S1 table 7.13 N, 64.37 W | S1 note f (Wagner et al. 2017): "LROC images show no sign of lander at these coordinates ... lander site is probably at least 10 km away, direction unknown" | Kept in D with this caveat; the cell is mare at -1,566 m and neighbouring cells are mare too, so the region is unlikely to change |
| Luna 5 impact | -1.35, -25.48 (F) | note e: 8.17 N 23.43 W (F), 30-31 S 8 W (F), 1.6 S 25 W (D) | Region F or D; not used in web text |
| Luna 15 impact | 17 N, 60 E (D) | note c1: 12 N 59 E (D) or 17 N 49 E (F) | Region D or F; not used in web text |
| Chandrayaan-3 site | S1 -69.3741, 32.32 | S21 ISRO "69.3° S, 32.3° E" | Consistent (ISRO rounded); same cell |
| SLIM site | S1 -13.3160, 25.2510 | S22 JAXA quotes the NASA LRO estimate, identical | Consistent |
| Moon Base I date | S6 "no earlier than fall 2026" | S8 "2027" | Web text gives no date |
| Griffin-1 site | S9 (Oct 2026) "Nobile Crater" | S5 (Oct 2026) TO20A "Mons Mouton", "in 2025" (the old VIPER delivery) | Use S9 (newer, mission-specific); web text does not name it |
| Blue Ghost 2 date | S14 NSSDCA "early 2026" | S11 NASA "2027", Firefly "no earlier than 2027" | Use 2027 |
| CS-11 / Draper | S14 Draper CP-12, ispace APEX 1.0, 2026 | S5 CS-11 "Lander to be determined"; S33 (ispace, Mar 27, 2026): "Mission 5: Lunar Lander launch, 2030 (formerly ispace-U.S. Mission 3)", selected "to carry NASA's CLPS Task Order CP-12 as a member of Team Draper", "the execution of CP-12 under the revised schedule is pending approval by NASA" | Not in web text; the 2026 date of S14 is out of date |
| Chandrayaan-3 region label | Region rule: 69.37 S is region F ("near-side highlands and mid-latitudes") | PIB (S20, June 2026) calls it "Chandrayaan-3's lunar south pole landing" and says it "touched down at 69.3° South latitude" | Region F is a label of this document only; web text gives the latitude (69° S) and never says Chandrayaan-3 was not a south-polar landing |
| Chang'e 7 | S3 "2026" | S17 CNSA: did not meet launch conditions for this year's window | Planned, no date |
| Chang'e 8 | S3 "2028" | S18 CNSA "around 2029" | Use CNSA |
| Artemis crew landing order | S16 Artemis IV page still has the Artemis III site-selection panel ("the first of the Artemis missions to bring crew to the lunar surface"), and RELEASE24-136 (not updated since Oct 28, 2024) still captions the nine regions "for NASA's Artemis III mission" | S30: Artemis III "now in 2027, will be designed to test out systems and operational capabilities in low Earth orbit" "to prepare for an Artemis IV landing in 2028"; S31 (Oct 23, 2026): "Artemis IV, the first Artemis mission on the lunar surface"; S35 Artemis III page (Oct 19, 2026): "Crewed Demonstration" "in low Earth orbit", "before Americans return to the Moon on Artemis IV"; the Artemis IV page (re-checked 2026-11-15, updated Mar 16, 2026) lists "nine candidate landing regions near the lunar South Pole" without a mission number in its text | Web text names only Artemis IV, as NASA's first Artemis crew landing (S30, S31, S35), and calls the nine regions those "NASA named in October 2024", without a mission number |
| IM-2 landing distance from target | S37 photo caption "about 820 feet" | S37 text "more than 1,300 feet (400 meters)" | Not used in web text |
| Equatorial night temperature | S27 140 K at night | table `tmin_k` median 94 K in D (Diviner pre-dawn minimum; R2 sec. 3 explains the 95 K vs 140 K difference) | Web text quotes only daytime |

## 3. Why each mission is not posed outside its zone

Support marks: **[C-Sx]** citation to a source above (quote in the table or below); **[D]** computed from the project's lunar table today (figures in sec. 2); **[T]** the team's own design choice, stated as such.

Official statements used:
- South pole: "contains permanently shadowed areas that can preserve resources, including water"; "Factors in the selection process included science potential, launch window availability, terrain suitability, communication capabilities with Earth, and lighting conditions" (S16, RELEASE24-136). VIPER: "Map the location of water ice and other potential resources"; "we know there is ice at the lunar poles" (S15). Moon Base: the South Pole is where "direct communications with Earth can be difficult" (S7).
- Polar light: "The spin axis of the Moon is tilted by only 1.54°", "leaving some areas near the poles in permanent shadow", "other nearby regions remain sunlit for the majority of the year" (S25); Shackleton: "three points on the rim remain collectively sunlit for more than 90 percent of the year"; "no location on the Moon stays continuously illuminated" (S26).
- Equator: "Daytime temperatures near the lunar equator reach ... (120° C, 400 K)"; "each lunar day lasts 14 Earth days", "a lunar night lasts 14 Earth days" (S27).
- Cold traps outside the south: Hermite crater, "-250° C, 25 K, making it the coldest temperature measured anywhere in the solar system" (S27); Hermite's IAU centre is 86.17 N (S28), i.e. region C.
- Apollo: free-return "required the spacecraft to leave earth orbit on a path that would bring it to the moon within five degrees of latitude of the lunar equator"; "Operational considerations predominated"; zone of interest "(5 degrees north to 5 degrees south latitude, 45 degrees east to 45 degrees west longitude)" (S24, p. 73 and the section "Picking Landing Sites"); "Slope: the general slope of the landing area must be less than 2 degrees" (S23).
- Far side: Chang'e 6 site chosen for "communication and telemetry conditions and the flatness of the terrain", landing "Supported by the Queqiao-2 relay satellite" (S19); Draper/CS-11 will "involve relay satellites in order to allow communication with Earth from the far side of the Moon" (S14).

### Rover (zone: A + B, latitude <= -75)

| Region | Reason (support) |
|---|---|
| C north-polar | The north pole also has extremely cold shadowed craters (Hermite, 25 K) [C-S27, S28], so it could host a similar test, and **by terrain it matches as well or better**: 9,888 Earth sites pair there against 10,192 in the zone, median similarity 99.7 against 93.3, median slope gap 0.10° against 0.41°, roughness 1.6 m against 5.3 m; of the 9,790 paired in both, 87.3 % have the more similar twin in the north [D, recomputed 2026-11-15]. The zone is justified by NASA's plans, not by data: VIPER targets water ice at the south pole (Mons Mouton) [C-S15] [T]. Missions there: GRAIL A and B impacted at 75.6 N in 2012 [C-S1]; no landing in S1. |
| D low equatorial plains | Rovers have worked here: Lunokhod 2 (1973) [C-S1]. The rover test is about prospecting for ice like VIPER, and NASA places that ice at the poles, in permanently shadowed areas [C-S15, S16]; the plains get no lasting shadow (day max median 388 K) [D]. |
| E far side | Yutu 2 (Chang'e 4, 2019) drove here and Chang'e 6 returned samples [C-S1, S19]. The rover test targets polar ice like VIPER [C-S15]; far-side surface work also needs a relay to reach Earth [C-S19, S14]. Another region could host a rover test; this one is the team's choice [T]. |
| F near-side highlands, mid-lat | Rovers have driven here: Lunokhod 1, Yutu (Chang'e 3) and Pragyan (Chandrayaan-3, 69.4 S) [C-S1, S21]. The team's rover follows VIPER, which goes to permanently shadowed craters at the south pole, so the zone starts at 75 S [C-S15, T]. |

### Solar panels (zone: D, low equatorial plains)

| Region | Reason (support) |
|---|---|
| A nine NASA regions | The Sun stays near the horizon (axis tilt 1.54°) [C-S25]; level ground gets 0.53 kWh/m2/day (median) in our table against 10.0 in the plains, and no cell at or beyond 75° gets more than 2.475, below the 3.537 that the least sunny ranked Earth site (4.137 above the atmosphere) needs within the 0.6 tolerance [D]. Some ridges are lit most of the year [C-S25, S26], but that is a vertical-panel test, not the team's flat-ground one [T]. IM-2 landed here (2025) [C-S1, S4]. |
| B south-polar, other | Same low Sun: 1.32 kWh/m2/day median on level ground vs 10.0 in the plains, at most 2.475 against the 3.537 needed [D]; peaks such as the Shackleton rim are sunlit over 90 % of the year [C-S26] and IM-1 landed near Malapert A (2024) [C-S1, S5], so the region is not ruled out; lit peaks call for a different panel geometry from the team's flat-ground test [T]. |
| C north-polar | Low Sun again: 1.38 kWh/m2/day median on level ground vs 10.0, at most 2.451 against the 3.537 needed [D]. No landing in S1; GRAIL impacted here [C-S1]. The team's test is designed for high Sun on flat ground [T]. |
| E far side | Sunlight is close to the plains' (median 8.96 vs 10.02 kWh/m2/day) and Chang'e 4 and 6 landed here [D, C-S1]. **The data do not rule it out**: 18,776 of 18,777 Earth sites pair here, including 12,416 of the 12,417 with no twin in the maria [D, recomputed 2026-11-15]. The team kept its zone to the low, flat plains (median slope 1.1° vs 6.2°) [D, T]; some far-side low plains (e.g. around Nassau) are inside the zone [D]. |
| F near-side highlands, mid-lat | Apollo 14 and 16, SLIM, Chang'e 3 and 5 and Chandrayaan-3 landed here [C-S1], and 18,776 of 18,777 Earth sites pair here, including 12,416 of the 12,417 with no twin in the maria [D], so the region is not ruled out (no claim is made about how each was powered: the Apollo landers' power source was not checked on an official page). The team kept the zone to the low plains: more energy (10.0 vs 8.25 kWh/m2/day) and flatter ground (1.1° vs 3.9°) [D, T]. |

### Lunar base (zone: A, the nine NASA regions)

| Region | Reason (support) |
|---|---|
| B south-polar, other | IM-1 landed here (2024) and LCROSS impacted Cabeus (2009) [C-S1]; several robotic missions target the wider south-polar region [C-S5, S7, S17, S20]. The base test follows NASA's crew-landing plan, so it uses only the nine regions NASA named in October 2024 [C-S16, T]. |
| C north-polar | NASA's crewed plans point to the south pole [C-S16]; the north pole also has cold shadowed craters [C-S27, S28], so this is the team's choice, not a physical limit [T]. GRAIL impacted here (2012) [C-S1]. |
| D low equatorial plains | Apollo 11, 12, 15 and 17 landed crews here [C-S1, S2]; the first Apollo sites stayed within 5° of the equator for operational reasons such as the free-return trajectory [C-S24]. NASA's next crew landing, Artemis IV (early 2028), targets the south pole, where shadowed areas can preserve water [C-S16, S30, S31]. Daytime reaches about 400 K and nights last 14 Earth days [C-S27]. |
| E far side | Chang'e 4 and 6 landed here [C-S1, S19]; Chang'e 6's landing was "Supported by the Queqiao-2 relay satellite" [C-S19]. NASA lists "communication capabilities with Earth" among its criteria and chose nine south-polar regions [C-S16]. |
| F near-side highlands, mid-lat | Apollo 14 and 16, Chandrayaan-3 and SLIM landed here [C-S1]. NASA's next crew landing targets the south pole, where shadowed areas "can preserve resources, including water", and its nine regions were selected on factors including terrain, communication with Earth and lighting [C-S16]; the base test uses them [T]. |

## 4. Web text (approved, with the corrections of 2026-11-15 applied)

**Approved** by the delegate, on the team lead's behalf, on 2026-11-15 at 08:55 CET, with corrections to apply before publishing; **the corrections are applied below** (list and sources in "Corrections of 2026-11-15 (after approval)"). The same strings, character for character, are in `tierra luna/engine/mission_zone_texts.json` (keys in brackets), which the engine copies into the data bundle; `tierra luna/tests/test_mission_zone_texts.py` checks that they match this section. Official pages consulted on 2026-11-15.

Rules checked for every string: no "no missions" or "never visited" claim; no "cannot work here"; no claim that the team's zone is the best by data; no NASA endorsement (NASA is cited as the source of a plan, not as a partner); every mission named is in sec. 1 with its source; every number is in the `figures` list of the json with how it was computed (recomputed on 2026-11-15, see the corrections section); at most 70 words each. Word counts in brackets. The three "why this zone" strings are shown when a mission is chosen; the others when a lunar cell outside the mission's zone is clicked (sec. 5).

**General note (Moon view)** (`general_note`) [45]
> Spacecraft have landed in many parts of the Moon: Apollo and Luna near the equator, Chang'e 4 and 6 on the far side, IM-2 near the south pole. Each test is searched in one zone the team chose; other regions are explained, not ruled out.

Gloss: Naves han aterrizado en muchas partes de la Luna: Apolo y Luna cerca del ecuador, Chang'e 4 y 6 en la cara oculta, IM-2 cerca del polo sur. Cada prueba se busca en una zona elegida por el equipo; las demás regiones se explican, no se descartan.

**Why this zone: Rover (south pole, at or below 75° S)** (`zone_why.rover`) [57]
> Why the south pole: our rover test follows NASA's plans there, such as the VIPER rover, meant to map water ice in permanently shadowed craters. It is not the best match by terrain: in our data the north pole pairs about as many Earth sites (9,888 against 10,192) and more closely (median slope gap 0.10° against 0.41°).

Gloss: Por qué el polo sur: nuestra prueba del rover sigue los planes de la NASA allí, como el rover VIPER, pensado para cartografiar hielo de agua en cráteres en sombra permanente. No es la mejor coincidencia por terreno: en nuestros datos el polo norte empareja casi tantos sitios de la Tierra (9.888 frente a 10.192) y con más parecido (diferencia mediana de pendiente 0,10° frente a 0,41°).

**Why this zone: Solar panels (low equatorial plains)** (`zone_why.solar`) [65]
> Why the equatorial maria: we target a high Sun on the lowest, flattest plains (median slope 1.1°), where Apollo landed, with sunlight as high as anywhere in our data: about 10 kWh/m² a day (highlands: 8 to 9). Nearly every Earth site without a twin here would have one in the highlands. Flat polar ground gets at most 2.48, below the 3.54 our sites need.

Gloss: Por qué los mares ecuatoriales: buscamos un Sol alto sobre las llanuras más bajas y llanas (pendiente mediana 1,1°), donde aterrizó el Apolo, con tanta luz solar como en cualquier parte de nuestros datos: unos 10 kWh/m² al día (tierras altas: 8 a 9). Casi todos los sitios de la Tierra sin gemelo aquí lo tendrían en las tierras altas. El suelo llano de los polos recibe como mucho 2,48, por debajo de los 3,54 que necesitan nuestros sitios.

**Why this zone: Lunar base (NASA's nine candidate regions)** (`zone_why.lunar_base`) [63]
> Why NASA's nine regions: our base test follows NASA's crew-landing plan, which named nine candidate regions near the south pole in October 2024. This is the team's choice, not a physical limit. Each pair is a likeness of thermal position (how cold and how variable a place is within its own world), not of temperature; the real difference is shown with every pair.

Gloss: Por qué las nueve regiones de la NASA: nuestra prueba de base sigue el plan de alunizaje tripulado de la NASA, que nombró nueve regiones candidatas cerca del polo sur en octubre de 2024. Es una elección del equipo, no un límite físico. Cada par es un parecido de posición térmica (lo frío y lo variable que es un lugar dentro de su propio mundo), no de temperatura; la diferencia real se enseña en cada par.

**Rover / North-polar region** (`outside.rover.C`) [55]
> Not our rover zone, but our data do not rule it out: by terrain the north pole matches Earth sites as closely or more (median similarity 99.7 against 93.3 in our south-pole zone). Our rover test follows NASA's south-pole plans, such as VIPER, for water ice. NASA's GRAIL probes ended their mission here in 2012.

Gloss: No es nuestra zona del rover, pero nuestros datos no la descartan: por terreno el polo norte se parece a los sitios de la Tierra igual o más (similitud mediana 99,7 frente a 93,3 en nuestra zona del polo sur). Nuestra prueba sigue los planes de la NASA en el polo sur, como VIPER, para el hielo de agua. Las sondas GRAIL de la NASA terminaron aquí su misión en 2012.

**Rover / Low equatorial plains (maria)** (`outside.rover.D`) [42]
> Rovers have driven here, like Lunokhod 2 in 1973. Our rover test is about finding water ice, as NASA plans with VIPER, and NASA says that ice lies at the poles, in permanently shadowed areas, so we search near the south pole.

Gloss: Aquí ya han circulado rovers, como Lunojod 2 en 1973. Nuestra prueba trata de buscar hielo de agua, como planea la NASA con VIPER, y la NASA dice que ese hielo está en los polos, en zonas en sombra permanente; por eso buscamos cerca del polo sur.

**Rover / Far side** (`outside.rover.E`) [40]
> China's Yutu-2 rover drove here after Chang'e 4 landed in 2019, so rovers work on the far side. Our rover test targets polar water ice, like NASA's VIPER, and far-side missions also need a relay satellite to talk to Earth.

Gloss: El rover chino Yutu-2 recorrió esta zona tras el aterrizaje de Chang'e 4 en 2019, así que los rovers funcionan en la cara oculta. Nuestra prueba busca hielo polar, como VIPER de la NASA, y las misiones en la cara oculta necesitan además un satélite repetidor para comunicarse con la Tierra.

**Rover / Near-side highlands and mid-latitudes** (`outside.rover.F`) [49]
> Rovers have worked here: Lunokhod 1, China's Yutu and India's Pragyan, which reached 69° S in 2023 on what India calls a south-pole landing. Our rover test follows NASA's VIPER plan for water ice in permanently shadowed craters, so the team set its zone at 75° S and beyond.

Gloss: Aquí han trabajado rovers: Lunojod 1, el Yutu chino y el Pragyan indio, que llegó a 69° S en 2023 en lo que la India llama un alunizaje en el polo sur. Nuestra prueba sigue el plan VIPER de la NASA para el hielo de agua en cráteres en sombra permanente, por eso el equipo fijó su zona a partir de 75° S.

**Solar panels / The nine NASA candidate regions** (`outside.solar.A`) [55]
> Near the pole the Sun stays low: in our data no flat ground beyond 75° S gets more than 2.48 kWh/m² a day, and even our least sunny Earth site would need 3.54 for a twin. Some ridges stay lit most of the year, suiting vertical panels, a different test. IM-2 landed here in 2025.

Gloss: Cerca del polo el Sol va bajo: en nuestros datos ningún suelo llano más allá de 75° S recibe más de 2,48 kWh/m² al día, y hasta nuestro sitio de la Tierra con menos sol necesitaría 3,54 para tener gemelo. Algunas crestas están iluminadas la mayor parte del año, lo que conviene a paneles verticales, otra prueba distinta. IM-2 aterrizó aquí en 2025.

**Solar panels / South-polar region (outside NASA's nine)** (`outside.solar.B`) [53]
> IM-1 landed here in 2024, and spots on Shackleton's rim are jointly lit over 90% of the year. But for a flat panel the Sun stays low: in our data no flat ground beyond 75° S gets more than 2.48 kWh/m² a day, below the 3.54 our least sunny Earth site would need.

Gloss: IM-1 aterrizó aquí en 2024, y unos puntos del borde de Shackleton están iluminados, en conjunto, más del 90 % del año. Pero para un panel horizontal el Sol va bajo: en nuestros datos ningún suelo llano más allá de 75° S recibe más de 2,48 kWh/m² al día, por debajo de los 3,54 que necesitaría nuestro sitio de la Tierra con menos sol.

**Solar panels / North-polar region** (`outside.solar.C`) [53]
> The Sun stays near the horizon here: in our data no flat ground beyond 75° N gets more than 2.45 kWh/m² a day, below the 3.54 our least sunny Earth site would need for a twin. Our panel test is designed for a high Sun on flat ground, so we search the maria.

Gloss: Aquí el Sol se mantiene cerca del horizonte: en nuestros datos ningún suelo llano más allá de 75° N recibe más de 2,45 kWh/m² al día, por debajo de los 3,54 que necesitaría nuestro sitio de la Tierra con menos sol para tener gemelo. Nuestra prueba de paneles está pensada para Sol alto y suelo llano, por eso buscamos en los mares.

**Solar panels / Far side** (`outside.solar.E`) [57]
> Our data do not rule this region out: 18,776 of our 18,777 Earth sites would find a sunlight twin here, including 12,416 with none in the maria. Chang'e 4 and 6 landed here. The team chose the maria as its design target: more sunlight on average (about 10 vs 9 kWh/m² a day) on lower, flatter plains.

Gloss: Nuestros datos no descartan esta región: 18.776 de nuestros 18.777 sitios de la Tierra encontrarían aquí un gemelo de luz, entre ellos 12.416 que no lo tienen en los mares. Chang'e 4 y 6 aterrizaron aquí. El equipo eligió los mares como objetivo de diseño: más luz solar de media (unos 10 frente a 9 kWh/m² al día) en llanuras más bajas y llanas.

**Solar panels / Near-side highlands and mid-latitudes** (`outside.solar.F`) [63]
> Our data do not rule this region out: 18,776 of our 18,777 Earth sites would find a sunlight twin here, including 12,416 with none in the maria. Apollo 14 and 16, SLIM and Chang'e 3 and 5 landed here. The team chose the maria as its design target: more sunlight on average (about 10 vs 8 kWh/m² a day) on lower, flatter plains.

Gloss: Nuestros datos no descartan esta región: 18.776 de nuestros 18.777 sitios de la Tierra encontrarían aquí un gemelo de luz, entre ellos 12.416 que no lo tienen en los mares. Aquí aterrizaron Apolo 14 y 16, SLIM y Chang'e 3 y 5. El equipo eligió los mares como objetivo de diseño: más luz solar de media (unos 10 frente a 8 kWh/m² al día) en llanuras más bajas y llanas.

**Lunar base / South-polar region (outside NASA's nine)** (`outside.lunar_base.B`) [49]
> IM-1 landed here in 2024, and more robotic missions target the south-polar region. Our base test follows NASA's plan for its first Artemis crew landing, Artemis IV, so it uses only the nine candidate regions NASA named in October 2024. This is the team's choice, not a physical limit.

Gloss: IM-1 aterrizó aquí en 2024 y más misiones robóticas apuntan a la región polar sur. Nuestra prueba de base sigue el plan de la NASA para su primer alunizaje tripulado de Artemis, Artemis IV, así que usa solo las nueve regiones candidatas que la NASA nombró en octubre de 2024. Es una elección del equipo, no un límite físico.

**Lunar base / North-polar region** (`outside.lunar_base.C`) [37]
> NASA's crewed landing plans point to the south pole, not here, although the north pole also has cold shadowed craters. NASA's GRAIL probes ended their mission here in 2012. Our base zone is NASA's nine south-polar regions.

Gloss: Los planes de alunizaje tripulado de la NASA apuntan al polo sur, no aquí, aunque el polo norte también tiene cráteres fríos en sombra. Las sondas GRAIL de la NASA terminaron aquí su misión en 2012. Nuestra zona de base son las nueve regiones del polo sur de la NASA.

**Lunar base / Low equatorial plains (maria)** (`outside.lunar_base.D`) [44]
> Apollo 11, 12, 15 and 17 landed crews here; early Apollo sites stayed near the equator for operational reasons, such as a safe return path. NASA's next crew landing, Artemis IV, targets the south pole, where shadowed areas can preserve water. We follow that.

Gloss: Apolo 11, 12, 15 y 17 llevaron tripulaciones aquí; los primeros lugares de Apolo se quedaron cerca del ecuador por razones operativas, como una trayectoria de regreso segura. El próximo alunizaje tripulado de la NASA, Artemis IV, apunta al polo sur, donde las zonas en sombra pueden conservar agua. Nosotros seguimos ese plan.

**Lunar base / Far side** (`outside.lunar_base.E`) [39]
> Chang'e 4 and 6 landed here; Chang'e 6 landed with support from the Queqiao-2 relay satellite. NASA lists communication with Earth among its criteria for crew landing sites and chose nine south-polar regions; our base test uses those regions.

Gloss: Chang'e 4 y 6 aterrizaron aquí; Chang'e 6 aterrizó con el apoyo del satélite repetidor Queqiao-2. La NASA incluye la comunicación con la Tierra entre sus criterios para los lugares de alunizaje tripulado y eligió nueve regiones del polo sur; nuestra prueba de base usa esas regiones.

**Lunar base / Near-side highlands and mid-latitudes** (`outside.lunar_base.F`) [42]
> Apollo 14 and 16, India's Chandrayaan-3 and Japan's SLIM landed here. NASA's next crew landing, Artemis IV, targets the south pole, where shadowed areas can preserve water, in nine regions picked for lighting, terrain and Earth communication. Our base test uses them.

Gloss: Aquí aterrizaron Apolo 14 y 16, Chandrayaan-3 de la India y SLIM de Japón. El próximo alunizaje tripulado de la NASA, Artemis IV, apunta al polo sur, donde las zonas en sombra pueden conservar agua, en nueve regiones elegidas por iluminación, terreno y comunicación con la Tierra. Nuestra prueba de base usa esas regiones.

Checks against sec. 1: every mission named in a string is in tables 1a-1c with its region (Lunokhod 2: D; Yutu-2/Chang'e 4, Chang'e 6: E; Lunokhod 1, Yutu, Pragyan, Apollo 14 and 16, SLIM, Chang'e 3 and 5, Chandrayaan-3: F; IM-1: B; IM-2: A; GRAIL: C; Apollo 11, 12, 15, 17: D). Artemis IV and VIPER are cited as NASA plans only; Artemis IV is the only Artemis mission named, as the first crew landing (S30, S31, S35). No string gives a date for a planned mission and none names the sites of Moon Base I, Griffin-1 or Chang'e 7 (not precise enough on official pages). No string says that rovers have or have not driven beyond 75° S (see the corrections section).

## 5. How the app can pick the text for a clicked lunar cell

1. Take the clicked cell's centre latitude, longitude and its `elevation_m` from the 1-degree lunar table (the same table the zones use).
2. Assign one region, testing in this order and stopping at the first match: A if the cell is one of the 280 cells of the nine NASA regions (the same cell list that defines the Lunar base zone); B if latitude <= -75; C if latitude >= 75; D if abs(latitude) <= 30 and elevation <= -1,200 m; E if abs(longitude) > 90; otherwise F.
3. For the mission on screen, if the region is part of that mission's zone (Rover: A, B; Solar panels: D; Lunar base: A), show the normal pair view; otherwise show the string for (mission, region) from sec. 4.
4. Show the general note once in the Moon view, independent of the click.
5. Keep the strings in data (one entry per mission and region, 14 entries, plus the note and the three "why this zone" strings: `tierra luna/engine/mission_zone_texts.json`), so that a later correction to this document changes text, not logic. If the mission list changes (for example a 2026-2027 landing), update sec. 1 first and re-check the strings that name missions.

## Fact check (independent checker, 2026-11-15)

Scratch files: `/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/zones-check/` (`check.py` places every point independently with pandas from `moon_real_1deg.csv` and `regions.json`; `pts.txt` holds the coordinates as printed in S1 and the IAU extract; `pages/` holds the pages I downloaded).

**What I re-opened (all on 2026-11-15).** All 29 of the draft's sources, plus six more pages: S1 (whole table and notes, parsed line by line), S2, S3, S4, S12, S13, S14 (Draper and BLUEGHOS2), S5, S6, S7, S8, S9, S10, S11 (NASA event page and Firefly), S15 (both pages), S16 (Artemis IV page and RELEASE24-136, full text by curl), S17 (CNSA 2026-08-23, Xinhua 2025-02-04, gov.cn 2026-05-23), S18, S19, S20 (the PIB press release gave HTTP 403 to WebFetch and opened on the second try by curl; the PIB June 2026 PDF; the ISRO TIM page), S21, S22 (PDF), S23, S24 (the whole 226 MB PDF downloaded again, with the same byte size as the writer's copy; quotes found in its text), S25, S26, S27 (PDF), S28 (local extract), S29. Added: S30, S31, S32, S33, S34. Every source was re-opened; none is marked "source not re-opened". Every coordinate in 1a to 1c matches S1's "(N, E positive)" column. Each 0-360 conversion (minus 360 above 180) was checked. The region and zone of all 75 points, and of the 8 feature centres used for planned missions, were recomputed independently and agree with the draft. Three cell elevations differ from the draft by 1 m, because a value ending in .5 can round either way (Surveyor 5 -2,064.5, SLIM -212.5, Luna 25 -714.5); this changes no zone. The regional figures of sec. 2 (cell counts, area shares, 1,029 far-side cells in D, and the area-weighted medians and p10 to p90 ranges) were all reproduced exactly.

**What I corrected.**
1. Table 1c and the counts per region left out three S1 impacts that have coordinates: the Apollo 16 subsatellite (E), the Chang'e 5-T1 booster (E, "considered most likely") and the Chang'e 5 ascent craft (F). They are now added. Impacts are now 8 in E (was 6) and 5 in F (was 4). Landing counts are unchanged: 28 successful landings, 6 of them crewed, and 12 failed landings.
2. The Solar panels text for the near-side highlands said "so panels work here too", right after naming Apollo 14 and 16. No official page opened today shows that those landers ran on solar panels, so the claim was unsupported. It now says "so this region is not ruled out", in the web string, in its gloss and in the reason table. The same unsupported "panels do work here" in the reason table for region B was reworded.
3. The Lunar base far-side text said Chang'e 6 "talked to Earth through" Queqiao-2. S19 says only that the landing was "Supported by the Queqiao-2 relay satellite". The string and the gloss now say that.
4. The general note said spacecraft "have landed across the Moon". The north-polar region (C) has no landing in S1, so it now says "in many parts of the Moon" (45 words).
5. "NASA's next crew landing, Artemis IV" had no source in the draft (S16 still carries the old Artemis III panel). It is now cited to S30 (RELEASE26-022) and S31 (the NASA blog of 2026-10-23), and a row was added to the disagreements table.
6. The rover strings no longer say VIPER "looks for" or "will do": VIPER has not flown, and its delivery is a contract option (S15). They now say "modelled on NASA's VIPER plan" and "as NASA plans with VIPER", which also avoids any hint that NASA endorses the project. "NASA places that ice in permanently shadowed craters" now follows the sources more closely: "NASA says that ice lies at the poles, in permanently shadowed areas" (S15 "we know there is ice at the lunar poles"; RELEASE25-064 "small, permanently shadowed regions").
7. The Solar panels far-side string said "a few far-side plains" are inside the zone, but they are 1,029 of the zone's 6,686 cells (15 %). It now says "some". In the gloss for the nine NASA regions, "casi todo el año" became "la mayor parte del año", to match "most of the year".
8. Planned missions added from official pages: ispace Mission 3 (2028, no site, S33); Luna 27 (IKI RAS, tentative 2029 and 2030, near-polar, S34); CS-8 and CX-2 (S5); the PROMISE target "late 2028" and "will land at the Moon's South Pole" (S32, RELEASE26-095, Nov 7, 2026).
9. Disagreements added: CS-11/CP-12, whose ispace lander is now "Mission 5", launch 2030, "pending approval by NASA" (S33), so NSSDCA's 2026 date is out of date; and Chandrayaan-3, which PIB calls a "lunar south pole landing" at 69.3 S while this document's rule puts it in region F. The web text gives the latitude and does not contradict PIB.
10. Small fixes: the Apollo S-IVB and ascent-stage impacts are "within about 27 degrees of the equator", not all "near the equator"; the word counts were recomputed after the edits (37 to 45 words each).

**Checked and found correct.** Every web string and gloss was checked against secs. 1 and 2. No string says or implies that a region has had no missions. The north-polar strings name GRAIL, which is the only S1 object there. No string says a mission "cannot" work in a region. Every figure is in sec. 2: 0.5, 1.3, 1.4, about 9, about 8 and about 10 kWh/m2/day match the medians 0.53, 1.32, 1.38, 8.96, 8.25 and 10.02. Every mission named is in its stated region: IM-2 in A (Mons Mouton Plateau footprint); IM-1 in B; GRAIL in C; Apollo 11, 12, 15 and 17 and Lunokhod 2 in D; Chang'e 4/Yutu-2 and Chang'e 6 in E; Apollo 14 and 16, Lunokhod 1, Yutu, Pragyan, SLIM, Chang'e 3 and 5 and Chandrayaan-3 in F. Quotes checked word for word: SP-4214 ("within five degrees of latitude of the lunar equator"; "Operational considerations predominated"); RELEASE24-136 ("communication capabilities with Earth, and lighting conditions"; "permanently shadowed areas that can preserve resources, including water"); PIA13720; the Shackleton "more than 90 percent"; the LRO lithograph (400 K, 140 K, Hermite 25 K, 14 Earth days). No page opened today (NASA pages updated up to Nov 12, 2026, CNSA 2026-08-23, ispace 2026-11-13) reports a lunar landing after 5 June 2025. A broad web search found none either. This means none was found, not that none happened.

**Could not confirm on an official page (kept out of the web text).** Everything in the "Not confirmed" list above, plus:
- whether the Apollo, Surveyor and Luna landers used solar power (so no string makes a power claim about past landers);
- IM-1's final attitude;
- exact sites for Moon Base I, Griffin-1, Chang'e 7, Chang'e 8, Chandrayaan-4 and LUPEX;
- ESA Argonaut and Korean lander plans (not searched).


## Corrections of 2026-11-15 (after approval)

The delegate approved section 4 on the team lead's behalf on 2026-11-15 at 08:55 CET with corrections to apply before publishing. All pages below were opened on 2026-11-15. Figures were recomputed on 2026-11-15 with own code (`/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/zonetexts/figures.py`, output `figures.json`) from `tierra luna/output_real/moon_real_1deg.csv`, `earth_real_1deg.csv` and the shipped bundle `app/public/data/v2` (read following `docs/DATA_CONTRACT.md`); the shipped zones reproduce the bundle twin for twin (Rover 10,192 pairs, Solar panels 6,360, both identical to `earth_<mission>.bin` `twin`).

**Corrections applied to the strings**

1. **Artemis coherence.** NASA's pages say today that the first crewed landing is Artemis IV: the Artemis III page (S35, updated Oct 19, 2026) calls Artemis III a "Crewed Demonstration" that "will carry out a series of objectives in low Earth orbit", "before Americans return to the Moon on Artemis IV"; NASA's blog of Oct 23, 2026 (S31) says "Artemis IV, the first Artemis mission on the lunar surface"; RELEASE26-022 (S30) agrees. The nine regions are still captioned "for NASA's Artemis III mission" on RELEASE24-136 (S16, unchanged since Oct 28, 2024), and the Artemis IV page lists "nine candidate landing regions near the lunar South Pole" without a mission number in its text. Every string now names only Artemis IV (Lunar base B, D, F) and calls the regions those "NASA named in October 2024". The draft had no "Artemis III" in a web string, but "NASA's plan for the first Artemis crew landing" (Lunar base B) now says "Artemis IV" explicitly. The only dated phrase was "status as of 2026-11-15" (sec. 1d); there was no "as of June 2025" in this document. Every page is cited with its consultation date, 2026-11-15.
2. **Missions of 2025-2026** (sec. 1, S35-S40). ispace Resilience (Hakuto-R Mission 2): hard landing on 5 June 2025 UTC (6 June JST) in Mare Frigoris, landing milestone "NOT COMPLETED" (S36, S1), region F, outside every zone; no string names it. Chang'e 7: not launched, "不能在今年预定窗口实施" (CNSA 2026-08-23), nothing newer up to 2026-11-09 (S38). IM-3, Blue Ghost Mission 2, Griffin-1 and Blue Moon Mark 1: planned, future tense on NASA pages updated Oct-Nov 2026 (S5, S7, S8, S9, S11). Sweep: no landing or attempt after June 2025 found on the NASA, NSSDCA, CNSA, ispace, Firefly, Astrobotic, ESA and KASA pages opened (intuitivemachines.com did not load, a redirect loop, so IM-3 rests on NASA and NSSDCA; Blue Origin's own pages were not opened, so Blue Moon Mark 1 rests on S7 and S8); two plans added to 1d (ESA Argonaut 2030, south-polar region; Korea's lander 2032, no site), neither placed. No new site falls in a zone, so no sentence about missions changes; the general note stands.
3. **Rover, south pole.** No draft string said "Rovers have not driven at the south pole". Checked anyway: IM-2's MAPP rover was not deployed (S37, Lunar Outpost); what happened to Yaoki and the hopper is not stated on an official page (S4, S37). The claim "no rover has driven beyond 75° S" is therefore **not made**. The Pragyan string now adds that India calls Chandrayaan-3 a south-pole landing (S20), so it does not contradict ISRO.
4. **Rover, decision 2.** New "why this zone" string: the zone is justified by NASA's plans (VIPER, "The rover can venture into permanently shadowed craters", S15, re-opened 2026-11-15), and by terrain the north pole pairs about as many Earth sites and more closely, with the figures below. The north-polar string now says the data do not rule it out, with the median similarities. No string presents the south pole as the best by data.
5. **Solar panels, decisions 3 and 4.** New "why this zone" string with the team's design target (high Sun, lowest and flattest plains, most sunlight, Apollo precedent), the highlands that would pair almost every unpaired site, and the poles with the maximum irradiance for a flat panel against the minimum needed. The far-side and near-side highland strings now give the 18,776 / 12,416 figures; the three polar strings give the maximum (2.48 or 2.45) and the 3.54, instead of the medians 0.5 / 1.3 / 1.4.
6. **Lunar base, decision 1.** New "why this zone" string: the nine regions follow NASA's crew-landing plan, a team choice, not a physical limit; each pair is a likeness of thermal position, not of temperature, with the real difference shown. The south-polar string adds "This is the team's choice, not a physical limit."

**Figures (recomputed 2026-11-15) and comparison**

| Figure | Recomputed | `docs/ZONE_CONTRAST.md` / decision wording | Difference |
|---|---|---|---|
| Rover, Earth sites with a twin: south-polar zone / north pole (>= 75 N) | 10,192 / 9,888 of 10,337 | 10,192 / 9,888 | none |
| Rover, median similarity: south / north | 93.29 / 99.72 (P90 99.24 / 99.95) | 93.3 / 99.7 | none |
| Rover, median real difference of slope: south / north | 0.41° / 0.10° (P90 0.85 / 0.39) | 0.41 / 0.10 | none |
| Rover, median real difference of roughness: south / north | 5.3 m / 1.6 m (P90 20.5 / 6.3) | 5.3 / 1.6 | none |
| Rover, paired in both: share whose north-polar twin is more similar | 87.3 % of 9,790 (median gain +4.29) | 87.3 % of 9,790, +4.3 | none |
| Solar, Earth sites with a twin in the maria / in E alone / in F alone | 6,360 / 18,776 / 18,776 of 18,777 | 6,360 / 18,776 / 18,776 | none |
| Solar, sites without a twin in the maria that would pair in E / in F | 12,416 / 12,416 of 12,417 (the last, E19334, pairs nowhere) | 12,416 "solo tienen par fuera" | none |
| Maximum lunar irradiance (horizontal surface) at or beyond 75°: south / north | 2.475 / 2.451 kWh/m²/day | 2.475 / 2.451 | none |
| 3.54: least sunlight above the atmosphere among the 18,777 ranked solar sites minus the 0.6 tolerance | 4.1368 − 0.6 = 3.5368 kWh/m²/day (16,496 lunar cells are below it) | 3.537; 16,496 | none |
| Irradiance, area-weighted median: D / E / F | 10.02 / 8.96 / 8.25 kWh/m²/day | decision: "about 10 against about 8 in the highlands"; ZONE_CONTRAST sec. 6 (unweighted) 9.97 / 8.14 / 7.29 | the far-side highlands are about 9, not 8: strings say "8 to 9" (zone) and "10 vs 9" (E), "10 vs 8" (F) |
| Slope, area-weighted median `slope_deg` (LDEM_16): D / E / F (and A / B / C) | 1.13 / 6.23 / 3.92° (10.6 / 6.8 / 5.7°); with `slope_iso_deg`, the engine's slope: 1.12 / 6.07 / 3.75° | sec. 2: 1.1 / 6.2 / 3.9 | none; D is the flattest of the six regions, so "flattest" is backed |
| Elevation, area-weighted median: D / E / F (and A / B / C) | −1,855 / +959 / −851 m (+1,127 / −1,637 / −745 m) | — | D is the lowest of the six regions (by definition at most −1,200 m), so "lowest" is backed |
| Roughness, area-weighted median: D / E / F | 46 / 191 / 129 m | — | consistent with "flattest" |

Everything above is in `tierra luna/engine/mission_zone_texts.json` `figures` with how it was computed; `tierra luna/tests/test_mission_zone_texts.py` recomputes the regional medians and the polar maxima from the lunar table.

### Second fact check of the corrections (independent checker, 2026-11-15)

Scratch: `/tmp/claude-0/-home-user/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/zonetexts-check/` (`fc.py` own recomputation, output `fc.json`; `toa.py` own insolation integral; `pages/` the pages fetched today). **Re-opened on 2026-11-15:** NASA Artemis III (updated Oct 19, 2026), Artemis IV (Mar 16, 2026), Artemis overview https://www.nasa.gov/artemis/ (Oct 21, 2026: "NASA's first crewed Moon landing under the Artemis program will take place in 2028" under "Artemis IV"), blog of Oct 23, 2026, RELEASE26-022, RELEASE24-136; Moon Base Phases (Nov 12, 2026); the NASA event pages of Blue Moon Mark 1 (Oct 21, "2027", Shackleton Connecting Ridge), Griffin-1 (Oct 14, "Late 2026", Nobile) and Blue Ghost Mission 2 (Oct 21, "2027", Nassau); Firefly's Blue Ghost Mission 2 page ("Upcoming Mission", "no earlier than 2027"); NSSDCA IM-3-NOVA and PRIME-1; ispace Mission 2 ("NOT COMPLETED") and the 2025-06-24 cause analysis (LRF anomaly, June 6, 2025); CNSA Chang'e 7 (2026-08-23) and the CNSA news list (newest 2026-11-09, no lunar item); RELEASE25-025 and Lunar Outpost on IM-2; Dymon's Yaoki pages (S41); NSSDCA impacts table (13 Aug 2025) and timeline (10 Jul 2025); CLPS deliveries (Oct 23, 2026, all post-2025 deliveries in the future tense); ESA Argonaut. Not reachable today: intuitivemachines.com (redirect loop), investors.intuitivemachines.com (403), blueorigin.com (429), kasa.go.kr (connection reset), so the Korean lander (S40) rests on the writer's reading. A web search found no landing or attempt after June 2025; a press tracker reports Griffin-1 slipping to January 2027, which no official page states (the web text gives no date). **Confirmed:** Artemis IV is NASA's first crewed landing on every NASA page opened, and every string names only Artemis IV; no string contains a date of an earlier consultation; no new site falls in any zone; every region and zone of the new sites (Resilience F; Reiner Gamma, Nassau D by centre; Nobile, Shackleton B by centre) agrees with my own placement; every figure of the strings and of the new DECISIONS.md section reproduces with my own code (Rover 10,192 / 9,888 of 10,337, similarity 93.29 / 99.72, slope gap 0.408 / 0.104 deg, roughness 5.34 / 1.55 m, 87.3 % of 9,790, +4.29; Solar 6,360 / 18,776 / 18,776, 12,416 / 12,416 of 12,417, E19334; polar maxima 2.475 / 2.451; 4.1368 - 0.6 = 3.5368, 16,496 cells below, all 10,800 polar cells; regional medians as in the table above; south-polar Rover twins and maria Solar twins identical to the bundle). The 4.1368 was re-derived with my own Kepler-weighted insolation integral (the ranked Earth site at 89.5 S). **Corrected:** (1) `zone_why.solar` said the maria have "the most sunlight in our data", but equatorial ground outside the maria (abs(lat) <= 30, 14,914 cells) has the same sunlight (area-weighted median 10.11 against 10.02; the table maximum 10.395 is reached in both): it now says "sunlight as high as anywhere in our data", and "under the 3.54 needed" became "below the 3.54 our sites need" (65 words); (2) the far-side and near-side Solar strings now say "more sunlight on average", because E and F reach 75 degrees of latitude; (3) the glosses follow; (4) DECISIONS.md point 4 records the same nuance, point 1 the engine's final Lunar base figures (identical to the expected ones), and the IM-2 note adds Yaoki (S41); (5) the test now also recomputes the Rover north/south figures and the 3.54 from the tables and the bundle and forbids "the most sunlight"; changing 0.41 to 0.51 in a string and its figure, or 9,888 to 9,889 in a string, makes it fail.

**Resumed pass of the second check (2026-11-15, 08:40 UTC).** Re-read the pages fetched today (Artemis III "Crewed Demonstration" and "return to the Moon on Artemis IV"; blog of Oct 23, 2026 "first Artemis mission on the lunar surface"; ispace Mission 2 "NOT COMPLETED"; Lunar Outpost "preventing MAPP's deployment"; CNSA 2026-08-23). Re-ran `fc.py` against the bundle rebuilt at 08:32: output byte-identical (Rover and Solar twins still identical to the bundle). Re-checked equatorial ground outside the maria: 14,914 cells, median 10.108 against 10.017, maximum 10.395 in both. Tests: 7 passed; changing "vs 8" to "vs 7" in `outside.solar.F` and its figure makes 3 fail. Nothing corrected in this pass. Found: the rebuilt bundle `app/public/data/v2/mission_zones.json` (08:32:32) holds an older copy of `zone_why.solar`, `outside.solar.E` and `outside.solar.F` (with "the most sunlight in our data"); the engine must re-export it from the current json.
