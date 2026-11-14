# A3 - The two filter systems, scoring, rover gates, ice, solar concept, thermal similarity

Scope: Phase 0 audit. No repository file was changed. Everything was run in a copy:
`cp -r .../stars/work .../stars/run-A3`. Python = `.../stars/venv/bin/python`. Helper scripts are in `.../stars/a3scripts/` (s1.py to s5.py), run with `-I`.
Abbreviations: `W` = `/tmp/claude-0/-home-user-NASA/7228bb30-9725-52d9-8d71-762c955fd0bd/scratchpad/stars/work`, `TL` = `/home/user/stars-beside-you/tierra luna`, `H` = `TL/harmonizer_cleaner.py`, `AF` = `TL/analog_finder.py`, `WEB` = `TL/web/index.html`.

## 0. Baseline (confirmed, run in run-A3)

| Check | Command | Result |
|---|---|---|
| new system selftest | `python mission_scoring.py selftest` | `selftest OK (5 comprobaciones)` |
| old system selftest | `python mission_filters.py selftest` | `selftest OK` |
| rover preset | `python rover_preset.py --selftest` | `11/11 checks passed` |
| pytest | `python -m pytest -q tests` | `15 passed` |
| zip vs work copy | `cmp` on both files | `mission_scoring.py` and `mission_scoring.json` in the zip are byte-identical to the copies in `W` |

Not available in this session: the zip of pull request #1 ("files 2.zip") and the team's local zip with rover_preset.py v3 and rover_integration.py. Everything below about the rover describes rover_preset.py **as committed** (`TL/rover_preset.py`, 607 lines). How v3 differs is not determined.

## 1. The two filter systems

### 1.1 Old system: `TL/mission_filters.json` + `TL/mission_filters.py`

- `"version": "v1.0-spaceapps-2026"` (line 2), `"mask_min": 0.3` (line 3).
- Every mission has `"frozen_at": "2026-11-14T16:30:00+00:00"` (lines 50, 85, 118, 143).

| Mission | Gates (exact) | require_present | Domain weights relieve/material/termico/luz/agua | Other |
|---|---|---|---|---|
| rover (l.5-52), author "Robotics 1 - Mobility Team" | `slope_300m_deg` min 0.5, max 15.0, `max_from: max_operational_slope_deg`, source "rover.max_operational_slope_deg: NASA VIPER operational slope limit (15 deg < 47.29 deg static tip-over, rover_preset.py)"; `rough_300m_m` min 5.0, max 650.0, source "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)" | slope_300m_deg, rough_300m_m | 0.35 / 0.3 / 0.1 / 0.1 / 0.15 | tolerances slope 5.0 deg, rough 10.0 m; workable_days rain_mm_max 1, wind_max_ms_max 12, tmin_c_min -10 |
| solar (l.53-87), "Robotics 2 - Power & Illumination Team" | `irradiance_kwh_m2_day` 1.8-8.5 ("NASA POWER / NOAA NCEP surface shortwave photovoltaic threshold (>=1.8 kWh/m2/day)"); `sun_elev_max_deg` 5.0-85.0 ("Lunar polar & mid-latitude solar array elevation envelope (5-85 deg)"); `sun_low_frac_0_5deg` 0.025-0.4 ("Artemis low-horizon grazing illumination regime (0-5 deg solar altitude fraction)") | all three | 0.15 / 0.1 / 0.2 / 0.45 / 0.1 | - |
| thermal (l.88-120), "Robotics 2 - Thermal Systems Team" | `lst_diurnal_amp_k` 16.0-60.0 ("MODIS/NCEP bare-regolith diurnal & seasonal surface thermal swing (>=16 K)"); `thermal_inertia_class` allow [roca, regolito, arena, hielo] ("LRO Diviner Bandfield et al. (2011) unvegetated substrate thermal inertia classes") | thermal_inertia_class, lst_diurnal_amp_k | 0.15 / 0.25 / 0.45 / 0.1 / 0.05 | - |
| ice (l.121-145), "ISRU & Cryosphere Prospecting Team" | `permafrost_class` exclude [ninguno, none] ("plan fase 1, parte 3 (IPA Brown et al. permafrost & cryosphere map)") | permafrost_class | 0.15 / 0.15 / 0.25 / 0.1 / 0.35 | - |

Engine (`mission_filters.py`):
- `failed_gates()` (l.148-179) checks four things in order: mask_fraction < mask_min fails (only when the value is present); a `require_present` column without data fails; a categorical gate with no data is kept unless `on_missing="drop"`; a numeric gate with no data is kept unless `drop`.
- `validate()` (l.122-144) rejects an active gate with an empty `source` and requires weights that sum to 1 and have a `weights_note`.
- The old system has no scoring. Scores come from `AF` (section 3).

### 1.2 New system: `W/mission_scoring.json` (v "v1-draft") + `W/mission_scoring.py`

These two files exist only in the zip. Nothing in the pipeline imports them: `grep mission_scoring` over `main.py`, `analog_finder.py` and `tests/` finds no import (only the module's own docstring). **The new system is not wired. The live code path is the old one.**

Top level (json l.3-8):
- The `note` says it "sustituye a mission_filters.json". It also says: "Umbrales de solar y thermal = valores de diseno NO validados con fuente externa".
- `"on_missing_gate": "keep"`.
- `common_gates`:
  - `elevation_m` min 1.0, why "solo tierra firme (descarta oceano, que el modelo fija en -250 m)".
  - `mask_fraction` min 0.3, why "celda con dato suficiente".

| Mission | require_present | Gates (exact, with source) | Soft: column - weight, bad -> good (why) | Domain weights | frozen_at |
|---|---|---|---|---|---|
| rover (l.11-31), with `provisional`: "Gates y tolerancias migrados tal cual ... 'soft' es una aproximacion lineal de la formula antigua: sustituir por la definitiva del equipo de Robotica 1." | slope_300m_deg, rough_300m_m | Same as old: slope_300m_deg 0.5-15.0 (+max_from), rough_300m_m 5.0-650.0, same sources | slope_300m_deg 0.45, 15.0->1.0 ("menos pendiente = mas traficable"); rough_300m_m 0.30, 650.0->30.0 ("menos rugosidad = menos obstaculos"); rock_or_bare_frac 0.25, 0.0->0.7 ("suelo expuesto firme frente a vegetacion") | 0.35/0.3/0.1/0.1/0.15 | 2026-11-14T16:30:00+00:00 |
| solar (l.32-53) "Colocacion de placas solares" | irradiance_kwh_m2_day, sun_elev_max_deg, sun_low_frac_0_5deg, slope_deg | irradiance >= 2.5 ("diseno: por debajo, la generacion no compensa"); slope_deg <= 15.0 ("diseno: el campo de placas necesita terreno practicamente plano"); sun_elev_max_deg >= 10.0 ("diseno: sol siempre rasante = sombras permanentes"); sun_low_frac_0_5deg <= 0.25 ("diseno: demasiado tiempo con sol a <5 grados"); thermal_inertia_class exclude [agua] ("diseno: no se instala sobre agua") | irradiance 0.35, 2.5->6.0 ("energia disponible"); sun_elev_max 0.15, 10.0->70.0 ("mejor captacion con sol alto"); sun_low_frac 0.15, 0.25->0.03 ("menos tiempo de sol rasante"); slope_deg 0.15, 12.0->1.0 ("menos movimiento de tierras"); lst_diurnal_amp_k 0.10, 35.0->10.0 ("menos ciclado termico en los paneles"); roughness_m 0.10, 400.0->30.0 ("terreno llano = montaje mas facil") | 0.15/0.1/0.2/0.45/0.1 | null |
| thermal (l.54-73) "Resistencia termica (ensayo de hardware bajo estres tipo lunar)" | lst_diurnal_amp_k, tmin_c, thermal_inertia_class | lst_diurnal_amp_k >= 15.0 ("diseno: sin ciclo termico fuerte no hay ensayo util"); tmin_c <= 5.0 ("diseno: hace falta frio real para estresar el equipo"); thermal_inertia_class exclude [agua] ("diseno: el agua amortigua los ciclos") | lst_diurnal_amp_k 0.35, 15.0->35.0 ("amplitud termica diaria (estres por ciclado)"); tmin_c 0.25, 5.0->-50.0 ("minimas extremas"); thermal_inertia_class 0.15 map {roca 1.0, regolito 1.0, arena 0.9, suelo 0.6, hielo 0.4} default 0.5 ("superficie de baja inercia, parecida al regolito"); rock_or_bare_frac 0.10, 0.10->0.70 ("superficie expuesta, sin vegetacion que amortigue"); irradiance 0.10, 3.0->6.0 ("mayor carga solar = mayor calentamiento diurno"); permafrost_class 0.05 map {esporadico 1.0, discontinuo 1.0, continuo 0.7, ninguno 0.3} default 0.5 ("ciclos congelacion-deshielo") | 0.15/0.25/0.45/0.1/0.05 | null |
| ice (l.74-88), with `provisional`: "Gate migrado tal cual; 'soft' = formula antigua (frio + permafrost) expresada en el nuevo esquema." | permafrost_class | Same as old (exclude ninguno, none) | temp_k 0.55, 280.0->220.0 ("mas frio = hielo mas estable"); permafrost_class 0.45 map {continuo 1.0, discontinuo 0.85, esporadico 0.7} default 0.55 ("continuidad del permafrost") | 0.15/0.15/0.25/0.1/0.35 | 2026-11-14T16:30:00+00:00 |

The soft weights sum to 1.0 for every mission (checked by hand from the table). Unlike the old `validate()`, the new module has no validation of sources or weights.

Engine (`mission_scoring.py`):
- **Gates.** `_gate_mask` (l.46-72) and `apply_gates` (l.75-97).
  - A numeric gate passes when `v >= min` and `v <= max`. A categorical gate checks `allow`, then `exclude`.
  - Missing value: the cell passes only if `on_missing == "keep"` (l.70). `score_mission` passes `cfg.get("on_missing_gate","drop")`, and the JSON sets "keep".
  - Every column in `require_present` fails when its value is NaN, "", "nan" or "none" (l.81-89).
  - The mission gates override the common gates (l.144).
- **Soft.** `utility` (l.101-114) and `apply_soft` (l.117-135).
  - Numeric utility: `clip((v-bad)/(good-bad), 0, 1)`. NaN propagates.
  - Categorical utility: the map value; `default` for an unknown class; NaN when the value is missing.
  - Score: `100 * sum(w*u) / sum(w over finite u)`. A missing variable is dropped and the remaining weights are renormalised.
  - `coverage = den / total_w`.
- **Scoring.** `score_mission` (l.139-157) sets `score_<m> = NaN` when a gate fails: the cell is **removed**, not down-weighted.
- **`evaluate(df, missions, cfg=None, weights=None)`** (l.160-168).
  - It returns df plus, for each mission, `pass_, fail_, failcols_, score_, coverage_, u_<m>_<col>`, plus `pass_all` (AND of the missions).
  - `weights` is `{mission: {soft_column: weight}}`. It overrides **soft** weights only (l.120-121).
  - The domain `weights` in the JSON are not used by this module. Only `to_web_cfg` (l.190-204) passes them through, and nothing calls `to_web_cfg`.
- **`combine_with_similarity(res, mission, alpha=0.5, sim_col="similarity_pct")`** (l.207-211).
  - It returns `alpha*res[sim_col] + (1-alpha)*res[f"score_{mission}"]`.
  - Gate-failed cells stay NaN.
  - `evaluate()` output has no `similarity_pct` column (the harmonised CSV does not carry one). Calling it on that output raises `KeyError 'similarity_pct'` (`s5.py`). It only works after a caller merges similarity from `AF`.
- **CLI** `run` (l.251-276): it keeps only rows with `body == EARTH` (l.266-267).

Docstrings and notes that disagree with the code:
- `mission_scoring.py` l.11-12 says rover is `'external': true`. The JSON has no `external` key and defines rover gates and soft.
- The author's note (`TL/Instruciones filtros solar y temp`) says rover "pendiente por definir / Hueco para tu compañero". The JSON already holds a provisional rover.
- The note says "En un filtro duro la celda se descarta" for missing data. The JSON uses `"keep"`. In practice every gate column of solar, thermal, rover and ice is also in `require_present`, so missing data still fails. The two common gates (elevation_m, mask_fraction) are not in `require_present`, so a missing value there is kept.

### 1.3 Differences for the same mission

| Mission | Item | Old (mission_filters.json + AF scoring) | New (mission_scoring.json) |
|---|---|---|---|
| all | land / mask | mask_min 0.3 at top level. AF pre-filters `elevation_m > 0` (AF l.430) | common gates elevation_m >= 1.0 and mask_fraction >= 0.3. On these data the two land rules are equivalent: no Earth cell has 0 < elev < 1, and every ocean cell is exactly -250.0 m with mask 0.0 (`s3.py`) |
| all | gate-failed cell | score x 0.35, cell kept (AF l.316, l.322) | score NaN, cell removed (l.153) |
| all | score composition | 0.65 x analog similarity to a lunar zone + 0.35 x hand-coded gate quality (AF l.315) | soft utilities only. Similarity is optional through `combine_with_similarity` |
| all | domain weights | drive the analog part through `map_domain_weights_to_features` | not used by the module |
| all | missing data | gates "keep", require_present fails | same ("keep" + require_present) |
| rover | gates | slope_300m_deg 0.5-15.0, rough_300m_m 5.0-650.0 | identical |
| rover | quality | Gaussian around the lunar **Tycho** zone mean (slope 9.3746 deg, rough 719.3235 m): `exp(-0.5((s-9.37)/5)^2)`, `exp(-0.5((r-719.3)/120)^2)`, weights 0.45/0.30 + 0.25 rock (AF l.274-285). The rough target 719.3 m lies above the 650 m gate | linear, flatter and smoother is better (slope 15->1, rough 650->30) + rock 0->0.7. This is **not** an approximation of the old formula: it reverses its direction (old: close to the lunar slope of about 9.4 deg; new: as flat as possible) |
| solar | gates | irr 1.8-8.5, sun_elev 5-85, sun_low 0.025-0.4 | irr >= 2.5, sun_elev >= 10, sun_low <= 0.25, slope_deg <= 15, tic != agua. slope_deg added to require_present |
| solar | quality | irr_q (irr-1.8)/6.7 (0.45); **low_q (slow-0.025)/0.18 (0.35): more grazing sun scores higher**; elev_q peaks at 35 deg (0.20) (AF l.286-293) | sun_low 0.25->0.03: **more grazing sun scores lower**. sun_elev 10->70: higher sun is better. Plus slope, amplitude and roughness |
| solar | lunar target | "South Pole PSR & Shackleton Rim (75°S-90°S)" profile (AF l.258-263) | none |
| thermal | gates | amp 16-60, tic allow [roca, regolito, arena, hielo] (so `suelo` fails) | amp >= 15, tmin_c <= 5, tic exclude [agua] (so `suelo` passes) |
| thermal | quality | amp_q (amp-16)/28 (0.5), tic_q roca/hielo 1.0, regolito 0.85, else 0.7 (0.25), rock (0.25) (AF l.294-300) | soft table in 1.2 (hielo 0.4 there, against 1.0 in the old formula) |
| ice | gates | permafrost exclude [ninguno, none] | identical |
| ice | quality | cold_q (280-T)/60 (0.55) + pfc continuo 1/discontinuo 0.85/esporadico 0.70/else 0.55 (0.45) | identical formula (temp 280->220 equals (280-T)/60; default 0.55). The old version adds 0.65 x similarity to the PSR zone |
| frozen | solar, thermal | frozen 2026-11-14T16:30 | null (unfrozen) |

## 2. Reproduction on the 16,200 Earth cells

Command (in run-A3):

```
python mission_scoring.py run --cells output_py/earth_moon_harmonized_clean.csv --missions solar,thermal --out run-A3/ms_st.csv
```

Output: `solar: 5192/16200 ... score medio 60.2`, `thermal: 2613/16200 ... score medio 57.6`, `pasan todas: 1986`.
**This matches the author's declaration exactly** (5,192 / 2,613 / 1,986). Nothing differs.

With all four missions (`--missions solar,thermal,rover,ice`): rover 5297, ice 3023, all four 1728.

Gate removals on Earth land cells only (5,927 cells with elevation > 0; `s5.py`). A cell can fail several gates:

| Mission | pass | fail_by |
|---|---|---|
| rover | 5297 | slope_300m_deg 591, rough_300m_m 290 |
| solar | 5192 | sun_low_frac 540, irradiance 449, slope_deg 203 |
| thermal | 2613 | lst_diurnal_amp_k 2381, tmin_c 2271 |
| ice | 3023 | permafrost_class 2904 |

Over all 16,200 cells, the 10,273 ocean cells also fail elevation_m and mask_fraction (and tic = agua for solar and thermal).

Top cells (`s1.py`; countries from reverse_geocoder):
- **Solar** top 10: Senegal (Matam, Louga), Chad (Lac, Kanem), Somalia, Burkina Faso, Central African Republic, Benin, DR Congo. Scores 95.08-95.62.
  - Top 100 by country: AU 18, ML 8, TD 7, CD 7, MR 7, ...; lat -27 to 23.
  - This is the "Sahel and Sahara" the author reports.
- **Thermal** top 4: Tibet/Xinjiang (33-35°N, 81-89°E), scores 80.2-84.1. Then lat -79 to -81°, lon 73-79°E (East Antarctica), about 79.4.
  - The geocoder labels these "TF Kerguelen" because it returns the nearest populated place. By latitude they are Antarctica.
  - Top 100: lat -83 to 35; geocoder labels TF 83, ZA 13, CN 4. TF and ZA are nearest-place labels, not checked one by one.

Web integration hazard (from reading the code; the JavaScript was not run):
- `GATE_PROP_MAP` (WEB l.634-643) has no entry for slope_deg, tmin_c or elevation_m.
- `evaluateCellMissionFails` (WEB l.769+) reads `cell[undefined]` for an unmapped `require_present` column and marks it missing.
- If the new config were exported to the web as it is, every cell would therefore fail solar (slope_deg) and thermal (tmin_c).

Old system on the same Earth cells (`mission_filters.apply_missions`, on_missing keep, `s3.py`): rover 5297, solar 5198, thermal 3337, ice 3023, all four 2114. These equal the committed `mission_stats` in `analog_web_data.json`.

Why the counts differ:
- Solar is 5198 old against 5192 new because the gates differ. Old sun_elev max 85 removes 729 tropical land cells; new irradiance >= 2.5, sun_low <= 0.25 and slope_deg <= 15 remove polar and steep cells instead.
- Thermal is 3337 against 2613 because the new gate tmin_c <= 5 is added and suelo is allowed.

**Lunar cells.** `mission_scoring.evaluate` run on the 16,200 MOON rows (`s1.py`). This is hypothetical: the CLI only scores EARTH rows.

| Mission | Lunar cells passing | Gate that removes most (all failures / sole cause) |
|---|---|---|
| rover | 1910 | elevation_m 11041 (sole cause 7152); rough_300m_m 7006 (sole 3014); slope 649 (sole 21) |
| solar | 4712 | elevation_m 11041 (sole 8619); irradiance 2466; sun_elev 1440; sun_low 1080; slope_deg 649 |
| thermal | 5159 | elevation_m 11041 (the only gate that fails) |
| ice | 801 | permafrost_class 11520 (sole 4358); elevation_m 11041 |
| all four | 203 | - |

On the Moon the common "land" gate `elevation_m >= 1` removes 11,041 of 16,200 cells, because lunar elevation_m is height relative to a datum. Its `why` ("descarta oceano") has no meaning on the Moon. Without that gate, every lunar cell would pass thermal.

Old system on the Moon (`s3.py`):

| Mission | Lunar cells passing | Main failures |
|---|---|---|
| rover | 9062 | rough > 650: 7006 |
| solar | 14400 | sun_elev fails 1800 = |lat| <= 5 (above 85 deg) and |lat| >= 87 (below 5 deg); irr < 1.8 fails 720 |
| thermal | **0** | every lunar cell has amplitude 63.08-179.99 K > 60, and every lunar cell is class `suelo` (not allowed) |
| ice | 4680 | - |

## 3. analog_finder.py

### (a) `map_domain_weights_to_features` (AF l.225-240; the same mapping is duplicated in WEB l.669-691)

```
slope_deg         = relieve*0.45 + luz*0.15
roughness_m       = relieve*0.35 + material*0.20
elevation_rel_m   = relieve*0.20 + luz*0.35 + agua*0.20
temp_k            = termico*0.80 + luz*0.35 + agua*0.45
rock_or_bare_frac = material*0.55 + termico*0.20 + luz*0.15
sar_sigma0_db     = material*0.25 + agua*0.35
then divided by the sum
```

Each domain's coefficients sum to 1.0 (`s3.py`), so the normalisation divides by 1.0 when the domain weights sum to 1.

Effective feature weights (`s3.py`):

| Mission | slope | rough | elev_rel | temp_k | rock_bare | sar |
|---|---|---|---|---|---|---|
| rover | 0.1725 | 0.1825 | 0.1350 | **0.1825** | 0.2000 | 0.1275 |
| solar | 0.1350 | 0.0725 | 0.2075 | 0.3625 | 0.1625 | 0.0600 |
| thermal | 0.0825 | 0.1025 | 0.0750 | 0.4175 | 0.2425 | 0.0800 |
| ice | 0.0825 | 0.0825 | 0.1350 | 0.3925 | 0.1475 | 0.1600 |

**Confirmed.** For the rover, temp_k gets 18.25% and slope 17.25%, although relieve = 0.35 and termico = 0.10.
- temp_k collects termico x 0.8 = 0.08, luz x 0.35 = 0.035 and agua x 0.45 = 0.0675.
- The relief domain is not lost in total: slope + rough + elev = 0.49. It is spread over three features, while three domains feed temp_k.
- Every mission's luz and agua weight flows mostly into temp_k and elevation_rel_m.
- No illumination variable (irradiance, sun_elev, sun_low) and no amplitude are among the features. "luz" therefore cannot express light.

### (b) Hard-filter failure

- AF l.314-317: `combined = 0.65*analog_sim + 0.35*gate_q`, then `score = where(pass, combined, combined*0.35)`.
- AF l.320-322: `score_all = where(pass_all, mean_of_mission_scores, mean*0.35)`.

**Confirmed.** A gate-failed cell keeps a score at 35% and stays in `earth_scored`. It is written with that score:
- to `analog_ranking.csv` (`score_*` columns; the ranking is sorted by similarity_pct, not by pass);
- to the web JSON (`s_rov`, `s_sol`, ... AF l.636-640).

Two consumers do remove failed cells:
- `build_optimal_mission_zones` keeps only `pass == 1` (AF l.339).
- The browser recomputes scores and sets them to 0 for failed missions (WEB l.1113-1118).

So the backend outputs and the browser disagree on failed cells (x 0.35 against 0).

### (c) Similarity, pairing and export

- **Normalisation** (AF l.143-181), **per body separately**: `z = clip((v - median)/(IQR/1.349), -4, 4)`. Missing values get z = 0.
  - Earth is normalised over land cells only (AF l.430-434).
  - A z-score therefore says where a cell stands within its own planet. It does not measure physical sameness.
- **Lunar targets** (AF l.184-222): 7 zones defined by lat, lon, elevation or slope masks. Each profile is the mean z of its cells.
  - The default target is "Global Lunar Surface Mean".
  - "South Pole PSR & Shackleton Rim" = every cell with lat <= -75 (1440 cells). It is a latitude band, not a PSR map.
- **Distance** (AF l.448-458): global weighted RMS over the 6 features, `rms = sqrt(sum w_f (z_e - z_target)^2)`, `similarity_pct = 100*exp(-0.45*rms)`.
  - Per-variable `sim_<f>_pct = 100*exp(-0.35*diff^2)` (l.451) is for display only.
- **Pairing**: an Earth cell is never paired with a lunar cell. It is compared with a zone **mean profile**. `matched_lunar_zone` = the argmin of the weighted distance over the 6 non-global zones (l.460-470).
  - In the committed ranking, all top 100 are matched to "Tycho & Southern Rocky Craters".
- **Mission analog part** (AF l.258-272): uses a mission-specific zone target (rover: Tycho; solar and ice: PSR; thermal: global).
- **`export_web_bundle`** (AF l.575-691) writes:
  - `analog_ranking.csv` (top_k = 100 by similarity);
  - `optimal_mission_zones.csv` (6 zones per mission + "all", minimum separation 14 deg);
  - `analog_web_data.json` and `web/analog_data.js`, with `grid`, `features`, `default_weights`, `lunar_zones`, `moon_stats`, `earth_stats`, `mission_filters` (the full old JSON), `mission_stats`, `optimal_mission_zones`, `rover_preset`, `earth_cells` (stride 2: 1477 cells) and `moon_cells` (4050 cells).
  - `pack_cells` fills missing values with fixed defaults: irr 4.0, smax 45.0, slow 0.05, damp 20.0, tic "roca", pfc "ninguno", tmin -5.0 (l.617-625). Missing data therefore becomes numbers in the web bundle.
- **Side effect:** `get_rover_preset_bundle` (AF l.35-56) calls `merge_into_presets(..., refreeze=True)` on every pipeline run. It rewrites `data/presets/presets.json` in place with a new `frozen_at` and `allow_unverified=True`.

## 4. Rover: preset (as committed) against mission_filters.json

`TL/rover_preset.py`:
- **ROVER_SPEC** (l.71-86):
  - mass_kg 440 is "OK".
  - Marked "VERIFICAR" or ESTIMADO: cg_height_m 0.60, cg_x/cg_y 0.0 ("assumed centred"), wheelbase_m 1.30, track_m 1.30, contact_patch_length_m 0.10, contact_patch_width_m 0.20, max_speed_mps 0.20, max_operational_slope_deg 15.
  - ground_clearance_m: `None`, status "MISSING".
- **PRESET_CONFIG** (l.92-112):
  - Weights: relief 0.35, surface_material 0.30, thermal_regime 0.10, light_and_sky 0.10, water_ice_aridity 0.15. Every one has a source starting "ILUSTRATIVO".
  - Tolerances: slope_300m_deg scale 5.0 deg, rough_300m_m 10.0 m, both "ILUSTRATIVO - set by Robotics 1".
  - Gates: `slope_300m_deg {"min": None, "max_from": "max_operational_slope_deg"}` (max 15). `rough_300m_m {"min": None, "max": None, "source": "no gate until Robotics 1 sets one"}`.
  - workable_days: 1 / 12 / -10, "ILUSTRATIVO".
- **Markers** (l.57-60): `UNVERIFIED_MARKERS = {VERIFICAR, VERIFY, ESTIMADO, ESTIMATED, ILUSTRATIVO, ILLUSTRATIVE}`.
- `python rover_preset.py` prints 14 unverified items. Min static tip-over = 47.29 deg.

The contradiction:

| Item | rover_preset.py PRESET_CONFIG | mission_filters.json rover (and mission_scoring.json) |
|---|---|---|
| slope_300m_deg | min None, max 15 (from the ESTIMADO field) | **min 0.5**, max 15.0 |
| rough_300m_m | **no gate** (min None, max None) | **min 5.0, max 650.0**, source "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)" |
| slope source text | "rover.max_operational_slope_deg: ESTIMADO - replace from project DB" (presets.json) | "...NASA VIPER operational slope limit (15 deg < 47.29 deg ...)". The JSON calls a field the preset marks ESTIMADO/VERIFICAR a NASA limit |
| tolerance sources | "ILUSTRATIVO" | "Robotics 1 rover_preset.py tolerance scale" (the illustrative label is dropped) |

**Live path today.**
- `AF` applies the gates from `mission_filters.json` (AF l.475, l.504-510). The rover gates are therefore slope 0.5-15 and rough 5-650.
- The preset's own `gates` are only exported inside `rover_preset` in the bundle.
- Tolerances: `m_obj["tolerances"]` from the JSON first, the preset as fallback (AF l.278).
- workable_days comes from the preset (AF l.494-502). It is not a gate in AF.
- In the browser, gates come from `data.mission_filters` (WEB l.646). The rover-panel input `rpMaxOpSlopeDeg` overwrites the rover slope max live (WEB l.914-920).

On Earth land, 591 cells fail slope (including 388 with slope < 0.5) and 290 fail roughness (48 with < 5 m, 242 with > 650 m) (`s3.py`).

R1 (`/home/user/NASA/docs/integration/R1_viper_rover_spec_sources.md`):
- l.42 and l.87: 15 deg is a VIPER requirement or design limit found in four NASA documents.
- l.87 and l.112: no official product uses a 300 m baseline, and a 15 deg limit at rover scale is not the same terrain as 15 deg on a 300 m slope.
- No research file found here gives a source for the 5-650 m roughness envelope (not determined).

Also, `slope_300m_deg` and `rough_300m_m` are plain copies of `slope_deg` and `roughness_m` at the grid resolution (H l.303-304). They are not computed at a 300 m baseline.

## 5. Ice mission in the old system (exact)

| Item | Value |
|---|---|
| description | "Cryospheric Drilling & Volatiles/Ice Prospecting (ISRU)" |
| gate | `permafrost_class: {"exclude": ["ninguno","none"], "source": "plan fase 1, parte 3 (IPA Brown et al. permafrost & cryosphere map)"}` |
| require_present | ["permafrost_class"] |
| weights | relieve 0.15, material 0.15, termico 0.25, luz 0.1, agua 0.35 |
| weights_note | "Targets cryospheric permafrost substrates and cold-trap thermal conditions for ISRU ice drilling." |
| frozen | 2026-11-14T16:30:00+00:00, "ISRU & Cryosphere Prospecting Team" |
| AF score | analog_sim against the **PSR zone** (lat <= -75) x 0.65 + 0.35 x (0.55 x clip((280-temp_k)/60) + 0.45 x pfc_q), with pfc_q continuo 1.0, discontinuo 0.85, esporadico 0.70, else 0.55 (AF l.301-310) |

`permafrost_class` is not read from a permafrost map. It is computed from temp_k and elevation (H l.276-284).
- Earth: continuo when T <= 265.15 K; discontinuo when T <= 270.15 K; esporadico when T <= 274.15 K, or when elevation >= 3400 m and T <= 278 K.
- Moon: continuo when |lat| >= 75 and T <= 75 K; discontinuo when |lat| >= 65 and 75 < T <= 90 K.

The "IPA Brown et al." source is therefore not what the code uses: the value is DERIVED from temp_k.
- Earth: 3023 of 5927 land cells pass.
- Moon: 4680 pass (old system).

## 6. Solar concept: what the code selects today

**Lunar side.**
- No lunar cell is ranked for the solar mission. The solar mission ranks **Earth** cells by similarity to the lunar zone profile "South Pole PSR & Shackleton Rim (75°S-90°S)" (AF l.250-263).
- That profile is the mean z of the 6 features over all 1440 cells with lat <= -75. It is defined by latitude and has no illumination input.
- Over those cells (`s5.py`): irradiance 1.647-2.739 (mean 2.112) kWh/m²/day, sun_elev_max 2.54-16.54 deg, sun_low_frac 0.2021-0.2817, temp_k mean 66.35 K. Its temp_k_z is -2.8476, the most extreme in the profile.
- The target therefore pulls the solar mission toward Earth's coldest cells. It does not target lit ridges, and the code does not represent them.

**Committed outputs (Earth side).**
- `optimal_mission_zones.csv`, solar zones 1-6 are all polar cold cells:
  - East Antarctic Polar Plateau (-73, 65);
  - McMurdo Dry Valleys label (-81, 153);
  - West Antarctic (-81, -153);
  - West Antarctic (-77, -89);
  - East Antarctic (-71, 113);
  - Verkhoyansk (67, 133).
  - Ranges over these six: irradiance 2.84-3.92, sun_elev_max 20.7-34.7 deg, sun_low 0.1638-0.2342, mission_score 55.29-57.11.
- `analog_ranking.csv`: the top 100 is sorted by similarity, not by solar. Its 5 best solar scores are all West Antarctic at -75° (irr 3.40-3.45, smax 26.7, slow 0.2021).
- `analog_web_data.json`: the same `optimal_mission_zones`. `mission_stats` solar pass = 5198.
- The low-sun term in AF scoring rewards a **higher** grazing fraction (AF l.291), which favours polar cells further.

**Is any illumination variable measured? No.** H l.249-257:
- `irradiance = clip((1.6 + 4.8*cos(lat)^0.75) * (0.78 + 0.32*bare + 0.04*clip(elev/3000)), 0.8, 8.2)`.
  - The same Earth-tuned formula is used for the Moon. It has no solar constant and no topographic shading.
- `sun_elev_max = clip(90 - |lat| + (1.54 if Moon else 11.7), 1.5, 90)`.
- `sun_low_frac = clip(0.028 + 0.26*(|lat|/90)^2.2, 0.025, 0.35)`.
- On the Moon, sun_elev_max, sun_low_frac and lst_diurnal_amp_k have a within-latitude standard deviation of exactly 0.0, so they depend on latitude only (`s3.py`). Irradiance varies by at most 0.14 within a latitude band (through rock_or_bare).
- Level: DERIVED from latitude (geometry) for sun_elev_max. MODELLED (an invented fitting formula) for irradiance and sun_low_frac.
- The +1.54 term corresponds to the Moon's spin-axis tilt to the ecliptic. The +11.7 for Earth is about half of Earth's obliquity (23.44 deg is the standard value; no project research note covers it, because R2-R4 do not exist yet and R1 only mentions PSR at l.48).
- **No variable represents polar ridge illumination**: no fraction of time lit, no horizon or topographic shading. The code cannot tell a lit rim from a PSR.

**What the gates do to lunar polar cells** (`s3.py`, `s4.py`):

| Gate | Effect on the Moon |
|---|---|
| old irr >= 1.8 | removes |lat| 87, 89 |
| old sun_elev 5-85 | removes |lat| 87, 89 **and** |lat| <= 5 |
| old sun_low 0.025-0.4 | removes nothing |
| new irr >= 2.5 | removes |lat| >= 79 entirely and 306 of 360 cells at |lat| = 77 |
| new sun_elev >= 10 | removes |lat| >= 83 |
| new sun_low <= 0.25 | removes |lat| >= 85 |

With the new gates, **no lunar cell poleward of about 77° can pass solar**, which is exactly where the near-permanently lit ridges are. Its `why` ("sol siempre rasante = sombras permanentes") treats grazing sun as bad, which is the opposite of the polar-ridge concept.

## 7. Thermal similarity

Data (`s3.py`, `s4.py`):
- Earth land lst_diurnal_amp_k: 8.89-38.75 K. Only 12 cells are >= 35 K.
- Moon: 63.08-179.99 K. On the Moon it is DERIVED from latitude only: `clip(180*cos(lat)^0.35, 25, 210)` (H l.259-260).
- On Earth it is `clip(8 + 22*bare + 0.0022*elev, 6, 48)` (H l.262-266). That is MODELLED, not MODIS.

What the code does:
- **lst_diurnal_amp_k is not a similarity feature.** ANALOG_FEATURES (AF l.59-66) are elevation_rel_m, slope_deg, roughness_m, temp_k, rock_or_bare_frac and sar_sigma0_db. Amplitude enters only the gates and the mission gate_q.
- The thermal feature is temp_k, z-scored **per body**. Earth land is 217.4-327.5 K and the Moon 43.5-110.4 K, yet per-variable `sim_temp_k_pct` reaches **100.0**.
  - 2356 of 5927 land cells are >= 90 against the global lunar mean, and 676 are >= 99.
  - Committed top 100: sim_temp_k 91.86-100.0. Overall similarity_pct 87.75-94.01.
  - The physical gap of about 130-280 K is invisible.
- Hypothetical, for scale only (not in the code):
  - Amplitude as a per-body z-feature with the same formula would also reach 100.0.
  - With one common normalisation over both bodies (scale 102.94 K), Earth's best amplitude cell reaches 67.65 against the lunar mean of 147.53 K, and 98.06 against the coldest lunar cell (63.08 K).
  - The same pooled treatment of temp_k gives 59.14 for Earth's coldest cell against the lunar mean.
- **The "good" value of 35 K** (new thermal soft):
  - Utility is 1 from 35 K up. Of the 2613 Earth cells that pass, 11 have u_amp = 1; the mean u_amp is 0.556; the best thermal score is 84.09.
  - Every lunar cell would have u_amp = 1 and u_tmin = 1.
  - The 35 K choice keeps the Earth scale informative. It encodes no lunar similarity: 35 K is 55% of the smallest lunar amplitude.
- Old AF amp_q = (amp-16)/28 saturates at 44 K, so Earth's maximum reaches only 0.8125.

## Data levels used here

| Variable | Level | Evidence |
|---|---|---|
| Earth base bands | not determined: loaded from `data/cache/earth_global_real.npz` when present (earth_extractor.py l.133-157), otherwise a seeded synthetic grid (l.159+). Labelled `source = global_model` for all 16200 rows (main.py l.141) | provenance of the npz not determined in A3 |
| Moon base bands | labelled real_PDS (main.py l.140) | not audited here |
| irradiance, sun_low_frac, lunar lst amp, Earth lst amp, mask_fraction (Earth), thermal_inertia_class, permafrost_class, rain, wind, tmin_c | MODELLED (formulas on latitude, bare fraction, elevation and temp) | H l.240-300 |
| sun_elev_max | DERIVED (geometry from latitude + tilt constant) | H l.256 |
| slope_300m_deg, rough_300m_m | copies of slope_deg and roughness_m, mislabelled baseline | H l.303-304 |
