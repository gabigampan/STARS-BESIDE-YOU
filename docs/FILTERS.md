# Mission filters and scoring (Phase 0)

Stars Beside You, NASA Space Apps Challenge 2026. Written 2026-11-14, from the files on branch `final-integration` at commit 618bc45. File references are relative to `tierra luna/` unless a path is given.

All values, names and source texts below are copied from the files and left in their original language. Nothing in the configuration was changed.

**Which state this document describes.** It describes commit 618bc45. While it was being written, uncommitted changes appeared in the working tree; they were not made by this audit:

- `tierra luna/analog_finder.py`: the x0.35 penalty is replaced by NaN for gate-failed cells, and the web bundle writes `null` scores.
- `tierra luna/mission_scoring.json`: `on_missing_gate` is changed from "keep" to "drop".
- A new untracked folder, `tierra luna/engine/`.

They are not audited here. Where this document says "keep" or "x0.35", it refers to the committed files.

All counts were re-run for this document in a scratch copy of the repository (`scratchpad/stars/run-docs`, a copy of `scratchpad/stars/work`) with `scratchpad/stars/venv/bin/python`. Scripts: `scratchpad/stars/docscripts/check2.py` and the commands quoted in each section. Detailed evidence is in [audit_evidence/A3_filters_scoring.md](audit_evidence/A3_filters_scoring.md).

Not available in this session, so **not compared** (pending):

- the zip of pull request #1 ("files 2.zip");
- the team's local zip said to contain `rover_preset.py` version 3 and `rover_integration.py`.

Everything about the rover below describes `rover_preset.py` **as committed**.

## (a) Old system: `mission_filters.json` + `mission_filters.py`

**Header:**

- `"version": "v1.0-spaceapps-2026"` (line 2).
- `"mask_min": 0.3` (line 3).
- Every mission has `"frozen_at": "2026-11-14T16:30:00+00:00"` (lines 50, 85, 118, 143).
- Weight order in every mission: relieve / material / termico / luz / agua.

| Mission (lines) | Description | Author | Hard filters (exact, with `source`) | require_present | Domain weights | weights_note |
|---|---|---|---|---|---|---|
| rover (5-52) | "Rover Mobility & Surface Trafficability (Robotics 1 - VIPER Reference)" | "Robotics 1 - Mobility Team" | `slope_300m_deg` min 0.5, max 15.0, `max_from` "max_operational_slope_deg", source "rover.max_operational_slope_deg: NASA VIPER operational slope limit (15 deg < 47.29 deg static tip-over, rover_preset.py)". `rough_300m_m` min 5.0, max 650.0, source "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)" | slope_300m_deg, rough_300m_m | 0.35 / 0.3 / 0.1 / 0.1 / 0.15 | "Robotics 1 rover_preset.py sector weights: relief (0.35), surface_material (0.30), thermal_regime (0.10), light_and_sky (0.10), water_ice_aridity (0.15)." |
| solar (53-87) | "Solar Energy & Low-Angle Illumination (Robotics 2)" | "Robotics 2 - Power & Illumination Team" | `irradiance_kwh_m2_day` min 1.8, max 8.5, source "NASA POWER / NOAA NCEP surface shortwave photovoltaic threshold (>=1.8 kWh/m2/day)". `sun_elev_max_deg` min 5.0, max 85.0, source "Lunar polar & mid-latitude solar array elevation envelope (5-85 deg)". `sun_low_frac_0_5deg` min 0.025, max 0.4, source "Artemis low-horizon grazing illumination regime (0-5 deg solar altitude fraction)" | irradiance_kwh_m2_day, sun_elev_max_deg, sun_low_frac_0_5deg | 0.15 / 0.1 / 0.2 / 0.45 / 0.1 | "Emphasizes solar irradiance, low-angle illumination geometry, and thermal regime for solar power generation." |
| thermal (88-120) | "Extreme Thermal Environment & Substrate Inertia (Robotics 2)" | "Robotics 2 - Thermal Systems Team" | `lst_diurnal_amp_k` min 16.0, max 60.0, source "MODIS/NCEP bare-regolith diurnal & seasonal surface thermal swing (>=16 K)". `thermal_inertia_class` allow ["roca", "regolito", "arena", "hielo"], source "LRO Diviner Bandfield et al. (2011) unvegetated substrate thermal inertia classes" | thermal_inertia_class, lst_diurnal_amp_k | 0.15 / 0.25 / 0.45 / 0.1 / 0.05 | "Focuses on surface thermal cycling amplitude and bare rock/regolith thermal inertia." |
| ice (121-145) | "Cryospheric Drilling & Volatiles/Ice Prospecting (ISRU)" | "ISRU & Cryosphere Prospecting Team" | `permafrost_class` exclude ["ninguno", "none"], source "plan fase 1, parte 3 (IPA Brown et al. permafrost & cryosphere map)" | permafrost_class | 0.15 / 0.15 / 0.25 / 0.1 / 0.35 | "Targets cryospheric permafrost substrates and cold-trap thermal conditions for ISRU ice drilling." |

The rover entry also carries:

- `tolerances`: `slope_300m_deg` scale 5.0 deg, source "Robotics 1 rover_preset.py tolerance scale (5.0 deg)"; `rough_300m_m` scale 10.0 m, source "Robotics 1 rover_preset.py tolerance scale (10.0 m)".
- `workable_days`: rain_mm_max 1, wind_max_ms_max 12, tmin_c_min -10, source "Phase-1 plan model 1 defaults (rover_preset.py)".

**Engine (`mission_filters.py`).** `failed_gates()` (lines 148-179) checks, in order:

1. `mask_fraction < mask_min` fails, but only when the value is present.
2. A `require_present` column with no value fails.
3. A gate with no value fails only when `on_missing == "drop"`.
4. Otherwise numeric `min`/`max` and categorical `allow`/`exclude` are applied.

`analog_finder.py:505-510` calls it with `on_missing="keep"`. `max_from` is ignored by this engine; only `rover_preset.py:322-327` reads it. `validate()` (lines 122-144) checks only form: an active gate has a non-empty `source` and min <= max; the weights are complete, sum to 1 and carry a `weights_note` (with `strict`, missing weights are also reported). It does not check what the source says.

**The old system has no scoring of its own.** Scores come from `analog_finder.py` (section (e)).

## (b) New system: `mission_scoring.json` + `mission_scoring.py`

**Header (lines 2-8):**

- `"version": "v1-draft"`.
- `note` (exact): "Motor unico de filtros por mision (sustituye a mission_filters.json). 'gates' = filtros duros (si falla uno, la zona se descarta). 'soft' = criterios ponderados 0-100: 'good' da utilidad 1 y 'bad' utilidad 0 (interpolacion lineal; si good < bad, menos es mejor). 'weights' (relieve/material/termico/luz/agua) solo los usa la web para el boton 'Use Weights' de la similitud. Umbrales de solar y thermal = valores de diseno NO validados con fuente externa."
- `"on_missing_gate": "keep"`.
- Common gates:
  - `elevation_m` min 1.0, why "solo tierra firme (descarta oceano, que el modelo fija en -250 m)";
  - `mask_fraction` min 0.3, why "celda con dato suficiente".

### Gates

| Mission | require_present | Gate | Value | `source` (exact) |
|---|---|---|---|---|
| rover | slope_300m_deg, rough_300m_m | slope_300m_deg | min 0.5, max 15.0, max_from "max_operational_slope_deg" | "rover.max_operational_slope_deg: NASA VIPER operational slope limit (15 deg < 47.29 deg static tip-over, rover_preset.py)" |
| rover | | rough_300m_m | min 5.0, max 650.0 | "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)" |
| solar | irradiance_kwh_m2_day, sun_elev_max_deg, sun_low_frac_0_5deg, slope_deg | irradiance_kwh_m2_day | min 2.5 | "diseno: por debajo, la generacion no compensa" |
| solar | | slope_deg | max 15.0 | "diseno: el campo de placas necesita terreno practicamente plano" |
| solar | | sun_elev_max_deg | min 10.0 | "diseno: sol siempre rasante = sombras permanentes" |
| solar | | sun_low_frac_0_5deg | max 0.25 | "diseno: demasiado tiempo con sol a <5 grados" |
| solar | | thermal_inertia_class | exclude ["agua"] | "diseno: no se instala sobre agua" |
| thermal | lst_diurnal_amp_k, tmin_c, thermal_inertia_class | lst_diurnal_amp_k | min 15.0 | "diseno: sin ciclo termico fuerte no hay ensayo util" |
| thermal | | tmin_c | max 5.0 | "diseno: hace falta frio real para estresar el equipo" |
| thermal | | thermal_inertia_class | exclude ["agua"] | "diseno: el agua amortigua los ciclos" |
| ice | permafrost_class | permafrost_class | exclude ["ninguno", "none"] | "plan fase 1, parte 3 (IPA Brown et al. permafrost & cryosphere map)" |

### Weighted (soft) criteria

Utility = `clip((v - bad)/(good - bad), 0, 1)` for numbers. Categories use the `map` value, or `default` for an unknown class.

| Mission | Column | Weight | bad | good | why (exact) |
|---|---|---|---|---|---|
| rover | slope_300m_deg | 0.45 | 15.0 | 1.0 | "menos pendiente = mas traficable" |
| rover | rough_300m_m | 0.30 | 650.0 | 30.0 | "menos rugosidad = menos obstaculos" |
| rover | rock_or_bare_frac | 0.25 | 0.0 | 0.7 | "suelo expuesto firme frente a vegetacion" |
| solar | irradiance_kwh_m2_day | 0.35 | 2.5 | 6.0 | "energia disponible" |
| solar | sun_elev_max_deg | 0.15 | 10.0 | 70.0 | "mejor captacion con sol alto" |
| solar | sun_low_frac_0_5deg | 0.15 | 0.25 | 0.03 | "menos tiempo de sol rasante" |
| solar | slope_deg | 0.15 | 12.0 | 1.0 | "menos movimiento de tierras" |
| solar | lst_diurnal_amp_k | 0.10 | 35.0 | 10.0 | "menos ciclado termico en los paneles" |
| solar | roughness_m | 0.10 | 400.0 | 30.0 | "terreno llano = montaje mas facil" |
| thermal | lst_diurnal_amp_k | 0.35 | 15.0 | 35.0 | "amplitud termica diaria (estres por ciclado)" |
| thermal | tmin_c | 0.25 | 5.0 | -50.0 | "minimas extremas" |
| thermal | thermal_inertia_class | 0.15 | map | map | "superficie de baja inercia, parecida al regolito" |
| thermal | rock_or_bare_frac | 0.10 | 0.10 | 0.70 | "superficie expuesta, sin vegetacion que amortigue" |
| thermal | irradiance_kwh_m2_day | 0.10 | 3.0 | 6.0 | "mayor carga solar = mayor calentamiento diurno" |
| thermal | permafrost_class | 0.05 | map | map | "ciclos congelacion-deshielo" |
| ice | temp_k | 0.55 | 280.0 | 220.0 | "mas frio = hielo mas estable" |
| ice | permafrost_class | 0.45 | map | map | "continuidad del permafrost" |

The soft weights sum to 1.00 in every mission.

**Category tables:**

| Mission, column | map | default |
|---|---|---|
| thermal, thermal_inertia_class | roca 1.0, regolito 1.0, arena 0.9, suelo 0.6, hielo 0.4 | 0.5 |
| thermal, permafrost_class | esporadico 1.0, discontinuo 1.0, continuo 0.7, ninguno 0.3 | 0.5 |
| ice, permafrost_class | continuo 1.0, discontinuo 0.85, esporadico 0.7 | 0.55 |

### Other fields per mission

| Mission | description | provisional | Domain weights (relieve/material/termico/luz/agua) | frozen_at | author |
|---|---|---|---|---|---|
| rover | "Rover Mobility & Surface Trafficability (Robotics 1 - VIPER Reference)" | "Gates y tolerancias migrados tal cual del mission_filters.json anterior. 'soft' es una aproximacion lineal de la formula antigua: sustituir por la definitiva del equipo de Robotica 1." | 0.35/0.3/0.1/0.1/0.15 | 2026-11-14T16:30:00+00:00 | Robotics 1 - Mobility Team |
| solar | "Colocacion de placas solares" | - | 0.15/0.1/0.2/0.45/0.1 | null | Robotics 2 - Power & Illumination Team |
| thermal | "Resistencia termica (ensayo de hardware bajo estres tipo lunar)" | - | 0.15/0.25/0.45/0.1/0.05 | null | Robotics 2 - Thermal Systems Team |
| ice | "Perforacion y prospeccion de hielo (solo si sobra tiempo)" | "Gate migrado tal cual; 'soft' = formula antigua (frio + permafrost) expresada en el nuevo esquema." | 0.15/0.15/0.25/0.1/0.35 | 2026-11-14T16:30:00+00:00 | ISRU & Cryosphere Prospecting Team |

The rover entry also keeps `tolerances` and `workable_days`, identical to the old file (`mission_scoring.json:23-27`). `mission_scoring.py` never reads either of them (no occurrence of "tolerances" or "workable" in the module).

**The rover block is not empty.** The team lead's brief said it was. The repository wins: `mission_scoring.json:10-31` holds a provisional rover block with gates (`slope_300m_deg` 0.5 to 15, `rough_300m_m` 5 to 650) and soft weights 0.45, 0.30, 0.25. It also holds a provisional ice block (lines 74-88). Two other texts disagree with the JSON:

- the module docstring calls rover `'external': true` (`mission_scoring.py:11-12`), but the JSON has no `external` key;
- the author's note says rover is "pendiente por definir / Hueco para tu compañero" (`Instruciones filtros solar y temp:17`).

### Behaviour on missing data

| Where | Behaviour |
|---|---|
| Code default | `cfg.get("on_missing_gate", "drop")` (`mission_scoring.py:147`): a gate with a missing value **drops** the cell |
| Shipped configuration | `"on_missing_gate": "keep"` (`mission_scoring.json:4`): a gate with a missing value **keeps** the cell (`mission_scoring.py:70`) |
| Author's note | "En un filtro duro la celda se descarta" (`Instruciones filtros solar y temp:9`). Module docstring lines 18-19 describe both options. |
| require_present | Always fails a missing value (NaN, "", "nan", "none"), whatever `on_missing_gate` says (`mission_scoring.py:81-89`) |
| Effect today | None on the committed data: every column has 0 missing values. Most mission gate columns are also in `require_present`, so a missing value fails there regardless. Three gate columns are not: the two common gates (`elevation_m`, `mask_fraction`, in no `require_present`) and the solar gate `thermal_inertia_class` (solar `require_present` lists only irradiance, sun elevation, grazing fraction and `slope_deg`, `mission_scoring.json:34`). With "keep", a missing elevation, mask or (for solar) thermal-inertia class would **keep** the cell. |
| Soft criteria | A missing value is ignored and the remaining weights are renormalised. `coverage_<m>` = weight with data / total weight (`mission_scoring.py:117-135`). |

### Functions

| Function | Signature and defaults | What it does |
|---|---|---|
| `evaluate` | `evaluate(df, missions, cfg=None, weights=None)` (line 160) | Loads `mission_scoring.json` next to the module when `cfg` is None. For each mission it appends `pass_<m>`, `fail_<m>`, `failcols_<m>`, `score_<m>`, `coverage_<m>`, `u_<m>_<col>`, then `pass_all` (AND of the missions). `weights = {mission: {soft_column: weight}}` overrides **soft** weights only (lines 120-121). The domain `weights` in the JSON are never read here. |
| `score_mission` | (line 139) | Common gates are merged with the mission gates, and mission gates win on the same column (line 144). `score_<m> = round(score, 2)` where the cell passes, **NaN where it fails** (line 153): a failed cell is removed, not down-weighted. |
| `apply_soft` | (line 117) | `score = 100 * sum(w*u) / sum(w over finite u)` |
| `combine_with_similarity` | `combine_with_similarity(res, mission, alpha=0.5, sim_col="similarity_pct")` (lines 207-211) | Returns `alpha*res[sim_col] + (1-alpha)*res[f"score_{mission}"]`. Failed cells stay NaN. The output of `evaluate()` has no `similarity_pct`, so calling it directly raises `KeyError` (A3 `s5.py`). It only works after `similarity_pct` from `analog_finder.py` has been merged in. |
| `to_web_cfg` | (lines 190-204) | Converts to the web format, with `mask_min` from the common gate. **Nothing calls it.** |
| CLI `run` | lines 251-276 | Reads `--cells`, **keeps only rows with `body == EARTH`** (lines 266-267), evaluates, prints the counts |
| `selftest` | lines 215-248 | Uses its own inline configuration with `on_missing_gate: "drop"` (line 217), not the shipped JSON. It prints "5 comprobaciones" but runs 7 `assert` statements (lines 235, 236, 237, 238, 240, 243, 247). |

## (c) Differences between the two systems, mission by mission

**Pass counts on the same data.** These are the 16,200 EARTH rows of the committed `output_py/earth_moon_harmonized_clean.csv`. Old counts come from `mission_filters.apply_missions(..., on_missing="keep")`, as `analog_finder.py:505-510` calls it; new counts come from `mission_scoring.evaluate`. Script: `docscripts/check2.py`.

| Mission | Old pass | New pass | Same verdict | Pass old only | Pass new only |
|---|---|---|---|---|---|
| rover | 5,297 | 5,297 | 16,200 | 0 | 0 |
| solar | 5,198 | 5,192 | 14,820 | 693 | 687 |
| thermal | 3,337 | 2,613 | 15,224 | 850 | 126 |
| ice | 3,023 | 3,023 | 16,200 | 0 | 0 |
| solar and thermal | 3,162 | 1,986 | | | |
| all four | 2,114 | 1,728 | | | |

The old counts equal `mission_stats` in the committed `output_py/analog_web_data.json` (A3 section 2). **The web page shows the old counts.**

| Mission | Item | Old | New |
|---|---|---|---|
| all | land rule | `mask_min` 0.3; `analog_finder.py:430` keeps `elevation_m > 0` before ranking | common gates `elevation_m >= 1.0` and `mask_fraction >= 0.3`. On this Earth grid the two rules select the same cells: no cell has 0 < elevation < 1, and all 10,273 ocean cells are exactly -250 m with mask 0 (re-checked) |
| all | failed cell | score x 0.35, cell kept (`analog_finder.py:314-317`) | score NaN, cell removed (`mission_scoring.py:153`) |
| all | score | 0.65 x analog similarity + 0.35 x hand-coded `gate_q` | soft utilities only; similarity optional through `combine_with_similarity` |
| all | domain weights | drive the similarity part through `map_domain_weights_to_features` | not used by the module (only passed through `to_web_cfg`, which nobody calls) |
| all | missing data | gates "keep", `require_present` fails | the same in the shipped JSON |
| rover | gates | slope_300m_deg 0.5-15.0; rough_300m_m 5.0-650.0 | identical |
| rover | quality | Gaussian around the **Tycho zone mean** (slope 9.3746 deg, rough 719.3236 m): `exp(-0.5((s-9.37)/5)^2)` and `exp(-0.5((r-719.3)/120)^2)`, weights 0.45 / 0.30, plus 0.25 rock (`analog_finder.py:274-285`). The 719.3 m target lies above the 650 m gate. | linear, flatter and smoother is better (slope 15 -> 1, rough 650 -> 30) plus rock 0 -> 0.7. Its `provisional` text calls it "una aproximacion lineal de la formula antigua". **It is not**: the old formula rewards slope near the lunar 9.4 deg, the new one rewards the flattest ground. |
| solar | gates | irradiance 1.8-8.5; sun_elev 5-85; sun_low 0.025-0.4 | irradiance >= 2.5; slope_deg <= 15; sun_elev >= 10; sun_low <= 0.25; not agua. `slope_deg` added to `require_present` |
| solar | quality | `0.45*irr_q + 0.35*low_q + 0.20*elev_q`, with `low_q = (slow-0.025)/0.18`: **more grazing sun scores higher**. `elev_q` peaks at 35 deg (`analog_finder.py:286-293`) | sun_low 0.25 -> 0.03: **more grazing sun scores lower**; sun_elev 10 -> 70: higher sun is better |
| solar | lunar target | "South Pole PSR & Shackleton Rim (75°S–90°S)" profile (`analog_finder.py:258-263`) | none |
| thermal | gates | amplitude 16-60; class allow roca/regolito/arena/hielo, **so `suelo` fails** | amplitude >= 15; tmin_c <= 5; class exclude agua, **so `suelo` passes** |
| thermal | quality | `0.50*amp_q + 0.25*tic_q + 0.25*rock`; amp_q = (amp-16)/28; tic_q roca/hielo 1.0, regolito 0.85, else 0.7 | soft table above. `hielo` scores 0.4 there, against 1.0 in the old formula |
| ice | gate | permafrost exclude ninguno/none | identical |
| ice | quality | `0.55*clip((280-T)/60) + 0.45*pfc_q`, pfc continuo 1 / discontinuo 0.85 / esporadico 0.70 / else 0.55, then 0.65 x similarity to the PSR zone | identical utility (280 -> 220 is (280-T)/60; default 0.55); no similarity term |
| solar, thermal | frozen | 2026-11-14T16:30 | null (not frozen) |

**Why the counts differ** (A3 section 2):

- Solar 5,198 against 5,192: the old `sun_elev_max <= 85` removes 729 tropical land cells. The new gates remove polar and steep cells instead.
- Thermal 3,337 against 2,613: the new gate `tmin_c <= 5` is added, and `suelo` is allowed.

## (d) Reproduction of the author's counts, and the same gates on the Moon

**Command** (author's note, `Instruciones filtros solar y temp:27`), run in the scratch copy:

```
python mission_scoring.py run --cells output_py/earth_moon_harmonized_clean.csv --missions solar,thermal --out <scratch>/ms_st.csv
solar: 5192/16200 celdas pasan los filtros duros; score medio 60.2
thermal: 2613/16200 celdas pasan los filtros duros; score medio 57.6
pasan todas: 1986
```

**The author's declared counts (5,192 / 2,613 / 1,986, notes lines 21-23) reproduce exactly.** With `--missions rover,solar,thermal,ice`: rover 5,297 (mean 72.7), ice 3,023 (mean 70.6), all four 1,728.

**Main reasons cells fail.** Over all 16,200 cells, the 10,273 ocean cells fail `elevation_m`, `mask_fraction` and, for solar and thermal, `thermal_inertia_class = agua`. Restricted to the 5,927 land cells (A3 `s5.py`; a cell can fail several gates):

| Mission | Pass | Fails on land |
|---|---|---|
| rover | 5,297 | slope_300m_deg 591 (388 of them below 0.5 deg), rough_300m_m 290 (48 below 5 m, 242 above 650 m) |
| solar | 5,192 | sun_low_frac_0_5deg 540, irradiance_kwh_m2_day 449, slope_deg 203 |
| thermal | 2,613 | lst_diurnal_amp_k 2,381, tmin_c 2,271 |
| ice | 3,023 | permafrost_class 2,904 |

**Top cells:**

- **Solar:** Senegal, Chad, Somalia, Burkina Faso, Central African Republic, Benin and DR Congo, with scores 95.08-95.62 (top 10; countries from `reverse_geocoder`). The top 100 lies between -27 and 23 deg latitude. The note says "los mejores sitios están en el Sahel y el Sahara" (`Instruciones filtros solar y temp:21`); that is only partly true: several top-10 cells lie outside both, in Somalia (1 S), DR Congo (3 S) and the Central African Republic (5 N).
- **Thermal:** Tibet and Xinjiang (scores 80.2-84.1), then East Antarctica near -80 deg (about 79.4).

### The same gates on lunar cells

This is hypothetical: the CLI scores only EARTH rows, and `analog_finder.py` gates only Earth cells. Re-run with `docscripts/check2.py` on the 16,200 MOON rows.

| Mission | Old system pass | New system pass | What removes lunar cells |
|---|---|---|---|
| rover | 9,062 | 1,910 | new: `elevation_m >= 1` fails 11,041 cells (the sole cause for 7,152); rough > 650 fails 7,006 |
| solar | 14,400 | 4,712 | old: `sun_elev_max` outside 5-85, i.e. abs(lat) <= 5 and abs(lat) >= 87. New: `elevation_m` (11,041); irradiance >= 2.5 removes every cell at abs(lat) >= 79 and 306 of 360 at abs(lat) = 77; `sun_elev >= 10` removes abs(lat) >= 83; `sun_low <= 0.25` removes abs(lat) >= 85 |
| thermal | **0** | 5,159 | old: every lunar amplitude (63.08-179.99 K) exceeds 60, and every lunar cell is class `suelo`. New: only `elevation_m` fails |
| ice | 4,680 | 801 | new: permafrost (11,520 `ninguno`) plus elevation |
| all four | 0 | 203 | |

**Findings on the Moon:**

- The common gate's `why` is "descarta oceano". On the Moon `elevation_m` is height relative to the 1737.4 km datum, so the gate removes 11,041 of 16,200 lunar cells for no physical reason.
- With the new gates, **no lunar cell poleward of about 77 deg can pass solar**, and the near-continuously lit polar ridges lie exactly there (R2 section 1; R3 section 4).

## (e) How `analog_finder.py` scores today

**Effective feature weights after the domain mapping.** `map_domain_weights_to_features` (`analog_finder.py:225-240`; duplicated in `web/index.html:669-691`) applies these coefficients and then divides by the total:

```
slope_deg         = relieve*0.45 + luz*0.15
roughness_m       = relieve*0.35 + material*0.20
elevation_rel_m   = relieve*0.20 + luz*0.35 + agua*0.20
temp_k            = termico*0.80 + luz*0.35 + agua*0.45
rock_or_bare_frac = material*0.55 + termico*0.20 + luz*0.15
sar_sigma0_db     = material*0.25 + agua*0.35
```

Re-computed with the module itself:

| Mission | slope_deg | roughness_m | elevation_rel_m | temp_k | rock_or_bare_frac | sar_sigma0_db |
|---|---|---|---|---|---|---|
| rover | 0.1725 | 0.1825 | 0.1350 | **0.1825** | 0.2000 | 0.1275 |
| solar | 0.1350 | 0.0725 | 0.2075 | 0.3625 | 0.1625 | 0.0600 |
| thermal | 0.0825 | 0.1025 | 0.0750 | 0.4175 | 0.2425 | 0.0800 |
| ice | 0.0825 | 0.0825 | 0.1350 | 0.3925 | 0.1475 | 0.1600 |
| ranking default (`DEFAULT_WEIGHTS`, no mapping) | 0.25 | 0.20 | 0.15 | 0.15 | 0.15 | 0.10 |

**What the mapping does:**

- For the rover, `temp_k` (0.1825) outweighs `slope_deg` (0.1725), although relieve = 0.35 and termico = 0.10.
- "luz" (light) has no light variable to land on: irradiance, sun elevation and grazing fraction are not similarity features (`analog_finder.py:59-66`). Light weight therefore flows into `temp_k` and `elevation_rel_m`.

**The 0.35 multiplier.**

- The mission score is `combined = 0.65*analog_sim + 0.35*gate_q`, then `score = where(pass, combined, combined*0.35)` (`analog_finder.py:314-317`). `score_all` uses the same rule (lines 320-322).
- A failed cell keeps 35 % of its score. It is written to `analog_ranking.csv` and to the web JSON (`s_rov`, `s_sol`, ...).
- `build_optimal_mission_zones` keeps only passing cells (line 339).
- The browser recomputes the scores and sets failed missions to 0 (`web/index.html:1113-1118`). **The backend outputs and the browser therefore disagree on failed cells.**

**How similarity is normalised, and what that means.**

- Each body is normalised **separately**: `z = clip((v - median)/(IQR/1.349), -4, 4)`, and a missing value gets z = 0 (`analog_finder.py:143-181`). Earth uses land cells only (lines 430-434).
- Distance: `rms = sqrt(sum w_f (z_earth - z_target)^2)`, and `similarity_pct = 100*exp(-0.45*rms)` (lines 448-457).
- Consequence: a z-score says where a cell sits within its own planet, not how physically alike two places are. Earth land `temp_k` spans 217-328 K and the Moon 43-110 K, yet `sim_temp_k_pct` reaches 100.0. In the committed top 100, `sim_temp_k` is 91.86-100.0 and `similarity_pct` 87.75-94.01 (A3 section 7).

**How an Earth cell is paired with a lunar target.**

- An Earth cell is never paired with a lunar cell. It is compared with a zone **mean z-profile**.
- The ranking target is "Global Lunar Surface Mean". `matched_lunar_zone` is the argmin of the weighted distance over the six other zones (lines 460-470).
- Each mission uses a fixed target zone: rover Tycho; solar and ice "South Pole PSR & Shackleton Rim"; thermal Global (lines 250-263).
- In the committed ranking, all 100 cells match "Tycho & Southern Rocky Craters".
- The zones are latitude/longitude boxes or value masks (lines 184-222). Two of them are mislabelled (AUDIT.md section (g)).

## (f) Rover: preset as committed against both JSON files

`rover_preset.py` as committed (607 lines, identical to the copy in the zip):

- No version string.
- No reference to `rover_integration.py`.
- No benchmark CSV and no site coordinates (A1 section 6; A4 section 5).

| Item | `rover_preset.py` (`ROVER_SPEC` lines 71-86, `PRESET_CONFIG` lines 92-112) | `mission_filters.json` rover = `mission_scoring.json` rover |
|---|---|---|
| slope gate | `{"min": None, "max_from": "max_operational_slope_deg"}`; that field = 15, source "ESTIMADO - replace from project DB", status "VERIFICAR" | **min 0.5**, max 15.0, source "...NASA VIPER operational slope limit (15 deg < 47.29 deg static tip-over, rover_preset.py)" |
| roughness gate | `{"min": None, "max": None, "source": "no gate until Robotics 1 sets one"}` | **min 5.0, max 650.0**, source "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)" |
| tolerances | 5.0 deg / 10.0 m, source "ILUSTRATIVO - set by Robotics 1" | 5.0 / 10.0, source "Robotics 1 rover_preset.py tolerance scale" (the ILUSTRATIVO label is dropped) |
| weights | 0.35 / 0.30 / 0.10 / 0.10 / 0.15, every source starting "ILUSTRATIVO" | same numbers, described as "Robotics 1 rover_preset.py sector weights" |
| workable_days | 1 / 12 / -10, "ILUSTRATIVO - phase-1 plan, model 1 defaults" | same numbers, "Phase-1 plan model 1 defaults (rover_preset.py)" |

**The contradiction, stated exactly.**

- The preset sets no roughness gate and no minimum slope. Both JSON files add `rough_300m_m` 5-650 and `slope_300m_deg >= 0.5`, and attribute the rover numbers to `rover_preset.py`.
- The JSON files call 15 deg a "NASA VIPER operational slope limit", while the preset marks that same field ESTIMADO/VERIFICAR.

What the official sources say (R1 section 3): 15 deg is a VIPER requirement or design limit in four NASA documents (M24 p.4 "Slopes up to 15 deg (reqt)"; F26 p.22 "15 deg slopes + 20 cm step obstacles (design limit)"). The value is supported, but as a rover-scale capability. No official product uses a 300 m baseline, and the column here is a 2-degree cell value (`harmonizer_cleaner.py:303`).

**Which path is live:**

- `analog_finder.py` applies the gates from `mission_filters.json` (lines 475 and 504-510), so the live rover gates are slope 0.5-15 and roughness 5-650.
- Tolerances are read from the JSON first, with the preset as fallback (line 278).
- `workable_days` comes from the preset (lines 494-502) and is not a gate.
- The preset's own `gates` are only exported inside `rover_preset` in the web bundle.
- In the browser, the gates come from `data.mission_filters` (`web/index.html:646`), and the rover-panel input `rpMaxOpSlopeDeg` overwrites the slope maximum live (A3 section 4).
- The new `mission_scoring.json` rover block is not live anywhere.

**Side effects of the live path:**

- `analog_finder.py:35-56` builds the preset with `freeze=True, allow_unverified=True`, which bypasses the module's own guard against freezing unverified values.
- `merge_into_presets(..., refreeze=True)` rewrites `data/presets/presets.json` on every pipeline and pytest run (A1 section 1.2).

**Preset values against R1:**

| Field | Preset value | R1 finding |
|---|---|---|
| mass_kg | 440, "OK", "Phase-1 plan (VIPER, arXiv 2405.11001)" | roving 447 kg, launch 490 kg (B25 p.46 "Mass: launch = 490kg, roving = 447kg") |
| max_speed_mps | 0.20 | 20 cm/s (B25 p.17) |
| ground_clearance_m | None, "MISSING" | 7 to 43 cm adjustable (B25 p.47) |
| wheelbase_m, track_m | 1.30, 1.30 | no official source found; footprint 1.7 x 1.7 m |
| cg_height_m | 0.60 | no official source found |

## (g) Every threshold and weight of the new system against official sources

Verdicts: **supported**, **contradicted**, or **no official source found** (n.s.f.). Sources:

- [sources/R3_threshold_sources.md](sources/R3_threshold_sources.md) (F-numbers are facts, D-numbers derived values);
- [sources/R1_viper_rover_spec_sources.md](sources/R1_viper_rover_spec_sources.md);
- [sources/R2_lunar_reference_sources.md](sources/R2_lunar_reference_sources.md).

R3 was written from values reported by the team lead. Every value below was re-read from `mission_scoring.json`. R3 called the irradiance unit an inference; the column name `irradiance_kwh_m2_day` states the unit. No value is changed here.

| Mission / item | Value | Author's reason (exact) | Official sources | Verdict |
|---|---|---|---|---|
| common gate elevation_m | min 1.0 | "solo tierra firme (descarta oceano, que el modelo fija en -250 m)" | none defines land by a 1 m elevation (R3 section 3); on the Moon elevation is relative to a datum | n.s.f.; wrong on the Moon |
| common gate mask_fraction | min 0.3 | "celda con dato suficiente" | none (R3 summary 7). The column is a function of elevation, not data coverage (`harmonizer_cleaner.py:243-247`) | n.s.f. |
| rover gate slope_300m_deg max | 15.0 | source "NASA VIPER operational slope limit" | VIPER "Slopes up to 15 deg (reqt)" (R1, M24 p.4); Apollo LRV designed for 20-23 deg, max 25 (R3 F21) | **supported** for the rover scale; not for a 300 m or 2-degree baseline (R1 section 4) |
| rover gate slope_300m_deg min | 0.5 | (none beyond the shared source) | none (R3: "Removes flat terrain, which is unusual for a rover gate") | n.s.f. |
| rover gate rough_300m_m | 5.0-650.0 | source "LRO LOLA & CNSA Yutu/VIPER topographic hazard envelope (5-650 m)" | none found; LOLA roughness products use 57 m to 2.7 km baselines (R1 section 4) | n.s.f. |
| rover soft slope_300m_deg | w 0.45, 15 -> 1 | "menos pendiente = mas traficable" | none | n.s.f. |
| rover soft rough_300m_m | w 0.30, 650 -> 30 | "menos rugosidad = menos obstaculos" | none | n.s.f. |
| rover soft rock_or_bare_frac | w 0.25, 0.0 -> 0.7 | "suelo expuesto firme frente a vegetacion" | none | n.s.f. |
| rover tolerances | 5.0 deg, 10.0 m | source "Robotics 1 rover_preset.py tolerance scale (5.0 deg)" / "Robotics 1 rover_preset.py tolerance scale (10.0 m)" | marked ILUSTRATIVO in the preset; not read by `mission_scoring.py` | n.s.f. |
| solar gate irradiance | min 2.5 kWh/m2/day | "diseno: por debajo, la generacion no compensa" | no official global minimum; BLM's former cut was 6.5 kWh/m2/day (R3 F19). Horizontal irradiance at a lunar pole is at most 0.88 kWh/m2/day (R3 D3) | n.s.f. as a value; on the Moon it removes the poles |
| solar gate slope_deg | max 15.0 | "diseno: el campo de placas necesita terreno practicamente plano" | federal 2012 exclusion: slopes over 5 % = 2.9 deg (R3 F19, D5); best-lit lunar polar sites have slopes of 8.4-17.1 deg (R3 F9) | **contradicted** as Earth solar siting (the reason itself says "practicamente plano"); plausible for lunar rims |
| solar gate sun_elev_max_deg | min 10.0 | "diseno: sol siempre rasante = sombras permanentes" | "At the Moon's North and South Poles, the Sun is never more than 1.5° above or below the horizon" (R2, SVS 4893); the gate fails every lunar cell above about 81.5 deg (R3 D1) | **contradicted** for the lunar poles; the reason equates grazing sun with permanent shadow, which R2's PSR definition contradicts |
| solar gate sun_low_frac_0_5deg | max 0.25 | "diseno: demasiado tiempo con sol a <5 grados" | at the lunar poles the Sun is always grazing (R3 F5) | n.s.f.; contradicts polar physics |
| solar gate thermal_inertia_class | exclude agua | "diseno: no se instala sobre agua" | definition | design choice |
| solar soft irradiance | w 0.35, 2.5 -> 6.0 | "energia disponible" | none | n.s.f. |
| solar soft sun_elev_max_deg | w 0.15, 10 -> 70 | "mejor captacion con sol alto" | no source for the weight (R3 summary 7: all weights are design choices). The polar advantage is near-continuous light at a low Sun angle (R3 F8; R2 Gläser 2014: 92.27 % of time at 2 m) | n.s.f. for the weight; its direction (higher Sun is better) runs against the polar facts as a lunar-analog criterion. This is an inference from R2/R3 facts, not an R3 verdict |
| solar soft sun_low_frac_0_5deg | w 0.15, 0.25 -> 0.03 | "menos tiempo de sol rasante" | same | same: n.s.f. for the weight; direction runs against the polar facts (inference, not an R3 verdict) |
| solar soft slope_deg | w 0.15, 12 -> 1 | "menos movimiento de tierras" | none | n.s.f. |
| solar soft lst_diurnal_amp_k | w 0.10, 35 -> 10 | "menos ciclado termico en los paneles" | none | n.s.f. |
| solar soft roughness_m | w 0.10, 400 -> 30 | "terreno llano = montaje mas facil" | none | n.s.f. |
| thermal gate lst_diurnal_amp_k | min 15.0 | "diseno: sin ciclo termico fuerte no hay ensayo util" | lunar equator about 295 K (R3 D6); R2 Diviner GCP sample: 250-300 K below 60 deg, medians 165-176 K at 80-90 deg; Diviner page: polar crater rims "remain constant at around 220K" (R3 F12) | n.s.f. (design) |
| thermal gate tmin_c | max 5.0 | "diseno: hace falta frio real para estresar el equipo" | air vs surface temperature not stated (R3 F14) | n.s.f. |
| thermal gate thermal_inertia_class | exclude agua | "diseno: el agua amortigua los ciclos" | definition | design choice |
| thermal soft lst_diurnal_amp_k | w 0.35, 15 -> 35 | "amplitud termica diaria (estres por ciclado)" | R3: "defensible" as a relative scale; no Earth cell approaches the lunar 250-300 K (R2 section 3) | n.s.f. (design) |
| thermal soft tmin_c | w 0.25, 5 -> -50 | "minimas extremas" | lunar pre-dawn minimum about 95 K = -178 C (R2 section 3) | n.s.f. |
| thermal soft thermal_inertia_class | w 0.15, map above | "superficie de baja inercia, parecida al regolito" | regolith thermal inertia 55 ± 2 (R2, Hayne 2017); the class is computed from bare fraction, not from inertia data | n.s.f. |
| thermal soft rock_or_bare_frac | w 0.10, 0.10 -> 0.70 | "superficie expuesta, sin vegetacion que amortigue" | none | n.s.f. |
| thermal soft irradiance | w 0.10, 3.0 -> 6.0 | "mayor carga solar = mayor calentamiento diurno" | none | n.s.f. |
| thermal soft permafrost_class | w 0.05, map above | "ciclos congelacion-deshielo" | none | n.s.f. |
| ice gate permafrost_class | exclude ninguno, none | "plan fase 1, parte 3 (IPA Brown et al. permafrost & cryosphere map)" | permafrost = ground at or below 0 C for at least two consecutive years (R3 F17, F18). The code's classes are temperature thresholds of 274.15 K (+1 C), 270.15 K and 265.15 K, plus 278 K above 3,400 m (`harmonizer_cleaner.py:282-284`); no IPA map is read | concept **supported**; implementation **contradicts** the cited source |
| ice soft temp_k | w 0.55, 280 -> 220 | "mas frio = hielo mas estable" | lunar cold-trap threshold 110 K (R2 section 3) | n.s.f. |
| ice soft permafrost_class | w 0.45, continuo 1.0 / discontinuo 0.85 / esporadico 0.7, default 0.55 | "continuidad del permafrost" | none | n.s.f. |
| domain weights (all missions) | as in section (b) | used only by the web "Use Weights" button (note) | none (R3 summary 7) | n.s.f.; the rover ones are ILUSTRATIVO in `rover_preset.py` |

## (h) The ice mission in both systems

| Item | Old (`mission_filters.json:121-145` + `analog_finder.py`) | New (`mission_scoring.json:74-88`) |
|---|---|---|
| description | "Cryospheric Drilling & Volatiles/Ice Prospecting (ISRU)" | "Perforacion y prospeccion de hielo (solo si sobra tiempo)" |
| gate | `permafrost_class` exclude ["ninguno", "none"], source "plan fase 1, parte 3 (IPA Brown et al. permafrost & cryosphere map)" | identical, plus the common gates |
| require_present | permafrost_class | permafrost_class |
| score | `0.65*analog_sim(PSR zone) + 0.35*(0.55*clip((280-temp_k)/60,0,1) + 0.45*pfc_q)`, pfc_q continuo 1.0, discontinuo 0.85, esporadico 0.70, else 0.55; x0.35 if the gate fails (`analog_finder.py:301-310`) | soft temp_k 0.55 (280 -> 220) + permafrost 0.45 (map, default 0.55): the same utility, without the similarity term; NaN if the gate fails |
| domain weights | 0.15 / 0.15 / 0.25 / 0.1 / 0.35 | same |
| frozen | 2026-11-14T16:30:00+00:00 | same |
| Earth pass | 3,023 | 3,023 |
| Moon pass (hypothetical) | 4,680 | 801 |
| what `permafrost_class` really is | Earth: `continuo` T <= 265.15 K, `discontinuo` <= 270.15 K, `esporadico` <= 274.15 K or (elev >= 3400 m and T <= 278 K). Moon: `continuo` abs(lat) >= 75 and T <= 75 K; `discontinuo` abs(lat) >= 65 and 75 < T <= 90 K (`harmonizer_cleaner.py:276-284`). MODELLED from `temp_k`, whose origin is undocumented. | same column |
| lunar target | "South Pole PSR & Shackleton Rim (75°S–90°S)" = every cell with lat <= -75 (1,440 cells), a latitude band, not a PSR map | none |

R3 notes that permafrost has no lunar equivalent by definition. The lunar analogue is cold-trap temperature: surfaces below 110 K (R2 section 3), with PSR floors as low as 25 K (R3 F13).

## (i) Effective weights of the domain mapping

Added 2026-11-14 with [SIMILARITY_PROPOSAL.md](SIMILARITY_PROPOSAL.md) (its section 4.1 lists every variant on both datasets). Domain weights from `mission_scoring.json` (relieve / material / termico / luz / agua): rover 0.35 / 0.30 / 0.10 / 0.10 / 0.15; solar 0.15 / 0.10 / 0.20 / 0.45 / 0.10; lunar base = thermal 0.15 / 0.25 / 0.45 / 0.10 / 0.05. Values are percent of the similarity weight.

**Today** (`map_domain_weights_to_features`, used by the web page's "Use Weights"; six variables; recomputed with the module's own function, confirming section (e)):

| Mission | slope | roughness | relative elevation | temperature | bare fraction | radar |
|---|---|---|---|---|---|---|
| Rover | 17.25 | 18.25 | 13.50 | 18.25 | 20.00 | 12.75 |
| Solar panels | 13.50 | 7.25 | 20.75 | 36.25 | 16.25 | 6.00 |
| Lunar base (thermal) | 8.25 | 10.25 | 7.50 | 41.75 | 24.25 | 8.00 |

"luz" and "agua" have no variable among the six, so the matrix spreads them over slope, relative elevation, temperature, bare fraction and radar. For the rover, temperature (18.25) outweighs slope (17.25) although relieve is 0.35 and termico 0.10. On the real 1-degree data radar is absent and bare fraction is removed (constant on the Moon), and the same matrix renormalised over the four remaining variables gives:

| Mission (real data) | slope | roughness | relative elevation | temperature |
|---|---|---|---|---|
| Rover | 25.65 | 27.14 | 20.07 | 27.14 |
| Solar panels | 17.36 | 9.32 | 26.69 | 46.62 |
| Lunar base (thermal) | 12.18 | 15.13 | 11.07 | 61.62 |

**Proposed (A3a, pending approval).** Each domain spends its weight only on its own variables among those in the similarity (relieve: slope, roughness, relative elevation; material: bare fraction and radar; termico: temperature), split inside a domain in proportion to `DEFAULT_WEIGHTS`; "luz" and "agua" are dropped and the rest renormalised.

| Mission | dataset | slope | roughness | relative elevation | temperature | bare fraction | radar |
|---|---|---|---|---|---|---|---|
| Rover | legacy 2-degree | 19.44 | 15.56 | 11.67 | 13.33 | 24.00 | 16.00 |
| Rover | real 1-degree | 32.41 | 25.93 | 19.44 | 22.22 |  |  |
| Solar panels | legacy 2-degree | 13.89 | 11.11 | 8.33 | 44.44 | 13.33 | 8.89 |
| Solar panels | real 1-degree | 17.86 | 14.29 | 10.71 | 57.14 |  |  |
| Lunar base (thermal) | legacy 2-degree | 7.35 | 5.88 | 4.41 | 52.94 | 17.65 | 11.76 |
| Lunar base (thermal) | real 1-degree | 10.42 | 8.33 | 6.25 | 75.00 |  |  |

For reference, the approved rule without mission weights (A1, `DEFAULT_WEIGHTS` renormalised) is slope 25 / roughness 20 / relative elevation 15 / temperature 15 / bare fraction 15 / radar 10 on the legacy table and 33.33 / 26.67 / 20.00 / 20.00 on the real table, for all three missions. Adding the light variables (A3b) is shown in the proposal; it is not recommended, because maximum sun elevation and low-sun fraction are flat-horizon formulas of latitude on both bodies, and irradiance on Earth is an interpolated climatology under the atmosphere.

## (j) Scope: three missions

The product ranks Earth analog points for three missions: Rover, Solar panels and Lunar base. **Lunar base is a copy of the `thermal` block** of `mission_scoring.json` (team decision): the same required variables (`lst_diurnal_amp_k`, `tmin_c`, `thermal_inertia_class`), hard filters (amplitude >= 15 K, minimum <= 5 C, not water), soft criteria and domain weights; only its lunar target zone differs (the nine NASA candidate landing regions, [SIMILARITY_PROPOSAL.md](SIMILARITY_PROPOSAL.md) section 1). The `thermal` and `ice` blocks stay in `mission_scoring.json` as components: `thermal` is the source of Lunar base and `ice` keeps its gates and soft criteria for later use, but neither is shown as a separate mission. In the JSON this is the `lunar_base` block and the list `"offered_missions": ["rover", "solar", "lunar_base"]`, both added by checkpoint commit 3b6c949; the verifier checked that the block's `require_present`, `gates`, `soft` and `weights` are identical to `thermal`. No other field of `mission_scoring.json` was changed.
