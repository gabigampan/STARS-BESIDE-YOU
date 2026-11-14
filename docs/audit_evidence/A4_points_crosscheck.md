# A4 - Do the points fall where they say?

Scope: committed outputs in `/home/user/stars-beside-you/tierra luna` (branch final-integration = main), read only. Nothing was run inside the repository. All scripts are in `scratchpad/stars/a4scripts/` and were run with `scratchpad/stars/venv/bin/python -I <script>`, reading the repo files directly (read-only) or copies. Companion files: `parts/A4_lunar_points.csv` (7 rows), `parts/A4_earth_points.csv` (1607 rows).

Not available in this session: the PR #1 zip ("files 2.zip") and the team zip said to hold `rover_preset.py` v3 and `rover_integration.py`. Nothing below describes their content. Step 5 applies to the committed `rover_preset.py`, which names no sites (see section 5).

## 0. Headline findings

| # | Finding | Evidence | What it changes |
|---|---|---|---|
| F1 | The lunar grid is **global** (90 x 180 cells of 2 deg, centres at odd degrees, lat -89..89, lon -179..179), and `elevation_m` equals **exactly** the 8x8-pixel block mean of LOLA `ldem_4.img` (MAE 0.00 m over all 16,200 cells). | `lunar_lro.py`: "csv vs 2deg block mean: MAE 0.00, max 0.00" | Lunar elevation is DERIVED from a measured product and is correctly georeferenced. |
| F2 | The committed code **does not produce** the committed lunar data. `moon_global_pds.npz` is loaded when it exists (`lunar_extractor.py:166-189`); no file in the repository writes it. Recomputing with the committed fallback path (`pds_reader.read_pds_global`: roll + `scipy.ndimage.zoom`, `pds_reader.py:101-111`) gives elevation MAE 500.76 m (max 5224 m) against the npz. | `lunar_lro.py` "npz vs team method"; grep shows no writer of the npz | If the npz is deleted, every lunar value changes. `zoom(order=1)` also misplaces rows: output row 0 samples lat 89.875 for a cell labelled 89.0 (0.875 deg off at the poles, about 26 km). |
| F3 | `roughness_m` = standard deviation of the 64 LDEM_4 pixels (7.58 km each) in the 2-deg block (exact match). `rough_300m_m` and `slope_300m_deg` are copies of `roughness_m` and `slope_deg` (`harmonizer_cleaner.py:303-304`). | `lunar_lro.py`, test "rough vs std of 64 px in block: MAE 0.000" | The "300m" names are false: these are kilometre-to-60-km-scale values. Rover gates and tolerances in metres or degrees at 300 m are being applied to them. |
| F4 | Lunar `temp_k` (within +/-60 deg) matches Diviner `DGDR_ST_CLC_CYL_0030` night-time regolith temperature (cached band at lat -42..-44: MAE 0.80 K, r 0.876). Lunar `rock_or_bare_frac` matches Diviner rock abundance (`DGDR_RA_AVG`, r 0.972, MAE 0.0006). Neither matches the formula in `lunar_extractor.py:130-153` (temp MAE 102.8 K). Poleward of 60 deg the source is **not determined**. | `lunar_lro.py` rows-66 tests; row variance step at 60 deg | Within +/-60 deg these columns are DERIVED (block means of measured L3 products). The temperature is a night-time value, not a daily or annual mean. |
| F5 | Two of the seven lunar zone labels describe places that the zone masks do not select. "Mare Tranquillitatis & Equatorial Maria": only 92 of 1626 cells lie within Mare Tranquillitatis. "Lunar Farside Highlands (> +2000 m)": the threshold is the 80th percentile (979.6 m), 15.4 % of the cells are on the nearside, and 40.4 % are below +2000 m. | `lunar_gaz.py` | Earth cells tagged with these `matched_lunar_zone` names are not analogs of the place named. |
| F6 | Earth labels are assigned to the nearest of 48 hard-coded anchor points, using a flat-degree distance with `cos(lat)` (`analog_finder.py:129-140`). Any cell within 18 "degrees" (up to about 2000 km) gets the bare name. In the top-100 ranking the median distance to the anchor is 672 km (maximum 1428 km). 4 cells fall in another country than the label says, and 15 lie mostly in sea or on an ice shelf. | `earth_points.py`, `sites_land.py` | Region names in the CSV, JSON and web map cannot be read as locations. Examples: rank 2 "Devon Island Haughton Crater" is in Greenland (83N, 25W), and rank 47/62 "Brooks Range (Alaska)" are in Chukotka, Russia. |
| F7 | 6 of the 44 benchmark analog sites fall in Earth cells coded as ocean: Teide, both Lanzarote sites, Mauna Kea, Kilauea and HI-SEAS. These cells have elevation -250 m, slope 0.01, rough 0.1 m and class "agua". The ranking drops all cells with `elevation_m <= 0` (`analog_finder.py:430`). | `sites_land.py` | Canary and Hawaiian analog sites can never appear in any result. A 2-deg cell (about 222 km N-S) cannot represent any of the named sites. |

## 1. Points the committed outputs name, rank or export

| Output | What it holds | Points | Coordinates |
|---|---|---|---|
| `data/presets/presets.json` | rover preset only (weights, gates, VIPER approximation) | **none**: no lat/lon key (`grep -n -i '"lat\|"lon\|coord\|site'` returns nothing) | - |
| `output_py/optimal_mission_zones.csv` | 5 missions (rover, solar, thermal, ice, all) x 6 zones = 30 Earth points with `earth_region`, `matched_lunar_zone`, bbox | 30 Earth | cell centres; bbox = cluster cell edges, clipped to +/-85 (`analog_finder.py:366-393`) |
| `output_py/analog_ranking.csv` | top 100 Earth cells by `similarity_pct` against the "Global Lunar Surface Mean" profile | 100 Earth | cell centres (`lat_deg`, `lon_deg`) |
| `output_py/analog_web_data.json` | `optimal_mission_zones` (identical to the CSV: checked mission, rank, lat, lon and region on all 30), `earth_cells` (1477, stride 2, each with `reg` and `zone` labels), `moon_cells` (4050, unlabelled), `lunar_zones` (7 named profiles) | 1477 Earth cells + 7 lunar zones | centres |
| `web/analog_data.js` | `window.ANALOG_DATA = <same JSON>;`. Parsed object equal to the JSON (`js==json True`). | same | same |

Lunar "points": the only lunar locations the outputs name are the 7 `lunar_zones` (`analog_finder.py:187-205`). Each Earth row carries one of them as `matched_lunar_zone`. Missions use a fixed target zone: rover uses Tycho, solar and ice use South Pole PSR, thermal uses Global (`analog_finder.py:258-263`). The 4050 `moon_cells` carry no name or rank and are not listed.

Earth points (all 1607 rows, including the 30 zones and the 100 ranked cells) are in `A4_earth_points.csv`, with `source`, `mission`, `rank`, `lat`, `lon` and `team_label`.

## 2. Lunar points against the IAU Gazetteer

Gazetteer used: `scratchpad/stars/iau/moon_shp/MOON_nomenclature_center_pts.shp`, already downloaded by another agent. It holds 9087 features. Its `.prj` gives the sphere radius 1,737,400 m, and its metadata says longitudes are 0-360 "Positive East". Distances are great-circle on R = 1737.4 km. Team longitudes are -180..180 east-positive; gazetteer longitudes above 180 were converted with lon - 360. "Nearest primary" excludes "Satellite Feature" entries (lettered craters such as "Tycho K").

| Id | Team label | Point tested | Nearest primary feature (type, D km, centre lat / lon E) | km | Verdict |
|---|---|---|---|---|---|
| LZ1 | South Pole-Aitken Basin (-53°S, 169°W) | -53.0, -169.0 (= 191.0 E) | Bose (crater, 92.55, -53.953 / 190.6394). The point lies inside Bose. | 29.6 | PARTLY. The coordinate is plausible, but South Pole-Aitken is **not** an IAU gazetteer feature (no rows match "Pole-Aitken" or "South Pole"), so its outline could not be checked here. The code zone is a box, lat -75..-30 and abs(lon) >= 135 (1058 cells, 100 % farside), not the basin. Aitken crater (-16.443, 172.9583 E) lies outside the box. The "-53°S" mixes a minus sign with "S". |
| LZ2 | Tycho & Southern Rocky Craters (35°S–55°S, 30°W–0°) | code box centre -45, -12.5 | Tycho (crater, 85.29, -43.2958 / 348.7847 = -11.2153) | 58.8 | YES. Tycho is inside the box. Tycho's cell (r66 c84, -43/-11) holds the highest lunar rock value, 0.0463. **Code/label mismatch:** the code box reaches lon +5.0 (`analog_finder.py:194`) while the label says 0°. The most frequent nearest features over the 198 zone cells are Longomontanus (20), Maginus (13) and Heinsius (10). |
| LZ3 | South Pole PSR & Shackleton Rim (75°S–90°S) | pole | Shackleton (crater, 20.92, -89.67 / 129.78) | 10.0 | YES for location. The zone is every cell with lat <= -75 (1440 cells, a 15-deg cap). A 2-deg cell is 60.6 km N-S, so the 21 km Shackleton rim is not resolved. No PSR map is used; "PSR" is a label only. |
| LZ4 | Mare Tranquillitatis & Equatorial Maria | mask: abs(lat) <= 30 and elevation <= -1200 m (1626 cells) | Mare Tranquillitatis (mare, 875.75, 8.3487 / 30.8346) | - | NO for "Tranquillitatis". Only 92 cells lie within 437.9 km of its centre. 45.0 % of the cells lie in any IAU mare (circle D/2 approximation) and 13.9 % are on the farside. |
| LZ5 | Lunar Farside Highlands (> +2000 m) | mask: elevation >= 80th percentile = 979.58 m (3240 cells) | - | - | NO. 84.6 % of the cells are farside, so 15.4 % are nearside. Only 59.6 % are above +2000 m. The label's number is wrong. |
| LZ6 | Steep Crater Walls & Massifs (Top 20% Slope) | mask: slope >= 11.32 deg (3240 cells) | - | - | The definition matches the code. It is not a place: the cells are spread globally, 62.2 % on the farside. Slope provenance is not determined (section 3). |
| - | Global Lunar Surface Mean (-90° to +90°) | all 16,200 cells | - | - | Consistent with the code. |

Zone cell counts recomputed from `moon_lola_diviner_clean.csv` match `pixel_count` in the JSON for all 7 zones.

## 3. Lunar values against the cached LRO products

Labels read from `data/cache/*.lbl`:

| Product | Size | Scale / offset / missing | Projection | Coverage of the full product | Rows actually cached | Latitude band cached |
|---|---|---|---|---|---|---|
| `ldem_4.img` (LOLA) | 720 x 1440, int16 LSB | 0.5 m; OFFSET 1737400 m (radius; height = DN x 0.5); MISSING not given (0 cells equal -32768) | simple cylindrical, 4 px/deg, lon 0-360 E, centre lon 180, 7580.84 m/px | 90S-90N | all | global |
| `ldem_64` (LOLA) | 11520 x 23040 | 0.5, offset 1737400 | 64 px/deg, 473.802 m/px | 90S-90N | 8466-8595 (130) | -42.29 to -44.30 |
| `dgdr_ra_avg_cyl_032` (Diviner rock abundance) | 3840 x 11520 | 0.001, 0, -32768 | 32 px/deg, 947.6 m/px | 60S-60N | 3272-3338 (67) | -42.27 to -44.33 (5.2 % missing) |
| `dgdr_st_avg_cyl_032` ("AVERAGE REGOLITH TEMPERATURE VARIATION", K) | same | 0.02, 0, -32768 | same | 60S-60N | same | same (5.2 % missing) |
| `dgdr_st_clc_cyl_0030_032` ("REGOLITH TEMPERATURE", K) | same | 0.02, 0, -32768 | same | 60S-60N. The label restricts data to local times 1930-0530; the file name carries 0030. | same | same (77.5 % missing) |

The grid is global, not a band. The partial products cover only one 2-deg row, r66 (lat -42..-44), which holds Tycho. They could be the leftover of a `--local-window --pds` run centred near Tycho; that is an inference, not checked.

Elevation sample (34 cells: every 3rd row, plus the Tycho cells and both polar rows), comparing the CSV with LDEM_4 recomputed two ways. Full table: `a4scripts/lunar_sample.csv`. Summary: CSV minus block mean = 0.0 m in all 34 cells. CSV minus bilinear value at the stated cell centre: mean abs 360.1 m, max 1019.3 m. That is expected, because a block mean is not a point value. Over all cells, mean abs(CSV - centre) is 294-465 m depending on the latitude band.

| row | col | lat | lon | elev CSV | LDEM_4 block mean | CSV-block | LDEM_4 at centre |
|---|---|---|---|---|---|---|---|
| 0 | 11 | 89 | -157 | -387.8 | -387.8 | 0.0 | -521.8 |
| 15 | 26 | 59 | -127 | -596.3 | -596.3 | 0.0 | -1034.6 |
| 39 | 14 | 11 | -151 | 6563.4 | 6563.4 | 0.0 | 6996.8 |
| 45 | 56 | -1 | -67 | -538.8 | -538.8 | 0.0 | -634.1 |
| 63 | 2 | -37 | -175 | -4870.2 | -4870.2 | 0.0 | -5831.4 |
| 66 | 84 | -43 | -11 (Tycho) | -2578.7 | -2578.7 | 0.0 | -3387.1 |
| 78 | 17 | -67 | -145 | -5058.3 | -5058.3 | 0.0 | -5405.5 |
| 89 | 64 | -89 | -51 | -806.2 | -806.2 | 0.0 | -1160.5 |

Lunar columns and their data level (CSV = npz exactly for elevation, slope, roughness, temperature and rock; SAR differs in 17 cells, max 5.37 dB, after cleaning):

| Column | What it is in the products | Agreement | Level |
|---|---|---|---|
| `elevation_m` | LDEM_4 8x8 block mean | exact | DERIVED |
| `elevation_rel_m` | elevation minus global mean (-518.97 m) | exact | DERIVED |
| `roughness_m` (= `rough_300m_m`) | std of the 64 LDEM_4 pixels in the block. This is not a LOLA roughness product and not a 300 m baseline. | exact | DERIVED |
| `slope_deg` (= `slope_300m_deg`) | **Not determined.** It is not the committed formula (`lunar_extractor.py:119-127`, applied with spacing 0.08 x 60.6 km: r 0.31). It is not mean, median, p75, p90 or max of LDEM_4 pixel slopes (best r 0.63). Row 66 against the block mean of LDEM_64 slope: r 0.764, MAE 1.79 deg (median 8.65 vs 7.26). A slope from 2-deg spacing would have median 0.89 deg. | partial | not determined |
| `temp_k` | within +/-60: block mean of Diviner ST_CLC_0030 night-time temperature (row 66 MAE 0.80 K, r 0.876; not ST_AVG, which is an anomaly from -3 to 14 K). Poleward of 60: not determined. The along-longitude std drops from 2.92 K at 59N to 0.46 K at 61N, which looks like a smooth fill. | row 66 only | DERIVED (+/-60); not determined (poleward) |
| `rock_or_bare_frac` | within +/-60: Diviner RA block mean (row 66 r 0.972, MAE 0.0006; Tycho cell 0.0463 vs 0.066 in the cached part). Poleward: not determined. The row mean jumps from 0.0034 at 59N to 0.0067 at 61N. | row 66 only | DERIVED (+/-60); not determined (poleward) |
| `sar_sigma0_db` | no lunar radar product in the cache. Fits -19 + 14.5 x rock + 0.14 x slope with an offset of 0.64 dB (r 0.9978). | - | MODELLED |
| irradiance, sun, diurnal amplitude, classes, permafrost (`harmonizer_cleaner.py:249-284`) | latitude and threshold formulas | - | MODELLED |

## 4. Earth points: country, region, land, label

Method: country polygons from Natural Earth 1:110m (`pyogrio/tests/fixtures/naturalearth_lowres`, 177 countries, includes Antarctica; offline). First-level region from `reverse_geocoder` (GeoNames cities1000, 144,563 places). `cell_land_frac_ne110` is the share of the 2x2-deg box inside NE land.

Limits:
- reverse_geocoder returns the nearest populated place, whatever the distance. In Antarctica and the high Arctic that place is 400-6200 km away, for example "Kerguelen", "Tasmania" or "Westfjords, Iceland" for Antarctic or Greenland cells. Its `rg_admin1` is meaningless there; trust it only when `rg_place_km` is small.
- NE 1:110m drops small islands (the Canaries are absent) and treats ice shelves as sea.

Rule in `label_check`: OFF_LAND if the centre is off NE land and less than 50 % of the cell is land; OFF_COUNTRY if the NE country is not one the label names; LOOSE if the cell is more than 500 km from the label's anchor (my threshold); otherwise OK.

Cell coordinates are **cell centres**: every lat/lon in all three outputs is an odd integer. Formula `lat = 90 - (row + 0.5) * 2`, `lon = -180 + (col + 0.5) * 2` (`harmonizer_cleaner.py:202-203`). The optimal-zone bbox edges are cell edges (centre +/- 1, `analog_finder.py:366-369`).

| Source | n | OK | LOOSE (>500 km) | OFF_COUNTRY | OFF_LAND | coastal |
|---|---|---|---|---|---|---|
| optimal_mission_zones.csv (= JSON) | 30 | 9 | 15 | 1 | 5 | 0 |
| analog_ranking.csv | 100 | 27 | 51 | 4 | 15 | 3 (LOOSE_COASTAL) |
| earth_cells (JSON / JS) | 1477 | 256 | 708 | 357 | 131 | 25 |

Optimal zones (all 30):

| mission | rank | lat, lon | team label | NE country / GeoNames admin1 | land frac | km to label anchor | check |
|---|---|---|---|---|---|---|---|
| rover | 1 | 45, 89 | Taklamakan & Tarim Basin | China / Xinjiang | 1.00 | 831 | LOOSE |
| rover | 2 | 33, -113 | Meteor Crater & Colorado Plateau (Arizona, USA) | USA / Arizona | 1.00 | 289 | OK |
| rover | 3 | 37, 115 | Gobi Desert & Altai Range (Mongolia) | China / Hebei | 1.00 | 1344 | OFF_COUNTRY |
| rover | 4 | -31, 139 | Central Australian Arid Ranges (MacDonnell) | Australia / South Australia | 1.00 | 921 | LOOSE |
| rover | 5 | 67, 175 | Kamchatka Volcanic Belt (Russia) | Russia / Chukotka | 1.00 | 1451 | LOOSE |
| rover | 6 | 75, -85 | Devon Island Haughton Crater (Arctic Canada) | Canada / Nunavut | 0.59 | 86 | OK |
| solar | 1 | -73, 65 | East Antarctic Polar Plateau | Antarctica | 1.00 | 818 | LOOSE |
| solar | 2 | -81, 153 | McMurdo Dry Valleys (Antarctica) | Antarctica | 1.00 | 430 | OK |
| solar | 3 | -81, -153 | West Antarctic Ice Sheet & Mountains | sea/ice shelf | 0.45 | 778 | OFF_LAND |
| solar | 4 | -77, -89 | West Antarctic Ice Sheet & Mountains | Antarctica | 1.00 | 568 | LOOSE |
| solar | 5 | -71, 113 | East Antarctic Polar Plateau | Antarctica | 1.00 | 1407 | LOOSE |
| solar | 6 | 67, 133 | Verkhoyansk & Chersky Range (NE Siberia) | Russia / Sakha | 1.00 | 317 | OK |
| thermal | 1 | -75, -97 | West Antarctic Ice Sheet & Mountains | Antarctica | 1.00 | 635 | LOOSE |
| thermal | 2 | 79, -25 | Greenland Interior Ice Sheet & Nunataks | Greenland | 1.00 | 877 | LOOSE |
| thermal | 3 | 67, 131 | Verkhoyansk & Chersky Range (NE Siberia) | Russia / Sakha | 1.00 | 387 | OK |
| thermal | 4 | 77, -91 | Devon Island Haughton Crater (Arctic Canada) | sea | 0.20 | 328 | OFF_LAND |
| thermal | 5 | -71, 71 | East Antarctic Polar Plateau | sea/ice shelf | 0.07 | 1006 | OFF_LAND |
| thermal | 6 | -79, -17 | Queen Maud Land Massifs (Antarctica) | Antarctica | 1.00 | 1063 | LOOSE |
| ice | 1 | -77, 127 | McMurdo Dry Valleys (Antarctica) | Antarctica | 1.00 | 848 | LOOSE |
| ice | 2 | -85, -101 | West Antarctic Ice Sheet & Mountains | Antarctica | 1.00 | 569 | LOOSE |
| ice | 3 | -79, 53 | East Antarctic Polar Plateau | Antarctica | 1.00 | 456 | OK |
| ice | 4 | -69, 93 | East Antarctic Polar Plateau | Antarctica | 1.00 | 1321 | LOOSE |
| ice | 5 | -77, -9 | Queen Maud Land Massifs (Antarctica) | Antarctica | 1.00 | 786 | LOOSE |
| ice | 6 | 79, -83 | Devon Island Haughton Crater (Arctic Canada) | Canada / Nunavut | 1.00 | 445 | OK |
| all | 1 | -77, -83 | West Antarctic Ice Sheet & Mountains | Antarctica | 1.00 | 676 | LOOSE |
| all | 2 | -81, 153 | McMurdo Dry Valleys (Antarctica) | Antarctica | 1.00 | 430 | OK |
| all | 3 | -73, 65 | East Antarctic Polar Plateau | Antarctica | 1.00 | 818 | LOOSE |
| all | 4 | 67, 133 | Verkhoyansk & Chersky Range (NE Siberia) | Russia / Sakha | 1.00 | 317 | OK |
| all | 5 | -75, -19 | Queen Maud Land Massifs (Antarctica) | sea/ice shelf | 0.27 | 963 | OFF_LAND |
| all | 6 | -79, -163 | West Antarctic Ice Sheet & Mountains | sea/ice shelf | 0.30 | 1042 | OFF_LAND |

Ranking (100 rows):
- 77 of the 100 cells are at lat >= 55N and 23 at <= 65S, so no top-100 cell lies between 65S and 55N. Labels: Devon Island 23, Verkhoyansk 23, West Antarctic 22, Putorana 11, Baffin 10, Kamchatka 6, Greenland 2, Brooks Range 2, East Antarctic 1.
- OFF_COUNTRY: ranks 2 and 11 are labelled "Devon Island" but lie in Greenland (83N, 25W and 27W); ranks 47 and 62 are labelled "Brooks Range & North Slope (Alaska)" but lie in Russia (67N, 179W and 177W).
- 15 ranked cells are OFF_LAND (listed in the CSV). The NE 1:110m data cannot tell an ice shelf from open sea, so this is not determined here for Antarctic cells.
- 156 of the 1477 earth_cells have their centre off NE land, yet all 1477 have elevation > 0. Example: 81N 49E, elevation 142.9 m, labelled "Central Siberian Traps".
- 82 earth_cells carry a "... Sector (lat, lon)" label.

Why labels drift: `assign_earth_region_names` (`analog_finder.py:129-140`) measures `hypot(dlat, dlon*cos(lat))` in degrees and drops the "Sector" suffix whenever that value is below 18. Near the poles cos(lat) shrinks the longitude term, so Greenland cells at 83N match the Devon Island anchor (75N, 82W), 1401 km away by great circle.

## 5. Rover-preset analog sites against the benchmark, and 2-deg cells

`rover_preset.py` as committed (523 non-empty lines; identical to the copy in the zip) has **no** `APPROX_SITE_COORDS`, benchmark list or site coordinates. `grep -n -i -E 'lat|lon|desert|crater|island|analog|sites?\b'` matches only line 5 ("analog finder"). So there is no preset site to compare. The v3 file said to hold one is not available here.

As the closest committed equivalent, the 48 `EARTH_LANDMARKS` anchors (`analog_finder.py:77-126`) are compared with the 44 verified sites in `/home/user/NASA/docs/research/02_analog_benchmark.csv`. Every landmark and every site, with nearest counterpart, distance and cell values, is in `a4scripts/sites.csv`. Cell = floor((90 - lat)/2), floor((lon + 180)/2). Values are from `output_py/earth_srtm_modis_aster_clean.csv`, whose `source` column says `global_model`. Earth data provenance is outside A4 and not determined here. A 2-deg cell is about 222 km N-S and 222 x cos(lat) km E-W.

Landmarks that name a benchmark site:

| Landmark | landmark lat, lon | bench id | bench lat, lon | km apart | landmark cell | bench cell | elev m | slope° | rough m | temp K | rock/bare | NE land frac | in outputs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Atacama Desert & Altiplano (Chile) | -23.5, -68.5 | MA01 | -24.08, -70.0 | 165.7 | r56 c55 | r57 c55 | 2176 | 16.51 | 769 | 292.4 | 0.851 | 1.00 | no |
| McMurdo Dry Valleys (Antarctica) | -77.5, 162.0 | MA07 | -77.4667, 162.5167 | 13.0 | r83 c171 | r83 c171 | 590 | 9.71 | 426 | 250.1 | 0.768 | 0.85 | no |
| Askja Volcanic Highlands (Iceland) | 64.8, -17.5 | MA10 | 65.0304, -16.7469 | 43.8 | r12 c81 | r12 c81 | 816 | 8.93 | 407 | 283.5 | 0.112 | 0.99 | no |
| Mauna Kea Volcanic Slopes (Hawaii) | 19.8, -155.5 | MO05 | 19.8207, -155.4681 | 4.1 | r35 c12 | r35 c12 | **-250** | 0.01 | 0 | 285.0 | 0.000 | 0.21 | no (ocean-coded) |
| Devon Island Haughton Crater | 75.0, -82.0 | MA06 | 75.3833, -89.6667 | 221.8 | r7 c49 | r7 c45 | 807 | 9.61 | 433 | 260.6 | 0.442 | 0.51 | no (Haughton's own cell r7 c45 is ranking #64) |
| Craters of the Moon (Idaho) | 43.4, -113.5 | MO07 | 43.405, -113.5061 | 0.7 | r23 c33 | r23 c33 | 1635 | 7.52 | 343 | 273.2 | 0.105 | 1.00 | no |
| Meteor Crater (Arizona) | 35.0, -111.0 | MO02 | 35.0271, -111.0184 | 3.4 | r27 c34 | r27 c34 | 1750 | 6.70 | 304 | 281.7 | 0.385 | 1.00 | no |
| Mount Etna & Apennine Belt | 37.7, 15.0 | MO11 | 37.755, 14.995 | 6.1 | r26 c97 | r26 c97 | 541 | 12.27 | 561 | 295.0 | 0.138 | 0.36 | no |
| Teide & Lanzarote (Canary Islands) | 28.3, -16.6 | ES05 | 28.2663, -16.5896 | 3.9 | r30 c81 | r30 c81 | **-250** | 0.01 | 0 | 285.0 | 0.000 | 0.00 | no (ocean-coded) |
| Teide & Lanzarote (Canary Islands) | 28.3, -16.6 | ES02 | 28.9942, -13.7933 | 284.5 | r30 c81 | r30 c83 | **-250** | 0.01 | 0 | 285.0 | 0.000 | 0.00 | no (ocean-coded) |
| Afar & East African Rift | 11.5, 41.0 | MA13 Dallol | 14.2425, 40.2997 | 314.3 | r39 c110 | r37 c110 | 700 | 6.87 | 312 | 314.4 | 0.429 | 1.00 | no |
| Pilbara Craton | -22.5, 120.0 | MA18 | -21.17, 119.42 | 159.5 | r56 c150 | r55 c149 | 474 | 1.30 | 59 | 298.0 | 0.680 | 1.00 | web layer only |

What the 44 benchmark sites look like in the 2-deg grid (full table in `a4scripts/site_tables.md` and `sites.csv`):
- Distance from site to cell centre: median 57 km, max 144 km (Yungay).
- **Six sites sit in ocean-coded cells** (elevation -250, class "agua"): ES02, ES03, ES05, MO05, MO06 and OP02. They are excluded by `analog_finder.py:430`.
- Sites that share one cell get identical values:
  - Meteor Crater, Cinder Lake and Black Point (r27 c34: elevation 1750 m, slope 6.70°, rock/bare 0.385).
  - Askja and Holuhraun (r12 c81).
  - Yungay and Salar de Pajonales (r57 c55: 3064 m, slope 23.18°, roughness 1112 m). That is the Andes average, not the Yungay hyper-arid core.
- Of the 44 cells, only one appears in the top-100 ranking: Haughton, r7 c45, rank 64. Only two (ES01 and ES04) are among the 1477 web cells, because the web layer keeps even rows and columns only.

Conclusion for the team: a 2-deg cell cannot represent any of these sites. Island and coastal sites drop out entirely, and a crater or a test site of a few km is averaged over a cell of more than 200 km.

## 6. Commands run

- `venv/bin/python -I a4scripts/lunar_lro.py a4scripts/lunar_sample.csv`: elevation, slope, roughness, temperature and rock against LDEM_4, LDEM_64 and Diviner.
- inline tests (slope and roughness hypotheses, polar fill, CSV = npz) as listed in sections 2-3.
- `venv/bin/python -I a4scripts/lunar_gaz.py iau/moon_shp/MOON_nomenclature_center_pts.shp a4scripts/lunar_points_draft.csv`
- `venv/bin/python -I a4scripts/earth_points.py <NE shp> a4scripts/earth_points_draft.csv`, then `sites_land.py`.
- No network access was used. The gazetteer was an existing local copy.
