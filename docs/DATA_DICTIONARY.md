# Data dictionary (Phase 0)

Stars Beside You, NASA Space Apps Challenge 2026. Written 2026-11-14 for the audit of `tierra luna/` on branch `final-integration` (commit 618bc45). Machine-readable version: [`data_dictionary.csv`](data_dictionary.csv) (one row per variable and body, 62 rows, same content plus metadata columns and the derived outputs).

**What the observed values describe.** Minimum, maximum, class counts and missing counts were recomputed from the committed file `tierra luna/output_py/earth_moon_harmonized_clean.csv` (32,400 rows: 16,200 EARTH, 16,200 MOON) with `docscripts/make_dict.py` in a scratch copy. That file is the output of `python main.py --pds`, not of the default `python main.py` (AUDIT.md section (a)). No cell has a missing value in any column. The six downstream outputs at the end of the CSV (`similarity_pct`, `feature_distance`, `workable_rover`, `score_rover`, `earth_region`, `matched_lunar_zone`) were computed over `output_py/analog_ranking.csv` (100 rows).

**Where the levels come from.** The level is judged by what the code does, not by the label or README:

- Earth bands come from `data/cache/earth_global_real.npz`, which no code in the repository produces (`earth_extractor.py:134-158`).
- Moon bands come from `data/cache/moon_global_pds.npz`, which no code in the repository produces either (`lunar_extractor.py:61-84`).
- The twelve mission columns are formulas in `harmonizer_cleaner.py:241-313`.

Evidence for the individual cases is in [audit_evidence/A2_data_audit.md](audit_evidence/A2_data_audit.md) and [audit_evidence/A4_points_crosscheck.md](audit_evidence/A4_points_crosscheck.md).

## 1. What each level means and how the interface must show it

| Level | Meaning in this project | Example here | How the interface must show it |
|---|---|---|---|
| MEASURED | Read from a downloaded official product at the resolution used, with the product ID known | none in the committed outputs | Plain value with the product ID and date in the tooltip or card. This is the only level that may be called "NASA data" without qualification. |
| DERIVED | Computed by a stated formula from a MEASURED value | Moon `elevation_m` = 2-degree block mean of LOLA LDEM_4; Moon `roughness_m` = standard deviation of the 64 LDEM_4 pixels in the cell | Value plus "derived from <product> by <formula>". The formula is one line in the tooltip. |
| MODELLED | Synthetic or estimated by a closed-form or invented formula, a constant, or a random generator | all 12 mission columns (`irradiance_kwh_m2_day`, `tmin_c`, ...); Moon `sar_sigma0_db` | Visibly different styling (for example hatched or italic) with a "model estimate, not data" badge. Never placed under a heading or badge that says real, NASA, LRO or MODIS. |
| UNDOCUMENTED ORIGIN | The value is loaded from a file whose producer, product and processing are not in the repository | every Earth band; Moon `slope_deg`, `temp_k`, `rock_or_bare_frac` | Greyed, with "origin undocumented" and a link to the open question in AUDIT.md. Must not be used for a public claim until the team documents the source. |

Two extra rules for the interface:

- When one score mixes levels, it takes the **weakest** level among its inputs. Every mission pass flag and mission score is therefore at best MODELLED, and the similarity percentage is UNDOCUMENTED ORIGIN.
- The labels `source = real_PDS` and `source = global_model`, and the web badge "Real LRO LOLA + Diviner vs. NOAA ETOPO1/SRTM30 + NCEP Global" (`web/index.html:372`), must not be shown as they stand (AUDIT.md section (e)).

**Where the auditors disagreed on levels, and what this document uses:**

- **Moon `elevation_m`.** A2 calls it MEASURED and A4 calls it DERIVED. Both found it equal to the 8x8 block mean of `ldem_4.img`. This document uses DERIVED: a 2-degree mean is computed from the product, not read from it, and the aggregation is not performed by any code in the repository.
- **Moon `temp_k` and `rock_or_bare_frac`.** A2 says not determined. A4 says DERIVED within 60 degrees of the equator. A4's match rests on the one cached latitude row (-42 to -44 deg), and the cached labels limit the products to 60S-60N (`MAXIMUM_LATITUDE = 60` in `dgdr_*_032_img.lbl`), yet the arrays hold values up to +-89 deg. This document uses UNDOCUMENTED ORIGIN, with A4's partial match noted in the CSV. (R2 lists a newer release of the rock-abundance product that covers 80S-80N; that is not the release cached in the repository, whose labels have `STOP_TIME = 2010-11-30`.)
- **Moon `sar_sigma0_db`.** A2's fit is used: the npz equals `-19.2 + 45*rock + 0.22*slope` exactly (max residual 2e-6, re-run for this document). A4's fit of the fallback formula `-19 + 14.5*rock + 0.14*slope` plus a 0.64 dB offset is approximate (r 0.998). Both agree that the value is MODELLED.
- **Earth `sar_sigma0_db`.** It fits a formula on land with R2 = 0.990, but not exactly, so this document uses UNDOCUMENTED ORIGIN.
- **Moon `sun_elev_max_deg`.** It is MODELLED, with correct geometry: `90 - |lat| + 1.54` uses the official 1.54 deg tilt (R2, PIA13720; R3 F4), but its only input is the cell-centre latitude, not a measured value, and it ignores topography and horizon. (The first version of this document called it DERIVED; that does not meet the definition in the table above, which requires a MEASURED input.) Earth uses `+11.7` where the obliquity is 23.44 deg (R3 F3), so the Earth value is MODELLED with a wrong constant.

## 2. Share of variables by level and body

The count covers 19 physical variables per body: the 7 bands and the 12 mission columns. Metadata (`body, row, col, x_m, y_m, lat_deg, lon_deg, resolution_m, source`) and downstream outputs are excluded.

| Level | EARTH | MOON |
|---|---|---|
| MEASURED | 0 (0 %) | 0 (0 %) |
| DERIVED | 0 (0 %) | 4 (21 %): `elevation_m`, `elevation_rel_m`, `roughness_m`, `rough_300m_m` |
| MODELLED | 10 (53 %): `mask_fraction`, `irradiance_kwh_m2_day`, `sun_elev_max_deg`, `sun_low_frac_0_5deg`, `lst_diurnal_amp_k`, `thermal_inertia_class`, `permafrost_class`, `rain_mm_day`, `wind_max_ms`, `tmin_c` | 11 (58 %): `sar_sigma0_db`, `mask_fraction`, `irradiance_kwh_m2_day`, `sun_elev_max_deg`, `sun_low_frac_0_5deg`, `lst_diurnal_amp_k`, `thermal_inertia_class`, `permafrost_class`, `rain_mm_day`, `wind_max_ms`, `tmin_c` |
| UNDOCUMENTED ORIGIN | 9 (47 %): `elevation_m`, `elevation_rel_m`, `slope_deg`, `roughness_m`, `temp_k`, `rock_or_bare_frac`, `sar_sigma0_db`, `slope_300m_deg`, `rough_300m_m` | 4 (21 %): `slope_deg`, `slope_300m_deg`, `temp_k`, `rock_or_bare_frac` |

**Consequences:**

- No gate and no weighted criterion, in either system, reads a MEASURED or DERIVED Earth value.
- On the Moon, gates would touch two DERIVED values: `elevation_m` (the new common gate `elevation_m >= 1`, which is meaningless on the Moon) and `rough_300m_m` (rover). Lunar cells are never gated in practice: the `mission_scoring.py` CLI keeps only EARTH rows (`mission_scoring.py:266-267`), and `analog_finder.py` gates only Earth cells (`analog_finder.py:504-510`). See FILTERS.md section (d).
- On Earth, 10,273 of 16,200 cells (63.4 %) are ocean. There all seven bands hold constant fill values (`elevation_m` -250, `elevation_rel_m` -1000, `slope_deg` 0.01, `roughness_m` 0.1, `temp_k` 285, `rock_or_bare_frac` 0, `sar_sigma0_db` -24; A2 section 2a). Those fill values are MODELLED.

**If both npz files were deleted** (A2 section 4, A1 section 5.3):

- Earth would become 100 % MODELLED (the seed-101 generator, `earth_extractor.py:160-254`).
- With `--pds`, the Moon would keep LOLA elevation (`ldem_4.img`, resampled by `scipy.ndimage.zoom` at `pds_reader.py:109-111`) and would get formula temperature, rock and radar (`lunar_extractor.py:25-48`).

## 3. Variables, observed values and what the code does

Levels in bold. File references are relative to `tierra luna/`. Classes are counts over 16,200 cells.

| Variable | Body | Unit | Level | Observed min | Observed max | Classes | Missing | Claimed source | What the code does |
|---|---|---|---|---|---|---|---|---|---|
| `elevation_m` | EARTH | m | **UNDOCUMENTED ORIGIN** | -250 | 5274.31 |  | 0 | README.md:39 SRTM gap-filled with ASTER; web/index.html:372 'NOAA ETOPO1/SRTM30' | earth_extractor.py:134-158 loads data/cache/earth_global_real.npz (no producer in repo); 10,273 ocean cells are a constant -250 fill |
| `elevation_m` | MOON | m | **DERIVED** | -7609.7 | 8301.88 |  | 0 | README.md:39 LOLA GDR | lunar_extractor.py:61-84 loads data/cache/moon_global_pds.npz; values equal the 8x8 block mean of data/cache/ldem_4.img exactly (A2 moon2.py, A4 lunar_lro.py) |
| `elevation_rel_m` | EARTH | m | **UNDOCUMENTED ORIGIN** | -1045.72 | 4226.89 |  | 0 | README.md:40 DEM minus local mean | npz array: land = elevation_m - 1047.422, ocean = constant -1000 (A2 npzcheck.py); not recomputed in global mode (harmonizer_cleaner.py:120) |
| `elevation_rel_m` | MOON | m | **DERIVED** | -7090.72 | 8820.86 |  | 0 | README.md:40 DEM minus local mean | npz array = elevation_m - global mean (-518.97 m), exact |
| `slope_deg` | EARTH | deg | **UNDOCUMENTED ORIGIN** | 0.01 | 37.1684 |  | 0 | README.md:41 2D gradient of DEM | npz array; not reproducible from its elevation with the repo formula (corr 0.60, A2) |
| `slope_deg` | MOON | deg | **UNDOCUMENTED ORIGIN** | 1.6914 | 31.4987 |  | 0 | README.md:41; web/index.html:619 'LOLA LDSM_16' | npz array; not the repo formula (corr 0.31) nor LDEM_4 pixel-slope statistics (best r 0.63) (A2, A4) |
| `roughness_m` | EARTH | m | **UNDOCUMENTED ORIGIN** | 0.1 | 1969.87 |  | 0 | harmonizer_cleaner.py:166 'local 3x3 std' | npz array, method not determined; ocean = 0.1 |
| `roughness_m` | MOON | m | **DERIVED** | 7.3542 | 3058.27 |  | 0 | harmonizer_cleaner.py:166 'local 3x3 std' | npz = standard deviation of the 64 LDEM_4 pixels (7.58 km) in each 2-degree cell (A2 moon3.py, A4) |
| `temp_k` | EARTH | K | **UNDOCUMENTED ORIGIN** | 217.358 | 327.52 |  | 0 | README.md:43 MODIS LST x 0.02 with ASTER fallback; web/index.html:622 NOAA NCEP | npz array; ocean = constant 285 |
| `temp_k` | MOON | K | **UNDOCUMENTED ORIGIN** | 43.4538 | 110.431 |  | 0 | README.md:7,43 Diviner night-time regolith temperature | npz array; on the one cached row (lat -42..-44) it matches the block mean of Diviner DGDR_ST_CLC_0030 night temperature (MAE 0.80 K, A4); values exist poleward of 60 deg where the cached product has no data (label MAXIMUM_LATITUDE = 60) |
| `rock_or_bare_frac` | EARTH | fraction | **UNDOCUMENTED ORIGIN** | 0 | 0.98 |  | 0 | README.md:44 ASTER 1 - NDVI | npz array; ocean = 0.0 |
| `rock_or_bare_frac` | MOON | fraction | **UNDOCUMENTED ORIGIN** | 0.0015 | 0.0463 |  | 0 | README.md:44 Diviner rock abundance | npz array; on the cached row it matches Diviner RA block mean (r 0.972, A4); values exist poleward of 60 deg |
| `sar_sigma0_db` | EARTH | dB | **UNDOCUMENTED ORIGIN** | -24 | 0.5853 |  | 0 | README.md:45 C-band SAR | npz array; on land fits -18.29 + 7.97*rock + 0.452*slope with R2 0.990 (A2, rechecked); ocean = -24 |
| `sar_sigma0_db` | MOON | dB | **MODELLED** | -18.6652 | -13.1026 |  | 0 | README.md:45 radar backscatter | npz array = -19.2 + 45*rock + 0.22*slope exactly (max residual 2e-6, rechecked); 17 cells IQR-replaced by harmonizer_cleaner.py:84 |
| `mask_fraction` | EARTH | fraction | **MODELLED** | 0 | 1 |  | 0 | mission_scoring.json:7 'celda con dato suficiente' | harmonizer_cleaner.py:243-247 elev>0: clip(0.35+0.65*min(elev/150,1),0.35,1) else 0 |
| `mask_fraction` | MOON | fraction | **MODELLED** | 1 | 1 |  | 0 | same | harmonizer_cleaner.py:241 constant 1.0 |
| `slope_300m_deg` | EARTH | deg | **UNDOCUMENTED ORIGIN** | 0.01 | 37.168 |  | 0 | name says 300 m baseline; mission_filters.json:12 cites the VIPER limit | harmonizer_cleaner.py:303 copy of slope_deg (2-degree cell) |
| `slope_300m_deg` | MOON | deg | **UNDOCUMENTED ORIGIN** | 1.691 | 31.499 |  | 0 | same | harmonizer_cleaner.py:303 copy of slope_deg |
| `rough_300m_m` | EARTH | m | **UNDOCUMENTED ORIGIN** | 0.1 | 1969.87 |  | 0 | name says 300 m baseline | harmonizer_cleaner.py:304 copy of roughness_m |
| `rough_300m_m` | MOON | m | **DERIVED** | 7.35 | 3058.27 |  | 0 | same | harmonizer_cleaner.py:304 copy of roughness_m |
| `irradiance_kwh_m2_day` | EARTH | kWh/m2/day | **MODELLED** | 1.644 | 7.006 |  | 0 | mission_filters.json:59 'NASA POWER / NOAA NCEP' | harmonizer_cleaner.py:249-255 clip((1.6+4.8*cos_lat^0.75)*(0.78+0.32*bare+0.04*clip(elev/3000,0,1.5)),0.8,8.2) |
| `irradiance_kwh_m2_day` | MOON | kWh/m2/day | **MODELLED** | 1.647 | 5.398 |  | 0 | same | harmonizer_cleaner.py:249-255 same Earth formula applied to the Moon |
| `sun_elev_max_deg` | EARTH | deg | **MODELLED** | 12.7 | 90 |  | 0 | mission_filters.json:64 'solar array elevation envelope' | harmonizer_cleaner.py:256 clip(90-/lat/+11.7,1.5,90); obliquity is 23.44 (R3 F3) |
| `sun_elev_max_deg` | MOON | deg | **MODELLED** | 2.54 | 90 |  | 0 | same | harmonizer_cleaner.py:256 clip(90-/lat/+1.54,1.5,90) |
| `sun_low_frac_0_5deg` | EARTH | fraction | **MODELLED** | 0.028 | 0.2817 |  | 0 | mission_filters.json:69 'Artemis low-horizon grazing illumination regime' | harmonizer_cleaner.py:257 clip(0.028+0.26*(/lat//90)^2.2,0.025,0.35) |
| `sun_low_frac_0_5deg` | MOON | fraction | **MODELLED** | 0.028 | 0.2817 |  | 0 | same | harmonizer_cleaner.py:257 same formula |
| `lst_diurnal_amp_k` | EARTH | K | **MODELLED** | 2.5 | 38.75 |  | 0 | mission_filters.json:94 'MODIS/NCEP' | harmonizer_cleaner.py:262-266 land clip(8+22*bare+0.0022*elev,6,48), ocean 2.5 |
| `lst_diurnal_amp_k` | MOON | K | **MODELLED** | 63.08 | 179.99 |  | 0 | same | harmonizer_cleaner.py:260 clip(180*cos_lat^0.35,25,210) |
| `thermal_inertia_class` | EARTH | category | **MODELLED** |  |  | agua:10273, suelo:2270, hielo:2163, arena:690, regolito:523, roca:281 | 0 | mission_filters.json:103 'LRO Diviner Bandfield et al. (2011)' | harmonizer_cleaner.py:268-274 thresholds on bare fraction, roughness, slope; hielo if T < 261 K; agua if elev <= 0 |
| `thermal_inertia_class` | MOON | category | **MODELLED** |  |  | suelo:16200 | 0 | same | harmonizer_cleaner.py:268-271 same thresholds; Moon rock max 0.046 so every cell is 'suelo' |
| `permafrost_class` | EARTH | category | **MODELLED** |  |  | ninguno:13177, continuo:2387, esporadico:358, discontinuo:278 | 0 | mission_filters.json:129 'IPA Brown et al.' | harmonizer_cleaner.py:280-284 temp_k <= 274.15 (or elev >= 3400 and <= 278) esporadico; <= 270.15 discontinuo; <= 265.15 continuo |
| `permafrost_class` | MOON | category | **MODELLED** |  |  | ninguno:11520, discontinuo:2922, continuo:1758 | 0 | same | harmonizer_cleaner.py:277-279 /lat/ >= 75 and T <= 75 continuo; /lat/ >= 65 and 75 < T <= 90 discontinuo |
| `rain_mm_day` | EARTH | mm/day | **MODELLED** | 0.01 | 4.62 |  | 0 | none in code | harmonizer_cleaner.py:290-294 clip(4.2*(1-bare)^1.8*clip(cos_lat+0.15,0.2,1.1),0.01,12) |
| `rain_mm_day` | MOON | mm/day | **MODELLED** | 0 | 0 |  | 0 | none | harmonizer_cleaner.py:287 constant 0 |
| `wind_max_ms` | EARTH | m/s | **MODELLED** | 4.51 | 12.63 |  | 0 | none in code | harmonizer_cleaner.py:295-299 clip(4.5+0.0012*elev+3.8*(/lat//90)^1.4,2.5,15.5) |
| `wind_max_ms` | MOON | m/s | **MODELLED** | 0 | 0 |  | 0 | none | harmonizer_cleaner.py:288 constant 0 |
| `tmin_c` | EARTH | degC | **MODELLED** | -66.91 | 44.29 |  | 0 | Instruciones filtros solar y temp:36 'estimaciones del modelo' | harmonizer_cleaner.py:300 (temp_k-273.15) - 0.35*lst_diurnal_amp_k |
| `tmin_c` | MOON | degC | **MODELLED** | -251.78 | -219.83 |  | 0 | same | harmonizer_cleaner.py:300 same formula on the night-time temp_k |

## 4. Ranges, sources and use in the old and the new system

**How "use" is defined in this table:**

- **Old system:** "gate" means a hard filter in `mission_filters.json` (or `mask_min`). "Weighted" means the column enters `analog_finder.py` scoring, either as one of the six similarity features (all four missions, through the domain mapping at `analog_finder.py:225-240`) or as a term of the mission `gate_q` (`analog_finder.py:274-310`).
- **New system:** "gate" means a gate or a common gate in `mission_scoring.json`. "Weighted" means a `soft` criterion.

| Variable | Valid range | Reason or source of the range | Old system use (mission_filters.json + analog_finder.py) | New system use (mission_scoring.json) |
|---|---|---|---|---|
| `elevation_m` | Earth -500..9000; Moon -9200..10800 (pipeline cleaning range) | config.py:88,98 (no source cited); LDEM_4 raw range -8878.5..10504 m computed by A2 | not a gate; Earth: land pre-filter elevation_m > 0 before ranking (analog_finder.py:430); Moon: two lunar zone masks (analog_finder.py:187-205) | gate: rover, solar, thermal, ice (common gate) |
| `elevation_rel_m` | Earth -6000..6000; Moon -9000..9000 | config.py:89,99 (no source) | weighted: rover, solar, thermal, ice; similarity feature in all 4 (analog_finder.py:59-66, 225-240) | not used |
| `slope_deg` | 0..90 | geometric definition | weighted: rover, solar, thermal, ice; similarity feature in all 4 (analog_finder.py:59-66, 225-240) | both (gate + weighted): solar |
| `roughness_m` | >= 0; config max 2500 Earth / 3500 Moon | definition; config.py:91,101 | weighted: rover, solar, thermal, ice; similarity feature in all 4 (analog_finder.py:59-66, 225-240) | weighted: solar |
| `temp_k` | > 0 K; config Earth 180..360, Moon 20..420 | absolute zero; config.py:92,102 | weighted: rover, solar, thermal, ice; similarity feature in all 4 (analog_finder.py:59-66, 225-240) | weighted: ice |
| `rock_or_bare_frac` | 0..1 | definition | weighted: rover, solar, thermal, ice; similarity feature in all 4 (analog_finder.py:59-66, 225-240) | weighted: rover, thermal |
| `sar_sigma0_db` | config -35..15 | config.py:94,104 (no source) | weighted: rover, solar, thermal, ice; similarity feature in all 4 (analog_finder.py:59-66, 225-240) | not used |
| `mask_fraction` | 0..1 | definition | gate: rover, solar, thermal, ice | gate: rover, solar, thermal, ice (common gate) |
| `slope_300m_deg` | 0..90 | definition | both (gate + weighted): rover | both (gate + weighted): rover |
| `rough_300m_m` | >= 0 | definition | both (gate + weighted): rover | both (gate + weighted): rover |
| `irradiance_kwh_m2_day` | >= 0; Moon horizontal at the pole <= 0.88 (R3 D3); Moon equator about 10.4 mean (R3 D4) | R3 F1, D3, D4 | both (gate + weighted): solar | both (gate + weighted): solar; weighted: thermal |
| `sun_elev_max_deg` | 0..90; Moon pole max 1.54 (R3 F5); Earth pole 23.44 (R3 F3) | R2, R3 | both (gate + weighted): solar | both (gate + weighted): solar |
| `sun_low_frac_0_5deg` | 0..1 | definition | both (gate + weighted): solar | both (gate + weighted): solar |
| `lst_diurnal_amp_k` | >= 0; Moon equator about 295 K (R3 D6), 250-300 K at low latitudes (R2 sec. 3) | R2, R3 | both (gate + weighted): thermal | both (gate + weighted): thermal; weighted: solar |
| `thermal_inertia_class` | suelo, arena, regolito, roca, hielo, agua | code categories | both (gate + weighted): thermal | both (gate + weighted): thermal; gate: solar |
| `permafrost_class` | ninguno, esporadico, discontinuo, continuo | code categories; official definition: ground <= 0 C for >= 2 years (R3 F17, F18) | both (gate + weighted): ice | both (gate + weighted): ice; weighted: thermal |
| `rain_mm_day` | >= 0 | definition | workable_rover flag only, exported, never a gate or score (analog_finder.py:494-502) | not used |
| `wind_max_ms` | >= 0 | definition | workable_rover flag only, exported, never a gate or score (analog_finder.py:494-502) | not used |
| `tmin_c` | >= -273.15 | absolute zero | workable_rover flag only, exported, never a gate or score (analog_finder.py:494-502) | both (gate + weighted): thermal |

## 5. Metadata and derived outputs (summary; full rows in the CSV)

| Column | What it is | Problem |
|---|---|---|
| `lat_deg`, `lon_deg` | cell centres, odd integers -89..89 and -179..179 (`harmonizer_cleaner.py:202-203`) | none: 0 out of range, 0 swapped, 0 duplicate cells per body (A2 section 3) |
| `x_m`, `y_m` | `(col-89.5)*500`, `(44.5-row)*500` (`harmonizer_cleaner.py:198-199`) | describe a 90 km x 45 km sheet, not the globe |
| `resolution_m` | constant 500 (`harmonizer_cleaner.py:225`) | a real cell is 222.4 km (Earth) and 60.6 km (Moon) north-south |
| `source` | EARTH `global_model`, MOON `real_PDS` (`main.py:140-141`) | set from the command-line flags, not from what was loaded |
| `similarity_pct` | `100*exp(-0.45*rms)` of per-body z-scores (`analog_finder.py:448-457`) | compares positions within each body's own distribution, not physical values |
| `earth_region` | nearest of 48 hard-coded anchors (`analog_finder.py:77-140`) | median 672 km from the anchor in the top 100; 4 in the wrong country (A4) |
| `matched_lunar_zone` | argmin over 6 zone mean profiles (`analog_finder.py:460-470`) | all 100 ranked cells match "Tycho & Southern Rocky Craters" |
| `workable_rover` | rain, wind and tmin limits from `rover_preset.py:108-109` (ILUSTRATIVO) | exported only, never used in a pass or a score |
| `pass_*`, `score_*` | old gates plus `0.65*analog_sim + 0.35*gate_q`, x0.35 on failure (`analog_finder.py:243-323`) | inputs are MODELLED or of undocumented origin |
